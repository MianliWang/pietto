"""Non-SELECT SET bodies, positional operand images and whole-row requirements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pietto.ast_nodes import SetRelationDef, SetOperationKind, SetOperationQuantifier
from pietto._project.project_set_operations import (
    ProjectSetOperation,
    ProjectSetColumn,
    ProjectSetMultiplicityLaw,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedSetOutputField,
    ProjectCompletedRowDomain,
    ProjectSetFullRowUniqueness,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedSetOperationOutput,
    ProjectIRSetOperandInput,
    ProjectIRQueryBlockResultProperties,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_row_equivalence import ProjectRowEquivalenceField

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanRef,
        ProjectSQLInputUse,
        ProjectSQLPort,
    )
    from pietto._project.project_sql_plan_results import ProjectSQLResultPort

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSetBody:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    source: ProjectIRCompletedSetOperationOutput
    operation: ProjectSetOperation
    kind: SetOperationKind
    quantifier: SetOperationQuantifier
    multiplicity: ProjectSetMultiplicityLaw
    requires_equivalence: bool
    full_row_unique: bool
    fold: Literal["source_order_left_fold"]
    operands: tuple[ProjectSQLPlanRef, ...]
    columns: tuple[ProjectSQLPlanRef, ...]
    outputs: tuple[ProjectSQLPlanRef, ...]
    row_domain: ProjectCompletedRowDomain
    properties: ProjectIRQueryBlockResultProperties
    uniqueness: ProjectSetFullRowUniqueness | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSetOperand:
    ref: ProjectSQLPlanRef
    body: ProjectSQLPlanRef
    position: int
    source: ProjectIRSetOperandInput
    use: ProjectSQLInputUse
    producer: ProjectSQLPlanRef
    fields: tuple[ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSetInput:
    ref: ProjectSQLPlanRef
    operand: ProjectSQLPlanRef
    position: int
    binding: ProjectSQLPort
    terminal: ProjectSQLPort | ProjectSQLResultPort
    evidence: ProjectRowEquivalenceField


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSetColumn:
    """A positional map; the SET operation always compares complete rows."""

    ref: ProjectSQLPlanRef
    body: ProjectSQLPlanRef
    position: int
    source: ProjectSetColumn
    semantic: ProjectCompletedSetOutputField
    field: ProjectIROutputFieldOccurrence
    inputs: tuple[ProjectSQLPlanRef, ...]
    value_inputs: tuple[ProjectSQLPlanRef, ...]
    output: ProjectSQLPlanRef


type Witness = (
    ProjectSQLSetBody | ProjectSQLSetOperand | ProjectSQLSetInput | ProjectSQLSetColumn
)


class ProjectSQLSetDemandKind(StrEnum):
    OPERATION = "set_operation_quantifier_multiplicity_and_membership"
    PROPERTIES = "set_properties_and_row_domain"
    COMPARISON = "set_whole_row_equivalence"
    OPERAND = "set_operand_membership"
    INPUT = "set_input_type_null_and_representation"
    COLUMN = "set_positional_column_and_value_sources"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSetDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLSetDemandKind
    witness: Witness
    origin: ProjectSQLPlanRef


def build_body(definition, uses, terminals, ref, port):
    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind as K
    from pietto._project.project_sql_plan_results import ProjectSQLResultPortRole

    entry = definition.entry
    assert isinstance(entry, ProjectIRCompletedSetOperationOutput)
    semantic = entry.semantic_entry
    operation = semantic.root
    authored_definition = operation.owner.definition
    if (
        not isinstance(authored_definition, SetRelationDef)
        or authored_definition.body.quantifier is None
    ):
        raise ValueError("SET body lost its original explicit quantifier")
    authored = authored_definition.body
    assert authored.quantifier is not None
    body_ref = ref(K.SET_BODY)
    operands, inputs, columns, outputs = [], [], [], []
    for i, image in enumerate(entry.operands):
        use = uses[id(image)]
        operand_ref = ref(K.SET_OPERAND)
        local_inputs = []
        for j, (binding, evidence) in enumerate(
            zip(use.ports, image.source.fields, strict=True)
        ):
            assert binding.producer_port is not None
            value = ProjectSQLSetInput(
                ref=ref(K.SET_INPUT),
                operand=operand_ref,
                position=j,
                binding=binding,
                terminal=terminals[binding.producer_port],
                evidence=evidence,
            )
            inputs.append(value)
            local_inputs.append(value.ref)
        operands.append(
            ProjectSQLSetOperand(
                ref=operand_ref,
                body=body_ref,
                position=i,
                source=image,
                use=use,
                producer=use.producer,
                fields=tuple(local_inputs),
            )
        )
    for i, (source, field, canonical) in enumerate(
        zip(operation.columns, semantic.fields, definition.exports, strict=True)
    ):
        column_ref = ref(K.SET_COLUMN)
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
        positions = tuple(operand.fields[i] for operand in operands)
        columns.append(
            ProjectSQLSetColumn(
                ref=column_ref,
                body=body_ref,
                position=i,
                source=source,
                semantic=field,
                field=canonical.field,
                inputs=positions,
                value_inputs=positions[:1]
                if authored.kind is SetOperationKind.EXCEPT
                else positions,
                output=output.ref,
            )
        )
        outputs.append(output)
    body = ProjectSQLSetBody(
        ref=body_ref,
        definition=definition.ref,
        source=entry,
        operation=operation,
        kind=authored.kind,
        quantifier=authored.quantifier,
        multiplicity=operation.multiplicity,
        requires_equivalence=operation.requires_equivalence,
        full_row_unique=operation.full_row_unique,
        fold="source_order_left_fold",
        operands=tuple(operand.ref for operand in operands),
        columns=tuple(column.ref for column in columns),
        outputs=tuple(output.ref for output in outputs),
        row_domain=semantic.row_domain,
        properties=entry.active_properties,
        uniqueness=semantic.uniqueness,
    )
    return body, operands, inputs, columns, outputs


def origin_context(plan):
    return (
        {body.ref: body for body in plan.set_bodies},
        {operand.ref: operand for operand in plan.set_operands},
    )


def origin_parts(witness, context):
    """Read original sites and explicit edges; no allocation or semantic analysis."""
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    D = ProjectSQLSetDemandKind
    bodies, operands = context
    if isinstance(witness, ProjectSQLSetBody):
        definition = witness.operation.owner.definition
        if not isinstance(definition, SetRelationDef):
            raise ValueError("SET origin requires its authored body")
        kinds = (
            D.OPERATION,
            D.PROPERTIES,
            *((D.COMPARISON,) if witness.requires_equivalence else ()),
        )
        return (
            witness.definition,
            definition.body,
            witness.operands + witness.outputs,
            P.MEMBERSHIP,
            kinds,
        )
    if isinstance(witness, ProjectSQLSetOperand):
        body = bodies[witness.body]
        return (
            body.definition,
            witness.source.source.resolution.reference.operand,
            (witness.use.ref, witness.producer, *witness.fields),
            P.MEMBERSHIP,
            (D.OPERAND,),
        )
    if isinstance(witness, ProjectSQLSetInput):
        operand = operands[witness.operand]
        body = bodies[operand.body]
        provenance = (
            P.MEMBERSHIP
            if body.kind is SetOperationKind.EXCEPT and operand.position > 0
            else P.VALUE
        )
        return (
            body.definition,
            operand.source.source.resolution.reference.operand,
            (witness.operand, witness.binding.ref, witness.terminal.ref),
            provenance,
            (D.INPUT,),
        )
    body = bodies[witness.body]
    return (
        body.definition,
        body.operation.owner.definition.body,
        (witness.body, *witness.inputs, witness.output),
        P.VALUE,
        (D.COLUMN,),
    )
