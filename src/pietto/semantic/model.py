"""Readonly public models produced by semantic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, TypeVar

from pietto.ast_nodes import (
    Definition,
    Expression,
    FieldDef,
    FromClause,
    Node,
    QueryDef,
    SatisfyingClause,
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


class ValueTypeKind(StrEnum):
    """Whether an expression value type is known or unavailable."""

    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResolvedType:
    """A resolved type name and its optional user declaration."""

    name: str
    kind: TypeKind
    definition: Node | None = None


@dataclass(frozen=True, slots=True)
class ValueType:
    """An expression's resolved type and effective nullability."""

    resolved_type: ResolvedType
    nullability: EffectiveNullability
    kind: ValueTypeKind = ValueTypeKind.KNOWN


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

    fields: Mapping[str, RowField] = field(default_factory=lambda: _readonly_mapping())
    is_unknown: bool = False

    def __post_init__(self) -> None:
        """Copy row fields into an immutable mapping."""

        object.__setattr__(self, "fields", _readonly_mapping(self.fields))


@dataclass(frozen=True, slots=True)
class RelationshipSemanticEndpointInfo:
    """One relationship endpoint resolved to an existing relation definition."""

    local_name: str
    relation_name: str
    relation: SourceDef | TableDef | QueryDef


@dataclass(frozen=True, slots=True)
class RelationshipSemanticInfo:
    """One validated relationship preserving source-ordered endpoints."""

    name: str
    endpoints: tuple[
        RelationshipSemanticEndpointInfo,
        RelationshipSemanticEndpointInfo,
    ]


@dataclass(frozen=True, slots=True)
class SatisfyingResultPredicateInfo:
    """Validated result-predicate facts for one relation ``satisfying:`` clause."""

    clause: SatisfyingClause
    output_expressions: Mapping[str, Expression]
    expression_value_types: Mapping[Expression, ValueType]

    def __post_init__(self) -> None:
        """Copy satisfying predicate facts into immutable mappings."""

        object.__setattr__(
            self,
            "output_expressions",
            _readonly_mapping(self.output_expressions),
        )
        object.__setattr__(
            self,
            "expression_value_types",
            _readonly_mapping(self.expression_value_types),
        )


@dataclass(frozen=True, slots=True)
class SemanticModel:
    """Readonly semantic state built incrementally across Phase 2."""

    mode: CheckMode
    type_symbols: Mapping[str, Definition] = field(
        default_factory=lambda: _readonly_mapping()
    )
    callable_symbols: Mapping[str, Definition] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_symbols: Mapping[str, Definition] = field(
        default_factory=lambda: _readonly_mapping()
    )
    type_resolutions: Mapping[TypeExpr, ResolvedType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    type_expansions: Mapping[TypeExpr, ResolvedType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    type_nullability: Mapping[TypeExpr, EffectiveNullability] = field(
        default_factory=lambda: _readonly_mapping()
    )
    source_row_schemas: Mapping[SourceDef, RowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    from_resolutions: Mapping[
        FromClause,
        SourceDef | TableDef | QueryDef,
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    expression_value_types: Mapping[Expression, ValueType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    result_predicates: Mapping[
        TableDef | QueryDef,
        SatisfyingResultPredicateInfo,
    ] = field(default_factory=lambda: _readonly_mapping())
    relationships: tuple[RelationshipSemanticInfo, ...] = ()

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
            "type_expansions",
            _readonly_mapping(self.type_expansions),
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
        object.__setattr__(
            self,
            "expression_value_types",
            _readonly_mapping(self.expression_value_types),
        )
        object.__setattr__(
            self,
            "result_predicates",
            _readonly_mapping(self.result_predicates),
        )


@dataclass(frozen=True, slots=True)
class SemanticResult:
    """A semantic model and its ordered diagnostics."""

    model: SemanticModel
    diagnostics: tuple[Diagnostic, ...]
