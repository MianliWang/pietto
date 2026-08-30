"""Readonly public models produced by semantic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping, TypeVar

from pietto.ast_nodes import (
    Definition,
    Expression,
    FieldDef,
    FromClause,
    LetBinding,
    LetClause,
    Node,
    QueryDef,
    SatisfyingClause,
    SourceDef,
    TableDef,
    TypeExpr,
    WindowExpr,
    WindowUseKind,
)
from pietto.errors import Diagnostic

if TYPE_CHECKING:
    from pietto.semantic.window_semantics import (
        ResolvedNamedWindowNamespace,
        WindowExpressionAnalysis,
    )

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


@dataclass(frozen=True, slots=True)
class DecimalPrecisionScale:
    """Validated Decimal precision-scale facts for one type expression."""

    precision: int
    scale: int


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
class LetScopeSemanticInfo:
    """Validated relation-local let binding facts for later compiler stages."""

    clause: LetClause
    bindings: tuple[LetBinding, ...]
    value_types: Mapping[str, ValueType]

    def __post_init__(self) -> None:
        """Copy let binding facts into immutable containers."""

        object.__setattr__(self, "bindings", tuple(self.bindings))
        object.__setattr__(self, "value_types", _readonly_mapping(self.value_types))


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
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale] = field(
        default_factory=lambda: _readonly_mapping()
    )
    decimal_expression_precision_scales: Mapping[
        Expression,
        DecimalPrecisionScale,
    ] = field(default_factory=lambda: _readonly_mapping())
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
    window_expression_analyses: Mapping[
        WindowExpr,
        WindowExpressionAnalysis,
    ] = field(default_factory=lambda: _readonly_mapping())
    named_window_namespaces: Mapping[
        TableDef | QueryDef,
        ResolvedNamedWindowNamespace,
    ] = field(default_factory=lambda: _readonly_mapping())
    result_predicates: Mapping[
        TableDef | QueryDef,
        SatisfyingResultPredicateInfo,
    ] = field(default_factory=lambda: _readonly_mapping())
    let_scopes: Mapping[
        TableDef | QueryDef,
        LetScopeSemanticInfo,
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
            "decimal_precision_scales",
            _readonly_mapping(self.decimal_precision_scales),
        )
        object.__setattr__(
            self,
            "decimal_expression_precision_scales",
            _readonly_mapping(self.decimal_expression_precision_scales),
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
        from pietto.semantic.window_semantics import (
            ResolvedNamedWindowNamespace,
            WindowExpressionAnalysis,
        )

        window_analysis_items = tuple(self.window_expression_analyses.items())
        if any(
            type(expression) is not WindowExpr
            or type(analysis) is not WindowExpressionAnalysis
            for expression, analysis in window_analysis_items
        ):
            raise TypeError("window expression analyses must be exact")
        for expression, analysis in window_analysis_items:
            semantic_fact = analysis.semantic_fact
            semantic_expression = semantic_fact.expression
            if (
                semantic_fact.identity != expression.identity
                or semantic_fact.occurrence.span != expression.span
                or semantic_expression.call is not expression.call
                or semantic_expression.nth_direction is not expression.nth_direction
                or semantic_expression.null_treatment is not expression.null_treatment
            ):
                raise ValueError(
                    "window analysis mapping must retain its exact source use"
                )
            if analysis.authored_expression is not expression:
                raise ValueError(
                    "window analysis mapping must retain its exact authored key"
                )
            if expression.use_kind is WindowUseKind.INLINE:
                if semantic_expression is not expression:
                    raise ValueError(
                        "inline window analysis mapping must retain its exact key"
                    )
            else:
                authored = analysis.validated_specification.resolved.authored
                if (
                    authored.span != expression.span
                    or authored.partition_by is not expression.spec.partition_by
                    or authored.order_by is not expression.spec.order_by
                    or authored.frame is not expression.spec.frame
                ):
                    raise ValueError(
                        "named window analysis mapping must retain local authorship"
                    )
            if (
                self.expression_value_types.get(expression)
                is not semantic_fact.result.value_type
            ):
                raise ValueError(
                    "window analysis mapping must retain its exact result type"
                )
        object.__setattr__(
            self,
            "window_expression_analyses",
            _readonly_mapping(self.window_expression_analyses),
        )
        named_window_namespace_items = tuple(self.named_window_namespaces.items())
        if any(
            type(definition) not in {TableDef, QueryDef}
            or type(namespace) is not ResolvedNamedWindowNamespace
            or namespace.definition is not definition
            or not definition.named_windows
            for definition, namespace in named_window_namespace_items
        ):
            raise TypeError("named window namespaces must retain exact relation owners")
        for expression, analysis in window_analysis_items:
            named = analysis.resolved_named_use
            if named is not None and (
                self.named_window_namespaces.get(named.composed.namespace.definition)
                is not named.composed.namespace
            ):
                raise ValueError(
                    "named window analysis must share its exact persisted namespace"
                )
        object.__setattr__(
            self,
            "named_window_namespaces",
            _readonly_mapping(self.named_window_namespaces),
        )
        object.__setattr__(
            self,
            "result_predicates",
            _readonly_mapping(self.result_predicates),
        )
        object.__setattr__(self, "let_scopes", _readonly_mapping(self.let_scopes))

    def decimal_precision_scale_for(
        self,
        type_expr: TypeExpr,
    ) -> DecimalPrecisionScale | None:
        """Return validated Decimal precision-scale facts for a type expression."""

        return self.decimal_precision_scales.get(type_expr)

    def decimal_expression_precision_scale_for(
        self,
        expression: Expression,
    ) -> DecimalPrecisionScale | None:
        """Return private Decimal precision-scale facts for a safe expression."""

        return self.decimal_expression_precision_scales.get(expression)


@dataclass(frozen=True, slots=True)
class SemanticResult:
    """A semantic model and its ordered diagnostics."""

    model: SemanticModel
    diagnostics: tuple[Diagnostic, ...]
