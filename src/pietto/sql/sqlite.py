"""Private SQLite single-file SQL generation (Phase78 B1)."""

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
from pietto.sql.sqlite_relations import render_sqlite_relation
from pietto.sql.sqlite_render import SqliteRenderError

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


def emit_sqlite_sql(script_ir: ScriptIR, *, constant: str | None = None) -> SqlResult:
    """Emit the SQLite relations of one file, skip metadata, and fail closed.

    `constant` names a top-level constant the file declares. The IR holds
    each constant read as its literal, and SQLite single-file SQL reads no
    top-level constant or `--set` value yet (D78.01), so while the file
    declares one every relation is refused.
    """

    sources = {
        definition.symbol: definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR)
    }
    artifacts: list[SqlArtifact] = []
    diagnostics: list[Diagnostic] = []
    for definition in script_ir.definitions:
        if isinstance(definition, _NON_EMITTING_DEFINITION_TYPES):
            continue
        if not isinstance(definition, RelationIR):
            diagnostics.append(_unsupported_definition_diagnostic(definition))
            continue
        try:
            if constant is not None:
                raise SqliteRenderError(
                    "SQLite single-file SQL reads no top-level constant yet, "
                    f"and this file declares constant {constant}"
                )
            sql = render_sqlite_relation(definition, sources=sources)
        except SqliteRenderError as error:
            diagnostics.append(
                _unsupported_definition_diagnostic(definition, reason=str(error))
            )
            continue
        artifacts.append(
            SqlArtifact(name=definition.name, kind=SqlArtifactKind.RELATION, sql=sql)
        )
    return SqlResult(artifacts=tuple(artifacts), diagnostics=tuple(diagnostics))


def _unsupported_definition_diagnostic(
    definition: DefinitionIR,
    *,
    reason: str | None = None,
) -> Diagnostic:
    """Report one unsupported SQLite emission target at its IR span."""

    diagnostic_definition = cast(_DiagnosticDefinition, definition)
    span = diagnostic_definition.span
    message = (
        "SQLite SQL emission is not implemented for "
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
