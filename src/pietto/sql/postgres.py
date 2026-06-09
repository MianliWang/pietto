"""PostgreSQL SQL generation entry point."""

from __future__ import annotations

from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import (
    ConstraintIR,
    DeriveIR,
    EnumIR,
    RelationIR,
    ScriptIR,
    ShapeIR,
    SourceIR,
    TypeIR,
)
from pietto.sql.model import SqlResult

_PostgresDefinitionIR = (
    TypeIR | EnumIR | ShapeIR | ConstraintIR | DeriveIR | SourceIR | RelationIR
)


def emit_postgres_sql(script_ir: ScriptIR) -> SqlResult:
    """Return scaffold diagnostics for definitions not yet emitted as SQL."""

    return SqlResult(
        artifacts=(),
        diagnostics=tuple(
            _unsupported_definition_diagnostic(definition)
            for definition in script_ir.definitions
        ),
    )


def _unsupported_definition_diagnostic(
    definition: _PostgresDefinitionIR,
) -> Diagnostic:
    """Report one unsupported PostgreSQL emission target at its IR span."""

    span = definition.span
    return Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message=(
            "PostgreSQL SQL emission is not implemented for "
            f"{type(definition).__name__}: {definition.name}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
