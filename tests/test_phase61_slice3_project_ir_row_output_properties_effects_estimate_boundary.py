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
    / "docs/spec/phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_ir_properties.py"
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Live Semantic Authority Audit",
    "Current Row And Output Model",
    "Exact Provided Property Domain",
    "Required Consumer Input Properties",
    "Effect And Evaluation Evidence",
    "Strict Empty Estimate Boundary",
    "Property-stage Formation Laws",
    "Determinism Immutability And Privacy",
    "Focused Assurance Contract",
    "Integration Boundary And Non-goals",
    "Slice 4 Handoff",
    "Gate Lifecycle And Publication",
)


def _configured_project(root: Path, source: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")
    return root


def _semantic_project(root: Path) -> ProjectSemanticResult:
    source = (
        "shape Row:\n"
        "    status: Text not null\n"
        "    gross: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = status\n"
        "        total = sum(gross)\n"
        "    order by:\n"
        "        total desc\n"
        "        label asc\n"
        "    limit 5\n"
        "query result:\n"
        "    from grouped\n"
        "    select:\n"
        "        label\n"
        "        total\n"
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        rank = row_number() window:\n"
        "            order by:\n"
        "                gross\n"
    )
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, source)
    )
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _relation_fact(
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


def _relation_anchor(
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
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    relation = _relation_anchor(fact)
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


@dataclass(frozen=True, slots=True)
class _PropertyCase:
    semantic: ProjectSemanticResult
    grouped_fact: ProjectModuleRelationSemanticFacts
    structural: project_ir.ProjectIRStructuralStage
    outputs: tuple[properties.ProjectIRCurrentOutput, ...]
    relation_output: properties.ProjectIRRelationRowOutput
    scalar_outputs: tuple[properties.ProjectIRScalarFieldOutput, ...]
    input_slot: project_ir.ProjectIRInputSlotOccurrence
    required_authority: project_ir.ProjectIRResolvedRelationAnchor


def _property_case(tmp_path: Path) -> _PropertyCase:
    semantic = _semantic_project(tmp_path)
    grouped_fact = _relation_fact(semantic, "grouped")
    result_fact = _relation_fact(semantic, "result")
    row_shape = _row_shape(semantic, grouped_fact)
    result_anchor = _relation_anchor(result_fact)
    scope = project_ir.ProjectIRSnapshotScope()
    producer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=row_shape.relation,
    )
    consumer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=1),
        anchor=result_anchor,
    )
    relation_occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=0),
        producer=producer,
        anchor=row_shape.relation,
    )
    field_occurrences = tuple(
        project_ir.ProjectIROutputValueOccurrence(
            ref=project_ir.ProjectIROutputValueRef(
                scope=scope,
                position=position,
            ),
            producer=producer,
            anchor=item.anchor,
        )
        for position, item in enumerate(row_shape.fields, start=1)
    )
    input_slot = project_ir.ProjectIRInputSlotOccurrence(
        ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=0),
        consumer=consumer,
        input_ordinal=0,
    )
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    dependency = next(
        item
        for item in attribution.dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.reference.owner == result_anchor.identity
        and item.target_declaration == row_shape.relation.identity
    )
    assert result_fact.resolution is not None
    required_authority = project_ir.ProjectIRResolvedRelationAnchor(
        resolution=result_fact.resolution,
        dependency=dependency,
    )
    use = project_ir.ProjectIRUseOccurrence(
        ref=project_ir.ProjectIRUseRef(scope=scope, position=0),
        output=relation_occurrence,
        slot=input_slot,
        role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
        source_order=0,
        anchor=required_authority,
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(producer, consumer),
        outputs=(relation_occurrence, *field_occurrences),
        input_slots=(input_slot,),
        uses=(use,),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=row_shape.relation,
                evidence=grouped_fact,
                root=producer,
            ),
        ),
    )
    relation_output = properties.ProjectIRRelationRowOutput(
        occurrence=relation_occurrence,
        row_shape=row_shape,
    )
    scalar_outputs = tuple(
        properties.ProjectIRScalarFieldOutput(
            occurrence=occurrence,
            row_shape=row_shape,
            field=item,
        )
        for occurrence, item in zip(
            field_occurrences,
            row_shape.fields,
            strict=True,
        )
    )
    return _PropertyCase(
        semantic=semantic,
        grouped_fact=grouped_fact,
        structural=structural,
        outputs=(relation_output, *scalar_outputs),
        relation_output=relation_output,
        scalar_outputs=scalar_outputs,
        input_slot=input_slot,
        required_authority=required_authority,
    )


def _estimate(case: _PropertyCase) -> properties.ProjectIREstimateBoundary:
    return properties.ProjectIREstimateBoundary(scope=case.structural.scope)


def test_controlling_contract_locks_authority_domains_scope_and_handoff() -> None:
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
        "a9725d46b1c4c79d5e1c78d79a0e042522e1edd3",
        "ef4db5396f1a1ce436d003454d99f314c2cfcae1",
        "33305962868",
        "A3/M4/D0",
        "ProjectIRRowShape",
        "ProjectIRScalarFieldOutput",
        "ProjectIRRelationRowOutput",
        "BAG != SET",
        "ProvidedProperties != RequiredInputProperties",
        "unknown != false",
        "not-applicable != unknown",
        "window-local ordering != relation-result ordering",
        "effects != estimates",
        "Current estimate entries = 0",
        "Phase 61 Slice 4 — Current Logical Operator Algebra And Exact Property Transfer",
        "Add Phase 61 Project IR property model",
        "PASS — PHASE61_SLICE3_PROJECT_IR_ROW_OUTPUT_PROPERTIES_EFFECTS_"
        "ESTIMATE_BOUNDARY_END_TO_END",
        "Slice 4 remains next / unstarted",
    ):
        assert evidence in normalized


def test_private_carriers_are_frozen_slotted_keyword_only_and_non_speculative() -> None:
    carriers = (
        properties.ProjectIRRowField,
        properties.ProjectIRRowShape,
        properties.ProjectIRScalarFieldOutput,
        properties.ProjectIRRelationRowOutput,
        properties.ProjectIRProvidedOutputShape,
        properties.ProjectIRProvidedBagMultiplicity,
        properties.ProjectIRProvidedClosedBindings,
        properties.ProjectIRProvidedRelationOrdering,
        properties.ProjectIRProvidedLocalGrainEvidence,
        properties.ProjectIRProvidedCardinalityUpperBound,
        properties.ProjectIRProvidedEvaluationPolicy,
        properties.ProjectIRUnavailableProvidedProperty,
        properties.ProjectIRRequiredRowShape,
        properties.ProjectIREffectEvidence,
        properties.ProjectIREstimateBoundary,
        properties.ProjectIRPropertyStage,
    )
    for carrier in carriers:
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    assert properties.__all__ == ()
    estimate_field = next(
        item
        for item in fields(properties.ProjectIRPropertyStage)
        if item.name == "estimates"
    )
    assert estimate_field.compare is False
    for name in (
        "NestedRelationOutput",
        "RecordOutput",
        "CollectOutput",
        "ProjectIRLogicalOperator",
        "ProjectIRPropertyTransfer",
        "ProjectIREstimator",
    ):
        assert not hasattr(properties, name)


def test_exact_ordered_row_shape_retains_field_identity_type_and_occurrences(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    shape = case.relation_output.row_shape
    assert tuple(item.anchor.identity.field_position for item in shape.fields) == (0, 1)
    assert tuple(item.anchor.identity.name for item in shape.fields) == (
        "label",
        "total",
    )
    assert tuple(item.evidence.name for item in shape.fields) == ("label", "total")
    assert all(item.evidence.resolved_type is not None for item in shape.fields)

    scope = project_ir.ProjectIRSnapshotScope()
    node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=shape.relation,
    )
    occurrences = tuple(
        project_ir.ProjectIROutputValueOccurrence(
            ref=project_ir.ProjectIROutputValueRef(scope=scope, position=position),
            producer=node,
            anchor=shape.relation,
        )
        for position in range(2)
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(node,),
        outputs=occurrences,
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=shape.relation,
                evidence=shape.evidence,
                root=node,
            ),
        ),
    )
    outputs = tuple(
        properties.ProjectIRRelationRowOutput(
            occurrence=occurrence,
            row_shape=shape,
        )
        for occurrence in occurrences
    )
    stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=outputs,
    )
    assert len(stage.outputs) == 2
    assert stage.outputs[0] != stage.outputs[1]
    assert stage.outputs[0].row_shape == stage.outputs[1].row_shape  # type: ignore[union-attr]

    with pytest.raises(ValueError, match="exact source order"):
        properties.ProjectIRRowShape(
            relation=shape.relation,
            evidence=shape.evidence,
            fields=tuple(reversed(shape.fields)),
        )


def test_current_scalar_relation_outputs_and_bag_are_explicit_without_set_variant(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    provided = (
        properties.ProjectIRProvidedOutputShape(output=case.relation_output),
        properties.ProjectIRProvidedBagMultiplicity(output=case.relation_output),
        properties.ProjectIRProvidedClosedBindings(output=case.relation_output),
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
        provided=provided,
    )
    assert type(stage.outputs[0]) is properties.ProjectIRRelationRowOutput
    assert all(
        type(item) is properties.ProjectIRScalarFieldOutput
        for item in stage.outputs[1:]
    )
    assert type(stage.provided[1]) is properties.ProjectIRProvidedBagMultiplicity
    assert not any("Set" in name for name in vars(properties))
    assert properties.ProjectIRProvidedBagMultiplicity != properties.ProjectIRRowShape


def test_provided_and_required_domains_remain_separate_and_consumer_owned(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    provided = properties.ProjectIRProvidedOutputShape(output=case.relation_output)
    required = properties.ProjectIRRequiredRowShape(
        input_slot=case.input_slot,
        row_shape=case.relation_output.row_shape,
        authority=case.required_authority,
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
        provided=(provided,),
        required=(required,),
    )
    assert stage.required[0].input_slot.consumer is case.input_slot.consumer
    assert stage.required[0].authority.reference.owner == (
        case.input_slot.consumer.anchor.identity
    )
    assert not hasattr(stage, "satisfied_requirements")
    with pytest.raises(TypeError, match="invalid carrier"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=case.outputs,
            required=(provided,),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="invalid carrier"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=case.outputs,
            provided=(required,),  # type: ignore[arg-type]
        )


def test_unknown_not_applicable_and_exact_empty_never_collapse(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    unknown_cardinality = properties.ProjectIRUnavailableProvidedProperty(
        output=case.relation_output,
        property_slot=properties.ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS,
        availability=properties.ProjectIRPropertyAvailability.UNKNOWN,
    )
    unknown_domains = properties.ProjectIRUnavailableProvidedProperty(
        output=case.relation_output,
        property_slot=properties.ProjectIRProvidedPropertySlot.FACT_DOMAINS,
        availability=properties.ProjectIRPropertyAvailability.UNKNOWN,
    )
    closed = properties.ProjectIRProvidedClosedBindings(output=case.relation_output)
    not_applicable = properties.ProjectIRUnavailableProvidedProperty(
        output=case.relation_output,
        property_slot=properties.ProjectIRProvidedPropertySlot.NULL_EXTENSION,
        availability=properties.ProjectIRPropertyAvailability.NOT_APPLICABLE,
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
        provided=(unknown_cardinality, unknown_domains, closed, not_applicable),
    )
    assert unknown_cardinality.availability is not not_applicable.availability
    assert unknown_domains != closed
    assert closed.bindings == ()
    assert stage.free_outer_bindings == ()


def test_relation_ordering_and_local_grain_reuse_only_exact_current_evidence(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    ordering_evidence = tuple(
        item
        for item in case.grouped_fact.clause_dependencies
        if item.role is ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )
    grain_evidence = tuple(
        item
        for item in case.grouped_fact.clause_dependencies
        if item.role is ProjectModuleFactOccurrenceRole.GROUP_KEY
    )
    ordering = properties.ProjectIRProvidedRelationOrdering(
        output=case.relation_output,
        evidence=case.grouped_fact,
    )
    grain = properties.ProjectIRProvidedLocalGrainEvidence(
        output=case.relation_output,
        evidence=case.grouped_fact,
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
        provided=(ordering, grain),
    )
    assert tuple(item.direction for item in ordering.items) == ("desc", "asc")
    assert all(
        item is fact.source_occurrence
        for item, fact in zip(ordering.items, ordering_evidence, strict=True)
    )
    assert len(grain.occurrences) == 1
    assert all(
        item is fact.source_occurrence
        for item, fact in zip(grain.occurrences, grain_evidence, strict=True)
    )
    assert not hasattr(grain, "descriptor")
    assert not hasattr(grain, "compare")
    assert not hasattr(grain, "fanout")
    assert stage.provided == (ordering, grain)
    with pytest.raises(ValueError, match="exact semantic authority"):
        properties.ProjectIRProvidedRelationOrdering(
            output=case.relation_output,
            evidence=replace(case.grouped_fact),
        )

    ranked = _relation_fact(case.semantic, "ranked")
    window = ranked.window_outputs[0]
    window_project_fact = window.project_fact
    assert window_project_fact is not None
    assert window_project_fact.analysis.order_binding_fact.bindings
    with pytest.raises(TypeError, match="relation semantic evidence"):
        properties.ProjectIRProvidedRelationOrdering(
            output=case.relation_output,
            evidence=(window,),  # type: ignore[arg-type]
        )


def test_exact_cardinality_is_not_an_estimate_and_empty_estimates_are_legal(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    cardinality = properties.ProjectIRProvidedCardinalityUpperBound(
        output=case.relation_output,
        evidence=case.grouped_fact,
    )
    estimates = _estimate(case)
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=estimates,
        outputs=case.outputs,
        provided=(cardinality,),
    )
    assert cardinality.upper_bound == 5
    assert estimates.statistics == ()
    assert stage.estimates is estimates
    with pytest.raises(ValueError, match="no legitimate estimate producer"):
        properties.ProjectIREstimateBoundary(
            scope=case.structural.scope,
            statistics=(object(),),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="invalid carrier"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=estimates,
            outputs=case.outputs,
            provided=(estimates,),  # type: ignore[arg-type]
        )


def test_existing_window_policy_is_exact_but_window_order_is_not_result_order(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    ranked = _relation_fact(semantic, "ranked")
    shape = _row_shape(semantic, ranked)
    assert len(shape.fields) == 1
    scope = project_ir.ProjectIRSnapshotScope()
    node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=shape.relation,
    )
    occurrence = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=0),
        producer=node,
        anchor=shape.fields[0].anchor,
    )
    structural = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(node,),
        outputs=(occurrence,),
        subjects=(
            project_ir.ProjectIRConcreteRelationSubject(
                anchor=shape.relation,
                evidence=ranked,
                root=node,
            ),
        ),
    )
    output = properties.ProjectIRScalarFieldOutput(
        occurrence=occurrence,
        row_shape=shape,
        field=shape.fields[0],
    )
    window = ranked.window_outputs[0]
    policy = properties.ProjectIRProvidedEvaluationPolicy(
        output=output,
        evidence=window,
    )
    window_project_fact = window.project_fact
    assert window_project_fact is not None
    stage = properties.ProjectIRPropertyStage(
        structural=structural,
        estimates=properties.ProjectIREstimateBoundary(scope=scope),
        outputs=(output,),
        provided=(
            properties.ProjectIRProvidedOutputShape(output=output),
            policy,
        ),
    )
    assert (
        policy.policy
        is window_project_fact.analysis.validated_specification.function_policy
    )
    assert stage.provided[-1] is policy
    assert not any(
        type(item) is properties.ProjectIRProvidedRelationOrdering
        for item in stage.provided
    )


def test_effect_unknown_never_becomes_purity_and_does_not_change_identity(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    output_ref = case.relation_output.occurrence.ref
    effect = properties.ProjectIREffectEvidence(
        output=case.relation_output,
        determinism=properties.ProjectIRDeterminismEvidence.UNKNOWN,
        error_behavior=properties.ProjectIRErrorBehaviorEvidence.UNKNOWN,
        side_effects=properties.ProjectIRSideEffectEvidence.UNKNOWN,
        evaluation_count=properties.ProjectIREvaluationCountEvidence.UNKNOWN,
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
        effects=(effect,),
    )
    assert stage.effects[0].output.occurrence.ref is output_ref
    assert (
        effect.determinism is not properties.ProjectIRDeterminismEvidence.DETERMINISTIC
    )
    assert (
        effect.error_behavior
        is not properties.ProjectIRErrorBehaviorEvidence.CANNOT_ERROR
    )
    assert (
        effect.side_effects
        is not properties.ProjectIRSideEffectEvidence.SIDE_EFFECT_FREE
    )
    assert (
        effect.evaluation_count
        is not properties.ProjectIREvaluationCountEvidence.INSENSITIVE
    )
    with pytest.raises(ValueError, match="only unknown effect evidence"):
        properties.ProjectIREffectEvidence(
            output=case.relation_output,
            determinism=properties.ProjectIRDeterminismEvidence.DETERMINISTIC,
            error_behavior=properties.ProjectIRErrorBehaviorEvidence.UNKNOWN,
            side_effects=properties.ProjectIRSideEffectEvidence.UNKNOWN,
            evaluation_count=properties.ProjectIREvaluationCountEvidence.UNKNOWN,
        )


def test_property_stage_fails_closed_on_scope_missing_duplicate_and_reorder(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    with pytest.raises(ValueError, match="one snapshot scope"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=properties.ProjectIREstimateBoundary(
                scope=project_ir.ProjectIRSnapshotScope()
            ),
            outputs=case.outputs,
        )
    shape_property = properties.ProjectIRProvidedOutputShape(
        output=case.relation_output
    )
    with pytest.raises(ValueError, match="unique authority"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=case.outputs,
            provided=(shape_property, shape_property),
        )
    with pytest.raises(ValueError, match="structural output coordinates"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=tuple(reversed(case.outputs)),
        )
    detached_shape = replace(
        case.relation_output.row_shape,
        evidence=replace(case.grouped_fact),
    )
    detached_output = replace(case.relation_output, row_shape=detached_shape)
    with pytest.raises(ValueError, match="concrete subject authority"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=(detached_output, *case.scalar_outputs),
        )
    detached = replace(case.relation_output)
    with pytest.raises(ValueError, match="retained output occurrences"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=case.outputs,
            provided=(properties.ProjectIRProvidedOutputShape(output=detached),),
        )
    result_shape = _row_shape(case.semantic, _relation_fact(case.semantic, "result"))
    with pytest.raises(ValueError, match="belong to their relation"):
        properties.ProjectIRRowShape(
            relation=case.relation_output.row_shape.relation,
            evidence=case.grouped_fact,
            fields=result_shape.fields,
        )
    with pytest.raises(TypeError, match="exact tuple"):
        properties.ProjectIRPropertyStage(
            structural=case.structural,
            estimates=_estimate(case),
            outputs=list(case.outputs),  # type: ignore[arg-type]
        )


def test_property_composition_preserves_topology_and_is_hash_cwd_deterministic(
    tmp_path: Path,
) -> None:
    case = _property_case(tmp_path)
    topology = (
        case.structural.nodes,
        case.structural.outputs,
        case.structural.input_slots,
        case.structural.uses,
        case.structural.subjects,
    )
    stage = properties.ProjectIRPropertyStage(
        structural=case.structural,
        estimates=_estimate(case),
        outputs=case.outputs,
    )
    assert stage.structural is case.structural
    assert topology == (
        stage.structural.nodes,
        stage.structural.outputs,
        stage.structural.input_slots,
        stage.structural.uses,
        stage.structural.subjects,
    )
    with pytest.raises(FrozenInstanceError):
        stage.outputs = ()  # type: ignore[misc]

    script = """
from pietto._project.project_ir import ProjectIRSnapshotScope, ProjectIRStructuralStage
from pietto._project.project_ir_properties import ProjectIREstimateBoundary, ProjectIRPropertyStage
scope = ProjectIRSnapshotScope()
structural = ProjectIRStructuralStage(scope=scope)
stage = ProjectIRPropertyStage(
    structural=structural,
    estimates=ProjectIREstimateBoundary(scope=scope),
)
print(repr(stage))
"""
    outputs = []
    for seed, directory in (("1", tmp_path / "first"), ("777", tmp_path / "second")):
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


def test_private_public_sql_and_script_level_behavior_remain_unchanged() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "operator_kind",
        "transfer_properties",
        "build_project_ir",
        "estimated_row_count",
        "selectivity",
        "estimated_cost",
        "canonical_bytes",
        "to_json",
        "from_json",
    ):
        assert forbidden not in source
    assert not hasattr(pietto, "ProjectIRPropertyStage")
    assert not hasattr(project_package, "ProjectIRPropertyStage")
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
        "pietto._project.project_ir_properties" not in path.read_text(encoding="utf-8")
        for path in public_readers
    )
    assert tuple(item.name for item in fields(project_ir.ProjectIRStructuralStage)) == (
        "scope",
        "nodes",
        "outputs",
        "input_slots",
        "uses",
        "subjects",
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
