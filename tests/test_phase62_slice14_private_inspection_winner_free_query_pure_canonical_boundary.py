from __future__ import annotations

import ast
from copy import copy
from dataclasses import replace
import os
from pathlib import Path
import subprocess
from typing import cast

import pytest

from pietto._project import project_phase62_inspection as inspection
from pietto._project import project_phase62_pure_boundary as pure
from pietto._project.project_multifact import ProjectAggregateFactJoinLocality
from pietto._project.project_phase62_verification import (
    ProjectPhase62AnalysisBundle,
    build_project_phase62_analysis_bundle,
    verify_project_phase62,
)
from test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment import (
    _build,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_SOURCE = REPO_ROOT / "src/pietto/_project/project_phase62_inspection.py"
PURE_SOURCE = REPO_ROOT / "src/pietto/_project/project_phase62_pure_boundary.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md"
)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> ProjectPhase62AnalysisBundle:
    root = _build(tmp_path_factory.mktemp("p62s14"))
    return build_project_phase62_analysis_bundle(verify_project_phase62(root))


@pytest.fixture(scope="module")
def product(
    bundle: ProjectPhase62AnalysisBundle,
) -> inspection.ProjectPhase62InspectionProduct:
    return inspection.build_project_phase62_inspection(bundle)


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _unsafe[Value](value: Value, **changes: object) -> Value:
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


def _replace_record(
    document: pure.ProjectPhase62PureDocument,
    position: int,
    record: pure.ProjectPhase62PureRecord,
) -> pure.ProjectPhase62PureDocument:
    return replace(
        document,
        records=(
            *document.records[:position],
            record,
            *document.records[position + 1 :],
        ),
    )


def _record_position(
    document: pure.ProjectPhase62PureDocument,
    kind: pure.ProjectPhase62RecordKind,
) -> int:
    return next(
        position
        for position, record in enumerate(document.records)
        if record.kind is kind
    )


def test_slice14_owners_are_private_pure_and_single_encoder() -> None:
    assert inspection.__all__ == ()
    assert pure.__all__ == ()
    pure_source = PURE_SOURCE.read_text(encoding="utf-8")
    inspection_source = INSPECTION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(pure_source)
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"__future__", "dataclasses", "enum", "heapq", "typing"}
    assert (
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_encode_document"
            for node in ast.walk(tree)
        )
        == 1
    )
    assert "project_bag_null_oracle" not in pure_source + inspection_source
    assert "import json" not in pure_source + inspection_source
    assert "deserialize" not in pure_source + inspection_source
    assert ".encode(" not in inspection_source
    assert pure.PROJECT_PHASE62_INSPECTION_FORMAT == "pietto.phase62-inspection.v1"


def test_verified_bundle_only_admission_and_exact_runtime_closure(
    bundle: ProjectPhase62AnalysisBundle,
    product: inspection.ProjectPhase62InspectionProduct,
) -> None:
    observed = product.inspection
    root = bundle.root
    assert observed.analysis_bundle is bundle
    assert observed.verification is bundle.verification
    assert observed.root is root
    assert observed.base_verification is bundle.verification.base_verification
    assert observed.combined_reverse_uses is bundle.combined_reverse_uses
    assert observed.combined_topological_order is bundle.combined_topological_order
    assert observed.nulling_provenance is bundle.nulling_provenance
    assert observed.fact_locality_index is bundle.fact_localities
    assert observed.multifact_alignment_index is bundle.multifact_alignments
    assert _same_objects(
        observed.relationship_subjects,
        root.join_regions.uses.relationships.subjects,
    )
    assert _same_objects(
        observed.relationship_directions, root.join_regions.uses.index.directions
    )
    assert _same_objects(observed.join_use_ledgers, root.join_regions.uses.ledgers)
    assert _same_objects(
        observed.join_output_properties, root.join_regions.properties.outputs
    )
    assert _same_objects(observed.aggregate_facts, root.facts)
    assert _same_objects(observed.home_localities, root.home_localities)
    assert _same_objects(observed.join_localities, root.join_localities)
    assert _same_objects(observed.alignments, root.alignments)
    assert _same_objects(observed.chasms, bundle.multifact_alignments.chasms)
    assert _same_objects(
        observed.non_concrete_multifact_regions, root.non_concrete_regions
    )
    assert observed.summary.relationship_count == len(observed.relationship_subjects)
    assert observed.summary.binary_join_count == len(observed.binary_joins)
    assert observed.summary.candidate_key_count == len(observed.candidate_keys)
    assert observed.summary.value_fd_count == len(observed.value_fds)
    assert observed.summary.aggregate_fact_count == len(observed.aggregate_facts)
    assert observed.summary.alignment_count == len(observed.alignments)
    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_phase62_inspection(root)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_phase62_inspection(  # type: ignore[arg-type]
            bundle.verification  # pyright: ignore[reportArgumentType]
        )


def test_complete_runtime_sections_retain_occurrences_not_winners(
    product: inspection.ProjectPhase62InspectionProduct,
) -> None:
    observed = product.inspection
    assert len(observed.relationship_directions) == 2 * len(
        observed.relationship_subjects
    )
    assert any(len(bucket) > 1 for bucket in observed.direct_candidate_buckets)
    assert all(
        _same_objects(condition.correspondences, retained)
        for condition, retained in zip(
            observed.relationship_conditions,
            (
                tuple(
                    item
                    for item in observed.correspondences
                    if item.identity.base_match is condition.identity
                )
                for condition in observed.relationship_conditions
            ),
            strict=True,
        )
    )
    assert all(
        _same_objects(
            use.path.steps,
            tuple(
                step
                for step in observed.path_steps
                if any(step is local for local in use.path.steps)
            ),
        )
        for use in observed.join_uses
        if use.path is not None
    )
    assert all(
        len(join.input_slots) == len(join.input_uses) == 2
        for join in observed.binary_joins
    )
    assert all(
        join.outer_join_barrier.value == "present"
        for join in observed.binary_joins
        if join.kind.value == "left"
    )
    assert all(
        output.fd_index.facts == output.fds
        for output in (
            *observed.base_relational_outputs,
            *observed.join_relational_outputs,
        )
    )
    assert all(
        locality.contextual_grain is retained
        for locality, retained in zip(
            observed.fact_localities, observed.contextual_grains, strict=True
        )
    )
    assert len(observed.aggregate_facts) > len(
        {fact.identity.aggregate_node for fact in observed.aggregate_facts}
    )
    ambiguous = tuple(
        result
        for result in observed.common_grain_results
        if result.status.value == "ambiguous"
    )
    assert ambiguous
    assert all(len(item.candidates) > 1 for item in ambiguous)
    assert all(
        alignment.structural.value
        and isinstance(alignment.multiplicity_risks, tuple)
        and isinstance(alignment.requirements, tuple)
        for alignment in observed.alignments
    )
    assert all(len(chasm.localities) >= 2 for chasm in observed.chasms)


def test_typed_queries_are_scope_closed_and_return_complete_buckets(
    product: inspection.ProjectPhase62InspectionProduct,
    tmp_path: Path,
) -> None:
    observed = product.inspection
    relationship = observed.relationship_subjects[0]
    assert inspection.query_project_phase62_relationships(
        observed, relationship.occurrence.identity
    ) == (relationship,)
    direction = observed.relationship_directions[0]
    assert inspection.query_project_phase62_directions(
        observed, direction.direction
    ) == (direction,)
    join_use = observed.join_uses[0]
    assert inspection.query_project_phase62_join_uses(observed, join_use.identity) == (
        join_use,
    )
    binary = observed.binary_joins[0]
    assert inspection.query_project_phase62_binary_joins(observed, binary.identity) == (
        binary,
    )
    assert inspection.query_project_phase62_nodes(observed, binary.node.ref) == (
        binary.node,
    )
    assert inspection.query_project_phase62_outputs(
        observed, binary.output.occurrence.ref
    ) == (binary.output.occurrence,)
    assert inspection.query_project_phase62_input_slots(
        observed, binary.input_slots[0].ref
    ) == (binary.input_slots[0],)
    assert inspection.query_project_phase62_uses(
        observed, binary.input_uses[0].ref
    ) == (binary.input_uses[0],)
    nulling = next(item for item in observed.nulling_provenance if item.nulling_joins)
    assert inspection.query_project_phase62_nulling(
        observed,
        nulling.coordinate.output,
        nulling.coordinate.field_position,
    ) == (nulling,)
    fact = observed.aggregate_facts[0]
    assert inspection.query_project_phase62_facts(observed, fact.identity) == (fact,)
    fact_localities = inspection.query_project_phase62_fact_localities(
        observed, fact.identity
    )
    assert fact_localities == next(
        entry.localities for entry in observed.fact_locality_index if entry.fact is fact
    )
    locality = next(
        item
        for item in observed.join_localities
        if inspection.query_project_phase62_alignments_involving(observed, item)
    )
    involving = inspection.query_project_phase62_alignments_involving(
        observed, locality
    )
    assert all(item.left is locality or item.right is locality for item in involving)
    pair = involving[0]
    assert inspection.query_project_phase62_alignment_bucket(
        observed, pair.left, pair.right
    ) == (pair,)
    assert inspection.query_project_phase62_common_grains(observed, pair) == (
        pair.common_grain,
    )
    chasm_locality = observed.chasms[0].localities[0]
    assert observed.chasms[0] in inspection.query_project_phase62_chasms_containing(
        observed, chasm_locality
    )
    assert inspection.query_project_phase62_non_concrete_join_uses(observed)
    assert inspection.query_project_phase62_non_concrete_join_regions(observed)
    assert inspection.query_project_phase62_non_concrete_multifact_regions(observed)

    fresh_root = _build(tmp_path / "fresh")
    fresh = inspection.build_project_phase62_inspection(
        build_project_phase62_analysis_bundle(verify_project_phase62(fresh_root))
    )
    assert fresh.canonical_bytes == product.canonical_bytes
    assert fresh.inspection.summary.scope is not observed.summary.scope
    with pytest.raises(ValueError, match="snapshot scope"):
        inspection.query_project_phase62_nodes(
            fresh.inspection,
            observed.combined_topological_order[0].ref,
        )
    with pytest.raises(ValueError, match="snapshot scope"):
        inspection.query_project_phase62_facts(
            fresh.inspection, observed.aggregate_facts[0].identity
        )


def test_portable_document_is_accepted_and_shifted_coordinates_change_bytes(
    product: inspection.ProjectPhase62InspectionProduct,
) -> None:
    outcome = pure.evaluate_project_phase62_document(product.document)
    assert outcome.status is pure.ProjectPhase62PureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes
    header = product.document.records[0]
    assert tuple(field.value.enumeration for field in header.fields[1:]) == (
        "verified",
        "verified",
    )
    direction = next(
        record
        for record in product.document.records
        if record.kind is pure.ProjectPhase62RecordKind.RELATIONSHIP_DIRECTION
    )
    runtime_direction = product.inspection.relationship_directions[0].direction
    assert tuple(field.value.text for field in direction.fields[4:]) == (
        runtime_direction.source.authored_role,
        runtime_direction.target.authored_role,
        runtime_direction.source.authored_relation_spelling,
        runtime_direction.target.authored_relation_spelling,
    )
    non_concrete = tuple(
        record
        for record in product.document.records
        if record.kind is pure.ProjectPhase62RecordKind.NON_CONCRETE
    )
    assert all(record.fields[3].value.enumerations for record in non_concrete)
    runtime_domains = {
        pure.ProjectPhase62PortableRefDomain.PLAN_NODE,
        pure.ProjectPhase62PortableRefDomain.OUTPUT_VALUE,
        pure.ProjectPhase62PortableRefDomain.INPUT_SLOT,
        pure.ProjectPhase62PortableRefDomain.USE,
    }

    def shift(ref: pure.ProjectPhase62PortableRef) -> pure.ProjectPhase62PortableRef:
        return (
            replace(ref, position=ref.position + 7)
            if ref.domain in runtime_domains
            else ref
        )

    shifted_records = tuple(
        replace(
            record,
            fields=tuple(
                replace(
                    field,
                    value=(
                        replace(
                            field.value,
                            ref=shift(
                                cast(
                                    pure.ProjectPhase62PortableRef,
                                    field.value.ref,
                                )
                            ),
                        )
                        if field.value.tag is pure.ProjectPhase62PureTag.REF
                        else (
                            replace(
                                field.value,
                                refs=tuple(shift(item) for item in field.value.refs),
                            )
                            if field.value.tag is pure.ProjectPhase62PureTag.REFS
                            else field.value
                        )
                    ),
                )
                for field in record.fields
            ),
        )
        for record in product.document.records
    )
    shifted = replace(product.document, records=shifted_records)
    shifted_outcome = pure.evaluate_project_phase62_document(shifted)
    assert shifted_outcome.status is pure.ProjectPhase62PureStatus.OK
    assert shifted_outcome.canonical_bytes != product.canonical_bytes


def test_pure_evaluator_normalizes_malformed_documents_without_text_echo(
    product: inspection.ProjectPhase62InspectionProduct,
) -> None:
    document = product.document
    assert pure.evaluate_project_phase62_document(object()).status is (
        pure.ProjectPhase62PureStatus.INVALID_DOCUMENT
    )
    unknown = replace(document, format_marker="untrusted\ntext")
    result = pure.evaluate_project_phase62_document(unknown)
    assert result.status is pure.ProjectPhase62PureStatus.UNKNOWN_FORMAT
    assert result.canonical_bytes is None
    assert not hasattr(result, "message")
    missing_header = replace(document, records=document.records[1:])
    assert pure.evaluate_project_phase62_document(missing_header).status is (
        pure.ProjectPhase62PureStatus.INVALID_HEADER
    )
    swapped = replace(
        document,
        records=(
            document.records[0],
            document.records[2],
            document.records[1],
            *document.records[3:],
        ),
    )
    assert pure.evaluate_project_phase62_document(swapped).status is (
        pure.ProjectPhase62PureStatus.INVALID_SECTION_ORDER
    )

    binary_position = _record_position(
        document, pure.ProjectPhase62RecordKind.BINARY_JOIN
    )
    binary = document.records[binary_position]
    slot_position = next(
        position for position, field in enumerate(binary.fields) if field.key == "slots"
    )
    malformed_binary = replace(
        binary,
        fields=(
            *binary.fields[:slot_position],
            replace(
                binary.fields[slot_position],
                value=pure.project_phase62_pure_refs(
                    (binary.fields[slot_position].value.refs[0],)
                ),
            ),
            *binary.fields[slot_position + 1 :],
        ),
    )
    assert (
        pure.evaluate_project_phase62_document(
            _replace_record(document, binary_position, malformed_binary)
        ).status
        is pure.ProjectPhase62PureStatus.INVALID_JOIN
    )

    use_position = _record_position(document, pure.ProjectPhase62RecordKind.PROJECT_USE)
    use = document.records[use_position]
    output_position = next(
        position for position, field in enumerate(use.fields) if field.key == "output"
    )
    dangling = replace(
        use,
        fields=(
            *use.fields[:output_position],
            replace(
                use.fields[output_position],
                value=pure.project_phase62_pure_ref(
                    pure.ProjectPhase62PortableRef(
                        domain=pure.ProjectPhase62PortableRefDomain.OUTPUT_VALUE,
                        position=10**6,
                    )
                ),
            ),
            *use.fields[output_position + 1 :],
        ),
    )
    assert (
        pure.evaluate_project_phase62_document(
            _replace_record(document, use_position, dangling)
        ).status
        is pure.ProjectPhase62PureStatus.DANGLING_REF
    )

    guarantee_position = _record_position(
        document, pure.ProjectPhase62RecordKind.MATCH_GUARANTEE
    )
    guarantee = document.records[guarantee_position]
    minimum_position = next(
        position
        for position, field in enumerate(guarantee.fields)
        if field.key == "minimum"
    )
    invalid_value = _unsafe(
        guarantee.fields[minimum_position].value,
        enumeration="untrusted\ntext",
    )
    invalid_guarantee = replace(
        guarantee,
        fields=(
            *guarantee.fields[:minimum_position],
            replace(guarantee.fields[minimum_position], value=invalid_value),
            *guarantee.fields[minimum_position + 1 :],
        ),
    )
    invalid_outcome = pure.evaluate_project_phase62_document(
        _replace_record(document, guarantee_position, invalid_guarantee)
    )
    assert invalid_outcome.status is pure.ProjectPhase62PureStatus.INVALID_VALUE
    assert invalid_outcome.record_position == guarantee_position
    assert invalid_outcome.field_position == minimum_position


def test_projection_is_zero_mutation_and_repeatable(
    bundle: ProjectPhase62AnalysisBundle,
    product: inspection.ProjectPhase62InspectionProduct,
) -> None:
    root = bundle.root
    before = (
        root.join_regions.starting_allocation,
        root.join_regions.ending_allocation,
        tuple(join.node.ref for join in product.inspection.binary_joins),
        tuple(fact.identity for fact in root.facts),
        bundle.verification,
        bundle.combined_reverse_uses,
        bundle.combined_topological_order,
        bundle.nulling_provenance,
        bundle.fact_localities,
        bundle.multifact_alignments,
    )
    repeated = inspection.build_project_phase62_inspection(bundle)
    after = (
        root.join_regions.starting_allocation,
        root.join_regions.ending_allocation,
        tuple(join.node.ref for join in repeated.inspection.binary_joins),
        tuple(fact.identity for fact in root.facts),
        bundle.verification,
        bundle.combined_reverse_uses,
        bundle.combined_topological_order,
        bundle.nulling_provenance,
        bundle.fact_localities,
        bundle.multifact_alignments,
    )
    assert all(
        actual is retained
        for actual, retained in zip(after[:2], before[:2], strict=True)
    )
    assert _same_objects(after[2], before[2])
    assert _same_objects(after[3], before[3])
    assert all(
        actual is retained
        for actual, retained in zip(after[4:], before[4:], strict=True)
    )
    assert repeated.document == product.document
    assert repeated.canonical_bytes == product.canonical_bytes


def test_hash_seed_and_unrelated_cwd_do_not_change_canonical_bytes(
    tmp_path: Path,
) -> None:
    python = REPO_ROOT / ".venv/bin/python"
    script = """
from pathlib import Path
import sys
from test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment import _build
from pietto._project.project_phase62_inspection import build_project_phase62_inspection
from pietto._project.project_phase62_verification import build_project_phase62_analysis_bundle, verify_project_phase62
path = Path(sys.argv[1])
path.mkdir(parents=True)
root = _build(path)
product = build_project_phase62_inspection(build_project_phase62_analysis_bundle(verify_project_phase62(root)))
sys.stdout.buffer.write(product.canonical_bytes)
"""
    outputs: list[bytes] = []
    for seed, name in (("1", "left"), ("987654", "right")):
        cwd = tmp_path / name
        cwd.mkdir()
        env = {
            **os.environ,
            "PYTHONHASHSEED": seed,
            "PYTHONPATH": os.pathsep.join(
                (str(REPO_ROOT / "src"), str(REPO_ROOT / "tests"))
            ),
        }
        completed = subprocess.run(
            [str(python), "-c", script, str(cwd / "project")],
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
        )
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]
    assert outputs[0].startswith(b"header\tformat=t:pietto.phase62-inspection.v1\t")


def test_slice14_spec_exists_and_freezes_private_boundaries() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "pietto.phase62-inspection.v1",
        "ProjectPhase62AnalysisBundle",
        "winner-free",
        "canonical bytes are not identity",
        "BAG/NULL oracle",
        "Slice 15",
    ):
        assert phrase in text
    assert ProjectAggregateFactJoinLocality is not object
