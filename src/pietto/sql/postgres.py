"""PostgreSQL SQL generation entry point."""

from __future__ import annotations

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
    TypeIR,
)
from pietto.sql.model import SqlArtifact, SqlArtifactKind, SqlResult
from pietto.sql.relations import render_relation_sql

_MetadataDefinitionIR = TypeIR | EnumIR | ShapeIR | ConstraintIR | DeriveIR | SourceIR


def emit_postgres_sql(script_ir: ScriptIR) -> SqlResult:
    """Emit relation SELECTs, skip metadata, and diagnose unsupported targets."""

    sources = {
        definition.symbol: definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR)
    }
    relations = {
        definition.symbol: definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    }
    artifacts: list[SqlArtifact] = []
    diagnostics: list[Diagnostic] = []

    for definition in script_ir.definitions:
        if isinstance(definition, RelationIR):
            try:
                sql = render_relation_sql(
                    definition,
                    sources=sources,
                    relations=relations,
                )
            except (TypeError, ValueError) as error:
                diagnostics.append(
                    _unsupported_definition_diagnostic(
                        definition,
                        reason=str(error),
                    )
                )
                continue
            artifacts.append(
                SqlArtifact(
                    name=definition.name,
                    kind=SqlArtifactKind.RELATION,
                    sql=sql,
                )
            )
            continue
        if isinstance(definition, _MetadataDefinitionIR):
            continue
        diagnostics.append(_unsupported_definition_diagnostic(definition))

    return SqlResult(
        artifacts=tuple(artifacts),
        diagnostics=tuple(diagnostics),
    )


def _unsupported_definition_diagnostic(
    definition: DefinitionIR,
    *,
    reason: str | None = None,
) -> Diagnostic:
    """Report one unsupported PostgreSQL emission target at its IR span."""

    span = definition.span
    message = (
        "PostgreSQL SQL emission is not implemented for "
        f"{type(definition).__name__}: {definition.name}"
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
