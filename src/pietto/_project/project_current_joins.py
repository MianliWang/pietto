"""Current direct-binary rows from exact authored facts, outside combined IR."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_current_join_inputs import (
    ProjectCurrentJoinInputScope,
    ProjectCurrentSourceField,
    require_current_input_properties,
)
from pietto._project.project_grain import (
    ProjectCompositeGrainOriginAuthority,
    ProjectGrainBasisState,
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
)
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRJoinOutputProperties,
    ProjectIRJoinUnavailableProperty,
    _all_non_null,
    _classes_for_output,
    _grain,
    _image_fd,
    _image_key,
    _ordered_classes,
    _build_join,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
    ProjectIRJoinedRowShape,
    ProjectIRJoinRowOutput,
    ProjectIRProvidedNullExtension,
    ProjectIRProvidedPropertySlot,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIRProvidedIntrinsicGrain,
    _compile_output_fd_index,
    _field_occurrences,
    _frontier,
    _key_fds,
)
from pietto._project.project_join_conditions import (
    ProjectJoinCondition,
    ProjectJoinConditionSet,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectRelationshipMaximumBound,
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUse,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto.ast_nodes import AuthoredJoinKind

__all__: tuple[str, ...] = ()

type ProjectCurrentFieldInput = tuple[
    ProjectRelationBindingOccurrence | None, ProjectCurrentSourceField
]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinGrainWitness:
    condition: ProjectJoinCondition
    left: ProjectIRProvidedIntrinsicGrain
    right: ProjectIRProvidedIntrinsicGrain


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _CurrentPrefix:
    condition: ProjectJoinCondition
    join: ProjectCurrentBinaryJoin | ProjectIRBinaryJoinOccurrence
    properties: ProjectCurrentJoinProperties | ProjectIRJoinOutputProperties
    origins: tuple[ProjectCurrentFieldInput, ...]
    allocation: ProjectIRAllocationState

    def __post_init__(self) -> None:
        if (
            self.properties.join is not self.join
            or self.properties.relational.output is not self.join.output
            or self.join.use.clause is not self.condition.use.clause
            or len(self.origins) != len(self.join.output.row_shape.fields)
        ):
            raise ValueError(
                "Current prefix requires exact previous operator and field roots."
            )
        if (
            isinstance(self.join, ProjectCurrentBinaryJoin)
            and self.origins is not self.join.field_inputs
        ):
            raise ValueError(
                "Current prefix must retain exact output field-role authority."
            )
        if isinstance(self.join, ProjectIRBinaryJoinOccurrence) and (
            self.join.use is not self.condition.effective_use
            or self.join.identity.path_step_position
            != len(self.join.use.path.steps) - 1
        ):
            raise ValueError(
                "Current prefix must end at its exact authored path boundary."
            )
        if (
            self.allocation.scope is not self.join.node.ref.scope
            or self.allocation.next_plan_node_position
            != self.join.node.ref.position + 1
            or self.allocation.next_output_value_position
            != self.join.output.occurrence.ref.position + 1
            or self.allocation.next_input_slot_position
            != self.join.input_slots[-1].ref.position + 1
            or self.allocation.next_use_position
            != self.join.input_uses[-1].ref.position + 1
        ):
            raise ValueError(
                "Current prefix allocation must follow its exact last operator."
            )
        if any(
            field.evidence is not origin.evidence
            for field, (_, origin) in zip(
                self.join.output.row_shape.fields, self.origins, strict=True
            )
        ):
            raise ValueError(
                "Current prefix must retain every exact input-field image."
            )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentBinaryJoin:
    condition: ProjectJoinCondition = field(repr=False)
    left_input: ProjectIROutputRelationalProperties = field(repr=False)
    right_input: ProjectIROutputRelationalProperties = field(repr=False)
    left_fields: tuple[ProjectCurrentFieldInput, ...] = field(repr=False)
    starting_allocation: ProjectIRAllocationState
    prefix: _CurrentPrefix | None = field(default=None, repr=False)
    input_scope: ProjectCurrentJoinInputScope | None = field(default=None, repr=False)
    use: ProjectJoinUse = field(init=False, repr=False)
    kind: AuthoredJoinKind = field(init=False)
    node: ProjectIRPlanNodeOccurrence = field(init=False)
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...] = field(init=False)
    input_uses: tuple[ProjectIRJoinInputUseOccurrence, ...] = field(init=False)
    output: ProjectIRJoinRowOutput = field(init=False)
    field_inputs: tuple[ProjectCurrentFieldInput, ...] = field(init=False, repr=False)
    properties: ProjectCurrentJoinProperties = field(init=False, repr=False)
    ending_allocation: ProjectIRAllocationState = field(init=False)

    def __post_init__(self) -> None:
        condition = self.condition
        if type(condition) is not ProjectJoinCondition or not condition.ready:
            raise ValueError("Current binary JOIN requires exact ready authority.")
        kind = condition.use.kind
        valid_mode = (
            (
                kind in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}
                and condition.mode in {"M3", "M4"}
            )
            or (
                kind is AuthoredJoinKind.CROSS
                and condition.mode == "M5"
                and condition.expression is None
                and condition.scope is None
                and not condition.base_conditions
            )
            or (
                kind
                in {
                    AuthoredJoinKind.RIGHT,
                    AuthoredJoinKind.FULL,
                    AuthoredJoinKind.SEMI,
                    AuthoredJoinKind.ANTI,
                }
                and condition.mode in {"M1", "M2", "M3", "M4"}
            )
        )
        if not valid_mode:
            raise ValueError("Current binary JOIN kind/mode is not supported here.")
        if (
            type(self.left_input) is not ProjectIROutputRelationalProperties
            or type(self.right_input) is not ProjectIROutputRelationalProperties
        ):
            raise TypeError("Current JOIN requires exact relational input properties.")
        if self.prefix is None:
            if condition.use.identity.join_position != 0:
                raise ValueError(
                    "Current first JOIN must retain its exact named input."
                )
            if self.input_scope is None:
                if self.left_input is not condition.environment.bindings[0].output:
                    raise ValueError(
                        "Current first JOIN lost its exact historical input."
                    )
            else:
                require_current_input_properties(
                    self.input_scope.bindings[0], self.left_input
                )
        elif (
            type(self.prefix) is not _CurrentPrefix
            or self.prefix.condition.root is not condition.root
            or self.prefix.condition.use.owner is not condition.use.owner
            or self.prefix.condition.use.identity.join_position + 1
            != condition.use.identity.join_position
            or self.left_input is not self.prefix.properties.relational
            or self.left_fields is not self.prefix.origins
            or self.starting_allocation is not self.prefix.allocation
            or self.prefix.condition.inputs is not None
            and self.prefix.condition.inputs.scope is not self.input_scope
        ):
            raise ValueError(
                "Current JOIN prefix must retain exact prior operation authority."
            )
        if self.input_scope is None:
            right_fields: tuple[ProjectCurrentSourceField, ...] = (
                self.right_input.fields
            )
            if self.right_input is not condition.use.target_binding.output:
                raise ValueError("Current right input lost its historical output.")
        else:
            scope = self.input_scope
            if (
                scope.ledger is not condition.ledger
                or scope.uses is not condition.root.uses
                or condition.inputs is not None
                and condition.inputs.scope is not scope
            ):
                raise ValueError(
                    "Current binary condition must retain its exact input scope."
                )
            right_binding = scope.bindings[condition.use.identity.join_position + 1]
            require_current_input_properties(right_binding, self.right_input)
            right_fields = right_binding.fields
        if len(self.left_fields) != len(self.left_input.fields):
            raise ValueError("Current JOIN requires exact pre-match input membership.")
        for (binding, original), current in zip(
            self.left_fields, self.left_input.fields, strict=True
        ):
            if binding is None:
                if (
                    self.prefix is None
                    or type(original) is not ProjectIROutputFieldOccurrence
                    or type(self.left_input.output) is not ProjectIRJoinRowOutput
                    or current.evidence is not original.evidence
                    or self.left_input.output.row_shape.fields[
                        current.field_position
                    ].introduction_use.output
                    is not original.output.occurrence
                ):
                    raise ValueError(
                        "Hidden prefix field requires exact structural input provenance."
                    )
                continue
            originals = (
                binding.output.fields
                if self.input_scope is None and binding.output is not None
                else tuple(
                    member
                    for item in self.input_scope.bindings
                    if item.binding is binding
                    for member in item.fields
                )
                if self.input_scope is not None
                else ()
            )
            if (
                not any(binding is item for item in condition.environment.bindings[:-1])
                or not any(original is item for item in originals)
                or current.evidence is not original.evidence
            ):
                raise ValueError(
                    "Current JOIN left field lost exact binding/input authority."
                )
        allocation = self.starting_allocation
        if type(allocation) is not ProjectIRAllocationState or any(
            properties.output.occurrence.ref.scope is not allocation.scope
            for properties in (self.left_input, self.right_input)
        ):
            raise ValueError("Current JOIN requires one exact allocation scope.")
        anchor = ProjectIRRelationAnchor(identity=condition.use.identity.owner)
        node = ProjectIRPlanNodeOccurrence(
            ref=ProjectIRPlanNodeRef(
                scope=allocation.scope, position=allocation.next_plan_node_position
            ),
            anchor=anchor,
        )
        slots = tuple(
            ProjectIRInputSlotOccurrence(
                ref=ProjectIRInputSlotRef(
                    scope=allocation.scope,
                    position=allocation.next_input_slot_position + i,
                ),
                consumer=node,
                input_ordinal=i,
            )
            for i in (0, 1)
        )
        uses = tuple(
            ProjectIRJoinInputUseOccurrence(
                ref=ProjectIRUseRef(
                    scope=allocation.scope, position=allocation.next_use_position + i
                ),
                output=properties.output.occurrence,
                slot=slots[i],
            )
            for i, properties in enumerate((self.left_input, self.right_input))
        )
        left_only = kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
        origins = (
            self.left_fields
            if left_only
            else (
                *self.left_fields,
                *((condition.use.target_binding, member) for member in right_fields),
            )
        )
        rejected = {
            (id(proof.field.binding), id(proof.field.input_field))
            for proof in condition.null_rejections
        }
        fields: list[ProjectIRJoinedRowField] = []
        left_nulling = kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
        right_nulling = kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}
        for position, member in enumerate(
            self.left_input.fields
            if left_only
            else (*self.left_input.fields, *self.right_input.fields)
        ):
            is_right = position >= len(self.left_input.fields)
            if not is_right and type(self.left_input.output) is ProjectIRJoinRowOutput:
                previous = self.left_input.output.row_shape.fields[position]
                introduction, nulling = (
                    previous.introduction_use,
                    (
                        (*previous.nulling_joins, node.ref)
                        if left_nulling
                        else previous.nulling_joins
                    ),
                )
            else:
                introduction = uses[1 if is_right else 0]
                nulling = (
                    (node.ref,)
                    if (is_right and right_nulling) or (not is_right and left_nulling)
                    else ()
                )
            nullability = (
                ProjectRowFieldNullability.NULLABLE
                if nulling
                else member.effective_nullability
            )
            binding, original = origins[position]
            if (
                kind is AuthoredJoinKind.INNER
                and not nulling
                and (id(binding), id(original)) in rejected
            ):
                nullability = ProjectRowFieldNullability.NON_NULL
            fields.append(
                ProjectIRJoinedRowField(
                    field_position=position,
                    evidence=member.evidence,
                    introduction_use=introduction,
                    nulling_joins=nulling,
                    effective_nullability=nullability,
                )
            )
        output = ProjectIRJoinRowOutput(
            occurrence=ProjectIROutputValueOccurrence(
                ref=ProjectIROutputValueRef(
                    scope=allocation.scope,
                    position=allocation.next_output_value_position,
                ),
                producer=node,
                anchor=anchor,
            ),
            row_shape=ProjectIRJoinedRowShape(
                relation=anchor, producer=node, fields=tuple(fields)
            ),
        )
        object.__setattr__(self, "use", condition.use)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "input_slots", slots)
        object.__setattr__(self, "input_uses", uses)
        object.__setattr__(self, "output", output)
        object.__setattr__(self, "field_inputs", origins)
        object.__setattr__(
            self,
            "ending_allocation",
            ProjectIRAllocationState(
                scope=allocation.scope,
                next_plan_node_position=allocation.next_plan_node_position + 1,
                next_output_value_position=allocation.next_output_value_position + 1,
                next_input_slot_position=allocation.next_input_slot_position + 2,
                next_use_position=allocation.next_use_position + 2,
            ),
        )
        object.__setattr__(self, "properties", ProjectCurrentJoinProperties(join=self))


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinProperties:
    join: ProjectCurrentBinaryJoin = field(repr=False)
    relational: ProjectIROutputRelationalProperties = field(init=False)
    null_extension: (
        ProjectIRProvidedNullExtension | ProjectIRJoinUnavailableProperty
    ) = field(init=False)
    ordering: ProjectIRJoinUnavailableProperty = field(init=False)

    def __post_init__(self) -> None:
        if type(self.join) is not ProjectCurrentBinaryJoin:
            raise ValueError("Current properties require the exact binary output.")
        relational = _properties(self.join)
        object.__setattr__(self, "relational", relational)
        witness = relational.grain.witness
        if (
            type(witness) is not ProjectCurrentJoinGrainWitness
            or witness.condition is not self.join.condition
            or witness.left is not self.join.left_input.grain
            or witness.right is not self.join.right_input.grain
        ):
            raise ValueError("Current grain requires exact condition/input evidence.")
        output = self.join.output
        nulling = (
            ProjectIRProvidedNullExtension(output=output)
            if any(item.nulling_joins for item in output.row_shape.fields)
            else ProjectIRJoinUnavailableProperty(
                output=output,
                property_slot=ProjectIRProvidedPropertySlot.NULL_EXTENSION,
            )
        )
        object.__setattr__(self, "null_extension", nulling)
        object.__setattr__(
            self,
            "ordering",
            ProjectIRJoinUnavailableProperty(
                output=output,
                property_slot=ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING,
            ),
        )


def _properties(join: ProjectCurrentBinaryJoin) -> ProjectIROutputRelationalProperties:
    if join.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}:
        return _left_subset_properties(join)
    left, right, output = join.left_input, join.right_input, join.output
    fields = _field_occurrences(output)
    left_classes, left_images = _classes_for_output(
        old=left.value_classes, output=output, fields=fields, offset=0
    )
    right_classes, right_images = _classes_for_output(
        old=right.value_classes, output=output, fields=fields, offset=len(left.fields)
    )
    classes = (*left_classes, *right_classes)
    kind = join.kind
    left_nulling = kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
    right_nulling = kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}
    left_keys = tuple(
        _image_key(
            key,
            left_images,
            classes,
            output=output,
            force_lax=left_nulling,
            support=join,
        )
        for key in left.keys
    )
    right_keys = tuple(
        _image_key(
            key,
            right_images,
            classes,
            output=output,
            force_lax=right_nulling,
            support=join,
        )
        for key in right.keys
    )
    base = join.condition.base_guarantee
    refined = join.condition.refinement_guarantee
    forward_at_most_one = (
        (
            refined is not None
            and refined.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        )
        or (
            refined is None
            and base is not None
            and base.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        )
    ) or right.grain.state is ProjectGrainBasisState.GLOBAL
    source_is_key = False
    reverse_at_most_one = left.grain.state is ProjectGrainBasisState.GLOBAL
    if base is not None and len(join.condition.environment.source_candidates) == 1:
        source = join.condition.environment.source_candidates[0]
        matched = tuple(
            member
            for value_class in base.source_matched_classes
            for member in value_class.members
        )
        positions = {
            position
            for position, (binding, original) in enumerate(join.left_fields)
            if binding is source and any(original is member for member in matched)
        }
        source_classes = _ordered_classes(
            tuple(
                value_class
                for value_class in left_classes
                if any(
                    member.field_position in positions for member in value_class.members
                )
            ),
            classes,
        )
        source_is_key = bool(source_classes) and any(
            set(key.determinants) == set(source_classes) for key in left_keys
        )
        reverse = tuple(
            item
            for item in join.condition.root.uses.index.by_declaration.get(
                base.direction.declaration, ()
            )
            if item.source_output is base.target_output
            and item.target_output is base.source_output
        )
        reverse_at_most_one |= (
            source_is_key
            and len(reverse) == 1
            and reverse[0].maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        )
    keys = list(left_keys) if forward_at_most_one else []
    if reverse_at_most_one:
        keys.extend(right_keys)
    for lhs in left_keys:
        for rhs in right_keys:
            determinants = _ordered_classes(
                (*lhs.determinants, *rhs.determinants), classes
            )
            strict = (
                lhs.strength is ProjectRowUniquenessStrength.STRICT
                and rhs.strength is ProjectRowUniquenessStrength.STRICT
            ) or all(_all_non_null(item) for item in determinants)
            keys.append(
                ProjectIROutputCandidateKey(
                    output=output,
                    determinants=determinants,
                    strength=ProjectRowUniquenessStrength.STRICT
                    if strict
                    else ProjectRowUniquenessStrength.LAX,
                    supports=(lhs, rhs, join),
                )
            )
    frontier = _frontier(tuple(keys))
    inherited = tuple(
        image
        for properties, images, weaken in (
            (left, left_images, left_nulling),
            (right, right_images, right_nulling),
        )
        for fact in properties.fds
        if (
            image := _image_fd(
                fact,
                images,
                classes,
                output=output,
                strength=(
                    ProjectRowUniquenessStrength.LAX
                    if weaken
                    and (
                        kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
                        or not all(_all_non_null(item) for item in fact.determinants)
                    )
                    else fact.strength
                ),
                support=join,
            )
        )
        is not None
    )
    fds = _key_fds(output, classes, frontier, inherited)
    grain, _ = _grain(
        join_identity=None,
        output=output,
        left=left.grain,
        right=right.grain,
        left_use=join.input_uses[0],
        right_use=join.input_uses[1],
        source_factors=None,
        nulling=(join.node.ref,) if right_nulling else (),
        left_nulling=(join.node.ref,) if left_nulling else (),
        forward_at_most_one=forward_at_most_one,
        reverse_at_most_one=reverse_at_most_one,
        witness=ProjectCurrentJoinGrainWitness(
            condition=join.condition, left=left.grain, right=right.grain
        ),
        origin_set=(
            None
            if left.grain.origin_set is right.grain.origin_set
            else ProjectCompositeGrainOriginAuthority(
                witness=join.condition,
                left=left.grain.origin_set,
                right=right.grain.origin_set,
            )
        ),
        preserve_nested_inputs=True,
        named_left_input=type(left.output) is not ProjectIRJoinRowOutput,
        empty_state=(
            ProjectGrainBasisState.UNKNOWN
            if kind is AuthoredJoinKind.FULL
            and left.grain.state is ProjectGrainBasisState.GLOBAL
            and right.grain.state is ProjectGrainBasisState.GLOBAL
            else ProjectGrainBasisState.GLOBAL
        ),
    )
    return ProjectIROutputRelationalProperties(
        output=output,
        fields=fields,
        value_classes=classes,
        keys=frontier,
        fds=fds,
        fd_index=_compile_output_fd_index(output, classes, fds),
        grain=grain,
    )


def _left_subset_properties(
    join: ProjectCurrentBinaryJoin,
) -> ProjectIROutputRelationalProperties:
    left, output = join.left_input, join.output
    fields = _field_occurrences(output)
    classes, images = _classes_for_output(
        old=left.value_classes, output=output, fields=fields, offset=0
    )
    keys = tuple(
        _image_key(key, images, classes, output=output, force_lax=False, support=join)
        for key in left.keys
    )
    fds = tuple(
        image
        for fact in left.fds
        if (
            image := _image_fd(
                fact,
                images,
                classes,
                output=output,
                strength=fact.strength,
                support=join,
            )
        )
        is not None
    )
    grain, _ = _grain(
        join_identity=None,
        output=output,
        left=left.grain,
        right=join.right_input.grain,
        left_use=join.input_uses[0],
        right_use=join.input_uses[1],
        source_factors=None,
        nulling=(),
        forward_at_most_one=False,
        reverse_at_most_one=False,
        witness=ProjectCurrentJoinGrainWitness(
            condition=join.condition, left=left.grain, right=join.right_input.grain
        ),
        preserve_nested_inputs=True,
        named_left_input=type(left.output) is not ProjectIRJoinRowOutput,
        left_only=True,
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


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinRegion:
    conditions: ProjectJoinConditionSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    starting_allocation: ProjectIRAllocationState
    input_scope: ProjectCurrentJoinInputScope | None = field(default=None, repr=False)
    input_properties: tuple[ProjectIROutputRelationalProperties, ...] = field(
        default=(), repr=False
    )
    operative: tuple[ProjectJoinCondition, ...] = field(default=(), repr=False)
    joins: tuple[ProjectCurrentBinaryJoin | ProjectIRBinaryJoinOccurrence, ...] = field(
        init=False
    )
    join_properties: tuple[
        ProjectCurrentJoinProperties | ProjectIRJoinOutputProperties, ...
    ] = field(init=False)
    ending_allocation: ProjectIRAllocationState = field(init=False)
    final_properties: ProjectCurrentJoinProperties | ProjectIRJoinOutputProperties = (
        field(init=False)
    )
    binding_introductions: tuple[ProjectIRJoinInputUseOccurrence, ...] = field(
        init=False
    )
    hidden_introductions: tuple[ProjectIRJoinInputUseOccurrence, ...] = field(
        init=False
    )

    def __post_init__(self) -> None:
        if type(self.conditions) is not ProjectJoinConditionSet or not any(
            self.ledger is item for item in self.conditions.uses.ledgers
        ):
            raise ValueError("Current JOIN region requires exact use roots.")
        conditions = tuple(
            item for item in self.conditions.entries if item.ledger is self.ledger
        )
        if self.input_scope is not None:
            if (
                self.input_scope.uses is not self.conditions.uses
                or self.input_scope.ledger is not self.ledger
                or len(self.input_properties) != len(self.ledger.bindings)
                or len(self.operative) != len(conditions)
                or any(
                    new.root is not self.conditions or new.use is not old.use
                    for new, old in zip(self.operative, conditions, strict=True)
                )
            ):
                raise ValueError(
                    "Current region requires exact operative condition/input membership."
                )
            for binding, input_properties in zip(
                self.input_scope.bindings, self.input_properties, strict=True
            ):
                require_current_input_properties(binding, input_properties)
            conditions = self.operative
            for position, condition in enumerate(conditions):
                if condition.inputs is not None and (
                    len(condition.inputs.prefix) != position
                    or any(
                        actual is not retained
                        for actual, retained in zip(
                            condition.inputs.prefix, conditions[:position], strict=True
                        )
                    )
                ):
                    raise ValueError(
                        "Current JOIN requires its exact operative prefix conditions."
                    )
        elif self.input_properties or self.operative:
            raise ValueError("Current input overrides require their exact scope.")
        if (
            len(conditions) != len(self.ledger.uses)
            or not conditions
            or any(
                not item.ready
                or item.use.kind
                not in {
                    AuthoredJoinKind.INNER,
                    AuthoredJoinKind.LEFT,
                    AuthoredJoinKind.CROSS,
                    AuthoredJoinKind.RIGHT,
                    AuthoredJoinKind.FULL,
                    AuthoredJoinKind.SEMI,
                    AuthoredJoinKind.ANTI,
                }
                for item in conditions
            )
        ):
            raise ValueError(
                "Current JOIN region requires every ready supported occurrence."
            )
        base = self.ledger.bindings[0]
        left = base.output if self.input_scope is None else self.input_properties[0]
        if left is None:
            raise ValueError("Current JOIN region requires an available base input.")
        origins: tuple[ProjectCurrentFieldInput, ...] = tuple(
            (base, member)
            for member in (
                left.fields
                if self.input_scope is None
                else self.input_scope.bindings[0].fields
            )
        )
        positions = {id(base): tuple(range(len(left.fields)))}
        allocation = self.starting_allocation
        built: list[ProjectCurrentBinaryJoin | ProjectIRBinaryJoinOccurrence] = []
        properties: list[
            ProjectCurrentJoinProperties | ProjectIRJoinOutputProperties
        ] = []
        introductions: list[ProjectIRJoinInputUseOccurrence] = []
        hidden: list[ProjectIRJoinInputUseOccurrence] = []
        for position, condition in enumerate(conditions):
            right = (
                condition.use.target_binding.output
                if self.input_scope is None
                else self.input_properties[position + 1]
            )
            if right is None:
                raise ValueError(
                    "Current JOIN region requires an available right input."
                )
            if condition.mode in {"M1", "M2"} and condition.use.kind in {
                AuthoredJoinKind.INNER,
                AuthoredJoinKind.LEFT,
            }:
                use = condition.effective_use
                if not isinstance(use, ProjectConcreteJoinUse):
                    raise ValueError(
                        "Current relationship path requires exact available use evidence."
                    )
                source_positions = positions[id(use.source_binding)]
                source_nulling = ()
                source_factors = None
                if isinstance(left.output, ProjectIRJoinRowOutput):
                    source_fields = tuple(
                        left.output.row_shape.fields[i] for i in source_positions
                    )
                    source_nulling = tuple(
                        dict.fromkeys(
                            ref for item in source_fields for ref in item.nulling_joins
                        )
                    )
                    intro = source_fields[0].introduction_use.ref
                    source_factors = tuple(
                        item
                        for item in left.grain.active
                        if isinstance(item, ProjectJoinGrainFactorIdentity)
                        and item.introduction_use == intro
                    )
                for ordinal, step in enumerate(use.path.steps):
                    step_right = step.guarantee.target_output
                    terminal = ordinal == len(use.path.steps) - 1
                    if terminal and step_right is not right:
                        raise ValueError(
                            "Current relationship cannot promote a changed effective endpoint."
                        )
                    origin_set = (
                        None
                        if left.grain.origin_set is step_right.grain.origin_set
                        else ProjectCompositeGrainOriginAuthority(
                            left=left.grain.origin_set,
                            right=step_right.grain.origin_set,
                            witness=condition,
                        )
                    )
                    (
                        node,
                        prop,
                        ending,
                        right_positions,
                        source_nulling,
                        source_factors,
                    ) = _build_join(
                        uses=self.conditions.uses,
                        use=use,
                        path_step=step,
                        left=left,
                        right=step_right,
                        source_positions=source_positions,
                        source_nulling=source_nulling,
                        source_factors=source_factors,
                        allocation=allocation,
                        origin_set=origin_set,
                    )
                    built.append(node)
                    properties.append(prop)
                    originals = (
                        (
                            step_right.fields
                            if self.input_scope is None
                            else self.input_scope.bindings[position + 1].fields
                        )
                        if terminal
                        else step_right.fields
                    )
                    origins = (
                        *origins,
                        *(
                            (condition.use.target_binding if terminal else None, member)
                            for member in originals
                        ),
                    )
                    if not terminal:
                        hidden.append(node.input_uses[1])
                    left, allocation, source_positions = (
                        prop.relational,
                        ending,
                        right_positions,
                    )
                positions[id(condition.use.target_binding)] = source_positions
            else:
                prefix = (
                    None
                    if not built
                    else _CurrentPrefix(
                        condition=conditions[position - 1],
                        join=built[-1],
                        properties=properties[-1],
                        origins=origins,
                        allocation=allocation,
                    )
                )
                offset = len(left.fields)
                node = ProjectCurrentBinaryJoin(
                    condition=condition,
                    left_input=left,
                    right_input=right,
                    left_fields=origins,
                    starting_allocation=allocation,
                    prefix=prefix,
                    input_scope=self.input_scope,
                )
                built.append(node)
                properties.append(node.properties)
                origins, left, allocation = (
                    node.field_inputs,
                    node.properties.relational,
                    node.ending_allocation,
                )
                if node.kind not in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}:
                    positions[id(condition.use.target_binding)] = tuple(
                        range(offset, offset + len(right.fields))
                    )
            if not introductions:
                introductions.append(built[0].input_uses[0])
            introductions.append(built[-1].input_uses[1])
        object.__setattr__(self, "joins", tuple(built))
        object.__setattr__(self, "join_properties", tuple(properties))
        object.__setattr__(self, "ending_allocation", allocation)
        object.__setattr__(self, "final_properties", properties[-1])
        object.__setattr__(self, "binding_introductions", tuple(introductions))
        object.__setattr__(self, "hidden_introductions", tuple(hidden))

    def introduction(
        self, binding: ProjectRelationBindingOccurrence
    ) -> ProjectIRJoinInputUseOccurrence:
        if not any(binding is retained for retained in self.ledger.bindings):
            raise ValueError("Current introduction requires exact binding membership.")
        return self.binding_introductions[binding.identity.binding_position]
