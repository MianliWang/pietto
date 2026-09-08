"""Semantic pre-match inputs, independent of tail modules and IR allocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pietto._project.model import ProjectRowField, ProjectRowFieldNullability
from pietto._project.module_attribution import ProjectModuleRowFieldIdentity
from pietto._project.module_attribution import _declaration_identity
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIRRelationalRowOutputExtension,
)
from pietto._project.project_ir import (
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRRelationAnchor,
)
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_relationship_paths import ProjectRelationshipPathStep
from pietto._project.project_relationship_match_guarantees import (
    ProjectRelationshipMinimumBound,
)
from pietto._project.project_relationship_uses import (
    ProjectJoinUse,
    ProjectJoinUseIdentity,
    ProjectJoinUseState,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
    ProjectRelationshipUseSet,
)
from pietto.ast_nodes import AuthoredJoinKind

if TYPE_CHECKING:
    from pietto._project.project_completion import (
        ProjectCompletion,
        ProjectCompletionDependency,
    )
    from pietto._project.project_join_conditions import ProjectJoinCondition
    from pietto._project.project_final_outputs import (
        ProjectConcreteEffectiveOutputEntry,
        ProjectEffectiveOutputCompletionEntry,
    )

__all__: tuple[str, ...] = ()


class ProjectCurrentInputAuthority:
    """Nominal completed-entry adapter implemented by the final-output owner."""

    __slots__ = ()
    completion: ProjectCompletion
    owner: ProjectDeclarationOccurrence
    entry: ProjectConcreteEffectiveOutputEntry
    fields: tuple[ProjectCurrentInputField | ProjectIROutputFieldOccurrence, ...]
    historical_properties: ProjectIROutputRelationalProperties | None

    def field_parts(
        self,
    ) -> tuple[tuple[ProjectModuleRowFieldIdentity, ProjectRowField, object], ...]:
        raise NotImplementedError

    def validate(self) -> None:
        raise NotImplementedError

    def materialized_properties(
        self,
        output: ProjectCurrentMaterializedInput,
        incoming: ProjectIROutputRelationalProperties | None,
    ) -> ProjectIROutputRelationalProperties:
        raise NotImplementedError


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentInputField:
    authority: ProjectCurrentInputAuthority = field(repr=False)
    field_position: int
    identity: ProjectModuleRowFieldIdentity = field(init=False)
    evidence: ProjectRowField = field(init=False)
    original: object = field(init=False, repr=False)
    effective_nullability: ProjectRowFieldNullability = field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authority, ProjectCurrentInputAuthority)
            or type(self.authority) is ProjectCurrentInputAuthority
        ):
            raise TypeError(
                "Current field requires a concrete input authority adapter."
            )
        self.authority.validate()
        parts = self.authority.field_parts()
        if type(self.field_position) is not int or not 0 <= self.field_position < len(
            parts
        ):
            raise ValueError(
                "Current input field requires exact producer-field membership."
            )
        identity, evidence, original = parts[self.field_position]
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "original", original)
        object.__setattr__(self, "effective_nullability", evidence.nullability)


type ProjectCurrentSourceField = (
    ProjectIROutputFieldOccurrence | ProjectCurrentInputField
)
type ProjectCurrentNullingCause = ProjectRelationshipPathStep | ProjectJoinUseIdentity
type ProjectCurrentInputRow = tuple[
    ProjectRelationBindingOccurrence,
    ProjectCurrentSourceField,
    ProjectRowFieldNullability,
    tuple[ProjectCurrentNullingCause, ...],
]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentInputRowField:
    field_position: int
    source_field: ProjectCurrentSourceField
    identity: ProjectModuleRowFieldIdentity
    evidence: ProjectRowField = field(init=False)
    effective_nullability: ProjectRowFieldNullability = field(init=False)

    def __post_init__(self) -> None:
        if (
            self.field_position != self.source_field.field_position
            or type(self.identity) is not ProjectModuleRowFieldIdentity
        ):
            raise ValueError(
                "Materialized input field requires its exact source occurrence."
            )
        object.__setattr__(self, "evidence", self.source_field.evidence)
        object.__setattr__(
            self, "effective_nullability", self.source_field.effective_nullability
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentInputRowShape:
    authority: ProjectCurrentInputAuthority = field(repr=False)
    producer: ProjectIRPlanNodeOccurrence
    relation: ProjectIRRelationAnchor = field(init=False)
    fields: tuple[ProjectCurrentInputRowField, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.authority.validate()
        if (
            type(self.producer) is not ProjectIRPlanNodeOccurrence
            or type(self.producer.anchor) is not ProjectIRRelationAnchor
            or self.producer.anchor.identity
            != _declaration_identity(self.authority.owner)
            or self.producer.ref.scope
            is not self.authority.completion.plan.structural_stage.scope
        ):
            raise ValueError(
                "Materialized input must retain exact producer and snapshot roots."
            )
        parts = self.authority.field_parts()
        if len(parts) != len(self.authority.fields):
            raise ValueError("Materialized input requires every producer field.")
        fields = tuple(
            ProjectCurrentInputRowField(
                field_position=position,
                source_field=member,
                identity=parts[position][0],
            )
            for position, member in enumerate(self.authority.fields)
        )
        if any(
            member.evidence is not part[1]
            for member, part in zip(fields, parts, strict=True)
        ):
            raise ValueError(
                "Materialized field cannot substitute equal-looking evidence."
            )
        object.__setattr__(self, "relation", self.producer.anchor)
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentMaterializedInput(ProjectIRRelationalRowOutputExtension):
    """A located row boundary over an already completed semantic producer."""

    authority: ProjectCurrentInputAuthority = field(repr=False)
    starting_allocation: ProjectIRAllocationState
    incoming: ProjectIROutputRelationalProperties | None = field(
        default=None, repr=False
    )
    node: ProjectIRPlanNodeOccurrence = field(init=False)
    occurrence: ProjectIROutputValueOccurrence = field(init=False)
    row_shape: ProjectCurrentInputRowShape = field(init=False)
    ending_allocation: ProjectIRAllocationState = field(init=False)
    properties: ProjectIROutputRelationalProperties = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.authority.validate()
        allocation = self.starting_allocation
        if (
            type(allocation) is not ProjectIRAllocationState
            or allocation.scope
            is not self.authority.completion.plan.structural_stage.scope
            or self.authority.historical_properties is not None
        ):
            raise ValueError(
                "Materialization requires exact completed, not historical, input authority."
            )
        anchor = ProjectIRRelationAnchor(
            identity=_declaration_identity(self.authority.owner)
        )
        node = ProjectIRPlanNodeOccurrence(
            ref=ProjectIRPlanNodeRef(
                scope=allocation.scope, position=allocation.next_plan_node_position
            ),
            anchor=anchor,
        )
        output = ProjectIROutputValueOccurrence(
            ref=ProjectIROutputValueRef(
                scope=allocation.scope, position=allocation.next_output_value_position
            ),
            producer=node,
            anchor=anchor,
        )
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "occurrence", output)
        object.__setattr__(
            self,
            "row_shape",
            ProjectCurrentInputRowShape(authority=self.authority, producer=node),
        )
        object.__setattr__(
            self,
            "ending_allocation",
            ProjectIRAllocationState(
                scope=allocation.scope,
                next_plan_node_position=allocation.next_plan_node_position + 1,
                next_output_value_position=allocation.next_output_value_position + 1,
                next_input_slot_position=allocation.next_input_slot_position,
                next_use_position=allocation.next_use_position,
            ),
        )
        properties = self.authority.materialized_properties(self, self.incoming)
        if (
            type(properties) is not ProjectIROutputRelationalProperties
            or properties.output is not self
        ):
            raise ValueError(
                "Materialized properties require the exact input output root."
            )
        object.__setattr__(self, "properties", properties)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentBindingInput:
    binding: ProjectRelationBindingOccurrence
    dependency: ProjectCompletionDependency | None
    authority: ProjectCurrentInputAuthority | None = field(default=None, repr=False)
    blocker: object | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.binding) is not ProjectRelationBindingOccurrence:
            raise TypeError("Current input requires an exact authored binding.")
        if self.dependency is not None and self.dependency.evidence is not self.binding:
            raise ValueError(
                "Current input dependency must retain its exact binding role."
            )
        if self.authority is not None:
            if (
                not isinstance(self.authority, ProjectCurrentInputAuthority)
                or self.dependency is None
                or self.authority.owner is not self.dependency.target
                or self.blocker is not None
            ):
                raise ValueError(
                    "Current input requires exact available producer authority."
                )
            self.authority.validate()
        elif self.blocker is None:
            raise ValueError("Unavailable current input requires its exact blocker.")

    @property
    def fields(self) -> tuple[ProjectCurrentSourceField, ...]:
        return () if self.authority is None else self.authority.fields


def require_current_input_properties(
    binding: ProjectCurrentBindingInput, properties: ProjectIROutputRelationalProperties
) -> None:
    authority = binding.authority
    if authority is None or type(properties) is not ProjectIROutputRelationalProperties:
        raise ValueError("JOIN input requires exact available property authority.")
    if authority.historical_properties is not None:
        valid = properties is authority.historical_properties
    else:
        output = properties.output
        valid = (
            isinstance(output, ProjectCurrentMaterializedInput)
            and output.authority is authority
            and output.properties is properties
        )
    if not valid:
        raise ValueError("JOIN input properties belong to a foreign or stale producer.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinInputScope:
    completion: ProjectCompletion = field(repr=False)
    uses: ProjectRelationshipUseSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    available_entries: tuple[ProjectEffectiveOutputCompletionEntry, ...] = field(
        repr=False
    )
    bindings: tuple[ProjectCurrentBindingInput, ...]

    def __post_init__(self) -> None:
        if (
            type(self.uses) is not ProjectRelationshipUseSet
            or self.completion.verification.root.join_regions.uses is not self.uses
            or not any(self.ledger is item for item in self.uses.ledgers)
        ):
            raise ValueError("Current inputs require exact completion/use roots.")
        if len(self.bindings) != len(self.ledger.bindings) or any(
            type(item) is not ProjectCurrentBindingInput or item.binding is not binding
            for item, binding in zip(self.bindings, self.ledger.bindings, strict=True)
        ):
            raise ValueError(
                "Current inputs must retain every binding occurrence in order."
            )
        for item in self.bindings:
            dependency = item.dependency
            if dependency is not None and not any(
                dependency is retained for retained in self.completion.dependencies
            ):
                raise ValueError(
                    "Current dependency is outside the exact completion root."
                )
            authority = item.authority
            if authority is not None:
                if authority.completion is not self.completion or not any(
                    authority.entry is entry for entry in self.available_entries
                ):
                    raise ValueError(
                        "Current producer must be an exact available entry."
                    )
                for position, member in enumerate(authority.fields):
                    if member.field_position != position:
                        raise ValueError(
                            "Current producer fields must retain source order."
                        )
                    if (
                        type(member) is ProjectCurrentInputField
                        and member.authority is not authority
                    ):
                        raise ValueError(
                            "Current input field belongs to a foreign producer."
                        )
            elif item.blocker is item.binding:
                if dependency is not None or item.binding.target is not None:
                    raise ValueError(
                        "Unresolved binding blocker cannot replace a resolved dependency."
                    )
            else:
                matches = tuple(
                    entry for entry in self.available_entries if entry is item.blocker
                )
                if (
                    len(matches) != 1
                    or dependency is None
                    or matches[0].owner is not dependency.target
                ):
                    raise ValueError(
                        "Current blocker must retain its exact dependency target."
                    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinInputFailure:
    scope: ProjectCurrentJoinInputScope = field(repr=False)
    blockers: tuple[object, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectCurrentJoinInputScope:
            raise TypeError("Current input failure requires an exact input scope.")
        blockers = tuple(
            item.blocker if item.authority is None else item.binding
            for item in self.scope.bindings
            if item.authority is None
            or item.binding.state is ProjectJoinUseState.AMBIGUOUS
        )
        if not blockers or any(item is None for item in blockers):
            raise ValueError(
                "Current input failure requires all exact unavailable causes."
            )
        object.__setattr__(self, "blockers", blockers)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentPreMatchInputs:
    scope: ProjectCurrentJoinInputScope = field(repr=False)
    use: ProjectJoinUse = field(repr=False)
    prefix: tuple[ProjectJoinCondition, ...] = field(default=(), repr=False)
    rows: tuple[ProjectCurrentInputRow, ...] = field(init=False)
    blocked_bindings: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectCurrentJoinInputScope or not any(
            self.use is retained for retained in self.scope.ledger.uses
        ):
            raise ValueError(
                "Pre-match inputs require exact current scope/use membership."
            )
        position = self.use.identity.join_position
        if len(self.prefix) != position or any(
            item.use is not use
            for item, use in zip(
                self.prefix, self.scope.ledger.uses[:position], strict=True
            )
        ):
            raise ValueError(
                "Pre-match prefix must retain every earlier authored condition."
            )
        if any(
            item.root.uses is not self.scope.uses
            or (item.inputs is not None and item.inputs.scope is not self.scope)
            or (
                item.inputs is None
                and not any(item is retained for retained in item.root.entries)
            )
            for item in self.prefix
        ):
            raise ValueError(
                "Pre-match prefix requires exact retained condition roots."
            )
        inputs = self.scope.bindings[: position + 2]
        nullability = {
            (id(item.binding), id(member)): member.effective_nullability
            for item in inputs
            for member in item.fields
        }
        nulling: dict[int, tuple[ProjectCurrentNullingCause, ...]] = {}
        blocked = [
            item.binding
            for item in inputs
            if item.authority is None
            or item.binding.state is ProjectJoinUseState.AMBIGUOUS
        ]
        for prior in self.prefix:
            if not prior.ready:
                blocked.extend(item.binding for item in inputs[:-1])
                break
            target = prior.use.target_binding
            if prior.mode in {"M1", "M2"} and prior.effective_use.path is not None:
                source = prior.effective_use.source_binding
                source_nulling = () if source is None else nulling.get(id(source), ())
                for ordinal, step in enumerate(prior.effective_use.path.steps):
                    guarantee = step.guarantee
                    right_nulling = (
                        (*source_nulling, step)
                        if prior.use.kind is AuthoredJoinKind.LEFT
                        and (
                            source_nulling
                            or guarantee.minimum
                            is ProjectRelationshipMinimumBound.ZERO_ALLOWED
                        )
                        else ()
                    )
                    if (
                        ordinal == 0
                        and source is not None
                        and prior.use.kind is AuthoredJoinKind.INNER
                        and not source_nulling
                    ):
                        for group in guarantee.source_matched_classes:
                            for member in group.members:
                                nullability[id(source), id(member)] = (
                                    ProjectRowFieldNullability.NON_NULL
                                )
                    if ordinal == len(prior.effective_use.path.steps) - 1:
                        nulling[id(target)] = right_nulling
                        for item in inputs:
                            if item.binding is target:
                                for member in item.fields:
                                    if right_nulling:
                                        nullability[id(target), id(member)] = (
                                            ProjectRowFieldNullability.NULLABLE
                                        )
                                    elif any(
                                        any(
                                            member is original
                                            for original in group.members
                                        )
                                        for group in guarantee.target_matched_classes
                                    ):
                                        nullability[id(target), id(member)] = (
                                            ProjectRowFieldNullability.NON_NULL
                                        )
                    source_nulling = right_nulling
                continue
            kind = prior.use.kind
            if kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}:
                for item in inputs[: prior.use.identity.join_position + 1]:
                    causes = (*nulling.get(id(item.binding), ()), prior.use.identity)
                    nulling[id(item.binding)] = causes
                    for member in item.fields:
                        nullability[id(item.binding), id(member)] = (
                            ProjectRowFieldNullability.NULLABLE
                        )
            if kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}:
                nulling[id(target)] = (
                    *nulling.get(id(target), ()),
                    prior.use.identity,
                )
                for item in inputs:
                    if item.binding is target:
                        for member in item.fields:
                            nullability[id(target), id(member)] = (
                                ProjectRowFieldNullability.NULLABLE
                            )
            elif kind is AuthoredJoinKind.INNER:
                for proof in prior.null_rejections:
                    target_field = proof.field
                    if not nulling.get(id(target_field.binding), ()):
                        nullability[
                            id(target_field.binding), id(target_field.input_field)
                        ] = ProjectRowFieldNullability.NON_NULL
        rows = tuple(
            (
                item.binding,
                member,
                nullability[id(item.binding), id(member)],
                nulling.get(id(item.binding), ()),
            )
            for item in inputs
            for member in item.fields
        )
        object.__setattr__(self, "rows", rows)
        object.__setattr__(
            self,
            "blocked_bindings",
            tuple(
                item.binding
                for item in inputs
                if any(item.binding is value for value in blocked)
            ),
        )
