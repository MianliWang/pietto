"""ANTLR-independent abstract syntax tree nodes for Pietto source."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class Span:
    """A 1-based, half-open source range: [line:column, end_line:end_column)."""

    path: str | None
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    """Base class for source-located Pietto AST nodes."""

    span: Span


@dataclass(frozen=True, slots=True, kw_only=True)
class Header(Node):
    """Optional file-level language and backend settings."""

    version: str | None = None
    mode: str | None = None
    dialect: str | None = None
    encoding: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Expression(Node):
    """Base class for parsed expressions without semantic typing."""

    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpr(Expression):
    """A scalar literal expression."""

    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NameExpr(Expression):
    """A reference to one identifier."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DottedNameExpr(Expression):
    """A qualified identifier reference such as ``user.email``."""

    parts: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CallExpr(Expression):
    """A call whose callee is a name or dotted name."""

    callee: NameExpr | DottedNameExpr
    arguments: tuple[Expression, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class UnaryExpr(Expression):
    """A prefix arithmetic expression."""

    operator: str
    operand: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BinaryExpr(Expression):
    """A binary arithmetic or Boolean expression."""

    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class ComparisonExpr(Expression):
    """A comparison between two expressions."""

    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BetweenExpr(Expression):
    """An inclusive ``between`` comparison."""

    value: Expression
    lower: Expression
    upper: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class IsNullExpr(Expression):
    """An ``is null`` or ``is not null`` predicate."""

    value: Expression
    negated: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeArgument(Node):
    """A positional or named argument in a type expression."""

    name: str | None
    value: Expression


class Nullability(StrEnum):
    """Explicit syntax state recorded for a parsed type expression."""

    IMPLICIT = "implicit"
    NULLABLE = "nullable"
    NOT_NULL = "not_null"


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeExpr(Node):
    """A parsed type reference with arguments and three-state nullability."""

    name: str
    arguments: tuple[TypeArgument, ...]
    nullability: Nullability


@dataclass(frozen=True, slots=True, kw_only=True)
class Parameter(Node):
    """A named parameter with its declared type."""

    name: str
    type: TypeExpr


@dataclass(frozen=True, slots=True, kw_only=True)
class EnsureClause(Node):
    """A parsed value guarantee attached to a type or field."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class Annotation(Node):
    """A parse-only bare annotation attached to a declaration."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeDef(Node):
    """A named type definition and its parsed guarantees."""

    name: str
    base: TypeExpr
    ensures: tuple[EnsureClause, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EnumDef(Node):
    """A named enumeration definition."""

    name: str
    members: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldDef(Node):
    """A parse-only shape field with an optional derived value expression."""

    name: str
    type_expr: TypeExpr
    derive_expression: Expression | None
    annotations: tuple[Annotation, ...]
    ensure_clauses: tuple[EnsureClause, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckDef(Node):
    """A named, parse-only shape invariant containing one expression."""

    name: str
    expression: Expression


ShapeItem = FieldDef | CheckDef


@dataclass(frozen=True, slots=True, kw_only=True)
class ShapeDef(Node):
    """A parse-only shape definition containing source-ordered items."""

    name: str
    items: tuple[ShapeItem, ...]

    @property
    def fields(self) -> tuple[FieldDef, ...]:
        """Return fields in source order for compatibility and convenience."""

        return tuple(item for item in self.items if isinstance(item, FieldDef))

    @property
    def checks(self) -> tuple[CheckDef, ...]:
        """Return shape checks in source order."""

        return tuple(item for item in self.items if isinstance(item, CheckDef))


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstraintDef(Node):
    """A parse-only constraint whose return type remains a syntax-level TypeExpr."""

    name: str
    parameters: tuple[Parameter, ...]
    return_type: TypeExpr
    body: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class DeriveDef(Node):
    """A parse-only derive whose return type remains a syntax-level TypeExpr."""

    name: str
    parameters: tuple[Parameter, ...]
    return_type: TypeExpr
    body: Expression


Definition = TypeDef | EnumDef | ConstraintDef | DeriveDef | ShapeDef


@dataclass(frozen=True, slots=True, kw_only=True)
class Script(Node):
    """The root node for one parsed Pietto source file."""

    header: Header | None
    definitions: tuple[Definition, ...]
