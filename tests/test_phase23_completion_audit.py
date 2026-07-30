from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import ast
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from pietto.semantic.catalog import BUILTIN_FUNCTIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-23-count-field-aggregate-mvp.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
GOLDEN_ROOT = REPO_ROOT / "tests/fixtures/golden"

PHASE23_ARTIFACTS = (
    "docs/plan/phase-23-count-field-aggregate-mvp.md",
    "tests/test_phase23_count_field_candidate_decision.py",
    "tests/test_phase23_count_field_semantics.py",
    "tests/test_phase23_count_field_ir.py",
    "tests/test_phase23_count_field_sql.py",
    "tests/test_phase23_count_field_cli_json_output.py",
    "tests/test_phase23_completion_audit.py",
)

PHASE23_SQL_GOLDENS = {
    "emit_sql_count_field_aggregate.sql",
    "emit_mysql_count_field_aggregate.sql",
    "emit_sql_grouped_count_field_aggregate.sql",
    "emit_mysql_grouped_count_field_aggregate.sql",
}

PHASE23_GOLDEN_INPUTS = {
    "emit_sql_count_field_aggregate.sql": (
        "tests/fixtures/phase23/postgres_count_field_aggregate.pietto",
    ),
    "emit_mysql_count_field_aggregate.sql": (
        "tests/fixtures/phase23/mysql_count_field_aggregate.pietto",
    ),
    "emit_sql_grouped_count_field_aggregate.sql": (
        "tests/fixtures/phase23/postgres_grouped_count_field_aggregate.pietto",
    ),
    "emit_mysql_grouped_count_field_aggregate.sql": (
        "tests/fixtures/phase23/mysql_grouped_count_field_aggregate.pietto",
    ),
}


def test_phase23_slice6_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE23_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 23 Slice 1 is complete as candidate decision and contract work only",
        "Phase 23 Slice 2 is complete as count(field) semantic validation and row-schema work",
        "Phase 23 Slice 3 is complete as count(field) IR lowering work",
        "Phase 23 Slice 4 is complete as PostgreSQL/MySQL SQL rendering and golden coverage",
        "Phase 23 Slice 5 is complete as CLI, JSON v1, output-file, malformed-backend, and no-regression hardening",
        "Phase 23 Slice 6 is complete as completion audit and status lock work only",
        "Phase 23 Count(Field) Aggregate MVP is complete.",
        "Slice 6 adds only `tests/test_phase23_completion_audit.py`, status documentation, and narrow static audit updates needed to record the completed phase",
    ):
        assert required in plan


def test_count_field_final_scope_type_and_nullability_contract_is_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 23 final accepted source shapes are exactly direct aliased `count(field)` and `count(source.field)` aggregate projections",
        "no-GROUP and grouped `select:` contexts",
        "existing `count()` remains valid and continues to mean SQL `COUNT(*)`",
        "`count(field)` counts non-null field values",
        "`count()` returns `Int not null`",
        "`count(field) -> Int not null`",
        "`count(source.field) -> Int not null`",
        "All concrete bound field types are accepted except `Any`",
        "`Any`, `Unknown`, and unresolved fields are rejected through existing diagnostics",
        "`count` remains an aggregate name only, not a scalar builtin",
    ):
        assert required in plan


def test_count_field_uses_existing_diagnostics_and_not_scalar_builtins() -> None:
    for aggregate_name in ("count", "sum", "avg", "min", "max"):
        assert aggregate_name not in BUILTIN_FUNCTIONS

    diagnostics = _read(DIAGNOSTICS_PATH)
    for code in (
        "PIE-S2308",
        "PIE-S2309",
        "PIE-S2310",
        "PIE-S2311",
        "PIE-S2312",
        "PIE-S2313",
        "PIE-S2314",
        "PIE-S2315",
        "PIE-B1000",
    ):
        assert f"| `{code}` |" in diagnostics

    plan = _normalized(PLAN_PATH)
    assert "No new diagnostic code is added for Phase 23" in plan
    assert (
        "Malformed hand-built aggregate IR remains fail-closed through existing `PIE-B1000`"
        in plan
    )


def test_slice2_through_slice5_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase23_count_field_semantics.py": {
            "test_count_star_remains_valid_int_non_null",
            "test_no_group_count_field_accepts_concrete_bound_field_types",
            "test_no_group_qualified_count_field_is_accepted",
            "test_grouped_count_field_projection_is_accepted",
            "test_grouped_qualified_count_field_projection_is_accepted",
            "test_count_any_field_is_rejected_with_existing_unsupported_type_diagnostic",
            "test_count_missing_field_uses_existing_unresolved_field_diagnostic_only",
            "test_count_field_invalid_projection_shapes_use_existing_diagnostics",
            "test_mixed_no_group_count_field_projection_remains_rejected",
            "test_count_field_in_invalid_context_remains_rejected",
            "test_existing_sum_avg_min_max_semantics_remain_unchanged",
            "test_existing_sum_avg_min_max_diagnostics_remain_covered",
        },
        "tests/test_phase23_count_field_ir.py": {
            "test_count_star_still_lowers_to_zero_arg_aggregate_ir",
            "test_no_group_count_field_lowers_to_one_arg_aggregate_ir",
            "test_no_group_qualified_count_field_lowers_to_qualified_field_ref",
            "test_grouped_count_field_lowers_with_group_keys_preserved",
            "test_grouped_qualified_count_field_lowers_with_group_keys_preserved",
            "test_direct_lower_expr_for_valid_count_field_uses_aggregate_call_ir",
            "test_invalid_count_field_shapes_do_not_emit_aggregate_call_ir",
            "test_existing_count_sum_avg_min_max_ir_behavior_remains_unchanged",
        },
        "tests/test_phase23_count_field_sql.py": {
            "test_direct_renderers_support_count_field_and_preserve_existing_aggregates",
            "test_direct_backend_count_field_sql_matches_reviewed_golden",
            "test_count_field_goldens_lock_function_and_qualification_shape",
            "test_existing_count_star_goldens_remain_byte_stable",
            "test_malformed_hand_built_count_field_ir_fails_closed_with_pie_b1000",
            "test_direct_malformed_count_field_renderer_errors_stay_dialect_specific",
            "test_phase23_count_field_goldens_are_registered_and_audited",
        },
        "tests/test_phase23_count_field_cli_json_output.py": {
            "test_cli_text_count_field_sql_matches_reviewed_golden",
            "test_cli_json_count_field_sql_success_preserves_v1_shape",
            "test_cli_text_count_field_output_writes_exact_sql",
            "test_cli_json_count_field_output_writes_exact_sql_and_keeps_artifacts",
            "test_cli_text_count_field_semantic_error_stops_before_sql",
            "test_cli_json_count_field_semantic_error_does_not_write_output",
            "test_cli_json_count_field_backend_error_does_not_write_output",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_count_field_golden_inventory_and_json_v1_shape_are_locked() -> None:
    goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(goldens, "SQL_FIXTURES"))
    json_fixtures = cast(frozenset[str], getattr(goldens, "JSON_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(goldens, "FIXTURE_INPUTS"),
    )
    reference_tests = cast(tuple[Path, ...], getattr(goldens, "REFERENCE_TESTS"))
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(goldens, "audit"))

    assert len(sql_fixtures) == 32
    assert len(json_fixtures) == 5
    assert len(sql_fixtures | json_fixtures) == 37
    assert PHASE23_SQL_GOLDENS <= sql_fixtures
    for golden, inputs in PHASE23_GOLDEN_INPUTS.items():
        assert fixture_inputs[golden] == inputs
    assert Path("tests/test_phase23_count_field_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()

    for golden in PHASE23_SQL_GOLDENS:
        assert (GOLDEN_ROOT / golden).is_file()

    cli_tests = _read(REPO_ROOT / "tests/test_phase23_count_field_cli_json_output.py")
    for required in (
        'assert result["schema_version"] == 1',
        '"schema_version"',
        '"command"',
        '"ok"',
        '"path"',
        '"dialect"',
        '"diagnostics"',
        '"cli_errors"',
        '"artifacts"',
        '"output"',
        'assert set(artifacts[0]) == {"kind", "name", "sql"}',
        'assert result["output"] == {"path": str(output_path), "written": True}',
        'assert result["output"] == {"path": str(output_path), "written": False}',
        'assert result["artifacts"] == []',
        "PIE-S2309",
        "PIE-B1000",
    ):
        assert required in cli_tests


def test_phase23_forbidden_features_and_surfaces_remain_deferred() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "`count_distinct(field)`",
        "distinct aggregates or `DISTINCT` syntax",
        "filtered aggregates",
        "aggregate expression arguments such as `count(a + b)` or `count(lower(name))`",
        "nested aggregates",
        "composed aggregate expressions",
        "unnamed aggregate projections",
        "result predicates, `satisfying`, post-select `where`, `such that`, SQL `HAVING`, or any HAVING-like user syntax",
        "grouped `ORDER BY`",
        "JOIN behavior",
        "relationship behavior",
        "runtime behavior",
        "public API expansion",
        "JSON schema changes",
        "CLI option changes",
        "dependency, config, package, version, or CI changes",
        "Slice 6 changes no grammar, generated ANTLR, AST, semantic acceptance, Semantic IR behavior, SQL renderer behavior, SQL fixtures or goldens, CLI options, JSON v1 schema, public API, dependency, lockfile, package metadata, CI, runtime/database behavior, UI, LSP, or relationship/JOIN behavior",
    ):
        assert required in plan


def test_status_documents_record_phase23_without_runtime_or_schema_claims() -> None:
    for relative_path in (
        "AGENTS.md",
        "docs/spec/pietto-v0.9.md",
    ):
        document = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 23",
            "Count(Field) Aggregate MVP",
            "`count()` as SQL `COUNT(*)`",
            "`count(field)`",
            "`count(source.field)`",
            "counts non-null field values",
            "`Int not null`",
            "all concrete bound field types are accepted except `Any`",
            "no runtime/database execution",
            "no JSON schema change",
            "no CLI option change",
            "no relationship/JOIN behavior",
        ):
            assert required in document


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase23_completion_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
