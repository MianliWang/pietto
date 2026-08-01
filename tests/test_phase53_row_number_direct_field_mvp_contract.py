from __future__ import annotations

import ast
import dataclasses
import hashlib
import subprocess
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_post_review_repair_gate2_is_active,
)

import pytest

import pietto
import pietto.semantic.window_analysis as window_analysis
from pietto import _window_identity
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    build_row_number_window_result_project_fact,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    NameExpr,
    QueryDef,
    Script,
    SatisfyingClause,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-row-number-direct-field-mvp-contract-v1.md"
SEMANTIC_REL = "src/pietto/semantic/window_analysis.py"
SELF_REL = "tests/test_phase53_row_number_direct_field_mvp_contract.py"
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"

SPEC_TITLE = "Phase 53 Slice 7 row_number Direct-field MVP Contract v1"
SLICE7_PLAN_H2 = "Slice 7 row_number Direct-field MVP"
SPEC_H2 = (
    "Status And Slice Identity",
    "Existing Syntax AST And Identity Authority",
    "Direct-field Candidate And Exact Supported Subset",
    "Selected-output Composition",
    "Source And Relation Scope",
    "Exact row_number Identity And Legality",
    "Private Semantic Integration",
    "Generic Signature Result Type And Nullability",
    "Semantic Result And Unsupported Evidence",
    "Diagnostic Contract",
    "Direct-field Binding",
    "WINDOW Stage And Semantic Fact",
    "Project Result Identity Dependency And Provenance",
    "Standalone Project Fact And No Persistence",
    "Row-schema And Downstream Visibility",
    "Clause Nesting Same-select And Multiple-window Boundary",
    "Grouping Aggregate Satisfying And Let Boundary",
    "IR And SQL Fail-closed Boundary",
    "Public Privacy And Serialization Boundary",
    "Positive Behavior Matrix",
    "Negative And Fail-closed Matrix",
    "Behavior Parity And Protected Surfaces",
    "Reader Closure Inventory And Repository States",
    "Validation Depth-one CI And Gate 3",
    "Deferred Ownership And Stop Conditions",
)

EXPECTED_TEST_FUNCTIONS = (
    "test_slice7_artifact_paths_headings_and_lifecycle_are_exact",
    "test_existing_window_syntax_ast_identity_and_span_authority_is_locked",
    "test_direct_field_candidate_output_and_later_slice_ownership_are_exact",
    "test_exact_row_number_identity_legality_and_case_policy_are_exact",
    "test_row_number_zero_argument_generic_signature_is_exact",
    "test_row_number_signature_binding_returns_builtin_int_without_variables",
    "test_row_number_non_null_formula_evaluates_exactly",
    "test_window_analysis_supported_result_shape_is_exact",
    "test_bare_and_immediate_qualified_order_field_success",
    "test_table_query_direct_source_and_immediate_upstream_success",
    "test_one_window_coexists_with_current_legal_non_window_outputs",
    "test_window_occurrence_identity_uses_source_relation_ordinal_and_span",
    "test_concrete_result_is_int_non_null_window_stage",
    "test_window_unsupported_evidence_and_diagnostic_mapping_are_exact",
    "test_wrong_row_number_arity_uses_pie_s2104",
    "test_unsupported_clause_and_shape_diagnostics_use_pie_s2103",
    "test_partition_shapes_remain_unsupported",
    "test_local_order_cardinality_and_direction_remain_unsupported",
    "test_computed_unknown_and_invalid_qualified_order_fields_fail_closed",
    "test_original_source_qualifier_does_not_cross_immediate_upstream",
    "test_group_aggregate_satisfying_and_let_relations_remain_unsupported",
    "test_window_expression_placements_outside_direct_select_fail_closed",
    "test_multiple_nested_and_same_select_windows_remain_unsupported",
    "test_where_final_order_and_limit_can_coexist_without_window_alias_use",
    "test_project_window_fact_supports_table_query_and_upstream_matrix",
    "test_project_relation_input_and_order_occurrences_are_exact",
    "test_project_dependency_edges_preserve_role_and_first_occurrence_order",
    "test_project_result_identity_and_derived_provenance_are_exact",
    "test_project_fact_is_transient_not_model_or_schema_state",
    "test_window_alias_is_not_downstream_or_final_order_visible",
    "test_ir_lowering_fails_closed_with_pie_i1000",
    "test_postgres_and_private_mysql_requests_fail_before_sql_lowering",
    "test_cli_json_metadata_project_json_and_public_exports_remain_private",
    "test_ordinary_scalar_direct_field_and_final_order_behavior_is_unchanged",
    "test_aggregate_grouped_let_and_diagnostics_behavior_is_unchanged",
    "test_non_row_number_window_identities_remain_semantically_unsupported",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice7_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_and_no_behavior_boundaries_are_locked",
)
CARDINALITIES = (
    1,
    6,
    3,
    12,
    1,
    1,
    1,
    4,
    4,
    4,
    6,
    4,
    1,
    8,
    4,
    10,
    4,
    6,
    8,
    2,
    6,
    6,
    6,
    5,
    4,
    4,
    2,
    4,
    3,
    4,
    2,
    2,
    6,
    6,
    6,
    7,
    1,
    1,
    1,
    1,
    1,
)

ADDED_PATHS = {
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md",
    "src/pietto/semantic/window_input_analysis.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
}
MODIFIED_PATHS = {
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/group_by.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_navigation_analysis.py",
    "src/pietto/semantic/window_partition_analysis.py",
    "src/pietto/semantic/window_order_analysis.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/window_semantics.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase15_semantic_completion_audit.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
}
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS

COMPILER_DIGEST = "c9f1c8ed5b44a3215b3d9873d152d26f404ae6032235cbd7cdf7439e1ef73f1a"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_DIGEST = "5cbd463b15073f4b66a90d48370b4d692893840803af9cdba214888746c7d018"
FOCUSED_SHA256 = "764c5879e93871b253e875ce1e8145ce3a998d48a94b578f8af9d31f9562e5ee"
OVERLAY_SHA256 = "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
FORMATTER_SHA256 = "5920e1a21f135b2537e8295b13c8bc6fa2962423812ffc3cbe1e52663e924daf"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _phase53_gate2_paths(name: str) -> set[str]:
    if _git_output(["rev-parse", "HEAD"]) in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
    }:
        path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        values: dict[str, set[str]] = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id
                in {
                    "ADDED_PATHS",
                    "NON_READER_MODIFIED_PATHS",
                    "MECHANICAL_READER_PATHS",
                }
            ):
                value = ast.literal_eval(node.value)
                assert isinstance(value, set)
                values[node.targets[0].id] = value
        if name == "ADDED_PATHS":
            return values["ADDED_PATHS"]
        if name == "MODIFIED_PATHS":
            return (
                values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"]
            )
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _git_optional_ref(ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 1)
    assert result.stderr == ""
    return result.stdout.strip() or None


def _repository_paths() -> tuple[str, ...]:
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


def _program(
    *,
    kind: str = "query",
    call: str = "row_number()",
    order: tuple[str, ...] = ("observed_at",),
    partition: tuple[str, ...] = (),
    direction: str | None = None,
    input_name: str = "rows",
    upstream: bool = False,
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
    where: bool = False,
    final_order: bool = False,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    if upstream:
        prefix += (
            "table intermediate:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        observed_at\n"
            "        label\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        rn = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        suffix = f" {direction}" if direction is not None else ""
        lines.extend(f"                {value}{suffix}" for value in order)
    lines.extend(f"        {value}" for value in after)
    if final_order:
        lines.extend(("    order by:", "        observed_at"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice7.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _direct_analysis(
    source: str,
    *,
    selected_output_ordinal: int | None = None,
) -> tuple[
    WindowExpressionSemanticFact | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        input_schema = semantic.model.source_row_schemas[target]
    else:
        assert isinstance(target, (TableDef, QueryDef))
        input_schema = semantic.model.relation_row_schemas[target]
    ordinal = selected_output_ordinal
    if ordinal is None:
        ordinal = next(
            index
            for index, selected in enumerate(relation.select_items)
            if isinstance(selected.expression, WindowExpr)
        )
    item = relation.select_items[ordinal]
    assert isinstance(item.expression, WindowExpr)
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_fact(
    *,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
) -> tuple[WindowExpressionSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_analysis(
        _program(
            kind=kind,
            order=(order,),
            upstream=upstream,
            before=before,
        )
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionSemanticFact)
    return result, relation


def _project_fact(
    *,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    semantic_fact, relation = _canonical_fact(
        kind=kind,
        qualified=qualified,
        upstream=upstream,
    )
    script, parsed_relation = _parsed_relation(
        _program(
            kind=kind,
            order=(
                f"{'intermediate' if upstream else 'rows'}.observed_at"
                if qualified
                else "observed_at",
            ),
            upstream=upstream,
        )
    )
    assert parsed_relation == relation
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == ("intermediate" if upstream else "rows")
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=(ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE),
        name=upstream_definition.name,
        path="slice7.pietto",
        location=SourceLocation(path="slice7.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    schema = ProjectRowSchema(
        fields={
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp",
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            )
        }
    )
    item = parsed_relation.select_items[-1]
    result = build_row_number_window_result_project_fact(
        definition=parsed_relation,
        item=item,
        selected_output_ordinal=len(parsed_relation.select_items) - 1,
        source_id="slice7.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    assert result.semantic_fact == semantic_fact
    return result


def test_slice7_artifact_paths_headings_and_lifecycle_are_exact() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    assert [line[2:] for line in spec.splitlines() if line.startswith("# ")] == [
        SPEC_TITLE
    ]
    assert (
        tuple(line[3:] for line in spec.splitlines() if line.startswith("## "))
        == SPEC_H2
    )
    assert not any(line.startswith("### ") for line in spec.splitlines())
    assert [line[3:] for line in plan.splitlines() if line.startswith("## ")].count(
        SLICE7_PLAN_H2
    ) == 1
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    functions = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert CARDINALITIES == (
        1,
        6,
        3,
        12,
        1,
        1,
        1,
        4,
        4,
        4,
        6,
        4,
        1,
        8,
        4,
        10,
        4,
        6,
        8,
        2,
        6,
        6,
        6,
        5,
        4,
        4,
        2,
        4,
        3,
        4,
        2,
        2,
        6,
        6,
        6,
        7,
        1,
        1,
        1,
        1,
        1,
    )
    assert sum(CARDINALITIES) == 168


@pytest.mark.parametrize("case", range(6))
def test_existing_window_syntax_ast_identity_and_span_authority_is_locked(
    case: int,
) -> None:
    order = ("rows.observed_at",) if case % 2 else ("observed_at",)
    script, relation = _parsed_relation(_program(order=order))
    del script
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assertions = (
        isinstance(expression, WindowExpr),
        expression.spec.partition_by == (),
        len(expression.spec.order_by) == 1,
        expression.identity.namespace == (),
        expression.identity.name == "row_number",
        expression.span.path == "slice7.pietto",
    )
    assert assertions[case]


@pytest.mark.parametrize("case", range(3))
def test_direct_field_candidate_output_and_later_slice_ownership_are_exact(
    case: int,
) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "Candidate A",
        "One legal window output may coexist",
        "Slice 15 retains Window IR",
    )
    assert required[case] in docs


@pytest.mark.parametrize(
    "call",
    (
        "row_number()",
        "Row_Number()",
        "ROW_NUMBER()",
        "analytics.row_number()",
        "rank()",
        "dense_rank()",
        "percent_rank()",
        "cume_dist()",
        "ntile(4)",
        "lag()",
        "lead()",
        "custom()",
    ),
)
def test_exact_row_number_identity_legality_and_case_policy_are_exact(
    call: str,
) -> None:
    script, relation = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    if call in {"row_number()", "rank()", "dense_rank()"}:
        assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
        assert expression in semantic.model.expression_value_types
    elif call in {"percent_rank()", "cume_dist()", "ntile(4)"}:
        assert not any(
            item.code in {"PIE-S2103", "PIE-S2104"} for item in semantic.diagnostics
        )
        assert expression in semantic.model.expression_value_types
    elif call in {"lag()", "lead()"}:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2104"]
        assert len(matching) == 1
        assert matching[0].message == (
            f"Invalid arguments for function {call.removesuffix('()')}: "
            "expected 1 through 3, got 0"
        )
        assert matching[0].location.line == expression.call.span.line
    else:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2103"]
        assert len(matching) == 1
        assert matching[0].location.line == expression.call.span.line


def test_row_number_zero_argument_generic_signature_is_exact() -> None:
    signature = window_analysis._ROW_NUMBER_SIGNATURE
    assert signature.type_variables == ()
    assert signature.parameters == ()
    result_expression = signature.result
    assert isinstance(result_expression, ConcreteTypeExpression)
    assert result_expression.logical_type.name == "Int"
    assert result_expression.logical_type.kind is TypeKind.BUILTIN


def test_row_number_signature_binding_returns_builtin_int_without_variables() -> None:
    result = bind_signature(window_analysis._ROW_NUMBER_SIGNATURE, ())
    assert isinstance(result, SignatureMatch)
    assert (
        result.bindings == result.constraint_evidence == result.omitted_positions == ()
    )
    assert (result.result_type.name, result.result_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )


def test_row_number_non_null_formula_evaluates_exactly() -> None:
    result = evaluate_signature_result_nullability(
        window_analysis._ROW_NUMBER_RESULT_FORMULA,
        NullabilityEvaluationContext(argument_nullabilities=(), omitted_positions=()),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("kind", "qualified"),
    (("query", False), ("query", True), ("table", False), ("table", True)),
)
def test_window_analysis_supported_result_shape_is_exact(
    kind: str, qualified: bool
) -> None:
    fact, _ = _canonical_fact(kind=kind, qualified=qualified)
    assert fact.identity.name == "row_number"
    assert fact.stage is WindowExpressionStage.WINDOW
    assert fact.result.kind is WindowResultAvailabilityKind.CONCRETE


@pytest.mark.parametrize(
    ("qualified", "upstream"),
    ((False, False), (True, False), (False, True), (True, True)),
)
def test_bare_and_immediate_qualified_order_field_success(
    qualified: bool, upstream: bool
) -> None:
    fact, _ = _canonical_fact(qualified=qualified, upstream=upstream)
    order = fact.expression.spec.order_by[0].expression
    assert isinstance(order, DottedNameExpr if qualified else NameExpr)


@pytest.mark.parametrize(
    ("kind", "upstream"),
    (("table", False), ("query", False), ("table", True), ("query", True)),
)
def test_table_query_direct_source_and_immediate_upstream_success(
    kind: str, upstream: bool
) -> None:
    fact, relation = _canonical_fact(kind=kind, upstream=upstream)
    assert isinstance(relation, TableDef if kind == "table" else QueryDef)
    assert fact.occurrence.relation_name == "ranked"


@pytest.mark.parametrize(
    "ordinary",
    (
        "id",
        "renamed = id",
        "literal = 1",
        "text = label",
        "sum_id = id + 1",
        "lowered = lower(label)",
    ),
)
def test_one_window_coexists_with_current_legal_non_window_outputs(
    ordinary: str,
) -> None:
    script, relation = _parsed_relation(_program(before=(ordinary,)))
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression in semantic.model.expression_value_types
    assert "rn" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("ordinary_count", range(4))
def test_window_occurrence_identity_uses_source_relation_ordinal_and_span(
    ordinary_count: int,
) -> None:
    before = tuple(
        "id" if index == 0 else f"id_{index} = id" for index in range(ordinary_count)
    )
    fact, relation = _canonical_fact(before=before)
    assert fact.occurrence.source_id == "slice7.pietto"
    assert fact.occurrence.relation_name == relation.name
    assert fact.occurrence.selected_output_ordinal == ordinary_count
    assert fact.occurrence.span == fact.expression.span


def test_concrete_result_is_int_non_null_window_stage() -> None:
    fact, _ = _canonical_fact()
    value_type = fact.result.value_type
    assert value_type is not None
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.name == "Int"
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert fact.stage is WindowExpressionStage.WINDOW


@pytest.mark.parametrize("case", range(8))
def test_window_unsupported_evidence_and_diagnostic_mapping_are_exact(
    case: int,
) -> None:
    sources = (
        _program(call="percent_rank()"),
        _program(call="row_number(id)"),
        _program(partition=("id + 1",)),
        _program(order=("observed_at", "id")),
        _program(direction="desc"),
        _program(order=("id + 1",)),
        _program(order=("missing",)),
        _program(order=("other.observed_at",)),
    )
    result, diagnostics, _, _ = _direct_analysis(sources[case])
    if case in {3, 4}:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []
        return
    assert isinstance(result, WindowExpressionUnsupported)
    assert result.reason.strip()
    expected = "PIE-S2104" if case == 1 else "PIE-S2102" if case >= 6 else "PIE-S2103"
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize(
    "arguments", ("id", "id, observed_at", "id, observed_at, label", "id,")
)
def test_wrong_row_number_arity_uses_pie_s2104(arguments: str) -> None:
    result, diagnostics, _, relation = _direct_analysis(
        _program(call=f"row_number({arguments})")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert diagnostics[0].message == (
        "Invalid arguments for function row_number: expected 0, got "
        f"{len(expression.call.arguments)}"
    )


@pytest.mark.parametrize("case", range(10))
def test_unsupported_clause_and_shape_diagnostics_use_pie_s2103(case: int) -> None:
    sources = (
        _program(call="percent_rank()"),
        _program(call="cume_dist()"),
        _program(partition=("id + 1",)),
        _program(order=("observed_at", "id")),
        _program(direction="asc"),
        _program(direction="desc"),
        _program(order=("id + 1",)),
        _program(order=("lower(label)",)),
        _program(order=("1",)),
        _program(call="analytics.row_number()"),
    )
    result, diagnostics, _, _ = _direct_analysis(sources[case])
    if case in {3, 4, 5}:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    "partition", (("id",), ("id", "label"), ("rows.id",), ("id + 1",))
)
def test_partition_shapes_remain_unsupported(partition: tuple[str, ...]) -> None:
    result, diagnostics, _, _ = _direct_analysis(_program(partition=partition))
    if partition == ("id + 1",):
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("order", "direction"),
    (
        ((), None),
        (("observed_at", "id"), None),
        (("observed_at", "id", "label"), None),
        (("observed_at",), "asc"),
        (("observed_at",), "desc"),
        (("rows.observed_at",), "asc"),
    ),
)
def test_local_order_cardinality_and_direction_remain_unsupported(
    order: tuple[str, ...], direction: str | None
) -> None:
    source = _program(
        order=order, partition=("id",) if not order else (), direction=direction
    )
    result, diagnostics, _, _ = _direct_analysis(source)
    if not order:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("order", "code"),
    (
        ("id + 1", "PIE-S2103"),
        ("lower(label)", "PIE-S2103"),
        ("1", "PIE-S2103"),
        ("missing", "PIE-S2102"),
        ("other.observed_at", "PIE-S2102"),
        ("rows.missing", "PIE-S2102"),
        ("rows.extra.observed_at", "PIE-S2102"),
        ("rn", "PIE-S2102"),
    ),
)
def test_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    order: str, code: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(_program(order=(order,)))
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]


@pytest.mark.parametrize("kind", ("table", "query"))
def test_original_source_qualifier_does_not_cross_immediate_upstream(kind: str) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(kind=kind, upstream=True, order=("rows.observed_at",))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize("case", range(6))
def test_group_aggregate_satisfying_and_let_relations_remain_unsupported(
    case: int,
) -> None:
    script, relation = _parsed_relation(_program())
    span = relation.span
    if case in {0, 1}:
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif case in {2, 3}:
        argument = () if case == 2 else (NameExpr(span=span, name="id"),)
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(
                            span=span,
                            name="count" if case == 2 else "sum",
                        ),
                        arguments=argument,
                    ),
                ),
            ),
        )
    elif case == 4:
        relation = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span,
                expression=NameExpr(span=span, name="id"),
            ),
        )
    else:
        relation = dataclasses.replace(
            relation,
            let_clause=LetClause(
                span=span,
                bindings=(
                    LetBinding(
                        span=span,
                        name="local_id",
                        expression=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=relation.select_items[0],
        selected_output_ordinal=0,
        source_id="slice7.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(6))
def test_window_expression_placements_outside_direct_select_fail_closed(
    case: int,
) -> None:
    semantic_source = _read("src/pietto/semantic/expressions.py")
    protected = (
        "if isinstance(expression, WindowExpr):",
        "_unknown_function_diagnostic(",
        "return _UNKNOWN_VALUE_TYPE",
        "where clause",
        "order by",
        "allow_aggregate_projection",
    )
    assert protected[case] in semantic_source


@pytest.mark.parametrize("case", range(6))
def test_multiple_nested_and_same_select_windows_remain_unsupported(case: int) -> None:
    script, relation = _parsed_relation(_program())
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(first, dataclasses.replace(first, alias=f"rn_{case}")),
    )
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=relation.select_items[case % 2],
        selected_output_ordinal=case % 2,
        source_id="slice7.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier="rows",
        value_types={},
        diagnostics=diagnostics,
    )
    assert type(result) is WindowExpressionSemanticFact
    assert diagnostics == []
    assert result.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize(
    ("where", "final_order", "limit"),
    (
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, True, True),
    ),
)
def test_where_final_order_and_limit_can_coexist_without_window_alias_use(
    where: bool, final_order: bool, limit: bool
) -> None:
    script, relation = _parsed_relation(
        _program(where=where, final_order=final_order, limit=limit)
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assert expression in semantic.model.expression_value_types
    assert "rn" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("kind", "upstream"),
    (("query", False), ("table", False), ("query", True), ("table", True)),
)
def test_project_window_fact_supports_table_query_and_upstream_matrix(
    kind: str, upstream: bool
) -> None:
    fact = _project_fact(kind=kind, upstream=upstream)
    assert isinstance(fact, WindowResultProjectFact)
    assert fact.result_identity.definition.name == "ranked"


@pytest.mark.parametrize("case", range(4))
def test_project_relation_input_and_order_occurrences_are_exact(case: int) -> None:
    fact = _project_fact(qualified=bool(case % 2), upstream=bool(case // 2))
    occurrences = fact.dependency_occurrences
    assert tuple(item.global_ordinal for item in occurrences) == (0, 1)
    assert tuple(item.role_ordinal for item in occurrences) == (0, 0)
    assert tuple(item.role for item in occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target.kind for item in occurrences) == (
        ProjectRowDependencyNodeKind.RELATION_INPUT,
        ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
    )


@pytest.mark.parametrize("qualified", (False, True))
def test_project_dependency_edges_preserve_role_and_first_occurrence_order(
    qualified: bool,
) -> None:
    fact = _project_fact(qualified=qualified)
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(4))
def test_project_result_identity_and_derived_provenance_are_exact(case: int) -> None:
    fact = _project_fact(kind="table" if case % 2 else "query", upstream=case >= 2)
    assert fact.result_identity.output_name == "rn"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location is not None


@pytest.mark.parametrize("case", range(3))
def test_project_fact_is_transient_not_model_or_schema_state(case: int) -> None:
    source = _read("src/pietto/_project/model.py") + _read(
        "src/pietto/_project/window_persistence.py"
    )
    required = (
        "build_project_window_persistence(",
        "relation_window_result_facts:",
        "ProjectRowResultRole.WINDOW_RESULT",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(4))
def test_window_alias_is_not_downstream_or_final_order_visible(case: int) -> None:
    script, relation = _parsed_relation(_program())
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    field = semantic.model.relation_row_schemas[relation].fields["rn"]
    assertions = (
        expression in semantic.model.expression_value_types,
        field.resolved_type.name == "Int",
        field.nullability is EffectiveNullability.NON_NULL,
        "relation_window_result_facts" in _read("src/pietto/_project/model.py"),
    )
    assert assertions[case]


@pytest.mark.parametrize("kind", ("query", "table"))
def test_ir_lowering_fails_closed_with_pie_i1000(kind: str) -> None:
    script, relation = _parsed_relation(_program(kind=kind))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("backend", ("postgres", "mysql"))
def test_postgres_and_private_mysql_requests_fail_before_sql_lowering(
    backend: str,
) -> None:
    del backend
    script, relation = _parsed_relation(_program())
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[0].expression), semantic.model
    )
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_cli_json_metadata_project_json_and_public_exports_remain_private(
    case: int,
) -> None:
    protected = (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/semantic/__init__.py",
    )
    assert _git_output(["diff", "--", protected[case]]) == ""
    assert not hasattr(pietto, "WindowExpressionSemanticFact")


@pytest.mark.parametrize("case", range(6))
def test_ordinary_scalar_direct_field_and_final_order_behavior_is_unchanged(
    case: int,
) -> None:
    sources = (
        _program(before=("id",)),
        _program(before=("renamed = id",)),
        _program(before=("text = label",)),
        _program(before=("lowered = lower(label)",)),
        _program(where=True),
        _program(final_order=True),
    )
    script, _ = _parsed_relation(sources[case])
    semantic = analyze(script)
    assert not any(
        item.code in {"PIE-S2102", "PIE-S2103"} for item in semantic.diagnostics
    )


@pytest.mark.parametrize("case", range(6))
def test_aggregate_grouped_let_and_diagnostics_behavior_is_unchanged(case: int) -> None:
    protected = (
        "src/pietto/semantic/aggregates.py",
        "src/pietto/semantic/grouping.py",
        "src/pietto/semantic/let_bindings.py",
        "src/pietto/semantic/satisfying.py",
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/__init__.py",
    )
    assert _git_output(["diff", "--", protected[case]]) == ""


@pytest.mark.parametrize(
    "name",
    ("rank", "dense_rank", "percent_rank", "cume_dist", "ntile", "lag", "lead"),
)
def test_non_row_number_window_identities_remain_semantically_unsupported(
    name: str,
) -> None:
    call = "ntile(4)" if name == "ntile" else f"{name}()"
    script, _ = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    assert all(item.code != "PIE-S2103" for item in semantic.diagnostics)
    if name in {"lag", "lead"}:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2104"]
        assert len(matching) == 1
        assert matching[0].message == (
            f"Invalid arguments for function {name}: expected 1 through 3, got 0"
        )
    else:
        assert all(item.code != "PIE-S2104" for item in semantic.diagnostics)


def test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked() -> None:
    expected = {
        "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
        "src/pietto/ast_nodes.py": "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
        "src/pietto/ast_builder.py": "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
        "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
        "src/pietto/_window_identity.py": "d1223f7095790dc08ffc176c103ae6180cd9e03773ddf9763448d482d6984c9b",
        "src/pietto/semantic/analyzer.py": "7a6f2830bf3710edab3ba5a8c4a72e90c6e44de19fe19ddd2b54b5d703277b32",
        "src/pietto/semantic/model.py": "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
        "src/pietto/semantic/catalog.py": "f566f39395e3bdc933e60d15e740749255dd3749cf3907684240e4b43dfc9e40",
    }
    assert {path: _sha256(path) for path in expected} == expected
    assert (
        sum(path.is_file() for path in (REPO_ROOT / "src/pietto/generated").iterdir())
        == 8
    )


def test_reader_hash_inventory_and_nested_closure_is_exact() -> None:
    repository_paths = _repository_paths()
    compiler_paths = [
        REPO_ROOT / path
        for path in repository_paths
        if path in {"Makefile", "grammar/Pietto.g4"} or path.startswith("src/pietto/")
    ]
    semantic_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/semantic"
        and path.endswith(".py")
    )
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    project_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/_project"
        and path.endswith(".py")
    )
    assert (
        len(compiler_paths),
        len(semantic_paths),
        len(phase15_paths),
        len(project_paths),
    ) == (102, 36, 33, 27)
    assert _digest(tuple(compiler_paths)) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_DIGEST


def test_slice7_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_post_review_repair_gate2_is_active():
        return
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = tracked | untracked
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    assert dirty in (set(), ALLOWLIST_PATHS, slice14_modified | slice14_added)
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    if dirty:
        assert tracked in (MODIFIED_PATHS, slice14_modified)
        assert untracked in (ADDED_PATHS, slice14_added)
        assert _git_output(["branch", "--show-current"]) == "main"
        assert head == main == origin_main
        assert head in (
            BASE_HEAD_SHA,
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        )
    else:
        assert main in (None, head)
        assert origin_main in (None, head)


def test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact() -> (
    None
):
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    readable = {path for path in (*tracked, *untracked) if (REPO_ROOT / path).is_file()}
    assert len(readable) == 912
    assert sum(path.endswith(".py") for path in readable) == 561
    assert sum(path.endswith(".md") for path in readable) == 255
    test_modules = {
        path
        for path in readable
        if path.startswith("tests/test_") and path.endswith(".py")
    }
    assert len(test_modules) == 458
    top_level_tests = 0
    for relative in sorted(test_modules):
        tree = ast.parse(_read(relative), filename=relative)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert top_level_tests == 5089
    assert 9580 == 9199 + 381
    assert 9580 - 185 == 9395
    assert (117, 70, 11, 106, 3488, 13171) == (117, 70, 11, 106, 3488, 13171)
    assert (FOCUSED_SHA256, OVERLAY_SHA256, FORMATTER_SHA256) == (
        "764c5879e93871b253e875ce1e8145ce3a998d48a94b578f8af9d31f9562e5ee",
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
        "5920e1a21f135b2537e8295b13c8bc6fa2962423812ffc3cbe1e52663e924daf",
    )
    assert len(ALLOWLIST_PATHS) == 71
    assert len(MODIFIED_PATHS) == 68
    assert len(ADDED_PATHS) == 3


def test_validation_gate3_and_no_behavior_boundaries_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for required in (
        "A3/M61/D0",
        "62-path handwritten Python manifest",
        "3107 focused items",
        "9014 passed, 185 deselected",
        "9199 passes in each clean-CI Python job",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Add Phase 53 window-local ordering and direction",
        "Slice 15 retains Window IR",
        "0.1.0",
    ):
        assert required in docs
    assert (
        _git_output(
            ["diff", "--", "pyproject.toml", "uv.lock", ".github/workflows/ci.yml"]
        )
        == ""
    )
    assert (
        _window_identity.WindowFunctionRole.WINDOW_FUNCTION.value == "window_function"
    )


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
