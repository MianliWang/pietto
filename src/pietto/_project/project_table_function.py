"""Bounded native table functions: the one closed PostgreSQL ``generate_series``.

A table-function FROM input is its own zero-input relation. Its call, binding,
row schema, function identity and effects evidence are kept apart: the binding
names the rows inside the body that wrote it and is never looked up, the row
schema is the binding as one ``Int not null`` column, and the function identity
is the closed catalog entry below, fixed in SQL by schema-qualified emission and
explicit ``pg_catalog.int8`` casts. Its three arguments are fixed integer
literals, its step is never zero and its static row count is bounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.project_values import ProjectValuesColumn, fixed_literal
from pietto._project.model import ProjectRowSchema
from pietto.ast_nodes import NameExpr, Span, TableFunctionRelationDef
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

# D70.07: the static row bound of one generate_series call (the default max_rows).
GENERATE_SERIES_MAX_ROWS = 1_048_576
_INT_MIN = -(1 << 63)
_INT_MAX = (1 << 63) - 1

# Phase70 table-function diagnostics, kept together.
FUNCTION_NOT_ADMITTED = "PIE-S2373"
ARGUMENT_COUNT = "PIE-S2374"
NOT_A_FIXED_INTEGER = "PIE-S2375"
ZERO_STEP = "PIE-S2376"
ROW_BOUND = "PIE-S2377"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTableFunctionSignature:
    """One closed native table-function identity and its occurrence effects.

    ``identity`` is what qualified emission fixes in SQL; no runtime catalog
    check repeats it. Error behavior and evaluation count stay unknown: the
    evidence admits the table-function input and promotes nothing else.
    """

    name: str
    family: str
    identity: str
    argument_type: str
    arity: int
    # Values of the ProjectIR*Evidence axes (project_ir_properties), by value so
    # that semantic facts never import the IR layer.
    determinism: str
    side_effects: str
    error_behavior: str
    evaluation_count: str

    @property
    def admitted(self) -> bool:
        """Admission consumes explicit determinism and side-effect evidence."""

        return (
            self.determinism == "deterministic"
            and self.side_effects == "side_effect_free"
        )


GENERATE_SERIES = ProjectTableFunctionSignature(
    name="generate_series",
    family="postgres",
    identity="pg_catalog.generate_series(pg_catalog.int8,pg_catalog.int8,pg_catalog.int8)",
    argument_type="pg_catalog.int8",
    arity=3,
    determinism="deterministic",
    side_effects="side_effect_free",
    error_behavior="unknown",
    evaluation_count="unknown",
)
# The closed catalog: one function, one overload, no search.
CATALOG: dict[str, ProjectTableFunctionSignature] = {"generate_series": GENERATE_SERIES}


def series_row_count(start: int, stop: int, step: int) -> int:
    """Exact rows of ``generate_series(start, stop, step)``; ``step`` is nonzero."""

    if step == 0:
        raise ValueError("generate_series step must be nonzero")
    if (step > 0 and start > stop) or (step < 0 and start < stop):
        return 0
    return abs(stop - start) // abs(step) + 1


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectTableFunctionRelation:
    """The independent static facts of one table-function FROM input.

    It is complete only without diagnostics: then ``signature`` is the closed
    catalog entry, ``arguments`` are its three int64 values and ``row_count``
    is within the D70.07 bound.
    """

    definition: TableFunctionRelationDef = field(repr=False)
    signature: ProjectTableFunctionSignature | None = field(init=False)
    arguments: tuple[int, ...] = field(init=False)
    row_count: int = field(init=False)
    columns: tuple[ProjectValuesColumn, ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    schema: ProjectRowSchema | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.definition) is not TableFunctionRelationDef:
            raise TypeError("Table-function semantics require an exact FROM input.")
        signature, arguments, rows, diagnostics = _analyze(self.definition)
        columns = (
            ProjectValuesColumn(
                position=0,
                name=self.definition.name,
                logical_type="Int",
                nullable=False,
            ),
        )
        object.__setattr__(self, "signature", None if diagnostics else signature)
        object.__setattr__(self, "arguments", () if diagnostics else arguments)
        object.__setattr__(self, "row_count", 0 if diagnostics else rows)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "diagnostics", diagnostics)
        object.__setattr__(
            self,
            "schema",
            None
            if diagnostics
            else ProjectRowSchema(fields={c.name: c.field for c in columns}),
        )


def table_function_diagnostics(
    definition: TableFunctionRelationDef,
) -> tuple[Diagnostic, ...]:
    """Return the deterministic source-ordered diagnostics of one call."""

    return ProjectTableFunctionRelation(definition=definition).diagnostics


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


def _analyze(
    definition: TableFunctionRelationDef,
) -> tuple[
    ProjectTableFunctionSignature | None,
    tuple[int, ...],
    int,
    tuple[Diagnostic, ...],
]:
    call = definition.source.call
    callee = call.callee
    signature = CATALOG.get(callee.name) if type(callee) is NameExpr else None
    if signature is None or not signature.admitted:
        return (
            None,
            (),
            0,
            (
                _diagnostic(
                    callee.span,
                    FUNCTION_NOT_ADMITTED,
                    "Only generate_series(Int, Int, Int) is an admitted table "
                    "function.",
                ),
            ),
        )
    if len(call.arguments) != signature.arity:
        return (
            None,
            (),
            0,
            (
                _diagnostic(
                    call.span,
                    ARGUMENT_COUNT,
                    f"generate_series takes exactly 3 arguments, not "
                    f"{len(call.arguments)}.",
                ),
            ),
        )
    diagnostics: list[Diagnostic] = []
    values: list[int] = []
    for argument in call.arguments:
        fixed, value = fixed_literal(argument)
        if not fixed or type(value) is not int or not _INT_MIN <= value <= _INT_MAX:
            diagnostics.append(
                _diagnostic(
                    argument.span,
                    NOT_A_FIXED_INTEGER,
                    "generate_series arguments are fixed non-null Int literals "
                    "within the signed 64-bit range, not parameters or expressions.",
                )
            )
            continue
        values.append(value)
    if diagnostics:
        return None, (), 0, tuple(diagnostics)
    start, stop, step = values
    if step == 0:
        return (
            None,
            (),
            0,
            (
                _diagnostic(
                    call.arguments[2].span,
                    ZERO_STEP,
                    "generate_series step cannot be zero.",
                ),
            ),
        )
    rows = series_row_count(start, stop, step)
    if rows > GENERATE_SERIES_MAX_ROWS:
        return (
            None,
            (),
            0,
            (
                _diagnostic(
                    call.span,
                    ROW_BOUND,
                    f"generate_series produces {rows} rows; at most "
                    f"{GENERATE_SERIES_MAX_ROWS} are allowed.",
                ),
            ),
        )
    return signature, (start, stop, step), rows, ()
