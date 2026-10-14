"""Typed VALUES bodies: a zero-input producer with its own declared columns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto._project.project_final_outputs import ProjectCompletedValuesOutputField
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedValuesOutput,
    ProjectIRQueryBlockResultProperties,
)
from pietto._project.project_values import (
    ProjectValuesColumn,
    ProjectValuesLiteral,
    ProjectValuesRelation,
)
from pietto.ast_nodes import ValuesRelationDef

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import ProjectSQLPlanRef

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLValuesBody:
    """One VALUES definition: no input use, fixed typed rows, one output per column."""

    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    source: ProjectIRCompletedValuesOutput
    relation: ProjectValuesRelation
    columns: tuple[ProjectSQLPlanRef, ...]
    outputs: tuple[ProjectSQLPlanRef, ...]
    rows: tuple[tuple[ProjectValuesLiteral, ...], ...]
    properties: ProjectIRQueryBlockResultProperties


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLValuesColumn:
    """One declared column; every cell of it is written with this type."""

    ref: ProjectSQLPlanRef
    body: ProjectSQLPlanRef
    position: int
    source: ProjectValuesColumn
    semantic: ProjectCompletedValuesOutputField
    field: ProjectIROutputFieldOccurrence
    output: ProjectSQLPlanRef


type Witness = ProjectSQLValuesBody | ProjectSQLValuesColumn


class ProjectSQLValuesDemandKind(StrEnum):
    ROWS = "values_fixed_rows_within_static_bounds"
    COLUMN = "values_declared_column_type_and_nullability"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLValuesDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLValuesDemandKind
    witness: Witness
    origin: ProjectSQLPlanRef


def build_body(definition, ref, port):
    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind as K
    from pietto._project.project_sql_plan_results import ProjectSQLResultPortRole

    entry = definition.entry
    assert isinstance(entry, ProjectIRCompletedValuesOutput)
    semantic = entry.semantic_entry
    relation = semantic.root
    if (
        not isinstance(relation.definition, ValuesRelationDef)
        or relation.definition is not entry.owner.definition
        or relation.diagnostics
    ):
        raise ValueError("VALUES body lost its authored typed relation")
    body_ref = ref(K.VALUES_BODY)
    columns, outputs = [], []
    for i, (source, field, canonical) in enumerate(
        zip(relation.columns, semantic.fields, definition.exports, strict=True)
    ):
        column_ref = ref(K.VALUES_COLUMN)
        output = port(
            definition.ref,
            body_ref,
            ProjectSQLResultPortRole.OUTPUT,
            i,
            column_ref,
            canonical,
            field,
            field.field,
        )
        columns.append(
            ProjectSQLValuesColumn(
                ref=column_ref,
                body=body_ref,
                position=i,
                source=source,
                semantic=field,
                field=canonical.field,
                output=output.ref,
            )
        )
        outputs.append(output)
    body = ProjectSQLValuesBody(
        ref=body_ref,
        definition=definition.ref,
        source=entry,
        relation=relation,
        columns=tuple(column.ref for column in columns),
        outputs=tuple(output.ref for output in outputs),
        rows=relation.rows,
        properties=entry.active_properties,
    )
    return body, columns, outputs


def origin_parts(witness, bodies):
    """Read the authored VALUES body and column; no allocation or analysis."""
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    D = ProjectSQLValuesDemandKind
    if isinstance(witness, ProjectSQLValuesBody):
        return (
            witness.definition,
            witness.relation.definition.body,
            witness.columns + witness.outputs,
            P.GENERATED_STRUCTURE,
            (D.ROWS,),
        )
    if isinstance(witness, ProjectSQLValuesColumn):
        body = bodies[witness.body]
        return (
            body.definition,
            body.relation.definition.body.columns[witness.position],
            (witness.body, witness.output),
            P.TYPE_PROOF,
            (D.COLUMN,),
        )
    raise TypeError("VALUES origin requires an exact VALUES witness")
