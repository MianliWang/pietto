from __future__ import annotations

import ast
from copy import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pietto._project import project_bag_null_oracle as oracle
from pietto._project import project_phase62_verification as verification
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_ir import ProjectIRPlanNodeRef, ProjectIRSnapshotScope
from pietto._project.project_ir_joins import ProjectIRConcreteJoinRegion
from pietto._project.project_multifact import (
    ProjectCommonGrainStatus,
    ProjectMultiFactAnalysis,
    ProjectMultiFactMultiplicityRisk,
    ProjectMultiFactStructuralAlignment,
)
from test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment import (
    _build,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_SOURCE = REPO_ROOT / "src/pietto/_project/project_phase62_verification.py"
ORACLE_SOURCE = REPO_ROOT / "src/pietto/_project/project_bag_null_oracle.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md"
)


def test_slice13_owners_are_private() -> None:
    assert oracle.__all__ == ()
    assert verification.__all__ == ()


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> ProjectMultiFactAnalysis:
    return _build(tmp_path_factory.mktemp("p62s13"))


def _unsafe[Value](value: Value, **changes: object) -> Value:
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


def _fresh(tmp_path: Path, name: str) -> ProjectMultiFactAnalysis:
    return _build(tmp_path / name)


def _join(root: ProjectMultiFactAnalysis, owner: str, position: int = 0):
    region = next(
        region
        for region in root.join_regions.regions
        if region.ledger.owner.definition.name == owner
    )
    assert type(region) is ProjectIRConcreteJoinRegion
    return region.joins[position]


def _wrapper(root: ProjectMultiFactAnalysis, owner: str):
    return next(
        item
        for item in root.concrete_regions
        if item.region.ledger.owner.definition.name == owner
    )


def _kinds(
    root: ProjectMultiFactAnalysis,
) -> tuple[verification.ProjectPhase62VerificationIssueKind, ...]:
    return tuple(
        issue.kind for issue in verification.verify_project_phase62(root).issues
    )


def _row(*values: oracle.ProjectBagNullScalar) -> oracle.ProjectBagNullRow:
    return oracle.ProjectBagNullRow(values=values)


def _bag(
    *entries: tuple[oracle.ProjectBagNullRow, int],
) -> oracle.ProjectFiniteBag:
    return oracle.ProjectFiniteBag(
        entries=tuple(
            oracle.ProjectBagNullEntry(row=row, multiplicity=multiplicity)
            for row, multiplicity in entries
        )
    )


def _contents(bag: oracle.ProjectFiniteBag) -> dict[oracle.ProjectBagNullRow, int]:
    return {entry.row: entry.multiplicity for entry in bag.entries}


def _spec(
    kind: oracle.ProjectBagNullJoinKind = oracle.ProjectBagNullJoinKind.INNER,
) -> oracle.ProjectBagNullJoinSpecification:
    return oracle.ProjectBagNullJoinSpecification(
        kind=kind,
        left_width=2,
        right_width=2,
        correspondences=(
            oracle.ProjectBagNullEqualityCorrespondence(
                left_position=0,
                right_position=0,
            ),
        ),
    )


def test_oracle_three_valued_equality_and_conjunction_are_exact() -> None:
    null = oracle.project_bag_null()
    one = oracle.project_bag_int(1)
    assert oracle.evaluate_project_bag_null_equality(null, one) is (
        oracle.ProjectBagNullTruth.UNKNOWN
    )
    assert oracle.evaluate_project_bag_null_equality(one, null) is (
        oracle.ProjectBagNullTruth.UNKNOWN
    )
    assert oracle.evaluate_project_bag_null_equality(
        one, oracle.project_bag_int(1)
    ) is (oracle.ProjectBagNullTruth.TRUE)
    assert oracle.evaluate_project_bag_null_equality(
        one, oracle.project_bag_text("1")
    ) is (oracle.ProjectBagNullTruth.FALSE)
    conjunction = oracle.ProjectBagNullJoinSpecification(
        kind=oracle.ProjectBagNullJoinKind.INNER,
        left_width=2,
        right_width=2,
        correspondences=(
            oracle.ProjectBagNullEqualityCorrespondence(
                left_position=0, right_position=0
            ),
            oracle.ProjectBagNullEqualityCorrespondence(
                left_position=1, right_position=1
            ),
        ),
    )
    assert (
        oracle.evaluate_project_bag_null_predicate(
            conjunction,
            _row(null, oracle.project_bag_int(2)),
            _row(one, oracle.project_bag_int(3)),
        )
        is oracle.ProjectBagNullTruth.FALSE
    )
    assert (
        oracle.evaluate_project_bag_null_predicate(
            conjunction,
            _row(null, oracle.project_bag_int(2)),
            _row(one, oracle.project_bag_int(2)),
        )
        is oracle.ProjectBagNullTruth.UNKNOWN
    )


def test_inner_join_preserves_bag_multiplication_and_rejects_set_deduplication() -> (
    None
):
    left_row = _row(oracle.project_bag_int(1), oracle.project_bag_text("left"))
    right_row = _row(oracle.project_bag_int(1), oracle.project_bag_text("right"))
    result = oracle.evaluate_project_bag_null_join(
        _spec(),
        _bag((left_row, 2)),
        _bag((right_row, 3)),
    )
    output = _row(*left_row.values, *right_row.values)
    assert _contents(result) == {output: 6}
    assert _contents(result) != {output: 1}


def test_left_join_matches_inner_and_preserves_each_unmatched_occurrence() -> None:
    matched = _row(oracle.project_bag_int(1), oracle.project_bag_text("matched"))
    unmatched = _row(oracle.project_bag_int(2), oracle.project_bag_text("unmatched"))
    unknown = _row(oracle.project_bag_null(), oracle.project_bag_text("unknown"))
    right = _row(oracle.project_bag_int(1), oracle.project_bag_text("right"))
    left_bag = _bag((matched, 2), (unmatched, 4), (unknown, 5))
    right_bag = _bag((right, 3))
    inner = oracle.evaluate_project_bag_null_join(_spec(), left_bag, right_bag)
    left = oracle.evaluate_project_bag_null_join(
        _spec(oracle.ProjectBagNullJoinKind.LEFT), left_bag, right_bag
    )
    nulls = (oracle.project_bag_null(), oracle.project_bag_null())
    assert _contents(inner) == {_row(*matched.values, *right.values): 6}
    assert _contents(left) == {
        _row(*matched.values, *right.values): 6,
        _row(*unmatched.values, *nulls): 4,
        _row(*unknown.values, *nulls): 5,
    }


def test_oracle_scaling_order_and_inner_swap_metamorphisms_are_bag_exact() -> None:
    left_rows = (
        (_row(oracle.project_bag_int(1), oracle.project_bag_text("a")), 2),
        (_row(oracle.project_bag_int(2), oracle.project_bag_text("b")), 3),
    )
    right_rows = (
        (_row(oracle.project_bag_int(1), oracle.project_bag_text("x")), 5),
        (_row(oracle.project_bag_int(2), oracle.project_bag_text("y")), 7),
    )
    base = oracle.evaluate_project_bag_null_join(
        _spec(), _bag(*left_rows), _bag(*right_rows)
    )
    reversed_inputs = oracle.evaluate_project_bag_null_join(
        _spec(), _bag(*reversed(left_rows)), _bag(*reversed(right_rows))
    )
    assert _contents(base) == _contents(reversed_inputs)

    scaled_left = oracle.evaluate_project_bag_null_join(
        _spec(),
        _bag(*((row, multiplicity * 2) for row, multiplicity in left_rows)),
        _bag(*right_rows),
    )
    assert _contents(scaled_left) == {
        row: multiplicity * 2 for row, multiplicity in _contents(base).items()
    }
    scaled_right = oracle.evaluate_project_bag_null_join(
        _spec(),
        _bag(*left_rows),
        _bag(*((row, multiplicity * 2) for row, multiplicity in right_rows)),
    )
    assert _contents(scaled_right) == {
        row: multiplicity * 2 for row, multiplicity in _contents(base).items()
    }
    swapped = oracle.evaluate_project_bag_null_join(
        _spec(), _bag(*right_rows), _bag(*left_rows)
    )
    swapped_back = {
        _row(*row.values[2:], *row.values[:2]): multiplicity
        for row, multiplicity in _contents(swapped).items()
    }
    assert swapped_back == _contents(base)
    left_forward = oracle.evaluate_project_bag_null_join(
        _spec(oracle.ProjectBagNullJoinKind.LEFT),
        _bag(*left_rows),
        _bag((right_rows[0][0], right_rows[0][1])),
    )
    left_swapped = oracle.evaluate_project_bag_null_join(
        _spec(oracle.ProjectBagNullJoinKind.LEFT),
        _bag((right_rows[0][0], right_rows[0][1])),
        _bag(*left_rows),
    )
    assert _contents(left_forward) != _contents(left_swapped)


def test_oracle_rejects_inputs_beyond_its_small_reference_boundary() -> None:
    rows = tuple(
        (_row(oracle.project_bag_int(position), oracle.project_bag_text("x")), 1)
        for position in range(9)
    )
    with pytest.raises(ValueError, match="bounded reference scope"):
        oracle.evaluate_project_bag_null_join(_spec(), _bag(*rows), _bag())
    with pytest.raises(ValueError, match="bounded reference scope"):
        oracle.evaluate_project_bag_null_join(
            _spec(),
            _bag((rows[0][0], 17)),
            _bag(),
        )
    with pytest.raises(ValueError, match="bounded input scope"):
        oracle.ProjectBagNullJoinSpecification(
            kind=oracle.ProjectBagNullJoinKind.INNER,
            left_width=9,
            right_width=1,
            correspondences=(
                oracle.ProjectBagNullEqualityCorrespondence(
                    left_position=0,
                    right_position=0,
                ),
            ),
        )


def test_valid_phase62_root_verifies_with_fixed_empty_issue_order(
    root: ProjectMultiFactAnalysis,
) -> None:
    result = verification.verify_project_phase62(root)
    assert result.status is verification.ProjectPhase62VerificationStatus.VERIFIED
    assert result.verified
    assert result.issues == ()
    assert result.base_verification.verified
    assert tuple(verification.ProjectPhase62VerificationIssueKind) == (
        verification.ProjectPhase62VerificationIssueKind.ROOT_COHERENCE,
        verification.ProjectPhase62VerificationIssueKind.BASE_PROJECT_IR,
        verification.ProjectPhase62VerificationIssueKind.JOIN_SCOPE_COORDINATE,
        verification.ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT,
        verification.ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS,
        verification.ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
        verification.ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING,
        verification.ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER,
        verification.ProjectPhase62VerificationIssueKind.JOIN_KEY_FD_GRAIN,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
        verification.ProjectPhase62VerificationIssueKind.CHASM_RISK,
        verification.ProjectPhase62VerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE,
    )


def test_verified_bundle_freshly_covers_all_five_phase62_analyses(
    root: ProjectMultiFactAnalysis,
) -> None:
    result = verification.verify_project_phase62(root)
    first = verification.build_project_phase62_analysis_bundle(result)
    second = verification.build_project_phase62_analysis_bundle(result)
    base = root.evaluation.project_plan.structural_stage
    joins = root.join_regions.structural
    assert len(first.combined_reverse_uses) == len(base.outputs) + len(joins.outputs)
    assert len(first.combined_topological_order) == len(base.nodes) + len(joins.nodes)
    assert len(first.nulling_provenance) == sum(
        len(item.join.output.row_shape.fields)
        for item in root.join_regions.properties.outputs
    )
    assert len(first.fact_localities) == len(root.facts)
    assert first.multifact_alignments.alignments == root.alignments
    assert first.combined_reverse_uses is not second.combined_reverse_uses
    assert first.combined_topological_order is not second.combined_topological_order
    assert all(
        entry.localities
        == (
            root.home_localities[position],
            *(locality for locality in root.join_localities if locality.fact is fact),
        )
        for position, (entry, fact) in enumerate(
            zip(first.fact_localities, root.facts, strict=True)
        )
    )

    nulled_position = next(
        position
        for position, entry in enumerate(first.nulling_provenance)
        if entry.nulling_joins
    )
    stale = _unsafe(
        first.nulling_provenance[nulled_position],
        nulling_joins=(),
    )
    with pytest.raises(ValueError, match="fresh canonical"):
        verification.ProjectPhase62AnalysisBundle(
            verification=first.verification,
            combined_reverse_uses=first.combined_reverse_uses,
            combined_topological_order=first.combined_topological_order,
            nulling_provenance=(
                *first.nulling_provenance[:nulled_position],
                stale,
                *first.nulling_provenance[nulled_position + 1 :],
            ),
            fact_localities=first.fact_localities,
            multifact_alignments=first.multifact_alignments,
        )


def test_phase62_change_domains_derive_exact_invalidation_matrix() -> None:
    all_kinds = tuple(verification.ProjectPhase62AnalysisKind)
    topology = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.BASE_TOPOLOGY,)
    )
    assert topology.invalidated == all_kinds
    assert topology.preserved == ()
    join_semantics = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.JOIN_SEMANTICS,)
    )
    assert join_semantics.preserved == (
        verification.ProjectPhase62AnalysisKind.COMBINED_REVERSE_USE_INDEX,
        verification.ProjectPhase62AnalysisKind.COMBINED_TOPOLOGICAL_ORDER,
    )
    assert join_semantics.invalidated == all_kinds[2:]
    base_semantics = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.BASE_SEMANTICS,)
    )
    assert base_semantics.invalidated == all_kinds[3:]
    alignment = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.MULTIFACT_ALIGNMENT,)
    )
    assert alignment.invalidated == (all_kinds[-1],)
    estimates = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.ESTIMATES,)
    )
    assert estimates.invalidated == ()
    assert estimates.preserved == all_kinds
    assert all(
        item.verification
        is verification.ProjectPhase62VerificationRequirement.RERUN_REQUIRED
        for item in (
            topology,
            join_semantics,
            base_semantics,
            alignment,
            estimates,
        )
    )
    with pytest.raises(ValueError, match="unique and canonical"):
        verification.assess_project_phase62_analysis_invalidation(())


def test_join_scope_slot_use_accumulation_and_region_corruptions_are_independent(
    tmp_path: Path,
) -> None:
    foreign = _fresh(tmp_path, "foreign")
    foreign_join = _join(foreign, "aligned_join")
    object.__setattr__(
        foreign_join.node,
        "ref",
        ProjectIRPlanNodeRef(
            scope=ProjectIRSnapshotScope(),
            position=foreign_join.node.ref.position,
        ),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_SCOPE_COORDINATE
        in _kinds(foreign)
    )

    gapped = _fresh(tmp_path, "gapped")
    gapped_join = _join(gapped, "aligned_join")
    object.__setattr__(
        gapped_join.node,
        "ref",
        ProjectIRPlanNodeRef(
            scope=gapped_join.node.ref.scope,
            position=gapped_join.node.ref.position + 1,
        ),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_SCOPE_COORDINATE
        in _kinds(gapped)
    )

    ordinal = _fresh(tmp_path, "ordinal")
    ordinal_join = _join(ordinal, "aligned_join")
    object.__setattr__(ordinal_join.input_slots[0], "input_ordinal", 1)
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT
        in _kinds(ordinal)
    )

    equal_copy = _fresh(tmp_path, "equal-use-copy")
    copied_join = _join(equal_copy, "aligned_join")
    object.__setattr__(
        copied_join,
        "input_uses",
        (_unsafe(copied_join.input_uses[0]), copied_join.input_uses[1]),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT
        in _kinds(equal_copy)
    )

    detached = _fresh(tmp_path, "detached")
    detached_join = _join(detached, "aligned_join")
    object.__setattr__(
        detached_join.input_uses[0],
        "output",
        detached.evaluation.project_plan.structural_stage.outputs[0],
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT
        in _kinds(detached)
    )

    accumulated = _fresh(tmp_path, "accumulated")
    second = _join(accumulated, "multihop_join", 1)
    object.__setattr__(
        second.input_uses[0],
        "output",
        accumulated.evaluation.project_plan.structural_stage.outputs[0],
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT
        in _kinds(accumulated)
    )

    partial = _fresh(tmp_path, "partial")
    partial_region = next(
        region
        for region in partial.join_regions.regions
        if region.ledger.owner.definition.name == "multihop_join"
    )
    assert type(partial_region) is ProjectIRConcreteJoinRegion
    object.__setattr__(partial_region, "joins", partial_region.joins[:-1])
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS
        in _kinds(partial)
    )


def test_join_condition_nulling_property_key_fd_and_grain_corruptions_are_independent(
    tmp_path: Path,
) -> None:
    condition = _fresh(tmp_path, "condition")
    object.__setattr__(
        _join(condition, "aligned_join"),
        "condition",
        _join(condition, "comparable_join").condition,
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING
        in _kinds(condition)
    )

    nulling = _fresh(tmp_path, "nulling")
    nulling_join = _join(nulling, "self_fact_join")
    nulled_field = next(
        field for field in nulling_join.output.row_shape.fields if field.nulling_joins
    )
    object.__setattr__(nulled_field, "nulling_joins", ())
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING
        in _kinds(nulling)
    )

    nullability = _fresh(tmp_path, "nullability")
    nullability_join = _join(nullability, "self_fact_join")
    nullable_field = next(
        field
        for field in nullability_join.output.row_shape.fields
        if field.nulling_joins
    )
    object.__setattr__(
        nullable_field,
        "effective_nullability",
        ProjectRowFieldNullability.NON_NULL,
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING
        in _kinds(nullability)
    )

    null_property = _fresh(tmp_path, "null-property")
    target_output = next(
        item
        for item in null_property.join_regions.properties.outputs
        if item.join.use.owner.definition.name == "self_fact_join"
    )
    unrelated_property = next(
        item.null_extension
        for item in null_property.join_regions.properties.outputs
        if not any(field.nulling_joins for field in item.join.output.row_shape.fields)
    )
    object.__setattr__(target_output, "null_extension", unrelated_property)
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING
        in _kinds(null_property)
    )

    key = _fresh(tmp_path, "key")
    keyed = next(
        item.relational
        for item in key.join_regions.properties.outputs
        if item.relational.keys
    )
    object.__setattr__(keyed, "keys", ())
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER
        in _kinds(key)
    )

    fd = _fresh(tmp_path, "fd")
    with_fds = next(
        item.relational
        for item in fd.join_regions.properties.outputs
        if item.relational.fds
    )
    object.__setattr__(with_fds, "fds", ())
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER
        in _kinds(fd)
    )

    value_class = _fresh(tmp_path, "value-class")
    relational = value_class.join_regions.properties.outputs[0].relational
    first_class = relational.value_classes[0]
    object.__setattr__(
        first_class,
        "members",
        (_unsafe(first_class.members[0]), *first_class.members[1:]),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER
        in _kinds(value_class)
    )

    grain = _fresh(tmp_path, "grain")
    grain_output = grain.join_regions.properties.outputs[0].relational.grain
    object.__setattr__(grain_output, "active", ())
    assert verification.ProjectPhase62VerificationIssueKind.JOIN_KEY_FD_GRAIN in _kinds(
        grain
    )


def test_multifact_catalog_locality_alignment_and_chasm_corruptions_are_independent(
    tmp_path: Path,
) -> None:
    removed = _fresh(tmp_path, "fact-removed")
    object.__setattr__(removed, "facts", removed.facts[:-1])
    assert verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG in _kinds(
        removed
    )

    duplicated = _fresh(tmp_path, "fact-duplicated")
    object.__setattr__(duplicated, "facts", (*duplicated.facts, duplicated.facts[0]))
    assert verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG in _kinds(
        duplicated
    )

    catalog_index = _fresh(tmp_path, "catalog-index")
    object.__setattr__(catalog_index, "facts_by_context", {})
    assert verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG in _kinds(
        catalog_index
    )

    introduction = _fresh(tmp_path, "introduction")
    reused = _wrapper(introduction, "reused_join").localities
    object.__setattr__(reused[0], "introduction_use", reused[1].introduction_use)
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY
        in _kinds(introduction)
    )

    contextual = _fresh(tmp_path, "contextual")
    locality = _wrapper(contextual, "chasm_join").localities[0]
    object.__setattr__(locality.contextual_grain, "factors", ())
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY
        in _kinds(contextual)
    )

    blocker = _fresh(tmp_path, "blocker")
    ambiguous_subject = next(
        item
        for item in blocker.non_concrete_regions
        if item.region.ledger.owner.definition.name == "ambiguous_fact_join"
    )
    object.__setattr__(
        ambiguous_subject,
        "structural",
        ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE,
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY
        in _kinds(blocker)
    )

    bucket = _fresh(tmp_path, "fact-bucket")
    bucket_region = _wrapper(bucket, "chasm_join")
    first_candidate = bucket_region.actual_candidates[0]
    corrupted_buckets = dict(bucket_region.fact_buckets)
    corrupted_buckets[first_candidate] = ()
    object.__setattr__(bucket_region, "fact_buckets", corrupted_buckets)
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT
        in _kinds(bucket)
    )

    dropped = _fresh(tmp_path, "dropped-candidate")
    dropped_alignment = _wrapper(dropped, "chasm_join").alignments[0]
    object.__setattr__(dropped_alignment.common_grain, "candidates", ())
    object.__setattr__(
        dropped_alignment.common_grain,
        "status",
        ProjectCommonGrainStatus.NONE,
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT
        in _kinds(dropped)
    )

    winner = _fresh(tmp_path, "first-winner")
    winner_alignment = next(
        item
        for item in _wrapper(winner, "aligned_join").alignments
        if item.common_grain.status is ProjectCommonGrainStatus.AMBIGUOUS
    )
    object.__setattr__(
        winner_alignment.common_grain,
        "candidates",
        (winner_alignment.common_grain.candidates[0],),
    )
    object.__setattr__(
        winner_alignment.common_grain,
        "status",
        ProjectCommonGrainStatus.UNIQUE,
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT
        in _kinds(winner)
    )

    copied_candidate = _fresh(tmp_path, "copied-candidate")
    copied_alignment = _wrapper(copied_candidate, "chasm_join").alignments[0]
    object.__setattr__(
        copied_alignment.common_grain.candidates[0],
        "candidate",
        _unsafe(copied_alignment.common_grain.candidates[0].candidate),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT
        in _kinds(copied_candidate)
    )

    copied_context = _fresh(tmp_path, "copied-context")
    context_alignment = _wrapper(copied_context, "aligned_join").alignments[0]
    assert context_alignment.grain_comparison is not None
    object.__setattr__(
        context_alignment.grain_comparison,
        "left",
        _unsafe(context_alignment.left.contextual_grain),
    )
    assert (
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT
        in _kinds(copied_context)
    )

    participant = _fresh(tmp_path, "participant")
    chasm = _wrapper(participant, "chasm_join").chasms[0]
    object.__setattr__(chasm, "localities", chasm.localities[:1])
    assert verification.ProjectPhase62VerificationIssueKind.CHASM_RISK in _kinds(
        participant
    )

    chasm_join = _fresh(tmp_path, "chasm-join")
    detached_chasm = _wrapper(chasm_join, "chasm_join").chasms[0]
    object.__setattr__(detached_chasm, "introduction_joins", ())
    assert verification.ProjectPhase62VerificationIssueKind.CHASM_RISK in _kinds(
        chasm_join
    )

    risk = _fresh(tmp_path, "risk")
    risk_alignment = _wrapper(risk, "incompatible_join").alignments[0]
    object.__setattr__(
        risk_alignment,
        "multiplicity_risks",
        (
            *risk_alignment.multiplicity_risks,
            ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
        ),
    )
    assert verification.ProjectPhase62VerificationIssueKind.CHASM_RISK in _kinds(risk)


def test_combined_cycle_is_invalid_and_invalid_result_cannot_form_bundle(
    tmp_path: Path,
) -> None:
    root = _fresh(tmp_path, "cycle")
    first = _join(root, "multihop_join", 0)
    second = _join(root, "multihop_join", 1)
    object.__setattr__(first.input_uses[0], "output", second.output.occurrence)
    result = verification.verify_project_phase62(root)
    kinds = tuple(issue.kind for issue in result.issues)
    assert result.status is verification.ProjectPhase62VerificationStatus.INVALID
    assert (
        verification.ProjectPhase62VerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE
        in kinds
    )
    order = tuple(verification.ProjectPhase62VerificationIssueKind)
    assert tuple(order.index(kind) for kind in kinds) == tuple(
        sorted(order.index(kind) for kind in kinds)
    )
    with pytest.raises(ValueError, match="Only VERIFIED"):
        verification.build_project_phase62_analysis_bundle(result)


def test_verifier_and_oracle_are_statically_separate_private_boundaries() -> None:
    verifier_source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    oracle_source = ORACLE_SOURCE.read_text(encoding="utf-8")
    oracle_tree = ast.parse(oracle_source, filename=str(ORACLE_SOURCE))
    imported_modules = tuple(
        node.module for node in oracle_tree.body if isinstance(node, ast.ImportFrom)
    )
    assert imported_modules == ("__future__", "dataclasses", "enum")
    assert "pietto" not in oracle_source
    for forbidden in (
        "project_bag_null_oracle",
        "evaluate_project_bag_null",
        "build_project_ir_join_region",
        "build_project_multifact_analysis",
        "lru_cache",
        "functools.cache",
        "pickle",
        "shelve",
        "optimizer",
    ):
        assert forbidden not in verifier_source
    for forbidden in (
        "ProjectIR",
        "relationship",
        "SemanticModel",
        "backend",
        "aggregate",
        "window",
        "where",
    ):
        assert forbidden.lower() not in oracle_source.lower()


_DETERMINISM_SCRIPT = r"""
import json
from pathlib import Path
import sys

from test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment import _build
from pietto._project import project_phase62_verification as verification

root = _build(Path(sys.argv[1]))
if sys.argv[2] == "reverse":
    invalidation = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.ESTIMATES,)
    )
    result = verification.verify_project_phase62(root)
    bundle = verification.build_project_phase62_analysis_bundle(result)
else:
    result = verification.verify_project_phase62(root)
    bundle = verification.build_project_phase62_analysis_bundle(result)
    invalidation = verification.assess_project_phase62_analysis_invalidation(
        (verification.ProjectPhase62ChangeDomain.ESTIMATES,)
    )
print(json.dumps({
    "status": result.status.value,
    "issues": [(item.kind.value, None if item.coordinate is None else item.coordinate.__class__.__name__) for item in result.issues],
    "topology": [item.ref.position for item in bundle.combined_topological_order],
    "reverse": [(item.output.ref.position, [use.ref.position for use in item.uses]) for item in bundle.combined_reverse_uses],
    "nulling": [(item.coordinate.output.position, item.coordinate.field_position, [ref.position for ref in item.nulling_joins]) for item in bundle.nulling_provenance],
    "facts": [(item.identity.aggregate_node.position, item.identity.aggregate_result_position, len(item.localities)) for item in bundle.fact_localities],
    "alignments": [(item.structural.value, [risk.value for risk in item.multiplicity_risks]) for item in bundle.multifact_alignments.alignments],
    "preserved": [item.value for item in invalidation.preserved],
}, separators=(",", ":")))
"""


def test_hash_seed_cwd_and_operation_order_do_not_change_phase62_results(
    tmp_path: Path,
) -> None:
    observations: list[dict[str, object]] = []
    for position, (seed, order) in enumerate(
        (("0", "normal"), ("1", "reverse"), ("4294967295", "normal"))
    ):
        cwd = tmp_path / f"cwd-{position}"
        cwd.mkdir()
        project = tmp_path / f"project-{position}"
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = os.pathsep.join(
            (
                str(REPO_ROOT / "src"),
                str(REPO_ROOT / "tests"),
                environment.get("PYTHONPATH", ""),
            )
        )
        completed = subprocess.run(
            (sys.executable, "-c", _DETERMINISM_SCRIPT, str(project), order),
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stderr == ""
        observations.append(json.loads(completed.stdout))
    assert observations[1:] == observations[:-1]


def test_slice13_contract_records_exact_boundaries_and_pass_title() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "constructor validity != independent verification",
        "verification != oracle proof",
        "verification = RERUN_REQUIRED",
        "bounded oracle != complete theorem prover",
        "The verifier neither imports nor invokes the oracle",
        "A4/M5/D0",
        "INDEPENDENT_VERIFIER_REPLAY_DOES_NOT_CLOSE_EXACT_IDENTITY_AND_INDEX_EVIDENCE",
        "Slice 13 repair batches: 1/1",
        "Phase 62 Slice 14 = NEXT / NOT IMPLEMENTED",
        "PASS — PHASE62_SLICE13_INTEGRITY_VERIFIER_ANALYSIS_INVALIDATION_BOUNDED_BAG_NULL_SEMANTIC_ORACLE_END_TO_END",
    ):
        assert evidence in document
