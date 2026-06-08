from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Span:
    path: str | None
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    span: Span


@dataclass(frozen=True, slots=True, kw_only=True)
class Header(Node):
    version: str | None = None
    mode: str | None = None
    dialect: str | None = None
    encoding: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Expression(Node):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpr(Expression):
    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NameExpr(Expression):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DottedNameExpr(Expression):
    parts: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CallExpr(Expression):
    callee: NameExpr | DottedNameExpr
    arguments: tuple[Expression, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class UnaryExpr(Expression):
    operator: str
    operand: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BinaryExpr(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class ComparisonExpr(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BetweenExpr(Expression):
    value: Expression
    lower: Expression
    upper: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class IsNullExpr(Expression):
    value: Expression
    negated: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeArgument(Node):
    name: str | None
    value: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeExpr(Node):
    name: str
    arguments: tuple[TypeArgument, ...]
    nullable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EnsureClause(Node):
    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeDef(Node):
    name: str
    base: TypeExpr
    ensures: tuple[EnsureClause, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EnumDef(Node):
    name: str
    members: tuple[str, ...]


Definition = TypeDef | EnumDef


@dataclass(frozen=True, slots=True, kw_only=True)
class Script(Node):
    header: Header | None
    definitions: tuple[Definition, ...]
