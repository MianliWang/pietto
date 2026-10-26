"""Private per-aggregate locality and multi-fact analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, cast

from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.model import ProjectAggregateResultFact
from pietto._project.module_semantic_fact_preservation import ProjectModuleSelectFact
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyIndex,
    ProjectGrainFactorIdentity,
    ProjectGrainFactorSet,
    ProjectGrainFactorUniverse,
    ProjectJoinGrainFactorIdentity,
    _compile_grain_dependency_index,
    grain_dependency_closure,
)
from pietto._project.project_ir import (
    ProjectIRJoinInputUseOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIROutputValueRef,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
    ProjectIREvaluationContextStage,
)
from pietto._project.project_ir_joins import (
    ProjectIRJoinRegionStage,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRRelationRowOutput,
    ProjectIRScalarFieldOutput,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRGrainDirectionStatus,
    ProjectIRGrainComparisonStatus,
    ProjectIRProvidedIntrinsicGrain,
    ProjectIRRelationalPropertyStage,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
)
from pietto._project.project_relationship_uses import ProjectNonConcreteJoinUse
from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    ProjectCurrentJoinProperties,
    ProjectCurrentJoinRegion,
)

__all__: tuple[str, ...] = ()


class ProjectFactJoinInputSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class ProjectCommonGrainStatus(StrEnum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    NONE = "none"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectActualGrainAuthorityKind(StrEnum):
    FACT_LOCALITY = "fact_locality"
    JOIN_LEFT_INPUT = "join_left_input"
    JOIN_RIGHT_INPUT = "join_right_input"
    JOIN_SOURCE_SLICE = "join_source_slice"
    JOIN_OUTPUT = "join_output"


class ProjectMultiFactStructuralAlignment(StrEnum):
    EXACTLY_ALIGNED = "exactly_aligned"
    STRUCTURALLY_ALIGNABLE = "structurally_alignable"
    REAGGREGATION_REQUIRED = "reaggregation_required"
    AMBIGUOUS_PATH = "ambiguous_path"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INCOMPATIBLE = "incompatible"


class ProjectMultiFactMultiplicityRisk(StrEnum):
    FANOUT_RISK = "fanout_risk"
    CROSS_FACT_MULTIPLICATION = "cross_fact_multiplication"


class ProjectMultiFactRequirement(StrEnum):
    AGGREGATE_ALGEBRA_REQUIRED = "aggregate_algebra_required"


ProjectFactGrainDirectionStatus = ProjectIRGrainDirectionStatus


def _same_object_index[Key, Value](
    supplied: Mapping[Key, tuple[Value, ...]],
    expected: Mapping[Key, tuple[Value, ...]],
) -> bool:
    return tuple(supplied) == tuple(expected) and all(
        len(supplied[key]) == len(values)
        and all(
            actual is retained
            for actual, retained in zip(supplied[key], values, strict=True)
        )
        for key, values in expected.items()
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAggregateFactIdentity:
    aggregate_node: ProjectIRPlanNodeRef
    aggregate_result_position: int

    def __post_init__(self) -> None:
        if type(self.aggregate_node) is not ProjectIRPlanNodeRef:
            raise TypeError("Aggregate fact identity requires one exact plan-node ref.")
        if (
            type(self.aggregate_result_position) is not int
            or self.aggregate_result_position < 0
        ):
            raise ValueError("Aggregate fact result position must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAggregateFactOccurrence:
    identity: ProjectAggregateFactIdentity
    context: ProjectIRAggregateEvaluationContext = field(
        repr=False, compare=False, hash=False
    )
    aggregate_result: ProjectAggregateResultFact = field(
        repr=False, compare=False, hash=False
    )
    select_fact: ProjectModuleSelectFact = field(repr=False, compare=False, hash=False)
    selected_output_ordinal: int
    stage_scalar_output: ProjectIROutputFieldOccurrence
    final_scalar_output: ProjectIRScalarFieldOutput
    input_row_properties: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    result_row_properties: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    home_relation_properties: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    home_field: ProjectIROutputFieldOccurrence
    home_value_class: ProjectIROutputValueClass
    source_intrinsic_grain: ProjectIRProvidedIntrinsicGrain
    result_intrinsic_grain: ProjectIRProvidedIntrinsicGrain

    def __post_init__(self) -> None:
        position = self.identity.aggregate_result_position
        if (
            type(self.context) is not ProjectIRAggregateEvaluationContext
            or self.identity.aggregate_node != self.context.operator.node.ref
            or position >= len(self.context.aggregate_results)
            or self.context.aggregate_results[position] is not self.aggregate_result
        ):
            raise ValueError("Aggregate fact requires its exact context result.")
        select_matches = tuple(
            item
            for item in self.context.semantic_facts.select_facts
            if item.aggregate_result_fact is self.aggregate_result
        )
        if (
            type(self.select_fact) is not ProjectModuleSelectFact
            or len(select_matches) != 1
            or select_matches[0] is not self.select_fact
            or self.selected_output_ordinal != self.select_fact.selected_output_ordinal
            or self.select_fact.field is None
        ):
            raise ValueError("Aggregate fact requires one exact selected output.")
        ordinal = self.selected_output_ordinal
        if (
            self.input_row_properties.output is not self.context.input_row_output
            or self.result_row_properties.output is not self.context.result_row_output
            or self.home_relation_properties.output
            is not self.context.fragment.root_relation_output
            or self.stage_scalar_output.output is not self.context.result_row_output
            or self.stage_scalar_output
            is not project_aggregate_stage_field(
                self.result_row_properties, self.select_fact
            )
            or self.home_field.output is not self.home_relation_properties.output
            or self.home_field.field_position != ordinal
            or self.home_field.evidence is not self.select_fact.field
        ):
            raise ValueError("Aggregate fact requires exact stage and home fields.")
        final_matches = tuple(
            output
            for output in self.context.fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position == ordinal
        )
        if (
            len(final_matches) != 1
            or final_matches[0] is not self.final_scalar_output
            or self.final_scalar_output.field.evidence is not self.home_field.evidence
            or self.final_scalar_output.occurrence
            is self.stage_scalar_output.output.occurrence
        ):
            raise ValueError("Aggregate fact requires its exact final scalar export.")
        value_matches = tuple(
            value_class
            for value_class in self.home_relation_properties.value_classes
            if any(member is self.home_field for member in value_class.members)
        )
        if len(value_matches) != 1 or value_matches[0] is not self.home_value_class:
            raise ValueError("Aggregate fact requires one exact home value class.")
        if (
            self.source_intrinsic_grain is not self.input_row_properties.grain
            or self.result_intrinsic_grain is not self.result_row_properties.grain
            or self.home_relation_properties.grain.state
            is not self.result_intrinsic_grain.state
            or self.home_relation_properties.grain.active
            != self.result_intrinsic_grain.active
            or self.home_relation_properties.grain.dependencies
            != self.result_intrinsic_grain.dependencies
        ):
            raise ValueError("Aggregate fact requires exact source/result/home grain.")

    @property
    def aggregate_result_position(self) -> int:
        return self.identity.aggregate_result_position


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFactContextualGrain:
    authority: ProjectIRProvidedIntrinsicGrain = field(
        repr=False, compare=False, hash=False
    )
    state: ProjectGrainBasisState
    factors: tuple[ProjectGrainFactorIdentity, ...]
    evidence: object = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.authority) is not ProjectIRProvidedIntrinsicGrain:
            raise TypeError("Contextual grain requires exact relational authority.")
        if self.state not in {
            ProjectGrainBasisState.FACTORIZED,
            ProjectGrainBasisState.GLOBAL,
        }:
            raise ValueError("Concrete contextual grain must be FACTORIZED or GLOBAL.")
        if type(self.factors) is not tuple or any(
            factor not in self.authority.active for factor in self.factors
        ):
            raise ValueError("Contextual factors require the exact active universe.")
        selected = set(self.factors)
        if self.factors != tuple(
            factor for factor in self.authority.active if factor in selected
        ):
            raise ValueError("Contextual factors must retain authority order.")
        if (self.state is ProjectGrainBasisState.GLOBAL and self.factors) or (
            self.state is ProjectGrainBasisState.FACTORIZED and not self.factors
        ):
            raise ValueError("Contextual grain state and active factors disagree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFactGrainDetermination:
    index: ProjectGrainDependencyIndex = field(repr=False, compare=False, hash=False)
    seed: ProjectGrainFactorSet
    requested: ProjectGrainFactorSet
    closure: ProjectGrainFactorSet
    status: ProjectFactGrainDirectionStatus

    def __post_init__(self) -> None:
        if not (
            self.seed.universe
            is self.requested.universe
            is self.closure.universe
            is self.index.universe
        ):
            raise ValueError("Grain determination requires one exact universe.")
        expected = grain_dependency_closure(self.index, self.seed)
        if self.closure.factors != expected.factors:
            raise ValueError("Grain determination closure must replay exactly.")
        proven = self.requested.mask & self.closure.mask == self.requested.mask
        expected_status = (
            ProjectFactGrainDirectionStatus.PROVEN
            if proven
            else ProjectFactGrainDirectionStatus.NOT_PROVEN
        )
        if self.status is not expected_status:
            raise ValueError("Grain determination status must match its closure.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFactGrainComparison:
    left: ProjectFactContextualGrain = field(repr=False, compare=False, hash=False)
    right: ProjectFactContextualGrain = field(repr=False, compare=False, hash=False)
    index: ProjectGrainDependencyIndex = field(repr=False, compare=False, hash=False)
    left_to_right: ProjectFactGrainDetermination
    right_to_left: ProjectFactGrainDetermination
    status: ProjectIRGrainComparisonStatus

    def __post_init__(self) -> None:
        if (
            self.left_to_right.index is not self.index
            or self.right_to_left.index is not self.index
            or self.left_to_right.seed.factors != self.left.factors
            or self.left_to_right.requested.factors != self.right.factors
            or self.right_to_left.seed.factors != self.right.factors
            or self.right_to_left.requested.factors != self.left.factors
        ):
            raise ValueError("Grain comparison requires two exact directions.")
        expected = {
            (
                ProjectFactGrainDirectionStatus.PROVEN,
                ProjectFactGrainDirectionStatus.PROVEN,
            ): ProjectIRGrainComparisonStatus.EQUAL,
            (
                ProjectFactGrainDirectionStatus.PROVEN,
                ProjectFactGrainDirectionStatus.NOT_PROVEN,
            ): ProjectIRGrainComparisonStatus.LEFT_FINER,
            (
                ProjectFactGrainDirectionStatus.NOT_PROVEN,
                ProjectFactGrainDirectionStatus.PROVEN,
            ): ProjectIRGrainComparisonStatus.RIGHT_FINER,
            (
                ProjectFactGrainDirectionStatus.NOT_PROVEN,
                ProjectFactGrainDirectionStatus.NOT_PROVEN,
            ): ProjectIRGrainComparisonStatus.INCOMPARABLE,
        }[(self.left_to_right.status, self.right_to_left.status)]
        if self.status is not expected:
            raise ValueError("Grain comparison must derive from both directions.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentMultiplicityExposure:
    join: ProjectCurrentBinaryJoin = field(repr=False)
    factor_additions: tuple[ProjectJoinGrainFactorIdentity, ...]

    def __post_init__(self) -> None:
        if (
            type(self.join) is not ProjectCurrentBinaryJoin
            or not self.factor_additions
            or any(
                type(item) is not ProjectJoinGrainFactorIdentity
                or not any(
                    item.introduction_use == use.ref for use in self.join.input_uses
                )
                for item in self.factor_additions
            )
        ):
            raise ValueError(
                "Current multiplicity exposure requires exact input factors."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAggregateFactHomeLocality:
    fact: ProjectAggregateFactOccurrence
    home_relation_properties: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    home_field: ProjectIROutputFieldOccurrence
    contextual_grain: ProjectFactContextualGrain

    def __post_init__(self) -> None:
        if (
            type(self.fact) is not ProjectAggregateFactOccurrence
            or self.home_relation_properties is not self.fact.home_relation_properties
            or self.home_field is not self.fact.home_field
            or self.contextual_grain.authority is not self.fact.result_intrinsic_grain
            or self.contextual_grain.state is not self.fact.result_intrinsic_grain.state
            or self.contextual_grain.factors != self.fact.result_intrinsic_grain.active
            or self.contextual_grain.evidence is not self.fact
        ):
            raise ValueError("Home locality requires exact fact result authority.")


# No authored JOIN joins by itself, so a fact is only ever at its home.
type ProjectAggregateFactLocality = ProjectAggregateFactHomeLocality


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectActualGrainAuthority:
    kind: ProjectActualGrainAuthorityKind
    evidence: tuple[object, ...] = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectActualGrainAuthorityKind:
            raise TypeError("Actual grain authority requires an exact kind.")
        if not self.evidence or any(item is None for item in self.evidence):
            raise ValueError("Actual grain authority requires retained evidence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectActualGrainCandidate:
    factors: ProjectGrainFactorSet
    authorities: tuple[ProjectActualGrainAuthority, ...]

    def __post_init__(self) -> None:
        if type(self.factors) is not ProjectGrainFactorSet or not self.authorities:
            raise ValueError("Actual grain candidate requires factors and authority.")
        if any(
            type(item) is not ProjectActualGrainAuthority for item in self.authorities
        ):
            raise TypeError("Actual grain candidate authorities must be exact.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCommonGrainCandidateEvidence:
    candidate: ProjectActualGrainCandidate
    left_to_candidate: ProjectFactGrainDetermination
    right_to_candidate: ProjectFactGrainDetermination

    def __post_init__(self) -> None:
        if (
            self.left_to_candidate.requested is not self.candidate.factors
            or self.right_to_candidate.requested is not self.candidate.factors
            or self.left_to_candidate.status
            is not ProjectFactGrainDirectionStatus.PROVEN
            or self.right_to_candidate.status
            is not ProjectFactGrainDirectionStatus.PROVEN
        ):
            raise ValueError("Common candidate must be reached by both facts.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCommonGrainResult:
    status: ProjectCommonGrainStatus
    actual_candidates: tuple[ProjectActualGrainCandidate, ...]
    common_candidates: tuple[ProjectCommonGrainCandidateEvidence, ...]
    candidates: tuple[ProjectCommonGrainCandidateEvidence, ...]

    def __post_init__(self) -> None:
        if type(self.status) is not ProjectCommonGrainStatus:
            raise TypeError("Common grain result requires an exact status.")
        if any(
            type(item) is not ProjectActualGrainCandidate
            for item in self.actual_candidates
        ) or any(
            type(item) is not ProjectCommonGrainCandidateEvidence
            for item in (*self.common_candidates, *self.candidates)
        ):
            raise TypeError("Common grain result requires exact candidate tuples.")
        if any(
            not any(item.candidate is actual for actual in self.actual_candidates)
            for item in self.common_candidates
        ) or any(
            not any(item is common for common in self.common_candidates)
            for item in self.candidates
        ):
            raise ValueError("Common grain candidates must retain actual authority.")
        expected = (
            ProjectCommonGrainStatus.NONE
            if not self.candidates
            else (
                ProjectCommonGrainStatus.UNIQUE
                if len(self.candidates) == 1
                else ProjectCommonGrainStatus.AMBIGUOUS
            )
        )
        if (
            self.status
            not in {
                ProjectCommonGrainStatus.UNKNOWN,
                ProjectCommonGrainStatus.CONFLICT,
            }
            and self.status is not expected
        ):
            raise ValueError("Common grain status must match retained candidates.")

    @property
    def candidate(self) -> ProjectActualGrainCandidate | None:
        return self.candidates[0].candidate if len(self.candidates) == 1 else None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectMultiFactAlignment:
    left: ProjectAggregateFactLocality = field(repr=False, compare=False, hash=False)
    right: ProjectAggregateFactLocality = field(repr=False, compare=False, hash=False)
    structural: ProjectMultiFactStructuralAlignment
    grain_comparison: ProjectFactGrainComparison | None
    common_grain: ProjectCommonGrainResult
    finer: ProjectAggregateFactLocality | None
    multiplicity_risks: tuple[ProjectMultiFactMultiplicityRisk, ...]
    requirements: tuple[ProjectMultiFactRequirement, ...]

    def __post_init__(self) -> None:
        if (
            self.left is self.right
            or type(self.structural) is not ProjectMultiFactStructuralAlignment
        ):
            raise ValueError("Multi-fact alignment requires two distinct localities.")
        if type(self.multiplicity_risks) is not tuple or len(
            set(self.multiplicity_risks)
        ) != len(self.multiplicity_risks):
            raise ValueError("Multiplicity risks must be a distinct exact tuple.")
        if type(self.requirements) is not tuple or len(set(self.requirements)) != len(
            self.requirements
        ):
            raise ValueError("Alignment requirements must be a distinct exact tuple.")
        if self.structural in {
            ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH,
            ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE,
        }:
            if self.grain_comparison is not None or self.finer is not None:
                raise ValueError("Non-comparable alignment cannot retain a winner.")
        elif (
            self.structural is not ProjectMultiFactStructuralAlignment.INCOMPATIBLE
            and self.grain_comparison is None
        ):
            raise ValueError("Concrete structural alignment requires grain evidence.")
        if (
            self.structural
            is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        ):
            if (
                ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED
                not in self.requirements
            ):
                raise ValueError("Reaggregation requires aggregate algebra authority.")
        if self.multiplicity_risks and (
            ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED
            not in self.requirements
        ):
            raise ValueError("Multiplicity risk requires aggregate algebra authority.")
        if self.grain_comparison is not None:
            comparison = self.grain_comparison
            if (
                comparison.left is not self.left.contextual_grain
                or comparison.right is not self.right.contextual_grain
            ):
                raise ValueError("Alignment comparison must retain exact localities.")
            if (
                self.left.contextual_grain.state is self.right.contextual_grain.state
                and self.left.contextual_grain.factors
                == self.right.contextual_grain.factors
            ):
                expected_structural = (
                    ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
                )
                expected_finer = None
            elif comparison.status is ProjectIRGrainComparisonStatus.EQUAL:
                expected_structural = (
                    ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
                )
                expected_finer = None
            elif comparison.status is ProjectIRGrainComparisonStatus.LEFT_FINER:
                expected_structural = (
                    ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
                )
                expected_finer = self.left
            elif comparison.status is ProjectIRGrainComparisonStatus.RIGHT_FINER:
                expected_structural = (
                    ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
                )
                expected_finer = self.right
            elif self.common_grain.status in {
                ProjectCommonGrainStatus.UNIQUE,
                ProjectCommonGrainStatus.AMBIGUOUS,
            }:
                expected_structural = (
                    ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
                )
                expected_finer = None
            else:
                expected_structural = ProjectMultiFactStructuralAlignment.INCOMPATIBLE
                expected_finer = None
            if (
                self.structural is not expected_structural
                or self.finer is not expected_finer
            ):
                raise ValueError("Alignment structure must replay exact grain proof.")
        # Two home localities expose no JOIN multiplicity.
        if self.multiplicity_risks:
            raise ValueError("Alignment risks must replay exact locality evidence.")
        expected_requirements = (
            (ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
            if self.structural
            is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
            else ()
        )
        if self.requirements != expected_requirements:
            raise ValueError("Alignment requirements must derive independently.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectMultiFactNonConcreteRegionSubject:
    region: ProjectIRNonConcreteJoinRegion = field(
        repr=False, compare=False, hash=False
    )
    blockers: tuple[ProjectNonConcreteJoinUse, ...] = field(
        repr=False, compare=False, hash=False
    )
    identifiable_facts: tuple[ProjectAggregateFactOccurrence, ...]
    structural: ProjectMultiFactStructuralAlignment

    def __post_init__(self) -> None:
        if (
            type(self.region) is not ProjectIRNonConcreteJoinRegion
            or self.blockers != self.region.blockers
            or self.structural
            not in {
                ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH,
                ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE,
            }
        ):
            raise ValueError("Non-concrete multi-fact subject requires exact blockers.")
        # No blocker is an ambiguous relationship path: no JOIN resolves one.
        if (
            self.structural
            is not ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
        ):
            raise ValueError("Non-concrete classification must retain exact cause.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectMultiFactAnalysis:
    evaluation: ProjectIREvaluationContextStage = field(
        repr=False, compare=False, hash=False
    )
    base_relational: ProjectIRRelationalPropertyStage = field(
        repr=False, compare=False, hash=False
    )
    join_regions: ProjectIRJoinRegionStage = field(
        repr=False, compare=False, hash=False
    )
    facts: tuple[ProjectAggregateFactOccurrence, ...]
    home_localities: tuple[ProjectAggregateFactHomeLocality, ...]
    non_concrete_regions: tuple[ProjectMultiFactNonConcreteRegionSubject, ...]
    home_alignments: tuple[ProjectMultiFactAlignment, ...]
    facts_by_context: Mapping[
        ProjectIRPlanNodeRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = field(repr=False, compare=False, hash=False)
    facts_by_home_output: Mapping[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if (
            type(self.evaluation) is not ProjectIREvaluationContextStage
            or type(self.base_relational) is not ProjectIRRelationalPropertyStage
            or type(self.join_regions) is not ProjectIRJoinRegionStage
            or self.base_relational.origins.evaluation is not self.evaluation
            or self.join_regions.base_plan is not self.evaluation.project_plan
            or self.join_regions.base_relational is not self.base_relational
        ):
            raise ValueError("Multi-fact analysis requires exact shared roots.")
        expected_fact_roots = tuple(
            (context, position, aggregate_result)
            for context in self.evaluation.aggregate_contexts
            for position, aggregate_result in enumerate(context.aggregate_results)
        )
        if len(self.facts) != len(expected_fact_roots) or any(
            fact.context is not context
            or fact.aggregate_result_position != position
            or fact.aggregate_result is not aggregate_result
            for fact, (context, position, aggregate_result) in zip(
                self.facts, expected_fact_roots, strict=True
            )
        ):
            raise ValueError("Aggregate fact catalog must cover every result once.")
        if len(self.home_localities) != len(self.facts) or any(
            locality.fact is not fact
            for locality, fact in zip(self.home_localities, self.facts, strict=True)
        ):
            raise ValueError("Every aggregate fact requires one home locality.")
        # Every JOIN region is non-concrete: no authored JOIN joins by itself.
        if tuple(item.region for item in self.non_concrete_regions) != (
            self.join_regions.regions
        ):
            raise ValueError("Multi-fact analysis must retain every JOIN region.")
        expected_home_pairs = tuple(
            (self.home_localities[left], self.home_localities[right])
            for left in range(len(self.home_localities))
            for right in range(left + 1, len(self.home_localities))
            if self.facts[left].context is self.facts[right].context
        )
        if len(self.home_alignments) != len(expected_home_pairs) or any(
            alignment.left is not left or alignment.right is not right
            for alignment, (left, right) in zip(
                self.home_alignments, expected_home_pairs, strict=True
            )
        ):
            raise ValueError("Home alignments must retain deterministic i < j order.")
        expected_by_context: dict[
            ProjectIRPlanNodeRef, tuple[ProjectAggregateFactOccurrence, ...]
        ] = {
            context.operator.node.ref: tuple(
                fact for fact in self.facts if fact.context is context
            )
            for context in self.evaluation.aggregate_contexts
        }
        expected_by_home: dict[
            ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
        ] = {}
        for fact in self.facts:
            output_ref = fact.home_relation_properties.output.occurrence.ref
            expected_by_home[output_ref] = (
                *expected_by_home.get(output_ref, ()),
                fact,
            )
        if not _same_object_index(self.facts_by_context, expected_by_context):
            raise ValueError("Multi-fact context facts index must be complete.")
        if not _same_object_index(self.facts_by_home_output, expected_by_home):
            raise ValueError("Multi-fact home facts index must be complete.")
        object.__setattr__(
            self, "facts_by_context", MappingProxyType(dict(self.facts_by_context))
        )
        object.__setattr__(
            self,
            "facts_by_home_output",
            MappingProxyType(dict(self.facts_by_home_output)),
        )


def _properties_for_output(
    properties: Mapping[ProjectIROutputValueRef, ProjectIROutputRelationalProperties],
    output: ProjectIRRelationRowOutput,
) -> ProjectIROutputRelationalProperties:
    item = properties.get(output.occurrence.ref)
    if item is None or item.output is not output:
        raise ValueError("Aggregate fact output requires one relational property.")
    return item


def project_aggregate_stage_field(
    properties: ProjectIROutputRelationalProperties,
    select_fact: ProjectModuleSelectFact,
) -> ProjectIROutputFieldOccurrence | None:
    """The one aggregate-stage field of a selected aggregate, or None.

    The stage row is the pre-window result, so a selected window before the
    aggregate shifts its final ordinal but not its stage field.
    """

    matches = tuple(
        item for item in properties.fields if item.evidence is select_fact.field
    )
    return matches[0] if len(matches) == 1 else None


def _build_fact(
    *,
    base_properties: Mapping[
        ProjectIROutputValueRef, ProjectIROutputRelationalProperties
    ],
    context: ProjectIRAggregateEvaluationContext,
    aggregate_result_position: int,
    aggregate_result: ProjectAggregateResultFact,
) -> ProjectAggregateFactOccurrence:
    select_matches = tuple(
        item
        for item in context.semantic_facts.select_facts
        if item.aggregate_result_fact is aggregate_result
    )
    if len(select_matches) != 1 or select_matches[0].field is None:
        raise ValueError("Aggregate result requires one exact selected field.")
    select_fact = select_matches[0]
    ordinal = select_fact.selected_output_ordinal
    input_properties = _properties_for_output(base_properties, context.input_row_output)
    result_properties = _properties_for_output(
        base_properties, context.result_row_output
    )
    home_properties = _properties_for_output(
        base_properties, context.fragment.root_relation_output
    )
    stage_scalar = project_aggregate_stage_field(result_properties, select_fact)
    if stage_scalar is None or ordinal >= len(home_properties.fields):
        raise ValueError("Aggregate selected ordinal is outside exact row authority.")
    home_field = home_properties.fields[ordinal]
    final_matches = tuple(
        output
        for output in context.fragment.final_scalar_outputs
        if output.field.anchor.identity.field_position == ordinal
    )
    value_matches = tuple(
        value_class
        for value_class in home_properties.value_classes
        if any(member is home_field for member in value_class.members)
    )
    if len(final_matches) != 1 or len(value_matches) != 1:
        raise ValueError("Aggregate fact requires exact final field/value authority.")
    return ProjectAggregateFactOccurrence(
        identity=ProjectAggregateFactIdentity(
            aggregate_node=context.operator.node.ref,
            aggregate_result_position=aggregate_result_position,
        ),
        context=context,
        aggregate_result=aggregate_result,
        select_fact=select_fact,
        selected_output_ordinal=ordinal,
        stage_scalar_output=stage_scalar,
        final_scalar_output=final_matches[0],
        input_row_properties=input_properties,
        result_row_properties=result_properties,
        home_relation_properties=home_properties,
        home_field=home_field,
        home_value_class=value_matches[0],
        source_intrinsic_grain=input_properties.grain,
        result_intrinsic_grain=result_properties.grain,
    )


def _grain_index(
    authority: ProjectIRProvidedIntrinsicGrain,
) -> ProjectGrainDependencyIndex:
    universe = ProjectGrainFactorUniverse(factors=authority.factors)
    return _compile_grain_dependency_index(universe, authority.dependencies)


def _factor_set(
    index: ProjectGrainDependencyIndex,
    factors: tuple[ProjectGrainFactorIdentity, ...],
) -> ProjectGrainFactorSet:
    selected = set(factors)
    ordered = tuple(
        factor.identity
        for factor in index.universe.factors
        if factor.identity in selected
    )
    if len(ordered) != len(factors):
        raise ValueError("Fact grain factors require the exact comparison universe.")
    return ProjectGrainFactorSet(universe=index.universe, factors=ordered)


def _determine(
    index: ProjectGrainDependencyIndex,
    seed: ProjectGrainFactorSet,
    requested: ProjectGrainFactorSet,
) -> ProjectFactGrainDetermination:
    if seed.universe is not index.universe or requested.universe is not index.universe:
        raise ValueError("Grain determination requires one exact index.")
    closure = grain_dependency_closure(index, seed)
    status = (
        ProjectFactGrainDirectionStatus.PROVEN
        if requested.mask & closure.mask == requested.mask
        else ProjectFactGrainDirectionStatus.NOT_PROVEN
    )
    return ProjectFactGrainDetermination(
        index=index,
        seed=seed,
        requested=requested,
        closure=closure,
        status=status,
    )


def _compare_grains(
    index: ProjectGrainDependencyIndex,
    left: ProjectFactContextualGrain,
    right: ProjectFactContextualGrain,
) -> ProjectFactGrainComparison:
    left_set = _factor_set(index, left.factors)
    right_set = _factor_set(index, right.factors)
    left_to_right = _determine(index, left_set, right_set)
    right_to_left = _determine(index, right_set, left_set)
    status = {
        (
            ProjectFactGrainDirectionStatus.PROVEN,
            ProjectFactGrainDirectionStatus.PROVEN,
        ): ProjectIRGrainComparisonStatus.EQUAL,
        (
            ProjectFactGrainDirectionStatus.PROVEN,
            ProjectFactGrainDirectionStatus.NOT_PROVEN,
        ): ProjectIRGrainComparisonStatus.LEFT_FINER,
        (
            ProjectFactGrainDirectionStatus.NOT_PROVEN,
            ProjectFactGrainDirectionStatus.PROVEN,
        ): ProjectIRGrainComparisonStatus.RIGHT_FINER,
        (
            ProjectFactGrainDirectionStatus.NOT_PROVEN,
            ProjectFactGrainDirectionStatus.NOT_PROVEN,
        ): ProjectIRGrainComparisonStatus.INCOMPARABLE,
    }[(left_to_right.status, right_to_left.status)]
    return ProjectFactGrainComparison(
        left=left,
        right=right,
        index=index,
        left_to_right=left_to_right,
        right_to_left=right_to_left,
        status=status,
    )


def _home_locality(
    fact: ProjectAggregateFactOccurrence,
) -> ProjectAggregateFactHomeLocality:
    contextual = ProjectFactContextualGrain(
        authority=fact.result_intrinsic_grain,
        state=fact.result_intrinsic_grain.state,
        factors=fact.result_intrinsic_grain.active,
        evidence=fact,
    )
    return ProjectAggregateFactHomeLocality(
        fact=fact,
        home_relation_properties=fact.home_relation_properties,
        home_field=fact.home_field,
        contextual_grain=contextual,
    )


def _localized_input_factors(
    *,
    grain: ProjectIRProvidedIntrinsicGrain,
    introduction_use: ProjectIRJoinInputUseOccurrence | CompiledGrainUse,
    final_grain: ProjectIRProvidedIntrinsicGrain,
) -> tuple[ProjectGrainFactorIdentity, ...]:
    from pietto._project.project_ir_joins import _is_join_factor
    from pietto._project.project_grain import CompiledGrainFactorIdentity
    from pietto._project.project_query_block_ir import CompiledIRRowOutput

    localized: list[ProjectGrainFactorIdentity] = []
    carried_join_output = isinstance(grain.output, ProjectIRJoinRowOutput) or (
        type(grain.output) is CompiledIRRowOutput and grain.output.node.kind == "join"
    )
    for factor in grain.active:

        def retains_source(
            retained: ProjectJoinGrainFactorIdentity | CompiledGrainFactorIdentity,
        ) -> bool:
            source = retained.source_factor
            while _is_join_factor(source):
                if source is factor:
                    return True
                source = source.source_factor
            return source is factor

        matches = tuple(
            retained
            for retained in final_grain.active
            if (
                (_is_join_factor(factor) and retained == factor)
                or (
                    _is_join_factor(retained)
                    and retains_source(retained)
                    and retained.introduction_use
                    == (
                        factor.introduction_use
                        if carried_join_output and _is_join_factor(factor)
                        else introduction_use.ref
                    )
                )
                or (
                    not _is_join_factor(factor)
                    and _is_join_factor(retained)
                    and retained.base == factor
                    and retained.introduction_use == introduction_use.ref
                )
            )
        )
        if len(matches) != 1:
            raise ValueError("JOIN input grain requires one exact contextual factor.")
        localized.append(matches[0])
    return tuple(localized)


def _add_actual_candidate(
    candidates: list[ProjectActualGrainCandidate],
    *,
    index: ProjectGrainDependencyIndex,
    kind: ProjectActualGrainAuthorityKind,
    evidence: tuple[object, ...],
    factors: tuple[ProjectGrainFactorIdentity, ...],
    allow_empty: bool,
) -> None:
    if not factors and not allow_empty:
        return
    factor_set = _factor_set(index, factors)
    authority = ProjectActualGrainAuthority(kind=kind, evidence=evidence)
    existing = next(
        (
            candidate
            for candidate in candidates
            if candidate.factors.factors == factor_set.factors
        ),
        None,
    )
    if existing is None:
        candidates.append(
            ProjectActualGrainCandidate(
                factors=factor_set,
                authorities=(authority,),
            )
        )
        return
    position = candidates.index(existing)
    candidates[position] = ProjectActualGrainCandidate(
        factors=existing.factors,
        authorities=(*existing.authorities, authority),
    )


def current_candidate_grounds(
    region: ProjectCurrentJoinRegion,
) -> tuple[
    tuple[
        ProjectActualGrainAuthorityKind,
        tuple[object, ...],
        tuple[ProjectGrainFactorIdentity, ...],
        bool,
    ],
    ...,
]:
    """Every current input/output authority in JOIN order, before factor grouping."""
    grain = region.final_properties.relational.grain
    grounds = []
    for join_position, (join, join_properties) in enumerate(
        zip(region.joins, region.join_properties, strict=True)
    ):
        for position, kind, properties in (
            (0, ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT, join.left_input),
            (1, ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT, join.right_input),
        ):
            if (
                position == 1
                and isinstance(join, ProjectCurrentBinaryJoin)
                and join.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
            ) or properties.grain.state is ProjectGrainBasisState.UNKNOWN:
                continue
            introduction = join.input_uses[position]
            factors = _localized_input_factors(
                grain=properties.grain,
                introduction_use=introduction,
                final_grain=grain,
            )
            grounds.append(
                (
                    kind,
                    (join, introduction, properties.grain),
                    factors,
                    properties.grain.state is ProjectGrainBasisState.GLOBAL,
                )
            )
        current = join_properties.relational.grain
        if current.state is ProjectGrainBasisState.UNKNOWN:
            continue
        current_factors = current.active
        if current is not grain:
            current_factors = _localized_input_factors(
                grain=current,
                introduction_use=region.joins[join_position + 1].input_uses[0],
                final_grain=grain,
            )
        grounds.append(
            (
                ProjectActualGrainAuthorityKind.JOIN_OUTPUT,
                (join, current),
                current_factors,
                current.state is ProjectGrainBasisState.GLOBAL,
            )
        )
    return tuple(grounds)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentMultiFactRegion:
    """Current row-grain evidence for the existing tail safety consumers only."""

    region: ProjectCurrentJoinRegion = field(repr=False)
    final_properties: ProjectCurrentJoinProperties = field(init=False, repr=False)
    grain_index: ProjectGrainDependencyIndex = field(init=False, repr=False)
    actual_candidates: tuple[ProjectActualGrainCandidate, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.region) is not ProjectCurrentJoinRegion:
            raise TypeError("Current grain bridge requires one exact current region.")
        final = self.region.final_properties
        grain = final.relational.grain
        index = _grain_index(grain)
        candidates: list[ProjectActualGrainCandidate] = []
        for kind, evidence, factors, allow_empty in current_candidate_grounds(
            self.region
        ):
            _add_actual_candidate(
                candidates,
                index=index,
                kind=kind,
                evidence=evidence,
                factors=factors,
                allow_empty=allow_empty,
            )
        object.__setattr__(self, "final_properties", final)
        object.__setattr__(self, "grain_index", index)
        object.__setattr__(self, "actual_candidates", tuple(candidates))


def _candidate_determinations(
    *,
    index: ProjectGrainDependencyIndex,
    grains: tuple[ProjectFactContextualGrain, ...],
    candidates: tuple[ProjectActualGrainCandidate, ...],
) -> Mapping[
    ProjectActualGrainCandidate,
    tuple[ProjectFactGrainDetermination, ...],
]:
    seeds = tuple(_factor_set(index, grain.factors) for grain in grains)
    return {
        candidate: tuple(_determine(index, seed, candidate.factors) for seed in seeds)
        for candidate in candidates
    }


def _candidate_dominator_masks(
    index: ProjectGrainDependencyIndex,
    candidates: tuple[ProjectActualGrainCandidate, ...],
) -> tuple[int, ...]:
    reaches = tuple(
        tuple(
            _determine(index, source.factors, target.factors).status
            is ProjectFactGrainDirectionStatus.PROVEN
            for target in candidates
        )
        for source in candidates
    )
    return tuple(
        sum(
            1 << other_position
            for other_position in range(len(candidates))
            if reaches[other_position][candidate_position]
            and not reaches[candidate_position][other_position]
        )
        for candidate_position in range(len(candidates))
    )


def _indexed_common_grain(
    *,
    actual_candidates: tuple[ProjectActualGrainCandidate, ...],
    determinations: Mapping[
        ProjectActualGrainCandidate,
        tuple[ProjectFactGrainDetermination, ...],
    ],
    dominator_masks: tuple[int, ...],
    left_position: int,
    right_position: int,
) -> ProjectCommonGrainResult:
    common: list[ProjectCommonGrainCandidateEvidence] = []
    common_positions: list[int] = []
    common_mask = 0
    for candidate_position, candidate in enumerate(actual_candidates):
        left_to_candidate = determinations[candidate][left_position]
        right_to_candidate = determinations[candidate][right_position]
        if (
            left_to_candidate.status is ProjectFactGrainDirectionStatus.PROVEN
            and right_to_candidate.status is ProjectFactGrainDirectionStatus.PROVEN
        ):
            common_mask |= 1 << candidate_position
            common_positions.append(candidate_position)
            common.append(
                ProjectCommonGrainCandidateEvidence(
                    candidate=candidate,
                    left_to_candidate=left_to_candidate,
                    right_to_candidate=right_to_candidate,
                )
            )
    retained = tuple(
        evidence
        for candidate_position, evidence in zip(common_positions, common, strict=True)
        if not dominator_masks[candidate_position] & common_mask
    )
    return ProjectCommonGrainResult(
        status=(
            ProjectCommonGrainStatus.NONE
            if not retained
            else (
                ProjectCommonGrainStatus.UNIQUE
                if len(retained) == 1
                else ProjectCommonGrainStatus.AMBIGUOUS
            )
        ),
        actual_candidates=actual_candidates,
        common_candidates=tuple(common),
        candidates=retained,
    )


def _common_grain(
    *,
    index: ProjectGrainDependencyIndex,
    left: ProjectFactContextualGrain,
    right: ProjectFactContextualGrain,
    actual_candidates: tuple[ProjectActualGrainCandidate, ...],
) -> ProjectCommonGrainResult:
    grains = (left, right)
    return _indexed_common_grain(
        actual_candidates=actual_candidates,
        determinations=_candidate_determinations(
            index=index,
            grains=grains,
            candidates=actual_candidates,
        ),
        dominator_masks=_candidate_dominator_masks(index, actual_candidates),
        left_position=0,
        right_position=1,
    )


def _build_alignment(
    *,
    left: ProjectAggregateFactLocality,
    right: ProjectAggregateFactLocality,
    index: ProjectGrainDependencyIndex,
    actual_candidates: tuple[ProjectActualGrainCandidate, ...],
) -> ProjectMultiFactAlignment:
    comparison = _compare_grains(index, left.contextual_grain, right.contextual_grain)
    common = _common_grain(
        index=index,
        left=left.contextual_grain,
        right=right.contextual_grain,
        actual_candidates=actual_candidates,
    )
    finer: ProjectAggregateFactLocality | None = None
    if (
        left.contextual_grain.state is right.contextual_grain.state
        and left.contextual_grain.factors == right.contextual_grain.factors
    ):
        structural = ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    elif comparison.status is ProjectIRGrainComparisonStatus.EQUAL:
        structural = ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
    elif comparison.status is ProjectIRGrainComparisonStatus.LEFT_FINER:
        structural = ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        finer = left
    elif comparison.status is ProjectIRGrainComparisonStatus.RIGHT_FINER:
        structural = ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        finer = right
    elif common.status in {
        ProjectCommonGrainStatus.UNIQUE,
        ProjectCommonGrainStatus.AMBIGUOUS,
    }:
        structural = ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
    else:
        structural = ProjectMultiFactStructuralAlignment.INCOMPATIBLE
    requirements = (
        (ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
        if structural is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        else ()
    )
    return ProjectMultiFactAlignment(
        left=left,
        right=right,
        structural=structural,
        grain_comparison=comparison,
        common_grain=common,
        finer=finer,
        multiplicity_risks=(),
        requirements=requirements,
    )


def _home_alignments(
    facts: tuple[ProjectAggregateFactOccurrence, ...],
    home_localities: tuple[ProjectAggregateFactHomeLocality, ...],
) -> tuple[ProjectMultiFactAlignment, ...]:
    alignments: list[ProjectMultiFactAlignment] = []
    for context in tuple(dict.fromkeys(fact.identity.aggregate_node for fact in facts)):
        positions = tuple(
            position
            for position, fact in enumerate(facts)
            if fact.identity.aggregate_node == context
        )
        if len(positions) < 2:
            continue
        first = home_localities[positions[0]]
        index = _grain_index(first.contextual_grain.authority)
        candidates: list[ProjectActualGrainCandidate] = []
        for position in positions:
            locality = home_localities[position]
            if (
                locality.contextual_grain.authority
                is not first.contextual_grain.authority
            ):
                raise ValueError(
                    "Same-context facts require one result grain authority."
                )
            _add_actual_candidate(
                candidates,
                index=index,
                kind=ProjectActualGrainAuthorityKind.FACT_LOCALITY,
                evidence=(locality,),
                factors=locality.contextual_grain.factors,
                allow_empty=(
                    locality.contextual_grain.state is ProjectGrainBasisState.GLOBAL
                ),
            )
        actual_candidates = tuple(candidates)
        alignments.extend(
            _build_alignment(
                left=home_localities[left_position],
                right=home_localities[right_position],
                index=index,
                actual_candidates=actual_candidates,
            )
            for offset, left_position in enumerate(positions)
            for right_position in positions[offset + 1 :]
        )
    return tuple(alignments)


def _binding_identifies_fact(
    binding: object,
    fact: ProjectAggregateFactOccurrence,
) -> bool:
    output = getattr(binding, "output", None)
    if output is fact.home_relation_properties:
        return True
    target = getattr(binding, "target", None)
    return target is not None and (
        target.target_occurrence is fact.context.semantic_facts.owner
    )


def _non_concrete_subject(
    *,
    region: ProjectIRNonConcreteJoinRegion,
    facts: tuple[ProjectAggregateFactOccurrence, ...],
) -> ProjectMultiFactNonConcreteRegionSubject:
    identifiable = tuple(
        fact
        for fact in facts
        if any(
            _binding_identifies_fact(binding, fact)
            for binding in region.ledger.bindings
        )
    )
    return ProjectMultiFactNonConcreteRegionSubject(
        region=region,
        blockers=region.blockers,
        identifiable_facts=identifiable,
        structural=ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE,
    )


def build_project_multifact_analysis(
    *,
    evaluation: ProjectIREvaluationContextStage,
    base_relational: ProjectIRRelationalPropertyStage,
    join_regions: ProjectIRJoinRegionStage,
) -> ProjectMultiFactAnalysis:
    """Build exact aggregate facts and useful home/JOIN-local alignments."""

    if (
        type(evaluation) is not ProjectIREvaluationContextStage
        or type(base_relational) is not ProjectIRRelationalPropertyStage
        or type(join_regions) is not ProjectIRJoinRegionStage
        or base_relational.origins.evaluation is not evaluation
        or join_regions.base_plan is not evaluation.project_plan
        or join_regions.base_relational is not base_relational
    ):
        raise ValueError("Multi-fact construction requires exact shared roots.")
    base_properties = {
        item.output.occurrence.ref: item for item in base_relational.outputs
    }
    if len(base_properties) != len(base_relational.outputs):
        raise ValueError("Multi-fact property indexes require distinct outputs.")
    facts = tuple(
        _build_fact(
            base_properties=base_properties,
            context=context,
            aggregate_result_position=position,
            aggregate_result=aggregate_result,
        )
        for context in evaluation.aggregate_contexts
        for position, aggregate_result in enumerate(context.aggregate_results)
    )
    home_localities = tuple(_home_locality(fact) for fact in facts)
    facts_by_context: dict[
        ProjectIRPlanNodeRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = {context.operator.node.ref: () for context in evaluation.aggregate_contexts}
    facts_by_home: dict[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = {}
    for fact in facts:
        facts_by_context[fact.identity.aggregate_node] = (
            *facts_by_context[fact.identity.aggregate_node],
            fact,
        )
        output_ref = fact.home_relation_properties.output.occurrence.ref
        facts_by_home[output_ref] = (*facts_by_home.get(output_ref, ()), fact)
    non_concrete_regions = tuple(
        _non_concrete_subject(region=region, facts=facts)
        for region in join_regions.regions
    )
    return ProjectMultiFactAnalysis(
        evaluation=evaluation,
        base_relational=base_relational,
        join_regions=join_regions,
        facts=facts,
        home_localities=home_localities,
        non_concrete_regions=non_concrete_regions,
        home_alignments=_home_alignments(facts, home_localities),
        facts_by_context=facts_by_context,
        facts_by_home_output=facts_by_home,
    )


def analyze_project_fact_locality_pair(
    analysis: ProjectMultiFactAnalysis,
    left: ProjectAggregateFactLocality,
    right: ProjectAggregateFactLocality,
) -> ProjectMultiFactAlignment:
    """Query two exact fact localities without creating a global pair table."""

    if (
        type(analysis) is not ProjectMultiFactAnalysis
        or type(left) is not ProjectAggregateFactHomeLocality
        or type(right) is not ProjectAggregateFactHomeLocality
    ):
        raise TypeError("Pair query requires one exact analysis and two localities.")
    if left is right:
        raise ValueError("Pair query requires two distinct fact localities.")
    retained_localities = analysis.home_localities
    if not any(left is item for item in retained_localities) or not any(
        right is item for item in retained_localities
    ):
        raise ValueError("Pair query localities must belong to the exact analysis.")
    for alignment in analysis.home_alignments:
        if alignment.left is left and alignment.right is right:
            return alignment
    if left.fact.context is right.fact.context:
        existing = next(
            item
            for item in analysis.home_alignments
            if item.left is right and item.right is left
        )
        return _build_alignment(
            left=left,
            right=right,
            index=existing.grain_comparison.index
            if existing.grain_comparison is not None
            else _grain_index(left.contextual_grain.authority),
            actual_candidates=existing.common_grain.actual_candidates,
        )
    return ProjectMultiFactAlignment(
        left=left,
        right=right,
        structural=ProjectMultiFactStructuralAlignment.INCOMPATIBLE,
        grain_comparison=None,
        common_grain=ProjectCommonGrainResult(
            status=ProjectCommonGrainStatus.NONE,
            actual_candidates=(),
            common_candidates=(),
            candidates=(),
        ),
        finer=None,
        multiplicity_risks=(),
        requirements=(),
    )


@dataclass(frozen=True, slots=True, eq=False)
class CompiledGrainUse:
    ir: Any = field(repr=False)
    ref: Any
    producer: Any = field(repr=False)

    def __post_init__(self):
        from pietto._project.project_query_block_ir import (
            CompiledQueryBlockIR,
            CompiledIRReference,
        )
        from pietto._project.project_compiled_schema import Address

        if (
            type(self.ir) is not CompiledQueryBlockIR
            or type(self.ref) is not CompiledIRReference
        ):
            raise ValueError("COMPILED_GRAIN_USE")
        address = Address(self.ref.kind, self.ref.position)
        if self.ref.kind != "use" or self.ir.references.get(address) is not self.ref:
            raise ValueError("COMPILED_GRAIN_USE")
        record = self.ir.completed.root.records[address]
        if not any(
            o is self.producer and o.ref is self.ir.references[record.get("producer")]
            for o in self.ir.operators
        ):
            raise ValueError("COMPILED_GRAIN_USE_PRODUCER")


@dataclass(frozen=True, slots=True, eq=False)
class CompiledMultiplicityExposure:
    join: Any = field(repr=False)
    factor_additions: tuple

    def __post_init__(self):
        from pietto._project.project_query_block_ir import CompiledIROperator
        from pietto._project.project_grain import CompiledGrainFactorIdentity

        if (
            type(self.join) is not CompiledIROperator
            or self.join.kind != "join"
            or not self.factor_additions
        ):
            raise ValueError("COMPILED_MULTIPLICITY_EXPOSURE")
        for factor in self.factor_additions:
            if (
                type(factor) is not CompiledGrainFactorIdentity
                or factor.base is None
                or factor.ref is not self.join.ref
            ):
                raise ValueError("COMPILED_MULTIPLICITY_EXPOSURE")


@dataclass(frozen=True, slots=True, eq=False)
class CompiledMultiFactRegion:
    ir: Any = field(repr=False)
    joins: tuple = field(repr=False)
    uses: Mapping[Any, CompiledGrainUse] = field(repr=False)
    final_properties: ProjectIROutputRelationalProperties = field(repr=False)
    grain_index: ProjectGrainDependencyIndex = field(repr=False)
    actual_candidates: tuple[ProjectActualGrainCandidate, ...]


def compiled_region_inputs(ir, stage):
    """Read one same-declaration JOIN region, never enter a named producer."""
    from pietto._project.project_query_block_ir import (
        CompiledQueryBlockIR,
        CompiledIROperator,
    )

    if (
        type(ir) is not CompiledQueryBlockIR
        or type(stage) is not CompiledIROperator
        or stage.kind != "aggregate"
    ):
        raise ValueError("COMPILED_AGGREGATE_REGION_INPUT")
    joins = tuple(
        o for o in ir.operators if o.kind == "join" and o.owner is stage.owner
    )
    records = ir.completed.root.records
    by_address = {o.record.address: o for o in ir.operators}
    inputs = tuple(
        (
            join,
            tuple(
                (address, by_address[records[address].get("producer")])
                for address in join.record.get("inputs")
            ),
        )
        for join in joins
    )
    if not joins or stage.record.get("risk_law") is None:
        raise ValueError("COMPILED_AGGREGATE_REGION")
    return inputs


def build_compiled_region(ir, stage):
    inputs = compiled_region_inputs(ir, stage)
    joins = tuple(join for join, _ in inputs)
    final = joins[-1].properties.relational
    index = _grain_index(final.grain)
    uses = {
        address: CompiledGrainUse(ir, ir.references[address], producer)
        for _join, pairs in inputs
        for address, producer in pairs
    }
    candidates = []
    for position, (join, pairs) in enumerate(inputs):
        for side, (address, producer) in enumerate(pairs):
            properties = producer.properties.relational
            if (
                side == 1 and join.record.get("kind") in ("semi", "anti")
            ) or properties.grain.state is ProjectGrainBasisState.UNKNOWN:
                continue
            use = uses[address]
            factors = _localized_input_factors(
                grain=properties.grain, introduction_use=use, final_grain=final.grain
            )
            _add_actual_candidate(
                candidates,
                index=index,
                kind=ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT
                if side == 0
                else ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT,
                evidence=(join, use, properties.grain),
                factors=factors,
                allow_empty=properties.grain.state is ProjectGrainBasisState.GLOBAL,
            )
        current = join.properties.relational.grain
        if current.state is ProjectGrainBasisState.UNKNOWN:
            continue
        factors = (
            current.active
            if current is final.grain
            else _localized_input_factors(
                grain=current,
                introduction_use=uses[inputs[position + 1][1][0][0]],
                final_grain=final.grain,
            )
        )
        _add_actual_candidate(
            candidates,
            index=index,
            kind=ProjectActualGrainAuthorityKind.JOIN_OUTPUT,
            evidence=(join, current),
            factors=factors,
            allow_empty=current.state is ProjectGrainBasisState.GLOBAL,
        )
    return CompiledMultiFactRegion(
        ir, joins, MappingProxyType(uses), final, index, tuple(candidates)
    )


def verify_compiled_region(region, ir, stage):
    """Check all candidate grounds from actual current inputs, not a saved list."""
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_grain import _compile_grain_dependency_index

    inputs = compiled_region_inputs(ir, stage)
    joins = tuple(join for join, _ in inputs)
    need(
        type(region) is CompiledMultiFactRegion
        and region.ir is ir
        and len(region.joins) == len(joins)
        and all(a is b for a, b in zip(region.joins, joins, strict=True))
        and region.final_properties is joins[-1].properties.relational,
        "AGGREGATE_REGION",
    )
    expected_uses = tuple(
        address for _join, pairs in inputs for address, _producer in pairs
    )
    need(
        type(region.uses) is MappingProxyType and tuple(region.uses) == expected_uses,
        "AGGREGATE_REGION_USES",
    )
    for _join, pairs in inputs:
        for address, producer in pairs:
            use = region.uses[address]
            need(
                type(use) is CompiledGrainUse
                and use.ir is ir
                and use.ref is ir.references[address]
                and use.producer is producer,
                "AGGREGATE_REGION_USE",
            )
    grain, index = region.final_properties.grain, region.grain_index
    need(
        index.universe.factors is grain.factors
        or index.universe.factors == grain.factors,
        "AGGREGATE_GRAIN_UNIVERSE",
    )
    need(index.facts == grain.dependencies, "AGGREGATE_GRAIN_DEPENDENCIES")
    expected_index = _compile_grain_dependency_index(index.universe, grain.dependencies)
    need(
        index == expected_index
        and tuple(index.positions.items()) == tuple(expected_index.positions.items()),
        "AGGREGATE_GRAIN_INDEX",
    )
    typed_uses = cast(Mapping[Any, CompiledGrainUse], region.uses)
    expected = []
    for position, (join, pairs) in enumerate(inputs):
        for side, (address, producer) in enumerate(pairs):
            local = producer.properties.relational.grain
            if (
                side == 1 and join.record.get("kind") in ("semi", "anti")
            ) or local.state is ProjectGrainBasisState.UNKNOWN:
                continue
            use = typed_uses[address]
            factors = _localized_input_factors(
                grain=local, introduction_use=use, final_grain=grain
            )
            if factors or local.state is ProjectGrainBasisState.GLOBAL:
                expected.append(
                    (
                        factors,
                        ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT
                        if side == 0
                        else ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT,
                        (join, use, local),
                    )
                )
        local = join.properties.relational.grain
        if local.state is ProjectGrainBasisState.UNKNOWN:
            continue
        factors = (
            local.active
            if local is grain
            else _localized_input_factors(
                grain=local,
                introduction_use=typed_uses[inputs[position + 1][1][0][0]],
                final_grain=grain,
            )
        )
        if factors or local.state is ProjectGrainBasisState.GLOBAL:
            expected.append(
                (factors, ProjectActualGrainAuthorityKind.JOIN_OUTPUT, (join, local))
            )
    groups = {}
    for factors, kind, evidence in expected:
        groups.setdefault(factors, []).append((kind, evidence))
    need(
        type(region.actual_candidates) is tuple
        and len(region.actual_candidates) == len(groups),
        "AGGREGATE_CANDIDATE_INVENTORY",
    )
    for candidate, (factors, authorities) in zip(
        region.actual_candidates, groups.items(), strict=True
    ):
        need(
            type(candidate) is ProjectActualGrainCandidate
            and candidate.factors.universe is index.universe
            and candidate.factors.factors == factors
            and len(candidate.authorities) == len(authorities),
            "AGGREGATE_CANDIDATE",
        )
        for actual, (kind, evidence) in zip(
            candidate.authorities, authorities, strict=True
        ):
            need(
                type(actual) is ProjectActualGrainAuthority
                and actual.kind is kind
                and len(actual.evidence) == len(evidence)
                and all(a is b for a, b in zip(actual.evidence, evidence, strict=True)),
                "AGGREGATE_CANDIDATE_AUTHORITY",
            )


def verify_compiled_grain_comparison(value, index, left, right):
    """Independently check both directions against the actual dependency graph."""
    from pietto._project.project_compiled_verification import need

    need(
        type(value) is ProjectFactGrainComparison
        and value.left is left
        and value.right is right,
        "GRAIN_COMPARISON_ROOT",
    )
    for direction, seed, requested in (
        (value.left_to_right, left, right),
        (value.right_to_left, right, left),
    ):
        need(
            type(direction) is ProjectFactGrainDetermination
            and direction.index is index
            and direction.seed.universe is index.universe
            and direction.seed.factors == seed.factors
            and direction.requested.universe is index.universe
            and direction.requested.factors == requested.factors,
            "GRAIN_COMPARISON_DIRECTION",
        )
        closure = grain_dependency_closure(index, direction.seed)
        expected = (
            ProjectFactGrainDirectionStatus.PROVEN
            if direction.requested.mask & closure.mask == direction.requested.mask
            else ProjectFactGrainDirectionStatus.NOT_PROVEN
        )
        need(
            direction.closure.universe is index.universe
            and direction.closure.factors == closure.factors
            and direction.status is expected,
            "GRAIN_COMPARISON_CLOSURE",
        )
    value.__post_init__()
