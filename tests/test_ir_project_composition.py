from __future__ import annotations

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
import pietto._project.project_ir_composition as composition
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_properties as properties
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Canonical Fragment Order And Allocation",
    "Exact Cross-relation Edge Authority",
    "Cross-boundary Row Requirement And Compatibility",
    "Project Structural DAG Sharing And Acyclicity",
    "Complete Concrete And Non-concrete Result",
    "Determinism Immutability And Privacy",
    "Focused Assurance",
    "Integration Boundaries And Non-goals",
    "Slice 7 Handoff",
    "Gate Lifecycle And Publication",
)


def _library_source() -> str:
    return """shape Row:
    id: Int not null
    amount: Int not null
source rows: Row is postgres.table("rows")
table projected:
    from rows
    select:
        id
        amount
export:
    table projected
"""


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    table Public as Input\n'
            "query final:\n"
            "    from consumer\n"
            "    select:\n"
            "        id\n"
            "query consumer:\n"
            "    from Input\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from Input\n"
            "    select:\n"
            "        id\n"
        ),
        "b.pietto": (
            'import "c.pietto":\n    table projected as Public\n'
            "export:\n"
            "    table Public\n"
        ),
        "c.pietto": _library_source(),
        "d.pietto": (
            "shape Other:\n"
            "    key: Int not null\n"
            'source other: Other is postgres.table("other")\n'
            "query other_result:\n"
            "    from other\n"
            "    select:\n"
            "        key\n"
        ),
    }


def _semantic_project(root: Path, files: dict[str, str]) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in files.items():
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _build_plan(
    semantic: ProjectSemanticResult,
    allocation: construction.ProjectIRAllocationState | None = None,
) -> composition.ProjectIRProjectPlan:
    fact_set = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert fact_set is not None and attribution is not None
    return composition.build_project_ir_project_plan(
        semantic_facts=fact_set,
        attribution=attribution,
        allocation=(
            construction.ProjectIRAllocationState(
                scope=project_ir.ProjectIRSnapshotScope()
            )
            if allocation is None
            else allocation
        ),
    )


def _fragment(
    plan: composition.ProjectIRProjectPlan,
    module_path: str,
    name: str,
) -> construction.ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in plan.fragments
        if fragment.semantic_facts.owner.identity.module_path == module_path
        and fragment.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def test_controlling_contract_locks_composition_authority_scope_and_handoff() -> None:
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
        "b9c9e38f809f911eb429e7284d377c2c205e548b",
        "4273b06c631db9e609d0915d3880bc6b4ea3aaa6",
        "33337635343",
        "A3/M5/D0",
        "dependency-ordered environments -> source-ordered relation facts",
        "semantic source order = exact owner/container-local evidence",
        "allocation order != topological order",
        "direct use occurrence = authority",
        "ProjectIRCrossRelationEdge",
        "ProjectIRProjectPlan",
        "Add Phase 61 Project IR composition DAG",
        "PASS — PHASE61_SLICE6_CROSS_MODULE_RELATION_COMPOSITION_ACYCLIC_"
        "PROJECT_PLAN_DAG_END_TO_END",
        "Phase 61 Slice 7 — Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority",
    ):
        assert evidence in normalized


def test_project_plan_carriers_are_private_frozen_and_fragments_follow_semantic_order(
    tmp_path: Path,
) -> None:
    for carrier in (
        composition.ProjectIRCrossRelationEdge,
        composition.ProjectIRProjectPlan,
    ):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    assert composition.__all__ == ()

    semantic = _semantic_project(tmp_path, _project_files())
    plan = _build_plan(semantic)
    facts = semantic.module_semantic_facts
    assert facts is not None
    canonical = tuple(
        fact
        for environment in facts.environments
        for fact in environment.relation_facts
    )
    assert tuple(fragment.semantic_facts for fragment in plan.fragments) == canonical
    assert all(
        fragment.snapshot_scope is plan.starting_allocation.scope
        for fragment in plan.fragments
    )
    assert all(
        fragment.logical_stage.effects is fragment.property_stage.effects
        and fragment.logical_stage.estimates is fragment.property_stage.estimates
        for fragment in plan.concrete_fragments
    )
    assert plan.attribution is semantic.module_attribution_facts
    with pytest.raises(FrozenInstanceError):
        plan.fragments = ()  # type: ignore[misc]

    expected_nodes = tuple(
        node for fragment in plan.fragments for node in fragment.structural_stage.nodes
    )
    assert len(plan.structural_stage.nodes) == len(expected_nodes)
    assert all(
        actual is expected
        for actual, expected in zip(
            plan.structural_stage.nodes,
            expected_nodes,
            strict=True,
        )
    )
    assert tuple(
        subject.anchor.identity for subject in plan.structural_stage.subjects
    ) == tuple(fragment.subject.anchor.identity for fragment in plan.fragments)
    assert tuple(identity.path for identity in facts.dependency_order)[:3] == (
        "c.pietto",
        "b.pietto",
        "a.pietto",
    )
    assert len(plan.fragments) > 1
    assert plan.fragments[0].subject.anchor.identity.module_position != (
        plan.fragments[-1].subject.anchor.identity.module_position
    )


def test_cross_edges_use_exact_resolution_dependency_root_output_and_owner_local_order(
    tmp_path: Path,
) -> None:
    plan = _build_plan(_semantic_project(tmp_path, _project_files()))
    pairs = tuple(
        (
            edge.producer.semantic_facts.owner.identity.declared_name,
            edge.consumer.semantic_facts.owner.identity.declared_name,
        )
        for edge in plan.cross_relation_edges
    )
    assert pairs == (
        ("rows", "projected"),
        ("consumer", "final"),
        ("projected", "consumer"),
        ("projected", "second"),
        ("other", "other_result"),
    )
    assert all(edge.use.source_order == 0 for edge in plan.cross_relation_edges)
    assert all(
        edge.use.role is ProjectModuleFactOccurrenceRole.RELATION_INPUT
        for edge in plan.cross_relation_edges
    )
    assert all(
        edge.use.output is edge.producer.root_relation_output.occurrence
        and edge.use.slot is edge.input_slot
        and edge.use.anchor is edge.authority
        for edge in plan.cross_relation_edges
    )
    assert all(
        edge.authority.dependency.origin_path is not None
        for edge in plan.cross_relation_edges
    )
    assert len(plan.cross_relation_edges) == len(
        tuple(
            fragment
            for fragment in plan.concrete_fragments
            if fragment.semantic_facts.owner.identity.declaration_kind.value
            in {"table", "query"}
        )
    )

    projected_edges = tuple(
        edge
        for edge in plan.cross_relation_edges
        if edge.producer.semantic_facts.owner.identity.declared_name == "projected"
    )
    assert len(projected_edges) == 2
    assert projected_edges[0].use is not projected_edges[1].use
    assert projected_edges[0].input_slot is not projected_edges[1].input_slot
    assert projected_edges[0].use.output is projected_edges[1].use.output
    assert not any(
        type(use) is project_ir.ProjectIRUseOccurrence
        and type(use.output.anchor) is project_ir.ProjectIRFieldAnchor
        for use in plan.structural_stage.uses
    )


def test_cross_boundary_row_requirement_is_exact_and_satisfied(tmp_path: Path) -> None:
    plan = _build_plan(_semantic_project(tmp_path, _project_files()))
    for edge in plan.cross_relation_edges:
        assert edge.compatibility.satisfied
        assert (
            edge.compatibility.status
            is operators.ProjectIRRowShapeCompatibilityStatus.SATISFIED
        )
        assert edge.provided_row_shape.output is edge.producer.root_relation_output
        assert edge.required_row_shape.input_slot is edge.input_slot
        assert edge.required_row_shape.authority is edge.authority
        assert (
            edge.required_row_shape.row_shape
            is edge.producer.root_relation_output.row_shape
        )
        input_operator = next(
            operator
            for operator in edge.consumer.logical_stage.operators
            if operator.kind is operators.ProjectIRLogicalOperatorKind.RELATION_INPUT
        )
        input_output = next(
            output
            for output in edge.consumer.property_stage.outputs
            if type(output) is properties.ProjectIRRelationRowOutput
            and output.occurrence.producer is input_operator.node
        )
        assert type(input_output.row_shape) is properties.ProjectIRStageRowShape
        assert (
            input_output.row_shape.checkpoint.kind
            is properties.ProjectIRStageRowCheckpointKind.INPUT
        )
        assert (
            input_output.row_shape.checkpoint.state
            is edge.producer.semantic_facts.state
        )
        assert (
            edge.consumer.semantic_facts.input_state
            is edge.producer.semantic_facts.state
        )
        assert not hasattr(edge, "required_ordering")
        assert not hasattr(edge, "required_grain")


def test_cross_allocation_appends_after_fragments_without_remapping_and_is_deterministic(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _project_files())
    start = construction.ProjectIRAllocationState(
        scope=project_ir.ProjectIRSnapshotScope(),
        next_plan_node_position=5,
        next_output_value_position=9,
        next_input_slot_position=4,
        next_use_position=4,
    )
    plan = _build_plan(semantic, start)
    repeat = _build_plan(semantic, start)
    last_fragment = plan.fragments[-1]
    assert plan.ending_allocation.next_plan_node_position == (
        last_fragment.ending_allocation.next_plan_node_position
    )
    assert plan.ending_allocation.next_output_value_position == (
        last_fragment.ending_allocation.next_output_value_position
    )
    assert plan.ending_allocation.next_input_slot_position == (
        last_fragment.ending_allocation.next_input_slot_position
        + len(plan.cross_relation_edges)
    )
    assert plan.ending_allocation.next_use_position == (
        last_fragment.ending_allocation.next_use_position
        + len(plan.cross_relation_edges)
    )
    assert tuple(
        edge.input_slot.ref.position for edge in plan.cross_relation_edges
    ) == tuple(
        range(
            last_fragment.ending_allocation.next_input_slot_position,
            plan.ending_allocation.next_input_slot_position,
        )
    )
    assert tuple(edge.use.ref.position for edge in plan.cross_relation_edges) == tuple(
        range(
            last_fragment.ending_allocation.next_use_position,
            plan.ending_allocation.next_use_position,
        )
    )
    assert tuple(edge.use.ref for edge in plan.cross_relation_edges) == tuple(
        edge.use.ref for edge in repeat.cross_relation_edges
    )
    assert tuple(fragment.subject.anchor for fragment in plan.fragments) == tuple(
        fragment.subject.anchor for fragment in repeat.fragments
    )

    forward = next(
        edge
        for edge in plan.cross_relation_edges
        if edge.consumer.semantic_facts.owner.identity.declared_name == "final"
    )
    assert forward.producer.root.ref.position > forward.input_slot.consumer.ref.position


def test_project_actual_use_graph_is_acyclic_and_does_not_trust_ref_order(
    tmp_path: Path,
) -> None:
    plan = _build_plan(_semantic_project(tmp_path, _project_files()))
    composition._require_acyclic(plan.structural_stage)
    assert any(
        edge.producer.root.ref.position > edge.input_slot.consumer.ref.position
        for edge in plan.cross_relation_edges
    )

    fragment = next(
        fragment
        for fragment in plan.concrete_fragments
        if len(fragment.logical_stage.operators) > 1
    )
    scope = project_ir.ProjectIRSnapshotScope()
    anchor = fragment.subject.anchor
    nodes = tuple(
        project_ir.ProjectIRPlanNodeOccurrence(
            ref=project_ir.ProjectIRPlanNodeRef(scope=scope, position=position),
            anchor=anchor,
        )
        for position in range(2)
    )
    outputs = tuple(
        project_ir.ProjectIROutputValueOccurrence(
            ref=project_ir.ProjectIROutputValueRef(scope=scope, position=position),
            producer=node,
            anchor=anchor,
        )
        for position, node in enumerate(nodes)
    )
    slots = tuple(
        project_ir.ProjectIRInputSlotOccurrence(
            ref=project_ir.ProjectIRInputSlotRef(scope=scope, position=position),
            consumer=nodes[1 - position],
            input_ordinal=0,
        )
        for position in range(2)
    )
    uses = tuple(
        project_ir.ProjectIROperatorFlowUseOccurrence(
            ref=project_ir.ProjectIRUseRef(scope=scope, position=position),
            output=output,
            slot=slot,
        )
        for position, (output, slot) in enumerate(zip(outputs, slots, strict=True))
    )
    cyclic = project_ir.ProjectIRStructuralStage(
        scope=scope,
        nodes=nodes,
        outputs=outputs,
        input_slots=slots,
        uses=uses,
    )
    with pytest.raises(ValueError, match="must be acyclic"):
        composition._require_acyclic(cyclic)


def test_owner_local_source_order_rejects_wrong_value_without_global_renumbering(
    tmp_path: Path,
) -> None:
    plan = _build_plan(_semantic_project(tmp_path, _project_files()))
    semantic_uses = tuple(
        use
        for use in plan.structural_stage.uses
        if type(use) is project_ir.ProjectIRUseOccurrence
    )
    assert len(semantic_uses) > 1
    assert {use.source_order for use in semantic_uses} == {0}
    wrong = replace(semantic_uses[0], source_order=1)
    uses = tuple(
        wrong if use is semantic_uses[0] else use for use in plan.structural_stage.uses
    )
    with pytest.raises(ValueError, match="source order"):
        replace(plan.structural_stage, uses=uses)


def test_non_concrete_cycles_remain_terminals_and_do_not_erase_concrete_component(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n"
                "    id: Int not null\n"
                'source rows: Row is postgres.table("rows")\n'
                "query okay:\n"
                "    from rows\n"
                "    select:\n"
                "        id\n"
                "query a:\n"
                "    from b\n"
                "    select:\n"
                "        id\n"
                "query b:\n"
                "    from a\n"
                "    select:\n"
                "        id\n"
            )
        },
    )
    plan = _build_plan(semantic)
    assert tuple(
        fragment.semantic_facts.owner.identity.declared_name
        for fragment in plan.non_concrete_fragments
    ) == ("a", "b")
    assert all(
        fragment.structural_stage.nodes == ()
        for fragment in plan.non_concrete_fragments
    )
    assert tuple(
        edge.consumer.semantic_facts.owner.identity.declared_name
        for edge in plan.cross_relation_edges
    ) == ("okay",)
    assert {
        fragment.semantic_facts.owner.identity.declared_name
        for fragment in plan.concrete_fragments
    } == {
        "rows",
        "okay",
    }
    composition._require_acyclic(plan.structural_stage)


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
facts = semantic.module_semantic_facts
attribution = semantic.module_attribution_facts
assert facts is not None and attribution is not None
plan = build_project_ir_project_plan(semantic_facts=facts, attribution=attribution, allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()))
print((tuple((fragment.semantic_facts.owner.identity.module_path, fragment.semantic_facts.owner.identity.declared_name) for fragment in plan.fragments), tuple((edge.producer.semantic_facts.owner.identity.declared_name, edge.consumer.semantic_facts.owner.identity.declared_name, edge.use.ref.position, edge.use.source_order) for edge in plan.cross_relation_edges), plan.ending_allocation.next_plan_node_position, plan.ending_allocation.next_use_position))
"""


def test_project_composition_is_hash_seed_cwd_independent_and_public_sql_zero_delta(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root, _project_files())
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("313", "cwd-b")):
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

    assert not hasattr(pietto, "ProjectIRProjectPlan")
    assert not hasattr(project_package, "ProjectIRProjectPlan")
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
        assert "project_ir_composition" not in text
        assert "ProjectIRProjectPlan" not in text
