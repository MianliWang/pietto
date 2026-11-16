"""Private SQLite single-file SQL generation (Phase78 B1), and the one
qualified SQLite build (D78.03) that the `sqlite_file` route requires."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class SQLiteBuild:
    release: str
    source_id: str
    compile_options: tuple[str, ...]


# The SQLite target of D78.03: family sqlite, release 3.53.1, this source id
# and these compile options together; a version alone is no identity. The
# native qualification and the `sqlite_file` route read it; the job store
# keeps its own constant.
QUALIFIED_SQLITE_BUILD = SQLiteBuild(
    release="3.53.1",
    source_id=(
        "2026-05-05 10:34:17 "
        "c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9"
    ),
    compile_options=(
        "ATOMIC_INTRINSICS=1",
        "COMPILER=clang-22.1.3",
        "DEFAULT_AUTOVACUUM",
        "DEFAULT_CACHE_SIZE=-2000",
        "DEFAULT_FILE_FORMAT=4",
        "DEFAULT_JOURNAL_SIZE_LIMIT=-1",
        "DEFAULT_MMAP_SIZE=0",
        "DEFAULT_PAGE_SIZE=4096",
        "DEFAULT_PCACHE_INITSZ=20",
        "DEFAULT_RECURSIVE_TRIGGERS",
        "DEFAULT_SECTOR_SIZE=4096",
        "DEFAULT_SYNCHRONOUS=2",
        "DEFAULT_WAL_AUTOCHECKPOINT=1000",
        "DEFAULT_WAL_SYNCHRONOUS=2",
        "DEFAULT_WORKER_THREADS=0",
        "DIRECT_OVERFLOW_READ",
        "ENABLE_DBSTAT_VTAB",
        "ENABLE_FTS3",
        "ENABLE_FTS3_PARENTHESIS",
        "ENABLE_FTS4",
        "ENABLE_FTS5",
        "ENABLE_GEOPOLY",
        "ENABLE_MATH_FUNCTIONS",
        "ENABLE_PERCENTILE",
        "ENABLE_RTREE",
        "MALLOC_SOFT_LIMIT=1024",
        "MAX_ATTACHED=10",
        "MAX_COLUMN=2000",
        "MAX_COMPOUND_SELECT=500",
        "MAX_DEFAULT_PAGE_SIZE=8192",
        "MAX_EXPR_DEPTH=1000",
        "MAX_FUNCTION_ARG=1000",
        "MAX_LENGTH=1000000000",
        "MAX_LIKE_PATTERN_LENGTH=50000",
        "MAX_MMAP_SIZE=0x7fff0000",
        "MAX_PAGE_COUNT=0xfffffffe",
        "MAX_PAGE_SIZE=65536",
        "MAX_SQL_LENGTH=1000000000",
        "MAX_TRIGGER_DEPTH=1000",
        "MAX_VARIABLE_NUMBER=32766",
        "MAX_VDBE_OP=250000000",
        "MAX_WORKER_THREADS=8",
        "MUTEX_PTHREADS",
        "SYSTEM_MALLOC",
        "TEMP_STORE=1",
        "THREADSAFE=1",
    ),
)

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
