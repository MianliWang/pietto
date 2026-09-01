"""Private intrinsic grain origins and basis-local dependency kernel."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.model import ProjectRelationRowSchemaStatus
from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
)
from pietto._project.project_ir import ProjectIRPlanNodeRef, ProjectIRUseRef
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
    ProjectIREvaluationContextStage,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_properties import (
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowShape,
)
from pietto._project.project_value_fds import (
    ProjectValueFDBasis,
    ProjectValueFDBasisSet,
)
from pietto.ast_nodes import GroupByItem, SourceDef

__all__: tuple[str, ...] = ()


class ProjectGrainBasisState(StrEnum):
    """Closed intrinsic-grain basis states."""

    FACTORIZED = "factorized"
    GLOBAL = "global"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectGrainOriginKind(StrEnum):
    """Currently constructible grain-changing origins."""

    SOURCE_ROW_DOMAIN = "source_row_domain"
    GROUPED_RESULT = "grouped_result"
    GLOBAL_AGGREGATE = "global_aggregate"


class ProjectGrainFactorKind(StrEnum):
    """Nominal intrinsic grain-domain factor kinds."""

    SOURCE_DOMAIN = "source_domain"
    GROUP_DOMAIN = "group_domain"


class ProjectOptionalGrainFactorReadiness(StrEnum):
    """Optional factor uses require future exact JOIN/nulling authority."""

    NOT_CONSTRUCTIBLE_BEFORE_LOGICAL_JOIN = "not_constructible_before_logical_join"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSourceGrainFactorIdentity:
    """One exact Source declaration's intrinsic row domain."""

    owner: ProjectDeclarationOccurrenceIdentity
    semantic: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectGrainFactorKind = field(
        default=ProjectGrainFactorKind.SOURCE_DOMAIN,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Source grain identity requires an exact owner.")
        if type(self.semantic) is not ProjectModuleRelationSemanticFacts or (
            type(self.semantic.owner.definition) is not SourceDef
            or self.semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        ):
            raise ValueError("Source grain identity requires exact concrete rows.")
        if self.semantic.owner.identity != self.owner.identity or (
            self.semantic.owner.module_position != self.owner.module_position
            or self.semantic.owner.declaration_position
            != self.owner.declaration_position
        ):
            raise ValueError("Source grain owner and semantic authority must agree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGroupedGrainFactorIdentity:
    """One exact GROUP_AGGREGATE occurrence's grouped row domain."""

    owner: ProjectDeclarationOccurrenceIdentity
    operator: ProjectIRPlanNodeRef
    context: ProjectIRAggregateEvaluationContext = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectGrainFactorKind = field(
        default=ProjectGrainFactorKind.GROUP_DOMAIN,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Grouped grain identity requires an exact owner.")
        if type(self.operator) is not ProjectIRPlanNodeRef:
            raise TypeError("Grouped grain identity requires an exact plan ref.")
        if type(self.context) is not ProjectIRAggregateEvaluationContext or (
            not self.context.group_keys
            or self.context.operator.node.ref != self.operator
            or self.context.operator.kind
            is not ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
            or self.context.operator.node.anchor.identity != self.owner
        ):
            raise ValueError("Grouped grain identity requires exact group authority.")


type ProjectBaseGrainFactorIdentity = (
    ProjectSourceGrainFactorIdentity | ProjectGroupedGrainFactorIdentity
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectJoinGrainFactorIdentity:
    """One snapshot-local factor use introduced into a JOIN region."""

    base: ProjectBaseGrainFactorIdentity
    introduction_use: ProjectIRUseRef
    nulling_joins: tuple[ProjectIRPlanNodeRef, ...]
    kind: ProjectGrainFactorKind = field(init=False)

    def __post_init__(self) -> None:
        if type(self.base) not in {
            ProjectSourceGrainFactorIdentity,
            ProjectGroupedGrainFactorIdentity,
        }:
            raise TypeError("JOIN grain use requires an exact base factor.")
        if type(self.introduction_use) is not ProjectIRUseRef:
            raise TypeError("JOIN grain use requires an introduction-use ref.")
        if type(self.nulling_joins) is not tuple or any(
            type(item) is not ProjectIRPlanNodeRef for item in self.nulling_joins
        ):
            raise TypeError("JOIN grain nulling refs must be an exact tuple.")
        positions = tuple(item.position for item in self.nulling_joins)
        if len(set(self.nulling_joins)) != len(self.nulling_joins) or any(
            left >= right for left, right in zip(positions, positions[1:], strict=False)
        ):
            raise ValueError("JOIN grain nulling refs must be unique and ordered.")
        if any(
            item.scope is not self.introduction_use.scope for item in self.nulling_joins
        ):
            raise ValueError("JOIN grain use requires one snapshot scope.")
        object.__setattr__(self, "kind", self.base.kind)


type ProjectGrainFactorIdentity = (
    ProjectSourceGrainFactorIdentity
    | ProjectGroupedGrainFactorIdentity
    | ProjectJoinGrainFactorIdentity
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainDomainFactor:
    """One intrinsic domain factor, distinct from future factor-use identity."""

    identity: ProjectGrainFactorIdentity

    def __post_init__(self) -> None:
        if type(self.identity) not in {
            ProjectSourceGrainFactorIdentity,
            ProjectGroupedGrainFactorIdentity,
            ProjectJoinGrainFactorIdentity,
        }:
            raise TypeError("Grain factor requires an exact domain identity.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainDependencyFact:
    """One basis-local FactorSet -> FactorSet semantic dependency."""

    determinants: tuple[ProjectGrainFactorIdentity, ...]
    dependents: tuple[ProjectGrainFactorIdentity, ...]

    def __post_init__(self) -> None:
        for values, label in (
            (self.determinants, "determinants"),
            (self.dependents, "dependents"),
        ):
            if (
                type(values) is not tuple
                or not values
                or any(
                    type(value)
                    not in {
                        ProjectSourceGrainFactorIdentity,
                        ProjectGroupedGrainFactorIdentity,
                        ProjectJoinGrainFactorIdentity,
                    }
                    for value in values
                )
            ):
                raise TypeError(f"Grain dependency {label} require exact factors.")
            if len(set(values)) != len(values):
                raise ValueError(f"Grain dependency {label} cannot repeat factors.")
        if set(self.determinants) & set(self.dependents):
            raise ValueError("Non-trivial grain dependencies forbid self edges.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainFactorUniverse:
    """One basis-local ordered factor universe."""

    factors: tuple[ProjectGrainDomainFactor, ...]

    def __post_init__(self) -> None:
        if type(self.factors) is not tuple or any(
            type(factor) is not ProjectGrainDomainFactor for factor in self.factors
        ):
            raise TypeError("Grain universe requires exact domain factors.")
        identities = tuple(factor.identity for factor in self.factors)
        if len(set(identities)) != len(identities):
            raise ValueError("Grain universe factors must remain distinct and ordered.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCompiledGrainDependencyRule:
    """Snapshot-local masks for one normative grain dependency."""

    fact: ProjectGrainDependencyFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    lhs_mask: int
    rhs_mask: int

    def __post_init__(self) -> None:
        if type(self.fact) is not ProjectGrainDependencyFact:
            raise TypeError("Compiled grain rule requires a normative fact.")
        if (
            type(self.lhs_mask) is not int
            or type(self.rhs_mask) is not int
            or self.lhs_mask <= 0
            or self.rhs_mask <= 0
            or self.lhs_mask & self.rhs_mask
        ):
            raise ValueError("Compiled grain masks must be non-trivial and disjoint.")


def _factor_mask(
    universe: ProjectGrainFactorUniverse,
    identities: tuple[ProjectGrainFactorIdentity, ...],
) -> int:
    positions = {
        factor.identity: position for position, factor in enumerate(universe.factors)
    }
    try:
        return sum(1 << positions[identity] for identity in identities)
    except KeyError as error:
        raise ValueError("Grain factor is outside the exact local universe.") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainDependencyIndex:
    """Immutable basis-local factor positions, rules, and incidents."""

    universe: ProjectGrainFactorUniverse
    facts: tuple[ProjectGrainDependencyFact, ...]
    positions: Mapping[ProjectGrainFactorIdentity, int] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    rules: tuple[ProjectCompiledGrainDependencyRule, ...] = ()
    incidents: tuple[tuple[int, ...], ...] = ()

    def __post_init__(self) -> None:
        if type(self.universe) is not ProjectGrainFactorUniverse:
            raise TypeError("Grain index requires one exact universe.")
        if type(self.facts) is not tuple or any(
            type(fact) is not ProjectGrainDependencyFact for fact in self.facts
        ):
            raise TypeError("Grain index requires exact dependency facts.")
        expected_positions = {
            factor.identity: position
            for position, factor in enumerate(self.universe.factors)
        }
        if dict(self.positions) != expected_positions:
            raise ValueError("Grain positions must match exact factor order.")
        object.__setattr__(self, "positions", MappingProxyType(expected_positions))
        expected_rules = tuple(
            ProjectCompiledGrainDependencyRule(
                fact=fact,
                lhs_mask=_factor_mask(self.universe, fact.determinants),
                rhs_mask=_factor_mask(self.universe, fact.dependents),
            )
            for fact in self.facts
        )
        if len(self.rules) != len(expected_rules) or any(
            supplied.fact is not expected.fact
            or supplied.lhs_mask != expected.lhs_mask
            or supplied.rhs_mask != expected.rhs_mask
            for supplied, expected in zip(self.rules, expected_rules, strict=True)
        ):
            raise ValueError("Compiled grain rules must retain normative order.")
        incident_lists: list[list[int]] = [list() for _factor in self.universe.factors]
        for rule_position, rule in enumerate(expected_rules):
            for factor_position in range(len(self.universe.factors)):
                if rule.lhs_mask & (1 << factor_position):
                    incident_lists[factor_position].append(rule_position)
        if self.incidents != tuple(tuple(values) for values in incident_lists):
            raise ValueError("Grain incidents must retain exact rule order.")


def _compile_grain_dependency_index(
    universe: ProjectGrainFactorUniverse,
    facts: tuple[ProjectGrainDependencyFact, ...],
) -> ProjectGrainDependencyIndex:
    """Compile typed factor dependencies without changing semantic authority."""

    if type(universe) is not ProjectGrainFactorUniverse or type(facts) is not tuple:
        raise TypeError("Grain dependency compilation requires exact typed inputs.")
    rules = tuple(
        ProjectCompiledGrainDependencyRule(
            fact=fact,
            lhs_mask=_factor_mask(universe, fact.determinants),
            rhs_mask=_factor_mask(universe, fact.dependents),
        )
        for fact in facts
    )
    incidents: list[list[int]] = [list() for _factor in universe.factors]
    for rule_position, rule in enumerate(rules):
        for factor_position in range(len(universe.factors)):
            if rule.lhs_mask & (1 << factor_position):
                incidents[factor_position].append(rule_position)
    return ProjectGrainDependencyIndex(
        universe=universe,
        facts=facts,
        positions={
            factor.identity: position
            for position, factor in enumerate(universe.factors)
        },
        rules=rules,
        incidents=tuple(tuple(values) for values in incidents),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainFactorSet:
    """One typed factor set and its basis-local computational mask."""

    universe: ProjectGrainFactorUniverse
    factors: tuple[ProjectGrainFactorIdentity, ...]
    mask: int = field(init=False)

    def __post_init__(self) -> None:
        if type(self.universe) is not ProjectGrainFactorUniverse or (
            type(self.factors) is not tuple
        ):
            raise TypeError("Grain factor set requires exact typed inputs.")
        mask = _factor_mask(self.universe, self.factors)
        expected = tuple(
            factor.identity
            for position, factor in enumerate(self.universe.factors)
            if mask & (1 << position)
        )
        if self.factors != expected:
            raise ValueError("Grain factor set must follow exact universe order.")
        object.__setattr__(self, "mask", mask)


def grain_dependency_closure(
    index: ProjectGrainDependencyIndex,
    seed: ProjectGrainFactorSet,
) -> ProjectGrainFactorSet:
    """Compute one finite targeted basis-local dependency fixed point."""

    if type(index) is not ProjectGrainDependencyIndex or (
        type(seed) is not ProjectGrainFactorSet or seed.universe is not index.universe
    ):
        raise ValueError("Grain closure requires one exact local universe.")
    closure_mask = seed.mask
    unsatisfied = [rule.lhs_mask.bit_count() for rule in index.rules]
    fired = [False] * len(index.rules)
    pending: deque[int] = deque(index.positions[factor] for factor in seed.factors)
    while pending:
        position = pending.popleft()
        for rule_position in index.incidents[position]:
            if fired[rule_position]:
                continue
            unsatisfied[rule_position] -= 1
            if unsatisfied[rule_position] != 0:
                continue
            fired[rule_position] = True
            new_mask = index.rules[rule_position].rhs_mask & ~closure_mask
            closure_mask |= new_mask
            pending.extend(
                factor_position
                for factor_position in range(len(index.universe.factors))
                if new_mask & (1 << factor_position)
            )
    return ProjectGrainFactorSet(
        universe=index.universe,
        factors=tuple(
            factor.identity
            for position, factor in enumerate(index.universe.factors)
            if closure_mask & (1 << position)
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSourceGrainWitness:
    """Exact existing source-row authority for one intrinsic domain."""

    semantic: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    value_fds: ProjectValueFDBasis = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.semantic) is not ProjectModuleRelationSemanticFacts or (
            type(self.value_fds) is not ProjectValueFDBasis
            or self.value_fds.universe.scope.relation is not self.semantic
        ):
            raise ValueError("Source grain witness requires exact Slice-5 authority.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGroupedGrainWitness:
    """Exact grouped occurrence, BASE_RESULT, and ordered group-key authority."""

    context: ProjectIRAggregateEvaluationContext = field(
        repr=False,
        compare=False,
        hash=False,
    )
    group_keys: tuple[GroupByItem, ...]

    def __post_init__(self) -> None:
        if type(self.context) is not ProjectIRAggregateEvaluationContext or (
            not self.context.group_keys
            or self.group_keys is not self.context.group_keys
        ):
            raise ValueError(
                "Grouped grain witness requires exact group-key authority."
            )
        shape = self.context.result_row_output.row_shape
        if type(shape) is not ProjectIRStageRowShape or (
            shape.checkpoint.kind is not ProjectIRStageRowCheckpointKind.BASE_RESULT
        ):
            raise ValueError("Grouped grain witness requires exact BASE_RESULT rows.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGlobalGrainWitness:
    """Exact aggregate context proving one whole-input observation unit."""

    context: ProjectIRAggregateEvaluationContext = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.context) is not ProjectIRAggregateEvaluationContext or (
            self.context.group_keys or not self.context.aggregate_results
        ):
            raise ValueError(
                "GLOBAL grain requires actual ungrouped aggregate authority."
            )


type ProjectGrainDerivationWitness = (
    ProjectSourceGrainWitness | ProjectGroupedGrainWitness | ProjectGlobalGrainWitness
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainBasis:
    """One immutable intrinsic basis value, separate from its origin identity."""

    state: ProjectGrainBasisState
    universe: ProjectGrainFactorUniverse
    dependencies: tuple[ProjectGrainDependencyFact, ...]
    dependency_index: ProjectGrainDependencyIndex
    witness: ProjectGrainDerivationWitness = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.state) is not ProjectGrainBasisState or self.state not in {
            ProjectGrainBasisState.FACTORIZED,
            ProjectGrainBasisState.GLOBAL,
        }:
            raise ValueError("Concrete GrainBasis must be FACTORIZED or GLOBAL.")
        if type(self.universe) is not ProjectGrainFactorUniverse:
            raise TypeError("GrainBasis requires an exact factor universe.")
        if type(self.dependencies) is not tuple or any(
            type(fact) is not ProjectGrainDependencyFact for fact in self.dependencies
        ):
            raise TypeError("GrainBasis dependencies must be exact facts.")
        if type(self.dependency_index) is not ProjectGrainDependencyIndex or (
            self.dependency_index.universe is not self.universe
            or self.dependency_index.facts != self.dependencies
        ):
            raise ValueError("GrainBasis requires its exact compiled dependency index.")
        if self.state is ProjectGrainBasisState.GLOBAL:
            if (
                self.universe.factors
                or self.dependencies
                or (type(self.witness) is not ProjectGlobalGrainWitness)
            ):
                raise ValueError(
                    "GLOBAL GrainBasis requires zero factors and evidence."
                )
            return
        if len(self.universe.factors) != 1 or type(self.witness) not in {
            ProjectSourceGrainWitness,
            ProjectGroupedGrainWitness,
        }:
            raise ValueError(
                "Current FACTORIZED basis requires one exact origin factor."
            )
        factor_identity = self.universe.factors[0].identity
        if type(self.witness) is ProjectSourceGrainWitness:
            if (
                type(factor_identity) is not ProjectSourceGrainFactorIdentity
                or factor_identity.semantic is not self.witness.semantic
                or self.witness.value_fds.universe.scope.owner != factor_identity.owner
            ):
                raise ValueError("Source GrainBasis factor and witness must agree.")
            return
        if type(self.witness) is not ProjectGroupedGrainWitness or (
            type(factor_identity) is not ProjectGroupedGrainFactorIdentity
            or factor_identity.context is not self.witness.context
        ):
            raise ValueError("Grouped GrainBasis factor and witness must agree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainOriginIdentity:
    """Occurrence identity of one source, grouped, or global grain origin."""

    kind: ProjectGrainOriginKind
    owner: ProjectDeclarationOccurrenceIdentity
    operator: ProjectIRPlanNodeRef | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectGrainOriginKind or (
            type(self.owner) is not ProjectDeclarationOccurrenceIdentity
        ):
            raise TypeError("Grain origin requires exact kind and owner.")
        if self.kind is ProjectGrainOriginKind.SOURCE_ROW_DOMAIN:
            if self.operator is not None:
                raise ValueError("Source grain origin forbids a plan operator ref.")
        elif type(self.operator) is not ProjectIRPlanNodeRef:
            raise TypeError("Aggregate grain origin requires exact operator identity.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectConcreteGrainOrigin:
    """One exact origin occurrence and its immutable GrainBasis value."""

    identity: ProjectGrainOriginIdentity
    basis: ProjectGrainBasis

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectGrainOriginIdentity or (
            type(self.basis) is not ProjectGrainBasis
        ):
            raise TypeError("Concrete grain origin requires exact typed authority.")
        if self.identity.kind is ProjectGrainOriginKind.GLOBAL_AGGREGATE:
            if (
                self.basis.state is not ProjectGrainBasisState.GLOBAL
                or type(self.basis.witness) is not ProjectGlobalGrainWitness
                or self.basis.witness.context.operator.node.ref
                != self.identity.operator
                or self.basis.witness.context.operator.node.anchor.identity
                != self.identity.owner
            ):
                raise ValueError("Global origin requires GLOBAL GrainBasis.")
            return
        if self.basis.state is not ProjectGrainBasisState.FACTORIZED:
            raise ValueError("Domain origin requires FACTORIZED GrainBasis.")
        factor_identity = self.basis.universe.factors[0].identity
        if self.identity.kind is ProjectGrainOriginKind.SOURCE_ROW_DOMAIN:
            if (
                type(factor_identity) is not ProjectSourceGrainFactorIdentity
                or factor_identity.owner != self.identity.owner
            ):
                raise ValueError("Source origin requires its exact domain factor.")
        elif (
            type(factor_identity) is not ProjectGroupedGrainFactorIdentity
            or factor_identity.owner != self.identity.owner
            or factor_identity.operator != self.identity.operator
        ):
            raise ValueError("Grouped origin requires its exact domain factor.")


class ProjectNonConcreteGrainOriginKind(StrEnum):
    """Non-concrete source versus aggregate origin subjects."""

    SOURCE_ROW_DOMAIN = "source_row_domain"
    AGGREGATE_CONTEXT = "aggregate_context"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteGrainSubject:
    """Exact causal authority without a fabricated concrete basis."""

    kind: ProjectNonConcreteGrainOriginKind
    semantic: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    readiness: ProjectAggregateGroupedClauseReadiness | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectNonConcreteGrainOriginKind or (
            type(self.semantic) is not ProjectModuleRelationSemanticFacts
        ):
            raise TypeError("Non-concrete grain subject requires exact authority.")
        if self.kind is ProjectNonConcreteGrainOriginKind.SOURCE_ROW_DOMAIN:
            if (
                type(self.semantic.owner.definition) is not SourceDef
                or self.semantic.state.status is ProjectRelationRowSchemaStatus.CONCRETE
                or self.readiness is not None
            ):
                raise ValueError("Non-concrete source grain must retain source state.")
            return
        if (
            type(self.readiness) is not ProjectAggregateGroupedClauseReadiness
            or self.readiness is not self.semantic.aggregate_grouped_clause_readiness
            or self.readiness.status
            is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            raise ValueError("Non-concrete aggregate grain requires readiness roots.")


def _aggregate_origin_matches_context(
    origin: ProjectConcreteGrainOrigin,
    context: ProjectIRAggregateEvaluationContext,
) -> bool:
    expected_kind = (
        ProjectGrainOriginKind.GROUPED_RESULT
        if context.group_keys
        else ProjectGrainOriginKind.GLOBAL_AGGREGATE
    )
    witness = origin.basis.witness
    identity_matches = (
        origin.identity.operator == context.operator.node.ref
        and origin.identity.owner == context.operator.node.anchor.identity
        and origin.identity.kind is expected_kind
    )
    if type(witness) is ProjectGroupedGrainWitness:
        return identity_matches and witness.context is context
    if type(witness) is ProjectGlobalGrainWitness:
        return identity_matches and witness.context is context
    return False


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectGrainOriginSet:
    """Complete source and aggregate grain-origin projection."""

    value_fds: ProjectValueFDBasisSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    evaluation: ProjectIREvaluationContextStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_origins: tuple[ProjectConcreteGrainOrigin, ...]
    aggregate_origins: tuple[ProjectConcreteGrainOrigin, ...]
    non_concrete: tuple[ProjectNonConcreteGrainSubject, ...] = ()

    def __post_init__(self) -> None:
        if type(self.value_fds) is not ProjectValueFDBasisSet or (
            type(self.evaluation) is not ProjectIREvaluationContextStage
        ):
            raise TypeError("Grain origins require exact Slice-5 and IR authority.")
        semantic_facts = self.value_fds.row_keys.semantic_result.module_semantic_facts
        if self.evaluation.project_plan.semantic_facts is not semantic_facts:
            raise ValueError("Grain origins require one exact semantic snapshot.")
        for values, item_type, label in (
            (self.source_origins, ProjectConcreteGrainOrigin, "source origins"),
            (self.aggregate_origins, ProjectConcreteGrainOrigin, "aggregate origins"),
            (
                self.non_concrete,
                ProjectNonConcreteGrainSubject,
                "non-concrete origins",
            ),
        ):
            if type(values) is not tuple or any(
                type(value) is not item_type for value in values
            ):
                raise TypeError(f"Grain {label} must be an exact tuple.")
        if len(self.source_origins) != len(self.value_fds.bases) or any(
            origin.identity.owner != basis.universe.scope.owner
            or origin.identity.kind is not ProjectGrainOriginKind.SOURCE_ROW_DOMAIN
            or type(origin.basis.witness) is not ProjectSourceGrainWitness
            or origin.basis.witness.value_fds is not basis
            for origin, basis in zip(
                self.source_origins,
                self.value_fds.bases,
                strict=True,
            )
        ):
            raise ValueError("Source grain origins must cover Slice-5 source order.")
        expected_contexts = tuple(
            context
            for context in self.evaluation.aggregate_contexts
            if context.group_keys or context.aggregate_results
        )
        if len(self.aggregate_origins) != len(expected_contexts) or any(
            not _aggregate_origin_matches_context(origin, context)
            for origin, context in zip(
                self.aggregate_origins,
                expected_contexts,
                strict=True,
            )
        ):
            raise ValueError("Aggregate grain origins must retain exact plan order.")
        expected_non_concrete: list[
            tuple[
                ProjectNonConcreteGrainOriginKind,
                ProjectModuleRelationSemanticFacts,
                ProjectAggregateGroupedClauseReadiness | None,
            ]
        ] = []
        for fragment in self.evaluation.project_plan.fragments:
            semantic = fragment.semantic_facts
            if type(semantic.owner.definition) is SourceDef and (
                semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            ):
                expected_non_concrete.append(
                    (
                        ProjectNonConcreteGrainOriginKind.SOURCE_ROW_DOMAIN,
                        semantic,
                        None,
                    )
                )
            readiness = semantic.aggregate_grouped_clause_readiness
            if readiness is not None and (
                readiness.status
                is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
            ):
                expected_non_concrete.append(
                    (
                        ProjectNonConcreteGrainOriginKind.AGGREGATE_CONTEXT,
                        semantic,
                        readiness,
                    )
                )
        if len(self.non_concrete) != len(expected_non_concrete) or any(
            subject.kind is not kind
            or subject.semantic is not semantic
            or subject.readiness is not readiness
            for subject, (kind, semantic, readiness) in zip(
                self.non_concrete,
                expected_non_concrete,
                strict=True,
            )
        ):
            raise ValueError("Non-concrete grain subjects must be complete and exact.")

    @property
    def origins(self) -> tuple[ProjectConcreteGrainOrigin, ...]:
        return (*self.source_origins, *self.aggregate_origins)


def _empty_dependency_index(
    factors: tuple[ProjectGrainDomainFactor, ...],
) -> tuple[ProjectGrainFactorUniverse, ProjectGrainDependencyIndex]:
    universe = ProjectGrainFactorUniverse(factors=factors)
    return universe, _compile_grain_dependency_index(universe, ())


def _source_origin(basis: ProjectValueFDBasis) -> ProjectConcreteGrainOrigin:
    semantic = basis.universe.scope.relation
    owner = basis.universe.scope.owner
    factor = ProjectGrainDomainFactor(
        identity=ProjectSourceGrainFactorIdentity(owner=owner, semantic=semantic)
    )
    universe, index = _empty_dependency_index((factor,))
    return ProjectConcreteGrainOrigin(
        identity=ProjectGrainOriginIdentity(
            kind=ProjectGrainOriginKind.SOURCE_ROW_DOMAIN,
            owner=owner,
        ),
        basis=ProjectGrainBasis(
            state=ProjectGrainBasisState.FACTORIZED,
            universe=universe,
            dependencies=(),
            dependency_index=index,
            witness=ProjectSourceGrainWitness(
                semantic=semantic,
                value_fds=basis,
            ),
        ),
    )


def _aggregate_origin(
    context: ProjectIRAggregateEvaluationContext,
) -> ProjectConcreteGrainOrigin | None:
    owner = context.operator.node.anchor.identity
    operator = context.operator.node.ref
    if context.group_keys:
        factor = ProjectGrainDomainFactor(
            identity=ProjectGroupedGrainFactorIdentity(
                owner=owner,
                operator=operator,
                context=context,
            )
        )
        universe, index = _empty_dependency_index((factor,))
        return ProjectConcreteGrainOrigin(
            identity=ProjectGrainOriginIdentity(
                kind=ProjectGrainOriginKind.GROUPED_RESULT,
                owner=owner,
                operator=operator,
            ),
            basis=ProjectGrainBasis(
                state=ProjectGrainBasisState.FACTORIZED,
                universe=universe,
                dependencies=(),
                dependency_index=index,
                witness=ProjectGroupedGrainWitness(
                    context=context,
                    group_keys=context.group_keys,
                ),
            ),
        )
    if not context.aggregate_results:
        return None
    universe, index = _empty_dependency_index(())
    return ProjectConcreteGrainOrigin(
        identity=ProjectGrainOriginIdentity(
            kind=ProjectGrainOriginKind.GLOBAL_AGGREGATE,
            owner=owner,
            operator=operator,
        ),
        basis=ProjectGrainBasis(
            state=ProjectGrainBasisState.GLOBAL,
            universe=universe,
            dependencies=(),
            dependency_index=index,
            witness=ProjectGlobalGrainWitness(context=context),
        ),
    )


def build_project_grain_origins(
    value_fds: ProjectValueFDBasisSet,
    evaluation: ProjectIREvaluationContextStage,
) -> ProjectGrainOriginSet:
    """Build exact source/group/global origins without operator transfer."""

    if type(value_fds) is not ProjectValueFDBasisSet or (
        type(evaluation) is not ProjectIREvaluationContextStage
    ):
        raise TypeError("Grain construction requires exact Slice-5 and IR inputs.")
    semantic_facts = value_fds.row_keys.semantic_result.module_semantic_facts
    if evaluation.project_plan.semantic_facts is not semantic_facts:
        raise ValueError("Grain construction requires one exact semantic snapshot.")
    source_origins = tuple(_source_origin(basis) for basis in value_fds.bases)
    aggregate_origins = tuple(
        origin
        for context in evaluation.aggregate_contexts
        if (origin := _aggregate_origin(context)) is not None
    )
    non_concrete: list[ProjectNonConcreteGrainSubject] = []
    for fragment in evaluation.project_plan.fragments:
        semantic = fragment.semantic_facts
        if type(semantic.owner.definition) is SourceDef and (
            semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        ):
            non_concrete.append(
                ProjectNonConcreteGrainSubject(
                    kind=ProjectNonConcreteGrainOriginKind.SOURCE_ROW_DOMAIN,
                    semantic=semantic,
                )
            )
        readiness = semantic.aggregate_grouped_clause_readiness
        if readiness is not None and (
            readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            non_concrete.append(
                ProjectNonConcreteGrainSubject(
                    kind=ProjectNonConcreteGrainOriginKind.AGGREGATE_CONTEXT,
                    semantic=semantic,
                    readiness=readiness,
                )
            )
    return ProjectGrainOriginSet(
        value_fds=value_fds,
        evaluation=evaluation,
        source_origins=source_origins,
        aggregate_origins=aggregate_origins,
        non_concrete=tuple(non_concrete),
    )
