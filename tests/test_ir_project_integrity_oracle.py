from __future__ import annotations

import ast
from copy import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pietto._project import project_bag_null_oracle as oracle
from pietto._project import project_phase62_verification as verification
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
from pietto._project.project_multifact import (
    ProjectCommonGrainStatus,
    ProjectMultiFactMultiplicityRisk,
)
from pietto._project.project_ir import ProjectIRPlanNodeRef, ProjectIRSnapshotScope
from pietto._project.project_query_block_ir import ProjectIRCompletedQueryBlockOutput
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisKind,
    ProjectIRQueryBlockOverlayRequirement,
    ProjectIRQueryBlockVerificationIssueKind,
    assess_project_query_block_ir_invalidation,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_ir_verification import ProjectIRChangeDomain
from _pietto_project_aggregate import (
    _build,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_SOURCE = REPO_ROOT / "src/pietto/_project/project_phase62_verification.py"
ORACLE_SOURCE = REPO_ROOT / "src/pietto/_project/project_bag_null_oracle.py"


def test_slice13_owners_are_private() -> None:
    assert oracle.__all__ == ()
    assert verification.__all__ == ()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    return _build(tmp_path_factory.mktemp("integrity"))


def _unsafe[Value](value: Value, **changes: object) -> Value:
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


def _fresh(tmp_path: Path, name: str):
    return _build(tmp_path / name)


def _entry(snapshot, owner: str):
    entry = next(
        item for item in snapshot.entries if item.owner.definition.name == owner
    )
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    assert entry.join_prefix is not None
    return entry


def _join(snapshot, owner: str, position: int = 0):
    entry = _entry(snapshot, owner)
    assert entry.join_prefix is not None
    return entry.join_prefix.joins[position]


def _kinds(root):
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
    built,
) -> None:
    _, completed, bundle, _ = built
    root = completed.verification.root
    assert completed.effective_outputs.current_regions
    assert verify_project_query_block_ir(bundle.verification.root).verified
    result = verification.verify_project_phase62(root)
    assert result.status is verification.ProjectPhase62VerificationStatus.VERIFIED
    assert result.verified
    assert result.issues == ()
    assert result.base_verification.verified
    assert tuple(verification.ProjectPhase62VerificationIssueKind) == (
        verification.ProjectPhase62VerificationIssueKind.ROOT_COHERENCE,
        verification.ProjectPhase62VerificationIssueKind.BASE_PROJECT_IR,
        verification.ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
        verification.ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
        verification.ProjectPhase62VerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE,
    )


def test_verified_bundle_freshly_covers_base_and_current_analyses(built) -> None:
    _, completed, bundle, product = built
    root = completed.verification.root
    base = verification.build_project_phase62_analysis_bundle(
        verification.verify_project_phase62(root)
    )
    structural = root.evaluation.project_plan.structural_stage
    # The JOIN regions allocate nothing: the combined graph is the base plan's.
    assert len(base.combined_reverse_uses) == len(structural.outputs)
    assert len(base.combined_topological_order) == len(structural.nodes)
    assert base.multifact_alignments.alignments == root.home_alignments
    assert len(base.fact_localities) == len(root.facts)
    assert len(root.home_localities) == len(root.facts)
    assert all(
        entry.localities == (root.home_localities[position],)
        for position, entry in enumerate(base.fact_localities)
    )
    observed = product.inspection
    nulled = next(
        field for field in observed.query_block_row_fields if field.nulling_joins
    )
    stale = _unsafe(nulled, nulling_joins=())
    with pytest.raises(ValueError, match="query_block_row_fields"):
        replace(
            observed,
            query_block_row_fields=tuple(
                stale if field is nulled else field
                for field in observed.query_block_row_fields
            ),
        )
    snapshot = bundle.verification.root
    result = verify_project_query_block_ir(snapshot)
    first = build_project_query_block_ir_analysis_bundle(result)
    second = build_project_query_block_ir_analysis_bundle(result)
    assert first.combined_reverse_uses
    assert first.combined_topological_order
    assert first.combined_reverse_uses is not second.combined_reverse_uses
    assert first.combined_topological_order is not second.combined_topological_order
    with pytest.raises(ValueError, match="fresh graph products"):
        type(first)(
            verification=result,
            combined_reverse_uses=(),
            combined_topological_order=first.combined_topological_order,
            combined_reachability=first.combined_reachability,
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
    assert base_semantics.invalidated == all_kinds[2:]
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


def test_current_invalidation_uses_real_overlay_domains() -> None:
    for domain in (
        ProjectIRChangeDomain.TOPOLOGY,
        ProjectIRChangeDomain.PROVENANCE,
        ProjectIRChangeDomain.PROPERTIES,
    ):
        result = assess_project_query_block_ir_invalidation((domain,))
        assert result.overlay is ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
        assert result.verification.value == "rerun_required"
        assert result.invalidated == (
            tuple(ProjectIRQueryBlockAnalysisKind)
            if domain is ProjectIRChangeDomain.TOPOLOGY
            else ()
        )
        assert assess_project_query_block_ir_invalidation(
            (domain,), completed_semantic_root_changed=True
        ).invalidated == tuple(ProjectIRQueryBlockAnalysisKind)


@pytest.mark.parametrize(
    "mutation",
    ("foreign_scope", "gap", "slot", "copy_use", "detached", "accumulated", "partial"),
)
def test_join_scope_slot_use_accumulation_and_region_corruptions_are_independent(
    tmp_path: Path,
    mutation: str,
) -> None:
    _, _, bundle, _ = _fresh(tmp_path, mutation)
    snapshot = bundle.verification.root
    entry = _entry(snapshot, "multihop_join")
    prefix = entry.join_prefix
    assert prefix is not None
    first, second = prefix.joins
    if mutation in ("foreign_scope", "gap"):
        ref = first.node.ref
        object.__setattr__(
            first.node,
            "ref",
            ProjectIRPlanNodeRef(
                scope=ProjectIRSnapshotScope()
                if mutation == "foreign_scope"
                else ref.scope,
                position=ref.position
                if mutation == "foreign_scope"
                else ref.position + 1,
            ),
        )
    elif mutation == "slot":
        object.__setattr__(first.input_uses[0].slot, "input_ordinal", 1)
    elif mutation == "copy_use":
        object.__setattr__(first.inputs[0], "use", _unsafe(first.input_uses[0]))
    elif mutation == "detached":
        object.__setattr__(first.input_uses[0], "output", first.input_uses[1].output)
    elif mutation == "accumulated":
        object.__setattr__(second.input_uses[0], "output", first.input_uses[0].output)
    else:
        object.__setattr__(prefix, "joins", prefix.joins[:-1])
    assert not verify_project_query_block_ir(snapshot).verified


@pytest.mark.parametrize(
    "mutation",
    (
        "condition",
        "nulling",
        "nullability",
        "null_property",
        "keys",
        "fds",
        "value_class",
        "grain",
    ),
)
def test_join_condition_nulling_property_key_fd_and_grain_corruptions_are_independent(
    tmp_path: Path,
    mutation: str,
) -> None:
    _, _, bundle, _ = _fresh(tmp_path, mutation)
    snapshot = bundle.verification.root
    entry = _entry(snapshot, "aggregate_left_outputs")
    assert entry.join_prefix is not None
    join = entry.join_prefix.final_join
    properties = entry.join_properties[-1].relational
    if mutation == "condition":
        object.__setattr__(
            join, "condition", _join(snapshot, "multihop_join").condition
        )
    elif mutation in ("nulling", "nullability"):
        field = next(
            field for field in join.output.row_shape.fields if field.nulling_joins
        )
        if mutation == "nulling":
            object.__setattr__(field, "nulling_joins", ())
        else:
            object.__setattr__(
                field, "effective_nullability", ProjectRowFieldNullability.NON_NULL
            )
    elif mutation == "null_property":
        source = join.source
        other = _join(snapshot, "multihop_join").source
        assert isinstance(source, ProjectCurrentBinaryJoin)
        assert isinstance(other, ProjectCurrentBinaryJoin)
        object.__setattr__(
            source.properties, "null_extension", other.properties.null_extension
        )
    elif mutation == "keys":
        assert properties.keys
        object.__setattr__(properties, "keys", ())
    elif mutation == "fds":
        assert properties.fds
        object.__setattr__(properties, "fds", ())
    elif mutation == "value_class":
        first = properties.value_classes[0]
        object.__setattr__(
            first, "members", (_unsafe(first.members[0]), *first.members[1:])
        )
    else:
        assert properties.grain.active
        object.__setattr__(properties.grain, "active", ())
    assert not verify_project_query_block_ir(snapshot).verified


@pytest.mark.parametrize("mutation", ("removed", "duplicated", "index"))
def test_base_fact_catalog_corruptions_are_independent(
    tmp_path: Path, mutation: str
) -> None:
    _, completed, _, _ = _fresh(tmp_path, mutation)
    root = completed.verification.root
    assert root.facts
    if mutation == "removed":
        object.__setattr__(root, "facts", root.facts[:-1])
    elif mutation == "duplicated":
        object.__setattr__(root, "facts", (*root.facts, root.facts[0]))
    else:
        object.__setattr__(root, "facts_by_context", {})
    assert verification.ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG in _kinds(
        root
    )


def _pair_result(completed, owner_name="aggregate_pair_outputs"):
    matches = tuple(
        result
        for tail in completed.effective_outputs.current_tails
        for result in tail.window_set.aggregation_set.results
        if result.input_filter.entry.owner.definition.name == owner_name
    )
    assert len(matches) == 1
    result = matches[0]
    assert len(result.grain_linkages) == 2
    assert len(result.pair_linkages) == 1
    return result


@pytest.mark.parametrize(
    "mutation",
    (
        "introduction",
        "context_factors",
        "context_copy",
        "actual_missing",
        "actual_duplicate",
        "actual_copy",
        "authority_missing",
        "common_actual_missing",
        "common_missing",
        "candidate_missing",
        "candidate_winner",
        "candidate_copy",
        "pair_participant",
        "chasm_missing",
        "exposure_join",
        "exposure_factors",
        "risk",
    ),
)
def test_current_aggregate_identity_candidates_and_chasm_corruptions_are_independent(
    tmp_path: Path,
    mutation: str,
) -> None:
    _, completed, bundle, _ = _fresh(tmp_path, mutation)
    snapshot = bundle.verification.root
    owner_name = {
        "common_missing": "aggregate_pair_same_input",
        "candidate_missing": "aggregate_pair_keyed",
        "candidate_winner": "aggregate_pair_keyed",
        "candidate_copy": "aggregate_pair_keyed",
        "chasm_missing": "aggregate_pair_shared_inputs",
    }.get(mutation, "aggregate_pair_outputs")
    result = _pair_result(completed, owner_name)
    left, right = result.grain_linkages
    pair = result.pair_linkages[0]
    region = left.multifact_region
    common = pair.common_grain
    assert right.multifact_region is region
    assert region.actual_candidates
    if mutation == "introduction":
        first = left.aggregate.field_dependencies[0].field_semantics
        other = right.aggregate.field_dependencies[0].field_semantics
        assert first.introduction_use is not other.introduction_use
        object.__setattr__(
            first.joined_field, "introduction_use", other.introduction_use
        )
    elif mutation == "context_factors":
        assert left.contextual_grain.factors
        object.__setattr__(left.contextual_grain, "factors", ())
    elif mutation == "context_copy":
        object.__setattr__(
            pair.grain_comparison, "left", _unsafe(left.contextual_grain)
        )
    elif mutation == "actual_missing":
        object.__setattr__(region, "actual_candidates", region.actual_candidates[:-1])
    elif mutation == "actual_duplicate":
        object.__setattr__(
            region,
            "actual_candidates",
            (*region.actual_candidates, region.actual_candidates[0]),
        )
    elif mutation == "actual_copy":
        object.__setattr__(
            region,
            "actual_candidates",
            (_unsafe(region.actual_candidates[0]), *region.actual_candidates[1:]),
        )
    elif mutation == "authority_missing":
        candidate = region.actual_candidates[0]
        assert candidate.authorities
        object.__setattr__(candidate, "authorities", candidate.authorities[:-1])
    elif mutation == "common_actual_missing":
        assert common.actual_candidates
        object.__setattr__(common, "actual_candidates", common.actual_candidates[:-1])
    elif mutation == "common_missing":
        assert common.common_candidates
        object.__setattr__(common, "common_candidates", common.common_candidates[:-1])
    elif mutation == "candidate_missing":
        assert common.candidates
        object.__setattr__(common, "candidates", common.candidates[:-1])
    elif mutation == "candidate_winner":
        assert len(common.candidates) >= 2
        object.__setattr__(common, "candidates", common.candidates[:1])
        object.__setattr__(common, "status", ProjectCommonGrainStatus.UNIQUE)
    elif mutation == "candidate_copy":
        assert common.candidates
        candidate = common.candidates[0]
        object.__setattr__(candidate, "candidate", _unsafe(candidate.candidate))
    elif mutation == "pair_participant":
        object.__setattr__(pair, "right", left)
    elif mutation == "chasm_missing":
        assert pair.chasm_candidates
        object.__setattr__(pair, "chasm_candidates", pair.chasm_candidates[:-1])
    elif mutation in ("exposure_join", "exposure_factors"):
        exposures = (*left.multiplicity_exposures, *right.multiplicity_exposures)
        assert exposures
        exposure = exposures[0]
        if mutation == "exposure_join":
            other = next(
                join for join in region.region.joins if join is not exposure.join
            )
            object.__setattr__(exposure, "join", other)
        else:
            assert exposure.factor_additions
            object.__setattr__(exposure, "factor_additions", ())
    else:
        object.__setattr__(
            pair,
            "multiplicity_risks",
            (
                *pair.multiplicity_risks,
                ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
            ),
        )
    assert not verify_project_query_block_ir(snapshot).verified


def test_combined_cycle_is_invalid_and_invalid_result_cannot_form_bundle(
    tmp_path: Path,
) -> None:
    _, _, bundle, _ = _fresh(tmp_path, "cycle")
    snapshot = bundle.verification.root
    first = _join(snapshot, "multihop_join")
    second = _join(snapshot, "multihop_join", 1)
    object.__setattr__(first.input_uses[0], "output", second.output.occurrence)
    result = verify_project_query_block_ir(snapshot)
    assert not result.verified
    assert ProjectIRQueryBlockVerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE in (
        issue.kind for issue in result.issues
    )
    with pytest.raises(ValueError, match="Only VERIFIED"):
        build_project_query_block_ir_analysis_bundle(result)


def test_verifier_and_oracle_are_statically_separate_private_boundaries() -> None:
    verifier_source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    oracle_source = ORACLE_SOURCE.read_text(encoding="utf-8")
    current_verifier = (
        REPO_ROOT / "src/pietto/_project/project_query_block_ir_verification.py"
    ).read_text(encoding="utf-8")
    assert "project_bag_null_oracle" not in current_verifier
    assert "evaluate_project_bag_null" not in current_verifier
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
from _pietto_project_aggregate import _build
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir, build_project_query_block_ir_analysis_bundle,
    assess_project_query_block_ir_invalidation,
)
from pietto._project.project_ir_verification import ProjectIRChangeDomain
_, completed, initial, _ = _build(Path(sys.argv[1]))
snapshot = initial.verification.root
if sys.argv[2] == "reverse":
    invalidation = assess_project_query_block_ir_invalidation((ProjectIRChangeDomain.TOPOLOGY,))
    result = verify_project_query_block_ir(snapshot)
    bundle = build_project_query_block_ir_analysis_bundle(result)
else:
    result = verify_project_query_block_ir(snapshot)
    bundle = build_project_query_block_ir_analysis_bundle(result)
    invalidation = assess_project_query_block_ir_invalidation((ProjectIRChangeDomain.TOPOLOGY,))
regions = completed.effective_outputs.current_regions
joins = [join for region in regions for join in region.joins]
assert joins
nulls = [field for join in joins for field in join.output.row_shape.fields if field.nulling_joins]
assert nulls
pair_names = (
    "aggregate_pair_outputs", "aggregate_pair_same_input",
    "aggregate_pair_keyed", "aggregate_pair_shared_inputs",
)
pair_results = [result for tail in completed.effective_outputs.current_tails
                for result in tail.window_set.aggregation_set.results
                if result.input_filter.entry.owner.definition.name in pair_names]
assert tuple(result.input_filter.entry.owner.definition.name for result in pair_results) == pair_names
pairs = []
for pair_result in pair_results:
    assert len(pair_result.grain_linkages) == 2 and len(pair_result.pair_linkages) == 1
    pair = pair_result.pair_linkages[0]
    common = pair.common_grain
    assert common.actual_candidates
    index = pair.left.multifact_region.grain_index
    def factors(values):
        return [index.positions[value] for value in values]
    pairs.append({
        "owner": pair_result.input_filter.entry.owner.definition.name,
        "variant": type(pair_result).__name__,
        "contexts": [factors(link.contextual_grain.factors) for link in pair_result.grain_linkages],
        "actual": [[factors(candidate.factors.factors), [authority.kind.value for authority in candidate.authorities]] for candidate in common.actual_candidates],
        "common": [common.actual_candidates.index(candidate.candidate) for candidate in common.common_candidates],
        "retained": [common.common_candidates.index(candidate) for candidate in common.candidates],
        "chasm": [common.candidates.index(candidate) for candidate in pair.chasm_candidates],
        "status": common.status.value,
        "risks": [risk.value for risk in pair.multiplicity_risks],
    })
print(json.dumps({
    "status": result.status.value,
    "issues": [item.kind.value for item in result.issues],
    "topology": [item.ref.position for item in bundle.combined_topological_order],
    "reverse": [(item.output.ref.position, [use.ref.position for use in item.uses]) for item in bundle.combined_reverse_uses],
    "joins": [(join.node.ref.position, len(join.input_uses), len(join.output.row_shape.fields)) for join in joins],
    "nulls": [(field.effective_nullability.value, len(field.nulling_joins)) for field in nulls],
    "properties": [(len(region.final_properties.relational.keys), len(region.final_properties.relational.fds), len(region.final_properties.relational.grain.active)) for region in regions],
    "pairs": pairs,
    "invalidated": [item.value for item in invalidation.invalidated],
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
