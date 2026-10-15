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
from pietto._project.project_table_function import ProjectTableFunctionRelation
from pietto._project.project_values import (
    ProjectValuesColumn,
    ProjectValuesLiteral,
    ProjectValuesRelation,
)
from pietto.ast_nodes import TableFunctionRelationDef, ValuesBody, ValuesRelationDef

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import ProjectSQLPlanRef

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLValuesBody:
    """One zero-input definition: no input use, one output per column.

    A VALUES body has fixed typed ``rows``. A table-function body has none: it
    names its closed ``function`` identity, its three fixed ``arguments`` and
    its static ``row_count``.
    """

    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    source: ProjectIRCompletedValuesOutput
    relation: ProjectValuesRelation | ProjectTableFunctionRelation
    columns: tuple[ProjectSQLPlanRef, ...]
    outputs: tuple[ProjectSQLPlanRef, ...]
    rows: tuple[tuple[ProjectValuesLiteral, ...], ...]
    properties: ProjectIRQueryBlockResultProperties
    function: str | None = None
    arguments: tuple[int, ...] = ()
    row_count: int | None = None


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
        not isinstance(
            relation.definition, (ValuesRelationDef, TableFunctionRelationDef)
        )
        or relation.definition is not entry.owner.definition
        or relation.diagnostics
    ):
        raise ValueError("VALUES body lost its authored typed relation")
    function, arguments, row_count = None, (), None
    if isinstance(relation, ProjectTableFunctionRelation):
        assert relation.signature is not None
        function = relation.signature.identity
        arguments, row_count = relation.arguments, relation.row_count
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
        rows=relation.rows if isinstance(relation, ProjectValuesRelation) else (),
        properties=entry.active_properties,
        function=function,
        arguments=arguments,
        row_count=row_count,
    )
    return body, columns, outputs


def authored_cause(relation: ProjectValuesRelation | ProjectTableFunctionRelation):
    """The authored node a zero-input body's structure and columns answer to."""

    definition = relation.definition
    return (
        definition.body
        if isinstance(definition, ValuesRelationDef)
        else definition.source
    )


def origin_parts(witness, bodies):
    """Read the authored VALUES body and column; no allocation or analysis."""
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    D = ProjectSQLValuesDemandKind
    if isinstance(witness, ProjectSQLValuesBody):
        return (
            witness.definition,
            authored_cause(witness.relation),
            witness.columns + witness.outputs,
            P.GENERATED_STRUCTURE,
            (D.ROWS,),
        )
    if isinstance(witness, ProjectSQLValuesColumn):
        body = bodies[witness.body]
        cause = authored_cause(body.relation)
        return (
            body.definition,
            cause.columns[witness.position] if isinstance(cause, ValuesBody) else cause,
            (witness.body, witness.output),
            P.TYPE_PROOF,
            (D.COLUMN,),
        )
    raise TypeError("VALUES origin requires an exact VALUES witness")
