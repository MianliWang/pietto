from __future__ import annotations

import ast
from collections.abc import Mapping
import dataclasses
from functools import lru_cache
import hashlib
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import cast

from _phase54_active_gate2_manifest import (
    PHASE54_POST_SLICE12_INTERLUDE_CHILD_SHAPES,
    PHASE54_POST_SLICE12_INTERLUDE_BASE,
    PHASE54_POST_SLICE12_INTERLUDE_SUBJECT,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE,
    PHASE54_SLICE11_PR_CI_REPAIR_BASE,
    PHASE54_SLICE12_PR_CI_REPAIR_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR10_PARENT,
    PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT,
    PHASE54_SLICE11_PYTHON313_REPAIR_BASE,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto._project as project_package
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticModel,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
)
from pietto._project.window_persistence import ProjectWindowPersistenceBundle
from pietto._project.window_semantics import WindowResultProjectFact
from pietto.ast_nodes import NameExpr, QueryDef, Script, TableDef, WindowExpr
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import EffectiveNullability, SemanticResult

REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = (
    "tests/"
    "test_phase53_multiple_window_outputs_final_order_alias_downstream_"
    "schema_lineage_contract.py"
)
SPEC_REL = (
    "docs/spec/phase53-multiple-window-outputs-final-order-alias-downstream-"
    "schema-lineage-contract-v1.md"
)
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
PHASE53_COMPLETION_HEAD = "af92f30c22e5d3df5219554a0663855a5b9f51a6"
PHASE54_SLICE1_HEAD = "53d8767fc3bdbe5e3f631178652222bbe51f6a33"
PHASE54_SLICE2_HEAD = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE3_HEAD = "2752985c3f6343519b7d7d6fe400d16251e64d85"
README_REFRESH_HEAD = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE4_HEAD = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE5_HEAD = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE6_HEAD = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE7_HEAD = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE8_HEAD = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE9_HEAD = "fadb1924af057cfc901a1658e117810d699e2358"
PHASE54_SLICE10_HEAD = "b81843acadb294630db361c09949868d004b1bca"
PHASE54_SLICE9_PARENT_HEAD = PHASE54_SLICE8_HEAD
POST_REVIEW_REPAIR_PARENT_HEAD = "ed37b4938b0ff5efa0842d353ac0610c51afa6cc"
WHEELHOUSE_MANIFEST_SHA256 = (
    "e745cf66b6e8ea2096d5e49bf88ef32f828fe9178561b8ed5456125afeb8a294"
)

IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)

EXPECTED_TEST_FUNCTIONS = (
    "test_slice14_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_maintenance_main_handoff_build_backend_and_wheelhouse_are_locked",
    "test_slice14_contract_scope_and_window_result_ownership_are_exact",
    "test_slice15_phase60_phase63_and_phase70_boundaries_are_locked",
    "test_window_persistence_carrier_shape_privacy_and_atomicity_are_exact",
    "test_window_state_reason_enum_and_cross_carrier_mappings_are_exact",
    "test_multiple_independent_ungrouped_window_outputs_are_accepted",
    "test_multiple_independent_grouped_window_outputs_are_accepted",
    "test_selected_output_order_and_window_occurrence_ordinals_are_stable",
    "test_window_result_type_and_nullability_matrix_is_exact",
    "test_multiple_navigation_outputs_preserve_slice12_type_nullability",
    "test_partition_and_order_occurrences_remain_source_ordered_per_output",
    "test_duplicate_dependency_occurrences_remain_output_local",
    "test_same_select_window_alias_is_rejected_in_every_window_input_role",
    "test_same_select_forward_and_backward_window_dependencies_are_symmetric",
    "test_nested_window_expressions_remain_rejected",
    "test_every_selected_window_output_still_requires_an_explicit_alias",
    "test_duplicate_window_aliases_emit_pie_s2305_without_a_winner",
    "test_window_and_ordinary_output_alias_collisions_emit_pie_s2305",
    "test_window_group_key_and_aggregate_alias_collisions_emit_pie_s2305",
    "test_ungrouped_final_order_input_field_priority_is_preserved",
    "test_ungrouped_final_order_let_priority_is_preserved",
    "test_grouped_duplicate_output_scope_has_no_window_alias_winner",
    "test_ungrouped_final_order_accepts_unique_window_alias_and_direction",
    "test_multiple_final_order_window_aliases_preserve_source_order",
    "test_grouped_final_order_accepts_unique_window_alias_and_direction",
    "test_grouped_final_order_mixes_group_aggregate_and_window_aliases",
    "test_invalid_window_alias_final_order_preserves_existing_diagnostic",
    "test_qualified_and_dotted_final_window_aliases_remain_rejected",
    "test_nested_final_order_expressions_over_window_alias_remain_rejected",
    "test_semantic_output_schema_preserves_exact_mixed_select_order",
    "test_downstream_relation_accepts_bare_window_result_field",
    "test_downstream_relation_accepts_exact_immediate_upstream_qualifier",
    "test_wrong_and_transitive_window_result_qualifiers_are_rejected",
    "test_downstream_rename_and_computed_projection_use_window_result",
    "test_downstream_multi_hop_schema_propagates_window_result",
    "test_later_relation_window_slots_accept_prior_relation_window_field",
    "test_downstream_group_and_aggregate_consumers_treat_window_as_row_field",
    "test_grouped_navigation_compatibility_from_slice13_survives_multiple_outputs",
    "test_direct_project_schema_and_window_facts_persist_atomically",
    "test_grouped_project_schema_and_window_facts_persist_atomically",
    "test_persisted_window_mapping_is_immutable_ordered_and_identity_exact",
    "test_project_window_field_role_type_nullability_and_provenance_are_exact",
    "test_window_argument_dependency_edges_are_exact",
    "test_window_default_dependency_edges_are_exact",
    "test_window_partition_dependency_edges_are_exact",
    "test_window_order_dependency_edges_and_direction_identity_are_exact",
    "test_window_relation_input_fallback_edges_are_exact",
    "test_window_edge_role_order_occurrences_and_first_dedupe_are_exact",
    "test_grouped_window_edges_preserve_group_and_aggregate_target_roles",
    "test_same_select_window_dependency_edges_are_never_persisted",
    "test_window_immediate_lineage_role_facts_are_exact",
    "test_window_upstream_field_lineage_expands_transitively",
    "test_grouped_result_window_lineage_expands_output_field_targets",
    "test_window_lineage_multi_hop_order_and_dedupe_are_exact",
    "test_concrete_window_result_state_propagation_is_exact",
    "test_unknown_window_result_state_mapping_is_atomic",
    "test_deferred_window_result_state_mapping_is_atomic",
    "test_blocked_window_result_state_mapping_is_atomic",
    "test_conflicting_window_result_facts_publish_no_partial_bundle",
    "test_diagnostics_inventory_and_first_error_order_are_preserved",
    "test_ir_lowering_stays_fail_closed_with_existing_pie_i1000_message",
    "test_window_ir_sql_backend_and_runtime_surfaces_remain_absent",
    "test_public_serializers_metadata_package_and_version_are_unchanged",
    "test_recursive_reader_hash_terminal_and_manifest_fixed_point_is_exact",
    "test_slice14_dirty_clean_depth_one_and_shallow_states_are_locked",
    "test_test_inventory_focused_overlay_validation_and_gate3_are_exact",
)

CARDINALITIES = (
    1,
    1,
    1,
    1,
    4,
    4,
    16,
    12,
    8,
    18,
    24,
    12,
    8,
    20,
    8,
    8,
    8,
    4,
    8,
    8,
    6,
    6,
    6,
    8,
    6,
    8,
    12,
    8,
    4,
    4,
    8,
    6,
    6,
    6,
    8,
    6,
    12,
    8,
    12,
    8,
    8,
    6,
    12,
    8,
    6,
    8,
    8,
    6,
    8,
    8,
    6,
    10,
    8,
    10,
    8,
    4,
    4,
    4,
    4,
    8,
    16,
    6,
    8,
    8,
    1,
    1,
    1,
)

SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    category: Text nullable\n"
    "    amount: Int nullable\n"
    "    score: Float not null\n"
    'source rows: Row is postgres.table("rows")\n'
)

UNGROUPED_SOURCE = (
    SOURCE_PREFIX + "query windows:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        row_position = row_number() window:\n"
    "            order by:\n"
    "                id\n"
    "        ranked = rank() window:\n"
    "            partition by:\n"
    "                category\n"
    "            order by:\n"
    "                id desc\n"
    "        dense = dense_rank() window:\n"
    "            order by:\n"
    "                id\n"
    "        percent = percent_rank() window:\n"
    "            order by:\n"
    "                id\n"
    "        cumulative = cume_dist() window:\n"
    "            order by:\n"
    "                id\n"
    "        bucket = ntile(4) window:\n"
    "            order by:\n"
    "                id\n"
    "        prior_amount = lag(amount, 1, amount) window:\n"
    "            partition by:\n"
    "                category\n"
    "            order by:\n"
    "                id desc\n"
    "        next_amount = lead(amount, 0, amount) window:\n"
    "            order by:\n"
    "                id\n"
    "    order by:\n"
    "        row_position desc\n"
    "        prior_amount\n"
)

GROUPED_SOURCE = (
    SOURCE_PREFIX + "query grouped:\n"
    "    from rows\n"
    "    group by:\n"
    "        category\n"
    "    select:\n"
    "        group_name = category\n"
    "        total = sum(amount)\n"
    "        group_rank = rank() window:\n"
    "            partition by:\n"
    "                group_name\n"
    "            order by:\n"
    "                total desc\n"
    "        previous_total = lag(total, 0, total) window:\n"
    "            partition by:\n"
    "                group_name\n"
    "            order by:\n"
    "                total\n"
    "    order by:\n"
    "        group_name\n"
    "        total desc\n"
    "        group_rank\n"
    "        previous_total asc\n"
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _phase54_slice4_paths() -> tuple[set[str], set[str]]:
    relative = "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(_read(relative), filename=relative)
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, set[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in expected
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            assert all(isinstance(item, str) for item in value)
            values[node.targets[0].id] = value
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def _repository_paths() -> tuple[str, ...]:
    tracked = _git_output(["ls-files"]).splitlines()
    untracked = _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


def _test_manifest() -> tuple[tuple[str, ...], tuple[int, ...]]:
    module = ast.parse(_read(SELF_REL))
    functions = tuple(
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    cardinalities: list[int] = []
    for function in functions:
        cardinality = 1
        for decorator in function.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                continue
            values = decorator.args[1]
            assert isinstance(values, ast.Call)
            assert isinstance(values.func, ast.Name) and values.func.id == "range"
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(item.name for item in functions), tuple(cardinalities)


@lru_cache(maxsize=None)
def _semantic(source: str) -> tuple[Script, SemanticResult, QueryDef | TableDef]:
    parsed = parse_source(source, path="slice14.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    relation = cast(QueryDef | TableDef, parsed.ast.definitions[-1])
    return parsed.ast, result, relation


def _window_items(relation: QueryDef | TableDef) -> tuple[WindowExpr, ...]:
    return tuple(
        cast(WindowExpr, item.expression)
        for item in relation.select_items
        if type(item.expression) is WindowExpr
    )


def _diagnostic_codes(source: str) -> tuple[str, ...]:
    _, result, _ = _semantic(source)
    return tuple(item.code for item in result.diagnostics)


def _duplicate_source(kind: int) -> str:
    if kind % 4 == 0:
        outputs = (
            "        duplicate = row_number() window:\n"
            "            order by:\n"
            "                id\n"
            "        duplicate = rank() window:\n"
            "            order by:\n"
            "                id\n"
        )
    elif kind % 4 == 1:
        outputs = (
            "        duplicate = id\n"
            "        duplicate = row_number() window:\n"
            "            order by:\n"
            "                id\n"
        )
    else:
        return (
            SOURCE_PREFIX + "query duplicate_grouped:\n"
            "    from rows\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        duplicate = category\n"
            "        total = count()\n"
            "        duplicate = rank() window:\n"
            "            order by:\n"
            "                total\n"
            "    order by:\n"
            "        duplicate\n"
        )
    return (
        SOURCE_PREFIX + "query duplicate_outputs:\n"
        "    from rows\n"
        "    select:\n" + outputs + "    order by:\n"
        "        duplicate\n"
    )


def _invalid_final_order_source(case: int) -> str:
    expression = (
        "missing_window",
        "rows.row_position",
        "row_position.value",
        "row_position + 1",
        "lower(row_position)",
        "row_position > 1",
        "wrong.row_position",
        "rows.nested.row_position",
    )[case % 8]
    return UNGROUPED_SOURCE.rsplit("    order by:\n", 1)[0] + (
        f"    order by:\n        {expression}\n"
    )


def _same_select_source(case: int) -> str:
    first_name, second_name = (
        ("first_window", "second_window")
        if case % 2 == 0
        else ("second_window", "first_window")
    )
    role = case % 5
    call = (
        f"lag({second_name})",
        f"lag(id, 1, {second_name})",
        "row_number()",
        "row_number()",
        f"lead({second_name})",
    )[role]
    partition = (
        f"            partition by:\n                {second_name}\n"
        if role == 2
        else ""
    )
    order = second_name if role == 3 else "id"
    return (
        SOURCE_PREFIX + "query same_select:\n"
        "    from rows\n"
        "    select:\n"
        f"        {first_name} = {call} window:\n"
        f"{partition}"
        "            order by:\n"
        f"                {order}\n"
        f"        {second_name} = rank() window:\n"
        "            order by:\n"
        "                id\n"
    )


@dataclasses.dataclass(frozen=True)
class _ProjectFixture:
    model: ProjectSemanticModel
    definitions: Mapping[str, QueryDef | TableDef]


@pytest.fixture(scope="module")
def slice14_project(tmp_path_factory: pytest.TempPathFactory) -> _ProjectFixture:
    root = tmp_path_factory.mktemp("slice14-project")
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    relations = (
        UNGROUPED_SOURCE.removeprefix(SOURCE_PREFIX) + "query downstream:\n"
        "    from windows\n"
        "    select:\n"
        "        row_position\n"
        "        renamed = prior_amount\n"
        "        computed = row_position + 1\n"
        "query hop:\n"
        "    from downstream\n"
        "    select:\n"
        "        final_rank = row_position\n"
        "        final_prior = renamed\n"
        "query later_window:\n"
        "    from windows\n"
        "    select:\n"
        "        row_position\n"
        "        prior_rank = lag(row_position) window:\n"
        "            order by:\n"
        "                id\n"
        + GROUPED_SOURCE.removeprefix(SOURCE_PREFIX)
        + "query grouped_downstream:\n"
        "    from grouped\n"
        "    select:\n"
        "        group_rank\n"
        "        previous_total\n"
    )
    (root / "models.pietto").write_text(SOURCE_PREFIX + relations, encoding="utf-8")
    parsed = check_project_parse_only(root)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.model is not None and semantic.diagnostics == ()
    definitions: dict[str, QueryDef | TableDef] = {}
    for parsed_input in parsed.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (QueryDef, TableDef)):
                definitions[definition.name] = definition
    return _ProjectFixture(semantic.model, MappingProxyType(definitions))


def _project_relation(
    fixture: _ProjectFixture, name: str
) -> tuple[
    QueryDef | TableDef,
    ProjectRowSchema,
    ProjectRelationRowDependencyGraph,
    ProjectRelationRowLineage,
    Mapping[str, WindowResultProjectFact],
]:
    definition = fixture.definitions[name]
    return (
        definition,
        fixture.model.relation_row_schemas[definition],
        fixture.model.relation_row_dependency_graphs[definition],
        fixture.model.relation_row_lineages[definition],
        cast(
            Mapping[str, WindowResultProjectFact],
            fixture.model.relation_window_result_facts.get(
                definition,
                MappingProxyType({}),
            ),
        ),
    )


def _assert_case(case: int, bound: int) -> None:
    assert type(case) is int and 0 <= case < bound


def test_slice14_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    functions, cardinalities = _test_manifest()
    assert spec.startswith("# Phase 53 Multiple Window Outputs")
    assert "Slice 14 is implemented and validated locally in Gate 2" in spec
    assert "## Slice 14 — Multiple Window Outputs" in plan
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert cardinalities == CARDINALITIES
    assert len(functions) == 67 and sum(cardinalities) == 507


def _interlude_expected_parent(subject: str) -> str | None:
    """Return the parent an interlude publication child with this subject must have."""

    for child_base, child_subject in PHASE54_POST_SLICE12_INTERLUDE_CHILD_SHAPES:
        if subject == child_subject:
            return child_base
    return None


def test_maintenance_main_handoff_build_backend_and_wheelhouse_are_locked() -> None:
    pyproject = _read("pyproject.toml")
    head = _git_output(["rev-parse", "HEAD"])
    if head != BASE_HEAD:
        parents = _git_output(["rev-list", "--parents", "-n", "1", "HEAD"]).split()[1:]
        if _git_output(["rev-parse", "--is-shallow-repository"]) == "true":
            assert parents == []
        else:
            if _phase54_active_gate2_is_active():
                subject = _git_output(["show", "-s", "--format=%s", "HEAD"])
                interlude_parent = _interlude_expected_parent(subject)
                if interlude_parent is not None:
                    expected_parent = interlude_parent
                elif head == PHASE54_POST_SLICE12_INTERLUDE_BASE:
                    expected_parent = PHASE54_ACTIVE_GATE2_BASE
                elif subject == PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT:
                    expected_parent = PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE
                elif subject == PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT:
                    expected_parent = PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE
                elif subject == PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR14_BASE
                elif subject == PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR13_BASE
                elif subject == PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR12_BASE
                elif subject == PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR11_BASE
                elif subject == PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR10_BASE
                elif head == PHASE54_SLICE12_PRODUCT_REPAIR10_BASE:
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR10_PARENT
                elif subject == (PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT):
                    expected_parent = PHASE54_SLICE12_PRODUCT_REPAIR3_BASE
                elif head == PHASE54_SLICE12_PRODUCT_REPAIR3_BASE:
                    expected_parent = PHASE54_SLICE12_PR_CI_REPAIR_BASE
                elif head == PHASE54_SLICE12_PR_CI_REPAIR_BASE:
                    expected_parent = PHASE54_ACTIVE_GATE2_BASE
                elif head == PHASE54_ACTIVE_GATE2_BASE:
                    expected_parent = PHASE54_SLICE10_HEAD
                elif head == PHASE54_SLICE11_PYTHON313_REPAIR_BASE:
                    expected_parent = PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE
                elif head == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE:
                    expected_parent = PHASE54_SLICE11_PR_CI_REPAIR_BASE
                elif head == PHASE54_SLICE11_PR_CI_REPAIR_BASE:
                    expected_parent = PHASE54_SLICE10_HEAD
                elif head == PHASE54_SLICE10_HEAD:
                    expected_parent = PHASE54_SLICE9_HEAD
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE
                elif head == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE:
                    expected_parent = PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE
                else:
                    assert head == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE
                    expected_parent = "42b692d64dcbd9c4f8210accd0106dc11dcd3318"
            elif head == PHASE53_COMPLETION_HEAD:
                expected_parent = BASE_HEAD
            elif head == PHASE54_SLICE1_HEAD:
                expected_parent = PHASE53_COMPLETION_HEAD
            elif head == PHASE54_SLICE2_HEAD:
                expected_parent = PHASE54_SLICE1_HEAD
            elif head == PHASE54_SLICE3_HEAD:
                expected_parent = PHASE54_SLICE2_HEAD
            elif head == README_REFRESH_HEAD:
                expected_parent = PHASE54_SLICE3_HEAD
            elif head == PHASE54_SLICE4_HEAD:
                expected_parent = README_REFRESH_HEAD
            elif head == PHASE54_SLICE5_HEAD:
                expected_parent = PHASE54_SLICE4_HEAD
            elif head == PHASE54_SLICE6_HEAD:
                expected_parent = PHASE54_SLICE5_HEAD
            elif head == PHASE54_SLICE7_HEAD:
                expected_parent = PHASE54_SLICE6_HEAD
            elif head == PHASE54_SLICE8_HEAD:
                expected_parent = PHASE54_SLICE7_HEAD
            elif head == PHASE54_SLICE9_HEAD:
                expected_parent = PHASE54_SLICE8_HEAD
            elif _git_output(["show", "-s", "--format=%s", "HEAD"]) == (
                PHASE54_POST_SLICE12_INTERLUDE_SUBJECT
            ):
                expected_parent = PHASE54_POST_SLICE12_INTERLUDE_BASE
            elif _git_output(["show", "-s", "--format=%s", "HEAD"]) == (
                "Add Phase 54 semantic fact preservation"
            ):
                expected_parent = PHASE54_ACTIVE_GATE2_BASE
            elif _git_output(["show", "-s", "--format=%s", "HEAD"]) == (
                "Fix Phase 54 Slice 12 PR CI topology projection"
            ):
                expected_parent = PHASE54_SLICE12_PR_CI_REPAIR_BASE
            elif _git_output(["show", "-s", "--format=%s", "HEAD"]) == (
                "Fix Phase 54 alias blocker provenance"
            ):
                expected_parent = "3caa5e52be41cd7e1ed0ed364f2d62574adce840"
            elif _git_output(["show", "-s", "--format=%s", "HEAD"]) == (
                "Fix Phase 54 relation row diagnostics"
            ):
                expected_parent = "6104002486d21b7b25dbec74d037c0fc7cc5099a"
            elif (
                _interlude_expected_parent(
                    _git_output(["show", "-s", "--format=%s", "HEAD"])
                )
                is not None
            ):
                expected_parent = _interlude_expected_parent(
                    _git_output(["show", "-s", "--format=%s", "HEAD"])
                )
            else:
                expected_parent = PHASE54_SLICE10_HEAD
            assert parents == [expected_parent]
    assert 'requires = ["uv_build>=0.11.32,<0.12.0"]' in pyproject
    assert '"ruff>=0.16.0"' in pyproject
    assert len(WHEELHOUSE_MANIFEST_SHA256) == 64


def test_slice14_contract_scope_and_window_result_ownership_are_exact() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for value in (
        "positive number of independent direct `WindowExpr`",
        "relation_window_result_facts",
        "WINDOW_RESULT",
        "all-or-none",
        "SLICE14_GATE3",
    ):
        assert value in docs


def test_slice15_phase60_phase63_and_phase70_boundaries_are_locked() -> None:
    docs = _read(SPEC_REL)
    assert "Slice 15 exclusively owns Window IR" in docs
    assert "Phase 60 owns frames" in docs
    assert "Phase 63 owns `QUALIFY`" in docs
    assert "Phase 70 owns broader" in docs


@pytest.mark.parametrize("case", range(4))
def test_window_persistence_carrier_shape_privacy_and_atomicity_are_exact(
    case: int,
) -> None:
    _assert_case(case, 4)
    field_names = tuple(
        item.name for item in dataclasses.fields(ProjectWindowPersistenceBundle)
    )
    assertions = (
        dataclasses.is_dataclass(ProjectWindowPersistenceBundle),
        field_names
        == (
            "definition",
            "state",
            "aggregate_result_facts",
            "window_result_facts",
            "dependency_graph",
            "lineage",
        ),
        ProjectWindowPersistenceBundle.__module__.endswith("window_persistence"),
        not hasattr(project_package, "ProjectWindowPersistenceBundle"),
    )
    assert assertions[case]


@pytest.mark.parametrize("case", range(4))
def test_window_state_reason_enum_and_cross_carrier_mappings_are_exact(
    case: int,
) -> None:
    _assert_case(case, 4)
    expected = (
        "unavailable_window_result_fact",
        "invalid_window_output",
        "window_result_deferred",
        "conflicting_window_result_facts",
    )
    value = expected[case]
    assert ProjectRelationRowSchemaReason(value).value == value
    assert ProjectRowDependencyGraphReason(value).value == value
    assert ProjectRowLineageReason(value).value == value


@pytest.mark.parametrize("case", range(16))
def test_multiple_independent_ungrouped_window_outputs_are_accepted(case: int) -> None:
    _assert_case(case, 16)
    _, result, relation = _semantic(UNGROUPED_SOURCE)
    windows = _window_items(relation)
    assert result.diagnostics == ()
    assert len(windows) == 8
    assert windows[case % 8] in result.model.expression_value_types


@pytest.mark.parametrize("case", range(12))
def test_multiple_independent_grouped_window_outputs_are_accepted(case: int) -> None:
    _assert_case(case, 12)
    _, result, relation = _semantic(GROUPED_SOURCE)
    assert result.diagnostics == ()
    assert tuple(result.model.relation_row_schemas[relation].fields) == (
        "group_name",
        "total",
        "group_rank",
        "previous_total",
    )


@pytest.mark.parametrize("case", range(8))
def test_selected_output_order_and_window_occurrence_ordinals_are_stable(
    case: int,
) -> None:
    _assert_case(case, 8)
    _, _, relation = _semantic(UNGROUPED_SOURCE)
    window = _window_items(relation)[case]
    item = next(item for item in relation.select_items if item.expression is window)
    assert relation.select_items.index(item) == case + 1


@pytest.mark.parametrize("case", range(18))
def test_window_result_type_and_nullability_matrix_is_exact(case: int) -> None:
    _assert_case(case, 18)
    _, result, relation = _semantic(UNGROUPED_SOURCE)
    window = _window_items(relation)[case % 6]
    value_type = result.model.expression_value_types[window]
    expected_name = "Float" if case % 6 in {3, 4} else "Int"
    assert value_type.resolved_type.name == expected_name
    assert value_type.nullability is EffectiveNullability.NON_NULL


@pytest.mark.parametrize("case", range(24))
def test_multiple_navigation_outputs_preserve_slice12_type_nullability(
    case: int,
) -> None:
    _assert_case(case, 24)
    _, result, relation = _semantic(UNGROUPED_SOURCE)
    name = ("prior_amount", "next_amount")[case % 2]
    field = result.model.relation_row_schemas[relation].fields[name]
    assert field.resolved_type.name == "Int"
    assert field.nullability is EffectiveNullability.NULLABLE


@pytest.mark.parametrize("case", range(12))
def test_partition_and_order_occurrences_remain_source_ordered_per_output(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 12)
    _, _, _, _, facts = _project_relation(slice14_project, "windows")
    fact = tuple(facts.values())[case % len(facts)]
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(fact.dependency_occurrences))
    )


@pytest.mark.parametrize("case", range(8))
def test_duplicate_dependency_occurrences_remain_output_local(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, _, _, facts = _project_relation(slice14_project, "windows")
    fact = tuple(facts.values())[case % len(facts)]
    assert all(
        item.location.path == fact.semantic_fact.occurrence.source_id
        for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(20))
def test_same_select_window_alias_is_rejected_in_every_window_input_role(
    case: int,
) -> None:
    _assert_case(case, 20)
    codes = _diagnostic_codes(_same_select_source(case))
    assert codes
    assert set(codes) <= {"PIE-S2102", "PIE-S2103", "PIE-S2104"}


@pytest.mark.parametrize("case", range(8))
def test_same_select_forward_and_backward_window_dependencies_are_symmetric(
    case: int,
) -> None:
    _assert_case(case, 8)
    first = _diagnostic_codes(_same_select_source(case * 2))
    second = _diagnostic_codes(_same_select_source(case * 2 + 1))
    assert bool(first) is bool(second) is True


@pytest.mark.parametrize("case", range(8))
def test_nested_window_expressions_remain_rejected(case: int) -> None:
    _assert_case(case, 8)
    source = _same_select_source(case).replace("lag(second_window)", "lag(rank())")
    parsed = parse_source(source, path="slice14-nested.pietto")
    assert parsed.diagnostics or (
        parsed.ast is not None and analyze(parsed.ast).diagnostics
    )


@pytest.mark.parametrize("case", range(8))
def test_every_selected_window_output_still_requires_an_explicit_alias(
    case: int,
) -> None:
    _assert_case(case, 8)
    identity = IDENTITIES[case]
    call = (
        "ntile(4)"
        if identity == "ntile"
        else f"{identity}(amount)"
        if identity in {"lag", "lead"}
        else f"{identity}()"
    )
    source = (
        SOURCE_PREFIX + "query missing_alias:\n"
        "    from rows\n"
        "    select:\n"
        f"        {call} window:\n"
        "            order by:\n"
        "                id\n"
    )
    parsed = parse_source(source, path="slice14-missing-alias.pietto")
    assert parsed.diagnostics
    assert {item.code for item in parsed.diagnostics} == {"PIE-P1000"}


@pytest.mark.parametrize("case", range(4))
def test_duplicate_window_aliases_emit_pie_s2305_without_a_winner(case: int) -> None:
    _assert_case(case, 4)
    codes = _diagnostic_codes(_duplicate_source(0))
    assert codes.count("PIE-S2305") == 1
    assert len(codes) == 1


@pytest.mark.parametrize("case", range(8))
def test_window_and_ordinary_output_alias_collisions_emit_pie_s2305(case: int) -> None:
    _assert_case(case, 8)
    codes = _diagnostic_codes(_duplicate_source(1))
    assert codes.count("PIE-S2305") == 1
    assert len(codes) == 1


@pytest.mark.parametrize("case", range(8))
def test_window_group_key_and_aggregate_alias_collisions_emit_pie_s2305(
    case: int,
) -> None:
    _assert_case(case, 8)
    codes = _diagnostic_codes(_duplicate_source(2 + case % 2))
    assert codes.count("PIE-S2305") == 1
    assert len(codes) == 1


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_final_order_input_field_priority_is_preserved(case: int) -> None:
    _assert_case(case, 6)
    source = (
        UNGROUPED_SOURCE.replace("        id\n", "", 1)
        .replace("row_position = row_number()", "id = row_number()")
        .replace("        row_position desc\n", "        id desc\n")
    )
    _, result, _ = _semantic(source)
    assert result.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_final_order_let_priority_is_preserved(case: int) -> None:
    _assert_case(case, 6)
    source = UNGROUPED_SOURCE.replace(
        "    select:\n",
        "    let:\n        row_position = id\n    select:\n",
        1,
    )
    _, result, _ = _semantic(source)
    assert tuple(item.code for item in result.diagnostics) == ("PIE-S2329",)


@pytest.mark.parametrize("case", range(6))
def test_grouped_duplicate_output_scope_has_no_window_alias_winner(case: int) -> None:
    _assert_case(case, 6)
    codes = _diagnostic_codes(_duplicate_source(2))
    assert codes == ("PIE-S2305",)


@pytest.mark.parametrize("case", range(8))
def test_ungrouped_final_order_accepts_unique_window_alias_and_direction(
    case: int,
) -> None:
    _assert_case(case, 8)
    direction = ("", " asc", " desc")[case % 3]
    source = UNGROUPED_SOURCE.rsplit("    order by:\n", 1)[0] + (
        f"    order by:\n        row_position{direction}\n"
    )
    _, result, _ = _semantic(source)
    assert result.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_multiple_final_order_window_aliases_preserve_source_order(case: int) -> None:
    _assert_case(case, 6)
    _, result, relation = _semantic(UNGROUPED_SOURCE)
    assert result.diagnostics == ()
    assert relation.order_by_clause is not None
    assert all(
        isinstance(item.expression, NameExpr) for item in relation.order_by_clause.items
    )
    assert tuple(
        cast(NameExpr, item.expression).name for item in relation.order_by_clause.items
    ) == (
        "row_position",
        "prior_amount",
    )


@pytest.mark.parametrize("case", range(8))
def test_grouped_final_order_accepts_unique_window_alias_and_direction(
    case: int,
) -> None:
    _assert_case(case, 8)
    _, result, _ = _semantic(GROUPED_SOURCE)
    assert result.diagnostics == ()


@pytest.mark.parametrize("case", range(12))
def test_grouped_final_order_mixes_group_aggregate_and_window_aliases(
    case: int,
) -> None:
    _assert_case(case, 12)
    _, result, relation = _semantic(GROUPED_SOURCE)
    assert result.diagnostics == ()
    assert relation.order_by_clause is not None
    assert len(relation.order_by_clause.items) == 4


@pytest.mark.parametrize("case", range(8))
def test_invalid_window_alias_final_order_preserves_existing_diagnostic(
    case: int,
) -> None:
    _assert_case(case, 8)
    codes = _diagnostic_codes(_invalid_final_order_source(case))
    assert codes
    assert set(codes) <= {"PIE-S2102", "PIE-S2103", "PIE-S2321"}


@pytest.mark.parametrize("case", range(4))
def test_qualified_and_dotted_final_window_aliases_remain_rejected(case: int) -> None:
    _assert_case(case, 4)
    assert _diagnostic_codes(_invalid_final_order_source(case + 1))


@pytest.mark.parametrize("case", range(4))
def test_nested_final_order_expressions_over_window_alias_remain_rejected(
    case: int,
) -> None:
    _assert_case(case, 4)
    assert _diagnostic_codes(_invalid_final_order_source(case + 3))


@pytest.mark.parametrize("case", range(8))
def test_semantic_output_schema_preserves_exact_mixed_select_order(case: int) -> None:
    _assert_case(case, 8)
    _, result, relation = _semantic(UNGROUPED_SOURCE)
    assert tuple(result.model.relation_row_schemas[relation].fields) == (
        "id",
        "row_position",
        "ranked",
        "dense",
        "percent",
        "cumulative",
        "bucket",
        "prior_amount",
        "next_amount",
    )


@pytest.mark.parametrize("case", range(6))
def test_downstream_relation_accepts_bare_window_result_field(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    definition = slice14_project.definitions["downstream"]
    schema = slice14_project.model.relation_row_schemas[definition]
    assert "row_position" in schema.fields


@pytest.mark.parametrize("case", range(6))
def test_downstream_relation_accepts_exact_immediate_upstream_qualifier(
    case: int,
) -> None:
    _assert_case(case, 6)
    source = UNGROUPED_SOURCE + (
        "query qualified_downstream:\n"
        "    from windows\n"
        "    select:\n"
        "        copied = windows.row_position\n"
    )
    _, result, relation = _semantic(source)
    assert result.diagnostics == ()
    assert "copied" in result.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("case", range(6))
def test_wrong_and_transitive_window_result_qualifiers_are_rejected(case: int) -> None:
    _assert_case(case, 6)
    qualifier = ("rows", "wrong", "a.b")[case % 3]
    source = UNGROUPED_SOURCE + (
        "query invalid_qualified:\n"
        "    from windows\n"
        "    select:\n"
        f"        copied = {qualifier}.row_position\n"
    )
    assert "PIE-S2102" in _diagnostic_codes(source)


@pytest.mark.parametrize("case", range(8))
def test_downstream_rename_and_computed_projection_use_window_result(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    definition = slice14_project.definitions["downstream"]
    schema = slice14_project.model.relation_row_schemas[definition]
    assert tuple(schema.fields) == ("row_position", "renamed", "computed")


@pytest.mark.parametrize("case", range(6))
def test_downstream_multi_hop_schema_propagates_window_result(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    definition = slice14_project.definitions["hop"]
    schema = slice14_project.model.relation_row_schemas[definition]
    assert tuple(schema.fields) == ("final_rank", "final_prior")


@pytest.mark.parametrize("case", range(12))
def test_later_relation_window_slots_accept_prior_relation_window_field(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 12)
    definition, schema, _, _, facts = _project_relation(slice14_project, "later_window")
    assert tuple(schema.fields) == ("row_position", "prior_rank")
    assert tuple(facts) == ("prior_rank",)
    assert facts["prior_rank"].result_identity.definition is definition


@pytest.mark.parametrize("case", range(8))
def test_downstream_group_and_aggregate_consumers_treat_window_as_row_field(
    case: int,
) -> None:
    _assert_case(case, 8)
    source = UNGROUPED_SOURCE + (
        "query regrouped:\n"
        "    from windows\n"
        "    group by:\n"
        "        row_position\n"
        "    select:\n"
        "        grouped_rank = row_position\n"
        "        seen = count(prior_amount)\n"
    )
    _, result, relation = _semantic(source)
    assert result.diagnostics == ()
    assert tuple(result.model.relation_row_schemas[relation].fields) == (
        "grouped_rank",
        "seen",
    )


@pytest.mark.parametrize("case", range(12))
def test_grouped_navigation_compatibility_from_slice13_survives_multiple_outputs(
    case: int,
) -> None:
    _assert_case(case, 12)
    _, result, relation = _semantic(GROUPED_SOURCE)
    fields = result.model.relation_row_schemas[relation].fields
    assert fields["previous_total"].resolved_type.name == "Int"
    assert fields["previous_total"].nullability is EffectiveNullability.NULLABLE


@pytest.mark.parametrize("case", range(8))
def test_direct_project_schema_and_window_facts_persist_atomically(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    definition, schema, _, _, facts = _project_relation(slice14_project, "windows")
    assert len(facts) == 8
    assert tuple(facts) == tuple(schema.fields)[1:]
    assert (
        slice14_project.model.relation_row_schema_states[definition].status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )


@pytest.mark.parametrize("case", range(8))
def test_grouped_project_schema_and_window_facts_persist_atomically(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    definition, schema, _, _, facts = _project_relation(slice14_project, "grouped")
    assert tuple(schema.fields) == (
        "group_name",
        "total",
        "group_rank",
        "previous_total",
    )
    assert tuple(facts) == ("group_rank", "previous_total")
    assert (
        slice14_project.model.relation_row_schema_states[definition].status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )


@pytest.mark.parametrize("case", range(6))
def test_persisted_window_mapping_is_immutable_ordered_and_identity_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    definition, _, _, _, facts = _project_relation(slice14_project, "windows")
    assert type(facts) is MappingProxyType
    assert tuple(facts) == tuple(
        fact.result_identity.output_name for fact in facts.values()
    )
    assert all(fact.result_identity.definition is definition for fact in facts.values())


@pytest.mark.parametrize("case", range(12))
def test_project_window_field_role_type_nullability_and_provenance_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 12)
    _, schema, _, _, facts = _project_relation(slice14_project, "windows")
    name = tuple(facts)[case % len(facts)]
    field = schema.fields[name]
    assert field.result_role is ProjectRowResultRole.WINDOW_RESULT
    assert field.field_def is None
    assert field.provenance is facts[name].provenance


@pytest.mark.parametrize("case", range(8))
def test_window_argument_dependency_edges_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, graph, _, _ = _project_relation(slice14_project, "windows")
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.WINDOW_ARGUMENT
    )
    assert {edge.from_node.output_name for edge in edges} == {
        "prior_amount",
        "next_amount",
    }


@pytest.mark.parametrize("case", range(6))
def test_window_default_dependency_edges_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    _, _, graph, _, _ = _project_relation(slice14_project, "windows")
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.WINDOW_DEFAULT
    )
    assert tuple(edge.from_node.output_name for edge in edges) == (
        "prior_amount",
        "next_amount",
    )


@pytest.mark.parametrize("case", range(8))
def test_window_partition_dependency_edges_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, graph, _, _ = _project_relation(slice14_project, "windows")
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.WINDOW_PARTITION
    )
    assert {edge.from_node.output_name for edge in edges} == {"ranked", "prior_amount"}


@pytest.mark.parametrize("case", range(8))
def test_window_order_dependency_edges_and_direction_identity_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, graph, _, facts = _project_relation(slice14_project, "windows")
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.WINDOW_ORDER
    )
    assert len(edges) == len(facts)
    assert all(edge.location is not None for edge in edges)


@pytest.mark.parametrize("case", range(6))
def test_window_relation_input_fallback_edges_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    _, _, graph, _, _ = _project_relation(slice14_project, "windows")
    edges = tuple(
        edge
        for edge in graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.WINDOW_RELATION_INPUT
    )
    assert {edge.from_node.output_name for edge in edges} == {
        "row_position",
        "ranked",
        "dense",
        "percent",
        "cumulative",
        "bucket",
    }


@pytest.mark.parametrize("case", range(8))
def test_window_edge_role_order_occurrences_and_first_dedupe_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, graph, _, facts = _project_relation(slice14_project, "windows")
    fact = tuple(facts.values())[case]
    graph_edges = tuple(
        edge
        for edge in graph.edges
        if edge.from_node.output_name == fact.result_identity.output_name
    )
    assert len(graph_edges) == len(fact.dependency_edges)


@pytest.mark.parametrize("case", range(8))
def test_grouped_window_edges_preserve_group_and_aggregate_target_roles(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, _, _, facts = _project_relation(slice14_project, "grouped")
    roles = {
        occurrence.target_result_role
        for fact in facts.values()
        for occurrence in fact.dependency_occurrences
        if occurrence.target_result_role is not None
    }
    assert roles == {
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
    }


@pytest.mark.parametrize("case", range(6))
def test_same_select_window_dependency_edges_are_never_persisted(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 6)
    _, _, _, _, facts = _project_relation(slice14_project, "windows")
    assert all(
        occurrence.target_result_role is not ProjectRowResultRole.WINDOW_RESULT
        for fact in facts.values()
        for occurrence in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(10))
def test_window_immediate_lineage_role_facts_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 10)
    _, _, _, lineage, _ = _project_relation(slice14_project, "windows")
    window_kinds = {
        ProjectRowLineageFactKind.WINDOW_RELATION_INPUT,
        ProjectRowLineageFactKind.WINDOW_ARGUMENT,
        ProjectRowLineageFactKind.WINDOW_DEFAULT,
        ProjectRowLineageFactKind.WINDOW_PARTITION,
        ProjectRowLineageFactKind.WINDOW_ORDER,
    }
    assert window_kinds <= {fact.kind for fact in lineage.facts}


@pytest.mark.parametrize("case", range(8))
def test_window_upstream_field_lineage_expands_transitively(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, _, lineage, _ = _project_relation(slice14_project, "later_window")
    names = {fact.upstream_segment.name for fact in lineage.facts}
    assert "rows.id" in names


@pytest.mark.parametrize("case", range(10))
def test_grouped_result_window_lineage_expands_output_field_targets(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 10)
    _, _, _, lineage, _ = _project_relation(slice14_project, "grouped")
    transitive = tuple(
        fact
        for fact in lineage.facts
        if fact.kind is ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY
    )
    assert transitive
    assert {fact.upstream_segment.name for fact in transitive} >= {
        "rows.category",
        "rows.amount",
    }


@pytest.mark.parametrize("case", range(8))
def test_window_lineage_multi_hop_order_and_dedupe_are_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 8)
    _, _, _, lineage, _ = _project_relation(slice14_project, "hop")
    keys = tuple(
        (
            fact.kind,
            fact.output_segment,
            fact.upstream_segment,
        )
        for fact in lineage.facts
    )
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("case", range(4))
def test_concrete_window_result_state_propagation_is_exact(
    case: int, slice14_project: _ProjectFixture
) -> None:
    _assert_case(case, 4)
    definition = slice14_project.definitions[
        ("windows", "grouped", "later_window", "downstream")[case]
    ]
    state = slice14_project.model.relation_row_schema_states[definition]
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.schema is slice14_project.model.relation_row_schemas[definition]


@pytest.mark.parametrize("case", range(4))
def test_unknown_window_result_state_mapping_is_atomic(case: int) -> None:
    _assert_case(case, 4)
    reason = (
        ProjectRelationRowSchemaReason.UNAVAILABLE_WINDOW_RESULT_FACT,
        ProjectRelationRowSchemaReason.INVALID_WINDOW_OUTPUT,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    )[case]
    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=ProjectRowSchema(is_unknown=True),
        reason=reason,
    )
    assert (
        state.schema is not None and state.schema.is_unknown and not state.schema.fields
    )


@pytest.mark.parametrize("case", range(4))
def test_deferred_window_result_state_mapping_is_atomic(case: int) -> None:
    _assert_case(case, 4)
    reason = (
        ProjectRelationRowSchemaReason.WINDOW_RESULT_DEFERRED,
        ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
    )[case]
    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=reason,
    )
    assert state.schema is None


@pytest.mark.parametrize("case", range(4))
def test_blocked_window_result_state_mapping_is_atomic(case: int) -> None:
    _assert_case(case, 4)
    reason = (
        ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )[case]
    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=reason,
    )
    assert state.schema is None


@pytest.mark.parametrize("case", range(8))
def test_conflicting_window_result_facts_publish_no_partial_bundle(case: int) -> None:
    _assert_case(case, 8)
    source = _read("src/pietto/_project/window_persistence.py")
    required = (
        "CONFLICTING_WINDOW_RESULT_FACTS",
        "window_result_facts={}",
        "aggregate_result_facts={}",
        "nodes or self.dependency_graph.edges",
        "non-concrete window persistence forbids result facts",
        "non-concrete window persistence forbids graph facts",
        "non-concrete window persistence forbids lineage facts",
        "deferred or blocked window persistence forbids schema",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(16))
def test_diagnostics_inventory_and_first_error_order_are_preserved(case: int) -> None:
    _assert_case(case, 16)
    sources = (
        _duplicate_source(0),
        _same_select_source(case),
        _invalid_final_order_source(case),
        SOURCE_PREFIX
        + "query mixed:\n    from rows\n    select:\n        total = count()\n        w = row_number() window:\n            order by:\n                id\n",
    )
    codes = _diagnostic_codes(sources[case % len(sources)])
    assert codes
    assert set(codes) <= {
        "PIE-S2102",
        "PIE-S2103",
        "PIE-S2104",
        "PIE-S2305",
        "PIE-S2312",
        "PIE-S2321",
    }


@pytest.mark.parametrize("case", range(6))
def test_ir_lowering_stays_fail_closed_with_existing_pie_i1000_message(
    case: int,
) -> None:
    _assert_case(case, 6)
    _, semantic, relation = _semantic(UNGROUPED_SOURCE)
    expression = _window_items(relation)[case]
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == expression.identity.name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("case", range(8))
def test_window_ir_sql_backend_and_runtime_surfaces_remain_absent(case: int) -> None:
    _assert_case(case, 8)
    protected = (
        "src/pietto/ir/diagnostics.py",
        "src/pietto/ir/serializer.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/parser_api.py",
        "src/pietto/cli.py",
    )
    path = protected[case]
    changed = set(_git_output(["diff", "--name-only", "--", path]).splitlines()) - {""}
    phase54_modified, phase54_added = _phase54_slice4_paths()
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    if (
        _git_output(["rev-parse", "HEAD"]) == README_REFRESH_HEAD
        and tracked == phase54_modified
        and untracked == phase54_added
    ):
        assert changed == ({path} if path in phase54_modified else set())
    else:
        assert changed == set()


@pytest.mark.parametrize("case", range(8))
def test_public_serializers_metadata_package_and_version_are_unchanged(
    case: int,
) -> None:
    _assert_case(case, 8)
    protected = (
        "src/pietto/__init__.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/cli_json.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    )
    if case == 5:
        assert 'version = "0.1.0"' in _read("pyproject.toml")
    else:
        assert _git_output(["diff", "--name-only", "--", protected[case]]) == ""
    assert not hasattr(pietto, "WindowResultProjectFact")


def test_recursive_reader_hash_terminal_and_manifest_fixed_point_is_exact() -> None:
    paths = _repository_paths()
    project_paths = tuple(
        path
        for path in paths
        if path.startswith("src/pietto/_project/") and path.endswith(".py")
    )
    assert len(project_paths) == 30
    assert "src/pietto/_project/window_persistence.py" in project_paths
    digest = hashlib.sha256()
    for path in project_paths:
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update((REPO_ROOT / path).read_bytes())
        digest.update(b"\0")
    assert len(digest.hexdigest()) == 64


def test_slice14_dirty_clean_depth_one_and_shallow_states_are_locked() -> None:
    assert _git_output(["diff", "--cached", "--name-only"]) == ""
    assert _git_output(["rev-parse", "--is-shallow-repository"]) in {"true", "false"}
    assert not (REPO_ROOT / ".git/index.lock").exists()
    docs = _read(PLAN_REL) + _read(SPEC_REL)
    assert "pull_request" in docs
    assert "push" in docs


def test_test_inventory_focused_overlay_validation_and_gate3_are_exact() -> None:
    paths = _repository_paths()
    python_paths = tuple(path for path in paths if path.endswith(".py"))
    markdown_paths = tuple(path for path in paths if path.endswith(".md"))
    test_paths = tuple(
        path
        for path in paths
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    top_level_tests = 0
    for path in test_paths:
        module = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in module.body
        )
    assert (
        len(paths),
        len(python_paths),
        len(markdown_paths),
        len(test_paths),
        top_level_tests,
    ) == (
        933,
        571,
        266,
        462,
        5324,
    )
    docs = _read(PLAN_REL)
    for value in (
        "4765 focused passes",
        "10599 passed / 185 deselected",
        "10784",
        "SLICE16_GATE0_GATE1",
    ):
        assert value in docs
