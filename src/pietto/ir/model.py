"""Immutable public models for Pietto Semantic IR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto.errors import Diagnostic

StaticValue = str | int | float | bool | None


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
class FieldId:
    """A stable field identity within an optional owning semantic symbol."""

    owner: SymbolId | None
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
class ExpressionIR:
    """Base class for typed, source-located Semantic IR expressions."""

    span: SourceSpan
    value_type: TypeRefIR


@dataclass(frozen=True, slots=True)
class LiteralIR(ExpressionIR):
    """A lowered scalar literal."""

    value: StaticValue


@dataclass(frozen=True, slots=True)
class FieldRefIR(ExpressionIR):
    """A lowered bare or dotted field reference."""

    name: str
    qualifier: tuple[str, ...]
    field: FieldId | None


@dataclass(frozen=True, slots=True)
class CallIR(ExpressionIR):
    """A lowered static call expression without execution behavior."""

    callee: str
    callee_symbol: SymbolId | None
    arguments: tuple[ExpressionIR, ...]


@dataclass(frozen=True, slots=True)
class UnaryIR(ExpressionIR):
    """A lowered unary expression."""

    operator: str
    operand: ExpressionIR


@dataclass(frozen=True, slots=True)
class BinaryIR(ExpressionIR):
    """A lowered binary arithmetic or Boolean expression."""

    left: ExpressionIR
    operator: str
    right: ExpressionIR


@dataclass(frozen=True, slots=True)
class ComparisonIR(ExpressionIR):
    """A lowered comparison expression."""

    left: ExpressionIR
    operator: str
    right: ExpressionIR


@dataclass(frozen=True, slots=True)
class BetweenIR(ExpressionIR):
    """A lowered inclusive between expression."""

    value: ExpressionIR
    lower: ExpressionIR
    upper: ExpressionIR


@dataclass(frozen=True, slots=True)
class IsNullIR(ExpressionIR):
    """A lowered is-null predicate, optionally negated."""

    value: ExpressionIR
    negated: bool


@dataclass(frozen=True, slots=True)
class ExpressionLoweringResult:
    """A lowered expression and its ordered IR diagnostics."""

    expression: ExpressionIR | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class DefinitionIR:
    """Marker base for definition IR nodes added by later lowering slices."""


@dataclass(frozen=True, slots=True)
class TypeIR(DefinitionIR):
    """A lowered type alias with declared and canonical targets."""

    symbol: SymbolId
    name: str
    declared_type: TypeRefIR
    canonical_type: TypeRefIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class EnumIR(DefinitionIR):
    """A lowered enum preserving member source order."""

    symbol: SymbolId
    name: str
    members: tuple[str, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeFieldIR:
    """A lowered shape field with resolved type metadata."""

    name: str
    type_ref: TypeRefIR
    nullability: NullabilityIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeIR(DefinitionIR):
    """A lowered shape containing ordered field metadata."""

    symbol: SymbolId
    name: str
    fields: tuple[ShapeFieldIR, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ParameterIR:
    """A lowered callable parameter with resolved type metadata."""

    name: str
    type_ref: TypeRefIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ConstraintIR(DefinitionIR):
    """A lowered top-level constraint declaration."""

    symbol: SymbolId
    name: str
    parameters: tuple[ParameterIR, ...]
    return_type: TypeRefIR
    body: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class DeriveIR(DefinitionIR):
    """A lowered top-level derive declaration."""

    symbol: SymbolId
    name: str
    parameters: tuple[ParameterIR, ...]
    return_type: TypeRefIR
    body: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ConnectorIR:
    """Static source connector metadata without runtime behavior."""

    name: str
    arguments: tuple[StaticValue, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceIR(DefinitionIR):
    """A lowered source declaration with static connector and row metadata."""

    symbol: SymbolId
    name: str
    shape_symbol: SymbolId | None
    row_schema: RowSchemaIR
    connector: ConnectorIR
    span: SourceSpan


class RelationKindIR(StrEnum):
    """Kinds of derived relations supported by the minimal IR."""

    TABLE = "table"
    QUERY = "query"


@dataclass(frozen=True, slots=True)
class RelationSourceIR:
    """A resolved input relation reference."""

    target: SymbolId
    name: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class FilterIR:
    """A lowered relation filter."""

    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ProjectionIR:
    """An ordered relation projection and its stable output metadata."""

    name: str | None
    expression: ExpressionIR
    type_ref: TypeRefIR | None
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class RelationIR(DefinitionIR):
    """A minimal lowered table or query relation."""

    symbol: SymbolId
    name: str
    kind: RelationKindIR
    source: RelationSourceIR
    filter: FilterIR | None
    projections: tuple[ProjectionIR, ...]
    row_schema: RowSchemaIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ScriptIR:
    """Top-level Semantic IR container preserving definition order."""

    definitions: tuple[DefinitionIR, ...]


@dataclass(frozen=True, slots=True)
class IrResult:
    """A Semantic IR result and its ordered lowering diagnostics."""

    ir: ScriptIR | None
    diagnostics: tuple[Diagnostic, ...]
