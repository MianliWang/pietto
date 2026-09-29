"""Exact public outputs of a verified complete emission, without source fiction.

The emission verifier independently checks expression, use, terminal and target
realization laws. This view retains those actual nodes; it is not another
semantic evaluator. Verification never calls the view's constructor.
"""

from dataclasses import dataclass, field as dc_field
from typing import Any

from pietto._project.project_result_contract import (
    ResultError,
    build_result_contract,
    verify_result_contract,
)
from pietto._project.project_sql_emission_ast import (
    SQLColumn,
    SQLLiteralColumn,
    SQLSelect,
    SQLRowQuery,
    SQLJoinQuery,
    RowValueColumn,
    RowCarryColumn,
)
from pietto._project.project_sql_emission_aggregation import AggregateProjectionColumn
from pietto._project.project_sql_emission_windows import WindowProjectionColumn
from pietto._project.project_sql_emission_results import ResultColumn
from pietto._project.project_sql_emission_sets import SetColumn
from pietto._project.project_sql_emission_rows import (
    Realization,
    field_realization,
    constant_realization,
)
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class OutputColumn:
    original: Any = dc_field(repr=False)
    field: Any = dc_field(repr=False)
    ordinal: int
    label: str
    export: Any = dc_field(repr=False)
    terminal: Any = dc_field(repr=False)
    realization: Realization = dc_field(repr=False)
    source_field: Any = dc_field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class GeneralOutput:
    artifact: Any = dc_field(repr=False)
    contract: Any = dc_field(repr=False)
    binding: Any = dc_field(repr=False)
    units: tuple[Any, ...] = dc_field(repr=False)
    columns: tuple[OutputColumn, ...] = dc_field(repr=False)


def prepare_output(artifact, *, binding=None):
    view = inspect_project_sql_emission(artifact, artifact.request)
    contract = build_result_contract(
        view.request.verification, scalar_meaning=view.request.scalar_meaning
    )
    ast = artifact.ast
    if type(ast) is SQLSelect:
        units = tuple(c.body for c in ast.ctes) + (ast,)
    elif type(ast) is SQLRowQuery:
        units = ast.bodies
    elif type(ast) is SQLJoinQuery:
        units = ast.units
    else:
        raise ResultError("OUTPUT_ROOT")
    columns = []
    for original, leaf in zip(view.columns, contract.shape.fields, strict=True):
        if type(original) is SQLColumn:
            source = original.source_field
            realized = field_realization(source)
        elif type(original) is SQLLiteralColumn:
            # A named literal reads its retained producer's actual value.
            value = original.value
            if value is None:
                value = original.origin.value
            realized = constant_realization(value, view.request.family)
            source = None
        else:
            realized = original.column.realization
            source = original.column.field
        if realized is None:
            raise ResultError("OUTPUT_REALIZATION")
        columns.append(
            OutputColumn(
                original,
                leaf,
                original.ordinal,
                original.label,
                original.export,
                units[-1],
                realized,
                source,
            )
        )
    output = GeneralOutput(artifact, contract, binding, units, tuple(columns))
    verify_output(output, artifact, contract, binding=binding)
    return output


def verify_output(output, artifact, contract, *, binding=None):
    if (
        type(output) is not GeneralOutput
        or output.artifact is not artifact
        or output.contract is not contract
        or output.binding is not binding
    ):
        raise ResultError("OUTPUT_ROOT")
    if binding is not None:
        from pietto._project.project_execution_binding_verification import (
            verify_binding,
        )

        verify_binding(binding)
        if binding.artifact is not artifact:
            raise ResultError("OUTPUT_BINDING")
    # This upstream verifier independently re-derives all concrete realizations,
    # including hidden computations and both complete SEMI/ANTI input terminals.
    view = inspect_project_sql_emission(artifact, artifact.request)
    verify_result_contract(contract, view.request.verification)
    if contract.scalar_meaning is not view.request.scalar_meaning:
        raise ResultError("OUTPUT_MEANING")
    ast = artifact.ast
    if type(ast) is SQLSelect:
        expected_units = tuple(c.body for c in ast.ctes) + (ast,)
    elif type(ast) is SQLRowQuery:
        expected_units = ast.bodies
    elif type(ast) is SQLJoinQuery:
        expected_units = ast.units
    else:
        raise ResultError("OUTPUT_TERMINAL")
    if (
        type(output.units) is not tuple
        or len(output.units) != len(expected_units)
        or any(a is not b for a, b in zip(output.units, expected_units, strict=True))
        or type(output.columns) is not tuple
        or len(output.columns) != len(contract.shape.fields)
        or len(view.columns) != len(output.columns)
    ):
        raise ResultError("OUTPUT_INVENTORY")
    for ordinal, (supplied, original, leaf) in enumerate(
        zip(output.columns, view.columns, contract.shape.fields, strict=True)
    ):
        if (
            type(supplied) is not OutputColumn
            or supplied.original is not original
            or supplied.field is not leaf
            or supplied.export is not leaf.port
            or original.export is not leaf.port
            or type(supplied.ordinal) is not int
            or supplied.ordinal != ordinal
            or original.ordinal != ordinal
            or type(supplied.label) is not str
            or supplied.label != leaf.label
            or original.label != leaf.label
            or supplied.terminal is not expected_units[-1]
        ):
            raise ResultError("OUTPUT_COLUMNS")
        if type(original) is SQLColumn:
            expected = field_realization(original.source_field)
            source = original.source_field
        elif type(original) is SQLLiteralColumn:
            value = (
                original.value if original.value is not None else original.origin.value
            )
            expected = constant_realization(value, view.request.family)
            source = None
        elif type(original) in (
            RowValueColumn,
            RowCarryColumn,
            AggregateProjectionColumn,
            WindowProjectionColumn,
            ResultColumn,
            SetColumn,
        ):
            expected = original.column.realization
            source = original.column.field
            if supplied.realization is not expected:
                raise ResultError("OUTPUT_REALIZATION")
        else:
            raise ResultError("OUTPUT_COLUMNS")
        real = supplied.realization
        if (
            type(real) is not Realization
            or expected is None
            or real.tag != expected.tag
            or real.storage != expected.storage
            or real.domain != expected.domain
            or type(real.nullable) is not type(expected.nullable)
            or real.nullable != expected.nullable
            or supplied.source_field is not source
        ):
            raise ResultError("OUTPUT_REALIZATION")
    return output.columns
