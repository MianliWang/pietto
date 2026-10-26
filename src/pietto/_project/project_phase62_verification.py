"""Independent Phase-62 verification, analyses, and invalidation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import cast

from pietto._project.project_grain import (
    grain_dependency_closure,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIREvaluationContextStage,
)
from pietto._project.project_ir_joins import (
    ProjectIRJoinRegionStage,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRRelationalPropertyStage,
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir_verification import (
    ProjectIRVerificationResult,
    ProjectIRVerificationStatus,
    verify_project_ir_stage,
)
from pietto._project.project_multifact import (
    ProjectAggregateFactHomeLocality,
    ProjectAggregateFactIdentity,
    ProjectAggregateFactLocality,
    ProjectAggregateFactOccurrence,
    ProjectFactGrainComparison,
    ProjectFactGrainDetermination,
    ProjectMultiFactAlignment,
    ProjectMultiFactAnalysis,
    ProjectMultiFactNonConcreteRegionSubject,
    ProjectMultiFactStructuralAlignment,
    project_aggregate_stage_field,
)
from pietto._project.project_relationship_uses import (
    ProjectJoinUseState,
    ProjectNonConcreteJoinUse,
)

__all__: tuple[str, ...] = ()


class ProjectPhase62VerificationStatus(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"


class ProjectPhase62VerificationIssueKind(StrEnum):
    ROOT_COHERENCE = "root_coherence"
    BASE_PROJECT_IR = "base_project_ir"
    JOIN_REGION_COMPLETENESS = "join_region_completeness"
    MULTIFACT_CATALOG = "multifact_catalog"
    MULTIFACT_LOCALITY = "multifact_locality"
    MULTIFACT_ALIGNMENT = "multifact_alignment"
    COMBINED_ACTUAL_USE_CYCLE = "combined_actual_use_cycle"


type ProjectPhase62VerificationCoordinate = (
    ProjectIRPlanNodeRef
    | ProjectIROutputValueRef
    | ProjectIRUseRef
    | ProjectIRInputSlotRef
    | ProjectAggregateFactIdentity
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62VerificationIssue:
    kind: ProjectPhase62VerificationIssueKind
    coordinate: ProjectPhase62VerificationCoordinate | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectPhase62VerificationIssueKind:
            raise TypeError("Phase-62 verification issue requires an exact kind.")
        if self.coordinate is not None and type(self.coordinate) not in {
            ProjectIRPlanNodeRef,
            ProjectIROutputValueRef,
            ProjectIRUseRef,
            ProjectIRInputSlotRef,
            ProjectAggregateFactIdentity,
        }:
            raise TypeError("Phase-62 verification issue requires a typed coordinate.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62VerificationResult:
    root: ProjectMultiFactAnalysis = field(repr=False, compare=False, hash=False)
    base_verification: ProjectIRVerificationResult
    status: ProjectPhase62VerificationStatus
    issues: tuple[ProjectPhase62VerificationIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.root) is not ProjectMultiFactAnalysis:
            raise TypeError("Phase-62 verification requires one exact checked root.")
        if type(self.base_verification) is not ProjectIRVerificationResult:
            raise TypeError("Phase-62 result requires one fresh base verification.")
        if type(self.status) is not ProjectPhase62VerificationStatus:
            raise TypeError("Phase-62 result requires an exact status.")
        if type(self.issues) is not tuple or any(
            type(issue) is not ProjectPhase62VerificationIssue for issue in self.issues
        ):
            raise TypeError("Phase-62 issues must be an exact tuple.")
        order = tuple(ProjectPhase62VerificationIssueKind)
        positions = tuple(order.index(issue.kind) for issue in self.issues)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Phase-62 issues must retain one fixed ordered pass.")
        if (self.status is ProjectPhase62VerificationStatus.VERIFIED) is bool(
            self.issues
        ):
            raise ValueError("Phase-62 verification status and issues disagree.")
        if self.base_verification.stage is not self.root.evaluation or (
            self.base_verification.status is ProjectIRVerificationStatus.INVALID
            and self.status is ProjectPhase62VerificationStatus.VERIFIED
        ):
            raise ValueError("Phase-62 result must retain fresh base verification.")

    @property
    def verified(self) -> bool:
        return self.status is ProjectPhase62VerificationStatus.VERIFIED


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _coordinate(subject: object | None) -> ProjectPhase62VerificationCoordinate | None:
    if type(subject) in {
        ProjectIRPlanNodeRef,
        ProjectIROutputValueRef,
        ProjectIRUseRef,
        ProjectIRInputSlotRef,
        ProjectAggregateFactIdentity,
    }:
        return cast(ProjectPhase62VerificationCoordinate, subject)
    if type(subject) is ProjectIRPlanNodeOccurrence:
        return subject.ref
    if type(subject) is ProjectIROutputValueOccurrence:
        return subject.ref
    if type(subject) is ProjectIRInputSlotOccurrence:
        return subject.ref
    if type(subject) is ProjectIRUseOccurrence:
        return subject.ref
    if type(subject) is ProjectIROperatorFlowUseOccurrence:
        return subject.ref
    if type(subject) is ProjectIRJoinInputUseOccurrence:
        return subject.ref
    if type(subject) is ProjectAggregateFactOccurrence:
        return subject.identity
    if type(subject) is ProjectAggregateFactHomeLocality:
        return subject.fact.identity
    return None


def _record(
    issues: list[ProjectPhase62VerificationIssue],
    kind: ProjectPhase62VerificationIssueKind,
    subject: object | None = None,
) -> None:
    if any(issue.kind is kind for issue in issues):
        return
    issues.append(
        ProjectPhase62VerificationIssue(
            kind=kind,
            coordinate=_coordinate(subject),
        )
    )


def _root_is_coherent(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> bool:
    valid = (
        type(root.evaluation) is ProjectIREvaluationContextStage
        and type(root.base_relational) is ProjectIRRelationalPropertyStage
        and type(root.join_regions) is ProjectIRJoinRegionStage
        and root.base_relational.origins.evaluation is root.evaluation
        and root.join_regions.base_plan is root.evaluation.project_plan
        and root.join_regions.base_relational is root.base_relational
        and root.join_regions.uses.semantic_result.module_semantic_facts
        is root.evaluation.project_plan.semantic_facts
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.ROOT_COHERENCE)
    return valid


def _verify_join_region_completeness(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    """Every join-bearing owner has one zero-allocation non-concrete region:
    no authored JOIN joins by itself."""

    stage = root.join_regions
    current = stage.starting_allocation
    valid = (
        current is root.evaluation.project_plan.ending_allocation
        and len(stage.regions) == len(stage.uses.ledgers)
        and all(
            region.ledger is ledger
            for region, ledger in zip(stage.regions, stage.uses.ledgers, strict=True)
        )
    )
    for region in stage.regions:
        blockers = tuple(
            use for use in region.ledger.uses if type(use) is ProjectNonConcreteJoinUse
        )
        valid = valid and (
            region.starting_allocation is current
            and type(region) is ProjectIRNonConcreteJoinRegion
            and region.ending_allocation is region.starting_allocation
            and bool(blockers)
            and region.blockers == blockers
            and region.state
            in {
                ProjectJoinUseState.UNKNOWN,
                ProjectJoinUseState.BLOCKED,
                ProjectJoinUseState.AMBIGUOUS,
            }
        )
        if not valid:
            _record(
                issues, ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS
            )
            return
        current = region.ending_allocation
    if not valid or current is not stage.ending_allocation:
        _record(issues, ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS)


def _base_properties(
    root: ProjectMultiFactAnalysis,
) -> Mapping[ProjectIROutputValueRef, ProjectIROutputRelationalProperties]:
    return {item.output.occurrence.ref: item for item in root.base_relational.outputs}


def _verify_multifact_catalog(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _base_properties(root)
    expected = tuple(
        (context, position, aggregate_result)
        for context in root.evaluation.aggregate_contexts
        for position, aggregate_result in enumerate(context.aggregate_results)
    )
    valid = len(root.facts) == len(expected)
    expected_by_context = {
        context.operator.node.ref: tuple(
            fact for fact in root.facts if fact.context is context
        )
        for context in root.evaluation.aggregate_contexts
    }
    expected_by_home: dict[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = {}
    for fact, (context, position, aggregate_result) in zip(
        root.facts, expected, strict=True
    ):
        select_matches = tuple(
            item
            for item in context.semantic_facts.select_facts
            if item.aggregate_result_fact is aggregate_result
        )
        input_properties = properties.get(context.input_row_output.occurrence.ref)
        result_properties = properties.get(context.result_row_output.occurrence.ref)
        home_properties = properties.get(
            context.fragment.root_relation_output.occurrence.ref
        )
        valid = valid and (
            type(fact) is ProjectAggregateFactOccurrence
            and fact.identity.aggregate_node == context.operator.node.ref
            and fact.identity.aggregate_result_position == position
            and fact.context is context
            and fact.aggregate_result is aggregate_result
            and len(select_matches) == 1
            and fact.select_fact is select_matches[0]
            and fact.selected_output_ordinal
            == select_matches[0].selected_output_ordinal
            and input_properties is not None
            and fact.input_row_properties is input_properties
            and result_properties is not None
            and fact.result_row_properties is result_properties
            and home_properties is not None
            and fact.home_relation_properties is home_properties
        )
        if (
            not valid
            or input_properties is None
            or result_properties is None
            or home_properties is None
        ):
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                fact,
            )
            return
        ordinal = fact.selected_output_ordinal
        final_matches = tuple(
            output
            for output in context.fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position == ordinal
        )
        class_matches = tuple(
            value_class
            for value_class in home_properties.value_classes
            if any(member is fact.home_field for member in value_class.members)
        )
        valid = valid and (
            fact.stage_scalar_output
            is project_aggregate_stage_field(result_properties, fact.select_fact)
            and ordinal < len(home_properties.fields)
            and fact.home_field is home_properties.fields[ordinal]
            and fact.stage_scalar_output.evidence is fact.home_field.evidence
            and len(final_matches) == 1
            and fact.final_scalar_output is final_matches[0]
            and fact.final_scalar_output.field.evidence is fact.home_field.evidence
            and len(class_matches) == 1
            and fact.home_value_class is class_matches[0]
            and fact.source_intrinsic_grain is input_properties.grain
            and fact.result_intrinsic_grain is result_properties.grain
        )
        output_ref = home_properties.output.occurrence.ref
        expected_by_home[output_ref] = (*expected_by_home.get(output_ref, ()), fact)
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                fact,
            )
            return
    valid = (
        valid
        and tuple(root.facts_by_context) == tuple(expected_by_context)
        and all(
            _same_objects(
                cast(tuple[object, ...], root.facts_by_context[key]),
                cast(tuple[object, ...], values),
            )
            for key, values in expected_by_context.items()
        )
    )
    valid = (
        valid
        and tuple(root.facts_by_home_output) == tuple(expected_by_home)
        and all(
            _same_objects(
                cast(tuple[object, ...], root.facts_by_home_output[key]),
                cast(tuple[object, ...], values),
            )
            for key, values in expected_by_home.items()
        )
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG)


def _determination_valid(determination: ProjectFactGrainDetermination) -> bool:
    if type(determination) is not ProjectFactGrainDetermination or not (
        determination.seed.universe
        is determination.requested.universe
        is determination.closure.universe
        is determination.index.universe
    ):
        return False
    expected = grain_dependency_closure(determination.index, determination.seed)
    proven = (
        determination.requested.mask & expected.mask == determination.requested.mask
    )
    return determination.closure.factors == expected.factors and (
        determination.status.value == ("proven" if proven else "not_proven")
    )


def _comparison_valid(comparison: ProjectFactGrainComparison) -> bool:
    if type(comparison) is not ProjectFactGrainComparison or not (
        comparison.left_to_right.index is comparison.index
        and comparison.right_to_left.index is comparison.index
        and _determination_valid(comparison.left_to_right)
        and _determination_valid(comparison.right_to_left)
        and comparison.left_to_right.seed.factors == comparison.left.factors
        and comparison.left_to_right.requested.factors == comparison.right.factors
        and comparison.right_to_left.seed.factors == comparison.right.factors
        and comparison.right_to_left.requested.factors == comparison.left.factors
    ):
        return False
    statuses = (
        comparison.left_to_right.status.value,
        comparison.right_to_left.status.value,
    )
    expected = {
        ("proven", "proven"): "equal",
        ("proven", "not_proven"): "left_finer",
        ("not_proven", "proven"): "right_finer",
        ("not_proven", "not_proven"): "incomparable",
    }[statuses]
    return comparison.status.value == expected


def _verify_multifact_localities(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    valid = len(root.home_localities) == len(root.facts) and all(
        type(locality) is ProjectAggregateFactHomeLocality
        and locality.fact is fact
        and locality.home_relation_properties is fact.home_relation_properties
        and locality.home_field is fact.home_field
        and locality.contextual_grain.authority is fact.result_intrinsic_grain
        and locality.contextual_grain.state is fact.result_intrinsic_grain.state
        and locality.contextual_grain.factors == fact.result_intrinsic_grain.active
        for locality, fact in zip(root.home_localities, root.facts, strict=True)
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY)
        return
    regions = root.join_regions.regions
    valid = len(root.non_concrete_regions) == len(regions)
    for subject, region in zip(root.non_concrete_regions, regions, strict=True):
        identifiable = tuple(
            fact
            for fact in root.facts
            if any(
                binding.output is fact.home_relation_properties
                or (
                    binding.target is not None
                    and binding.target.target_occurrence
                    is fact.context.semantic_facts.owner
                )
                for binding in region.ledger.bindings
            )
        )
        valid = valid and (
            type(subject) is ProjectMultiFactNonConcreteRegionSubject
            and subject.region is region
            and subject.blockers == region.blockers
            and subject.identifiable_facts == identifiable
            and subject.structural
            is ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
        )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY)


def _verify_multifact_alignments(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    expected_home_pairs = tuple(
        (root.home_localities[left], root.home_localities[right])
        for left in range(len(root.home_localities))
        for right in range(left + 1, len(root.home_localities))
        if root.facts[left].context is root.facts[right].context
    )
    valid = len(root.home_alignments) == len(expected_home_pairs) and all(
        alignment.left is left
        and alignment.right is right
        and _comparison_valid(
            cast(ProjectFactGrainComparison, alignment.grain_comparison)
        )
        and alignment.structural is ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
        and not alignment.multiplicity_risks
        and not alignment.requirements
        for alignment, (left, right) in zip(
            root.home_alignments, expected_home_pairs, strict=True
        )
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT)


type ProjectPhase62CombinedUse = (
    ProjectIRUseOccurrence
    | ProjectIROperatorFlowUseOccurrence
    | ProjectIRJoinInputUseOccurrence
)


# The JOIN regions allocate nothing, so the combined graph is the base plan's.
def _combined_nodes(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    return root.evaluation.project_plan.structural_stage.nodes


def _combined_outputs(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIROutputValueOccurrence, ...]:
    return root.evaluation.project_plan.structural_stage.outputs


def _combined_uses(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62CombinedUse, ...]:
    return root.evaluation.project_plan.structural_stage.uses


def _combined_successors(
    root: ProjectMultiFactAnalysis,
) -> tuple[tuple[int, ...], ...] | None:
    nodes = _combined_nodes(root)
    positions = {node.ref: position for position, node in enumerate(nodes)}
    if len(positions) != len(nodes):
        return None
    successors: list[list[int]] = [[] for _node in nodes]
    for use in _combined_uses(root):
        producer = positions.get(use.output.producer.ref)
        consumer = positions.get(use.slot.consumer.ref)
        if (
            producer is None
            or consumer is None
            or nodes[producer] is not use.output.producer
            or nodes[consumer] is not use.slot.consumer
        ):
            return None
        successors[producer].append(consumer)
    return tuple(tuple(values) for values in successors)


def _combined_topological_order(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIRPlanNodeOccurrence, ...] | None:
    nodes = _combined_nodes(root)
    successors = _combined_successors(root)
    if successors is None:
        return None
    indegree = [0] * len(nodes)
    for values in successors:
        for consumer in values:
            indegree[consumer] += 1
    ready: list[tuple[int, int]] = []
    for position, (node, degree) in enumerate(zip(nodes, indegree, strict=True)):
        if degree == 0:
            heappush(ready, (node.ref.position, position))
    order: list[ProjectIRPlanNodeOccurrence] = []
    while ready:
        _, position = heappop(ready)
        order.append(nodes[position])
        for consumer in successors[position]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                heappush(ready, (nodes[consumer].ref.position, consumer))
    return tuple(order) if len(order) == len(nodes) else None


def _verify_combined_cycle(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    if (
        _combined_successors(root) is not None
        and _combined_topological_order(root) is None
    ):
        _record(issues, ProjectPhase62VerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE)


def verify_project_phase62(
    root: ProjectMultiFactAnalysis,
) -> ProjectPhase62VerificationResult:
    """Freshly verify one exact Phase-62 root without invoking builders."""

    if type(root) is not ProjectMultiFactAnalysis:
        raise TypeError("Phase-62 verification requires one exact root.")
    issues: list[ProjectPhase62VerificationIssue] = []
    coherent = _root_is_coherent(root, issues)
    base_verification = verify_project_ir_stage(root.evaluation)
    if not base_verification.verified:
        _record(
            issues,
            ProjectPhase62VerificationIssueKind.BASE_PROJECT_IR,
            base_verification.issues[0].coordinate
            if base_verification.issues
            else None,
        )
    if coherent:
        _verify_join_region_completeness(root, issues)
        _verify_multifact_catalog(root, issues)
        if not any(
            issue.kind is ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG
            for issue in issues
        ):
            _verify_multifact_localities(root, issues)
        if not any(
            issue.kind
            in {
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
            }
            for issue in issues
        ):
            _verify_multifact_alignments(root, issues)
        _verify_combined_cycle(root, issues)
    issue_tuple = tuple(issues)
    return ProjectPhase62VerificationResult(
        root=root,
        base_verification=base_verification,
        status=(
            ProjectPhase62VerificationStatus.VERIFIED
            if not issue_tuple
            else ProjectPhase62VerificationStatus.INVALID
        ),
        issues=issue_tuple,
    )


class ProjectPhase62AnalysisKind(StrEnum):
    COMBINED_REVERSE_USE_INDEX = "combined_reverse_use_index"
    COMBINED_TOPOLOGICAL_ORDER = "combined_topological_order"
    FACT_LOCALITY_INDEX = "fact_locality_index"
    MULTIFACT_ALIGNMENT_INDEX = "multifact_alignment_index"


class ProjectPhase62ChangeDomain(StrEnum):
    BASE_TOPOLOGY = "base_topology"
    BASE_SEMANTICS = "base_semantics"
    RELATIONSHIP_USE_AUTHORITY = "relationship_use_authority"
    JOIN_TOPOLOGY = "join_topology"
    JOIN_SEMANTICS = "join_semantics"
    JOIN_PROPERTIES = "join_properties"
    MULTIFACT_LOCALITY = "multifact_locality"
    MULTIFACT_ALIGNMENT = "multifact_alignment"
    ESTIMATES = "estimates"


class ProjectPhase62VerificationRequirement(StrEnum):
    RERUN_REQUIRED = "rerun_required"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62CombinedReverseUseEntry:
    output: ProjectIROutputValueOccurrence
    uses: tuple[ProjectPhase62CombinedUse, ...]

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIROutputValueOccurrence:
            raise TypeError("Combined reverse-use entry requires an exact output.")
        if type(self.uses) is not tuple or any(
            type(use)
            not in {
                ProjectIRUseOccurrence,
                ProjectIROperatorFlowUseOccurrence,
                ProjectIRJoinInputUseOccurrence,
            }
            or use.output is not self.output
            for use in self.uses
        ):
            raise ValueError("Combined reverse-use entry requires exact direct uses.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62FactLocalityEntry:
    fact: ProjectAggregateFactOccurrence = field(repr=False, compare=False, hash=False)
    identity: ProjectAggregateFactIdentity
    localities: tuple[ProjectAggregateFactLocality, ...]

    def __post_init__(self) -> None:
        if (
            type(self.fact) is not ProjectAggregateFactOccurrence
            or self.identity != self.fact.identity
            or not self.localities
            or self.localities[0].fact is not self.fact
            or type(self.localities[0]) is not ProjectAggregateFactHomeLocality
            or any(locality.fact is not self.fact for locality in self.localities)
        ):
            raise ValueError("Fact-locality entry requires exact canonical localities.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62MultiFactAlignmentIndex:
    alignments: tuple[ProjectMultiFactAlignment, ...]

    def __post_init__(self) -> None:
        if type(self.alignments) is not tuple or any(
            type(item) is not ProjectMultiFactAlignment for item in self.alignments
        ):
            raise TypeError("Alignment index requires exact alignments.")


def _derive_reverse_uses(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62CombinedReverseUseEntry, ...]:
    uses = _combined_uses(root)
    return tuple(
        ProjectPhase62CombinedReverseUseEntry(
            output=output,
            uses=tuple(use for use in uses if use.output is output),
        )
        for output in _combined_outputs(root)
    )


def _derive_fact_locality_index(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62FactLocalityEntry, ...]:
    return tuple(
        ProjectPhase62FactLocalityEntry(
            fact=fact,
            identity=fact.identity,
            localities=(root.home_localities[position],),
        )
        for position, fact in enumerate(root.facts)
    )


def _derive_alignment_index(
    root: ProjectMultiFactAnalysis,
) -> ProjectPhase62MultiFactAlignmentIndex:
    return ProjectPhase62MultiFactAlignmentIndex(alignments=root.home_alignments)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62AnalysisBundle:
    verification: ProjectPhase62VerificationResult
    combined_reverse_uses: tuple[ProjectPhase62CombinedReverseUseEntry, ...]
    combined_topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    fact_localities: tuple[ProjectPhase62FactLocalityEntry, ...]
    multifact_alignments: ProjectPhase62MultiFactAlignmentIndex

    def __post_init__(self) -> None:
        if (
            type(self.verification) is not ProjectPhase62VerificationResult
            or not self.verification.verified
            or self.verification.issues
        ):
            raise ValueError("Phase-62 analyses require one VERIFIED result.")
        root = self.verification.root
        expected_topological = _combined_topological_order(root)
        expected_alignment = _derive_alignment_index(root)
        valid = (
            _same_reverse_uses(self.combined_reverse_uses, _derive_reverse_uses(root))
            and expected_topological is not None
            and _same_objects(
                cast(tuple[object, ...], self.combined_topological_order),
                cast(tuple[object, ...], expected_topological or ()),
            )
            and _same_fact_localities(
                self.fact_localities, _derive_fact_locality_index(root)
            )
            and _same_objects(
                cast(tuple[object, ...], self.multifact_alignments.alignments),
                cast(tuple[object, ...], expected_alignment.alignments),
            )
        )
        if not valid:
            raise ValueError("Phase-62 bundle must retain fresh canonical products.")

    @property
    def root(self) -> ProjectMultiFactAnalysis:
        return self.verification.root


def _same_reverse_uses(
    actual: tuple[ProjectPhase62CombinedReverseUseEntry, ...],
    expected: tuple[ProjectPhase62CombinedReverseUseEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.output is retained.output
        and _same_objects(
            cast(tuple[object, ...], item.uses),
            cast(tuple[object, ...], retained.uses),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


def _same_fact_localities(
    actual: tuple[ProjectPhase62FactLocalityEntry, ...],
    expected: tuple[ProjectPhase62FactLocalityEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.fact is retained.fact
        and item.identity == retained.identity
        and _same_objects(
            cast(tuple[object, ...], item.localities),
            cast(tuple[object, ...], retained.localities),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


def build_project_phase62_analysis_bundle(
    verification: ProjectPhase62VerificationResult,
) -> ProjectPhase62AnalysisBundle:
    """Rederive all four detachable analyses from the verified current root."""

    if (
        type(verification) is not ProjectPhase62VerificationResult
        or not verification.verified
    ):
        raise ValueError("Only VERIFIED Phase-62 roots may produce analyses.")
    root = verification.root
    topological = _combined_topological_order(root)
    if topological is None:
        raise ValueError("Verified combined actual-use graph must remain acyclic.")
    return ProjectPhase62AnalysisBundle(
        verification=verification,
        combined_reverse_uses=_derive_reverse_uses(root),
        combined_topological_order=topological,
        fact_localities=_derive_fact_locality_index(root),
        multifact_alignments=_derive_alignment_index(root),
    )


def _analysis_dependencies(
    kind: ProjectPhase62AnalysisKind,
) -> tuple[ProjectPhase62ChangeDomain, ...]:
    if kind in {
        ProjectPhase62AnalysisKind.COMBINED_REVERSE_USE_INDEX,
        ProjectPhase62AnalysisKind.COMBINED_TOPOLOGICAL_ORDER,
    }:
        return (
            ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
            ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
        )
    if kind is ProjectPhase62AnalysisKind.FACT_LOCALITY_INDEX:
        return (
            ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
            ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
            ProjectPhase62ChangeDomain.RELATIONSHIP_USE_AUTHORITY,
            ProjectPhase62ChangeDomain.JOIN_SEMANTICS,
            ProjectPhase62ChangeDomain.JOIN_PROPERTIES,
            ProjectPhase62ChangeDomain.BASE_SEMANTICS,
            ProjectPhase62ChangeDomain.MULTIFACT_LOCALITY,
        )
    return (
        ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
        ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
        ProjectPhase62ChangeDomain.RELATIONSHIP_USE_AUTHORITY,
        ProjectPhase62ChangeDomain.JOIN_SEMANTICS,
        ProjectPhase62ChangeDomain.JOIN_PROPERTIES,
        ProjectPhase62ChangeDomain.BASE_SEMANTICS,
        ProjectPhase62ChangeDomain.MULTIFACT_LOCALITY,
        ProjectPhase62ChangeDomain.MULTIFACT_ALIGNMENT,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62AnalysisInvalidation:
    changed_domains: tuple[ProjectPhase62ChangeDomain, ...]
    invalidated: tuple[ProjectPhase62AnalysisKind, ...]
    preserved: tuple[ProjectPhase62AnalysisKind, ...]
    verification: ProjectPhase62VerificationRequirement = field(
        init=False,
        default=ProjectPhase62VerificationRequirement.RERUN_REQUIRED,
    )

    def __post_init__(self) -> None:
        order = tuple(ProjectPhase62ChangeDomain)
        if (
            type(self.changed_domains) is not tuple
            or not self.changed_domains
            or any(
                type(domain) is not ProjectPhase62ChangeDomain
                for domain in self.changed_domains
            )
            or len(set(self.changed_domains)) != len(self.changed_domains)
            or self.changed_domains
            != tuple(sorted(self.changed_domains, key=order.index))
        ):
            raise ValueError("Phase-62 change domains must be unique and canonical.")
        expected_invalidated = tuple(
            kind
            for kind in ProjectPhase62AnalysisKind
            if any(
                domain in self.changed_domains
                for domain in _analysis_dependencies(kind)
            )
        )
        expected_preserved = tuple(
            kind
            for kind in ProjectPhase62AnalysisKind
            if kind not in expected_invalidated
        )
        if (
            self.invalidated != expected_invalidated
            or self.preserved != expected_preserved
        ):
            raise ValueError("Phase-62 invalidation disagrees with dependencies.")


def assess_project_phase62_analysis_invalidation(
    changed_domains: tuple[ProjectPhase62ChangeDomain, ...],
) -> ProjectPhase62AnalysisInvalidation:
    """Derive conservative preservation without ever preserving verification."""

    invalidated = tuple(
        kind
        for kind in ProjectPhase62AnalysisKind
        if any(domain in changed_domains for domain in _analysis_dependencies(kind))
    )
    return ProjectPhase62AnalysisInvalidation(
        changed_domains=changed_domains,
        invalidated=invalidated,
        preserved=tuple(
            kind for kind in ProjectPhase62AnalysisKind if kind not in invalidated
        ),
    )
