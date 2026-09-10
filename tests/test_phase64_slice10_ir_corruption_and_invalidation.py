"""Independent corruption checks over real immutable combined IR roots."""

from copy import copy
from pathlib import Path

import pytest

from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir,
    build_project_query_block_ir_analysis_bundle,
    assess_project_query_block_ir_invalidation,
    ProjectIRQueryBlockOverlayRequirement,
    ProjectIRQueryBlockAnalysisKind,
)
from pietto._project.project_ir_verification import ProjectIRChangeDomain
from pietto._project.project_ir import ProjectIRStageFieldAnchor
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)
from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
    _source as set_source,
)


def _unsafe(value, **changes):
    changed = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(changed, name, replacement)
    return changed


def test_swapped_same_schema_active_producer_is_not_a_valid_input_image(
    tmp_path: Path,
) -> None:
    root = build_project_query_block_ir(_completed(tmp_path, _source("true")))
    entry = next(
        entry for entry in root.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    joined = entry.join_prefix.final_join
    left, right = joined.inputs
    assert left.producer is not None and right.producer is not None
    # Mutate only newly allocated IR objects; semantic producer witnesses remain exact.
    object.__setattr__(right.use, "output", left.use.output)
    object.__setattr__(right, "producer", left.producer)
    assert not verify_project_query_block_ir(root).verified


def test_stage_anchor_cannot_replace_a_canonical_join_producer_anchor(
    tmp_path: Path,
) -> None:
    root = build_project_query_block_ir(_completed(tmp_path, _source("true")))
    assert verify_project_query_block_ir(root).verified
    entry = next(
        entry for entry in root.entries if entry.owner.definition.name == "result"
    )
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    assert entry.join_prefix is not None
    source = entry.join_prefix.final_join.inputs[0].source_properties.output
    object.__setattr__(
        source.occurrence,
        "anchor",
        ProjectIRStageFieldAnchor(
            producer=source.occurrence.producer, field_position=0
        ),
    )
    assert not verify_project_query_block_ir(root).verified


def test_coherent_loss_of_grain_images_is_rejected_against_semantic_authority(
    tmp_path: Path,
) -> None:
    root = build_project_query_block_ir(_completed(tmp_path, _source("true")))
    entry = next(
        entry for entry in root.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    assert entry.source_properties.grain.active
    for properties in (*entry.join_properties, *entry.row_properties):
        object.__setattr__(properties.relational.grain, "active", ())
    assert not verify_project_query_block_ir(root).verified


@pytest.mark.parametrize("mutation", ("missing", "extra", "reordered", "foreign"))
def test_set_operand_occurrences_cannot_be_dropped_duplicated_or_grafted(
    tmp_path: Path, mutation: str
) -> None:
    root = build_project_query_block_ir(
        _completed(tmp_path / "local", set_source(operands=("lhs", "rhs", "lhs")))
    )
    entry = next(
        entry
        for entry in root.entries
        if isinstance(entry, ProjectIRCompletedSetOperationOutput)
    )
    operands = entry.operands
    if mutation == "missing":
        changed = operands[:-1]
    elif mutation == "extra":
        changed = (*operands, operands[0])
    elif mutation == "reordered":
        changed = tuple(reversed(operands))
    else:
        other = build_project_query_block_ir(
            _completed(tmp_path / "other", set_source(operands=("lhs", "rhs", "lhs")))
        )
        foreign = next(
            entry
            for entry in other.entries
            if isinstance(entry, ProjectIRCompletedSetOperationOutput)
        )
        changed = (foreign.operands[0], *operands[1:])
    object.__setattr__(entry, "operands", changed)
    assert not verify_project_query_block_ir(root).verified


@pytest.mark.parametrize("mutation", ("missing", "extra", "foreign_proof", "scope"))
def test_single_match_obligations_and_proofs_cannot_be_replaced(
    tmp_path: Path, mutation: str
) -> None:
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _asymmetric_source,
        _request,
    )

    original = _completed(tmp_path, _asymmetric_source(target_unique=True))
    completed = with_project_single_match_requests(original, (_request(original),))
    root = build_project_query_block_ir(completed)
    retained = root.requirements[0]
    if mutation == "missing":
        object.__setattr__(root, "requirements", ())
    elif mutation == "extra":
        object.__setattr__(root, "requirements", (retained, retained))
    elif mutation == "foreign_proof":
        proof = retained.proofs[0]
        object.__setattr__(proof, "source", _unsafe(proof.source))
    else:
        object.__setattr__(retained, "boundaries", ())
    assert not verify_project_query_block_ir(root).verified


@pytest.mark.parametrize(
    "domain",
    (
        ProjectIRChangeDomain.TOPOLOGY,
        ProjectIRChangeDomain.PROVENANCE,
        ProjectIRChangeDomain.PROPERTIES,
    ),
)
def test_semantic_evidence_changes_require_rebuild_and_fresh_verification(
    domain,
) -> None:
    result = assess_project_query_block_ir_invalidation((domain,))
    assert result.overlay is ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
    assert result.verification.value == "rerun_required"
    assert result.invalidated == (
        tuple(ProjectIRQueryBlockAnalysisKind)
        if domain is ProjectIRChangeDomain.TOPOLOGY
        else ()
    )
    changed_root = assess_project_query_block_ir_invalidation(
        (domain,), completed_semantic_root_changed=True
    )
    assert changed_root.invalidated == tuple(ProjectIRQueryBlockAnalysisKind)


def test_all_except_membership_and_repeated_uses_reach_the_consumer(
    tmp_path: Path,
) -> None:
    root = build_project_query_block_ir(
        _completed(
            tmp_path, set_source("except", "all", operands=("lhs", "rhs", "rhs"))
        )
    )
    entry = next(
        entry
        for entry in root.entries
        if isinstance(entry, ProjectIRCompletedSetOperationOutput)
    )
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(root)
    )
    right = entry.operands[1].producer.active_output.occurrence
    uses = next(
        item.uses for item in bundle.combined_reverse_uses if item.output is right
    )
    assert sum(use is entry.uses[1] or use is entry.uses[2] for use in uses) == 2
    reachable = next(
        item.reachable
        for item in bundle.combined_reachability
        if item.source is right.producer
    )
    assert any(node is entry.operator.node for node in reachable)


@pytest.mark.parametrize(
    "member", ("condition", "source_properties", "input_properties", "producer")
)
def test_historical_match_views_cannot_graft_evidence(
    tmp_path: Path, member: str
) -> None:
    root = build_project_query_block_ir(_completed(tmp_path, _source(None)))
    assert verify_project_query_block_ir(root).verified
    assert root.retained_joins
    joined = root.retained_joins[0]
    if member in {"condition", "source_properties"}:
        original = (
            joined.condition if member == "condition" else joined.source_properties
        )
        object.__setattr__(joined, member, _unsafe(original))
    elif member == "input_properties":
        object.__setattr__(
            joined.inputs[0],
            "source_properties",
            _unsafe(joined.inputs[0].source_properties),
        )
    else:
        object.__setattr__(joined.inputs[0], "producer", None)
    assert not verify_project_query_block_ir(root).verified


@pytest.mark.parametrize("variant", ("one", "zero", "two", "absent"))
def test_historical_view_requires_exact_condition_singleton(
    tmp_path: Path, variant: str
) -> None:
    root = build_project_query_block_ir(_completed(tmp_path, _source(None)))
    assert verify_project_query_block_ir(root).verified
    assert root.retained_joins
    operative = root.completed.effective_outputs.operative_conditions
    assert operative is not None
    if variant == "zero":
        object.__setattr__(operative, "entries", ())
    elif variant == "two":
        object.__setattr__(
            operative, "entries", (*operative.entries, *operative.entries)
        )
    elif variant == "absent":
        object.__setattr__(
            root.completed.effective_outputs, "operative_conditions", None
        )
    result = verify_project_query_block_ir(root)
    assert result.verified == (variant == "one")
