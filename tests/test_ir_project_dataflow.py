from __future__ import annotations

from dataclasses import dataclass, fields, replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto
import pietto._project as project_package
import pietto._project.project_ir as project_ir
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_properties as properties
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyKind,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority And Observed Blocker",
    "Frozen Reader And Changed-path Closure",
    "Exact Semantic Row Checkpoints",
    "Stage Row And Scalar Value Authority",
    "Semantic Use And Operator-flow Use Separation",
    "Exact Intra-relation Topology",
    "Property Transfer Through Flow Authority",
    "Feasibility Proof",
    "Determinism Immutability And Privacy",
    "Integration Boundaries And Non-goals",
    "Slice 5 Resume Handoff",
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
query group_window:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
        ranking = row_number() window:
            order by:
                total desc
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
        ranking = row_number() window:
            order by:
                total desc
    satisfying:
        total > 0
    order by:
        ranking
    limit 5
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


def _anchor(
    fact: ProjectModuleRelationSemanticFacts,
) -> project_ir.ProjectIRRelationAnchor:
    owner = fact.owner
    return project_ir.ProjectIRRelationAnchor(
        identity=ProjectDeclarationOccurrenceIdentity(
            identity=owner.identity,
            module_position=owner.module_position,
            declaration_position=owner.declaration_position,
        )
    )


def _final_shape(
    semantic: ProjectSemanticResult,
    fact: ProjectModuleRelationSemanticFacts,
) -> properties.ProjectIRRowShape:
    schema = fact.state.schema
    assert schema is not None
    relation = _anchor(fact)
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    if fact.owner.identity.declaration_kind is ProjectSymbolKind.SOURCE:
        identities = tuple(
            item.source_field
            for item in attribution.source_field_origins
            if item.source_field.owner == relation.identity
        )
    else:
        identities = tuple(
            item.identity
            for item in attribution.find_relation_output_fields(relation.identity)
        )
    evidence = tuple(schema.fields.values())
    assert len(identities) == len(evidence)
    return properties.ProjectIRRowShape(
        relation=relation,
        evidence=fact,
        fields=tuple(
            properties.ProjectIRRowField(
                anchor=project_ir.ProjectIRFieldAnchor(identity=identity),
                evidence=field,
            )
            for identity, field in zip(identities, evidence, strict=True)
        ),
    )


def _stage_shape(
    fact: ProjectModuleRelationSemanticFacts,
    kind: properties.ProjectIRStageRowCheckpointKind,
) -> properties.ProjectIRStageRowShape:
    checkpoint = properties.ProjectIRStageRowCheckpoint(
        relation=_anchor(fact),
        evidence=fact,
        kind=kind,
    )
    schema = checkpoint.state.schema
    assert schema is not None
    return properties.ProjectIRStageRowShape(
        checkpoint=checkpoint,
        fields=tuple(
            properties.ProjectIRStageRowField(
                checkpoint=checkpoint,
                field_position=position,
                evidence=field,
            )
            for position, field in enumerate(schema.fields.values())
        ),
    )


def _shape_for_operator(
    fact: ProjectModuleRelationSemanticFacts,
    final_shape: properties.ProjectIRRowShape,
    kind: operators.ProjectIRLogicalOperatorKind,
) -> properties.ProjectIRCurrentRowShape:
    if fact.owner.identity.declaration_kind is ProjectSymbolKind.SOURCE:
        return final_shape
    checkpoint = {
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT: (
            properties.ProjectIRStageRowCheckpointKind.INPUT
        ),
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER: (
            properties.ProjectIRStageRowCheckpointKind.INPUT
        ),
        operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE: (
            properties.ProjectIRStageRowCheckpointKind.BASE_RESULT
        ),
        operators.ProjectIRLogicalOperatorKind.RESULT_FILTER: (
            properties.ProjectIRStageRowCheckpointKind.BASE_RESULT
        ),
        operators.ProjectIRLogicalOperatorKind.WINDOW_EVALUATION: (
            properties.ProjectIRStageRowCheckpointKind.FINAL
        ),
    }.get(kind)
    return final_shape if checkpoint is None else _stage_shape(fact, checkpoint)


@dataclass(frozen=True, slots=True)
class _Pipeline:
    structural: project_ir.ProjectIRStructuralStage
    property_stage: properties.ProjectIRPropertyStage
    operators: tuple[operators.ProjectIRLogicalOperatorOccurrence, ...]
    logical: operators.ProjectIRLogicalOperatorStage
    row_outputs: tuple[properties.ProjectIRRelationRowOutput, ...]
    flow_uses: tuple[project_ir.ProjectIROperatorFlowUseOccurrence, ...]


def _pipeline(
    semantic: ProjectSemanticResult,
    fact: ProjectModuleRelationSemanticFacts,
    kinds: tuple[operators.ProjectIRLogicalOperatorKind, ...],
) -> _Pipeline:
    scope = project_ir.ProjectIRSnapshotScope()
    relation = _anchor(fact)
    nodes = tuple(
        project_ir.ProjectIRPlanNodeOccurrence(
            ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=position),
            anchor=relation,
        )
        for position in range(len(kinds))
    )
    final_shape = _final_shape(semantic, fact)
    output_pairs = tuple(
        (
            occurrence := project_ir.ProjectIROutputValueOccurrence(
                ref=project_ir.ProjectIROutputValueRef(
                    scope=scope,
                    position=position,
                ),
                producer=node,
                anchor=relation,
            ),
            properties.ProjectIRRelationRowOutput(
                occurrence=occurrence,
                row_shape=_shape_for_operator(fact, final_shape, kind),
            ),
        )
        for position, (node, kind) in enumerate(zip(nodes, kinds, strict=True))
    )
    occurrences = tuple(item[0] for item in output_pairs)
    row_outputs = tuple(item[1] for item in output_pairs)
    slots = tuple(
        project_ir.ProjectIRInputSlotOccurrence(
            ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=position),
            consumer=node,
            input_ordinal=0,
        )
        for position, node in enumerate(nodes[1:])
    )
    flow_uses = tuple(
        project_ir.ProjectIROperatorFlowUseOccurrence(
            ref=project_ir.ProjectIRUseRef(scope=scope, position=position),
            output=output,
            slot=slot,
        )
        for position, (output, slot) in enumerate(zip(occurrences, slots, strict=False))
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=occurrences,
        input_slots=slots,
        uses=flow_uses,
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=relation,
                evidence=fact,
                root=nodes[-1],
            ),
        ),
    )
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=row_outputs,
    )
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=fact,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
    )
    return _Pipeline(
        structural=structural,
        property_stage=property_stage,
        operators=operator_occurrences,
        logical=logical,
        row_outputs=row_outputs,
        flow_uses=flow_uses,
    )


def test_controlling_contract_locks_root_cause_authority_scope_and_handoff() -> None:
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
        "INTRA_RELATION_PLAN_DATAFLOW_AUTHORITY_MISSING",
        "FINAL_RELATION_SCHEMA_OVERLOADED_AS_ALL_OPERATOR_ROW_SHAPES",
        "SEMANTIC_PROVENANCE_USE_OVERLOADED_AS_ALL_PLAN_DATAFLOW_USES",
        "final semantic row != intermediate stage row",
        "semantic provenance edge != intra-relation operator-flow edge",
        "A2/M11/D0",
        "cce7709f143de4eb5f9989cbbbd804fe08e71d74",
        "33321099987",
        "Add Project IR intra-relation dataflow readiness",
        "PASS — PHASE61_SLICE5_INTRA_RELATION_DATAFLOW_READINESS_"
        "CONTINUATION_END_TO_END",
        "Slice 5 remains next / unstarted",
    ):
        assert evidence in normalized


def test_semantic_input_base_result_and_final_checkpoints_are_exact(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    rows = _fact(semantic, "rows")
    simple = _fact(semantic, "simple")
    group_window = _fact(semantic, "group_window")
    readiness = group_window.aggregate_grouped_clause_readiness
    assert readiness is not None

    assert rows.input_state is None
    assert rows.base_result_state is None
    assert simple.input_state is rows.state
    assert simple.base_result_state is simple.state
    assert tuple(simple.input_state.schema.fields) == (  # type: ignore[union-attr]
        "id",
        "amount",
        "category",
    )
    assert tuple(simple.state.schema.fields) == ("id", "amount")  # type: ignore[union-attr]

    assert group_window.input_state is rows.state
    assert group_window.base_result_state is readiness.finalization.state
    assert group_window.base_result_state is not group_window.state
    assert tuple(group_window.base_result_state.schema.fields) == (  # type: ignore[union-attr]
        "category",
        "total",
    )
    assert tuple(group_window.state.schema.fields) == (  # type: ignore[union-attr]
        "category",
        "total",
        "ranking",
    )

    broken = _fact(semantic, "broken")
    assert broken.input_state is rows.state
    assert broken.base_result_state is broken.state
    assert broken.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    with pytest.raises(ValueError, match="concrete checkpoint"):
        _stage_shape(broken, properties.ProjectIRStageRowCheckpointKind.BASE_RESULT)


def test_stage_rows_and_scalars_are_plan_local_while_final_exports_keep_identity(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    simple = _fact(semantic, "simple")
    grouped = _fact(semantic, "group_window")
    simple_input = _stage_shape(
        simple,
        properties.ProjectIRStageRowCheckpointKind.INPUT,
    )
    grouped_base = _stage_shape(
        grouped,
        properties.ProjectIRStageRowCheckpointKind.BASE_RESULT,
    )
    grouped_final_stage = _stage_shape(
        grouped,
        properties.ProjectIRStageRowCheckpointKind.FINAL,
    )
    final_shape = _final_shape(semantic, grouped)

    assert tuple(item.evidence.name for item in simple_input.fields) == (
        "id",
        "amount",
        "category",
    )
    assert tuple(item.evidence.name for item in grouped_base.fields) == (
        "category",
        "total",
    )
    assert tuple(item.evidence.name for item in grouped_final_stage.fields) == (
        "category",
        "total",
        "ranking",
    )
    assert all(not hasattr(item, "identity") for item in grouped_base.fields)
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    exact_identities = tuple(
        item.identity
        for item in attribution.find_relation_output_fields(_anchor(grouped).identity)
    )
    assert (
        tuple(item.anchor.identity for item in final_shape.fields) == exact_identities
    )

    scope = project_ir.ProjectIRSnapshotScope()
    window_node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=_anchor(grouped),
    )
    stage_anchor = project_ir.ProjectIRStageFieldAnchor(
        producer=window_node,
        field_position=2,
    )
    stage_occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=0),
        producer=window_node,
        anchor=stage_anchor,
    )
    stage_scalar = properties.ProjectIRStageScalarFieldOutput(
        occurrence=stage_occurrence,
        row_shape=grouped_final_stage,
        field=grouped_final_stage.fields[2],
    )
    window_fact = grouped.window_outputs[0]
    policy = properties.ProjectIRProvidedEvaluationPolicy(
        output=stage_scalar,
        evidence=window_fact,
    )
    assert type(stage_scalar.occurrence.anchor) is project_ir.ProjectIRStageFieldAnchor
    assert not isinstance(
        stage_scalar.occurrence.anchor, project_ir.ProjectIRFieldAnchor
    )
    project_fact = window_fact.project_fact
    assert project_fact is not None
    assert (
        policy.policy is project_fact.analysis.validated_specification.function_policy
    )

    final_node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=1),
        anchor=_anchor(grouped),
    )
    final_occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=1),
        producer=final_node,
        anchor=final_shape.fields[2].anchor,
    )
    final_scalar = properties.ProjectIRScalarFieldOutput(
        occurrence=final_occurrence,
        row_shape=final_shape,
        field=final_shape.fields[2],
    )
    assert type(final_scalar) is not type(stage_scalar)
    assert final_scalar.field.anchor.identity is exact_identities[2]


def test_semantic_use_and_operator_flow_use_keep_separate_authority(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    simple = _fact(semantic, "simple")
    pipeline = _pipeline(
        semantic,
        simple,
        (
            operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
            operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ),
    )
    flow = pipeline.flow_uses[0]
    assert tuple(item.name for item in fields(flow)) == ("ref", "output", "slot")
    assert not hasattr(flow, "source_order")
    assert not hasattr(flow, "anchor")
    assert flow.output is pipeline.row_outputs[0].occurrence
    assert flow.slot.consumer is pipeline.operators[1].node

    attribution = semantic.module_attribution_facts
    assert attribution is not None and simple.resolution is not None
    dependency = next(
        item
        for item in attribution.dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.reference.owner == _anchor(simple).identity
    )
    semantic_anchor = project_ir.ProjectIRResolvedRelationAnchor(
        resolution=simple.resolution,
        dependency=dependency,
    )
    with pytest.raises(ValueError, match="exact endpoints"):
        project_ir.ProjectIRUseOccurrence(
            ref=project_ir.ProjectIRUseRef(
                scope=pipeline.structural.scope,
                position=1,
            ),
            output=pipeline.row_outputs[0].occurrence,
            slot=flow.slot,
            role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
            source_order=0,
            anchor=semantic_anchor,
        )


def test_full_pipeline_has_one_exact_flow_edge_per_adjacent_operator(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    full = _fact(semantic, "full")
    kinds = tuple(operators.ProjectIRLogicalOperatorKind)
    pipeline = _pipeline(semantic, full, kinds)
    assert len(pipeline.row_outputs) == len(kinds) == 8
    assert len(pipeline.flow_uses) == len(kinds) - 1
    for position, flow in enumerate(pipeline.flow_uses):
        assert flow.output is pipeline.row_outputs[position].occurrence
        assert flow.slot.consumer is pipeline.operators[position + 1].node
        assert flow.slot.input_ordinal == 0
    assert tuple(type(output.row_shape) for output in pipeline.row_outputs) == (
        properties.ProjectIRStageRowShape,
        properties.ProjectIRStageRowShape,
        properties.ProjectIRStageRowShape,
        properties.ProjectIRStageRowShape,
        properties.ProjectIRStageRowShape,
        properties.ProjectIRRowShape,
        properties.ProjectIRRowShape,
        properties.ProjectIRRowShape,
    )

    source = _pipeline(
        semantic,
        _fact(semantic, "rows"),
        (operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,),
    )
    assert source.flow_uses == ()
    assert type(source.row_outputs[0].row_shape) is properties.ProjectIRRowShape


def test_flow_topology_rejects_missing_skipped_cross_relation_and_tuple_drift(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    full = _fact(semantic, "full")
    pipeline = _pipeline(
        semantic,
        full,
        tuple(operators.ProjectIRLogicalOperatorKind),
    )

    missing_structural = replace(
        pipeline.structural,
        uses=pipeline.structural.uses[:-1],
    )
    missing_properties = replace(
        pipeline.property_stage,
        structural=missing_structural,
    )
    with pytest.raises(ValueError, match="topology must agree"):
        replace(pipeline.logical, property_stage=missing_properties)

    rewired = replace(
        pipeline.flow_uses[1],
        output=pipeline.flow_uses[0].output,
    )
    rewired_structural = replace(
        pipeline.structural,
        uses=(pipeline.flow_uses[0], rewired, *pipeline.flow_uses[2:]),
    )
    rewired_properties = replace(
        pipeline.property_stage,
        structural=rewired_structural,
    )
    with pytest.raises(ValueError, match="topology must agree"):
        replace(pipeline.logical, property_stage=rewired_properties)

    wrong_order = (
        replace(
            pipeline.operators[0],
            kind=operators.ProjectIRLogicalOperatorKind.ROW_FILTER,
        ),
        replace(
            pipeline.operators[1],
            kind=operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        ),
        *pipeline.operators[2:],
    )
    with pytest.raises(ValueError, match="exact stage order"):
        replace(pipeline.logical, operators=wrong_order)

    simple = _fact(semantic, "simple")
    foreign_node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(
            scope=pipeline.structural.scope,
            position=len(pipeline.structural.nodes),
        ),
        anchor=_anchor(simple),
    )
    foreign_slot = project_ir.ProjectIRInputSlotOccurrence(
        ref=project_ir.ProjectIRInputSlotRef(
            scope=pipeline.structural.scope,
            position=len(pipeline.structural.input_slots),
        ),
        consumer=foreign_node,
        input_ordinal=0,
    )
    with pytest.raises(ValueError, match="within one relation"):
        project_ir.ProjectIROperatorFlowUseOccurrence(
            ref=project_ir.ProjectIRUseRef(
                scope=pipeline.structural.scope,
                position=len(pipeline.structural.uses),
            ),
            output=pipeline.row_outputs[0].occurrence,
            slot=foreign_slot,
        )


def test_preserved_property_uses_exact_flow_predecessor(tmp_path: Path) -> None:
    semantic = _semantic_project(tmp_path)
    simple = _fact(semantic, "simple")
    pipeline = _pipeline(
        semantic,
        simple,
        (
            operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
            operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ),
    )
    input_bag = properties.ProjectIRProvidedBagMultiplicity(
        output=pipeline.row_outputs[0]
    )
    final_bag = properties.ProjectIRProvidedBagMultiplicity(
        output=pipeline.row_outputs[1]
    )
    property_stage = replace(
        pipeline.property_stage,
        provided=(input_bag, final_bag),
    )
    established = operators.ProjectIREstablishedPropertyTransfer(
        operator=pipeline.operators[0],
        output_property=input_bag,
    )
    preserved = operators.ProjectIRPreservedPropertyTransfer(
        operator=pipeline.operators[1],
        input_property=input_bag,
        output_property=final_bag,
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=pipeline.operators,
        transfers=(established, preserved),
    )
    assert logical.transfers == (established, preserved)

    wrong_input = replace(preserved, input_property=final_bag)
    with pytest.raises(ValueError, match="exact flow predecessor"):
        replace(logical, transfers=(established, wrong_input))


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRSnapshotScope,
    ProjectIRUseRef,
)
from pietto._project.project_ir_properties import (
    ProjectIRStageRowCheckpoint,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowField,
    ProjectIRStageRowShape,
)

parsed = check.check_project_parse_only(Path(sys.argv[1]))
semantic = build_empty_project_semantic_result(parsed)
facts = semantic.module_semantic_facts
assert facts is not None
relation = next(
    fact
    for environment in facts.environments
    for fact in environment.relation_facts
    if fact.owner.identity.declared_name == "simple"
)
owner = relation.owner
anchor = ProjectIRRelationAnchor(
    identity=ProjectDeclarationOccurrenceIdentity(
        identity=owner.identity,
        module_position=owner.module_position,
        declaration_position=owner.declaration_position,
    )
)
checkpoint = ProjectIRStageRowCheckpoint(
    relation=anchor,
    evidence=relation,
    kind=ProjectIRStageRowCheckpointKind.INPUT,
)
schema = checkpoint.state.schema
assert schema is not None
shape = ProjectIRStageRowShape(
    checkpoint=checkpoint,
    fields=tuple(
        ProjectIRStageRowField(
            checkpoint=checkpoint,
            field_position=position,
            evidence=field,
        )
        for position, field in enumerate(schema.fields.values())
    ),
)
scope = ProjectIRSnapshotScope()
first = ProjectIRPlanNodeOccurrence(
    ref=ProjectIRPlanNodeRef(scope=scope, position=0), anchor=anchor
)
second = ProjectIRPlanNodeOccurrence(
    ref=ProjectIRPlanNodeRef(scope=scope, position=1), anchor=anchor
)
output = ProjectIROutputValueOccurrence(
    ref=ProjectIROutputValueRef(scope=scope, position=0),
    producer=first,
    anchor=anchor,
)
slot = ProjectIRInputSlotOccurrence(
    ref=ProjectIRInputSlotRef(scope=scope, position=0),
    consumer=second,
    input_ordinal=0,
)
flow = ProjectIROperatorFlowUseOccurrence(
    ref=ProjectIRUseRef(scope=scope, position=0),
    output=output,
    slot=slot,
)
print((repr(scope), checkpoint.kind.value, tuple(item.evidence.name for item in shape.fields), flow.ref.position, hasattr(flow, "source_order")))
"""


def test_new_carriers_are_hash_seed_and_cwd_independent_and_private(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("271", "cwd-b")):
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
        outputs.append(completed.stdout.strip())
    assert outputs[0] == outputs[1]
    assert outputs[0] == (
        "('ProjectIRSnapshotScope()', 'input', ('id', 'amount', 'category'), 0, False)"
    )

    assert not hasattr(pietto, "ProjectIROperatorFlowUseOccurrence")
    assert not hasattr(project_package, "ProjectIROperatorFlowUseOccurrence")
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
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "ProjectIROperatorFlowUseOccurrence" not in text
        assert "ProjectIRStageRowShape" not in text
    for source in (
        REPO_ROOT / "src/pietto/_project/project_ir.py",
        REPO_ROOT / "src/pietto/_project/project_ir_properties.py",
        REPO_ROOT / "src/pietto/_project/project_ir_operators.py",
    ):
        text = source.read_text(encoding="utf-8")
        assert "build_project_ir" not in text
        assert "ProjectIRAllocation" not in text
