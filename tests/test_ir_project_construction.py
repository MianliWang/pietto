from __future__ import annotations

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
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_properties as properties
from pietto._project import check as project_check
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-canonical-single-relation-project-ir-construction-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Exact Builder Inputs And Allocation",
    "Canonical Operator Row And Output Construction",
    "Intra-relation Flow And Slice 6 Boundary",
    "Property Transfer Effect And Estimate Construction",
    "Concrete And Non-concrete Results",
    "Determinism Canonicality And Privacy",
    "Focused Assurance",
    "Integration Boundaries And Non-goals",
    "Slice 6 Handoff",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    amount: Int nullable
    category: Text nullable
source rows: Row is postgres.table("rows")
query simple:
    from rows
    select:
        id
        amount
query filtered:
    from rows
    where id > 0
    select:
        id
        amount
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
query satisfying:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
    satisfying:
        total > 0
query windowed:
    from rows
    select:
        id
        ranking = row_number() window:
            order by:
                id
query ordered:
    from rows
    select:
        id
        amount
    order by:
        id desc
query limited:
    from rows
    select:
        id
        amount
    limit 3
query full:
    from rows
    let:
        floor = 0
    where id > floor
    group by:
        category
    select:
        category
        total = sum(amount)
        ranking = row_number() window child
    window child = base
    window base:
        partition by:
            category
        order by:
            total desc
    satisfying:
        total > 0
    order by:
        ranking
    limit 5
query same_a:
    from rows
    select:
        id
query same_b:
    from rows
    select:
        id
query consumer:
    from simple
    select:
        id
        amount
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


def _fact(
    semantic: ProjectSemanticResult,
    name: str,
) -> ProjectModuleRelationSemanticFacts:
    fact_set = semantic.module_semantic_facts
    assert fact_set is not None
    matches = tuple(
        fact
        for environment in fact_set.environments
        for fact in environment.relation_facts
        if fact.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _build(
    semantic: ProjectSemanticResult,
    name: str,
    allocation: construction.ProjectIRAllocationState | None = None,
) -> construction.ProjectIRSingleRelationFragment:
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    return construction.build_project_ir_single_relation_fragment(
        semantic=_fact(semantic, name),
        attribution=attribution,
        allocation=(
            construction.ProjectIRAllocationState(
                scope=project_ir.ProjectIRSnapshotScope()
            )
            if allocation is None
            else allocation
        ),
    )


def _concrete(
    fragment: construction.ProjectIRSingleRelationFragment,
) -> construction.ProjectIRConcreteSingleRelationFragment:
    assert type(fragment) is construction.ProjectIRConcreteSingleRelationFragment
    return fragment


def test_controlling_contract_locks_builder_authority_scope_and_handoff() -> None:
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
        "1ac00344554967ba30f2e3bdff553ec63c2a4c12",
        "c73d5c93c2c037f8258beab4ba5587e4873c3319",
        "33335654061",
        "A3/M5/D0",
        "same exact semantic/attribution authority + same explicit starting allocator",
        "ProjectIRAllocationState",
        "ProjectIRConcreteSingleRelationFragment",
        "ProjectIRNonConcreteSingleRelationFragment",
        "final semantic field identity != intermediate plan-local field/value identity",
        "intra-relation operator flow != future cross-relation semantic dependency edge",
        "Add Phase 61 single-relation Project IR builder",
        "PASS — PHASE61_SLICE5_CANONICAL_SINGLE_RELATION_CONSTRUCTION_FROM_"
        "PROJECT_SEMANTIC_FACTS_END_TO_END",
        "Phase 61 Slice 6 — Cross-Module Relation Composition And Acyclic Project Plan DAG",
    ):
        assert evidence in normalized


def test_allocation_and_result_carriers_are_private_frozen_and_source_is_one_leaf(
    tmp_path: Path,
) -> None:
    carriers = (
        construction.ProjectIRAllocationState,
        construction.ProjectIRConcreteSingleRelationFragment,
        construction.ProjectIRNonConcreteSingleRelationFragment,
    )
    for carrier in carriers:
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    assert construction.__all__ == ()
    scope = project_ir.ProjectIRSnapshotScope()
    allocation = construction.ProjectIRAllocationState(scope=scope)
    with pytest.raises(FrozenInstanceError):
        allocation.next_plan_node_position = 1  # type: ignore[misc]

    semantic = _semantic_project(tmp_path)
    source = _concrete(_build(semantic, "rows", allocation))
    assert tuple(item.kind for item in source.logical_stage.operators) == (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
    )
    assert len(source.structural_stage.nodes) == 1
    assert len(source.logical_stage.outputs) == 1
    assert source.structural_stage.input_slots == ()
    assert source.structural_stage.uses == ()
    assert source.final_scalar_outputs == ()
    assert source.root is source.logical_stage.operators[0].node
    assert source.root_relation_output is source.logical_stage.outputs[0]
    assert type(source.root_relation_output.row_shape) is properties.ProjectIRRowShape
    assert tuple(
        property_.property_slot for property_ in source.property_stage.provided
    ) == (
        properties.ProjectIRProvidedPropertySlot.OUTPUT_SHAPE,
        properties.ProjectIRProvidedPropertySlot.MULTIPLICITY,
        properties.ProjectIRProvidedPropertySlot.FREE_BINDINGS,
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("simple", ("relation_input", "final_projection")),
        ("filtered", ("relation_input", "row_filter", "final_projection")),
        (
            "aggregate_only",
            ("relation_input", "group_aggregate", "final_projection"),
        ),
        ("grouped", ("relation_input", "group_aggregate", "final_projection")),
        (
            "satisfying",
            (
                "relation_input",
                "group_aggregate",
                "result_filter",
                "final_projection",
            ),
        ),
        (
            "windowed",
            ("relation_input", "window_evaluation", "final_projection"),
        ),
        ("ordered", ("relation_input", "final_projection", "relation_ordering")),
        ("limited", ("relation_input", "final_projection", "limit")),
        (
            "full",
            tuple(kind.value for kind in operators.ProjectIRLogicalOperatorKind),
        ),
    ),
)
def test_builder_derives_exact_operator_rows_and_flow(
    tmp_path: Path,
    name: str,
    expected: tuple[str, ...],
) -> None:
    fragment = _concrete(_build(_semantic_project(tmp_path), name))
    assert (
        tuple(item.kind.value for item in fragment.logical_stage.operators) == expected
    )
    row_outputs = tuple(
        output
        for output in fragment.logical_stage.outputs
        if type(output) is properties.ProjectIRRelationRowOutput
    )
    assert len(row_outputs) == len(expected)
    flow_uses = tuple(
        use
        for use in fragment.structural_stage.uses
        if type(use) is project_ir.ProjectIROperatorFlowUseOccurrence
    )
    assert len(flow_uses) == len(expected) - 1
    assert not any(type(use) is project_ir.ProjectIRUseOccurrence for use in flow_uses)
    for position, use in enumerate(flow_uses):
        assert use.ref.position == position
        assert use.slot.ref.position == position
        assert use.output is row_outputs[position].occurrence
        assert use.slot.consumer is fragment.logical_stage.operators[position + 1].node
        assert use.slot.input_ordinal == 0
    assert fragment.root is fragment.logical_stage.operators[-1].node
    assert fragment.root_relation_output is row_outputs[-1]
    if name in {"ordered", "limited", "full"}:
        assert (
            type(fragment.root_relation_output.row_shape)
            is properties.ProjectIRRowShape
        )

    if name == "full":
        definition = fragment.semantic_facts.owner.definition
        assert definition.let_clause is not None  # type: ignore[union-attr]
        assert definition.named_windows  # type: ignore[union-attr]
        assert not any(
            member in operators.ProjectIRLogicalOperatorKind.__members__
            for member in ("LET", "NAMED_WINDOW", "WINDOW_FRAME")
        )
        assert tuple(type(output.row_shape) for output in row_outputs) == (
            properties.ProjectIRStageRowShape,
            properties.ProjectIRStageRowShape,
            properties.ProjectIRStageRowShape,
            properties.ProjectIRStageRowShape,
            properties.ProjectIRStageRowShape,
            properties.ProjectIRRowShape,
            properties.ProjectIRRowShape,
            properties.ProjectIRRowShape,
        )
        input_shape = row_outputs[0].row_shape
        group_shape = row_outputs[2].row_shape
        window_shape = row_outputs[4].row_shape
        projected_shape = row_outputs[5].row_shape
        assert type(input_shape) is properties.ProjectIRStageRowShape
        assert type(group_shape) is properties.ProjectIRStageRowShape
        assert type(window_shape) is properties.ProjectIRStageRowShape
        assert type(projected_shape) is properties.ProjectIRRowShape
        assert tuple(item.evidence.name for item in input_shape.fields) == (
            "id",
            "amount",
            "category",
        )
        assert tuple(item.evidence.name for item in group_shape.fields) == (
            "category",
            "total",
        )
        assert tuple(item.evidence.name for item in window_shape.fields) == (
            "category",
            "total",
            "ranking",
        )
        assert tuple(item.evidence.name for item in projected_shape.fields) == (
            "category",
            "total",
            "ranking",
        )


def test_checkpoint_fidelity_and_output_allocation_reuse_exact_final_identities(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    simple = _concrete(_build(semantic, "simple"))
    simple_rows = tuple(
        output
        for output in simple.logical_stage.outputs
        if type(output) is properties.ProjectIRRelationRowOutput
    )
    input_shape = simple_rows[0].row_shape
    final_shape = simple_rows[1].row_shape
    assert type(input_shape) is properties.ProjectIRStageRowShape
    assert (
        input_shape.checkpoint.kind is properties.ProjectIRStageRowCheckpointKind.INPUT
    )
    assert tuple(item.evidence.name for item in input_shape.fields) == (
        "id",
        "amount",
        "category",
    )
    assert type(final_shape) is properties.ProjectIRRowShape
    assert tuple(item.evidence.name for item in final_shape.fields) == ("id", "amount")

    windowed = _concrete(_build(semantic, "windowed"))
    outputs = windowed.logical_stage.outputs
    assert tuple(output.occurrence.ref.position for output in outputs) == tuple(
        range(len(outputs))
    )
    assert tuple(type(output) for output in outputs) == (
        properties.ProjectIRRelationRowOutput,
        properties.ProjectIRRelationRowOutput,
        properties.ProjectIRStageScalarFieldOutput,
        properties.ProjectIRRelationRowOutput,
        properties.ProjectIRScalarFieldOutput,
        properties.ProjectIRScalarFieldOutput,
    )
    stage_scalar = outputs[2]
    assert type(stage_scalar) is properties.ProjectIRStageScalarFieldOutput
    assert type(stage_scalar.occurrence.anchor) is project_ir.ProjectIRStageFieldAnchor
    final_ranking = windowed.final_scalar_outputs[1]
    assert stage_scalar.occurrence.ref != final_ranking.occurrence.ref

    attribution = semantic.module_attribution_facts
    assert attribution is not None
    exact = attribution.find_relation_output_fields(windowed.subject.anchor.identity)
    assert tuple(
        output.field.anchor.identity for output in windowed.final_scalar_outputs
    ) == tuple(item.identity for item in exact)
    assert all(
        output.field.evidence is item.semantic_field
        for output, item in zip(windowed.final_scalar_outputs, exact, strict=True)
    )


def test_full_properties_transfers_effects_and_estimates_are_complete(
    tmp_path: Path,
) -> None:
    fragment = _concrete(_build(_semantic_project(tmp_path), "full"))
    stage = fragment.property_stage
    assert len(fragment.logical_stage.transfers) == len(stage.provided)
    assert len(stage.effects) == len(stage.outputs)
    assert stage.estimates.statistics == ()
    assert all(
        effect.determinism is properties.ProjectIRDeterminismEvidence.UNKNOWN
        and effect.error_behavior is properties.ProjectIRErrorBehaviorEvidence.UNKNOWN
        and effect.side_effects is properties.ProjectIRSideEffectEvidence.UNKNOWN
        and effect.evaluation_count
        is properties.ProjectIREvaluationCountEvidence.UNKNOWN
        for effect in stage.effects
    )
    assert not any("Set" in name for name in vars(properties))

    row_slots = []
    for operator in fragment.logical_stage.operators:
        row_output = next(
            output
            for output in stage.outputs
            if type(output) is properties.ProjectIRRelationRowOutput
            and output.occurrence.producer is operator.node
        )
        row_slots.append(
            tuple(
                item.property_slot
                for item in stage.provided
                if item.output is row_output
            )
        )
    shape = properties.ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
    cardinality = properties.ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    bag = properties.ProjectIRProvidedPropertySlot.MULTIPLICITY
    ordering = properties.ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    grain = properties.ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    closed = properties.ProjectIRProvidedPropertySlot.FREE_BINDINGS
    assert tuple(row_slots) == (
        (shape, bag, closed),
        (shape, bag, closed),
        (shape, bag, grain, closed),
        (shape, bag, grain, closed),
        (shape, bag, grain, closed),
        (shape, bag, closed),
        (shape, bag, ordering, closed),
        (shape, cardinality, bag, ordering, closed),
    )
    policies = tuple(
        item
        for item in stage.provided
        if type(item) is properties.ProjectIRProvidedEvaluationPolicy
    )
    assert len(policies) == 1
    assert type(policies[0].output) is properties.ProjectIRStageScalarFieldOutput

    flow_by_consumer = {
        use.slot.consumer.ref: use
        for use in fragment.structural_stage.uses
        if type(use) is project_ir.ProjectIROperatorFlowUseOccurrence
    }
    for transfer in fragment.logical_stage.transfers:
        if type(transfer) is not operators.ProjectIRPreservedPropertyTransfer:
            continue
        flow = flow_by_consumer[transfer.operator.node.ref]
        assert transfer.input_property.output.occurrence is flow.output


def test_global_aggregate_omits_local_grain_without_inventing_it_downstream(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "aggregate_only")
    assert fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert fact.aggregate_grouped_clause_readiness is not None
    assert fact.aggregate_grouped_clause_readiness.status is (
        ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    )
    assert fact.group_key_occurrences == ()
    assert fact.aggregate_result_facts

    fragment = _concrete(_build(semantic, "aggregate_only"))
    group = next(
        operator
        for operator in fragment.logical_stage.operators
        if operator.kind is operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    assert group.evidence.group_key_occurrences == ()
    assert not any(
        property_.property_slot
        is properties.ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
        for property_ in fragment.property_stage.provided
    )
    assert all(
        sum(
            transfer.output_property is property_
            for transfer in fragment.logical_stage.transfers
        )
        == 1
        for property_ in fragment.property_stage.provided
    )


def test_grouped_aggregate_retains_exact_positive_local_grain_downstream(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "full")
    assert fact.group_key_occurrences
    fragment = _concrete(_build(semantic, "full"))
    grain_properties = tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is properties.ProjectIRProvidedLocalGrainEvidence
    )
    assert len(grain_properties) == 3
    assert all(
        len(property_.occurrences) == len(fact.group_key_occurrences)
        and all(
            occurrence is exact
            for occurrence, exact in zip(
                property_.occurrences,
                fact.group_key_occurrences,
                strict=True,
            )
        )
        for property_ in grain_properties
    )
    transfers = tuple(
        next(
            transfer
            for transfer in fragment.logical_stage.transfers
            if transfer.output_property is property_
        )
        for property_ in grain_properties
    )
    assert type(transfers[0]) is operators.ProjectIREstablishedPropertyTransfer
    assert all(
        type(transfer) is operators.ProjectIRPreservedPropertyTransfer
        for transfer in transfers[1:]
    )


def test_allocation_is_deterministic_continuable_and_occurrence_distinct(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    scope = project_ir.ProjectIRSnapshotScope()
    start = construction.ProjectIRAllocationState(
        scope=scope,
        next_plan_node_position=7,
        next_output_value_position=11,
        next_input_slot_position=5,
        next_use_position=5,
    )
    first = _concrete(_build(semantic, "simple", start))
    repeat = _concrete(_build(semantic, "simple", start))
    assert tuple(item.ref for item in first.structural_stage.nodes) == tuple(
        item.ref for item in repeat.structural_stage.nodes
    )
    assert tuple(item.ref for item in first.structural_stage.outputs) == tuple(
        item.ref for item in repeat.structural_stage.outputs
    )
    assert first.ending_allocation == repeat.ending_allocation

    continued = _concrete(_build(semantic, "full", first.ending_allocation))
    assert continued.structural_stage.nodes[0].ref.position == (
        first.ending_allocation.next_plan_node_position
    )
    assert continued.structural_stage.outputs[0].ref.position == (
        first.ending_allocation.next_output_value_position
    )
    assert first.structural_stage.nodes[0].ref.position == 7
    assert tuple(
        item.ref.position for item in continued.structural_stage.nodes
    ) == tuple(
        range(
            first.ending_allocation.next_plan_node_position,
            continued.ending_allocation.next_plan_node_position,
        )
    )

    other = _concrete(
        _build(
            semantic,
            "simple",
            construction.ProjectIRAllocationState(
                scope=project_ir.ProjectIRSnapshotScope(),
                next_plan_node_position=7,
                next_output_value_position=11,
                next_input_slot_position=5,
                next_use_position=5,
            ),
        )
    )
    assert first.structural_stage.nodes[0].ref != other.structural_stage.nodes[0].ref

    same_a = _concrete(_build(semantic, "same_a"))
    same_b = _concrete(_build(semantic, "same_b"))
    assert same_a.subject.anchor != same_b.subject.anchor
    assert same_a.final_scalar_outputs[0].field.evidence.name == (
        same_b.final_scalar_outputs[0].field.evidence.name
    )
    assert same_a.final_scalar_outputs[0].field.evidence.resolved_type == (
        same_b.final_scalar_outputs[0].field.evidence.resolved_type
    )
    assert (
        same_a.final_scalar_outputs[0].field.anchor.identity
        != same_b.final_scalar_outputs[0].field.anchor.identity
    )


def test_non_concrete_is_zero_allocation_and_builder_does_not_follow_upstream(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    start = construction.ProjectIRAllocationState(
        scope=project_ir.ProjectIRSnapshotScope(),
        next_plan_node_position=9,
        next_output_value_position=12,
        next_input_slot_position=4,
        next_use_position=4,
    )
    terminal = _build(semantic, "broken", start)
    assert type(terminal) is construction.ProjectIRNonConcreteSingleRelationFragment
    assert (
        terminal.subject.state is project_ir.ProjectIRRelationConstructionState.UNKNOWN
    )
    assert terminal.ending_allocation is start
    assert terminal.structural_stage.nodes == ()
    assert terminal.structural_stage.outputs == ()
    assert terminal.structural_stage.input_slots == ()
    assert terminal.structural_stage.uses == ()
    assert terminal.logical_stage.operators == ()
    assert terminal.property_stage.provided == ()
    assert terminal.root is None

    consumer = _concrete(_build(semantic, "consumer"))
    assert consumer.semantic_facts.resolution is not None
    assert consumer.attribution is semantic.module_attribution_facts
    assert consumer.structural_stage.subjects == (consumer.subject,)
    assert all(
        type(use) is project_ir.ProjectIROperatorFlowUseOccurrence
        for use in consumer.structural_stage.uses
    )
    assert not any(
        type(use) is project_ir.ProjectIRUseOccurrence
        for use in consumer.structural_stage.uses
    )

    foreign = _semantic_project(tmp_path / "foreign")
    foreign_attribution = foreign.module_attribution_facts
    assert foreign_attribution is not None
    with pytest.raises(ValueError, match="exact semantic root"):
        construction.build_project_ir_single_relation_fragment(
            semantic=_fact(semantic, "simple"),
            attribution=foreign_attribution,
            allocation=start,
        )


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_construction import ProjectIRAllocationState, build_project_ir_single_relation_fragment

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
facts = semantic.module_semantic_facts
attribution = semantic.module_attribution_facts
assert facts is not None and attribution is not None
relation = next(fact for environment in facts.environments for fact in environment.relation_facts if fact.owner.identity.declared_name == "full")
result = build_project_ir_single_relation_fragment(
    semantic=relation,
    attribution=attribution,
    allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
)
print((tuple(item.kind.value for item in result.logical_stage.operators), tuple(item.ref.position for item in result.structural_stage.outputs), tuple(output.field.anchor.identity.field_position for output in result.final_scalar_outputs), result.ending_allocation.next_use_position))
"""


def test_builder_is_hash_seed_cwd_independent_and_public_sql_relation_ir_zero_delta(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("999", "cwd-b")):
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

    assert not hasattr(pietto, "ProjectIRAllocationState")
    assert not hasattr(project_package, "ProjectIRAllocationState")
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
        assert "project_ir_construction" not in text
        assert "ProjectIRAllocationState" not in text
