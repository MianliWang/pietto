"""Query-block IR of Collect reads, each one verified expression block use, and
of Unnest occurrences, each one verified zero-input entry its JOIN reads."""

from __future__ import annotations

from copy import copy
from typing import cast

import pytest

from pietto._project.project_joined_row_filter import ProjectJoinedRowMultiplicity
from pietto._project.project_query_block_ir import (
    ProjectIRCaptureStage,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedValuesOutput,
    build_project_query_block_ir,
    capture_read,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
    serialize_project_query_block_ir_inspection,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationIssueKind as Kind,
    verify_project_query_block_ir,
)
from pietto._project.project_unnest import ProjectUnnestRelation
from pietto.ast_nodes import CollectRelationExpr

from _pietto_plan_nested import (
    SHAPES,
    UNNEST_SHAPES,
    imported_sources,
    nested_roots,
    sources,
)

pytestmark = pytest.mark.ci_workload("general-runtime")


def _graft(value, **changes):
    changed = copy(value)
    for name, item in changes.items():
        object.__setattr__(changed, name, item)
    return changed


def _collect_edges(bundle):
    return tuple(
        edge
        for edge in bundle.root.expression_uses
        if type(edge.use.expression) is CollectRelationExpr
    )


@pytest.mark.parametrize("shape", (*SHAPES, "imported"))
def test_every_collect_read_is_one_verified_whole_block_read(tmp_path, shape):
    files = imported_sources() if shape == "imported" else sources(shape)
    _, bundle, _ = nested_roots(tmp_path / "p", files)

    edges = _collect_edges(bundle)
    expected = {"parallel": 2}.get(shape, 1)
    assert len(edges) == expected
    for edge in edges:
        # A Collect read names no column: it reads whole rows of its let.
        assert edge.column is None
        assert edge.producer.owner is edge.use.target
        assert edge.use.target.let_position is not None
        assert edge.output is edge.producer.output


@pytest.mark.parametrize(
    ("shape", "stages"),
    [
        ("top_k", (ProjectIRCaptureStage.INPUT,)),
        ("staged_capture", (ProjectIRCaptureStage.INPUT,)),
        ("joined_capture", (ProjectIRCaptureStage.JOINED,) * 2),
    ],
)
def test_a_captured_collect_read_is_the_checkpoint_of_each_capture_line(
    tmp_path, shape, stages
):
    _, bundle, _ = nested_roots(tmp_path / "p", sources(shape))

    (edge,) = _collect_edges(bundle)
    captures = bundle.root.capture_uses
    assert tuple(c.checkpoint.stage for c in captures) == stages
    for capture in captures:
        assert capture.checkpoint.read is edge
        assert capture_read(bundle.root.expression_uses, capture.capture) is edge


def test_the_ir_rejects_a_deleted_forged_or_swapped_collect_edge(tmp_path):
    completed, bundle, _ = nested_roots(tmp_path / "p", sources("parallel"))
    snapshot = build_project_query_block_ir(completed)
    assert verify_project_query_block_ir(snapshot).verified
    first, second = snapshot.expression_uses
    for edges in (
        (second,),
        (second, first),
        (_graft(first, column=0), second),
    ):
        issues = verify_project_query_block_ir(
            _graft(snapshot, expression_uses=edges)
        ).issues
        assert Kind.EXPRESSION_BLOCK_USE in {issue.kind for issue in issues}


@pytest.mark.parametrize("shape", ("closed", "top_k"))
def test_the_private_inspection_document_encodes_a_collect_output_as_a_field(
    tmp_path, shape
):
    _, bundle, _ = nested_roots(tmp_path / "p", sources(shape))

    documents = {
        serialize_project_query_block_ir_inspection(
            build_project_query_block_ir_inspection(bundle).inspection
        )
        for _ in range(2)
    }
    (data,) = documents
    # The document encodes no type: the nested output is one more named field.
    name = b"name=t:nested\t" if shape == "closed" else b"name=t:recent_orders\t"
    assert name in data
    assert b"nested relation" not in data and b"nested_relation" not in data


def _unnest_entries(root) -> tuple[ProjectIRCompletedValuesOutput, ...]:
    entries = tuple(e for e in root.entries if e.owner.unnest is not None)
    assert all(type(e) is ProjectIRCompletedValuesOutput for e in entries)
    return cast(tuple[ProjectIRCompletedValuesOutput, ...], entries)


def _unnest_relation(entry: ProjectIRCompletedValuesOutput) -> ProjectUnnestRelation:
    relation = entry.semantic_entry.root
    assert type(relation) is ProjectUnnestRelation
    return relation


@pytest.mark.parametrize("shape", UNNEST_SHAPES)
def test_each_unnest_is_one_verified_entry_that_its_join_reads(tmp_path, shape):
    completed, bundle, _ = nested_roots(tmp_path / "p", sources(shape))

    entries = _unnest_entries(bundle.root)
    assert len(entries) == (2 if shape == "unnest_two_bodies" else 1)
    facts = completed.completion.plan.semantic_facts
    for entry in entries:
        # Zero inputs, the typed element fields of its one input fact, and no
        # key, dependency, order or bound (D-S05-3).
        (owned,) = facts.find_owner(entry.owner)
        fact = owned.unnest_occurrence
        assert fact is not None and fact.nested_type is not None
        assert _unnest_relation(entry).fact is fact
        assert [f.evidence for f in entry.active_output.row_shape.fields] == [
            element.field for element in fact.nested_type.element_fields
        ]
        properties = entry.active_properties
        assert properties.multiplicity is ProjectJoinedRowMultiplicity.BAG
        assert properties.relational.keys == () == properties.relational.fds
        assert properties.ordering is None and properties.cardinality is None
        # Exactly one JOIN input reads it, as its right input.
        reads = [
            (join, ordinal)
            for owner in bundle.root.entries
            if type(owner) is ProjectIRCompletedQueryBlockOutput
            and owner.join_prefix is not None
            for join in owner.join_prefix.joins
            for ordinal, image in enumerate(join.inputs)
            if image.producer is entry.owner
        ]
        assert [ordinal for _, ordinal in reads] == [1]


def test_the_ir_rejects_an_unnest_entry_that_is_not_its_fact_s(tmp_path):
    completed, bundle, _ = nested_roots(tmp_path / "p", sources("unnest_cross"))
    snapshot = build_project_query_block_ir(completed)
    assert verify_project_query_block_ir(snapshot).verified
    (entry,) = _unnest_entries(snapshot)
    relation = _unnest_relation(entry)
    fact = relation.fact
    # An equal copy is not the semantic root's own fact.
    forged = copy(fact)
    object.__setattr__(relation, "fact", forged)
    try:
        issues = verify_project_query_block_ir(snapshot).issues
        assert Kind.SEMANTIC_EVIDENCE in {issue.kind for issue in issues}
    finally:
        object.__setattr__(relation, "fact", fact)
    assert verify_project_query_block_ir(snapshot).verified


@pytest.mark.parametrize("shape", ("unnest_captured_exists", "unnest_beside_series"))
def test_an_unnest_beside_a_capture_or_table_function_keeps_its_owner(tmp_path, shape):
    completed, bundle, _ = nested_roots(tmp_path / "p", sources(shape))

    # The capture's outer is the declaration, never its Unnest occurrence.
    for capture in bundle.root.capture_uses:
        assert capture.capture.outer.unnest is None
        assert capture.capture.outer.let_position is None
    (entry,) = _unnest_entries(bundle.root)
    owners = [e.owner for e in bundle.root.entries]
    same_body = [
        o
        for o in owners
        if (o.module_position, o.declaration_position)
        == (entry.owner.module_position, entry.owner.declaration_position)
    ]
    # The declaration, its Unnest and its let or table function: no winner.
    assert len(same_body) == 3
    assert len({id(o) for o in same_body}) == 3
