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
import pietto._project.project_ir_evaluation_context as evaluation
import pietto._project.project_ir_operators as operators
import pietto._project.project_ir_properties as properties
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import NameExpr
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md"
)
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Aggregate Evaluation Context",
    "Window Operator And Result Contexts",
    "Policy Effect And Closed-binding Preservation",
    "Completeness Uniqueness And Zero Mutation",
    "Determinism Immutability And No-ambient Authority",
    "Focused Assurance",
    "Integration Boundaries And Non-goals",
    "Slice 8 Handoff",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    amount: Int nullable
    category: Text nullable
source rows: Row is postgres.table("rows")
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
query where_group:
    from rows
    where id > 0
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
        ranked = rank() window:
            order by:
                id
query full:
    from rows
    let:
        adjusted = amount + id
    where id > 0
    group by:
        category
    select:
        category
        total = sum(adjusted)
        ranking = row_number() window child
    window child = base
    window base:
        partition by:
            category
        order by:
            total desc
    satisfying:
        sum(adjusted) > 0
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


def _build_plan(semantic: ProjectSemanticResult) -> composition.ProjectIRProjectPlan:
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    return composition.build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=construction.ProjectIRAllocationState(
            scope=project_ir.ProjectIRSnapshotScope()
        ),
    )


def _build_stage(
    semantic: ProjectSemanticResult,
) -> evaluation.ProjectIREvaluationContextStage:
    return evaluation.build_project_ir_evaluation_context_stage(_build_plan(semantic))


def _aggregate_context(
    stage: evaluation.ProjectIREvaluationContextStage,
    name: str,
) -> evaluation.ProjectIRAggregateEvaluationContext:
    matches = tuple(
        context
        for context in stage.aggregate_contexts
        if context.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _window_context(
    stage: evaluation.ProjectIREvaluationContextStage,
    name: str,
) -> evaluation.ProjectIRWindowOperatorEvaluationContext:
    matches = tuple(
        context
        for context in stage.window_operator_contexts
        if context.semantic_facts.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def test_controlling_contract_locks_evaluation_authority_scope_and_handoff() -> None:
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
        "21b478569029dbae43aa6cbddecfa0c3709abe5d",
        "351a5ee5dfc709c9f46a7fecd4112f05a01c9c53",
        "33340163436",
        "A3/M6/D0",
        "evaluation context != evaluator",
        "stream input row != semantic BASE_RESULT row",
        "window policy != effect classification",
        "logical DAG sharing != evaluate once",
        "ProjectIRAggregateEvaluationContext",
        "ProjectIRWindowResultEvaluationContext",
        "ProjectIREvaluationContextStage",
        "Add Phase 61 Project IR evaluation contexts",
        "PASS — PHASE61_SLICE7_AGGREGATE_WINDOW_EVALUATION_CONTEXT_POLICY_"
        "EFFECT_NO_AMBIENT_AUTHORITY_END_TO_END",
        "Phase 61 Slice 8 — Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness",
    ):
        assert evidence in normalized


def test_context_carriers_are_private_frozen_complete_and_canonical(
    tmp_path: Path,
) -> None:
    carriers = (
        evaluation.ProjectIRAggregateEvaluationContext,
        evaluation.ProjectIRWindowOperatorEvaluationContext,
        evaluation.ProjectIRWindowResultEvaluationContext,
        evaluation.ProjectIREvaluationContextStage,
    )
    for carrier in carriers:
        assert getattr(carrier, "__dataclass_params__").frozen
        assert hasattr(carrier, "__slots__")
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    assert evaluation.__all__ == ()

    stage = _build_stage(_semantic_project(tmp_path))
    assert tuple(
        context.semantic_facts.owner.identity.declared_name
        for context in stage.aggregate_contexts
    ) == ("aggregate_only", "grouped", "where_group", "satisfying", "full")
    assert tuple(
        context.semantic_facts.owner.identity.declared_name
        for context in stage.window_operator_contexts
    ) == ("windowed", "full")
    assert tuple(
        (
            context.operator_context.semantic_facts.owner.identity.declared_name,
            context.window_fact.output_name,
        )
        for context in stage.window_result_contexts
    ) == (
        ("windowed", "ranking"),
        ("windowed", "ranked"),
        ("full", "ranking"),
    )
    assert not any(
        context.fragment.semantic_facts.owner.identity.declared_name == "broken"
        for context in (*stage.aggregate_contexts, *stage.window_operator_contexts)
    )
    with pytest.raises(FrozenInstanceError):
        stage.aggregate_contexts = ()  # type: ignore[misc]


def test_aggregate_contexts_retain_exact_flow_semantics_and_base_result(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    for context in stage.aggregate_contexts:
        assert (
            context.operator.kind
            is operators.ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        )
        assert context.incoming_flow.slot.consumer is context.operator.node
        assert context.incoming_flow.output is context.input_row_output.occurrence
        assert context.result_row_output.occurrence.producer is context.operator.node
        assert context.semantic_facts is context.fragment.semantic_facts
        assert (
            context.readiness
            is context.semantic_facts.aggregate_grouped_clause_readiness
        )
        assert context.group_keys is context.semantic_facts.group_key_occurrences
        assert (
            context.aggregate_results is context.semantic_facts.aggregate_result_facts
        )
        assert context.let_scope is context.semantic_facts.let_scope_facts
        assert (
            type(context.result_row_output.row_shape)
            is properties.ProjectIRStageRowShape
        )
        assert context.result_row_output.row_shape.checkpoint.kind is (
            properties.ProjectIRStageRowCheckpointKind.BASE_RESULT
        )
        assert context.result_row_output.row_shape.checkpoint.state is (
            context.semantic_facts.base_result_state
        )
        assert context.input_closed_bindings.bindings == ()
        assert context.result_closed_bindings.bindings == ()
        assert not hasattr(context, "policy")

    aggregate_only = _aggregate_context(stage, "aggregate_only")
    grouped = _aggregate_context(stage, "grouped")
    where_group = _aggregate_context(stage, "where_group")
    satisfying = _aggregate_context(stage, "satisfying")
    assert aggregate_only.group_keys == ()
    assert len(aggregate_only.aggregate_results) == 1
    assert not any(
        type(property_) is properties.ProjectIRProvidedLocalGrainEvidence
        for property_ in aggregate_only.fragment.property_stage.provided
    )
    assert type(grouped.group_keys[0].key) is NameExpr
    assert grouped.group_keys[0].key.name == "category"
    assert any(
        type(property_) is properties.ProjectIRProvidedLocalGrainEvidence
        for property_ in grouped.fragment.property_stage.provided
    )
    assert where_group.incoming_flow.output.producer is next(
        operator.node
        for operator in where_group.fragment.logical_stage.operators
        if operator.kind is operators.ProjectIRLogicalOperatorKind.ROW_FILTER
    )
    assert any(
        operator.kind is operators.ProjectIRLogicalOperatorKind.RESULT_FILTER
        for operator in satisfying.fragment.logical_stage.operators
    )


def test_window_contexts_keep_stream_input_and_semantic_base_distinct(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    windowed = _window_context(stage, "windowed")
    full = _window_context(stage, "full")
    for context in (windowed, full):
        assert (
            context.operator.kind
            is operators.ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
        )
        assert (
            context.incoming_flow.output is context.stream_input_row_output.occurrence
        )
        assert context.result_row_output.occurrence.producer is context.operator.node
        assert context.semantic_base_checkpoint.kind is (
            properties.ProjectIRStageRowCheckpointKind.BASE_RESULT
        )
        assert (
            context.semantic_base_checkpoint.state
            is context.semantic_facts.base_result_state
        )
        assert context.let_scope is context.semantic_facts.let_scope_facts
        assert (
            context.named_window_namespace
            is context.semantic_facts.named_window_namespace
        )
        assert context.stream_closed_bindings.bindings == ()
        assert context.result_closed_bindings.bindings == ()
    assert not windowed.stream_matches_semantic_base
    assert full.stream_matches_semantic_base
    stream_shape = windowed.stream_input_row_output.row_shape
    assert type(stream_shape) is properties.ProjectIRStageRowShape
    assert stream_shape.checkpoint.state is windowed.semantic_facts.input_state
    assert full.semantic_facts.named_window_namespace is not None
    assert full.semantic_facts.let_scope_facts is not None
    assert full.semantic_facts.let_scope_facts.bindings


def test_window_results_bind_exact_stage_scalar_policy_effect_and_final_distinction(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    for context in stage.window_result_contexts:
        assert context.project_fact is context.window_fact.project_fact
        assert (
            context.stage_scalar_output.occurrence.producer
            is context.operator_context.operator.node
        )
        assert context.stage_scalar_output.field.field_position == (
            context.window_fact.selected_output_ordinal
        )
        assert context.policy.output is context.stage_scalar_output
        assert context.policy.evidence is context.window_fact
        assert context.effect.output is context.stage_scalar_output
        assert (
            context.effect.determinism
            is properties.ProjectIRDeterminismEvidence.UNKNOWN
        )
        assert (
            context.effect.error_behavior
            is properties.ProjectIRErrorBehaviorEvidence.UNKNOWN
        )
        assert (
            context.effect.side_effects
            is properties.ProjectIRSideEffectEvidence.UNKNOWN
        )
        assert context.effect.evaluation_count is (
            properties.ProjectIREvaluationCountEvidence.UNKNOWN
        )
        final = next(
            output
            for output in context.operator_context.fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position
            == context.window_fact.selected_output_ordinal
        )
        assert context.stage_scalar_output.occurrence is not final.occurrence


def test_contexts_reuse_exact_effects_and_reject_rebuilt_semantic_policy_effect(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    aggregate = stage.aggregate_contexts[0]
    result = stage.window_result_contexts[0]
    with pytest.raises(ValueError, match="exact semantic authority"):
        replace(aggregate, semantic_facts=replace(aggregate.semantic_facts))
    with pytest.raises(ValueError, match="policy/effect authority"):
        replace(result, policy=replace(result.policy))
    with pytest.raises(ValueError, match="policy/effect authority"):
        replace(result, effect=replace(result.effect))
    assert not hasattr(aggregate, "aggregate_policy")
    assert result.policy is next(
        property_
        for property_ in result.operator_context.fragment.property_stage.provided
        if property_ is result.policy
    )
    assert result.effect is next(
        effect
        for effect in result.operator_context.fragment.property_stage.effects
        if effect is result.effect
    )


def test_evaluation_stage_rejects_missing_duplicate_and_foreign_contexts(
    tmp_path: Path,
) -> None:
    stage = _build_stage(_semantic_project(tmp_path))
    with pytest.raises(ValueError, match="complete aggregate"):
        replace(stage, aggregate_contexts=stage.aggregate_contexts[:-1])
    with pytest.raises(ValueError, match="complete aggregate"):
        replace(
            stage,
            aggregate_contexts=(*stage.aggregate_contexts, stage.aggregate_contexts[0]),
        )
    with pytest.raises(ValueError, match="complete window-result"):
        replace(stage, window_result_contexts=stage.window_result_contexts[:-1])

    foreign = _build_stage(_semantic_project(tmp_path / "foreign"))
    with pytest.raises(ValueError, match="complete window contexts"):
        replace(
            stage,
            window_operator_contexts=(
                foreign.window_operator_contexts[0],
                *stage.window_operator_contexts[1:],
            ),
        )


def test_stage_preserves_project_plan_structure_allocation_and_no_ambient_authority(
    tmp_path: Path,
) -> None:
    plan = _build_plan(_semantic_project(tmp_path))
    stage = evaluation.build_project_ir_evaluation_context_stage(plan)
    assert stage.project_plan is plan
    assert stage.structural_stage is plan.structural_stage
    assert stage.starting_allocation is plan.starting_allocation
    assert stage.ending_allocation is plan.ending_allocation
    assert stage.structural_stage.free_outer_bindings == ()
    assert all(
        context.fragment in plan.concrete_fragments
        for context in stage.aggregate_contexts
    )
    assert all(
        context.fragment in plan.concrete_fragments
        for context in stage.window_operator_contexts
    )
    source = (
        REPO_ROOT / "src/pietto/_project/project_ir_evaluation_context.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "getcwd",
        "environ",
        "current_project",
        "current_relation",
        "registry",
        "resolve_name",
        "evaluate_expression",
    ):
        assert forbidden not in source


_DETERMINISM_PROBE = r"""
from pathlib import Path
import sys

from pietto._project import check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import build_project_ir_evaluation_context_stage

semantic = build_empty_project_semantic_result(check.check_project_parse_only(Path(sys.argv[1])))
facts = semantic.module_semantic_facts
attribution = semantic.module_attribution_facts
assert facts is not None and attribution is not None
plan = build_project_ir_project_plan(semantic_facts=facts, attribution=attribution, allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()))
stage = build_project_ir_evaluation_context_stage(plan)
print((tuple(context.semantic_facts.owner.identity.declared_name for context in stage.aggregate_contexts), tuple((context.semantic_facts.owner.identity.declared_name, context.stream_matches_semantic_base) for context in stage.window_operator_contexts), tuple((context.window_fact.selected_output_ordinal, context.stage_scalar_output.occurrence.ref.position) for context in stage.window_result_contexts), stage.ending_allocation.next_use_position))
"""


def test_evaluation_context_is_hash_seed_cwd_independent_and_public_sql_zero_delta(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    _semantic_project(project_root)
    outputs = []
    for seed, cwd_name in (("1", "cwd-a"), ("707", "cwd-b")):
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

    assert not hasattr(pietto, "ProjectIREvaluationContextStage")
    assert not hasattr(project_package, "ProjectIREvaluationContextStage")
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
        assert "project_ir_evaluation_context" not in text
        assert "ProjectIREvaluationContextStage" not in text
