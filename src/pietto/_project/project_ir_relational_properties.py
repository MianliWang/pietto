"""Private output-occurrence key, FD, and intrinsic-grain transfer."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from types import MappingProxyType
from typing import cast

from pietto._project.model import ProjectRowField, ProjectRowFieldNullability
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectGrainOriginSet,
)
from pietto._project.project_ir import (
    ProjectIROperatorFlowUseOccurrence,
    ProjectIRPlanNodeOccurrence,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRJoinedRowField,
    ProjectIRRelationRowOutput,
)
from pietto._project.project_ir_verification import ProjectIRAnalysisBundle
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto.ast_nodes import DottedNameExpr, NameExpr

__all__: tuple[str, ...] = ()

type ProjectIRRelationalRowOutput = ProjectIRRelationRowOutput | ProjectIRJoinRowOutput
_RELATIONAL_ROW_OUTPUT_TYPES = (ProjectIRRelationRowOutput, ProjectIRJoinRowOutput)


class ProjectIRGrainComparisonStatus(StrEnum):
    EQUAL = "equal"
    LEFT_FINER = "left_finer"
    RIGHT_FINER = "right_finer"
    INCOMPARABLE = "incomparable"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputFieldOccurrence:
    output: ProjectIRRelationalRowOutput
    field_position: int
    evidence: ProjectRowField = field(repr=False)
    effective_nullability: ProjectRowFieldNullability = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) not in _RELATIONAL_ROW_OUTPUT_TYPES:
            raise TypeError("Output field requires an exact relation-row output.")
        row_fields = self.output.row_shape.fields
        if (
            type(self.field_position) is not int
            or self.field_position < 0
            or self.field_position >= len(row_fields)
            or row_fields[self.field_position].evidence is not self.evidence
        ):
            raise ValueError("Output field must retain exact row-shape order.")
        shape_field = row_fields[self.field_position]
        object.__setattr__(
            self,
            "effective_nullability",
            (
                shape_field.effective_nullability
                if type(shape_field) is ProjectIRJoinedRowField
                else self.evidence.nullability
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIROutputValueClass:
    output: ProjectIRRelationalRowOutput
    members: tuple[ProjectIROutputFieldOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.output) not in _RELATIONAL_ROW_OUTPUT_TYPES or not self.members:
            raise ValueError("Value class requires one exact output and members.")
        if any(member.output is not self.output for member in self.members):
            raise ValueError("Value-class members must share one output occurrence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputCandidateKey:
    output: ProjectIRRelationalRowOutput
    determinants: tuple[ProjectIROutputValueClass, ...]
    strength: ProjectRowUniquenessStrength
    supports: tuple[object, ...] = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if (
            type(self.output) not in _RELATIONAL_ROW_OUTPUT_TYPES
            or not self.determinants
            or any(item.output is not self.output for item in self.determinants)
            or not self.supports
        ):
            raise ValueError("Output key requires exact determinants and support.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputValueFD:
    output: ProjectIRRelationalRowOutput
    determinants: tuple[ProjectIROutputValueClass, ...]
    dependents: tuple[ProjectIROutputValueClass, ...]
    strength: ProjectRowUniquenessStrength
    supports: tuple[object, ...] = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if (
            type(self.output) not in _RELATIONAL_ROW_OUTPUT_TYPES
            or not self.determinants
            or not self.dependents
            or any(
                item.output is not self.output
                for item in (*self.determinants, *self.dependents)
            )
            or set(self.determinants) & set(self.dependents)
            or not self.supports
        ):
            raise ValueError("Output FD requires exact non-trivial local classes.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRCompiledOutputFDRule:
    fact: ProjectIROutputValueFD = field(repr=False, compare=False, hash=False)
    lhs_mask: int
    rhs_mask: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputFDIndex:
    output: ProjectIRRelationalRowOutput
    universe: tuple[ProjectIROutputValueClass, ...]
    facts: tuple[ProjectIROutputValueFD, ...]
    positions: Mapping[ProjectIROutputValueClass, int] = field(
        repr=False, compare=False, hash=False
    )
    strict_rules: tuple[ProjectIRCompiledOutputFDRule, ...]
    lax_rules: tuple[ProjectIRCompiledOutputFDRule, ...]
    incidents: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if any(item.output is not self.output for item in self.universe):
            raise ValueError("FD index universe must be output-local.")
        expected = {item: position for position, item in enumerate(self.universe)}
        if dict(self.positions) != expected:
            raise ValueError("FD index positions must retain universe order.")
        object.__setattr__(self, "positions", MappingProxyType(expected))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputValueClassSet:
    index: ProjectIROutputFDIndex
    classes: tuple[ProjectIROutputValueClass, ...]
    mask: int = field(init=False)

    def __post_init__(self) -> None:
        if any(item not in self.index.positions for item in self.classes):
            raise ValueError("Value-class set requires the exact FD universe.")
        mask = sum(1 << self.index.positions[item] for item in self.classes)
        expected = tuple(
            item
            for position, item in enumerate(self.index.universe)
            if mask & (1 << position)
        )
        if expected != self.classes:
            raise ValueError("Value-class set must retain exact universe order.")
        object.__setattr__(self, "mask", mask)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputFDProofStep:
    fact: ProjectIROutputValueFD = field(repr=False, compare=False, hash=False)
    derived: tuple[ProjectIROutputValueClass, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputStrictClosure:
    seed: ProjectIROutputValueClassSet
    classes: ProjectIROutputValueClassSet
    witness: tuple[ProjectIROutputFDProofStep, ...]


class ProjectIROutputDeterminationStatus(StrEnum):
    PROVEN = "proven"
    NOT_PROVEN = "not_proven"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputDeterminationResult:
    seed: ProjectIROutputValueClassSet
    requested: ProjectIROutputValueClassSet
    closure: ProjectIROutputStrictClosure
    status: ProjectIROutputDeterminationStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProvidedIntrinsicGrain:
    output: ProjectIRRelationalRowOutput
    state: ProjectGrainBasisState
    factors: tuple[ProjectGrainDomainFactor, ...]
    active: tuple[ProjectGrainFactorIdentity, ...]
    dependencies: tuple[ProjectGrainDependencyFact, ...]
    origin_set: ProjectGrainOriginSet = field(repr=False, compare=False, hash=False)
    witness: object = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.output) not in _RELATIONAL_ROW_OUTPUT_TYPES or self.state not in {
            ProjectGrainBasisState.FACTORIZED,
            ProjectGrainBasisState.GLOBAL,
        }:
            raise ValueError("Provided grain requires one concrete output state.")
        identities = tuple(factor.identity for factor in self.factors)
        if any(item not in identities for item in self.active):
            raise ValueError("Active grain factors require the exact local universe.")
        if self.state is ProjectGrainBasisState.GLOBAL and self.active:
            raise ValueError("GLOBAL provided grain has no active factors.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputRelationalProperties:
    output: ProjectIRRelationalRowOutput
    fields: tuple[ProjectIROutputFieldOccurrence, ...]
    value_classes: tuple[ProjectIROutputValueClass, ...]
    keys: tuple[ProjectIROutputCandidateKey, ...]
    fds: tuple[ProjectIROutputValueFD, ...]
    fd_index: ProjectIROutputFDIndex
    grain: ProjectIRProvidedIntrinsicGrain

    def __post_init__(self) -> None:
        if (
            self.grain.output is not self.output
            or self.fd_index.output is not self.output
            or any(
                item.output is not self.output
                for item in (*self.fields, *self.value_classes, *self.keys, *self.fds)
            )
        ):
            raise ValueError("Relational properties require one output occurrence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRelationalPropertyStage:
    origins: ProjectGrainOriginSet = field(repr=False, compare=False, hash=False)
    analyses: ProjectIRAnalysisBundle = field(repr=False, compare=False, hash=False)
    outputs: tuple[ProjectIROutputRelationalProperties, ...]

    def __post_init__(self) -> None:
        if self.origins.evaluation is not self.analyses.stage:
            raise ValueError("Relational stage requires exact shared snapshot roots.")
        expected = tuple(
            output
            for node in self.analyses.topological_order
            for output in self.analyses.stage.project_plan.structural_stage.outputs
            if output.producer is node
            for typed in self.analyses.stage.project_plan.concrete_fragments
            for output_property in typed.property_stage.outputs
            if output_property.occurrence is output
            and type(output_property) is ProjectIRRelationRowOutput
            for output in (output_property,)
        )
        if len(self.outputs) != len(expected) or any(
            item.output is not output
            for item, output in zip(self.outputs, expected, strict=True)
        ):
            raise ValueError(
                "Relational stage must cover topological row outputs once."
            )


def _row_output(
    analyses: ProjectIRAnalysisBundle,
    node: ProjectIRPlanNodeOccurrence,
) -> ProjectIRRelationRowOutput:
    matches = tuple(
        output
        for fragment in analyses.stage.project_plan.concrete_fragments
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence.producer is node
    )
    if len(matches) != 1:
        raise ValueError("Concrete operator requires one exact row output.")
    return matches[0]


def _operator(analyses: ProjectIRAnalysisBundle, node: ProjectIRPlanNodeOccurrence):
    matches = tuple(
        operator
        for fragment in analyses.stage.project_plan.concrete_fragments
        for operator in fragment.logical_stage.operators
        if operator.node is node
    )
    if len(matches) != 1:
        raise ValueError("Concrete output requires one exact logical operator.")
    return matches[0]


def _incoming(
    analyses: ProjectIRAnalysisBundle,
    node: ProjectIRPlanNodeOccurrence,
    built: dict[object, ProjectIROutputRelationalProperties],
) -> ProjectIROutputRelationalProperties | None:
    flows = tuple(
        use
        for use in analyses.stage.project_plan.structural_stage.uses
        if type(use) is ProjectIROperatorFlowUseOccurrence and use.slot.consumer is node
    )
    if flows:
        if len(flows) != 1:
            raise ValueError("Unary operator requires one exact incoming flow.")
        return built.get(flows[0].output.ref)
    edges = tuple(
        edge
        for edge in analyses.stage.project_plan.cross_relation_edges
        if edge.input_slot.consumer is node
    )
    if edges:
        if len(edges) != 1:
            raise ValueError("Derived input requires one exact cross edge.")
        return built.get(edges[0].use.output.ref)
    return None


def _field_occurrences(output: ProjectIRRelationalRowOutput):
    return tuple(
        ProjectIROutputFieldOccurrence(
            output=output,
            field_position=position,
            evidence=item.evidence,
        )
        for position, item in enumerate(output.row_shape.fields)
    )


def _singleton_classes(output, fields):
    return tuple(
        ProjectIROutputValueClass(output=output, members=(item,)) for item in fields
    )


def _preserving_classes(
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIRRelationalRowOutput,
    fields: tuple[ProjectIROutputFieldOccurrence, ...],
):
    classes: list[ProjectIROutputValueClass] = []
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass | None] = {}
    used: set[int] = set()
    for old in incoming.value_classes:
        members = tuple(
            fields[member.field_position]
            for member in old.members
            if member.field_position < len(fields)
        )
        if members:
            image = ProjectIROutputValueClass(output=output, members=members)
            classes.append(image)
            images[old] = image
            used.update(item.field_position for item in members)
        else:
            images[old] = None
    classes.extend(
        ProjectIROutputValueClass(output=output, members=(item,))
        for item in fields
        if item.field_position not in used
    )
    classes.sort(key=lambda item: min(member.field_position for member in item.members))
    return tuple(classes), images


def _projection_images(
    incoming: ProjectIROutputRelationalProperties,
    operator: ProjectIRLogicalOperatorOccurrence,
    output: ProjectIRRelationalRowOutput,
    fields: tuple[ProjectIROutputFieldOccurrence, ...],
):
    members_by_old = {item: [] for item in incoming.value_classes}
    assigned: set[int] = set()
    for fact in operator.evidence.select_facts:
        if (
            fact.selected_output_ordinal >= len(fields)
            or len(fact.references) != 1
            or type(fact.item.expression) not in {NameExpr, DottedNameExpr}
        ):
            continue
        reference = fact.references[0]
        matches = tuple(
            old
            for old in incoming.value_classes
            if any(
                reference.input_field is member.evidence
                or fact.field is member.evidence
                for member in old.members
            )
        )
        if len(matches) == 1:
            member = fields[fact.selected_output_ordinal]
            members_by_old[matches[0]].append(member)
            assigned.add(member.field_position)
    classes: list[ProjectIROutputValueClass] = []
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass | None] = {}
    for old in incoming.value_classes:
        members = tuple(members_by_old[old])
        if members:
            image = ProjectIROutputValueClass(output=output, members=members)
            classes.append(image)
            images[old] = image
        else:
            images[old] = None
    classes.extend(
        ProjectIROutputValueClass(output=output, members=(item,))
        for item in fields
        if item.field_position not in assigned
    )
    classes.sort(key=lambda item: min(member.field_position for member in item.members))
    return tuple(classes), images


def _frontier(keys: tuple[ProjectIROutputCandidateKey, ...]):
    merged: list[ProjectIROutputCandidateKey] = []
    for key in keys:
        existing = next(
            (
                item
                for item in merged
                if item.output is key.output
                and item.determinants == key.determinants
                and item.strength is key.strength
            ),
            None,
        )
        if existing is None:
            merged.append(key)
        else:
            supports = (*existing.supports, *key.supports)
            merged[merged.index(existing)] = ProjectIROutputCandidateKey(
                output=key.output,
                determinants=key.determinants,
                strength=key.strength,
                supports=supports,
            )
    retained: list[ProjectIROutputCandidateKey] = []
    for position, key in enumerate(merged):
        fields = frozenset(key.determinants)
        if any(
            other.output is key.output
            and frozenset(other.determinants) <= fields
            and (
                other.strength is ProjectRowUniquenessStrength.STRICT
                or other.strength is key.strength
            )
            for other_position, other in enumerate(merged)
            if other_position != position
        ):
            continue
        retained.append(key)
    return tuple(retained)


def _key_fds(output, classes, keys, inherited=()):
    facts = list(inherited)
    for key in keys:
        dependents = tuple(item for item in classes if item not in key.determinants)
        if dependents:
            facts.append(
                ProjectIROutputValueFD(
                    output=output,
                    determinants=key.determinants,
                    dependents=dependents,
                    strength=key.strength,
                    supports=(key,),
                )
            )
    merged: list[ProjectIROutputValueFD] = []
    for fact in facts:
        existing = next(
            (
                item
                for item in merged
                if item.determinants == fact.determinants
                and item.dependents == fact.dependents
                and item.strength is fact.strength
            ),
            None,
        )
        if existing is None:
            merged.append(fact)
        else:
            merged[merged.index(existing)] = ProjectIROutputValueFD(
                output=output,
                determinants=fact.determinants,
                dependents=fact.dependents,
                strength=fact.strength,
                supports=(*existing.supports, *fact.supports),
            )
    return tuple(merged)


def _compile_output_fd_index(output, universe, facts):
    positions = {item: position for position, item in enumerate(universe)}

    def rule(fact):
        return ProjectIRCompiledOutputFDRule(
            fact=fact,
            lhs_mask=sum(1 << positions[item] for item in fact.determinants),
            rhs_mask=sum(1 << positions[item] for item in fact.dependents),
        )

    strict_rules = tuple(
        rule(fact)
        for fact in facts
        if fact.strength is ProjectRowUniquenessStrength.STRICT
    )
    lax_rules = tuple(
        rule(fact)
        for fact in facts
        if fact.strength is ProjectRowUniquenessStrength.LAX
    )
    incidents = tuple(
        tuple(
            rule_position
            for rule_position, compiled in enumerate(strict_rules)
            if compiled.lhs_mask & (1 << position)
        )
        for position in range(len(universe))
    )
    return ProjectIROutputFDIndex(
        output=output,
        universe=universe,
        facts=facts,
        positions=positions,
        strict_rules=strict_rules,
        lax_rules=lax_rules,
        incidents=incidents,
    )


def strict_output_fd_closure(index, seed):
    if seed.index is not index:
        raise ValueError("STRICT closure requires one exact output-local universe.")
    closure_mask = seed.mask
    unsatisfied = [rule.lhs_mask.bit_count() for rule in index.strict_rules]
    pending: deque[int] = deque(index.positions[item] for item in seed.classes)
    ready: list[int] = []
    fired = [False] * len(index.strict_rules)
    witness: list[ProjectIROutputFDProofStep] = []
    while pending or ready:
        while pending:
            position = pending.popleft()
            for rule_position in index.incidents[position]:
                if fired[rule_position]:
                    continue
                unsatisfied[rule_position] -= 1
                if unsatisfied[rule_position] == 0:
                    heappush(ready, rule_position)
        if not ready:
            break
        rule_position = heappop(ready)
        fired[rule_position] = True
        rule = index.strict_rules[rule_position]
        new_mask = rule.rhs_mask & ~closure_mask
        if not new_mask:
            continue
        closure_mask |= new_mask
        derived = tuple(
            item
            for position, item in enumerate(index.universe)
            if new_mask & (1 << position)
        )
        witness.append(ProjectIROutputFDProofStep(fact=rule.fact, derived=derived))
        pending.extend(index.positions[item] for item in derived)
    classes = ProjectIROutputValueClassSet(
        index=index,
        classes=tuple(
            item
            for position, item in enumerate(index.universe)
            if closure_mask & (1 << position)
        ),
    )
    return ProjectIROutputStrictClosure(
        seed=seed,
        classes=classes,
        witness=tuple(witness),
    )


def strictly_determines_output(index, seed, requested):
    if seed.index is not index or requested.index is not index:
        raise ValueError("Determination requires one exact output-local universe.")
    closure = strict_output_fd_closure(index, seed)
    status = (
        ProjectIROutputDeterminationStatus.PROVEN
        if requested.mask & closure.classes.mask == requested.mask
        else ProjectIROutputDeterminationStatus.NOT_PROVEN
    )
    return ProjectIROutputDeterminationResult(
        seed=seed,
        requested=requested,
        closure=closure,
        status=status,
    )


def _source_seed(origins, output, classes):
    owner = output.row_shape.relation.identity
    matches = tuple(
        origin for origin in origins.source_origins if origin.identity.owner == owner
    )
    if len(matches) != 1:
        raise ValueError("Source output requires one exact grain origin.")
    origin = matches[0]
    source_keys = tuple(
        key
        for key in origins.value_fds.row_keys.candidate_keys
        if key.identity.owner == owner
    )
    keys = tuple(
        ProjectIROutputCandidateKey(
            output=output,
            determinants=tuple(
                classes[item.field_position] for item in key.identity.determinants
            ),
            strength=key.identity.strength,
            supports=(key,),
        )
        for key in source_keys
    )
    factors = origin.basis.universe.factors
    return keys, ProjectIRProvidedIntrinsicGrain(
        output=output,
        state=origin.basis.state,
        factors=factors,
        active=tuple(item.identity for item in factors),
        dependencies=origin.basis.dependencies,
        origin_set=origins,
        witness=origin,
    )


def build_project_ir_relational_property_stage(
    origins: ProjectGrainOriginSet,
    analyses: ProjectIRAnalysisBundle,
) -> ProjectIRRelationalPropertyStage:
    if origins.evaluation is not analyses.stage:
        raise ValueError("Relational construction requires exact shared roots.")
    built: dict[object, ProjectIROutputRelationalProperties] = {}
    values: list[ProjectIROutputRelationalProperties] = []
    for node in analyses.topological_order:
        output = _row_output(analyses, node)
        operator = _operator(analyses, node)
        fields = _field_occurrences(output)
        incoming = _incoming(analyses, node, built)
        if incoming is None:
            classes = _singleton_classes(output, fields)
            keys, provided_grain = _source_seed(origins, output, classes)
            fds = _key_fds(output, classes, keys)
        elif operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
            classes = _singleton_classes(output, fields)
            context = next(
                item
                for item in analyses.stage.aggregate_contexts
                if item.operator is operator
            )
            origin = next(
                item
                for item in origins.aggregate_origins
                if item.identity.operator == operator.node.ref
            )
            dependencies = list(incoming.grain.dependencies)
            factors = (*incoming.grain.factors, *origin.basis.universe.factors)
            if context.group_keys:
                active = tuple(item.identity for item in origin.basis.universe.factors)
                dependencies.append(
                    ProjectGrainDependencyFact(
                        determinants=incoming.grain.active,
                        dependents=active,
                    )
                )
                group_fields = tuple(
                    target
                    for fact in context.semantic_facts.clause_dependencies
                    if fact.role.value == "group_key"
                    for target in fact.target_fields
                )
                if any(
                    key.strength is ProjectRowUniquenessStrength.STRICT
                    and all(
                        any(
                            target is member.evidence
                            for target in group_fields
                            for member in determinant.members
                        )
                        for determinant in key.determinants
                    )
                    for key in incoming.keys
                ):
                    dependencies.append(
                        ProjectGrainDependencyFact(
                            determinants=active,
                            dependents=incoming.grain.active,
                        )
                    )
                visible = (
                    classes[: len(context.group_keys)]
                    if len(classes) >= len(context.group_keys)
                    else ()
                )
                keys = (
                    (
                        ProjectIROutputCandidateKey(
                            output=output,
                            determinants=visible,
                            strength=ProjectRowUniquenessStrength.STRICT,
                            supports=(context, origin),
                        ),
                    )
                    if visible
                    else ()
                )
                state = ProjectGrainBasisState.FACTORIZED
            else:
                active = ()
                keys = ()
                state = ProjectGrainBasisState.GLOBAL
            provided_grain = ProjectIRProvidedIntrinsicGrain(
                output=output,
                state=state,
                factors=factors,
                active=active,
                dependencies=tuple(dependencies),
                origin_set=origins,
                witness=(incoming.grain, context, origin),
            )
            fds = _key_fds(output, classes, keys)
        else:
            classes, images = (
                _projection_images(incoming, operator, output, fields)
                if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                else _preserving_classes(incoming, output, fields)
            )
            transferred = tuple(
                ProjectIROutputCandidateKey(
                    output=output,
                    determinants=tuple(
                        cast(ProjectIROutputValueClass, images[item])
                        for item in key.determinants
                    ),
                    strength=(
                        ProjectRowUniquenessStrength.STRICT
                        if all(
                            all(
                                member.evidence.nullability
                                is ProjectRowFieldNullability.NON_NULL
                                for member in cast(
                                    ProjectIROutputValueClass, images[item]
                                ).members
                            )
                            for item in key.determinants
                        )
                        else key.strength
                    ),
                    supports=(key,),
                )
                for key in incoming.keys
                if all(images[item] for item in key.determinants)
            )
            keys = _frontier(transferred)
            mapped_fds = tuple(
                ProjectIROutputValueFD(
                    output=output,
                    determinants=tuple(
                        cast(ProjectIROutputValueClass, images[item])
                        for item in fact.determinants
                    ),
                    dependents=tuple(
                        cast(ProjectIROutputValueClass, images[item])
                        for item in fact.dependents
                        if images[item] is not None
                    ),
                    strength=fact.strength,
                    supports=(fact,),
                )
                for fact in incoming.fds
                if all(images[item] for item in fact.determinants)
                and any(images[item] for item in fact.dependents)
            )
            fds = _key_fds(output, classes, keys, mapped_fds)
            provided_grain = ProjectIRProvidedIntrinsicGrain(
                output=output,
                state=incoming.grain.state,
                factors=incoming.grain.factors,
                active=incoming.grain.active,
                dependencies=incoming.grain.dependencies,
                origin_set=origins,
                witness=(incoming.grain, operator),
            )
        item = ProjectIROutputRelationalProperties(
            output=output,
            fields=fields,
            value_classes=classes,
            keys=keys,
            fds=fds,
            fd_index=_compile_output_fd_index(output, classes, fds),
            grain=provided_grain,
        )
        values.append(item)
        built[output.occurrence.ref] = item
    return ProjectIRRelationalPropertyStage(
        origins=origins,
        analyses=analyses,
        outputs=tuple(values),
    )


class ProjectIRGrainDirectionStatus(StrEnum):
    PROVEN = "proven"
    NOT_PROVEN = "not_proven"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRCompiledGrainComparisonRule:
    fact: ProjectGrainDependencyFact = field(repr=False, compare=False, hash=False)
    lhs_mask: int
    rhs_mask: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRGrainComparisonDomain:
    factors: tuple[ProjectGrainFactorIdentity, ...]
    facts: tuple[ProjectGrainDependencyFact, ...]
    positions: Mapping[ProjectGrainFactorIdentity, int] = field(
        repr=False, compare=False, hash=False
    )
    rules: tuple[ProjectIRCompiledGrainComparisonRule, ...]
    incidents: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        expected_positions = {
            factor: position for position, factor in enumerate(self.factors)
        }
        if (
            len(expected_positions) != len(self.factors)
            or dict(self.positions) != expected_positions
        ):
            raise ValueError("Comparison domain requires distinct ordered factors.")
        object.__setattr__(self, "positions", MappingProxyType(expected_positions))
        if any(
            rule.fact is not fact
            for rule, fact in zip(self.rules, self.facts, strict=True)
        ) or len(self.rules) != len(self.facts):
            raise ValueError("Comparison rules must retain normative fact order.")
        expected_rules = tuple(
            ProjectIRCompiledGrainComparisonRule(
                fact=fact,
                lhs_mask=sum(
                    1 << expected_positions[item] for item in fact.determinants
                ),
                rhs_mask=sum(1 << expected_positions[item] for item in fact.dependents),
            )
            for fact in self.facts
        )
        if any(
            actual.lhs_mask != expected.lhs_mask or actual.rhs_mask != expected.rhs_mask
            for actual, expected in zip(self.rules, expected_rules, strict=True)
        ):
            raise ValueError("Comparison compiled masks must match normative facts.")
        expected_incidents = tuple(
            tuple(
                rule_position
                for rule_position, rule in enumerate(expected_rules)
                if rule.lhs_mask & (1 << position)
            )
            for position in range(len(self.factors))
        )
        if self.incidents != expected_incidents:
            raise ValueError("Comparison incidents must retain normative rule order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRGrainComparisonFactorSet:
    domain: ProjectIRGrainComparisonDomain
    factors: tuple[ProjectGrainFactorIdentity, ...]
    mask: int = field(init=False)

    def __post_init__(self) -> None:
        if any(factor not in self.domain.positions for factor in self.factors):
            raise ValueError("Comparison factor set requires its exact domain.")
        mask = sum(1 << self.domain.positions[factor] for factor in self.factors)
        expected = tuple(
            factor
            for position, factor in enumerate(self.domain.factors)
            if mask & (1 << position)
        )
        if expected != self.factors:
            raise ValueError("Comparison factor set must follow domain order.")
        object.__setattr__(self, "mask", mask)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRGrainProofStep:
    fact: ProjectGrainDependencyFact = field(repr=False, compare=False, hash=False)
    derived: tuple[ProjectGrainFactorIdentity, ...]


def _indexed_grain_closure(domain, seed_mask):
    closure_mask = seed_mask
    unsatisfied = [rule.lhs_mask.bit_count() for rule in domain.rules]
    pending: deque[int] = deque(
        position
        for position in range(len(domain.factors))
        if seed_mask & (1 << position)
    )
    ready: list[int] = []
    fired = [False] * len(domain.rules)
    witness: list[ProjectIRGrainProofStep] = []
    while pending or ready:
        while pending:
            position = pending.popleft()
            for rule_position in domain.incidents[position]:
                if fired[rule_position]:
                    continue
                unsatisfied[rule_position] -= 1
                if unsatisfied[rule_position] == 0:
                    heappush(ready, rule_position)
        if not ready:
            break
        rule_position = heappop(ready)
        fired[rule_position] = True
        rule = domain.rules[rule_position]
        new_mask = rule.rhs_mask & ~closure_mask
        if not new_mask:
            continue
        closure_mask |= new_mask
        derived = tuple(
            factor
            for position, factor in enumerate(domain.factors)
            if new_mask & (1 << position)
        )
        witness.append(ProjectIRGrainProofStep(fact=rule.fact, derived=derived))
        pending.extend(domain.positions[factor] for factor in derived)
    return closure_mask, tuple(witness)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRGrainDirectionalDetermination:
    source: ProjectIRProvidedIntrinsicGrain = field(
        repr=False, compare=False, hash=False
    )
    target: ProjectIRProvidedIntrinsicGrain = field(
        repr=False, compare=False, hash=False
    )
    seed: ProjectIRGrainComparisonFactorSet
    requested: ProjectIRGrainComparisonFactorSet
    closure: ProjectIRGrainComparisonFactorSet
    witness: tuple[ProjectIRGrainProofStep, ...]
    status: ProjectIRGrainDirectionStatus

    def __post_init__(self) -> None:
        if not (self.seed.domain is self.requested.domain is self.closure.domain):
            raise ValueError("Directional result requires one exact comparison domain.")
        expected_seed = tuple(
            factor
            for factor in self.seed.domain.factors
            if factor in self.source.active
        )
        expected_requested = tuple(
            factor
            for factor in self.seed.domain.factors
            if factor in self.target.active
        )
        if (
            self.seed.factors != expected_seed
            or self.requested.factors != expected_requested
        ):
            raise ValueError("Directional seed/request must retain exact properties.")
        expected_mask, expected_witness = (
            (self.seed.mask, ())
            if self.requested.mask == 0
            else _indexed_grain_closure(self.seed.domain, self.seed.mask)
        )
        if (
            self.closure.mask != expected_mask
            or len(self.witness) != len(expected_witness)
            or any(
                actual.fact is not expected.fact or actual.derived != expected.derived
                for actual, expected in zip(self.witness, expected_witness, strict=True)
            )
        ):
            raise ValueError("Directional witness must replay the indexed fixed point.")
        proven = self.requested.mask & self.closure.mask == self.requested.mask
        expected_status = (
            ProjectIRGrainDirectionStatus.PROVEN
            if proven
            else ProjectIRGrainDirectionStatus.NOT_PROVEN
        )
        if self.status is not expected_status:
            raise ValueError("Directional status must match the retained closure.")


def _comparison_domain(left, right):
    factors: list[ProjectGrainFactorIdentity] = []
    for factor in (*left.factors, *right.factors):
        if factor.identity not in factors:
            factors.append(factor.identity)
    facts: list[ProjectGrainDependencyFact] = []
    for fact in (*left.dependencies, *right.dependencies):
        if not any(fact is retained for retained in facts):
            facts.append(fact)
        for factor in (*fact.determinants, *fact.dependents):
            if factor not in factors:
                factors.append(factor)
    positions = {factor: position for position, factor in enumerate(factors)}
    rules = tuple(
        ProjectIRCompiledGrainComparisonRule(
            fact=fact,
            lhs_mask=sum(1 << positions[item] for item in fact.determinants),
            rhs_mask=sum(1 << positions[item] for item in fact.dependents),
        )
        for fact in facts
    )
    incidents = tuple(
        tuple(
            rule_position
            for rule_position, rule in enumerate(rules)
            if rule.lhs_mask & (1 << position)
        )
        for position in range(len(factors))
    )
    return ProjectIRGrainComparisonDomain(
        factors=tuple(factors),
        facts=tuple(facts),
        positions=positions,
        rules=rules,
        incidents=incidents,
    )


def _direction(domain, source, target):
    seed = ProjectIRGrainComparisonFactorSet(
        domain=domain,
        factors=tuple(factor for factor in domain.factors if factor in source.active),
    )
    requested = ProjectIRGrainComparisonFactorSet(
        domain=domain,
        factors=tuple(factor for factor in domain.factors if factor in target.active),
    )
    closure_mask, witness = (
        (seed.mask, ())
        if requested.mask == 0
        else _indexed_grain_closure(domain, seed.mask)
    )
    closure = ProjectIRGrainComparisonFactorSet(
        domain=domain,
        factors=tuple(
            factor
            for position, factor in enumerate(domain.factors)
            if closure_mask & (1 << position)
        ),
    )
    status = (
        ProjectIRGrainDirectionStatus.PROVEN
        if requested.mask & closure.mask == requested.mask
        else ProjectIRGrainDirectionStatus.NOT_PROVEN
    )
    return ProjectIRGrainDirectionalDetermination(
        source=source,
        target=target,
        seed=seed,
        requested=requested,
        closure=closure,
        witness=witness,
        status=status,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRGrainComparison:
    left: ProjectIRProvidedIntrinsicGrain
    right: ProjectIRProvidedIntrinsicGrain
    domain: ProjectIRGrainComparisonDomain
    left_to_right: ProjectIRGrainDirectionalDetermination
    right_to_left: ProjectIRGrainDirectionalDetermination
    status: ProjectIRGrainComparisonStatus

    def __post_init__(self) -> None:
        if not (
            self.left_to_right.source is self.left
            and self.left_to_right.target is self.right
            and self.right_to_left.source is self.right
            and self.right_to_left.target is self.left
            and self.left_to_right.seed.domain is self.domain
            and self.right_to_left.seed.domain is self.domain
        ):
            raise ValueError("Comparison requires two exact directional results.")
        expected = {
            (
                ProjectIRGrainDirectionStatus.PROVEN,
                ProjectIRGrainDirectionStatus.PROVEN,
            ): ProjectIRGrainComparisonStatus.EQUAL,
            (
                ProjectIRGrainDirectionStatus.PROVEN,
                ProjectIRGrainDirectionStatus.NOT_PROVEN,
            ): ProjectIRGrainComparisonStatus.LEFT_FINER,
            (
                ProjectIRGrainDirectionStatus.NOT_PROVEN,
                ProjectIRGrainDirectionStatus.PROVEN,
            ): ProjectIRGrainComparisonStatus.RIGHT_FINER,
            (
                ProjectIRGrainDirectionStatus.NOT_PROVEN,
                ProjectIRGrainDirectionStatus.NOT_PROVEN,
            ): ProjectIRGrainComparisonStatus.INCOMPARABLE,
        }[(self.left_to_right.status, self.right_to_left.status)]
        if self.status is not expected:
            raise ValueError("Comparison status must derive from both directions.")


def compare_project_ir_grain(left, right):
    domain = _comparison_domain(left, right)
    left_to_right = _direction(domain, left, right)
    right_to_left = _direction(domain, right, left)
    status = {
        (
            ProjectIRGrainDirectionStatus.PROVEN,
            ProjectIRGrainDirectionStatus.PROVEN,
        ): ProjectIRGrainComparisonStatus.EQUAL,
        (
            ProjectIRGrainDirectionStatus.PROVEN,
            ProjectIRGrainDirectionStatus.NOT_PROVEN,
        ): ProjectIRGrainComparisonStatus.LEFT_FINER,
        (
            ProjectIRGrainDirectionStatus.NOT_PROVEN,
            ProjectIRGrainDirectionStatus.PROVEN,
        ): ProjectIRGrainComparisonStatus.RIGHT_FINER,
        (
            ProjectIRGrainDirectionStatus.NOT_PROVEN,
            ProjectIRGrainDirectionStatus.NOT_PROVEN,
        ): ProjectIRGrainComparisonStatus.INCOMPARABLE,
    }[(left_to_right.status, right_to_left.status)]
    return ProjectIRGrainComparison(
        left=left,
        right=right,
        domain=domain,
        left_to_right=left_to_right,
        right_to_left=right_to_left,
        status=status,
    )
