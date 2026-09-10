"""Exact semantic-to-combined JOIN correspondence in the existing IR domains."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_current_join_inputs import ProjectCurrentMaterializedInput
from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    ProjectCurrentJoinRegion,
)
from pietto._project.project_grain import (
    ProjectBaseGrainFactorIdentity,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectGrainOriginAuthority,
    ProjectGroupedGrainFactorIdentity,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRUseRef,
    _declaration_identity,
)
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
    ProjectIRJoinedRowShape,
    ProjectIRJoinRowOutput,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRRelationalRowOutput,
    ProjectIROutputRelationalProperties,
    ProjectIRProvidedIntrinsicGrain,
    _compile_output_fd_index,
    _field_occurrences,
    _image_keys_and_fds,
    _preserving_classes,
)
from pietto._project.project_join_conditions import ProjectJoinCondition
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify

if TYPE_CHECKING:
    from pietto._project.project_completed_semantics import (
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput

__all__: tuple[str, ...] = ()

type ProjectIRSemanticJoin = ProjectCurrentBinaryJoin | ProjectIRBinaryJoinOccurrence

type ProjectIRSemanticJoinRegion = (
    ProjectCurrentJoinRegion | ProjectIRConcreteJoinRegion
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRJoinInputCorrespondence:
    source: ProjectIRJoinInputUseOccurrence = field(repr=False)
    use: ProjectIRJoinInputUseOccurrence
    source_properties: ProjectIROutputRelationalProperties = field(repr=False)
    producer: ProjectDeclarationOccurrence | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRComposedJoin:
    source: ProjectIRSemanticJoin = field(repr=False)
    condition: ProjectJoinCondition = field(repr=False)
    source_properties: ProjectIROutputRelationalProperties = field(repr=False)
    node: ProjectIRPlanNodeOccurrence
    inputs: tuple[ProjectIRJoinInputCorrespondence, ...]
    output: ProjectIRJoinRowOutput

    @property
    def input_uses(self) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
        return tuple(item.use for item in self.inputs)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRComposedJoinPrefix:
    semantic_entry: ProjectCompletedEffectiveOutput = field(repr=False)
    region: ProjectIRSemanticJoinRegion = field(repr=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    joins: tuple[ProjectIRComposedJoin, ...]
    final_join: ProjectIRComposedJoin
    ref_images: tuple[tuple[object, object], ...] = field(repr=False)

    @property
    def nodes(self) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
        return tuple(item.node for item in self.joins)

    @property
    def outputs(self) -> tuple[ProjectIROutputValueOccurrence, ...]:
        return tuple(item.output.occurrence for item in self.joins)

    @property
    def uses(self) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
        return tuple(use for item in self.joins for use in item.input_uses)

    @property
    def slots(self) -> tuple[ProjectIRInputSlotOccurrence, ...]:
        return tuple(use.slot for use in self.uses)


def _historical_refs(
    completed: ProjectConcreteCompletedSemanticResult,
) -> tuple[object, ...]:
    plan = completed.verification.root.evaluation.project_plan.structural_stage
    joins = completed.verification.root.join_regions.structural
    return tuple(
        item.ref
        for items in (
            plan.nodes,
            plan.outputs,
            plan.input_slots,
            plan.uses,
            joins.nodes,
            joins.outputs,
            joins.input_slots,
            joins.uses,
        )
        for item in items
    )


def _mapped_ref(
    original: object, images: Mapping[int, object], historical: tuple[object, ...]
) -> object:
    result = images.get(id(original))
    if result is not None:
        return result
    if any(original is item for item in historical):
        return original
    raise ValueError("Composed provenance has no exact source-to-combined image.")


def build_project_ir_join_prefix(
    completed: ProjectConcreteCompletedSemanticResult,
    entry: ProjectCompletedEffectiveOutput,
    region: ProjectIRSemanticJoinRegion,
    active: Mapping[int, ProjectIRRelationalRowOutput],
    allocation: ProjectIRAllocationState,
    previous: tuple[ProjectIRComposedJoinPrefix, ...],
) -> ProjectIRComposedJoinPrefix:
    """Remap retained rows/uses; never invoke semantic JOIN construction."""
    images = {
        id(source): target
        for prefix in previous
        for source, target in prefix.ref_images
    }
    historical = _historical_refs(completed)
    row_images: dict[int, ProjectIRJoinRowOutput] = {}
    use_images: dict[int, ProjectIRJoinInputUseOccurrence] = {
        id(item.source): item.use
        for prefix in previous
        for join in prefix.joins
        for item in join.inputs
    }
    current = allocation
    built: list[ProjectIRComposedJoin] = []
    own_images: list[tuple[object, object]] = []
    final: ProjectIRComposedJoin | None = None
    conditions = completed.effective_outputs.operative_conditions
    if conditions is None:
        raise ValueError("Composed JOIN requires retained operative conditions.")
    root = entry.root
    if not isinstance(root, ProjectConcreteJoinedQualify):
        raise TypeError("Composed JOIN prefix requires a joined semantic tail.")
    final_source = (
        root.window_stage.input_aggregation.input_filter.joined_semantics.final_output
    )
    for original in region.joins:
        matches = tuple(
            c
            for c in conditions.entries
            if c.ledger is region.ledger
            and (c.use is original.use or c.effective_use is original.use)
        )
        if len(matches) != 1:
            raise ValueError("Composed JOIN requires its exact operative condition.")
        condition = matches[0]
        source_results = (
            tuple(p.relational for p in region.join_properties if p.join is original)
            if isinstance(region, ProjectCurrentJoinRegion)
            else tuple(
                p.relational
                for p in completed.verification.root.join_regions.properties.outputs
                if p.join is original
            )
        )
        if len(source_results) != 1:
            raise ValueError(
                "Composed JOIN requires its exact semantic property result."
            )
        node = ProjectIRPlanNodeOccurrence(
            ref=ProjectIRPlanNodeRef(
                scope=allocation.scope, position=current.next_plan_node_position
            ),
            anchor=ProjectIRRelationAnchor(identity=_declaration_identity(entry.owner)),
        )
        local_images: list[tuple[object, object]] = [(original.node.ref, node.ref)]
        inputs: list[ProjectIRJoinInputCorrespondence] = []
        for ordinal, (old_use, source) in enumerate(
            zip(
                original.input_uses,
                (original.left_input, original.right_input),
                strict=True,
            )
        ):
            producer = None
            incoming: ProjectIRRelationalRowOutput | None = row_images.get(
                id(source.output)
            )
            if incoming is None:
                if isinstance(source.output, ProjectCurrentMaterializedInput):
                    producer = source.output.authority.owner
                    if not any(
                        source.output.authority.entry is retained
                        for retained in completed.effective_outputs.entries
                    ):
                        raise ValueError(
                            "Composed input cannot use a foreign completed entry."
                        )
                else:
                    owners = tuple(
                        owner
                        for owner in completed.effective_outputs.owners
                        if _declaration_identity(owner)
                        == source.output.row_shape.relation.identity
                    )
                    if len(owners) != 1 or not any(
                        source.output.occurrence is output
                        for output in completed.verification.root.evaluation.project_plan.structural_stage.outputs
                    ):
                        raise ValueError(
                            "Composed input requires its exact historical producer."
                        )
                    producer = owners[0]
                incoming = active.get(id(producer))
                if incoming is None:
                    raise ValueError(
                        "Composed input requires an explicit available active output."
                    )
            slot = ProjectIRInputSlotOccurrence(
                ref=ProjectIRInputSlotRef(
                    scope=allocation.scope,
                    position=current.next_input_slot_position + ordinal,
                ),
                consumer=node,
                input_ordinal=ordinal,
            )
            use = ProjectIRJoinInputUseOccurrence(
                ref=ProjectIRUseRef(
                    scope=allocation.scope, position=current.next_use_position + ordinal
                ),
                output=incoming.occurrence,
                slot=slot,
            )
            inputs.append(
                ProjectIRJoinInputCorrespondence(
                    source=old_use, use=use, source_properties=source, producer=producer
                )
            )
            use_images[id(old_use)] = use
            local_images.extend(((old_use.ref, use.ref), (old_use.slot.ref, slot.ref)))
        images.update((id(source), target) for source, target in local_images)
        fields: list[ProjectIRJoinedRowField] = []
        for old_field in original.output.row_shape.fields:
            introduction = use_images.get(id(old_field.introduction_use))
            if introduction is None:
                if not any(
                    old_field.introduction_use is use
                    for use in completed.verification.root.join_regions.structural.uses
                ):
                    raise ValueError("Composed field lost its introduction-use image.")
                introduction = old_field.introduction_use
            fields.append(
                ProjectIRJoinedRowField(
                    field_position=old_field.field_position,
                    evidence=old_field.evidence,
                    introduction_use=introduction,
                    nulling_joins=tuple(
                        cast(ProjectIRPlanNodeRef, _mapped_ref(ref, images, historical))
                        for ref in old_field.nulling_joins
                    ),
                    effective_nullability=old_field.effective_nullability,
                )
            )
        occurrence = ProjectIROutputValueOccurrence(
            ref=ProjectIROutputValueRef(
                scope=allocation.scope, position=current.next_output_value_position
            ),
            producer=node,
            anchor=node.anchor,
        )
        output = ProjectIRJoinRowOutput(
            occurrence=occurrence,
            row_shape=ProjectIRJoinedRowShape(
                relation=cast(ProjectIRRelationAnchor, node.anchor),
                producer=node,
                fields=tuple(fields),
            ),
        )
        local_images.append((original.output.occurrence.ref, occurrence.ref))
        images[id(original.output.occurrence.ref)] = occurrence.ref
        own_images.extend(local_images)
        joined = ProjectIRComposedJoin(
            source=original,
            condition=condition,
            source_properties=source_results[0],
            node=node,
            inputs=tuple(inputs),
            output=output,
        )
        built.append(joined)
        row_images[id(original.output)] = output
        if original.output is final_source:
            final = joined
        current = ProjectIRAllocationState(
            scope=allocation.scope,
            next_plan_node_position=current.next_plan_node_position + 1,
            next_output_value_position=current.next_output_value_position + 1,
            next_input_slot_position=current.next_input_slot_position + 2,
            next_use_position=current.next_use_position + 2,
        )
    if final is None:
        raise ValueError(
            "Composed prefix requires the explicit semantic final JOIN output."
        )
    return ProjectIRComposedJoinPrefix(
        semantic_entry=entry,
        region=region,
        starting_allocation=allocation,
        ending_allocation=current,
        joins=tuple(built),
        final_join=final,
        ref_images=tuple(own_images),
    )


def image_project_ir_join_properties(
    source: ProjectIROutputRelationalProperties,
    output: ProjectIRJoinRowOutput,
    origins: ProjectGrainOriginAuthority,
    ref_images: Mapping[int, object],
    historical: tuple[object, ...],
    factor_images: dict[int, ProjectGrainFactorIdentity],
) -> ProjectIROutputRelationalProperties:
    """Use existing field/key/FD kernels and mechanically image grain coordinates."""

    def factor(identity: ProjectGrainFactorIdentity) -> ProjectGrainFactorIdentity:
        known = factor_images.get(id(identity))
        if known is not None:
            return known
        if isinstance(identity, ProjectJoinGrainFactorIdentity):
            result: ProjectGrainFactorIdentity = ProjectJoinGrainFactorIdentity(
                base=cast(ProjectBaseGrainFactorIdentity, factor(identity.base)),
                introduction_use=cast(
                    ProjectIRUseRef,
                    _mapped_ref(identity.introduction_use, ref_images, historical),
                ),
                nulling_joins=tuple(
                    cast(ProjectIRPlanNodeRef, _mapped_ref(ref, ref_images, historical))
                    for ref in identity.nulling_joins
                ),
                source_factor=None
                if identity.source_factor is None
                else cast(
                    ProjectJoinGrainFactorIdentity, factor(identity.source_factor)
                ),
            )
        elif isinstance(identity, ProjectGroupedGrainFactorIdentity):
            if not any(identity.operator is ref for ref in historical):
                raise ValueError(
                    "Composed grouped input requires its active factor image."
                )
            result = identity
        else:
            result = identity
        factor_images[id(identity)] = result
        return result

    fields = _field_occurrences(output)
    classes, images = _preserving_classes(source, output, fields)
    keys, fds = _image_keys_and_fds(source, output, classes, images, support=source)
    old = source.grain
    grain = ProjectIRProvidedIntrinsicGrain(
        output=output,
        state=old.state,
        factors=tuple(
            ProjectGrainDomainFactor(identity=factor(f.identity)) for f in old.factors
        ),
        active=tuple(factor(f) for f in old.active),
        dependencies=tuple(
            ProjectGrainDependencyFact(
                determinants=tuple(factor(f) for f in d.determinants),
                dependents=tuple(factor(f) for f in d.dependents),
            )
            for d in old.dependencies
        ),
        origin_set=origins,
        witness=source,
    )
    return ProjectIROutputRelationalProperties(
        output=output,
        fields=fields,
        value_classes=classes,
        keys=keys,
        fds=fds,
        fd_index=_compile_output_fd_index(output, classes, fds),
        grain=grain,
    )
