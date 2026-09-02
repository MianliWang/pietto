"""Private per-aggregate locality, chasm, and multi-fact analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

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
    ProjectIRUseRef,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
    ProjectIREvaluationContextStage,
)
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinOutputProperties,
    ProjectIRJoinRegionStage,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
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
from pietto._project.project_relationship_paths import ProjectRelationshipPathStep
from pietto._project.project_relationship_uses import (
    ProjectJoinUseIssueKind,
    ProjectNonConcreteJoinUse,
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
            or self.stage_scalar_output.field_position != ordinal
            or self.stage_scalar_output.evidence is not self.select_fact.field
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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFactMultiplicityExposure:
    join: ProjectIRBinaryJoinOccurrence = field(repr=False, compare=False, hash=False)
    factor_additions: tuple[ProjectJoinGrainFactorIdentity, ...]

    def __post_init__(self) -> None:
        if type(self.join) is not ProjectIRBinaryJoinOccurrence:
            raise TypeError("Multiplicity exposure requires one exact JOIN.")
        if not self.factor_additions or any(
            type(factor) is not ProjectJoinGrainFactorIdentity
            for factor in self.factor_additions
        ):
            raise ValueError("Multiplicity exposure requires exact added factors.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAggregateFactHomeLocality:
    fact: ProjectAggregateFactOccurrence
    home_relation_properties: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    home_field: ProjectIROutputFieldOccurrence
    contextual_grain: ProjectFactContextualGrain
    relationship_entry_path: None = field(init=False, default=None)
    introduction_use: None = field(init=False, default=None)
    introduction_join: None = field(init=False, default=None)

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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAggregateFactJoinLocality:
    fact: ProjectAggregateFactOccurrence
    region: ProjectIRConcreteJoinRegion = field(repr=False, compare=False, hash=False)
    introduction_use: ProjectIRJoinInputUseOccurrence
    introduction_join: ProjectIRBinaryJoinOccurrence = field(
        repr=False, compare=False, hash=False
    )
    side: ProjectFactJoinInputSide
    relationship_entry_path: ProjectRelationshipPathStep | None = field(
        repr=False, compare=False, hash=False
    )
    carried_fields: tuple[ProjectIRJoinedRowField, ...]
    final_region_properties: ProjectIRJoinOutputProperties = field(
        repr=False, compare=False, hash=False
    )
    final_field: ProjectIRJoinedRowField
    contextual_grain: ProjectFactContextualGrain
    final_grain_comparison: ProjectFactGrainComparison
    multiplicity_exposures: tuple[ProjectFactMultiplicityExposure, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.fact) is not ProjectAggregateFactOccurrence
            or type(self.region) is not ProjectIRConcreteJoinRegion
            or not any(self.introduction_join is join for join in self.region.joins)
            or type(self.introduction_use) is not ProjectIRJoinInputUseOccurrence
            or self.side
            not in {ProjectFactJoinInputSide.LEFT, ProjectFactJoinInputSide.RIGHT}
        ):
            raise ValueError("JOIN locality requires exact fact and region roots.")
        side_position = 0 if self.side is ProjectFactJoinInputSide.LEFT else 1
        if (
            self.introduction_join.input_uses[side_position]
            is not self.introduction_use
        ):
            raise ValueError("JOIN locality side must match its introduction use.")
        expected_input = (
            self.introduction_join.left_input
            if side_position == 0
            else self.introduction_join.right_input
        )
        if expected_input is not self.fact.home_relation_properties:
            raise ValueError("JOIN locality must introduce the exact fact home output.")
        if (
            self.side is ProjectFactJoinInputSide.LEFT
            and self.relationship_entry_path is not None
        ) or (
            self.side is ProjectFactJoinInputSide.RIGHT
            and self.relationship_entry_path is not self.introduction_join.path_step
        ):
            raise ValueError("JOIN locality path authority must match its side.")
        start = self.region.joins.index(self.introduction_join)
        expected_fields: list[ProjectIRJoinedRowField] = []
        for join in self.region.joins[start:]:
            matches = tuple(
                joined_field
                for joined_field in join.output.row_shape.fields
                if joined_field.evidence is self.fact.home_field.evidence
                and joined_field.introduction_use is self.introduction_use
            )
            if len(matches) != 1:
                raise ValueError("JOIN locality requires one carried field per output.")
            expected_fields.append(matches[0])
        if self.carried_fields != tuple(expected_fields):
            raise ValueError("JOIN locality carried fields must retain region order.")
        if (
            self.final_region_properties.join is not self.region.joins[-1]
            or self.final_field is not self.carried_fields[-1]
            or self.contextual_grain.authority
            is not self.final_region_properties.relational.grain
            or self.contextual_grain.state is not self.fact.result_intrinsic_grain.state
            or self.contextual_grain.evidence is not self.introduction_use
            or self.final_grain_comparison.left is not self.contextual_grain
            or self.final_grain_comparison.right.authority
            is not self.final_region_properties.relational.grain
            or self.final_grain_comparison.right.state
            is not self.final_region_properties.relational.grain.state
            or self.final_grain_comparison.right.factors
            != self.final_region_properties.relational.grain.active
            or self.final_grain_comparison.right.evidence
            is not self.final_region_properties
        ):
            raise ValueError("JOIN locality requires exact final field and grain.")
        home_factors = self.fact.result_intrinsic_grain.active
        if len(home_factors) != len(self.contextual_grain.factors) or any(
            type(contextual) is not ProjectJoinGrainFactorIdentity
            or contextual.base != home
            or contextual.introduction_use != self.introduction_use.ref
            or contextual.nulling_joins != self.final_field.nulling_joins
            for home, contextual in zip(
                home_factors, self.contextual_grain.factors, strict=True
            )
        ):
            raise ValueError("JOIN locality factors must preserve base/use identity.")
        exposure_joins = tuple(
            exposure.join for exposure in self.multiplicity_exposures
        )
        exposure_positions = tuple(
            self.region.joins.index(join) for join in exposure_joins
        )
        if any(position < start for position in exposure_positions) or any(
            left >= right
            for left, right in zip(
                exposure_positions, exposure_positions[1:], strict=False
            )
        ):
            raise ValueError("Multiplicity exposures must retain later JOIN order.")
        expected_unresolved = tuple(
            factor
            for factor in self.final_grain_comparison.right.factors
            if factor not in self.final_grain_comparison.left_to_right.closure.factors
        )
        retained_additions = tuple(
            factor
            for exposure in self.multiplicity_exposures
            for factor in exposure.factor_additions
        )
        if (
            self.final_grain_comparison.status
            is ProjectIRGrainComparisonStatus.RIGHT_FINER
        ):
            if len(set(retained_additions)) != len(retained_additions) or set(
                retained_additions
            ) != set(expected_unresolved):
                raise ValueError(
                    "Multiplicity exposures must cover exact finer-region factors."
                )
        elif retained_additions:
            raise ValueError("Non-finer final grain cannot invent multiplicity risk.")


type ProjectAggregateFactLocality = (
    ProjectAggregateFactHomeLocality | ProjectAggregateFactJoinLocality
)


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
class ProjectFactChasmCandidate:
    region: ProjectIRConcreteJoinRegion = field(repr=False, compare=False, hash=False)
    common_grain: ProjectActualGrainCandidate
    localities: tuple[ProjectAggregateFactJoinLocality, ...]
    introduction_joins: tuple[ProjectIRBinaryJoinOccurrence, ...] = field(
        repr=False, compare=False, hash=False
    )
    contextual_factor_sets: tuple[ProjectGrainFactorSet, ...]
    pairwise_comparisons: tuple[ProjectFactGrainComparison, ...]
    common_determinations: tuple[ProjectFactGrainDetermination, ...]

    def __post_init__(self) -> None:
        if (
            type(self.region) is not ProjectIRConcreteJoinRegion
            or len(self.localities) < 2
        ):
            raise ValueError("Chasm candidate requires one region and multiple facts.")
        if any(locality.region is not self.region for locality in self.localities):
            raise ValueError("Chasm localities must share one exact region.")
        if len(self.contextual_factor_sets) != len(self.localities) or any(
            factor_set.factors != locality.contextual_grain.factors
            for factor_set, locality in zip(
                self.contextual_factor_sets, self.localities, strict=True
            )
        ):
            raise ValueError("Chasm must retain every contextual factor set.")
        expected_pairs = len(self.localities) * (len(self.localities) - 1) // 2
        if len(self.pairwise_comparisons) != expected_pairs or any(
            comparison.status is not ProjectIRGrainComparisonStatus.INCOMPARABLE
            for comparison in self.pairwise_comparisons
        ):
            raise ValueError("Chasm facts must remain mutually incomparable.")
        if len(self.common_determinations) != len(self.localities) or any(
            determination.requested is not self.common_grain.factors
            or determination.status is not ProjectFactGrainDirectionStatus.PROVEN
            for determination in self.common_determinations
        ):
            raise ValueError("Every chasm fact must determine the common grain.")
        expected_joins = tuple(
            join
            for join in self.region.joins
            if any(locality.introduction_join is join for locality in self.localities)
        )
        if self.introduction_joins != expected_joins:
            raise ValueError("Chasm JOIN evidence must retain region order.")

    def contains_pair(
        self,
        left: ProjectAggregateFactJoinLocality,
        right: ProjectAggregateFactJoinLocality,
    ) -> bool:
        return any(left is item for item in self.localities) and any(
            right is item for item in self.localities
        )


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
    chasms: tuple[ProjectFactChasmCandidate, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )

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
        if (
            ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION
            in self.multiplicity_risks
            and not self.chasms
        ):
            raise ValueError("Cross-fact multiplication requires exact chasm evidence.")
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
        expected_risks: list[ProjectMultiFactMultiplicityRisk] = []
        if self.grain_comparison is not None and (
            (
                type(self.left) is ProjectAggregateFactJoinLocality
                and self.left.multiplicity_exposures
            )
            or (
                type(self.right) is ProjectAggregateFactJoinLocality
                and self.right.multiplicity_exposures
            )
        ):
            expected_risks.append(ProjectMultiFactMultiplicityRisk.FANOUT_RISK)
        if self.chasms:
            if (
                type(self.left) is not ProjectAggregateFactJoinLocality
                or type(self.right) is not ProjectAggregateFactJoinLocality
                or any(
                    not chasm.contains_pair(self.left, self.right)
                    for chasm in self.chasms
                )
            ):
                raise ValueError("Alignment chasms must retain this exact pair.")
            expected_risks.append(
                ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION
            )
        if self.multiplicity_risks != tuple(expected_risks):
            raise ValueError("Alignment risks must replay exact locality evidence.")
        expected_requirements = (
            (ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
            if self.structural
            is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
            or expected_risks
            else ()
        )
        if self.requirements != expected_requirements:
            raise ValueError("Alignment requirements must derive independently.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectMultiFactConcreteRegion:
    region: ProjectIRConcreteJoinRegion = field(repr=False, compare=False, hash=False)
    final_properties: ProjectIRJoinOutputProperties = field(
        repr=False, compare=False, hash=False
    )
    grain_index: ProjectGrainDependencyIndex = field(
        repr=False, compare=False, hash=False
    )
    localities: tuple[ProjectAggregateFactJoinLocality, ...]
    actual_candidates: tuple[ProjectActualGrainCandidate, ...]
    fact_buckets: Mapping[
        ProjectActualGrainCandidate,
        tuple[ProjectAggregateFactJoinLocality, ...],
    ] = field(repr=False, compare=False, hash=False)
    chasms: tuple[ProjectFactChasmCandidate, ...]
    alignments: tuple[ProjectMultiFactAlignment, ...]

    def __post_init__(self) -> None:
        if (
            type(self.region) is not ProjectIRConcreteJoinRegion
            or self.final_properties.join is not self.region.joins[-1]
            or self.grain_index.universe.factors
            != self.final_properties.relational.grain.factors
            or self.grain_index.facts
            != self.final_properties.relational.grain.dependencies
        ):
            raise ValueError("Concrete multi-fact region requires exact final roots.")
        if any(locality.region is not self.region for locality in self.localities):
            raise ValueError("Concrete region localities must share one region.")
        if any(
            candidate.factors.universe is not self.grain_index.universe
            for candidate in self.actual_candidates
        ):
            raise ValueError("Actual candidates require the exact region universe.")
        if len(self.fact_buckets) != len(self.actual_candidates) or any(
            retained is not candidate
            for retained, candidate in zip(
                self.fact_buckets, self.actual_candidates, strict=True
            )
        ):
            raise ValueError("Candidate fact buckets must retain authority order.")
        for candidate in self.actual_candidates:
            expected = tuple(
                locality
                for locality in self.localities
                if _determine(
                    self.grain_index,
                    _factor_set(self.grain_index, locality.contextual_grain.factors),
                    candidate.factors,
                ).status
                is ProjectFactGrainDirectionStatus.PROVEN
            )
            supplied = self.fact_buckets[candidate]
            if len(supplied) != len(expected) or any(
                actual is not retained
                for actual, retained in zip(supplied, expected, strict=True)
            ):
                raise ValueError("Candidate fact bucket must be complete and ordered.")
        if any(chasm.region is not self.region for chasm in self.chasms):
            raise ValueError("Concrete region chasms must share one region.")
        expected_pairs = tuple(
            (self.localities[left], self.localities[right])
            for left in range(len(self.localities))
            for right in range(left + 1, len(self.localities))
        )
        if len(self.alignments) != len(expected_pairs) or any(
            alignment.left is not left or alignment.right is not right
            for alignment, (left, right) in zip(
                self.alignments, expected_pairs, strict=True
            )
        ):
            raise ValueError("Region alignments must retain deterministic i < j order.")
        object.__setattr__(
            self, "fact_buckets", MappingProxyType(dict(self.fact_buckets))
        )


_PATH_AMBIGUITY_ISSUES = frozenset(
    {
        ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_AMBIGUOUS,
        ProjectJoinUseIssueKind.AMBIGUOUS_RELATIONSHIP,
        ProjectJoinUseIssueKind.AMBIGUOUS_ENDPOINT_DIRECTION,
    }
)


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
        path_ambiguous = bool(self.identifiable_facts) and any(
            issue.kind in _PATH_AMBIGUITY_ISSUES
            for blocker in self.blockers
            for issue in blocker.issues
        )
        expected = (
            ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH
            if path_ambiguous
            else ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
        )
        if self.structural is not expected:
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
    concrete_regions: tuple[ProjectMultiFactConcreteRegion, ...]
    non_concrete_regions: tuple[ProjectMultiFactNonConcreteRegionSubject, ...]
    home_alignments: tuple[ProjectMultiFactAlignment, ...]
    facts_by_context: Mapping[
        ProjectIRPlanNodeRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = field(repr=False, compare=False, hash=False)
    facts_by_home_output: Mapping[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = field(repr=False, compare=False, hash=False)
    localities_by_introduction_use: Mapping[
        ProjectIRUseRef, tuple[ProjectAggregateFactJoinLocality, ...]
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
        expected_concrete = tuple(
            region
            for region in self.join_regions.regions
            if type(region) is ProjectIRConcreteJoinRegion
        )
        expected_non_concrete = tuple(
            region
            for region in self.join_regions.regions
            if type(region) is ProjectIRNonConcreteJoinRegion
        )
        if (
            tuple(item.region for item in self.concrete_regions) != expected_concrete
            or tuple(item.region for item in self.non_concrete_regions)
            != expected_non_concrete
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
        expected_by_use: dict[
            ProjectIRUseRef, tuple[ProjectAggregateFactJoinLocality, ...]
        ] = {use.ref: () for use in self.join_regions.structural.uses}
        for locality in (
            locality
            for region in self.concrete_regions
            for locality in region.localities
        ):
            use_ref = locality.introduction_use.ref
            expected_by_use[use_ref] = (*expected_by_use[use_ref], locality)
        if not _same_object_index(self.facts_by_context, expected_by_context):
            raise ValueError("Multi-fact context facts index must be complete.")
        if not _same_object_index(self.facts_by_home_output, expected_by_home):
            raise ValueError("Multi-fact home facts index must be complete.")
        if not _same_object_index(self.localities_by_introduction_use, expected_by_use):
            raise ValueError(
                "Multi-fact introduction localities index must be complete."
            )
        object.__setattr__(
            self, "facts_by_context", MappingProxyType(dict(self.facts_by_context))
        )
        object.__setattr__(
            self,
            "facts_by_home_output",
            MappingProxyType(dict(self.facts_by_home_output)),
        )
        object.__setattr__(
            self,
            "localities_by_introduction_use",
            MappingProxyType(dict(self.localities_by_introduction_use)),
        )

    @property
    def join_localities(self) -> tuple[ProjectAggregateFactJoinLocality, ...]:
        return tuple(
            locality
            for region in self.concrete_regions
            for locality in region.localities
        )

    @property
    def alignments(self) -> tuple[ProjectMultiFactAlignment, ...]:
        return (
            *self.home_alignments,
            *(
                alignment
                for region in self.concrete_regions
                for alignment in region.alignments
            ),
        )


def _properties_for_output(
    properties: Mapping[ProjectIROutputValueRef, ProjectIROutputRelationalProperties],
    output: ProjectIRRelationRowOutput,
) -> ProjectIROutputRelationalProperties:
    item = properties.get(output.occurrence.ref)
    if item is None or item.output is not output:
        raise ValueError("Aggregate fact output requires one relational property.")
    return item


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
    if ordinal >= len(result_properties.fields) or ordinal >= len(
        home_properties.fields
    ):
        raise ValueError("Aggregate selected ordinal is outside exact row authority.")
    stage_scalar = result_properties.fields[ordinal]
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


def _join_properties(
    properties: Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties],
    join: ProjectIRBinaryJoinOccurrence,
) -> ProjectIRJoinOutputProperties:
    item = properties.get(join.node.ref)
    if item is None or item.join is not join:
        raise ValueError("Binary JOIN requires one exact property output.")
    return item


def _localized_input_factors(
    *,
    grain: ProjectIRProvidedIntrinsicGrain,
    introduction_use: ProjectIRJoinInputUseOccurrence,
    final_grain: ProjectIRProvidedIntrinsicGrain,
) -> tuple[ProjectGrainFactorIdentity, ...]:
    localized: list[ProjectGrainFactorIdentity] = []
    for factor in grain.active:
        matches = tuple(
            retained
            for retained in final_grain.active
            if (
                retained == factor
                if type(factor) is ProjectJoinGrainFactorIdentity
                else (
                    type(retained) is ProjectJoinGrainFactorIdentity
                    and retained.base == factor
                    and retained.introduction_use == introduction_use.ref
                )
            )
        )
        if len(matches) != 1:
            raise ValueError("JOIN input grain requires one exact contextual factor.")
        localized.append(matches[0])
    return tuple(localized)


def _multiplicity_exposures(
    *,
    join_properties: Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties],
    region: ProjectIRConcreteJoinRegion,
    introduction_join: ProjectIRBinaryJoinOccurrence,
    contextual: ProjectFactContextualGrain,
    comparison: ProjectFactGrainComparison,
) -> tuple[ProjectFactMultiplicityExposure, ...]:
    if comparison.status is not ProjectIRGrainComparisonStatus.RIGHT_FINER:
        return ()
    final_active = comparison.right.factors
    reachable = set(comparison.left_to_right.closure.factors)
    unresolved = tuple(factor for factor in final_active if factor not in reachable)
    start = region.joins.index(introduction_join)
    previous = set(contextual.factors)
    exposures: list[ProjectFactMultiplicityExposure] = []
    covered: set[ProjectGrainFactorIdentity] = set()
    for join in region.joins[start:]:
        current = set(_join_properties(join_properties, join).relational.grain.active)
        additions = tuple(
            cast(ProjectJoinGrainFactorIdentity, factor)
            for factor in final_active
            if factor in unresolved and factor in current and factor not in previous
        )
        if additions:
            exposures.append(
                ProjectFactMultiplicityExposure(
                    join=join,
                    factor_additions=additions,
                )
            )
            covered.update(additions)
        previous = current
    if covered != set(unresolved):
        raise ValueError("Fact multiplicity exposure must retain every added factor.")
    return tuple(exposures)


def _join_locality(
    *,
    join_properties: Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties],
    region: ProjectIRConcreteJoinRegion,
    fact: ProjectAggregateFactOccurrence,
    introduction_join: ProjectIRBinaryJoinOccurrence,
    side: ProjectFactJoinInputSide,
    final_properties: ProjectIRJoinOutputProperties,
    index: ProjectGrainDependencyIndex,
) -> ProjectAggregateFactJoinLocality:
    side_position = 0 if side is ProjectFactJoinInputSide.LEFT else 1
    introduction_use = introduction_join.input_uses[side_position]
    contextual_factors = _localized_input_factors(
        grain=fact.result_intrinsic_grain,
        introduction_use=introduction_use,
        final_grain=final_properties.relational.grain,
    )
    contextual = ProjectFactContextualGrain(
        authority=final_properties.relational.grain,
        state=fact.result_intrinsic_grain.state,
        factors=contextual_factors,
        evidence=introduction_use,
    )
    full = ProjectFactContextualGrain(
        authority=final_properties.relational.grain,
        state=final_properties.relational.grain.state,
        factors=final_properties.relational.grain.active,
        evidence=final_properties,
    )
    comparison = _compare_grains(index, contextual, full)
    start = region.joins.index(introduction_join)
    carried: list[ProjectIRJoinedRowField] = []
    for join in region.joins[start:]:
        matches = tuple(
            joined_field
            for joined_field in join.output.row_shape.fields
            if joined_field.evidence is fact.home_field.evidence
            and joined_field.introduction_use is introduction_use
        )
        if len(matches) != 1:
            raise ValueError("Fact locality requires one exact carried JOIN field.")
        carried.append(matches[0])
    exposures = _multiplicity_exposures(
        join_properties=join_properties,
        region=region,
        introduction_join=introduction_join,
        contextual=contextual,
        comparison=comparison,
    )
    return ProjectAggregateFactJoinLocality(
        fact=fact,
        region=region,
        introduction_use=introduction_use,
        introduction_join=introduction_join,
        side=side,
        relationship_entry_path=(
            introduction_join.path_step
            if side is ProjectFactJoinInputSide.RIGHT
            else None
        ),
        carried_fields=tuple(carried),
        final_region_properties=final_properties,
        final_field=carried[-1],
        contextual_grain=contextual,
        final_grain_comparison=comparison,
        multiplicity_exposures=exposures,
    )


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


def _actual_region_candidates(
    *,
    join_properties: Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties],
    region: ProjectIRConcreteJoinRegion,
    localities: tuple[ProjectAggregateFactJoinLocality, ...],
    final_properties: ProjectIRJoinOutputProperties,
    index: ProjectGrainDependencyIndex,
) -> tuple[ProjectActualGrainCandidate, ...]:
    candidates: list[ProjectActualGrainCandidate] = []
    for locality in localities:
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
    final_grain = final_properties.relational.grain
    for join in region.joins:
        for side_position, (kind, properties) in enumerate(
            (
                (ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT, join.left_input),
                (ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT, join.right_input),
            )
        ):
            introduction_use = join.input_uses[side_position]
            factors = _localized_input_factors(
                grain=properties.grain,
                introduction_use=introduction_use,
                final_grain=final_grain,
            )
            _add_actual_candidate(
                candidates,
                index=index,
                kind=kind,
                evidence=(join, introduction_use, properties.grain),
                factors=factors,
                allow_empty=properties.grain.state is ProjectGrainBasisState.GLOBAL,
            )
        source_introduction = join.matches[0].left.introduction_use.ref
        source_factors = tuple(
            factor
            for factor in final_grain.active
            if type(factor) is ProjectJoinGrainFactorIdentity
            and factor.introduction_use == source_introduction
        )
        source_output = join.use.source_binding.output
        if source_output is None:
            raise ValueError("Concrete JOIN source binding requires exact grain.")
        _add_actual_candidate(
            candidates,
            index=index,
            kind=ProjectActualGrainAuthorityKind.JOIN_SOURCE_SLICE,
            evidence=(join, join.use.source_binding, source_output.grain),
            factors=source_factors,
            allow_empty=source_output.grain.state is ProjectGrainBasisState.GLOBAL,
        )
        output_grain = _join_properties(join_properties, join).relational.grain
        _add_actual_candidate(
            candidates,
            index=index,
            kind=ProjectActualGrainAuthorityKind.JOIN_OUTPUT,
            evidence=(join, output_grain),
            factors=output_grain.active,
            allow_empty=output_grain.state is ProjectGrainBasisState.GLOBAL,
        )
    return tuple(candidates)


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


def _candidate_fact_buckets(
    *,
    localities: tuple[ProjectAggregateFactJoinLocality, ...],
    candidates: tuple[ProjectActualGrainCandidate, ...],
    determinations: Mapping[
        ProjectActualGrainCandidate,
        tuple[ProjectFactGrainDetermination, ...],
    ],
) -> Mapping[
    ProjectActualGrainCandidate,
    tuple[ProjectAggregateFactJoinLocality, ...],
]:
    return {
        candidate: tuple(
            locality
            for locality, determination in zip(
                localities, determinations[candidate], strict=True
            )
            if determination.status is ProjectFactGrainDirectionStatus.PROVEN
        )
        for candidate in candidates
    }


def _build_chasms(
    *,
    region: ProjectIRConcreteJoinRegion,
    localities: tuple[ProjectAggregateFactJoinLocality, ...],
    index: ProjectGrainDependencyIndex,
    actual_candidates: tuple[ProjectActualGrainCandidate, ...],
    comparisons: Mapping[tuple[int, int], ProjectFactGrainComparison],
    common_results: Mapping[tuple[int, int], ProjectCommonGrainResult],
    determinations: Mapping[
        ProjectActualGrainCandidate,
        tuple[ProjectFactGrainDetermination, ...],
    ],
) -> tuple[ProjectFactChasmCandidate, ...]:
    chasms: list[ProjectFactChasmCandidate] = []
    factor_sets = tuple(
        _factor_set(index, locality.contextual_grain.factors) for locality in localities
    )
    for candidate in actual_candidates:
        qualifying: list[tuple[int, int]] = []
        for left_position in range(len(localities)):
            for right_position in range(left_position + 1, len(localities)):
                comparison = comparisons[(left_position, right_position)]
                if (
                    comparison.status is not ProjectIRGrainComparisonStatus.INCOMPARABLE
                    or not factor_sets[left_position].factors
                    or not factor_sets[right_position].factors
                    or not any(
                        candidate is retained
                        for retained in (
                            evidence.candidate
                            for evidence in common_results[
                                (left_position, right_position)
                            ].candidates
                        )
                    )
                ):
                    continue
                left_to_common = _determine(
                    index, factor_sets[left_position], candidate.factors
                )
                right_to_common = _determine(
                    index, factor_sets[right_position], candidate.factors
                )
                if (
                    left_to_common.status is ProjectFactGrainDirectionStatus.PROVEN
                    and right_to_common.status is ProjectFactGrainDirectionStatus.PROVEN
                ):
                    qualifying.append((left_position, right_position))
        if not qualifying:
            continue
        positions = tuple(
            position
            for position in range(len(localities))
            if any(position in pair for pair in qualifying)
        )
        complete_count = len(positions) * (len(positions) - 1) // 2
        groups = (
            (positions,)
            if len(qualifying) == complete_count
            else tuple((left, right) for left, right in qualifying)
        )
        for group in groups:
            pairwise = tuple(
                comparisons[(left, right)]
                for offset, left in enumerate(group)
                for right in group[offset + 1 :]
            )
            if any(
                item.status is not ProjectIRGrainComparisonStatus.INCOMPARABLE
                for item in pairwise
            ):
                continue
            grouped_localities = tuple(localities[position] for position in group)
            common_determinations = tuple(
                determinations[candidate][position] for position in group
            )
            chasms.append(
                ProjectFactChasmCandidate(
                    region=region,
                    common_grain=candidate,
                    localities=grouped_localities,
                    introduction_joins=tuple(
                        join
                        for join in region.joins
                        if any(
                            locality.introduction_join is join
                            for locality in grouped_localities
                        )
                    ),
                    contextual_factor_sets=tuple(
                        factor_sets[position] for position in group
                    ),
                    pairwise_comparisons=pairwise,
                    common_determinations=common_determinations,
                )
            )
    return tuple(chasms)


def _build_alignment(
    *,
    left: ProjectAggregateFactLocality,
    right: ProjectAggregateFactLocality,
    index: ProjectGrainDependencyIndex,
    actual_candidates: tuple[ProjectActualGrainCandidate, ...],
    chasms: tuple[ProjectFactChasmCandidate, ...],
    common_grain: ProjectCommonGrainResult | None = None,
) -> ProjectMultiFactAlignment:
    comparison = _compare_grains(index, left.contextual_grain, right.contextual_grain)
    common = common_grain or _common_grain(
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

    exact_chasms = (
        tuple(
            chasm
            for chasm in chasms
            if chasm.contains_pair(
                cast(ProjectAggregateFactJoinLocality, left),
                cast(ProjectAggregateFactJoinLocality, right),
            )
        )
        if (
            type(left) is ProjectAggregateFactJoinLocality
            and type(right) is ProjectAggregateFactJoinLocality
        )
        else ()
    )
    risks: list[ProjectMultiFactMultiplicityRisk] = []
    if (
        type(left) is ProjectAggregateFactJoinLocality and left.multiplicity_exposures
    ) or (
        type(right) is ProjectAggregateFactJoinLocality and right.multiplicity_exposures
    ):
        risks.append(ProjectMultiFactMultiplicityRisk.FANOUT_RISK)
    if exact_chasms:
        risks.append(ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION)
    requirements = (
        (ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
        if structural is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        or risks
        else ()
    )
    return ProjectMultiFactAlignment(
        left=left,
        right=right,
        structural=structural,
        grain_comparison=comparison,
        common_grain=common,
        finer=finer,
        multiplicity_risks=tuple(risks),
        requirements=requirements,
        chasms=exact_chasms,
    )


def _build_concrete_region(
    *,
    join_properties: Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties],
    region: ProjectIRConcreteJoinRegion,
    facts: tuple[ProjectAggregateFactOccurrence, ...],
    facts_by_home_output: Mapping[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ],
) -> ProjectMultiFactConcreteRegion:
    final_properties = _join_properties(join_properties, region.joins[-1])
    index = _grain_index(final_properties.relational.grain)
    positions = {fact.identity: position for position, fact in enumerate(facts)}
    sites: list[
        list[tuple[ProjectIRBinaryJoinOccurrence, ProjectFactJoinInputSide]]
    ] = [[] for _fact in facts]
    for join in region.joins:
        for side, properties in (
            (ProjectFactJoinInputSide.LEFT, join.left_input),
            (ProjectFactJoinInputSide.RIGHT, join.right_input),
        ):
            for fact in facts_by_home_output.get(properties.output.occurrence.ref, ()):
                if fact.home_relation_properties is not properties:
                    raise ValueError("Fact home index must retain exact JOIN input.")
                sites[positions[fact.identity]].append((join, side))
    localities: list[ProjectAggregateFactJoinLocality] = []
    for fact_position, fact in enumerate(facts):
        localities.extend(
            _join_locality(
                join_properties=join_properties,
                region=region,
                fact=fact,
                introduction_join=join,
                side=side,
                final_properties=final_properties,
                index=index,
            )
            for join, side in sites[fact_position]
        )
    retained_localities = tuple(localities)
    actual_candidates = _actual_region_candidates(
        join_properties=join_properties,
        region=region,
        localities=retained_localities,
        final_properties=final_properties,
        index=index,
    )
    candidate_determinations = _candidate_determinations(
        index=index,
        grains=tuple(locality.contextual_grain for locality in retained_localities),
        candidates=actual_candidates,
    )
    dominator_masks = _candidate_dominator_masks(index, actual_candidates)
    fact_buckets = _candidate_fact_buckets(
        localities=retained_localities,
        candidates=actual_candidates,
        determinations=candidate_determinations,
    )
    comparisons = {
        (left_position, right_position): _compare_grains(
            index,
            retained_localities[left_position].contextual_grain,
            retained_localities[right_position].contextual_grain,
        )
        for left_position in range(len(retained_localities))
        for right_position in range(left_position + 1, len(retained_localities))
    }
    common_results = {
        (left_position, right_position): _indexed_common_grain(
            actual_candidates=actual_candidates,
            determinations=candidate_determinations,
            dominator_masks=dominator_masks,
            left_position=left_position,
            right_position=right_position,
        )
        for left_position in range(len(retained_localities))
        for right_position in range(left_position + 1, len(retained_localities))
    }
    chasms = _build_chasms(
        region=region,
        localities=retained_localities,
        index=index,
        actual_candidates=actual_candidates,
        comparisons=comparisons,
        common_results=common_results,
        determinations=candidate_determinations,
    )
    alignments = tuple(
        _build_alignment(
            left=retained_localities[left_position],
            right=retained_localities[right_position],
            index=index,
            actual_candidates=actual_candidates,
            chasms=chasms,
            common_grain=common_results[(left_position, right_position)],
        )
        for left_position in range(len(retained_localities))
        for right_position in range(left_position + 1, len(retained_localities))
    )
    return ProjectMultiFactConcreteRegion(
        region=region,
        final_properties=final_properties,
        grain_index=index,
        localities=retained_localities,
        actual_candidates=actual_candidates,
        fact_buckets=fact_buckets,
        chasms=chasms,
        alignments=alignments,
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
                chasms=(),
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
    path_ambiguous = bool(identifiable) and any(
        issue.kind in _PATH_AMBIGUITY_ISSUES
        for blocker in region.blockers
        for issue in blocker.issues
    )
    return ProjectMultiFactNonConcreteRegionSubject(
        region=region,
        blockers=region.blockers,
        identifiable_facts=identifiable,
        structural=(
            ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH
            if path_ambiguous
            else ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
        ),
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
    join_properties = {
        item.join.node.ref: item for item in join_regions.properties.outputs
    }
    if len(base_properties) != len(base_relational.outputs) or len(
        join_properties
    ) != len(join_regions.properties.outputs):
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
    concrete_regions = tuple(
        _build_concrete_region(
            join_properties=join_properties,
            region=region,
            facts=facts,
            facts_by_home_output=facts_by_home,
        )
        for region in join_regions.regions
        if type(region) is ProjectIRConcreteJoinRegion
    )
    non_concrete_regions = tuple(
        _non_concrete_subject(region=region, facts=facts)
        for region in join_regions.regions
        if type(region) is ProjectIRNonConcreteJoinRegion
    )
    localities_by_use: dict[
        ProjectIRUseRef, tuple[ProjectAggregateFactJoinLocality, ...]
    ] = {use.ref: () for use in join_regions.structural.uses}
    for region in concrete_regions:
        for locality in region.localities:
            use_ref = locality.introduction_use.ref
            localities_by_use[use_ref] = (
                *localities_by_use.get(use_ref, ()),
                locality,
            )
    return ProjectMultiFactAnalysis(
        evaluation=evaluation,
        base_relational=base_relational,
        join_regions=join_regions,
        facts=facts,
        home_localities=home_localities,
        concrete_regions=concrete_regions,
        non_concrete_regions=non_concrete_regions,
        home_alignments=_home_alignments(facts, home_localities),
        facts_by_context=facts_by_context,
        facts_by_home_output=facts_by_home,
        localities_by_introduction_use=localities_by_use,
    )


def analyze_project_fact_locality_pair(
    analysis: ProjectMultiFactAnalysis,
    left: ProjectAggregateFactLocality,
    right: ProjectAggregateFactLocality,
) -> ProjectMultiFactAlignment:
    """Query two exact fact localities without creating a global pair table."""

    if (
        type(analysis) is not ProjectMultiFactAnalysis
        or type(left)
        not in {
            ProjectAggregateFactHomeLocality,
            ProjectAggregateFactJoinLocality,
        }
        or type(right)
        not in {
            ProjectAggregateFactHomeLocality,
            ProjectAggregateFactJoinLocality,
        }
    ):
        raise TypeError("Pair query requires one exact analysis and two localities.")
    if left is right:
        raise ValueError("Pair query requires two distinct fact localities.")
    retained_localities: tuple[ProjectAggregateFactLocality, ...] = (
        *analysis.home_localities,
        *analysis.join_localities,
    )
    if not any(left is item for item in retained_localities) or not any(
        right is item for item in retained_localities
    ):
        raise ValueError("Pair query localities must belong to the exact analysis.")
    for alignment in analysis.alignments:
        if alignment.left is left and alignment.right is right:
            return alignment
    if (
        type(left) is ProjectAggregateFactHomeLocality
        and type(right) is ProjectAggregateFactHomeLocality
        and left.fact.context is right.fact.context
    ):
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
            chasms=(),
        )
    if (
        type(left) is ProjectAggregateFactJoinLocality
        and type(right) is ProjectAggregateFactJoinLocality
        and left.region is right.region
    ):
        region = next(
            item for item in analysis.concrete_regions if item.region is left.region
        )
        return _build_alignment(
            left=left,
            right=right,
            index=region.grain_index,
            actual_candidates=region.actual_candidates,
            chasms=region.chasms,
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
        chasms=(),
    )
