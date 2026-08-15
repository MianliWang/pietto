from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-27-grouped-result-ordering-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/grouped-result-ordering-v1.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE27_ARTIFACTS = (
    "docs/spec/grouped-result-ordering-v1.md",
    "docs/plan/phase-27-grouped-result-ordering-mvp.md",
    "tests/test_phase27_grouped_order_candidate_decision.py",
    "tests/test_phase27_grouped_order_semantics.py",
    "tests/test_phase27_grouped_order_ir.py",
    "tests/test_phase27_grouped_order_sql.py",
    "tests/test_phase27_grouped_order_cli_json_output.py",
    "tests/test_phase27_completion_audit.py",
)

LOCKED_BOUNDARY_SURFACES = {
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "1abb7763827982777ac1c7af3912a7c6dbea94824d448973e4d640de7dc3247a",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1",
    ),
    "ast_nodes": (
        "src/pietto/ast_nodes.py",
        1,
        "261118027be70b53cedd10f7c3c6c29b64fa4e942a99f03a6f594b8647def69a",
    ),
    "ast_builder": (
        "src/pietto/ast_builder.py",
        1,
        "c2c8126fbeeccc4dc264fe9e3a80441ce204205bd2b2b85a2a142bc017a80e0c",
    ),
    "parser_api": (
        "src/pietto/parser_api.py",
        1,
        "537178041b413d964bda00aef376f90d745a64d61378ede2dbc6a715b49e7f3f",
    ),
    "semantic": (
        "src/pietto/semantic",
        36,
        "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "310c07a1a5c9ae53f878b143b9d5dc3b092bfdfa072728ee4cae168e361907ec",
    ),
    "cli_json": (
        "src/pietto/cli_json.py",
        1,
        "573fd193b98a746cfd84a6990a22248d2b63a7fc0ed1069f442ffff9c4dd99e7",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "efe30986b76da78cfaa8614cc4e3e10b39dac2a6bf984e7dc6878a82308df6da",
    ),
    "fixtures": (
        "tests/fixtures",
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        "tests/fixtures/golden",
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
    "scripts": (
        "scripts",
        4,
        "013844a763f970b8e0f0094f0c68ad114e3056fb1f12858c5c2758c2c57e9887",
    ),
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "phase27_plan": (
        "docs/plan/phase-27-grouped-result-ordering-mvp.md",
        1,
        "40f4ca0c83ebbee9d1f19276d679836fe151de2ef17791d149e953eb7d8ba62f",
    ),
    "phase27_spec": (
        "docs/spec/grouped-result-ordering-v1.md",
        1,
        "dd1ab903d87d083d0b3379d7305987b3566e843f92ce2796d669d8c45108ece7",
    ),
    "readme": (
        "README.md",
        1,
        "0566a1a845af6301c16551c9c9ac455bf4a19b7ae630fd79fd27974696136272",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "4691169dd8550dea14ecdb987c6761ecf497e9c10a8a8028b0711ad4cc2150e9",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "ebc774397dc050bd542106b4bffb28f15423153d668798b024236cff1faf0103",
    ),
}


def test_phase27_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE27_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    for required in (
        "Phase 27 is complete. Slices 1 through 6 cover candidate decision "
        "and exact contract, grouped result-order semantic validation, IR "
        "lowering, PostgreSQL and private MySQL SQL lowering, CLI / JSON / "
        "output hardening, and completion audit/status lock",
        "Status: complete as candidate decision, exact contract, and static "
        "audit work only",
        "Status: complete as grouped result-order semantic validation only",
        "Status: complete as IR lowering only",
        "Status: complete as PostgreSQL/private MySQL SQL backend lowering only",
        "Status: complete as tests-only CLI / JSON / output hardening",
        "Status: complete as completion audit and status lock work only",
    ):
        assert required in plan
    for required in (
        "Status: Phase 27 is complete for the grouped result-ordering MVP",
        "The implemented behavior is limited to grouped result-scope `ORDER "
        "BY` over bare selected output names",
        "SQL renders underlying selected expressions, not SELECT aliases",
        "Phase 27 changes no grammar, generated ANTLR, AST, AST builder, "
        "JSON schema, JSON serializer, fixture, golden, script, dependency, "
        "lockfile, package metadata, CI, Makefile/config, public API",
    ):
        assert required in spec


def test_phase27_final_status_docs_are_precise_without_broadening_scope() -> None:
    for relative_path in ("AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 27 Grouped Result Ordering MVP",
            "complete",
            "grouped result-scope `ORDER BY` over bare selected output names",
            "selected group-key projection outputs",
            "selected direct aggregate projection outputs",
            "selected Phase 26 aggregate-expression projection outputs",
            "`sum(amount + tax)`",
            "`avg(score * weight)`",
            "`count_distinct(lower(trim(status)))`",
            "SQL renders the underlying selected expression rather than the "
            "SELECT alias",
            "Unsupported grouped order source shapes continue to use existing "
            "diagnostics such as `PIE-S2321`",
            "JSON schema change",
            "CLI option change",
            "public MySQL API expansion",
            "runtime/database execution",
            "project/multi-file behavior",
            "relationship/JOIN behavior",
        ):
            assert required in status_doc
        for forbidden in (
            "arbitrary grouped `ORDER BY` expressions are supported",
            "direct aggregate calls inside source `order by:` are supported",
            "no-GROUP projection aliases are available to ordering",
            "public `emit_mysql_sql`",
        ):
            assert forbidden not in status_doc


def test_phase27_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase27_grouped_order_candidate_decision.py": {
            "test_phase27_slice1_artifacts_exist_and_record_status",
            "test_slice1_boundary_is_docs_plan_spec_static_audit_and_status_only",
            "test_phase12_phase21_phase25_phase26_baselines_are_locked",
            "test_existing_parser_ast_and_ir_surface_already_support_clause_shape",
            "test_exact_accepted_grouped_order_subset_is_locked",
            "test_sql_lowering_uses_underlying_expression_not_select_alias",
            "test_diagnostic_strategy_keeps_s2321_without_new_code",
            "test_backend_placement_and_current_grouped_order_guard_are_acknowledged",
            "test_slice_plan_and_validation_commands_are_locked",
            "test_required_non_goals_remain_explicitly_deferred",
            "test_status_docs_record_phase27_completion_without_broadening_scope",
        },
        "tests/test_phase27_grouped_order_semantics.py": {
            "test_grouped_order_accepts_supported_selected_outputs",
            "test_grouped_order_accepts_existing_direction_syntax",
            "test_grouped_order_preserves_duplicate_items_and_source_order_in_ast",
            "test_grouped_satisfying_and_accepted_order_by_are_semantically_valid",
            "test_grouped_order_rejects_unsupported_item_shapes",
            "test_grouped_order_ordinal_remains_parser_owned",
            "test_grouped_order_rejects_original_name_for_renamed_group_key",
            "test_grouped_order_preserves_duplicate_projection_primary_diagnostic",
            "test_grouped_order_preserves_invalid_aggregate_primary_diagnostic",
            "test_grouped_order_rejects_unsupported_computed_projection_output",
            "test_pietto_check_accepts_grouped_order_source",
        },
        "tests/test_phase27_grouped_order_ir.py": {
            "test_grouped_order_lowers_bare_group_key_output",
            "test_grouped_order_lowers_aliased_group_key_to_underlying_field",
            "test_grouped_order_lowers_direct_aggregate_aliases",
            "test_grouped_order_lowers_numeric_expression_aggregate_alias",
            "test_grouped_order_lowers_text_transform_aggregate_alias",
            "test_grouped_satisfying_and_order_by_lower_underlying_expressions",
            "test_grouped_order_preserves_duplicates_and_source_order",
            "test_no_group_order_by_still_uses_input_scope_ir",
            "test_no_group_projection_alias_still_does_not_resolve_in_order_by",
            "test_unsupported_grouped_order_fails_before_ir_with_s2321",
            "test_grouped_order_ordinal_remains_parser_owned",
        },
        "tests/test_phase27_grouped_order_sql.py": {
            "test_grouped_order_by_bare_group_key_output_renders_field_expression",
            "test_grouped_order_by_aliased_group_key_renders_underlying_field",
            "test_grouped_order_by_aggregate_outputs_render_underlying_expressions",
            "test_grouped_satisfying_order_by_and_limit_render_in_clause_order",
            "test_grouped_order_preserves_duplicate_items_and_source_order",
            "test_no_group_sql_order_by_still_uses_input_scope",
            "test_no_group_projection_alias_still_fails_before_sql",
            "test_unsupported_grouped_order_source_fails_semantically_before_sql",
            "test_malformed_grouped_order_expression_fails_closed_with_pie_b1000",
            "test_malformed_grouped_order_direction_still_fails_closed_with_pie_b1000",
            "test_private_mysql_api_remains_unexported",
        },
        "tests/test_phase27_grouped_order_cli_json_output.py": {
            "test_check_accepts_grouped_result_ordering",
            "test_text_emit_sql_carries_grouped_result_ordering",
            "test_json_emit_sql_preserves_v1_shape_with_grouped_result_ordering",
            "test_text_output_writes_grouped_order_sql_on_success",
            "test_json_output_writes_grouped_order_sql_and_keeps_artifacts",
            "test_invalid_grouped_order_text_fails_before_sql_artifacts",
            "test_invalid_grouped_order_json_fails_without_artifacts",
            "test_invalid_grouped_order_json_output_does_not_replace_existing_file",
            "test_no_group_projection_alias_order_still_fails_before_sql",
            "test_public_mysql_api_remains_private",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_phase27_accepted_scope_and_alias_normalization_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    sql_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_sql.py")
    ir_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_ir.py")
    cli_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_cli_json_output.py")

    for required in (
        "Phase 27 supports only grouped result-scope `ORDER BY` over bare "
        "selected output names",
        "the item expression is a bare name",
        "the name resolves to exactly one selected output name",
        "group-key projection output",
        "direct aggregate projection output",
        "Phase 26 aggregate-expression projection output",
        "`sum(amount + tax)`",
        "`avg(score * weight)`",
        "`count_distinct(lower(trim(status)))`",
        "duplicate order items are preserved",
    ):
        assert required in spec

    for required in (
        "test_grouped_order_by_aliased_group_key_renders_underlying_field",
        "test_grouped_order_by_aggregate_outputs_render_underlying_expressions",
        'assert f"{quote}{forbidden_alias}{quote}" not in order_by',
        "test_grouped_satisfying_order_by_and_limit_render_in_clause_order",
        "test_grouped_order_preserves_duplicate_items_and_source_order",
    ):
        assert required in sql_tests
    assert '"total"' in cli_tests
    assert "not in _order_by_clause" in cli_tests
    assert "`total`" in cli_tests
    assert 'field.name != "r"' in ir_tests
    assert '_assert_aggregate_order(relation.order_by[0].expression, "sum")' in (
        ir_tests
    )


def test_phase27_diagnostics_and_unsupported_boundaries_are_locked() -> None:
    diagnostics = _read(DIAGNOSTICS_PATH)
    semantics_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_semantics.py")
    sql_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_sql.py")
    cli_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_cli_json_output.py")
    semantic_group_by = _read(REPO_ROOT / "src/pietto/semantic/group_by.py")

    assert "| `PIE-S2321` | Grouped ORDER BY is deferred |" in diagnostics
    assert (
        "| `PIE-S2328` | Parsed `let:` binding uses an unsupported lowering "
        "boundary outside the current row-level inline expansion MVP |"
    ) in diagnostics
    assert "PIE-S2328" not in semantics_tests
    assert (
        "Unsupported grouped ORDER BY item; expected a supported select output name"
        in semantic_group_by
    )
    for required in (
        "missing",
        "orders.region",
        '"east"',
        "sum(amount)",
        "total + 1",
        "total > 1",
        'total > 1 and region == "east"',
        "PIE-S2321",
    ):
        assert required in semantics_tests
    assert "PIE-P1000" in semantics_tests
    assert "test_unsupported_grouped_order_source_fails_semantically_before_sql" in (
        sql_tests
    )
    assert "invalid grouped order must stop before IR and SQL" in cli_tests


def test_no_group_order_by_and_parser_boundaries_remain_locked() -> None:
    phase12_order = _normalized(REPO_ROOT / "docs/spec/order-limit-contract-v1.md")
    semantics_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_semantics.py")
    ir_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_ir.py")
    sql_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_sql.py")
    cli_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_cli_json_output.py")

    assert (
        "Projection aliases are not members of the `ORDER BY` name-resolution scope"
        in phase12_order
    )
    for test_source in (ir_tests, sql_tests, cli_tests):
        assert "test_no_group" in test_source
        assert "PIE-S2102" in test_source
    assert "test_grouped_order_ordinal_remains_parser_owned" in semantics_tests
    assert "PIE-P1000" in semantics_tests


def test_cli_json_public_api_and_mysql_boundaries_remain_locked() -> None:
    cli_tests = _read(REPO_ROOT / "tests/test_phase27_grouped_order_cli_json_output.py")

    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")
    for required in (
        "EMIT_SQL_KEYS",
        '"schema_version"',
        '"schema_version_v2"',
        '"project"',
        '"project_root"',
        '"diagnostics"',
        '"cli_errors"',
        '"artifacts"',
        '"output"',
        '"written"',
        "test_invalid_grouped_order_json_output_does_not_replace_existing_file",
    ):
        assert required in cli_tests


def test_fixture_golden_inventory_and_validation_scripts_remain_unchanged() -> None:
    check_goldens = _check_goldens_module()

    assert len(check_goldens.SQL_FIXTURES) == 32
    assert len(check_goldens.JSON_FIXTURES) == 5
    assert len(check_goldens.CLASSIFIED_FIXTURES) == 37
    assert check_goldens.audit(REPO_ROOT) == ()
    assert not any(
        "phase27" in fixture for fixture in check_goldens.CLASSIFIED_FIXTURES
    )
    assert not (REPO_ROOT / "tests/fixtures/phase27").exists()

    plan = _normalized(PLAN_PATH)
    for required in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert required in plan


def test_boundary_surfaces_remain_phase27_locked() -> None:
    for name, (
        relative_path,
        expected_count,
        expected_digest,
    ) in LOCKED_BOUNDARY_SURFACES.items():
        paths = _paths(REPO_ROOT / relative_path)
        assert len(paths) == expected_count, name
        assert _digest(paths) == expected_digest, name


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(_read(path), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


def _paths(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(
        sorted(
            child
            for child in path.rglob("*")
            if child.is_file()
            and "__pycache__" not in child.parts
            and child.suffix != ".pyc"
        )
    )


def _digest(paths: tuple[Path, ...]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        hasher.update(relative_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _check_goldens_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_goldens", CHECK_GOLDENS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 54 Slice 3 reader migration.
