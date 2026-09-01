from __future__ import annotations

import ast
from dataclasses import fields
from importlib.metadata import version
from pathlib import Path
import subprocess

import pietto
import pietto._project as project_package
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_properties import (
    ProjectIRProvidedPropertySlot,
)
from pietto._project.project_ir_pure_boundary import (
    PROJECT_IR_INSPECTION_FORMAT,
    ProjectIRPureStatus,
)
from pietto._project.project_ir_verification import (
    ProjectIRAnalysisKind,
    ProjectIRVerificationStatus,
)
from pietto.ir.model import RelationIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase61-completion-audit-phase62-handoff-v1.md"
ROUTE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md"
)
SOURCE = REPO_ROOT / "tests/test_phase61_slice12_completion_audit_phase62_handoff.py"
PROBE = REPO_ROOT / "tests/_pietto_phase61_project_ir_differential_probe.py"
PHASE61_BASE = "bf4eeb06507f84374b9d97070423face3e54d929"
PHASE61_BASE_TREE = "1ca3542b1f373cdce6b7035b33000eda474ae39d"
PHASE61_BASE_CI = "33295132391"
PHASE61_BASE_SUBJECT = "Complete Phase 60 advanced windows"

_UNIT_AUTHORITIES = (
    (
        "Slice 1",
        "Architecture, Mature-Source Audit, Semantic Laws, And Route Lock",
        "phase61-project-ir-architecture-source-audit-route-lock-v1.md",
        "test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py",
        (),
    ),
    (
        "Slice 2",
        "Scope, Stages, Plan/Value/Use Occurrences, Anchors, And Construction States",
        "phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md",
        "test_phase61_slice2_project_ir_scope_stages_occurrences_anchors_construction_states.py",
        ("src/pietto/_project/project_ir.py",),
    ),
    (
        "Slice 3",
        "Row/Output Model, Provided/Required Properties, Effects, And Estimate Boundary",
        "phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md",
        "test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py",
        ("src/pietto/_project/project_ir_properties.py",),
    ),
    (
        "Slice 4",
        "Current Logical Operator Algebra And Exact Property Transfer",
        "phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md",
        "test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py",
        (
            "src/pietto/_project/project_ir_operators.py",
            "src/pietto/_project/project_ir_properties.py",
        ),
    ),
    (
        "Slice 5 output-identity prerequisite",
        "Complete Project Relation Output Identity Authority",
        "phase61-slice5-output-identity-authority-readiness-continuation-v1.md",
        "test_phase61_slice5_output_identity_authority_readiness_continuation.py",
        (
            "src/pietto/_project/model.py",
            "src/pietto/_project/module_attribution.py",
            "src/pietto/_project/module_inspection.py",
            "src/pietto/_project/module_package_neutral_identity.py",
        ),
    ),
    (
        "Slice 5 dataflow prerequisite",
        "Intra-Relation Dataflow Authority",
        "phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md",
        "test_phase61_slice5_intra_relation_dataflow_readiness_continuation.py",
        (
            "src/pietto/_project/module_semantic_fact_preservation.py",
            "src/pietto/_project/project_ir.py",
            "src/pietto/_project/project_ir_operators.py",
            "src/pietto/_project/project_ir_properties.py",
        ),
    ),
    (
        "Slice 5",
        "Canonical Single-Relation Construction From Existing Project Semantic Facts",
        "phase61-slice5-canonical-single-relation-project-ir-construction-v1.md",
        "test_phase61_slice5_canonical_single_relation_project_ir_construction.py",
        (
            "src/pietto/_project/project_ir.py",
            "src/pietto/_project/project_ir_construction.py",
        ),
    ),
    (
        "Slice 6",
        "Cross-Module Relation Composition And Acyclic Project Plan DAG",
        "phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md",
        "test_phase61_slice6_cross_module_relation_composition_acyclic_project_plan_dag.py",
        (
            "src/pietto/_project/project_ir.py",
            "src/pietto/_project/project_ir_composition.py",
        ),
    ),
    (
        "Slice 7",
        "Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority",
        "phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md",
        "test_phase61_slice7_aggregate_window_evaluation_context_policy_effect_no_ambient_authority.py",
        (
            "src/pietto/_project/project_ir_construction.py",
            "src/pietto/_project/project_ir_evaluation_context.py",
        ),
    ),
    (
        "Slice 8",
        "Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness",
        "phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md",
        "test_phase61_slice8_integrity_verifier_analysis_invalidation_semantic_equivalence_optimizer_recursion_readiness.py",
        ("src/pietto/_project/project_ir_verification.py",),
    ),
    (
        "Slice 9",
        "Private Inspection, Query, Canonical Serialization, And Pure Boundary",
        "phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md",
        "test_phase61_slice9_private_inspection_query_canonical_serialization_pure_boundary.py",
        (
            "src/pietto/_project/project_ir_inspection.py",
            "src/pietto/_project/project_ir_pure_boundary.py",
        ),
    ),
    (
        "Slice 10",
        "Real Authored Multi-Module Project IR E2E",
        "phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md",
        "test_phase61_slice10_real_authored_multi_module_project_ir_e2e.py",
        ("src/pietto/_project/project_ir_pipeline.py",),
    ),
    (
        "Slice 11",
        "Differential Compatibility",
        "phase61-slice11-differential-compatibility-v1.md",
        "test_phase61_slice11_differential_compatibility.py",
        (),
    ),
    (
        "Slice 12",
        "Completion Audit And Phase 62 Handoff",
        "phase61-completion-audit-phase62-handoff-v1.md",
        "test_phase61_slice12_completion_audit_phase62_handoff.py",
        (),
    ),
)

_NUMBERED_UNIT_INDEXES = (0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13)

_PUBLISHED_UNITS = (
    (
        "Slice 1",
        "6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2",
        "c82cfb9e4c5ab7549619b6c1505be6d2fad6bd71",
        PHASE61_BASE,
        "33303992201",
        "Add Phase 61 Project IR route lock",
    ),
    (
        "Slice 2",
        "a9725d46b1c4c79d5e1c78d79a0e042522e1edd3",
        "ef4db5396f1a1ce436d003454d99f314c2cfcae1",
        "6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2",
        "33305962868",
        "Add Phase 61 Project IR structural model",
    ),
    (
        "Slice 3",
        "be984f7ae9c0821cfa14229da99bf9c8da97a048",
        "c0d4bc91aa1883065427244d5572ba3e2d424b67",
        "a9725d46b1c4c79d5e1c78d79a0e042522e1edd3",
        "33308020119",
        "Add Phase 61 Project IR property model",
    ),
    (
        "Slice 4",
        "6359867c7e9c51d9b59bd23642d7bd2492b24862",
        "ba3d57d0b7217cbf4ec47c2ec6b4fae40c8a3d02",
        "be984f7ae9c0821cfa14229da99bf9c8da97a048",
        "33317947197",
        "Add Phase 61 Project IR operator algebra",
    ),
    (
        "Slice 5 output-identity prerequisite",
        "cce7709f143de4eb5f9989cbbbd804fe08e71d74",
        "e8bb0c2c2150d21692ac1da346d88b610eefa4fa",
        "6359867c7e9c51d9b59bd23642d7bd2492b24862",
        "33321099987",
        "Add complete Project relation output identities",
    ),
    (
        "Slice 5 dataflow prerequisite",
        "1ac00344554967ba30f2e3bdff553ec63c2a4c12",
        "c73d5c93c2c037f8258beab4ba5587e4873c3319",
        "cce7709f143de4eb5f9989cbbbd804fe08e71d74",
        "33335654061",
        "Add Project IR intra-relation dataflow readiness",
    ),
    (
        "Slice 5",
        "b9c9e38f809f911eb429e7284d377c2c205e548b",
        "4273b06c631db9e609d0915d3880bc6b4ea3aaa6",
        "1ac00344554967ba30f2e3bdff553ec63c2a4c12",
        "33337635343",
        "Add Phase 61 single-relation Project IR builder",
    ),
    (
        "Slice 6",
        "21b478569029dbae43aa6cbddecfa0c3709abe5d",
        "351a5ee5dfc709c9f46a7fecd4112f05a01c9c53",
        "b9c9e38f809f911eb429e7284d377c2c205e548b",
        "33340163436",
        "Add Phase 61 Project IR composition DAG",
    ),
    (
        "Slice 7",
        "455629a9edc93622180788ff4cba8b76776c4e9f",
        "6b9bfe44d00de3de112214515f3682131696967a",
        "21b478569029dbae43aa6cbddecfa0c3709abe5d",
        "33342737233",
        "Add Phase 61 Project IR evaluation contexts",
    ),
    (
        "Slice 8",
        "577511b9dd6dbf14dbd5dc3710bee0a3d86b92be",
        "c4bc106f54d31939c4681d4d1dd6bb10d519f78c",
        "455629a9edc93622180788ff4cba8b76776c4e9f",
        "33349469530",
        "Add Phase 61 Project IR verifier",
    ),
    (
        "Slice 9",
        "edf68678b2a766302e654202f3fe0798c3386ffd",
        "71002ac6c2836805e544340eb7052c76f249620a",
        "577511b9dd6dbf14dbd5dc3710bee0a3d86b92be",
        "33353818947",
        "Add Phase 61 Project IR inspection",
    ),
    (
        "Slice 10",
        "6607e7a7b127562e5f24490a0135bd7e14134744",
        "700df2d796a30852e2076c75af5b60411e8feeea",
        "edf68678b2a766302e654202f3fe0798c3386ffd",
        "33355551275",
        "Add Phase 61 Project IR end-to-end pipeline",
    ),
    (
        "Slice 11",
        "34a9f48811101b0df66119db94277ff2fbfd9d23",
        "7024668474203c59bf4c4acf7cd4bfb5f38a34ea",
        "6607e7a7b127562e5f24490a0135bd7e14134744",
        "33357860140",
        "Add Phase 61 differential compatibility assurance",
    ),
)

_EXIT_TEST_FUNCTIONS = {
    "test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py": {
        "test_layer_identity_use_multiplicity_and_execution_laws_are_exact",
        "test_graph_provenance_recursion_correlation_and_optimizer_laws_are_exact",
    },
    "test_phase61_slice2_project_ir_scope_stages_occurrences_anchors_construction_states.py": {
        "test_private_carrier_inventory_is_frozen_slotted_and_stage_specific",
        "test_concrete_and_typed_non_concrete_subjects_prevent_mixed_states",
    },
    "test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py": {
        "test_current_scalar_relation_outputs_and_bag_are_explicit_without_set_variant",
        "test_effect_unknown_never_becomes_purity_and_does_not_change_identity",
    },
    "test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py": {
        "test_exact_eight_stage_algebra_retains_order_without_let_or_named_operators",
        "test_transfer_matrix_freezes_group_window_projection_bag_and_order_boundaries",
    },
    "test_phase61_slice5_output_identity_authority_readiness_continuation.py": {
        "test_concrete_semantic_outputs_are_complete_while_legacy_lineage_is_deferred",
        "test_semantic_to_attribution_dependency_is_exact_and_downstream_roots_close",
    },
    "test_phase61_slice5_intra_relation_dataflow_readiness_continuation.py": {
        "test_semantic_input_base_result_and_final_checkpoints_are_exact",
        "test_full_pipeline_has_one_exact_flow_edge_per_adjacent_operator",
    },
    "test_phase61_slice5_canonical_single_relation_project_ir_construction.py": {
        "test_full_properties_transfers_effects_and_estimates_are_complete",
        "test_global_aggregate_omits_local_grain_without_inventing_it_downstream",
    },
    "test_phase61_slice6_cross_module_relation_composition_acyclic_project_plan_dag.py": {
        "test_cross_edges_use_exact_resolution_dependency_root_output_and_owner_local_order",
        "test_non_concrete_cycles_remain_terminals_and_do_not_erase_concrete_component",
    },
    "test_phase61_slice7_aggregate_window_evaluation_context_policy_effect_no_ambient_authority.py": {
        "test_aggregate_contexts_retain_exact_flow_semantics_and_base_result",
        "test_window_results_bind_exact_stage_scalar_policy_effect_and_final_distinction",
    },
    "test_phase61_slice8_integrity_verifier_analysis_invalidation_semantic_equivalence_optimizer_recursion_readiness.py": {
        "test_independent_verifier_detects_controlled_corruption",
        "test_fresh_reverse_topological_and_transitive_reachability_analyses",
    },
    "test_phase61_slice9_private_inspection_query_canonical_serialization_pure_boundary.py": {
        "test_typed_queries_return_complete_exact_buckets_without_winners",
        "test_pure_evaluator_accepts_reference_document_and_normalizes_malformed_inputs",
    },
    "test_phase61_slice10_real_authored_multi_module_project_ir_e2e.py": {
        "test_real_authored_project_reaches_complete_verified_inspection",
        "test_real_mixed_project_preserves_terminal_and_independent_component",
    },
    "test_phase61_slice11_differential_compatibility.py": {
        "test_every_environment_matches_one_reviewed_common_manifest",
        "test_invalid_verifier_and_pure_rejections_use_typed_normalized_outcomes",
    },
}

_PHASE61_PRODUCTION_PATHS = (
    "src/pietto/_project/model.py",
    "src/pietto/_project/module_attribution.py",
    "src/pietto/_project/module_inspection.py",
    "src/pietto/_project/module_package_neutral_identity.py",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "src/pietto/_project/project_ir.py",
    "src/pietto/_project/project_ir_composition.py",
    "src/pietto/_project/project_ir_construction.py",
    "src/pietto/_project/project_ir_evaluation_context.py",
    "src/pietto/_project/project_ir_inspection.py",
    "src/pietto/_project/project_ir_operators.py",
    "src/pietto/_project/project_ir_pipeline.py",
    "src/pietto/_project/project_ir_properties.py",
    "src/pietto/_project/project_ir_pure_boundary.py",
    "src/pietto/_project/project_ir_verification.py",
)

_PRODUCT_SYMBOLS = {
    "src/pietto/_project/module_attribution.py": {
        "ProjectModuleRelationOutputFieldAttribution",
    },
    "src/pietto/_project/module_semantic_fact_preservation.py": {
        "ProjectModuleRelationSemanticFacts",
    },
    "src/pietto/_project/project_ir.py": {
        "ProjectIRSnapshotScope",
        "ProjectIRPlanNodeRef",
        "ProjectIROutputValueRef",
        "ProjectIRUseRef",
        "ProjectIRInputSlotRef",
        "ProjectIRUseOccurrence",
        "ProjectIROperatorFlowUseOccurrence",
        "ProjectIRConcreteRelationSubject",
        "ProjectIRNonConcreteRelationSubject",
        "ProjectIRStructuralStage",
    },
    "src/pietto/_project/project_ir_properties.py": {
        "ProjectIRRowShape",
        "ProjectIRStageRowCheckpoint",
        "ProjectIRStageRowShape",
        "ProjectIRProvidedBagMultiplicity",
        "ProjectIRProvidedClosedBindings",
        "ProjectIRRequiredRowShape",
        "ProjectIREffectEvidence",
        "ProjectIREstimateBoundary",
    },
    "src/pietto/_project/project_ir_operators.py": {
        "ProjectIRLogicalOperatorKind",
        "ProjectIRLogicalOperatorOccurrence",
        "ProjectIRPreservedPropertyTransfer",
        "ProjectIREstablishedPropertyTransfer",
        "ProjectIRRowShapeCompatibility",
    },
    "src/pietto/_project/project_ir_construction.py": {
        "ProjectIRAllocationState",
        "ProjectIRConcreteSingleRelationFragment",
        "ProjectIRNonConcreteSingleRelationFragment",
        "build_project_ir_single_relation_fragment",
    },
    "src/pietto/_project/project_ir_composition.py": {
        "ProjectIRCrossRelationEdge",
        "ProjectIRProjectPlan",
        "build_project_ir_project_plan",
    },
    "src/pietto/_project/project_ir_evaluation_context.py": {
        "ProjectIRAggregateEvaluationContext",
        "ProjectIRWindowOperatorEvaluationContext",
        "ProjectIRWindowResultEvaluationContext",
        "ProjectIREvaluationContextStage",
        "build_project_ir_evaluation_context_stage",
    },
    "src/pietto/_project/project_ir_verification.py": {
        "ProjectIRVerificationResult",
        "ProjectIRAnalysisInvalidation",
        "ProjectIRSemanticEquivalenceAssessment",
        "ProjectIRAnalysisBundle",
        "verify_project_ir_stage",
        "build_project_ir_analysis_bundle",
    },
    "src/pietto/_project/project_ir_inspection.py": {
        "ProjectIRInspection",
        "ProjectIRInspectionProduct",
        "build_project_ir_inspection",
        "serialize_project_ir_inspection",
        "query_project_ir_non_concrete",
    },
    "src/pietto/_project/project_ir_pure_boundary.py": {
        "PROJECT_IR_INSPECTION_FORMAT",
        "ProjectIRPureDocument",
        "ProjectIRPureOutcome",
        "evaluate_project_ir_document",
        "_encode_document",
    },
    "src/pietto/_project/project_ir_pipeline.py": {
        "ProjectIRPipelineResult",
        "build_project_ir_pipeline",
    },
}

_SLICE12_STATIC_PATHS = (
    "docs/spec/phase61-completion-audit-phase62-handoff-v1.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice12_completion_audit_phase62_handoff.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )[1:]


def _defined_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    names.update(
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Name)
    )
    return frozenset(names)


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def test_exact_route_units_specs_tests_and_prerequisite_count_are_closed() -> None:
    specs = {path.name for path in (REPO_ROOT / "docs/spec").glob("phase61*.md")}
    tests = {path.name for path in (REPO_ROOT / "tests").glob("test_phase61_slice*.py")}
    assert specs == {
        spec for _unit, _owner, spec, _test, _production in _UNIT_AUTHORITIES
    }
    assert tests == {
        test for _unit, _owner, _spec, test, _production in _UNIT_AUTHORITIES
    }

    route = _table(
        _section(ROUTE_LOCK.read_text(encoding="utf-8"), "Exact 12-slice Route")
    )
    numbered = tuple(_UNIT_AUTHORITIES[index] for index in _NUMBERED_UNIT_INDEXES)
    assert tuple((row[0], row[1]) for row in route) == tuple(
        (str(number), owner)
        for number, (_unit, owner, _spec, _test, _production) in enumerate(
            numbered,
            start=1,
        )
    )
    completion_route = _table(
        _section(SPEC.read_text(encoding="utf-8"), "Numbered Route Closure")
    )
    assert tuple((row[0], row[1]) for row in completion_route) == tuple(
        (row[0], row[1]) for row in route
    )
    assert (
        tuple(row[2] for row in completion_route[:11])
        == ("`COMPLETED / PUBLISHED`",) * 11
    )
    assert completion_route[11][2] == "`CURRENT / COMPLETION CANDIDATE`"
    assert len(_PUBLISHED_UNITS) == 13
    assert len(numbered) == 12
    assert sum("prerequisite" in unit for unit, *_rest in _UNIT_AUTHORITIES) == 2


def test_13_predecessor_publications_match_exact_first_parent_git_and_ci_ledger() -> (
    None
):
    rows = _table(
        _section(SPEC.read_text(encoding="utf-8"), "Published Phase 61 Authority")
    )
    assert len(rows) == 13
    assert tuple(row[0] for row in rows) == tuple(item[0] for item in _PUBLISHED_UNITS)
    assert tuple(row[1:6] for row in rows) == tuple(
        (
            f"`{commit}`",
            f"`{tree}`",
            f"`{parent}`",
            f"`{subject}`",
            f"`{run_id}`",
        )
        for _unit, commit, tree, parent, run_id, subject in _PUBLISHED_UNITS
    )
    assert (
        tuple(row[6:] for row in rows)
        == (
            (
                "`push / main / attempt 1 / success`",
                "`success`",
                "`success`",
            ),
        )
        * 13
    )
    normalized = " ".join(
        _section(
            SPEC.read_text(encoding="utf-8"),
            "Published Phase 61 Authority",
        ).split()
    )
    for evidence in (
        PHASE61_BASE,
        PHASE61_BASE_TREE,
        PHASE61_BASE_CI,
        PHASE61_BASE_SUBJECT,
        "push / main / attempt 1 / success",
        "Python 3.12 and Python 3.13 both succeeded",
    ):
        assert evidence in normalized

    if _git("rev-parse", "--is-shallow-repository") == "true":
        assert "13 rows are one exact single-parent first-parent chain" in normalized
        return

    expected = tuple(
        (commit, tree, parent, subject)
        for _unit, commit, tree, parent, _run_id, subject in _PUBLISHED_UNITS
    )
    actual = tuple(
        tuple(line.split("\t"))
        for line in _git(
            "log",
            "--reverse",
            "--first-parent",
            "--format=%H%x09%T%x09%P%x09%s",
            f"{PHASE61_BASE}..{_PUBLISHED_UNITS[-1][1]}",
        ).splitlines()
    )
    assert actual == expected
    assert _git("show", "-s", "--format=%T", PHASE61_BASE) == PHASE61_BASE_TREE
    assert _git("show", "-s", "--format=%s", PHASE61_BASE) == PHASE61_BASE_SUBJECT
    assert _git("merge-base", "--is-ancestor", _PUBLISHED_UNITS[-1][1], "HEAD") == ""


def test_exact_13_criterion_exit_ledger_recomputes_live_product_and_test_evidence() -> (
    None
):
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Phase 61 Exit Ledger"))
    assert len(rows) == 13
    assert tuple(row[-1] for row in rows) == ("`SATISFIED`",) * 13
    for row, authority, publication in zip(
        rows,
        _UNIT_AUTHORITIES[:13],
        _PUBLISHED_UNITS,
        strict=True,
    ):
        unit, _owner, _spec, test, _production = authority
        _published_unit, commit, tree, _parent, run_id, _subject = publication
        assert row[1] == unit
        assert row[2]
        assert row[3] == f"`tests/{test}`"
        assert row[4] == f"`{commit}` / `{tree}`"
        assert row[5] == f"`{run_id}`"
    assert all(
        required <= _function_names(REPO_ROOT / "tests" / filename)
        for filename, required in _EXIT_TEST_FUNCTIONS.items()
    )
    assert all((REPO_ROOT / path).is_file() for path in _PHASE61_PRODUCTION_PATHS)
    assert "Phase 61 exit criteria = 13" in document
    assert "SATISFIED = 13" in document
    assert "NOT_APPLICABLE_BY_FROZEN_SCOPE = 0" in document
    assert "missing owner/evidence rows = 0" in document

    for path, expected in _PRODUCT_SYMBOLS.items():
        assert expected <= _defined_names(REPO_ROOT / path)


def test_architecture_laws_product_inventory_and_eight_operator_algebra_are_exact() -> (
    None
):
    document = SPEC.read_text(encoding="utf-8")
    laws = " ".join(_section(document, "Architecture Law Reconciliation").split())
    for value in (
        "AST / authored syntax != semantic model != script RelationIR != Project semantic facts != canonical Project Logical IR != optimizer memo != chosen target plan != physical SQL strategy",
        "declaration occurrence != semantic-fact occurrence != plan node != output value != use != input slot != ProjectIR local ref != future persistent cache identity",
        "BAG semantics remain default",
        "definition != use != DAG sharing != materialization != execution count",
        "producer output -> exact use -> exact consumer slot = direct topology authority",
        "semantic provenance use != intra-relation operator flow",
        "final semantic field identity != intermediate plan-local value identity",
        "direct topology != derived reachability/topological/equivalence analysis",
        "constructor validity != independent verification",
        "inspection/query/serialization != semantic authority",
        "canonical bytes != occurrence identity != persistent identity",
        "ordinary cycle != recursion",
        "CanonicalProjectIR != OptimizationMemo != ChosenTargetPlan",
    ):
        assert value in laws

    inventory = _table(_section(document, "Complete Private Product Inventory"))
    assert len(inventory) == 11
    assert all(row[1] and row[2] for row in inventory)
    assert tuple(ProjectIRLogicalOperatorKind) == (
        ProjectIRLogicalOperatorKind.RELATION_INPUT,
        ProjectIRLogicalOperatorKind.ROW_FILTER,
        ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
        ProjectIRLogicalOperatorKind.RESULT_FILTER,
        ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
        ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ProjectIRLogicalOperatorKind.RELATION_ORDERING,
        ProjectIRLogicalOperatorKind.LIMIT,
    )
    assert tuple(ProjectIRVerificationStatus) == (
        ProjectIRVerificationStatus.VERIFIED,
        ProjectIRVerificationStatus.INVALID,
    )
    assert tuple(ProjectIRAnalysisKind) == (
        ProjectIRAnalysisKind.REVERSE_USE_INDEX,
        ProjectIRAnalysisKind.TOPOLOGICAL_ORDER,
        ProjectIRAnalysisKind.REACHABILITY,
        ProjectIRAnalysisKind.SEMANTIC_EQUIVALENCE_CANDIDATES,
    )
    assert ProjectIRProvidedPropertySlot.MULTIPLICITY.value == "multiplicity"
    assert PROJECT_IR_INSPECTION_FORMAT == "pietto.project-ir-inspection.v1"
    assert ProjectIRPureStatus.INVALID_ENDPOINT_RELATION.value == (
        "invalid_endpoint_relation"
    )


def test_real_e2e_differential_negative_and_order_assurance_are_published() -> None:
    e2e_functions = _function_names(
        REPO_ROOT
        / "tests/test_phase61_slice10_real_authored_multi_module_project_ir_e2e.py"
    )
    assert {
        "test_real_authored_project_reaches_complete_verified_inspection",
        "test_real_mixed_project_preserves_terminal_and_independent_component",
        "test_fresh_snapshot_scopes_keep_runtime_identity_out_of_canonical_bytes",
    } <= e2e_functions
    differential_functions = _function_names(
        REPO_ROOT / "tests/test_phase61_slice11_differential_compatibility.py"
    )
    assert {
        "test_four_hash_seeds_preserve_exact_observation_and_inspection_bytes",
        "test_all_available_supported_interpreters_and_combined_cases_match",
        "test_relocation_creation_order_cwd_ambient_and_operation_order_do_not_leak",
        "test_isolated_installed_wheel_matches_and_proves_import_origin",
        "test_real_semantic_non_concrete_and_cycle_blocking_are_differentially_exact",
        "test_invalid_verifier_and_pure_rejections_use_typed_normalized_outcomes",
    } <= differential_functions

    probe_tree = ast.parse(PROBE.read_text(encoding="utf-8"), filename=str(PROBE))
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(probe_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert "sorted" not in called
    probe_source = PROBE.read_text(encoding="utf-8")
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "lru_cache",
        "functools.cache",
        "shelve",
        "pickle",
    ):
        assert forbidden not in probe_source


def test_public_compatibility_is_zero_delta_and_project_ir_remains_private() -> None:
    assert version("pietto") == "0.1.0"
    assert project_package.__all__ == ()
    for name in (
        "ProjectIRProjectPlan",
        "ProjectIRVerificationResult",
        "ProjectIRInspection",
        "ProjectIRPipelineResult",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
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

    if _git("rev-parse", "--is-shallow-repository") != "true":
        changed_production = tuple(
            _git(
                "diff",
                "--name-only",
                f"{PHASE61_BASE}..{_PUBLISHED_UNITS[-1][1]}",
                "--",
                "src",
            ).splitlines()
        )
        assert changed_production == _PHASE61_PRODUCTION_PATHS
        assert (
            _git(
                "diff",
                "--name-only",
                f"{PHASE61_BASE}..{_PUBLISHED_UNITS[-1][1]}",
                "--",
                "src/pietto/__init__.py",
                "src/pietto/_project/__init__.py",
                "src/pietto/cli.py",
                "src/pietto/ir/model.py",
                "src/pietto/sql",
                "src/pietto/_project_explain",
                "docs/spec/cli-json-v1.md",
                "docs/spec/project-cli-json-v2.md",
                "docs/spec/semantic-metadata-artifact-v1.md",
                "docs/spec/pietto-config-v1.md",
                "pyproject.toml",
                "uv.lock",
                ".github/workflows",
                "grammar",
            )
            == ""
        )


def test_deferred_subjects_self_owned_open_and_exact_later_owners_are_closed() -> None:
    document = SPEC.read_text(encoding="utf-8")
    deferred = _table(_section(document, "Deferred-Subject Reconciliation"))
    assert tuple(row[2] for row in deferred) == (
        "Phase 62",
        "Phase 63",
        "Phase 64",
        "Phase 65",
        "Phase 66",
        "Phase 67",
        "Phase 68",
        "Phase 69",
        "Phase 70",
        "Dedicated unnumbered recursion owner",
        "Dedicated unnumbered incremental owner",
    )
    assert (
        tuple(row[1] for row in deferred)
        == ("`TRANSFERRED_TO_EXACT_LATER_OWNER`",) * 11
    )

    self_owned = _table(_section(document, "Self-Owned-Open Audit"))
    terminals = {
        "CLOSED",
        "PUBLISHED_NEGATIVE_STATE",
        "PUBLISHED_CONSERVATIVE_STATE",
        "TRANSFERRED_TO_EXACT_LATER_OWNER",
        "INTENTIONALLY_OUT_OF_SCOPE",
    }
    assert all(row[1].strip("`") in terminals and row[2] for row in self_owned)
    assert not {"OPEN", "UNASSIGNED", "UNKNOWN_OWNER"} & {
        row[1].strip("`") for row in self_owned
    }
    assert "PHASE61_SELF_OWNED_OPEN = 0" in document

    markers = ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    historical_specs = tuple(
        REPO_ROOT / "docs/spec" / spec
        for _unit, _owner, spec, _test, _production in _UNIT_AUTHORITIES[:-1]
    )
    historical_tests = tuple(
        REPO_ROOT / "tests" / test
        for _unit, _owner, _spec, test, _production in _UNIT_AUTHORITIES[:-1]
    )
    product_paths = tuple(REPO_ROOT / path for path in _PHASE61_PRODUCTION_PATHS)
    assert not any(
        marker in path.read_text(encoding="utf-8")
        for path in (*historical_specs, *historical_tests, *product_paths, PROBE)
        for marker in markers
    )


def test_phase62_readiness_and_historical_unstarted_state_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    readiness = _table(_section(document, "Phase 62 Readiness Inventory"))
    assert len(readiness) == 13
    assert all(row[0] and row[1] for row in readiness)
    normalized = " ".join(_section(document, "Phase 62 Readiness Inventory").split())
    for distinction in (
        "relationship traversal != correlation",
        "relationship cardinality != container multiplicity",
        "key/FD evidence != inferred uniqueness",
        "grain evidence != grain comparison",
        "fanout != join count",
        "JOIN semantics != physical SQL join strategy",
        "multi-fact alignment != arbitrary common-column matching",
        "fresh architecture/source audit and route lock",
    ):
        assert distinction in normalized

    handoff_section = _section(document, "Phase 62 Handoff Boundary")
    handoff = " ".join(handoff_section.split())
    assert (
        "Phase 62 — Relationships/JOIN, key/FD evidence, grain comparison, "
        "fanout/multiplicity, and multi-fact alignment"
    ) in handoff
    assert "Phase 62 = NEXT / NOT IMPLEMENTED" in handoff
    assert "contains no Phase 62 route table" in handoff
    assert "| Slice |" not in handoff_section

    # Source-checkout assurance is distinct from repository-history reconstruction.
    scope = " ".join(_section(document, "Scope And Live Result").split())
    for evidence in (
        "Slice 12 is documentation/static assurance only",
        "relationship/JOIN/grain",
        "A real Phase-61-owned product gap would stop this audit",
        "the live audit found none",
    ):
        assert evidence in scope

    inventory = " ".join(
        _section(document, "Complete Private Product Inventory").split()
    )
    for evidence in (
        "`ProjectIRLogicalOperatorKind` has exactly",
        "RELATION_INPUT",
        "ROW_FILTER",
        "GROUP_AGGREGATE",
        "RESULT_FILTER",
        "WINDOW_EVALUATION",
        "FINAL_PROJECTION",
        "RELATION_ORDERING",
        "LIMIT",
        "There is no hidden ninth operator",
    ):
        assert evidence in inventory

    historical_delta = " ".join(
        _section(document, "Reader Closure And Slice 12 Delta").split()
    )
    for evidence in (
        "production 0",
        "grammar/generated 0",
        "package/deps 0",
        "workflow 0",
        "public schema 0",
    ):
        assert evidence in historical_delta


def test_slice12_reader_closure_zero_delta_and_non_circular_lifecycle_are_exact() -> (
    None
):
    document = SPEC.read_text(encoding="utf-8")
    reader = _section(document, "Reader Closure And Slice 12 Delta")
    normalized_reader = " ".join(reader.split())
    assert all(path in reader for path in _SLICE12_STATIC_PATHS)
    assert "A2/M4/D0" in reader
    assert "sole direct reader" in normalized_reader
    assert all((REPO_ROOT / path).is_file() for path in _SLICE12_STATIC_PATHS)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in _SLICE12_STATIC_PATHS
    )
    for value in (
        "production        0",
        "grammar/generated 0",
        "goldens           0",
        "package/deps      0",
        "workflow          0",
        "public schema     0",
        "version           0.1.0",
    ):
        assert value in reader

    lifecycle = " ".join(_section(document, "Lifecycle And Publication").split())
    for value in (
        "Phase 61: ACTIVE / COMPLETION CANDIDATE",
        "Slices 1-11: COMPLETED / PUBLISHED",
        "Slice 12: CURRENT / COMPLETION CANDIDATE",
        "both Slice 5 prerequisites: COMPLETED / PUBLISHED",
        "Phase61 self-owned-open: 0",
        "Phase 62: NEXT / NOT IMPLEMENTED",
        "Phase 61 = COMPLETED",
        "Slices 1-12 = COMPLETED",
        "No local generated, golden, or package auxiliary is required",
        "Complete Phase 61 Project IR",
    ):
        assert value in lifecycle

    source_tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "rglob"
        for node in ast.walk(source_tree)
    )
