"""Private MySQL SQL generation skeleton."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields, is_dataclass
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
    SymbolId,
    TypeIR,
)
from pietto.sql.model import SqlArtifact, SqlArtifactKind, SqlResult
from pietto.sql.mysql_relations import MySqlEmission, render_mysql_relation
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
    emission = MySqlEmission()
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
                    emission=emission,
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


def emit_mysql_sql_refusing_constants(
    script_ir: ScriptIR,
    constant_reads: frozenset[tuple[str | None, int, int, int, int]],
) -> SqlResult:
    """``emit_mysql_sql``, but each relation that holds a top-level constant
    read (``constant_reads`` are their source ranges), or reads a relation
    that does, is refused: MySQL emits no constant until its two-engine
    differential passes. The other relations emit as before."""

    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    refused = {
        definition.symbol
        for definition in relations
        if any(
            type(item) is SourceSpan
            and (item.path, item.line, item.column, item.end_line, item.end_column)
            in constant_reads
            for item in _ir_values(definition)
        )
    }
    grown = bool(refused)
    while grown:
        grown = False
        for definition in relations:
            if definition.symbol not in refused and any(
                type(item) is SymbolId and item in refused
                for item in _ir_values(definition)
            ):
                refused.add(definition.symbol)
                grown = True
    if not refused:
        return emit_mysql_sql(script_ir)
    kept = emit_mysql_sql(
        ScriptIR(
            definitions=tuple(
                definition
                for definition in script_ir.definitions
                if not isinstance(definition, RelationIR)
                or definition.symbol not in refused
            )
        )
    )
    diagnostics = [
        *kept.diagnostics,
        *(
            _unsupported_definition_diagnostic(
                definition,
                reason="MySQL has no top-level constants yet; "
                "emit with --dialect postgres",
            )
            for definition in relations
            if definition.symbol in refused
        ),
    ]
    # Every diagnostic is at its definition, so source order is definition order.
    diagnostics.sort(key=lambda item: (item.location.line, item.location.column))
    return SqlResult(artifacts=kept.artifacts, diagnostics=tuple(diagnostics))


def _ir_values(definition: DefinitionIR) -> Iterator[object]:
    """Every value inside ``definition``'s IR, its spans and symbols included."""

    pending: list[object] = [definition]
    while pending:
        item = pending.pop()
        if type(item) is tuple:
            pending.extend(cast(tuple[object, ...], item))
            continue
        yield item
        if (
            is_dataclass(item)
            and not isinstance(item, type)
            and type(item) not in (SourceSpan, SymbolId)
        ):
            pending.extend(getattr(item, field.name) for field in fields(item))


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
