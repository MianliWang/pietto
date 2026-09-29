"""Narrow unchanged-source correspondence through a verified row query."""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission_ast import (
    SQLRowQuery,
    RowBody,
    RowScan,
    RowStageUse,
    RowNamedUse,
    RowCarryColumn,
    RowValueColumn,
)
from pietto._project.project_sql_emission_results import (
    RowResultBody,
    RowResultUse,
    ResultColumn,
)
from pietto._project.project_sql_emission_rows import SQLStageReference
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionSourceColumn:
    original: Any = field(repr=False)
    ordinal: int
    export: Any = field(repr=False)
    label: str
    source_field: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionProjection:
    artifact: Any = field(repr=False)
    columns: tuple[ExecutionSourceColumn, ...] = field(repr=False)


def _direct_columns(artifact):
    view = inspect_project_sql_emission(artifact, artifact.request)
    if type(artifact.ast) is not SQLRowQuery:
        raise ResultError("EXECUTION_PROJECTION_SHAPE")
    source_fields = tuple(f for s in view.request.sources for f in s.fields)
    previous = []
    for body in artifact.ast.bodies:
        if (
            type(body) not in (RowBody, RowResultBody)
            or body.aggregation is not None
            or body.window is not None
            or (type(body) is RowResultBody and body.distinct is not None)
        ):
            raise ResultError("EXECUTION_PROJECTION_SHAPE")
        if type(body.scan) is RowScan:
            if not any(body.scan.realization is s for s in view.request.sources):
                raise ResultError("EXECUTION_PROJECTION_SOURCE")
        elif type(body.scan) in (RowStageUse, RowNamedUse, RowResultUse):
            if not any(body.scan.body is b for b in previous):
                raise ResultError("EXECUTION_PROJECTION_STAGE")
        else:
            raise ResultError("EXECUTION_PROJECTION_SHAPE")
        for column in body.columns:
            if type(column) is RowValueColumn:
                if type(column.value) is not SQLStageReference:
                    raise ResultError("EXECUTION_PROJECTION_COMPUTED")
                read = column.value.column
            elif type(column) in (RowCarryColumn, ResultColumn):
                read = column.read
            else:
                raise ResultError("EXECUTION_PROJECTION_SHAPE")
            stage = column.column
            if (
                stage.field is None
                or read.field is not stage.field
                or not any(stage.field is f for f in source_fields)
                or stage.source_port is not read.source_port
                or any(
                    v is not None
                    for v in (stage.literal, stage.aggregate, stage.window)
                )
            ):
                raise ResultError("EXECUTION_PROJECTION_LINEAGE")
        previous.append(body)
    if not previous or not previous[-1].final:
        raise ResultError("EXECUTION_PROJECTION_TERMINAL")
    return view.columns


def prepare_projection(artifact):
    columns = _direct_columns(artifact)
    result = ExecutionProjection(
        artifact,
        tuple(
            ExecutionSourceColumn(c, c.ordinal, c.export, c.label, c.column.field)
            for c in columns
        ),
    )
    verify_projection(result, artifact)
    return result


def verify_projection(projection, artifact):
    columns = _direct_columns(artifact)
    if (
        type(projection) is not ExecutionProjection
        or projection.artifact is not artifact
        or type(projection.columns) is not tuple
        or len(projection.columns) != len(columns)
    ):
        raise ResultError("EXECUTION_PROJECTION_ROOT")
    for supplied, column in zip(projection.columns, columns, strict=True):
        if (
            type(supplied) is not ExecutionSourceColumn
            or supplied.original is not column
            or supplied.export is not column.export
            or type(supplied.ordinal) is not int
            or supplied.ordinal != column.ordinal
            or supplied.label != column.label
            or supplied.source_field is not column.column.field
        ):
            raise ResultError("EXECUTION_PROJECTION_COLUMNS")
    return projection.columns
