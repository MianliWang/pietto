"""Typed VALUES relation semantics: header schema, fixed literal cells, limits."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto.ast_nodes import (
    Expression,
    LiteralExpr,
    Nullability,
    Span,
    UnaryExpr,
    ValuesRelationDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

# D70.07 static bounds of one VALUES relation.
VALUES_MAX_ROWS = 1_000
VALUES_MAX_COLUMNS = 64
# One closed VALUES header type set; a cell is one fixed literal of its column.
_LITERAL_TYPES: dict[str, type] = {
    "Bool": bool,
    "Int": int,
    "Float": float,
    "Text": str,
}
_INT_MIN = -(1 << 63)
_INT_MAX = (1 << 63) - 1

# Phase70 VALUES diagnostics, kept together.
DUPLICATE_COLUMN = "PIE-S2001"
INVALID_COLUMN = "PIE-S2361"
ROW_WIDTH = "PIE-S2362"
NOT_A_LITERAL = "PIE-S2363"
CELL_TYPE = "PIE-S2364"
LIMIT_EXCEEDED = "PIE-S2365"

type ProjectValuesLiteral = bool | int | float | str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValuesColumn:
    """One admitted VALUES header column: a built-in type and explicit nullability."""

    position: int
    name: str
    logical_type: str
    nullable: bool
    field: ProjectRowField = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.position) is not int
            or self.position < 0
            or type(self.name) is not str
            or not self.name
            or self.logical_type not in _LITERAL_TYPES
            or type(self.nullable) is not bool
        ):
            raise ValueError("VALUES column requires an admitted typed header.")
        object.__setattr__(
            self,
            "field",
            ProjectRowField(
                name=self.name,
                resolved_type=ProjectResolvedType(
                    name=self.logical_type, kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=(
                    ProjectRowFieldNullability.NULLABLE
                    if self.nullable
                    else ProjectRowFieldNullability.NON_NULL
                ),
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectValuesRelation:
    """The independent typed row schema and fixed rows of one VALUES body.

    It is complete only without diagnostics: then every row has one fixed
    literal per column, of the column's type and nullability, within D70.07.
    """

    definition: ValuesRelationDef = field(repr=False)
    columns: tuple[ProjectValuesColumn, ...] = field(init=False)
    rows: tuple[tuple[ProjectValuesLiteral, ...], ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    schema: ProjectRowSchema | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.definition) is not ValuesRelationDef:
            raise TypeError("VALUES semantics require an exact VALUES relation.")
        columns, rows, diagnostics = _analyze(self.definition)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "diagnostics", diagnostics)
        object.__setattr__(
            self,
            "schema",
            None
            if diagnostics
            else ProjectRowSchema(fields={c.name: c.field for c in columns}),
        )


def values_diagnostics(definition: ValuesRelationDef) -> tuple[Diagnostic, ...]:
    """Return the deterministic source-ordered diagnostics of one VALUES body."""

    return ProjectValuesRelation(definition=definition).diagnostics


def _diagnostic(span: Span, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
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


def fixed_literal(expression: Expression) -> tuple[bool, ProjectValuesLiteral]:
    """Fold one authored cell: a literal, or a sign directly on a number literal."""

    if type(expression) is LiteralExpr:
        return True, expression.value
    if (
        type(expression) is UnaryExpr
        and expression.operator in {"-", "+"}
        and type(expression.operand) is LiteralExpr
    ):
        value = expression.operand.value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True, -value if expression.operator == "-" else value
    return False, None


def _cell_matches(value: ProjectValuesLiteral, column: ProjectValuesColumn) -> bool:
    if value is None:
        return column.nullable
    if type(value) is not _LITERAL_TYPES[column.logical_type]:
        return False
    if type(value) is int:
        return _INT_MIN <= value <= _INT_MAX
    if type(value) is float:
        return math.isfinite(value)
    return True


def _analyze(
    definition: ValuesRelationDef,
) -> tuple[
    tuple[ProjectValuesColumn, ...],
    tuple[tuple[ProjectValuesLiteral, ...], ...],
    tuple[Diagnostic, ...],
]:
    body = definition.body
    diagnostics: list[Diagnostic] = []
    if len(body.columns) > VALUES_MAX_COLUMNS or len(body.rows) > VALUES_MAX_ROWS:
        diagnostics.append(
            _diagnostic(
                body.span,
                LIMIT_EXCEEDED,
                f"VALUES allows at most {VALUES_MAX_ROWS} rows and "
                f"{VALUES_MAX_COLUMNS} columns.",
            )
        )
    columns: list[ProjectValuesColumn | None] = []
    seen: set[str] = set()
    for position, column in enumerate(body.columns):
        declared = column.type
        if column.name in seen:
            diagnostics.append(
                _diagnostic(
                    column.span,
                    DUPLICATE_COLUMN,
                    f"Duplicate VALUES column name '{column.name}'.",
                )
            )
        seen.add(column.name)
        if declared.name not in _LITERAL_TYPES or declared.arguments:
            diagnostics.append(
                _diagnostic(
                    declared.span,
                    INVALID_COLUMN,
                    "VALUES column type must be Bool, Int, Float or Text, "
                    "optionally followed by '| None'.",
                )
            )
            columns.append(None)
            continue
        columns.append(
            ProjectValuesColumn(
                position=position,
                name=column.name,
                logical_type=declared.name,
                nullable=declared.nullability is Nullability.NULLABLE,
            )
        )
    rows: list[tuple[ProjectValuesLiteral, ...]] = []
    for row in body.rows:
        if len(row.values) != len(columns):
            diagnostics.append(
                _diagnostic(
                    row.span,
                    ROW_WIDTH,
                    f"VALUES row has {len(row.values)} values for "
                    f"{len(columns)} columns.",
                )
            )
            continue
        values: list[ProjectValuesLiteral] = []
        for cell, column in zip(row.values, columns, strict=True):
            fixed, value = fixed_literal(cell)
            if not fixed:
                diagnostics.append(
                    _diagnostic(
                        cell.span,
                        NOT_A_LITERAL,
                        "VALUES cells accept fixed literals only, not parameters "
                        "or expressions.",
                    )
                )
            elif column is not None and not _cell_matches(value, column):
                diagnostics.append(
                    _diagnostic(
                        cell.span,
                        CELL_TYPE,
                        f"VALUES cell does not match column '{column.name}' "
                        f"declared {column.logical_type}"
                        f"{' | None' if column.nullable else ''}.",
                    )
                )
            values.append(value)
        rows.append(tuple(values))
    complete = tuple(column for column in columns if column is not None)
    if diagnostics:
        return complete, (), tuple(diagnostics)
    return complete, tuple(rows), ()
