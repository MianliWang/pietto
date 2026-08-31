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
import pietto._project.project_ir_construction as construction
import pietto._project.project_ir_inspection as inspection
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_pipeline as pipeline
import pietto._project.project_ir_verification as verification
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Real-authored Semantic Entry And Exact Roots",
    "Explicit Allocation And One-way Pipeline",
    "Mandatory Independent Verification",
    "Complete E2E Result And Authority Continuity",
    "Real Multi-module Assurance Corpus",
    "Mixed Concrete And Non-concrete Project",
    "Canonical Observation And Bounded Determinism",
    "Privacy Compatibility And Non-goals",
    "Focused Assurance",
    "Slice 11 Handoff",
    "Gate Lifecycle And Publication",
)


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
            "query full:\n"
            "    from Input\n"
            "    let:\n"
            "        floor = 0\n"
            "    where id > floor\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(amount)\n"
            "        ranking = row_number() window child\n"
            "    window child = base\n"
            "    window base:\n"
            "        partition by:\n"
            "            category\n"
            "        order by:\n"
            "            total desc\n"
            "    satisfying:\n"
            "        total > 0\n"
            "    order by:\n"
            "        ranking\n"
            "    limit 5\n"
            "query broken:\n"
            "    from Input\n"
            "    select:\n"
            "        missing\n"
        ),
        "b.pietto": (
            'import "c.pietto":\n    table projected as Public\n'
            "export:\n"
            "    table Public\n"
        ),
        "c.pietto": (
            "shape Row:\n"
            "    id: Int not null\n"
            "    amount: Int nullable\n"
            "    category: Text nullable\n"
            'source rows: Row is postgres.table("rows")\n'
            "table projected:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        amount\n"
            "        category\n"
            "export:\n"
            "    table projected\n"
        ),
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


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in _project_files().items():
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _allocation() -> construction.ProjectIRAllocationState:
    return construction.ProjectIRAllocationState(
        scope=project_ir.ProjectIRSnapshotScope()
    )


def _build(
    semantic: ProjectSemanticResult,
    allocation: construction.ProjectIRAllocationState | None = None,
) -> pipeline.ProjectIRPipelineResult:
    return pipeline.build_project_ir_pipeline(
        semantic_result=semantic,
        allocation=_allocation() if allocation is None else allocation,
    )


def _fragment(
    result: pipeline.ProjectIRPipelineResult,
    module_path: str,
    name: str,
) -> construction.ProjectIRSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in result.project_plan.fragments
        if fragment.semantic_facts.owner.identity.module_path == module_path
        and fragment.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _concrete(
    result: pipeline.ProjectIRPipelineResult,
    module_path: str,
    name: str,
) -> construction.ProjectIRConcreteSingleRelationFragment:
    fragment = _fragment(result, module_path, name)
    assert type(fragment) is construction.ProjectIRConcreteSingleRelationFragment
    return fragment


def _edge(
    result: pipeline.ProjectIRPipelineResult,
    consumer: construction.ProjectIRConcreteSingleRelationFragment,
):
    matches = tuple(
        edge
        for edge in result.project_plan.cross_relation_edges
        if edge.consumer is consumer
    )
    assert len(matches) == 1
    return matches[0]


def test_controlling_contract_locks_real_authored_pipeline_and_handoff() -> None:
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
        "edf68678b2a766302e654202f3fe0798c3386ffd",
        "71002ac6c2836805e544340eb7052c76f249620a",
        "33353818947",
        "A3/M4/D0",
        "ProjectSemanticResult",
        "ProjectIRAllocationState",
        "build_project_ir_project_plan",
        "build_project_ir_evaluation_context_stage",
        "verify_project_ir_stage",
        "build_project_ir_analysis_bundle",
        "build_project_ir_inspection",
        "serialize_project_ir_inspection",
        "pietto.project-ir-inspection.v1",
        "Add Phase 61 Project IR end-to-end pipeline",
        "PASS — PHASE61_SLICE10_REAL_AUTHORED_MULTI_MODULE_PROJECT_IR_END_TO_END",
        "Phase 61 Slice 11 — Differential Compatibility",
    ):
        assert evidence in normalized


def test_real_authored_project_reaches_complete_verified_inspection(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    allocation = _allocation()
    result = _build(semantic, allocation)
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = result.project_plan

    assert result.semantic_result is semantic
    assert attribution._authority.semantic_facts is facts
    assert plan.semantic_facts is facts
    assert plan.attribution is attribution
    assert result.starting_allocation is allocation
    assert plan.starting_allocation is allocation
    assert result.ending_allocation is plan.ending_allocation
    assert result.evaluation_context_stage.project_plan is plan
    assert result.verification.stage is result.evaluation_context_stage
    assert (
        result.verification.status is verification.ProjectIRVerificationStatus.VERIFIED
    )
    assert result.verification.issues == ()
    assert result.analysis_bundle.verification is result.verification
    assert result.inspection.analysis_bundle is result.analysis_bundle
    assert result.inspection_product.inspection is result.inspection
    assert result.canonical_bytes == result.inspection_product.canonical_bytes
    assert result.canonical_bytes.startswith(
        b"header\tformat=e:pietto.project-ir-inspection.v1"
    )

    canonical_facts = tuple(
        fact
        for environment in facts.environments
        for fact in environment.relation_facts
    )
    assert len(plan.fragments) == len(canonical_facts)
    assert all(
        fragment.semantic_facts is fact
        for fragment, fact in zip(plan.fragments, canonical_facts, strict=True)
    )
    assert all(
        node.ref.scope is allocation.scope for node in plan.structural_stage.nodes
    )
    assert all(
        edge.compatibility.status
        is operators.ProjectIRRowShapeCompatibilityStatus.SATISFIED
        for edge in plan.cross_relation_edges
    )

    projected = _concrete(result, "c.pietto", "projected")
    consumer = _concrete(result, "a.pietto", "consumer")
    second = _concrete(result, "a.pietto", "second")
    final = _concrete(result, "a.pietto", "final")
    consumer_edge = _edge(result, consumer)
    second_edge = _edge(result, second)
    final_edge = _edge(result, final)
    assert consumer_edge.producer is projected
    assert second_edge.producer is projected
    assert final_edge.producer is consumer
    assert consumer_edge.use is not second_edge.use
    assert consumer_edge.input_slot is not second_edge.input_slot
    assert consumer_edge.authority.reference != second_edge.authority.reference
    assert consumer_edge.authority.resolution is consumer.semantic_facts.resolution
    assert consumer_edge.authority.dependency is next(
        dependency
        for dependency in attribution.dependencies
        if dependency is consumer_edge.authority.dependency
    )
    assert consumer_edge.authority.dependency.origin_path is not None
    assert len(consumer_edge.authority.dependency.origin_path.hops) == 2

    assert consumer.subject.anchor.identity != consumer.root.ref
    assert consumer.root.ref != consumer.root_relation_output.occurrence.ref
    assert consumer.final_scalar_outputs[0].occurrence.ref != (
        second.final_scalar_outputs[0].occurrence.ref
    )
    assert consumer.final_scalar_outputs[0].field.anchor.identity != (
        second.final_scalar_outputs[0].field.anchor.identity
    )

    full = _concrete(result, "a.pietto", "full")
    assert tuple(operator.kind for operator in full.logical_stage.operators) == tuple(
        operators.ProjectIRLogicalOperatorKind
    )
    aggregate_context = next(
        context
        for context in result.evaluation_context_stage.aggregate_contexts
        if context.fragment is full
    )
    window_context = next(
        context
        for context in result.evaluation_context_stage.window_operator_contexts
        if context.fragment is full
    )
    window_results = tuple(
        context
        for context in result.evaluation_context_stage.window_result_contexts
        if context.operator_context is window_context
    )
    assert aggregate_context.semantic_facts is full.semantic_facts
    assert aggregate_context.incoming_flow in full.structural_stage.uses
    assert window_context.semantic_facts is full.semantic_facts
    assert window_context.incoming_flow in full.structural_stage.uses
    assert len(window_results) == 1
    assert window_results[0].stage_scalar_output.occurrence is not (
        full.final_scalar_outputs[-1].occurrence
    )
    assert window_results[0].policy in full.property_stage.provided
    assert window_results[0].effect in full.property_stage.effects


def test_real_mixed_project_preserves_terminal_and_independent_component(
    tmp_path: Path,
) -> None:
    result = _build(_semantic_project(tmp_path))
    broken = _fragment(result, "a.pietto", "broken")
    other = _concrete(result, "d.pietto", "other_result")
    assert type(broken) is construction.ProjectIRNonConcreteSingleRelationFragment
    assert broken.subject.state is project_ir.ProjectIRRelationConstructionState.UNKNOWN
    assert broken.structural_stage.nodes == ()
    assert broken.structural_stage.outputs == ()
    assert broken.structural_stage.input_slots == ()
    assert broken.structural_stage.uses == ()
    assert broken.starting_allocation is broken.ending_allocation
    assert other.root in result.project_plan.structural_stage.nodes
    assert not any(
        edge.consumer is broken for edge in result.project_plan.cross_relation_edges
    )
    assert result.verification.verified
    assert inspection.query_project_ir_non_concrete(
        result.inspection,
        broken.subject.anchor.identity,
    ) == (broken,)


def test_fresh_snapshot_scopes_keep_runtime_identity_out_of_canonical_bytes(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    first = _build(semantic)
    second = _build(semantic)
    assert first.starting_allocation.scope is not second.starting_allocation.scope
    assert first.project_plan.structural_stage.nodes[0].ref != (
        second.project_plan.structural_stage.nodes[0].ref
    )
    assert first.analysis_bundle is not second.analysis_bundle
    assert first.inspection is not second.inspection
    assert first.canonical_bytes == second.canonical_bytes
    assert first.canonical_bytes is not second.canonical_bytes
    assert b"ProjectIRSnapshotScope" not in first.canonical_bytes
    assert b"0x" not in first.canonical_bytes


def test_invalid_verification_stops_before_analysis_and_missing_roots_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path)
    analysis_called = False

    def invalid(stage):
        return verification.ProjectIRVerificationResult(
            stage=stage,
            status=verification.ProjectIRVerificationStatus.INVALID,
            issues=(
                verification.ProjectIRVerificationIssue(
                    kind=verification.ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION
                ),
            ),
        )

    def forbidden_analysis(_result):
        nonlocal analysis_called
        analysis_called = True
        raise AssertionError("analysis must not observe INVALID Project IR")

    monkeypatch.setattr(pipeline, "verify_project_ir_stage", invalid)
    monkeypatch.setattr(
        pipeline, "build_project_ir_analysis_bundle", forbidden_analysis
    )
    with pytest.raises(ValueError, match="integrity verification failed"):
        _build(semantic)
    assert not analysis_called

    empty = ProjectSemanticResult(root=None, config_path=None, model=None)
    with pytest.raises(ValueError, match="retained Project roots"):
        _build(empty)


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_pipeline import build_project_ir_pipeline

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
result = build_project_ir_pipeline(
    semantic_result=semantic,
    allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
)
sys.stdout.buffer.write(result.canonical_bytes)
"""


def test_pipeline_is_hash_seed_cwd_independent_private_and_immutable(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs: list[bytes] = []
    for seed, cwd_name in (("1", "cwd-a"), ("977", "cwd-b")):
        cwd = tmp_path / cwd_name
        cwd.mkdir()
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        source_root = str(REPO_ROOT / "src")
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            source_root if not existing else os.pathsep.join((source_root, existing))
        )
        completed = subprocess.run(
            (sys.executable, "-c", _DETERMINISM_PROBE, str(project_root)),
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
        )
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]
    assert str(tmp_path).encode() not in outputs[0]
    assert outputs[0].startswith(b"header\tformat=e:pietto.project-ir-inspection.v1")

    assert pipeline.__all__ == ()
    assert not hasattr(pietto, "ProjectIRPipelineResult")
    assert not hasattr(project_package, "ProjectIRPipelineResult")
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
    assert getattr(pipeline.ProjectIRPipelineResult, "__dataclass_params__").frozen
    assert hasattr(pipeline.ProjectIRPipelineResult, "__slots__")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in inspect.signature(
            pipeline.ProjectIRPipelineResult
        ).parameters.values()
    )
    result = _build(_semantic_project(tmp_path / "immutability"))
    with pytest.raises(TypeError, match="exact stage products"):
        replace(result, project_plan=object())  # type: ignore[arg-type]
    with pytest.raises(FrozenInstanceError):
        result.project_plan = result.project_plan  # type: ignore[misc]
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        REPO_ROOT / "src/pietto/ir/model.py",
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "project_ir_pipeline" not in text
        assert "ProjectIRPipelineResult" not in text
