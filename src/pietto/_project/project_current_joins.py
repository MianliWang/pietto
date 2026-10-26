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
    ProjectIRJoinUnavailableProperty,
    _all_non_null,
    _classes_for_output,
    _grain,
    _is_join_factor,
    _image_fd,
    _image_key,
    _ordered_classes,
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
    resolved_matching_keys,
)
from pietto._project.project_relationship_uses import (
    ProjectNonConcreteJoinUse,
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
    join: ProjectCurrentBinaryJoin
    properties: ProjectCurrentJoinProperties
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
        if self.origins is not self.join.field_inputs:
            raise ValueError(
                "Current prefix must retain exact output field-role authority."
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
    use: ProjectNonConcreteJoinUse = field(init=False, repr=False)
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
            kind is AuthoredJoinKind.CROSS
            and condition.mode == "M5"
            and condition.expression is None
            and condition.scope is None
        ) or (kind is not AuthoredJoinKind.CROSS and condition.mode == "M3")
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
            binding, original = origins[position]
            nullability = resolved_join_field_nullability(
                kind,
                member.effective_nullability,
                bool(nulling),
                (id(binding), id(original)) in rejected,
            )
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


def resolved_join_field_nullability(kind, incoming, null_extended, rejected):
    """Original current field law; retained NULL provenance is never cleared."""
    return (
        ProjectRowFieldNullability.NULLABLE
        if null_extended
        else ProjectRowFieldNullability.NON_NULL
        if kind is AuthoredJoinKind.INNER and rejected
        else incoming
    )


def current_forward_at_most_one(condition: ProjectJoinCondition) -> bool:
    """Each left row has at most one RHS match: a key of the JOIN's target is
    matched by its `on`."""
    return any(
        proof.binding is condition.use.target_binding for proof in condition.key_matches
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
    forward_at_most_one = (
        current_forward_at_most_one(join.condition)
        or right.grain.state is ProjectGrainBasisState.GLOBAL
    )
    reverse_at_most_one = left.grain.state is ProjectGrainBasisState.GLOBAL
    # Bound the accumulated left row, not one named input inside that row.
    matched_left_positions = {
        position
        for equality in join.condition.mandatory_equalities
        for own, other in (
            (equality.left, equality.right),
            (equality.right, equality.left),
        )
        if own.binding is not join.condition.use.target_binding
        and other.binding is join.condition.use.target_binding
        for position, (binding, original) in enumerate(join.left_fields)
        if binding is own.binding and original is own.input_field
    }
    matched_left_classes = tuple(
        group
        for group in left.value_classes
        if any(
            member.field_position in matched_left_positions for member in group.members
        )
    )
    reverse_at_most_one |= bool(resolved_matching_keys(left.keys, matched_left_classes))
    local_reverse_sources = ()
    if (
        not reverse_at_most_one
        and kind in {AuthoredJoinKind.INNER, AuthoredJoinKind.RIGHT}
        and type(left.output) is ProjectIRJoinRowOutput
    ):
        introductions = {
            current.introduction_use.ref
            for (binding, _original), current in zip(
                join.left_fields, left.output.row_shape.fields, strict=True
            )
            if any(proof.binding is binding for proof in join.condition.key_matches)
        }
        local_reverse_sources = _local_reverse_factor_groups(left.grain, introductions)
    return resolved_join_properties(
        kind=kind,
        left=left,
        right=right,
        output=output,
        input_uses=join.input_uses,
        node_ref=join.node.ref,
        forward_at_most_one=forward_at_most_one,
        reverse_at_most_one=reverse_at_most_one,
        witness=join,
        grain_witness=ProjectCurrentJoinGrainWitness(
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
        named_left_input=type(left.output) is not ProjectIRJoinRowOutput,
        prepared=(fields, classes, left_images, right_images, left_keys, right_keys),
        local_reverse_sources=local_reverse_sources,
    )


def resolved_join_properties(
    *,
    kind,
    left,
    right,
    output,
    input_uses,
    node_ref,
    forward_at_most_one,
    reverse_at_most_one,
    witness,
    grain_witness,
    origin_set,
    named_left_input,
    prepared=None,
    local_reverse_sources=(),
) -> ProjectIROutputRelationalProperties:
    """Original current JOIN key/FD/grain algebra over resolved input images."""
    left_nulling = kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
    right_nulling = kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}
    if prepared is None:
        fields = _field_occurrences(output)
        left_classes, left_images = _classes_for_output(
            old=left.value_classes, output=output, fields=fields, offset=0
        )
        right_classes, right_images = _classes_for_output(
            old=right.value_classes,
            output=output,
            fields=fields,
            offset=len(left.fields),
        )
        classes = (*left_classes, *right_classes)
        left_keys = tuple(
            _image_key(
                k,
                left_images,
                classes,
                output=output,
                force_lax=left_nulling,
                support=witness,
            )
            for k in left.keys
        )
        right_keys = tuple(
            _image_key(
                k,
                right_images,
                classes,
                output=output,
                force_lax=right_nulling,
                support=witness,
            )
            for k in right.keys
        )
    else:
        fields, classes, left_images, right_images, left_keys, right_keys = prepared
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
                    supports=(lhs, rhs, witness),
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
                support=witness,
            )
        )
        is not None
    )
    fds = _key_fds(output, classes, frontier, inherited)
    grain, _ = _grain(
        output=output,
        left=left.grain,
        right=right.grain,
        left_use=input_uses[0],
        right_use=input_uses[1],
        source_factors=None,
        nulling=(node_ref,) if right_nulling else (),
        left_nulling=(node_ref,) if left_nulling else (),
        forward_at_most_one=forward_at_most_one,
        reverse_at_most_one=reverse_at_most_one,
        local_reverse_sources=local_reverse_sources,
        witness=grain_witness,
        origin_set=origin_set,
        preserve_nested_inputs=True,
        named_left_input=named_left_input,
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
    return resolved_left_subset_properties(
        left=join.left_input,
        right=join.right_input,
        output=join.output,
        input_uses=join.input_uses,
        witness=join,
        grain_witness=ProjectCurrentJoinGrainWitness(
            condition=join.condition,
            left=join.left_input.grain,
            right=join.right_input.grain,
        ),
        origin_set=None,
        named_left_input=type(join.left_input.output) is not ProjectIRJoinRowOutput,
    )


def resolved_left_subset_properties(
    *,
    left,
    right,
    output,
    input_uses,
    witness,
    grain_witness,
    origin_set,
    named_left_input,
) -> ProjectIROutputRelationalProperties:
    """Original SEMI/ANTI left-subset property kernel over resolved inputs."""
    fields = _field_occurrences(output)
    classes, images = _classes_for_output(
        old=left.value_classes, output=output, fields=fields, offset=0
    )
    keys = tuple(
        _image_key(
            key, images, classes, output=output, force_lax=False, support=witness
        )
        for key in left.keys
    )
    # Two left FDs whose dependents differ only in order image to one FD,
    # merged once as every other JOIN kernel and the composed image merge it.
    fds = _key_fds(
        output,
        classes,
        (),
        tuple(
            image
            for fact in left.fds
            if (
                image := _image_fd(
                    fact,
                    images,
                    classes,
                    output=output,
                    strength=fact.strength,
                    support=witness,
                )
            )
            is not None
        ),
    )
    grain, _ = _grain(
        output=output,
        left=left.grain,
        right=right.grain,
        left_use=input_uses[0],
        right_use=input_uses[1],
        source_factors=None,
        nulling=(),
        forward_at_most_one=False,
        reverse_at_most_one=False,
        witness=grain_witness,
        origin_set=origin_set,
        preserve_nested_inputs=True,
        named_left_input=named_left_input,
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
    joins: tuple[ProjectCurrentBinaryJoin, ...] = field(init=False)
    join_properties: tuple[ProjectCurrentJoinProperties, ...] = field(init=False)
    ending_allocation: ProjectIRAllocationState = field(init=False)
    final_properties: ProjectCurrentJoinProperties = field(init=False)
    binding_introductions: tuple[ProjectIRJoinInputUseOccurrence, ...] = field(
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
        allocation = self.starting_allocation
        built: list[ProjectCurrentBinaryJoin] = []
        properties: list[ProjectCurrentJoinProperties] = []
        introductions: list[ProjectIRJoinInputUseOccurrence] = []
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
            if not introductions:
                introductions.append(built[0].input_uses[0])
            introductions.append(built[-1].input_uses[1])
        object.__setattr__(self, "joins", tuple(built))
        object.__setattr__(self, "join_properties", tuple(properties))
        object.__setattr__(self, "ending_allocation", allocation)
        object.__setattr__(self, "final_properties", properties[-1])
        object.__setattr__(self, "binding_introductions", tuple(introductions))

    def introduction(
        self, binding: ProjectRelationBindingOccurrence
    ) -> ProjectIRJoinInputUseOccurrence:
        if not any(binding is retained for retained in self.ledger.bindings):
            raise ValueError("Current introduction requires exact binding membership.")
        return self.binding_introductions[binding.identity.binding_position]


@dataclass(frozen=True, slots=True, eq=False)
class CompiledPropertyInputUse:
    ref: object


def _compiled_matched_classes(records, record, incoming, side):
    """The value classes of one input that a compiled JOIN's equalities match."""
    positions = tuple(
        records[
            records[records[a].get("left" if side == 0 else "right")].get("port")
        ].get("ordinal")
        for a in record.get("equalities")
    )
    return tuple(
        c
        for c in incoming.value_classes
        if any(m.field_position in positions for m in c.members)
    )


def _compiled_predicate_matched_classes(records, record, incoming, side):
    """Project the exact positive ON equalities onto one current JOIN side."""
    from pietto._project.project_compiled_schema import predicate_equalities

    uses = record.get("inputs")
    positions = set()
    for equality in predicate_equalities(records, record):
        operands = equality.get("operands")
        for own, other in (operands, operands[::-1]):
            if own.kind == other.kind == "read" and (
                records[own].get("use") == uses[side]
                and records[other].get("use") == uses[1 - side]
            ):
                positions.add(records[records[own].get("port")].get("ordinal"))
    return tuple(
        group
        for group in incoming.value_classes
        if any(member.field_position in positions for member in group.members)
    )


def compiled_forward_at_most_one(records, record, right) -> bool:
    """`current_forward_at_most_one` for a compiled JOIN: a key of its right
    input is matched by the JOIN's equalities."""
    matched = _compiled_matched_classes(records, record, right, 1)
    predicate_matched = _compiled_predicate_matched_classes(records, record, right, 1)
    return bool(resolved_matching_keys(right.keys, matched)) or bool(
        resolved_matching_keys(right.keys, predicate_matched)
    )


def _local_reverse_factor_groups(grain, introductions):
    """Every matched input's complete active factor group, in grain order."""
    groups = {}
    for factor in grain.active:
        if _is_join_factor(factor) and factor.introduction_use in introductions:
            groups.setdefault(factor.introduction_use, []).append(factor)
    return tuple(tuple(factors) for factors in groups.values())


def compiled_local_reverse_sources(records, record, left, built, references):
    """Re-derive local input keys without bounding the accumulated left row."""
    from pietto._project.project_compiled_schema import _carried, predicate_equalities

    if record.get("law") != "current" or record.get("kind") not in {"inner", "right"}:
        return ()
    left_use, right_use = record.get("inputs")
    fields = {}
    for equality in predicate_equalities(records, record):
        operands = equality.get("operands")
        for own, other in (operands, operands[::-1]):
            if (
                own.kind != "read"
                or other.kind != "read"
                or (
                    records[own].get("use") != left_use
                    or records[other].get("use") != right_use
                )
            ):
                continue
            binding, chain = _carried(
                records, record.get("owner"), records[own].get("port")
            )
            if chain:
                fields.setdefault(left_use if binding is None else binding, set()).add(
                    chain[-1].get("ordinal")
                )
    introductions = set()
    for use, positions in fields.items():
        properties = built[records[use].get("producer")].properties.relational
        matched = tuple(
            group
            for group in properties.value_classes
            if any(member.field_position in positions for member in group.members)
        )
        if resolved_matching_keys(properties.keys, matched):
            introductions.add(references[use])
    return _local_reverse_factor_groups(left.grain, introductions)


def compiled_join_properties(completed, record, output, built, origin, references):
    """Bind compiled inputs to the existing current JOIN kernel."""
    records = completed.root.records
    uses = tuple(records[a] for a in record.get("inputs"))
    left, right = (built[u.get("producer")].properties.relational for u in uses)
    input_uses = tuple(CompiledPropertyInputUse(references[u.address]) for u in uses)
    kind = AuthoredJoinKind(record.get("kind"))
    named_left = uses[0].get("producer").kind != "join"
    if kind in (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI):
        return resolved_left_subset_properties(
            left=left,
            right=right,
            output=output,
            input_uses=input_uses,
            witness=record,
            grain_witness=record,
            origin_set=origin,
            named_left_input=named_left,
        )

    matched_left = _compiled_matched_classes(records, record, left, 0)
    matched_right = _compiled_matched_classes(records, record, right, 1)
    forward_keys = (
        resolved_matching_keys(right.keys, matched_right) if matched_right else ()
    )
    reverse_keys = (
        resolved_matching_keys(left.keys, matched_left) if matched_left else ()
    )
    source_is_key = bool(matched_left) and any(
        set(k.determinants) == set(matched_left) for k in left.keys
    )
    predicate_forward_keys = resolved_matching_keys(
        right.keys, _compiled_predicate_matched_classes(records, record, right, 1)
    )
    predicate_reverse_keys = resolved_matching_keys(
        left.keys, _compiled_predicate_matched_classes(records, record, left, 0)
    )
    return resolved_join_properties(
        kind=kind,
        left=left,
        right=right,
        output=output,
        input_uses=input_uses,
        node_ref=references[record.address],
        forward_at_most_one=bool(forward_keys)
        or bool(predicate_forward_keys)
        or right.grain.state is ProjectGrainBasisState.GLOBAL,
        reverse_at_most_one=(source_is_key and bool(reverse_keys))
        or bool(predicate_reverse_keys)
        or left.grain.state is ProjectGrainBasisState.GLOBAL,
        witness=record,
        grain_witness=record,
        origin_set=origin,
        named_left_input=named_left,
        local_reverse_sources=compiled_local_reverse_sources(
            records, record, left, built, references
        ),
    )
