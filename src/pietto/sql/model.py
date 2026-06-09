"""Immutable public models for generated SQL artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto.errors import Diagnostic


class SqlArtifactKind(StrEnum):
    """Kinds of SQL artifacts produced by backend emitters."""

    RELATION = "relation"


@dataclass(frozen=True, slots=True)
class SqlArtifact:
    """One named SQL artifact emitted for a compiler definition."""

    name: str
    kind: SqlArtifactKind
    sql: str


@dataclass(frozen=True, slots=True)
class SqlResult:
    """Generated SQL artifacts and ordered backend diagnostics."""

    artifacts: tuple[SqlArtifact, ...]
    diagnostics: tuple[Diagnostic, ...]
