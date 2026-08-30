from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto
import pietto._project as project_package
import pietto._project.project_ir as project_ir
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyKind,
    ProjectModuleReferenceRole,
)
from pietto._project.module_catalog import ProjectNominalDeclarationIdentity
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssueStatus,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_ir.py"
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Snapshot Scope And Typed Ref Domains",
    "Exact Relation Resolution And Field Anchors",
    "Explicit Structural Stage",
    "Plan Output Use And Input-slot Occurrences",
    "Construction-state Sum Boundary",
    "Determinism Immutability And Privacy",
    "Focused Assurance Contract",
    "Integration Boundary And Non-goals",
    "Slice 3 Handoff",
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


def _semantic_project(root: Path, source: str) -> ProjectSemanticResult:
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, source)
    )
    assert parse_result.ok
    return build_empty_project_semantic_result(parse_result)


def _fact_set(semantic: ProjectSemanticResult) -> ProjectModuleSemanticFactSet:
    result = semantic.module_semantic_facts
    assert result is not None
    return result


def _relation_fact(
    semantic: ProjectSemanticResult,
    name: str,
) -> ProjectModuleRelationSemanticFacts:
    matches = tuple(
        fact
        for environment in _fact_set(semantic).environments
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


def _identity(
    *,
    name: str,
    module_position: int = 0,
    declaration_position: int = 0,
    kind: ProjectSymbolKind = ProjectSymbolKind.QUERY,
) -> ProjectDeclarationOccurrenceIdentity:
    return ProjectDeclarationOccurrenceIdentity(
        identity=ProjectNominalDeclarationIdentity(
            module_path="main.pietto",
            namespace=ProjectSymbolNamespace.RELATION,
            declaration_kind=kind,
            declared_name=name,
        ),
        module_position=module_position,
        declaration_position=declaration_position,
    )


def _base_source() -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query first:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount\n"
        "query result:\n"
        "    from first\n"
        "    select:\n"
        "        first_id = id\n"
        "        second_id = id\n"
    )


def test_controlling_contract_locks_scope_laws_zero_delta_and_handoff() -> None:
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
        "Project IR snapshot scope + explicit structural stage boundary + typed "
        "plan/output/use/input-slot occurrence domains + exact relation/field "
        "anchor seams + typed relation construction states",
        "6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2",
        "c82cfb9e4c5ab7549619b6c1505be6d2fad6bd71",
        "33303992201",
        "A3/M4/D0",
        "same local position under two scope objects is unequal",
        "not a domain enum plus one generic ref",
        "free_outer_bindings = ()",
        "ProjectIROutputValueOccurrence -> ProjectIRUseOccurrence -> "
        "ProjectIRInputSlotOccurrence",
        "The input ordinal is owned only by `ProjectIRInputSlotOccurrence`",
        "CONCRETE UNKNOWN DEFERRED BLOCKED AMBIGUOUS",
        "No `UnknownPlanNode`, `DeferredPlanNode`, `BlockedPlanNode`, or "
        "`AmbiguousPlanNode` exists",
        "No authored project automatically produces any Slice 2 carrier",
        "Slice 5 owns canonical construction",
        "Phase 61 Slice 3 — Row/Output Model, Provided/Required Properties, "
        "Effects, And Estimate Boundary",
        "Add Phase 61 Project IR structural model",
        "PASS — PHASE61_SLICE2_PROJECT_IR_SCOPE_STAGES_OCCURRENCES_ANCHORS_"
        "CONSTRUCTION_STATES_END_TO_END",
        "Slice 3 remains next / unstarted and is not authorized here",
    ):
        assert evidence in normalized


def test_private_carrier_inventory_is_frozen_slotted_and_stage_specific() -> None:
    assert project_ir.__all__ == ()
    assert tuple(project_ir.ProjectIRRelationConstructionState) == (
        project_ir.ProjectIRRelationConstructionState.CONCRETE,
        project_ir.ProjectIRRelationConstructionState.UNKNOWN,
        project_ir.ProjectIRRelationConstructionState.DEFERRED,
        project_ir.ProjectIRRelationConstructionState.BLOCKED,
        project_ir.ProjectIRRelationConstructionState.AMBIGUOUS,
    )
    expected_fields = {
        project_ir.ProjectIRSnapshotScope: (),
        project_ir.ProjectIRPlanNodeRef: ("scope", "position"),
        project_ir.ProjectIROutputValueRef: ("scope", "position"),
        project_ir.ProjectIRUseRef: ("scope", "position"),
        project_ir.ProjectIRInputSlotRef: ("scope", "position"),
        project_ir.ProjectIRRelationAnchor: ("identity",),
        project_ir.ProjectIRResolvedRelationAnchor: (
            "resolution",
            "dependency",
            "reference",
            "target",
        ),
        project_ir.ProjectIRFieldAnchor: ("identity",),
        project_ir.ProjectIRResolvedFieldAnchor: (
            "dependency",
            "reference",
            "target",
        ),
        project_ir.ProjectIRPlanNodeOccurrence: ("ref", "anchor"),
        project_ir.ProjectIROutputValueOccurrence: (
            "ref",
            "producer",
            "anchor",
        ),
        project_ir.ProjectIRInputSlotOccurrence: (
            "ref",
            "consumer",
            "input_ordinal",
        ),
        project_ir.ProjectIRUseOccurrence: (
            "ref",
            "output",
            "slot",
            "role",
            "source_order",
            "anchor",
        ),
        project_ir.ProjectIRConcreteRelationSubject: (
            "anchor",
            "evidence",
            "root",
        ),
        project_ir.ProjectIRNonConcreteRelationSubject: (
            "anchor",
            "state",
            "evidence",
        ),
        project_ir.ProjectIRStructuralStage: (
            "scope",
            "nodes",
            "outputs",
            "input_slots",
            "uses",
            "subjects",
        ),
    }
    for carrier, names in expected_fields.items():
        assert tuple(item.name for item in fields(carrier)) == names
        assert "__dict__" not in carrier.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )

    scope = project_ir.ProjectIRSnapshotScope()
    assert repr(scope) == "ProjectIRSnapshotScope()"
    assert "0x" not in repr(scope)
    node_ref = project_ir.ProjectIRPlanNodeRef(scope=scope, position=0)
    with pytest.raises(FrozenInstanceError):
        node_ref.position = 1  # type: ignore[misc]


def test_snapshot_scope_and_nominal_ref_domains_are_exact() -> None:
    first = project_ir.ProjectIRSnapshotScope()
    second = project_ir.ProjectIRSnapshotScope()
    first_node = project_ir.ProjectIRPlanNodeRef(scope=first, position=0)
    second_node = project_ir.ProjectIRPlanNodeRef(scope=second, position=0)
    assert first_node != second_node
    assert first is not second

    refs = (
        first_node,
        project_ir.ProjectIROutputValueRef(scope=first, position=0),
        project_ir.ProjectIRUseRef(scope=first, position=0),
        project_ir.ProjectIRInputSlotRef(scope=first, position=0),
    )
    assert len({type(item) for item in refs}) == 4
    assert all(
        left != right
        for left in refs
        for right in refs
        if type(left) is not type(right)
    )

    with pytest.raises(TypeError, match="non-negative integer"):
        project_ir.ProjectIRPlanNodeRef(scope=first, position=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact snapshot scope"):
        project_ir.ProjectIRPlanNodeRef(scope=object(), position=0)  # type: ignore[arg-type]


def test_relation_resolution_and_field_anchors_wrap_exact_existing_identities(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _base_source())
    first = _relation_fact(semantic, "first")
    result = _relation_fact(semantic, "result")
    first_anchor = _relation_anchor(first)
    result_anchor = _relation_anchor(result)
    assert first_anchor.identity.identity.declared_name == "first"
    assert result_anchor.identity.identity.declared_name == "result"

    resolution = result.resolution
    assert resolution is not None
    dependencies = semantic.module_attribution_facts
    assert dependencies is not None
    relation_dependency = next(
        item
        for item in dependencies.dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.reference.owner == result_anchor.identity
    )
    resolved_anchor = project_ir.ProjectIRResolvedRelationAnchor(
        resolution=resolution,
        dependency=relation_dependency,
    )
    assert resolved_anchor.reference.role is ProjectModuleReferenceRole.RELATION_FROM
    assert resolved_anchor.reference.owner == result_anchor.identity
    assert resolved_anchor.target == first_anchor.identity

    attribution = semantic.module_attribution_facts
    assert attribution is not None
    lineage = attribution.find_row_lineage(first_anchor.identity)
    assert len(lineage) == 1 and lineage[0].fields
    field_identity = lineage[0].fields[0].field
    field_anchor = project_ir.ProjectIRFieldAnchor(identity=field_identity)
    assert field_anchor.identity is field_identity
    assert field_anchor.identity.owner == first_anchor.identity
    field_dependency = next(
        item
        for item in dependencies.dependencies
        if item.kind is ProjectModuleDependencyKind.ROW_FIELD_REFERENCE
        and item.target_row_field == field_identity
        and item.reference.owner == result_anchor.identity
    )
    resolved_field = project_ir.ProjectIRResolvedFieldAnchor(
        dependency=field_dependency
    )
    assert resolved_field.reference is field_dependency.reference
    assert resolved_field.target is field_identity
    assert resolved_field.dependency.origin_path is not None

    shape_identity = next(
        item.identity
        for item in attribution.declarations
        if item.identity.identity.declaration_kind is ProjectSymbolKind.SHAPE
    )
    with pytest.raises(ValueError, match="relation declaration"):
        project_ir.ProjectIRRelationAnchor(identity=shape_identity)
    with pytest.raises(TypeError, match="row field identity"):
        project_ir.ProjectIRFieldAnchor(identity="id")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="dependency provenance"):
        project_ir.ProjectIRResolvedFieldAnchor(dependency=relation_dependency)


def test_foreign_scope_and_domain_composition_fail_closed() -> None:
    first = project_ir.ProjectIRSnapshotScope()
    second = project_ir.ProjectIRSnapshotScope()
    relation = project_ir.ProjectIRRelationAnchor(identity=_identity(name="result"))
    node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=first, position=0),
        anchor=relation,
    )
    with pytest.raises(TypeError, match="plan-node ref"):
        project_ir.ProjectIRPlanNodeOccurrence(
            ref=project_ir.ProjectIROutputValueRef(scope=first, position=0),  # type: ignore[arg-type]
            anchor=relation,
        )
    with pytest.raises(ValueError, match="same snapshot scope"):
        project_ir.ProjectIROutputValueOccurrence(
            ref=project_ir.ProjectIROutputValueRef(scope=second, position=0),
            producer=node,
            anchor=relation,
        )


def test_repeated_field_uses_retain_role_source_order_and_slot_ordinal(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _base_source())
    first_anchor = _relation_anchor(_relation_fact(semantic, "first"))
    result_anchor = _relation_anchor(_relation_fact(semantic, "result"))
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    field_identity = (
        attribution.find_row_lineage(first_anchor.identity)[0].fields[0].field
    )
    field_anchor = project_ir.ProjectIRFieldAnchor(identity=field_identity)
    field_dependencies = tuple(
        item
        for item in attribution.dependencies
        if item.kind is ProjectModuleDependencyKind.ROW_FIELD_REFERENCE
        and item.target_row_field == field_identity
        and item.reference.owner == result_anchor.identity
    )
    assert len(field_dependencies) == 2
    resolved_fields = tuple(
        project_ir.ProjectIRResolvedFieldAnchor(dependency=item)
        for item in field_dependencies
    )
    scope = project_ir.ProjectIRSnapshotScope()
    producer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=first_anchor,
    )
    consumer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=1),
        anchor=result_anchor,
    )
    output = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=0),
        producer=producer,
        anchor=field_anchor,
    )
    slots = tuple(
        project_ir.ProjectIRInputSlotOccurrence(
            ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=ordinal),
            consumer=consumer,
            input_ordinal=ordinal,
        )
        for ordinal in range(2)
    )
    uses = tuple(
        project_ir.ProjectIRUseOccurrence(
            ref=project_ir.ProjectIRUseRef(scope=scope, position=ordinal),
            output=output,
            slot=slots[ordinal],
            role=ProjectModuleFactOccurrenceRole.SELECT_VALUE,
            source_order=ordinal,
            anchor=resolved_fields[ordinal],
        )
        for ordinal in range(2)
    )
    assert uses[0] != uses[1]
    assert uses[0].output is uses[1].output is output
    assert tuple(item.input_ordinal for item in uses) == (0, 1)
    assert tuple(item.source_order for item in uses) == (0, 1)
    assert all(
        item.role is ProjectModuleFactOccurrenceRole.SELECT_VALUE for item in uses
    )

    stage = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(producer, consumer),
        outputs=(output,),
        input_slots=slots,
        uses=uses,
    )
    assert stage.uses == uses
    assert stage.free_outer_bindings == ()
    assert uses[0].anchor.reference != uses[1].anchor.reference
    assert uses[0].anchor.target == uses[1].anchor.target == field_identity
    assert all(item.anchor.dependency.origin_path is not None for item in uses)

    with pytest.raises(ValueError, match="input ordinals"):
        project_ir.ProjectIRStructuralStage(
            scope=scope,
            nodes=(producer, consumer),
            outputs=(output,),
            input_slots=(slots[0], replace(slots[1], input_ordinal=0)),
        )
    with pytest.raises(ValueError, match="cannot select a use winner"):
        project_ir.ProjectIRStructuralStage(
            scope=scope,
            nodes=(producer, consumer),
            outputs=(output,),
            input_slots=slots,
            uses=(uses[0], replace(uses[1], slot=slots[0])),
        )
    with pytest.raises(ValueError, match="source order"):
        project_ir.ProjectIRStructuralStage(
            scope=scope,
            nodes=(producer, consumer),
            outputs=(output,),
            input_slots=slots,
            uses=(uses[0], replace(uses[1], source_order=0)),
        )


def test_relation_dependency_composes_output_use_and_consumer_slot(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _base_source())
    first = _relation_fact(semantic, "first")
    result = _relation_fact(semantic, "result")
    first_anchor = _relation_anchor(first)
    result_anchor = _relation_anchor(result)
    assert result.resolution is not None
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    relation_dependency = next(
        item
        for item in attribution.dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.reference.owner == result_anchor.identity
    )
    resolution_anchor = project_ir.ProjectIRResolvedRelationAnchor(
        resolution=result.resolution,
        dependency=relation_dependency,
    )
    scope = project_ir.ProjectIRSnapshotScope()
    producer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=first_anchor,
    )
    consumer = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=1),
        anchor=result_anchor,
    )
    output = project_ir.ProjectIROutputValueOccurrence(
        ref=project_ir.ProjectIROutputValueRef(scope=scope, position=0),
        producer=producer,
        anchor=first_anchor,
    )
    slot = project_ir.ProjectIRInputSlotOccurrence(
        ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=0),
        consumer=consumer,
        input_ordinal=0,
    )
    use = project_ir.ProjectIRUseOccurrence(
        ref=project_ir.ProjectIRUseRef(scope=scope, position=0),
        output=output,
        slot=slot,
        role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
        source_order=0,
        anchor=resolution_anchor,
    )
    assert use.output is output
    assert use.slot is slot
    assert use.input_ordinal == 0
    assert type(use.anchor) is project_ir.ProjectIRResolvedRelationAnchor
    assert use.anchor.target == first_anchor.identity
    assert use.anchor.reference.owner == result_anchor.identity
    assert use.anchor.dependency.origin_path is not None

    with pytest.raises(ValueError, match="RELATION_INPUT"):
        project_ir.ProjectIRUseOccurrence(
            ref=project_ir.ProjectIRUseRef(scope=scope, position=1),
            output=output,
            slot=slot,
            role=ProjectModuleFactOccurrenceRole.SELECT_VALUE,
            source_order=1,
            anchor=resolution_anchor,
        )


def test_structural_stage_rejects_duplicate_or_reordered_local_coordinates() -> None:
    scope = project_ir.ProjectIRSnapshotScope()
    anchor = project_ir.ProjectIRRelationAnchor(identity=_identity(name="result"))
    node = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=anchor,
    )
    duplicate = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=anchor,
    )
    with pytest.raises(ValueError, match="plan-node coordinates"):
        project_ir.ProjectIRStructuralStage(scope=scope, nodes=(node, duplicate))

    same_semantics_later_occurrence = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=1),
        anchor=project_ir.ProjectIRRelationAnchor(
            identity=_identity(name="result", declaration_position=1)
        ),
    )
    retained = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(node, same_semantics_later_occurrence),
    )
    assert retained.nodes == (node, same_semantics_later_occurrence)
    with pytest.raises(ValueError, match="plan-node coordinates"):
        project_ir.ProjectIRStructuralStage(
            scope=scope,
            nodes=(same_semantics_later_occurrence, node),
        )


def test_concrete_and_typed_non_concrete_subjects_prevent_mixed_states(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        _base_source()
        + 'source unknown is postgres.table("unknown")\n'
        + "query pending:\n    from unknown\n    select:\n        id\n",
    )
    first = _relation_fact(semantic, "first")
    pending = _relation_fact(semantic, "pending")
    assert first.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert pending.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    first_anchor = _relation_anchor(first)
    pending_anchor = _relation_anchor(pending)
    scope = project_ir.ProjectIRSnapshotScope()
    root = project_ir.ProjectIRPlanNodeOccurrence(
        ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=0),
        anchor=first_anchor,
    )
    concrete = project_ir.ProjectIRConcreteRelationSubject(
        anchor=first_anchor,
        evidence=first,
        root=root,
    )
    terminal = project_ir.ProjectIRNonConcreteRelationSubject(
        anchor=pending_anchor,
        state=project_ir.ProjectIRRelationConstructionState.UNKNOWN,
        evidence=pending,
    )
    assert concrete.state is project_ir.ProjectIRRelationConstructionState.CONCRETE
    assert terminal.state is project_ir.ProjectIRRelationConstructionState.UNKNOWN
    assert not hasattr(terminal, "root")
    assert not hasattr(terminal, "reason")
    with pytest.raises(ValueError, match="non-concrete state"):
        project_ir.ProjectIRNonConcreteRelationSubject(
            anchor=pending_anchor,
            state=project_ir.ProjectIRRelationConstructionState.CONCRETE,
            evidence=pending,
        )
    with pytest.raises(TypeError):
        inspect.signature(project_ir.ProjectIRNonConcreteRelationSubject).bind(
            anchor=pending_anchor,
            state=project_ir.ProjectIRRelationConstructionState.UNKNOWN,
            evidence=pending,
            root=root,
        )

    stage = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=(root,),
        subjects=(concrete, terminal),
    )
    assert stage.subjects == (concrete, terminal)
    for name in (
        "UnknownPlanNode",
        "DeferredPlanNode",
        "BlockedPlanNode",
        "AmbiguousPlanNode",
    ):
        assert not hasattr(project_ir, name)


def test_all_non_concrete_states_require_matching_exact_evidence(
    tmp_path: Path,
) -> None:
    unknown = _semantic_project(
        tmp_path / "unknown",
        'source unknown is postgres.table("unknown")\n'
        "query result:\n    from unknown\n    select:\n        id\n",
    )
    deferred = _semantic_project(
        tmp_path / "deferred",
        "shape Row:\n    amount: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "query pending:\n"
        "    from rows\n"
        "    select:\n"
        "        divided = amount / 2\n"
        "query result:\n"
        "    from pending\n"
        "    select:\n"
        "        divided\n",
    )
    blocked = _semantic_project(
        tmp_path / "blocked",
        "query result:\n    from missing\n    select:\n        id\n",
    )
    ambiguous = _semantic_project(
        tmp_path / "ambiguous",
        "shape Row:\n    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "query duplicate:\n    from rows\n    select:\n        id\n"
        "query duplicate:\n    from rows\n    select:\n        id\n"
        "query result:\n    from duplicate\n    select:\n        id\n",
    )
    evidence = (
        (
            project_ir.ProjectIRRelationConstructionState.UNKNOWN,
            _relation_fact(unknown, "result"),
        ),
        (
            project_ir.ProjectIRRelationConstructionState.DEFERRED,
            _relation_fact(deferred, "result"),
        ),
        (
            project_ir.ProjectIRRelationConstructionState.BLOCKED,
            _relation_fact(blocked, "result"),
        ),
    )
    assert tuple(item.state.status.value for _, item in evidence) == (
        "unknown",
        "deferred",
        "blocked",
    )
    for state, fact in evidence:
        terminal = project_ir.ProjectIRNonConcreteRelationSubject(
            anchor=_relation_anchor(fact),
            state=state,
            evidence=fact,
        )
        assert terminal.state is state

    duplicate_facts = tuple(
        fact
        for environment in _fact_set(ambiguous).environments
        for fact in environment.relation_facts
        if fact.owner.identity.declared_name == "duplicate"
    )
    assert len(duplicate_facts) == 2
    ambiguous_fact = duplicate_facts[0]
    issue = next(
        item
        for item in _fact_set(ambiguous).issues
        if item.status
        is ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME
        and ambiguous_fact.owner in item.occurrences
    )
    terminal = project_ir.ProjectIRNonConcreteRelationSubject(
        anchor=_relation_anchor(ambiguous_fact),
        state=project_ir.ProjectIRRelationConstructionState.AMBIGUOUS,
        evidence=issue,
    )
    assert terminal.state is project_ir.ProjectIRRelationConstructionState.AMBIGUOUS

    with pytest.raises(ValueError, match="does not support construction state"):
        project_ir.ProjectIRNonConcreteRelationSubject(
            anchor=_relation_anchor(evidence[0][1]),
            state=project_ir.ProjectIRRelationConstructionState.BLOCKED,
            evidence=evidence[0][1],
        )


def test_structural_repr_is_independent_of_hash_seed_and_ambient_cwd(
    tmp_path: Path,
) -> None:
    script = """
from pietto._project.model import ProjectSymbolKind, ProjectSymbolNamespace
from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.module_catalog import ProjectNominalDeclarationIdentity
from pietto._project.project_ir import (
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRSnapshotScope,
    ProjectIRStructuralStage,
)
scope = ProjectIRSnapshotScope()
anchor = ProjectIRRelationAnchor(identity=ProjectDeclarationOccurrenceIdentity(
    identity=ProjectNominalDeclarationIdentity(
        module_path="main.pietto",
        namespace=ProjectSymbolNamespace.RELATION,
        declaration_kind=ProjectSymbolKind.QUERY,
        declared_name="result",
    ),
    module_position=0,
    declaration_position=0,
))
node = ProjectIRPlanNodeOccurrence(
    ref=ProjectIRPlanNodeRef(scope=scope, position=0),
    anchor=anchor,
)
second_anchor = ProjectIRRelationAnchor(identity=ProjectDeclarationOccurrenceIdentity(
    identity=ProjectNominalDeclarationIdentity(
        module_path="main.pietto",
        namespace=ProjectSymbolNamespace.RELATION,
        declaration_kind=ProjectSymbolKind.QUERY,
        declared_name="result",
    ),
    module_position=0,
    declaration_position=1,
))
second = ProjectIRPlanNodeOccurrence(
    ref=ProjectIRPlanNodeRef(scope=scope, position=1),
    anchor=second_anchor,
)
print(repr(ProjectIRStructuralStage(scope=scope, nodes=(node, second))))
"""
    outputs: list[str] = []
    for ordinal, seed in enumerate(("1", "777")):
        cwd = tmp_path / str(ordinal)
        cwd.mkdir()
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            (sys.executable, "-c", script),
            cwd=cwd,
            env=environment,
            check=True,
            text=True,
            capture_output=True,
        )
        assert result.stderr == ""
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
    assert "0x" not in outputs[0]
    assert str(tmp_path) not in outputs[0]


def test_model_has_no_ambient_registry_operator_builder_or_public_projection() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported_roots & {"hashlib", "os", "pathlib", "random", "uuid"}
    assert not any(isinstance(node, ast.Global) for node in ast.walk(tree))
    for forbidden in (
        "RelationIR(",
        "ProjectModuleRelationSemanticFacts(",
        "operator_kind",
        "provided_properties",
        "required_properties",
        "estimated_cost",
        "canonical_bytes",
        "to_json",
        "from_json",
    ):
        assert forbidden not in source

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
        "pietto._project.project_ir" not in path.read_text(encoding="utf-8")
        for path in public_readers
    )
    assert not hasattr(pietto, "ProjectIRStructuralStage")
    assert not hasattr(project_package, "ProjectIRStructuralStage")
    assert "operator" not in {
        item.name for item in fields(project_ir.ProjectIRPlanNodeOccurrence)
    }
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
