"""Readonly public models produced by semantic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, TypeVar

from pietto.ast_nodes import (
    Definition,
    FieldDef,
    FromClause,
    Node,
    QueryDef,
    SourceDef,
    TableDef,
    TypeExpr,
)
from pietto.errors import Diagnostic

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")


class CheckMode(StrEnum):
    """Semantic checking modes supported by Pietto."""

    LOOSE = "loose"
    CHECKED = "checked"
    STRICT = "strict"


class TypeKind(StrEnum):
    """Kinds of type names recognized by minimal semantic resolution."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"


class EffectiveNullability(StrEnum):
    """Effective nullability recorded independently from parser syntax."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResolvedType:
    """A resolved type name and its optional user declaration."""

    name: str
    kind: TypeKind
    definition: Node | None = None


def _readonly_mapping(
    values: Mapping[_Key, _Value] | None = None,
) -> Mapping[_Key, _Value]:
    """Copy values into an immutable public mapping."""

    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True, slots=True)
class RowField:
    """A row field carrying resolved type and nullability information."""

    name: str
    resolved_type: ResolvedType
    nullability: EffectiveNullability
    definition: FieldDef | None = None


@dataclass(frozen=True, slots=True)
class RowSchema:
    """An ordered readonly row schema, optionally marked unknown."""

    fields: Mapping[str, RowField] = field(default_factory=_readonly_mapping)
    is_unknown: bool = False

    def __post_init__(self) -> None:
        """Copy row fields into an immutable mapping."""

        object.__setattr__(self, "fields", _readonly_mapping(self.fields))


@dataclass(frozen=True, slots=True)
class SemanticModel:
    """Readonly semantic state built incrementally across Phase 2."""

    mode: CheckMode
    type_symbols: Mapping[str, Definition] = field(default_factory=_readonly_mapping)
    callable_symbols: Mapping[str, Definition] = field(
        default_factory=_readonly_mapping
    )
    relation_symbols: Mapping[str, Definition] = field(
        default_factory=_readonly_mapping
    )
    type_resolutions: Mapping[TypeExpr, ResolvedType] = field(
        default_factory=_readonly_mapping
    )
    type_nullability: Mapping[TypeExpr, EffectiveNullability] = field(
        default_factory=_readonly_mapping
    )
    source_row_schemas: Mapping[SourceDef, RowSchema] = field(
        default_factory=_readonly_mapping
    )
    from_resolutions: Mapping[
        FromClause,
        SourceDef | TableDef | QueryDef,
    ] = field(default_factory=_readonly_mapping)
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema] = field(
        default_factory=_readonly_mapping
    )

    def __post_init__(self) -> None:
        """Copy public mapping inputs into immutable mappings."""

        object.__setattr__(self, "type_symbols", _readonly_mapping(self.type_symbols))
        object.__setattr__(
            self,
            "callable_symbols",
            _readonly_mapping(self.callable_symbols),
        )
        object.__setattr__(
            self,
            "relation_symbols",
            _readonly_mapping(self.relation_symbols),
        )
        object.__setattr__(
            self,
            "type_resolutions",
            _readonly_mapping(self.type_resolutions),
        )
        object.__setattr__(
            self,
            "type_nullability",
            _readonly_mapping(self.type_nullability),
        )
        object.__setattr__(
            self,
            "source_row_schemas",
            _readonly_mapping(self.source_row_schemas),
        )
        object.__setattr__(
            self,
            "from_resolutions",
            _readonly_mapping(self.from_resolutions),
        )
        object.__setattr__(
            self,
            "relation_row_schemas",
            _readonly_mapping(self.relation_row_schemas),
        )


@dataclass(frozen=True, slots=True)
class SemanticResult:
    """A semantic model and its ordered diagnostics."""

    model: SemanticModel
    diagnostics: tuple[Diagnostic, ...]
