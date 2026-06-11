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
from pietto.sql.model import SqlArtifact, SqlArtifactKind, SqlResult
from pietto.sql.mysql_relations import render_mysql_relation
from pietto.sql.mysql_render import MySqlRenderError

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
    """Emit approved MySQL relations, skip metadata, and fail closed."""

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
        if isinstance(definition, _NON_EMITTING_DEFINITION_TYPES):
            continue
        if isinstance(definition, _EMITTING_DEFINITION_TYPES):
            try:
                sql = render_mysql_relation(
                    definition,
                    sources=sources,
                    relations=relations,
                )
            except MySqlRenderError as error:
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
