from __future__ import annotations

from collections.abc import Callable
from copy import copy
from dataclasses import FrozenInstanceError, fields
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto
import pietto._project as project_package
import pietto._project.project_ir as project_ir
import pietto._project.project_ir_composition as composition
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_evaluation_context as evaluation
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_properties as properties
import pietto._project.project_ir_verification as verification
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Independent Verification Passes",
    "Typed Verification Result",
    "Fresh Derived Analyses",
    "Analysis Invalidation And Preservation",
    "Semantic Equivalence And Rewrite Readiness",
    "Optimizer And Recursion Readiness Boundaries",
    "Determinism Immutability And Privacy",
    "Focused Assurance",
    "Integration Boundaries And Non-goals",
    "Slice 9 Handoff",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    amount: Int nullable
    category: Text nullable
shape Other:
    key: Int not null
source rows: Row is postgres.table("rows")
source other: Other is postgres.table("other")
query chained:
    from same_a
    select:
        id
query same_a:
    from rows
    select:
        id
query same_b:
    from rows
    select:
        id
query ordered:
    from rows
    select:
        id
    order by:
        id
query unordered:
    from rows
    select:
        id
query window_row:
    from rows
    select:
        id
        ranking = row_number() window:
            order by:
                id
query window_rank:
    from rows
    select:
        id
        ranking = rank() window:
            order by:
                id
query aggregate_only:
    from rows
    select:
        total = sum(amount)
query grouped:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
query full:
    from rows
    let:
        adjusted = amount + id
    where id > 0
    group by:
        category
    select:
        category
        total = sum(adjusted)
        ranking = row_number() window child
    window child = base
    window base:
        partition by:
            category
        order by:
            total desc
    satisfying:
        sum(adjusted) > 0
query other_result:
    from other
    select:
        key
query broken:
    from rows
    select:
        missing
"""


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _build_stage(
    semantic: ProjectSemanticResult,
) -> evaluation.ProjectIREvaluationContextStage:
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = composition.build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=construction.ProjectIRAllocationState(
            scope=project_ir.ProjectIRSnapshotScope()
        ),
    )
    return evaluation.build_project_ir_evaluation_context_stage(plan)


def _fragment(
    stage: evaluation.ProjectIREvaluationContextStage,
    name: str,
) -> construction.ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in stage.project_plan.fragments
        if fragment.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _concrete(
    stage: evaluation.ProjectIREvaluationContextStage,
    name: str,
) -> construction.ProjectIRConcreteSingleRelationFragment:
    fragment = _fragment(stage, name)
    assert type(fragment) is construction.ProjectIRConcreteSingleRelationFragment
    return fragment


def _unsafe(value: object, **changes: object) -> object:
    clone = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(clone, name, replacement)
    return clone


def _with_plan(
    stage: evaluation.ProjectIREvaluationContextStage,
    **changes: object,
) -> evaluation.ProjectIREvaluationContextStage:
    plan = _unsafe(stage.project_plan, **changes)
    assert type(plan) is composition.ProjectIRProjectPlan
    result = _unsafe(stage, project_plan=plan)
    assert type(result) is evaluation.ProjectIREvaluationContextStage
    return result


def _with_structural(
    stage: evaluation.ProjectIREvaluationContextStage,
    **changes: object,
) -> evaluation.ProjectIREvaluationContextStage:
    structural = _unsafe(stage.project_plan.structural_stage, **changes)
    assert type(structural) is project_ir.ProjectIRStructuralStage
    return _with_plan(stage, structural_stage=structural)


def _with_fragment(
    stage: evaluation.ProjectIREvaluationContextStage,
    original: construction.ProjectIRSingleRelationFragment,
    replacement: construction.ProjectIRSingleRelationFragment,
) -> evaluation.ProjectIREvaluationContextStage:
    fragments = tuple(
        replacement if fragment is original else fragment
        for fragment in stage.project_plan.fragments
    )
    return _with_plan(stage, fragments=fragments)


def test_controlling_contract_locks_verifier_analysis_and_handoff() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == SPEC_HEADINGS
    )
    normalized = " ".join(document.split())
    for evidence in (
        "455629a9edc93622180788ff4cba8b76776c4e9f",
        "6b9bfe44d00de3de112214515f3682131696967a",
        "33342737233",
        "A3/M4/D0",
        "constructor validity != independent verification",
        "verification itself is never preservable",
        "semantic-equivalence candidate != rewrite proof != rewrite",
        "CanonicalProjectIR != OptimizationMemo != ChosenTargetPlan",
        "ProjectIRVerificationResult",
        "ProjectIRAnalysisInvalidation",
        "Add Phase 61 Project IR verifier",
        "PASS — PHASE61_SLICE8_INTEGRITY_VERIFIER_ANALYSIS_INVALIDATION_"
        "SEMANTIC_EQUIVALENCE_OPTIMIZER_RECURSION_READINESS_END_TO_END",
        "Phase 61 Slice 9 — Private Inspection, Query, Canonical Serialization, And Pure Boundary",
    ):
        assert evidence in normalized


def test_valid_stage_verifies_independently_and_carriers_are_private_frozen(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    result = verification.verify_project_ir_stage(stage)
    assert result.stage is stage
    assert result.status is verification.ProjectIRVerificationStatus.VERIFIED
    assert result.issues == ()
    assert result.verified
    assert verification.__all__ == ()
    for carrier in (
        verification.ProjectIRVerificationIssue,
        verification.ProjectIRVerificationResult,
        verification.ProjectIRReverseUseEntry,
        verification.ProjectIRReachabilityEntry,
        verification.ProjectIRSemanticDimensionAssessment,
        verification.ProjectIRSemanticEquivalenceAssessment,
        verification.ProjectIRRewriteReadiness,
        verification.ProjectIRAnalysisInvalidation,
        verification.ProjectIRAnalysisBundle,
    ):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    source = (REPO_ROOT / "src/pietto/_project/project_ir_verification.py").read_text(
        encoding="utf-8"
    )
    assert "_expected_operator_kinds" not in source
    assert "_require_acyclic" not in source
    with pytest.raises(FrozenInstanceError):
        result.issues = ()  # type: ignore[misc]


def _foreign_snapshot(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    node = stage.project_plan.structural_stage.nodes[0]
    ref = _unsafe(node.ref, scope=project_ir.ProjectIRSnapshotScope())
    assert type(ref) is project_ir.ProjectIRPlanNodeRef
    replacement = _unsafe(node, ref=ref)
    assert type(replacement) is project_ir.ProjectIRPlanNodeOccurrence
    return _with_structural(
        stage,
        nodes=(replacement, *stage.project_plan.structural_stage.nodes[1:]),
    )


def _missing_output(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    outputs = stage.project_plan.structural_stage.outputs
    used = next(
        output
        for output in outputs
        if any(use.output is output for use in stage.project_plan.structural_stage.uses)
    )
    return _with_structural(
        stage,
        outputs=tuple(output for output in outputs if output is not used),
    )


def _bad_use_endpoint(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    structural = stage.project_plan.structural_stage
    use = structural.uses[0]
    replacement = _unsafe(use, slot=structural.input_slots[-1])
    assert type(replacement) in {
        project_ir.ProjectIRUseOccurrence,
        project_ir.ProjectIROperatorFlowUseOccurrence,
    }
    return _with_structural(
        stage,
        uses=(replacement, *structural.uses[1:]),
    )


def _duplicate_coordinate(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    outputs = stage.project_plan.structural_stage.outputs
    ref = _unsafe(outputs[1].ref, position=outputs[0].ref.position)
    assert type(ref) is project_ir.ProjectIROutputValueRef
    replacement = _unsafe(outputs[1], ref=ref)
    assert type(replacement) is project_ir.ProjectIROutputValueOccurrence
    return _with_structural(
        stage,
        outputs=(outputs[0], replacement, *outputs[2:]),
    )


def _gapped_coordinate(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    outputs = stage.project_plan.structural_stage.outputs
    ref = _unsafe(outputs[-1].ref, position=outputs[-1].ref.position + 1)
    assert type(ref) is project_ir.ProjectIROutputValueRef
    replacement = _unsafe(outputs[-1], ref=ref)
    assert type(replacement) is project_ir.ProjectIROutputValueOccurrence
    return _with_structural(stage, outputs=(*outputs[:-1], replacement))


def _wrong_operator_order(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "full")
    operators_ = fragment.logical_stage.operators
    logical_stage = _unsafe(
        fragment.logical_stage,
        operators=(operators_[1], operators_[0], *operators_[2:]),
    )
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(fragment, logical_stage=logical_stage)
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _wrong_flow_adjacency(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "full")
    group = next(
        operator
        for operator in fragment.logical_stage.operators
        if operator.kind is operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    relation_input = fragment.logical_stage.operators[0]
    input_row = next(
        output
        for output in fragment.property_stage.outputs
        if type(output) is properties.ProjectIRRelationRowOutput
        and output.occurrence.producer is relation_input.node
    )
    flow = next(
        use
        for use in stage.project_plan.structural_stage.uses
        if type(use) is project_ir.ProjectIROperatorFlowUseOccurrence
        and use.slot.consumer is group.node
    )
    replacement = _unsafe(flow, output=input_row.occurrence)
    assert type(replacement) is project_ir.ProjectIROperatorFlowUseOccurrence
    return _with_structural(
        stage,
        uses=tuple(
            replacement if use is flow else use
            for use in stage.project_plan.structural_stage.uses
        ),
    )


def _wrong_cross_endpoint(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    plan = stage.project_plan
    edge = plan.cross_relation_edges[0]
    wrong = _concrete(stage, "other_result")
    use = _unsafe(edge.use, output=wrong.root_relation_output.occurrence)
    assert type(use) is project_ir.ProjectIRUseOccurrence
    replacement = _unsafe(edge, use=use)
    assert type(replacement) is composition.ProjectIRCrossRelationEdge
    structural = _unsafe(
        plan.structural_stage,
        uses=tuple(
            use if item is edge.use else item for item in plan.structural_stage.uses
        ),
    )
    assert type(structural) is project_ir.ProjectIRStructuralStage
    return _with_plan(
        stage,
        structural_stage=structural,
        cross_relation_edges=(replacement, *plan.cross_relation_edges[1:]),
    )


def _broken_compatibility(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    plan = stage.project_plan
    edge = plan.cross_relation_edges[0]
    compatibility = _unsafe(
        edge.compatibility,
        status=operators.ProjectIRRowShapeCompatibilityStatus.NOT_SATISFIED,
    )
    assert type(compatibility) is operators.ProjectIRRowShapeCompatibility
    replacement = _unsafe(edge, compatibility=compatibility)
    assert type(replacement) is composition.ProjectIRCrossRelationEdge
    return _with_plan(
        stage,
        cross_relation_edges=(replacement, *plan.cross_relation_edges[1:]),
    )


def _missing_property(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "same_a")
    property_stage = _unsafe(
        fragment.property_stage,
        provided=fragment.property_stage.provided[1:],
    )
    assert type(property_stage) is properties.ProjectIRPropertyStage
    logical_stage = _unsafe(fragment.logical_stage, property_stage=property_stage)
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(
        fragment,
        property_stage=property_stage,
        logical_stage=logical_stage,
    )
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _missing_bag_property(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "same_a")
    bag = next(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is properties.ProjectIRProvidedBagMultiplicity
        and property_.output is fragment.root_relation_output
    )
    property_stage = _unsafe(
        fragment.property_stage,
        provided=tuple(
            property_
            for property_ in fragment.property_stage.provided
            if property_ is not bag
        ),
    )
    assert type(property_stage) is properties.ProjectIRPropertyStage
    logical_stage = _unsafe(fragment.logical_stage, property_stage=property_stage)
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(
        fragment,
        property_stage=property_stage,
        logical_stage=logical_stage,
    )
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _missing_transfer(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "same_a")
    logical_stage = _unsafe(
        fragment.logical_stage,
        transfers=fragment.logical_stage.transfers[1:],
    )
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(fragment, logical_stage=logical_stage)
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _missing_final_scalar(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "same_a")
    replacement = _unsafe(fragment, final_scalar_outputs=())
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _wrong_effect(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "same_a")
    outputs = fragment.property_stage.outputs
    effect = _unsafe(fragment.property_stage.effects[0], output=outputs[1])
    assert type(effect) is properties.ProjectIREffectEvidence
    property_stage = _unsafe(
        fragment.property_stage,
        effects=(effect, *fragment.property_stage.effects[1:]),
    )
    assert type(property_stage) is properties.ProjectIRPropertyStage
    logical_stage = _unsafe(fragment.logical_stage, property_stage=property_stage)
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(
        fragment,
        property_stage=property_stage,
        logical_stage=logical_stage,
    )
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _wrong_policy(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    fragment = _concrete(stage, "window_row")
    other = _concrete(stage, "window_rank")
    policy = next(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is properties.ProjectIRProvidedEvaluationPolicy
    )
    other_policy = next(
        property_
        for property_ in other.property_stage.provided
        if type(property_) is properties.ProjectIRProvidedEvaluationPolicy
    )
    replacement_policy = _unsafe(policy, policy=other_policy.policy)
    assert type(replacement_policy) is properties.ProjectIRProvidedEvaluationPolicy
    property_stage = _unsafe(
        fragment.property_stage,
        provided=tuple(
            replacement_policy if property_ is policy else property_
            for property_ in fragment.property_stage.provided
        ),
    )
    assert type(property_stage) is properties.ProjectIRPropertyStage
    logical_stage = _unsafe(fragment.logical_stage, property_stage=property_stage)
    assert type(logical_stage) is operators.ProjectIRLogicalOperatorStage
    replacement = _unsafe(
        fragment,
        property_stage=property_stage,
        logical_stage=logical_stage,
    )
    assert type(replacement) is construction.ProjectIRConcreteSingleRelationFragment
    return _with_fragment(stage, fragment, replacement)


def _missing_evaluation_context(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    result = _unsafe(stage, aggregate_contexts=stage.aggregate_contexts[:-1])
    assert type(result) is evaluation.ProjectIREvaluationContextStage
    return result


def _duplicate_evaluation_context(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    result = _unsafe(
        stage,
        aggregate_contexts=(*stage.aggregate_contexts, stage.aggregate_contexts[0]),
    )
    assert type(result) is evaluation.ProjectIREvaluationContextStage
    return result


def _non_concrete_with_ir(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    terminal = _fragment(stage, "broken")
    concrete = _concrete(stage, "same_a")
    assert type(terminal) is construction.ProjectIRNonConcreteSingleRelationFragment
    replacement = _unsafe(
        terminal,
        ending_allocation=concrete.ending_allocation,
        structural_stage=concrete.structural_stage,
        property_stage=concrete.property_stage,
        logical_stage=concrete.logical_stage,
    )
    assert type(replacement) is construction.ProjectIRNonConcreteSingleRelationFragment
    return _with_fragment(stage, terminal, replacement)


def _actual_use_cycle(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    plan = stage.project_plan
    edge = next(
        edge
        for edge in plan.cross_relation_edges
        if edge.consumer.semantic_facts.owner.identity.declared_name == "chained"
    )
    use = _unsafe(
        edge.use,
        output=edge.consumer.root_relation_output.occurrence,
    )
    assert type(use) is project_ir.ProjectIRUseOccurrence
    replacement = _unsafe(edge, use=use)
    assert type(replacement) is composition.ProjectIRCrossRelationEdge
    structural = _unsafe(
        plan.structural_stage,
        uses=tuple(
            use if item is edge.use else item for item in plan.structural_stage.uses
        ),
    )
    assert type(structural) is project_ir.ProjectIRStructuralStage
    return _with_plan(
        stage,
        structural_stage=structural,
        cross_relation_edges=tuple(
            replacement if item is edge else item for item in plan.cross_relation_edges
        ),
    )


def _detached_provenance(
    stage: evaluation.ProjectIREvaluationContextStage,
) -> evaluation.ProjectIREvaluationContextStage:
    plan = stage.project_plan
    edge = plan.cross_relation_edges[0]
    dependency = copy(edge.authority.dependency)
    authority = _unsafe(edge.authority, dependency=dependency)
    assert type(authority) is project_ir.ProjectIRResolvedRelationAnchor
    use = _unsafe(edge.use, anchor=authority)
    assert type(use) is project_ir.ProjectIRUseOccurrence
    replacement = _unsafe(edge, authority=authority, use=use)
    assert type(replacement) is composition.ProjectIRCrossRelationEdge
    structural = _unsafe(
        plan.structural_stage,
        uses=tuple(
            use if item is edge.use else item for item in plan.structural_stage.uses
        ),
    )
    assert type(structural) is project_ir.ProjectIRStructuralStage
    return _with_plan(
        stage,
        structural_stage=structural,
        cross_relation_edges=(replacement, *plan.cross_relation_edges[1:]),
    )


@pytest.mark.parametrize(
    ("corrupt", "expected"),
    (
        (_foreign_snapshot, verification.ProjectIRVerificationIssueKind.SNAPSHOT_SCOPE),
        (
            _missing_output,
            verification.ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
        ),
        (
            _bad_use_endpoint,
            verification.ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
        ),
        (
            _duplicate_coordinate,
            verification.ProjectIRVerificationIssueKind.REF_COORDINATE,
        ),
        (
            _gapped_coordinate,
            verification.ProjectIRVerificationIssueKind.REF_COORDINATE,
        ),
        (
            _wrong_operator_order,
            verification.ProjectIRVerificationIssueKind.OPERATOR_LEGALITY,
        ),
        (
            _wrong_flow_adjacency,
            verification.ProjectIRVerificationIssueKind.OPERATOR_FLOW,
        ),
        (
            _wrong_cross_endpoint,
            verification.ProjectIRVerificationIssueKind.CROSS_RELATION_ENDPOINT,
        ),
        (
            _broken_compatibility,
            verification.ProjectIRVerificationIssueKind.ROW_COMPATIBILITY,
        ),
        (
            _missing_property,
            verification.ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
        ),
        (
            _missing_transfer,
            verification.ProjectIRVerificationIssueKind.PROPERTY_TRANSFER,
        ),
        (
            _missing_final_scalar,
            verification.ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION,
        ),
        (_wrong_effect, verification.ProjectIRVerificationIssueKind.EFFECT_ATTACHMENT),
        (
            _wrong_policy,
            verification.ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
        ),
        (
            _missing_evaluation_context,
            verification.ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
        ),
        (
            _duplicate_evaluation_context,
            verification.ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
        ),
        (
            _non_concrete_with_ir,
            verification.ProjectIRVerificationIssueKind.NON_CONCRETE_TERMINAL,
        ),
        (
            _actual_use_cycle,
            verification.ProjectIRVerificationIssueKind.ACTUAL_USE_CYCLE,
        ),
        (
            _detached_provenance,
            verification.ProjectIRVerificationIssueKind.PROVENANCE_REACHABILITY,
        ),
    ),
)
def test_independent_verifier_detects_controlled_corruption(
    tmp_path: Path,
    corrupt: Callable[
        [evaluation.ProjectIREvaluationContextStage],
        evaluation.ProjectIREvaluationContextStage,
    ],
    expected: verification.ProjectIRVerificationIssueKind,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    result = verification.verify_project_ir_stage(corrupt(stage))
    assert result.status is verification.ProjectIRVerificationStatus.INVALID
    assert not result.verified
    assert expected in tuple(issue.kind for issue in result.issues)


def _assessment(
    bundle: verification.ProjectIRAnalysisBundle,
    left: str,
    right: str,
) -> verification.ProjectIRSemanticEquivalenceAssessment:
    matches = tuple(
        assessment
        for assessment in bundle.equivalence_assessments
        if (
            assessment.left.semantic_facts.owner.identity.declared_name,
            assessment.right.semantic_facts.owner.identity.declared_name,
        )
        in {(left, right), (right, left)}
    )
    assert len(matches) == 1
    return matches[0]


def test_fresh_reverse_topological_and_transitive_reachability_analyses(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    verified = verification.verify_project_ir_stage(stage)
    first = verification.build_project_ir_analysis_bundle(verified)
    second = verification.build_project_ir_analysis_bundle(verified)
    structural = stage.project_plan.structural_stage
    assert first is not second
    assert first.reverse_uses[0] is not second.reverse_uses[0]
    assert first.reachability[0] is not second.reachability[0]
    assert tuple(entry.output for entry in first.reverse_uses) == structural.outputs
    assert all(
        entry.uses
        == tuple(use for use in structural.uses if use.output is entry.output)
        for entry in first.reverse_uses
    )
    assert tuple(node.ref.position for node in first.topological_order) == tuple(
        node.ref.position for node in second.topological_order
    )

    same_a = _concrete(stage, "same_a")
    chained = _concrete(stage, "chained")
    assert same_a.root.ref.position > chained.root.ref.position
    assert first.topological_order.index(same_a.root) < first.topological_order.index(
        chained.logical_stage.operators[0].node
    )
    rows = _concrete(stage, "rows")
    reachable = next(
        entry.reachable for entry in first.reachability if entry.source is rows.root
    )
    assert same_a.root in reachable
    assert chained.root in reachable
    other = _concrete(stage, "other")
    assert other.root not in reachable
    source_roots = tuple(
        fragment.root
        for fragment in (rows, other)
        if all(use.slot.consumer is not fragment.root for use in structural.uses)
    )
    assert tuple(first.topological_order.index(node) for node in source_roots) == tuple(
        sorted(first.topological_order.index(node) for node in source_roots)
    )


def test_same_scope_stale_analysis_and_noncanonical_issue_order_are_rejected(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    result = verification.verify_project_ir_stage(stage)
    bundle = verification.build_project_ir_analysis_bundle(result)
    stale = _unsafe(bundle.reachability[0], reachable=())
    assert type(stale) is verification.ProjectIRReachabilityEntry
    with pytest.raises(ValueError, match="fresh canonical"):
        verification.ProjectIRAnalysisBundle(
            verification=bundle.verification,
            reverse_uses=bundle.reverse_uses,
            topological_order=bundle.topological_order,
            reachability=(stale, *bundle.reachability[1:]),
            equivalence_assessments=bundle.equivalence_assessments,
            rewrite_readiness=bundle.rewrite_readiness,
        )

    corrupted = _missing_evaluation_context(_bad_use_endpoint(stage))
    issues = verification.verify_project_ir_stage(corrupted).issues
    assert verification.ProjectIRVerificationIssueKind.INPUT_SLOT_ATTACHMENT in tuple(
        issue.kind for issue in issues
    )
    order = tuple(verification.ProjectIRVerificationIssueKind)
    assert tuple(order.index(issue.kind) for issue in issues) == tuple(
        sorted(order.index(issue.kind) for issue in issues)
    )


def test_change_domains_derive_exact_invalidation_and_never_preserve_verification() -> (
    None
):
    topology = verification.assess_project_ir_analysis_invalidation(
        (verification.ProjectIRChangeDomain.TOPOLOGY,)
    )
    assert topology.invalidated == tuple(verification.ProjectIRAnalysisKind)
    assert topology.preserved == ()
    effects = verification.assess_project_ir_analysis_invalidation(
        (verification.ProjectIRChangeDomain.EFFECTS,)
    )
    assert effects.invalidated == (
        verification.ProjectIRAnalysisKind.SEMANTIC_EQUIVALENCE_CANDIDATES,
    )
    semantic_changes = tuple(
        verification.assess_project_ir_analysis_invalidation((domain,))
        for domain in (
            verification.ProjectIRChangeDomain.OPERATOR_SEMANTICS,
            verification.ProjectIRChangeDomain.OUTPUT_SEMANTICS,
            verification.ProjectIRChangeDomain.PROPERTIES,
            verification.ProjectIRChangeDomain.EFFECTS,
            verification.ProjectIRChangeDomain.EVALUATION_CONTEXT,
            verification.ProjectIRChangeDomain.PROVENANCE,
        )
    )
    assert all(item.invalidated == effects.invalidated for item in semantic_changes)
    estimates = verification.assess_project_ir_analysis_invalidation(
        (verification.ProjectIRChangeDomain.ESTIMATES,)
    )
    assert estimates.invalidated == ()
    assert estimates.preserved == tuple(verification.ProjectIRAnalysisKind)
    assert all(
        result.verification
        is verification.ProjectIRVerificationRequirement.RERUN_REQUIRED
        for result in (topology, effects, *semantic_changes, estimates)
    )
    assert "VERIFICATION" not in verification.ProjectIRAnalysisKind.__members__
    with pytest.raises(ValueError, match="explicit"):
        verification.assess_project_ir_analysis_invalidation(())


def test_candidate_equivalence_is_dimensioned_occurrence_distinct_and_not_rewrite_ready(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    bundle = verification.build_project_ir_analysis_bundle(
        verification.verify_project_ir_stage(stage)
    )
    candidate = _assessment(bundle, "same_a", "same_b")
    assert candidate.left is not candidate.right
    assert candidate.left.subject.anchor != candidate.right.subject.anchor
    assert candidate.status is (
        verification.ProjectIRSemanticEquivalenceStatus.CANDIDATE_NOT_DISPROVEN
    )
    assert tuple(item.dimension for item in candidate.dimensions) == tuple(
        verification.ProjectIRSemanticDimension
    )
    by_dimension = {item.dimension: item.status for item in candidate.dimensions}
    assert (
        by_dimension[verification.ProjectIRSemanticDimension.SCHEMA_TYPES]
        is verification.ProjectIRSemanticDimensionStatus.EVIDENCED
    )
    assert (
        by_dimension[verification.ProjectIRSemanticDimension.BAG_MULTIPLICITY]
        is verification.ProjectIRSemanticDimensionStatus.EVIDENCED
    )
    for dimension in (
        verification.ProjectIRSemanticDimension.VALUES,
        verification.ProjectIRSemanticDimension.EFFECTS_ERROR_BEHAVIOR,
        verification.ProjectIRSemanticDimension.EVALUATION_COUNT,
        verification.ProjectIRSemanticDimension.REQUIRED_CAPABILITIES,
        verification.ProjectIRSemanticDimension.PROVENANCE_TRACEABILITY,
    ):
        assert by_dimension[dimension] is (
            verification.ProjectIRSemanticDimensionStatus.NOT_PROVEN
        )
    readiness = next(
        item for item in bundle.rewrite_readiness if item.assessment is candidate
    )
    assert readiness.status is verification.ProjectIRRewriteReadinessStatus.BLOCKED
    assert verification.ProjectIRSemanticDimension.PROVENANCE_TRACEABILITY in (
        readiness.blockers
    )
    assert candidate.left.root is not candidate.right.root
    assert (
        candidate.left.root_relation_output is not candidate.right.root_relation_output
    )


def test_known_ordering_and_policy_conflicts_reject_equivalence(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    bundle = verification.build_project_ir_analysis_bundle(
        verification.verify_project_ir_stage(stage)
    )
    ordered = _assessment(bundle, "ordered", "unordered")
    assert ordered.status is (
        verification.ProjectIRSemanticEquivalenceStatus.KNOWN_INCOMPATIBLE
    )
    assert (
        next(
            item.status
            for item in ordered.dimensions
            if item.dimension is verification.ProjectIRSemanticDimension.ORDERING
        )
        is verification.ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    )
    policy = _assessment(bundle, "window_row", "window_rank")
    assert policy.status is (
        verification.ProjectIRSemanticEquivalenceStatus.KNOWN_INCOMPATIBLE
    )
    assert (
        next(
            item.status
            for item in policy.dimensions
            if item.dimension is verification.ProjectIRSemanticDimension.POLICY_CONTEXT
        )
        is verification.ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    )


def test_bag_or_effect_corruption_is_invalid_before_equivalence_analysis(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    for corrupted in (_missing_bag_property(stage), _wrong_effect(stage)):
        result = verification.verify_project_ir_stage(corrupted)
        assert result.status is verification.ProjectIRVerificationStatus.INVALID
        with pytest.raises(ValueError, match="VERIFIED"):
            verification.build_project_ir_analysis_bundle(result)


def test_invalid_or_cyclic_ir_cannot_produce_analysis_or_recursion_semantics(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    corrupted = _actual_use_cycle(stage)
    result = verification.verify_project_ir_stage(corrupted)
    assert result.status is verification.ProjectIRVerificationStatus.INVALID
    assert verification.ProjectIRVerificationIssueKind.ACTUAL_USE_CYCLE in tuple(
        issue.kind for issue in result.issues
    )
    with pytest.raises(ValueError, match="VERIFIED"):
        verification.build_project_ir_analysis_bundle(result)
    forbidden = {
        "OptimizationMemo",
        "ChosenTargetPlan",
        "Fixpoint",
        "RecursiveRelation",
        "WorkingTable",
        "DeltaRelation",
        "SemiNaive",
    }
    assert forbidden.isdisjoint(vars(verification))


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import build_project_ir_evaluation_context_stage
from pietto._project.project_ir_verification import build_project_ir_analysis_bundle, verify_project_ir_stage

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
facts = semantic.module_semantic_facts
attribution = semantic.module_attribution_facts
assert facts is not None and attribution is not None
plan = build_project_ir_project_plan(semantic_facts=facts, attribution=attribution, allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()))
stage = build_project_ir_evaluation_context_stage(plan)
result = verify_project_ir_stage(stage)
bundle = build_project_ir_analysis_bundle(result)
print((result.status.value, tuple(node.ref.position for node in bundle.topological_order), tuple((item.left.subject.anchor.identity.declaration_position, item.right.subject.anchor.identity.declaration_position, item.status.value) for item in bundle.equivalence_assessments), tuple(tuple(node.ref.position for node in entry.reachable) for entry in bundle.reachability)))
"""


def test_verification_analysis_are_hash_seed_cwd_independent_and_public_zero_delta(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("811", "cwd-b")):
        cwd = tmp_path / cwd_name
        cwd.mkdir()
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        existing = environment.get("PYTHONPATH")
        source_root = str(REPO_ROOT / "src")
        environment["PYTHONPATH"] = (
            source_root if not existing else os.pathsep.join((source_root, existing))
        )
        completed = subprocess.run(
            (sys.executable, "-c", _DETERMINISM_PROBE, str(project_root)),
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]
    assert not hasattr(pietto, "ProjectIRVerificationResult")
    assert not hasattr(project_package, "ProjectIRVerificationResult")
    assert tuple(item.name for item in fields(RelationIR)) == (
        "symbol",
        "name",
        "kind",
        "source",
        "filter",
        "projections",
        "row_schema",
        "span",
        "order_by",
        "limit",
        "group_keys",
        "result_predicate",
        "named_windows",
    )
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        REPO_ROOT / "src/pietto/ir/model.py",
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "project_ir_verification" not in text
        assert "ProjectIRVerificationResult" not in text
