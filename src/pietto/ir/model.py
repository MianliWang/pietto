"""Immutable public models for Pietto Semantic IR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto.errors import Diagnostic


class SymbolNamespace(StrEnum):
    """Semantic namespaces used to form stable IR symbol identities."""

    TYPE = "type"
    CALLABLE = "callable"
    RELATION = "relation"


class TypeKindIR(StrEnum):
    """Type declaration kinds copied from resolved semantic facts."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"


class NullabilityIR(StrEnum):
    """Effective nullability preserved independently from parser syntax."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """A parser-independent, 1-based, half-open source range."""

    path: str | None
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class SymbolId:
    """A stable resolved symbol identity within one semantic namespace."""

    namespace: SymbolNamespace
    name: str


@dataclass(frozen=True, slots=True)
class TypeRefIR:
    """Declared and canonical type metadata copied from semantic analysis."""

    symbol: SymbolId | None
    canonical_symbol: SymbolId | None
    declared_name: str
    canonical_name: str
    kind: TypeKindIR
    canonical_kind: TypeKindIR
    nullability: NullabilityIR


@dataclass(frozen=True, slots=True)
class RowFieldIR:
    """An ordered row field with canonical type and source metadata."""

    name: str
    type_ref: TypeRefIR
    nullability: NullabilityIR
    span: SourceSpan | None


@dataclass(frozen=True, slots=True)
class RowSchemaIR:
    """An ordered row schema, optionally marked semantically unknown."""

    fields: tuple[RowFieldIR, ...]
    is_unknown: bool = False


@dataclass(frozen=True, slots=True)
class DefinitionIR:
    """Marker base for definition IR nodes added by later lowering slices."""


@dataclass(frozen=True, slots=True)
class ScriptIR:
    """Top-level Semantic IR container preserving definition order."""

    definitions: tuple[DefinitionIR, ...]


@dataclass(frozen=True, slots=True)
class IrResult:
    """A Semantic IR result and its ordered lowering diagnostics."""

    ir: ScriptIR | None
    diagnostics: tuple[Diagnostic, ...]
