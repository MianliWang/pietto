"""Structured parser diagnostics and internal AST construction errors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from antlr4.error.ErrorListener import ErrorListener


class Severity(StrEnum):
    """Severity levels exposed by parser diagnostics."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A one-based source location with optional half-open end coordinates."""

    path: str | None
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A structured, user-facing parser diagnostic."""

    code: str
    severity: Severity
    message: str
    location: SourceLocation
    suggestion: str | None = None


class AstBuildError(Exception):
    """An ordinary source error discovered while constructing the AST."""

    def __init__(self, message: str, *, line: int, column: int) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


def source_path(path: str | Path | None) -> str | None:
    """Normalize an optional path for public diagnostic and AST values."""

    return str(path) if path is not None else None


class DiagnosticErrorListener(ErrorListener):
    """Convert ANTLR lexer and parser errors into Pietto diagnostics."""

    def __init__(self, path: str | Path | None) -> None:
        self.path = source_path(path)
        self.diagnostics: list[Diagnostic] = []

    def syntaxError(
        self,
        recognizer: object,
        offendingSymbol: object,
        line: int,
        column: int,
        msg: str,
        exception: Exception | None,
    ) -> None:
        """Record an ANTLR syntax callback as a generic Phase 1 error."""

        del recognizer, offendingSymbol, exception
        self.diagnostics.append(
            Diagnostic(
                code="PIE-P1000",
                severity=Severity.ERROR,
                message=msg,
                location=SourceLocation(
                    path=self.path,
                    line=line,
                    column=column + 1,
                ),
            )
        )
