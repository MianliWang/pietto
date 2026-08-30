from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, fields, replace
import inspect
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
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyKind,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_ir_operators.py"
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Live Current Semantic Authority Audit",
    "Frozen Current Operator Algebra",
    "Operator Occurrence And Stage-order Laws",
    "Exact Property-transfer Matrix",
    "Required Row-shape Compatibility",
    "Effect And Estimate Preservation",
    "Logical-stage Formation Laws",
    "Determinism Immutability And Privacy",
    "Focused Assurance Contract",
    "Integration Boundary And Non-goals",
    "Slice 5 Handoff",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    value: Int nullable
    category: Text nullable
source rows: Row is postgres.table("rows")
query full:
    from rows
    let:
        floor = 0
    where id > floor
    group by:
        category
    select:
        group_name = category
        total = sum(value)
        ranking = row_number() window child
    window child = base
    window base:
        partition by:
            group_name
        order by:
            total desc
    satisfying:
        total > 0
    order by:
        ranking
    limit 5
query filtered:
    from rows
    where id > 0
    select:
        id
        value
        category
query ordered:
    from rows
    select:
        id
        value
        category
    order by:
        id desc
    limit 3
query grouped:
    from rows
    group by:
        category
    select:
        group_name = category
        total = sum(value)
query literal_satisfying:
    from rows
    group by:
        category
    select:
        group_name = category
        total = sum(value)
    satisfying:
        true
query consumer:
    from filtered
    select:
        id
        value
        category
"""


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parse_result = project_check.check_project_parse_only(root)
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
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


def _row_shape(
    semantic: ProjectSemanticResult,
    fact: ProjectModuleRelationSemanticFacts,
) -> properties.ProjectIRRowShape:
    assert fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    schema = fact.state.schema
    assert schema is not None
    relation = _anchor(fact)
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    lineages = attribution.find_row_lineage(relation.identity)
    assert len(lineages) == 1
    evidence = tuple(schema.fields.values())
    identities = tuple(item.field for item in lineages[0].fields) or tuple(
        ProjectModuleRowFieldIdentity(
            owner=relation.identity,
            kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
            field_position=position,
            name=field.name,
        )
        for position, field in enumerate(evidence)
    )
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


def _node(
    scope: project_ir.ProjectIRSnapshotScope,
    position: int,
    anchor: project_ir.ProjectIRRelationAnchor,
) -> project_ir.ProjectIRPlanNodeOccurrence:
    return project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=position),
        anchor=anchor,
    )


def _relation_output(
    scope: project_ir.ProjectIRSnapshotScope,
    position: int,
    node: project_ir.ProjectIRPlanNodeOccurrence,
    shape: properties.ProjectIRRowShape,
) -> tuple[
    project_ir.ProjectIROutputValueOccurrence,
    properties.ProjectIRRelationRowOutput,
]:
    occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=position),
        producer=node,
        anchor=shape.relation,
    )
    return occurrence, properties.ProjectIRRelationRowOutput(
        occurrence=occurrence,
        row_shape=shape,
    )


@dataclass(frozen=True, slots=True)
class _Pipeline:
    structural: project_ir.ProjectIRStructuralStage
    property_stage: properties.ProjectIRPropertyStage
    operator_occurrences: tuple[operators.ProjectIRLogicalOperatorOccurrence, ...]
    logical_stage: operators.ProjectIRLogicalOperatorStage


def _empty_pipeline(
    fact: ProjectModuleRelationSemanticFacts,
    kinds: tuple[operators.ProjectIRLogicalOperatorKind, ...],
) -> _Pipeline:
    scope = project_ir.ProjectIRSnapshotScope()
    anchor = _anchor(fact)
    nodes = tuple(_node(scope, position, anchor) for position in range(len(kinds)))
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=anchor,
                evidence=fact,
                root=nodes[-1],
            ),
        ),
    )
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
    )
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=fact,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )
    logical_stage = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
    )
    return _Pipeline(
        structural=structural,
        property_stage=property_stage,
        operator_occurrences=operator_occurrences,
        logical_stage=logical_stage,
    )


def test_controlling_contract_locks_authority_algebra_transfer_and_handoff() -> None:
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
        "be984f7ae9c0821cfa14229da99bf9c8da97a048",
        "c0d4bc91aa1883065427244d5572ba3e2d424b67",
        "33308020119",
        "A3/M5/D0",
        "Relation Input -> Row Filter -> Group/Aggregate -> Result Filter -> "
        "Window Evaluation -> Final Projection -> Relation Ordering -> Limit",
        "operator kind != plan-node identity",
        "`let:` and named-window declarations are not operators",
        "window-local ordering != relation-result ordering",
        "provided property != required property != effect evidence != estimate",
        "input row multiplicity == output row multiplicity",
        "ProjectIRRowShapeCompatibilityStatus",
        "Phase 61 Slice 5 — Canonical Single-Relation Construction From Existing "
        "Project Semantic Facts",
        "Add Phase 61 Project IR operator algebra",
        "PASS — PHASE61_SLICE4_PROJECT_IR_CURRENT_LOGICAL_OPERATOR_ALGEBRA_"
        "EXACT_PROPERTY_TRANSFER_END_TO_END",
        "Slice 5 remains next / unstarted",
    ):
        assert evidence in normalized


def test_operator_carriers_are_private_frozen_slotted_and_keyword_only() -> None:
    carriers = (
        operators.ProjectIRLogicalOperatorOccurrence,
        operators.ProjectIRPreservedPropertyTransfer,
        operators.ProjectIREstablishedPropertyTransfer,
        operators.ProjectIRUnavailablePropertyTransfer,
        operators.ProjectIRRowShapeCompatibility,
        operators.ProjectIRLogicalOperatorStage,
    )
    for carrier in carriers:
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    assert operators.__all__ == ()
    assert tuple(operators.ProjectIRLogicalOperatorKind) == (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER,
        operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
        operators.ProjectIRLogicalOperatorKind.RESULT_FILTER,
        operators.ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        operators.ProjectIRLogicalOperatorKind.RELATION_ORDERING,
        operators.ProjectIRLogicalOperatorKind.LIMIT,
    )


def test_exact_eight_stage_algebra_retains_order_without_let_or_named_operators(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    full = _fact(semantic, "full")
    definition = full.owner.definition
    assert definition.let_clause is not None  # type: ignore[union-attr]
    assert definition.named_windows  # type: ignore[union-attr]
    pipeline = _empty_pipeline(full, tuple(operators.ProjectIRLogicalOperatorKind))
    assert tuple(item.kind for item in pipeline.logical_stage.operators) == tuple(
        operators.ProjectIRLogicalOperatorKind
    )
    assert not any(
        name in operators.ProjectIRLogicalOperatorKind.__members__
        for name in (
            "LET",
            "COMPUTE",
            "NAMED_WINDOW",
            "WINDOW_FRAME",
            "EXCLUDE",
            "NULL_TREATMENT",
            "FROM_FIRST_LAST",
        )
    )
    assert pipeline.logical_stage.structural is pipeline.structural


def test_absent_clauses_omit_nodes_and_source_input_is_one_logical_leaf(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    consumer = _empty_pipeline(
        _fact(semantic, "consumer"),
        (
            operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
            operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ),
    )
    assert len(consumer.logical_stage.operators) == 2
    source = _empty_pipeline(
        _fact(semantic, "rows"),
        (operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,),
    )
    assert len(source.logical_stage.operators) == 1
    assert source.logical_stage.operators[0].evidence.resolution is None
    assert not hasattr(operators, "ProjectIRScanOperator")


def test_where_satisfying_and_combined_group_operator_are_nominally_distinct(
    tmp_path: Path,
) -> None:
    pipeline = _empty_pipeline(
        _fact(_semantic_project(tmp_path), "full"),
        tuple(operators.ProjectIRLogicalOperatorKind),
    )
    kinds = tuple(item.kind for item in pipeline.operator_occurrences)
    assert kinds.index(operators.ProjectIRLogicalOperatorKind.ROW_FILTER) < kinds.index(
        operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    assert kinds.index(
        operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    ) < kinds.index(operators.ProjectIRLogicalOperatorKind.RESULT_FILTER)
    assert kinds.count(operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE) == 1
    assert "GROUP" not in operators.ProjectIRLogicalOperatorKind.__members__
    assert "AGGREGATE" not in operators.ProjectIRLogicalOperatorKind.__members__


def test_empty_satisfying_dependency_ledger_is_exact_not_missing(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "literal_satisfying")
    assert not tuple(
        item
        for item in fact.clause_dependencies
        if item.role is ProjectModuleFactOccurrenceRole.SATISFYING
    )
    pipeline = _empty_pipeline(
        fact,
        (
            operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
            operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
            operators.ProjectIRLogicalOperatorKind.RESULT_FILTER,
            operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ),
    )
    assert pipeline.operator_occurrences[2].kind is (
        operators.ProjectIRLogicalOperatorKind.RESULT_FILTER
    )


def test_row_filter_preserves_only_exact_caller_supplied_properties(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "filtered")
    shape = _row_shape(semantic, fact)
    scope = project_ir.ProjectIRSnapshotScope()
    anchor = shape.relation
    nodes = tuple(_node(scope, position, anchor) for position in range(3))
    first_occurrence, first_output = _relation_output(scope, 0, nodes[0], shape)
    second_occurrence, second_output = _relation_output(scope, 1, nodes[1], shape)
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=(first_occurrence, second_occurrence),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=anchor,
                evidence=fact,
                root=nodes[-1],
            ),
        ),
    )
    first_properties = (
        properties.ProjectIRProvidedOutputShape(output=first_output),
        properties.ProjectIRProvidedBagMultiplicity(output=first_output),
        properties.ProjectIRProvidedClosedBindings(output=first_output),
    )
    second_properties = (
        properties.ProjectIRProvidedOutputShape(output=second_output),
        properties.ProjectIRProvidedBagMultiplicity(output=second_output),
        properties.ProjectIRProvidedClosedBindings(output=second_output),
    )
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=(first_output, second_output),
        provided=(*first_properties, *second_properties),
    )
    kinds = (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
    )
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=fact,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )
    filter_operator = operator_occurrences[1]
    transfers = (
        *(
            operators.ProjectIREstablishedPropertyTransfer(
                operator=operator_occurrences[0],
                output_property=property_,
            )
            for property_ in first_properties
        ),
        *(
            operators.ProjectIRPreservedPropertyTransfer(
                operator=filter_operator,
                input_property=input_property,
                output_property=output_property,
            )
            for input_property, output_property in zip(
                first_properties,
                second_properties,
                strict=True,
            )
        ),
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
        transfers=transfers,
    )
    assert logical.transfers == transfers
    with pytest.raises(ValueError, match="requires one exact transfer proof"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=property_stage,
            operators=operator_occurrences,
            transfers=transfers[:-1],
        )
    preserved = operators.project_ir_preserved_property_slots(
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER
    )
    assert (
        properties.ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING in preserved
    )
    assert properties.ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS in preserved
    assert (
        properties.ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE not in preserved
    )

    unknown = properties.ProjectIRUnavailableProvidedProperty(
        output=first_output,
        property_slot=properties.ProjectIRProvidedPropertySlot.FACT_DOMAINS,
        availability=properties.ProjectIRPropertyAvailability.UNKNOWN,
    )
    with pytest.raises(ValueError, match="cannot preserve"):
        operators.ProjectIRPreservedPropertyTransfer(
            operator=filter_operator,
            input_property=unknown,
            output_property=second_properties[0],
        )


def test_transfer_matrix_freezes_group_window_projection_bag_and_order_boundaries() -> (
    None
):
    group = operators.project_ir_established_property_slots(
        operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    assert group == (
        properties.ProjectIRProvidedPropertySlot.OUTPUT_SHAPE,
        properties.ProjectIRProvidedPropertySlot.MULTIPLICITY,
        properties.ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE,
    )
    assert (
        properties.ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING not in group
    )

    window_preserved = operators.project_ir_preserved_property_slots(
        operators.ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
    )
    assert properties.ProjectIRProvidedPropertySlot.MULTIPLICITY in window_preserved
    assert (
        properties.ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
        not in window_preserved
    )
    projection = operators.project_ir_preserved_property_slots(
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION
    )
    assert properties.ProjectIRProvidedPropertySlot.MULTIPLICITY in projection
    assert properties.ProjectIRProvidedPropertySlot.OUTPUT_SHAPE not in projection
    assert not any("Set" in name for name in vars(operators))


def test_one_operator_retains_distinct_relation_and_scalar_output_transfers(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "filtered")
    shape = _row_shape(semantic, fact)
    scope = project_ir.ProjectIRSnapshotScope()
    nodes = tuple(_node(scope, position, shape.relation) for position in range(3))
    input_occurrence, input_output = _relation_output(scope, 0, nodes[0], shape)
    relation_occurrence, relation_output = _relation_output(scope, 1, nodes[2], shape)
    scalar_occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=2),
        producer=nodes[2],
        anchor=shape.fields[0].anchor,
    )
    scalar_output = properties.ProjectIRScalarFieldOutput(
        occurrence=scalar_occurrence,
        row_shape=shape,
        field=shape.fields[0],
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=(input_occurrence, relation_occurrence, scalar_occurrence),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=shape.relation,
                evidence=fact,
                root=nodes[-1],
            ),
        ),
    )
    input_shape = properties.ProjectIRProvidedOutputShape(output=input_output)
    relation_shape = properties.ProjectIRProvidedOutputShape(output=relation_output)
    scalar_shape = properties.ProjectIRProvidedOutputShape(output=scalar_output)
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=(input_output, relation_output, scalar_output),
        provided=(input_shape, relation_shape, scalar_shape),
    )
    kinds = (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
    )
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=fact,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )
    transfers = (
        operators.ProjectIREstablishedPropertyTransfer(
            operator=operator_occurrences[0],
            output_property=input_shape,
        ),
        operators.ProjectIREstablishedPropertyTransfer(
            operator=operator_occurrences[-1],
            output_property=relation_shape,
        ),
        operators.ProjectIREstablishedPropertyTransfer(
            operator=operator_occurrences[-1],
            output_property=scalar_shape,
        ),
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
        transfers=transfers,
    )
    assert logical.transfers == transfers
    with pytest.raises(ValueError, match="cannot preserve"):
        operators.ProjectIRPreservedPropertyTransfer(
            operator=operator_occurrences[1],
            input_property=input_shape,
            output_property=scalar_shape,
        )


def test_relation_ordering_and_limit_establish_exact_ungrouped_properties(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    fact = _fact(semantic, "ordered")
    shape = _row_shape(semantic, fact)
    scope = project_ir.ProjectIRSnapshotScope()
    anchor = shape.relation
    nodes = tuple(_node(scope, position, anchor) for position in range(4))
    order_occurrence, order_output = _relation_output(scope, 0, nodes[2], shape)
    limit_occurrence, limit_output = _relation_output(scope, 1, nodes[3], shape)
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=(order_occurrence, limit_occurrence),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=anchor,
                evidence=fact,
                root=nodes[-1],
            ),
        ),
    )
    order_property = properties.ProjectIRProvidedRelationOrdering(
        output=order_output,
        evidence=fact,
    )
    cardinality = properties.ProjectIRProvidedCardinalityUpperBound(
        output=limit_output,
        evidence=fact,
    )
    retained_order = properties.ProjectIRProvidedRelationOrdering(
        output=limit_output,
        evidence=fact,
    )
    effect = properties.ProjectIREffectEvidence(
        output=limit_output,
        determinism=properties.ProjectIRDeterminismEvidence.UNKNOWN,
        error_behavior=properties.ProjectIRErrorBehaviorEvidence.UNKNOWN,
        side_effects=properties.ProjectIRSideEffectEvidence.UNKNOWN,
        evaluation_count=properties.ProjectIREvaluationCountEvidence.UNKNOWN,
    )
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=(order_output, limit_output),
        provided=(order_property, cardinality, retained_order),
        effects=(effect,),
    )
    kinds = (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        operators.ProjectIRLogicalOperatorKind.RELATION_ORDERING,
        operators.ProjectIRLogicalOperatorKind.LIMIT,
    )
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=fact,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )
    transfers = (
        operators.ProjectIREstablishedPropertyTransfer(
            operator=operator_occurrences[2],
            output_property=order_property,
        ),
        operators.ProjectIREstablishedPropertyTransfer(
            operator=operator_occurrences[3],
            output_property=cardinality,
        ),
        operators.ProjectIRPreservedPropertyTransfer(
            operator=operator_occurrences[3],
            input_property=order_property,
            output_property=retained_order,
        ),
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
        transfers=transfers,
    )
    assert tuple(item.direction for item in order_property.items) == ("desc",)
    assert cardinality.upper_bound == 3
    assert logical.effects is property_stage.effects
    assert logical.estimates is property_stage.estimates
    assert logical.estimates.statistics == ()


def _compatibility_stage(
    semantic: ProjectSemanticResult,
) -> tuple[
    operators.ProjectIRLogicalOperatorStage,
    operators.ProjectIRRowShapeCompatibility,
    properties.ProjectIRRequiredRowShape,
]:
    filtered = _fact(semantic, "filtered")
    consumer = _fact(semantic, "consumer")
    filtered_shape = _row_shape(semantic, filtered)
    consumer_shape = _row_shape(semantic, consumer)
    consumer_anchor = consumer_shape.relation
    scope = project_ir.ProjectIRSnapshotScope()
    filtered_nodes = tuple(
        _node(scope, position, filtered_shape.relation) for position in range(3)
    )
    consumer_nodes = tuple(
        _node(scope, position + 3, consumer_anchor) for position in range(2)
    )
    nodes = (*filtered_nodes, *consumer_nodes)
    filtered_occurrence, filtered_output = _relation_output(
        scope,
        0,
        filtered_nodes[-1],
        filtered_shape,
    )
    consumer_occurrence, consumer_output = _relation_output(
        scope,
        1,
        consumer_nodes[-1],
        consumer_shape,
    )
    input_slot = project_ir.ProjectIRInputSlotOccurrence(
        ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=0),
        consumer=consumer_nodes[0],
        input_ordinal=0,
    )
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    dependency = next(
        item
        for item in attribution.dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.reference.owner == consumer_anchor.identity
        and item.target_declaration == filtered_shape.relation.identity
    )
    assert consumer.resolution is not None
    authority = project_ir.ProjectIRResolvedRelationAnchor(
        resolution=consumer.resolution,
        dependency=dependency,
    )
    use = project_ir.ProjectIRUseOccurrence(
        ref=project_ir.ProjectIRUseRef(scope=scope, position=0),
        output=filtered_occurrence,
        slot=input_slot,
        role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
        source_order=0,
        anchor=authority,
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=(filtered_occurrence, consumer_occurrence),
        input_slots=(input_slot,),
        uses=(use,),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=filtered_shape.relation,
                evidence=filtered,
                root=filtered_nodes[-1],
            ),
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=consumer_anchor,
                evidence=consumer,
                root=consumer_nodes[-1],
            ),
        ),
    )
    provided = properties.ProjectIRProvidedOutputShape(output=filtered_output)
    required = properties.ProjectIRRequiredRowShape(
        input_slot=input_slot,
        row_shape=filtered_shape,
        authority=authority,
    )
    property_stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=(filtered_output, consumer_output),
        provided=(provided,),
        required=(required,),
    )
    kinds = (
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.ROW_FILTER,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        operators.ProjectIRLogicalOperatorKind.RELATION_INPUT,
        operators.ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
    )
    evidences = (filtered, filtered, filtered, consumer, consumer)
    operator_occurrences = tuple(
        operators.ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=evidence,
        )
        for node, kind, evidence in zip(nodes, kinds, evidences, strict=True)
    )
    compatibility = operators.ProjectIRRowShapeCompatibility(
        provided=provided,
        required=required,
    )
    logical = operators.ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operator_occurrences,
        transfers=(
            operators.ProjectIREstablishedPropertyTransfer(
                operator=operator_occurrences[2],
                output_property=provided,
            ),
        ),
        compatibilities=(compatibility,),
    )
    return logical, compatibility, required


def test_row_shape_compatibility_is_exact_consumer_side_and_fail_closed(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    logical, compatibility, required = _compatibility_stage(semantic)
    assert compatibility.satisfied
    assert (
        compatibility.status is operators.ProjectIRRowShapeCompatibilityStatus.SATISFIED
    )
    detached_shape = replace(
        required.row_shape,
        evidence=replace(required.row_shape.evidence),
    )
    detached_required = replace(required, row_shape=detached_shape)
    mismatch = operators.ProjectIRRowShapeCompatibility(
        provided=compatibility.provided,
        required=detached_required,
    )
    assert not mismatch.satisfied
    assert mismatch.status is (
        operators.ProjectIRRowShapeCompatibilityStatus.NOT_SATISFIED
    )
    assert logical.compatibilities == (compatibility,)
    with pytest.raises(ValueError, match="one exact compatibility result"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=logical.property_stage,
            operators=logical.operators,
            transfers=logical.transfers,
        )
    assert not hasattr(logical, "provider_search")


def test_operator_stage_rejects_foreign_duplicate_missing_and_wrong_order(
    tmp_path: Path,
) -> None:
    fact = _fact(_semantic_project(tmp_path), "full")
    pipeline = _empty_pipeline(fact, tuple(operators.ProjectIRLogicalOperatorKind))
    original = pipeline.operator_occurrences
    duplicate = replace(original[1], node=original[0].node)
    with pytest.raises(ValueError, match="cannot select an operator winner"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=pipeline.property_stage,
            operators=(original[0], duplicate, *original[2:]),
        )
    with pytest.raises(ValueError, match="every structural node"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=pipeline.property_stage,
            operators=original[:-1],
        )
    wrong_order = (
        replace(original[0], kind=operators.ProjectIRLogicalOperatorKind.ROW_FILTER),
        replace(
            original[1], kind=operators.ProjectIRLogicalOperatorKind.RELATION_INPUT
        ),
        *original[2:],
    )
    with pytest.raises(ValueError, match="exact stage order"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=pipeline.property_stage,
            operators=wrong_order,
        )
    foreign_scope = project_ir.ProjectIRSnapshotScope()
    foreign_node = _node(foreign_scope, 0, original[0].node.anchor)
    foreign = replace(original[0], node=foreign_node)
    with pytest.raises(ValueError, match="every structural node"):
        operators.ProjectIRLogicalOperatorStage(
            property_stage=pipeline.property_stage,
            operators=(foreign, *original[1:]),
        )
    assert tuple(pipeline.logical_stage.structural.nodes) == tuple(
        pipeline.structural.nodes
    )
    assert pipeline.logical_stage.property_stage is pipeline.property_stage
    with pytest.raises(FrozenInstanceError):
        pipeline.logical_stage.operators = ()  # type: ignore[misc]


def test_logical_formation_is_hash_seed_and_cwd_independent(tmp_path: Path) -> None:
    script = """
from pietto._project.project_ir import ProjectIRSnapshotScope, ProjectIRStructuralStage
from pietto._project.project_ir_properties import ProjectIREstimateBoundary, ProjectIRPropertyStage
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorStage
scope = ProjectIRSnapshotScope()
structural = ProjectIRStructuralStage(scope=scope)
properties = ProjectIRPropertyStage(
    structural=structural,
    estimates=ProjectIREstimateBoundary(scope=scope),
)
print(repr(ProjectIRLogicalOperatorStage(property_stage=properties)))
"""
    outputs = []
    for seed, directory in (("1", tmp_path / "first"), ("999", tmp_path / "second")):
        directory.mkdir()
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            (sys.executable, "-c", script),
            cwd=directory,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]
    assert "0x" not in outputs[0]


def test_private_public_sql_and_script_relation_ir_remain_unchanged() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "build_project_ir",
        "allocate_ref",
        "optimizer",
        "cost_model",
        "canonical_bytes",
        "to_json",
        "from_json",
        "JoinOperator",
        "NestedOutput",
    ):
        assert forbidden not in source
    assert not hasattr(pietto, "ProjectIRLogicalOperatorStage")
    assert not hasattr(project_package, "ProjectIRLogicalOperatorStage")
    public_readers = (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        REPO_ROOT / "src/pietto/ir/model.py",
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
        *(REPO_ROOT / "src/pietto/_project_explain").glob("*.py"),
    )
    assert all(
        "pietto._project.project_ir_operators" not in path.read_text(encoding="utf-8")
        for path in public_readers
    )
    assert tuple(
        item.name for item in fields(project_ir.ProjectIRPlanNodeOccurrence)
    ) == (
        "ref",
        "anchor",
    )
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
