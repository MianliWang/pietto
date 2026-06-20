from __future__ import annotations

import ast
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"

PHASE21_TESTS = (
    "tests/test_phase21_candidate_decision_audit.py",
    "tests/test_phase21_group_by_syntax_contract_audit.py",
    "tests/test_phase21_group_by_semantic_ir_sql_contract_audit.py",
    "tests/test_phase21_group_by_parser_ast_fail_closed.py",
    "tests/test_phase21_group_by_semantic_validation.py",
    "tests/test_phase21_group_by_semantic_validation_audit.py",
    "tests/test_phase21_group_by_ir_lowering.py",
    "tests/test_phase21_group_by_ir_lowering_audit.py",
    "tests/test_phase21_group_by_sql_lowering.py",
    "tests/test_phase21_group_by_cli_hardening.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase21_completion_audit.py",
)

GROUPED_FIXTURES = {
    "mysql_group_by_aggregate.pietto",
    "postgres_group_by_aggregate.pietto",
}
GROUPED_SQL_GOLDENS = {
    "emit_mysql_group_by_aggregate.sql",
    "emit_sql_group_by_aggregate.sql",
}


def test_phase21_slice9_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in (
        "docs/plan/phase-21-group-by-contract-planning.md",
        *PHASE21_TESTS,
    ):
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 21 Slice 9 is complete as GROUP BY Aggregate MVP completion audit",
        "Phase 21 GROUP BY Aggregate MVP is complete as a bounded MVP",
        "Slice 9 adds only completion audit coverage and this status documentation",
        "Phase 21 is complete after Slice 9",
        "9. **Slice 9: GROUP BY completion audit**: complete final audit slice for the authorized GROUP BY Aggregate MVP",
    ):
        assert required in plan

    for forbidden in (
        "GROUP BY is implemented",
        "implements GROUP BY",
        "GROUP BY implementation is complete",
        "Phase 21 implements GROUP BY",
    ):
        assert forbidden not in plan


def test_group_by_syntax_parser_and_cli_success_coverage_is_locked() -> None:
    parser_tests = REPO_ROOT / "tests/test_phase21_group_by_parser_ast_fail_closed.py"
    sql_tests = REPO_ROOT / "tests/test_phase21_group_by_sql_lowering.py"
    cli_tests = REPO_ROOT / "tests/test_phase21_group_by_cli_hardening.py"

    _assert_functions(
        parser_tests,
        {
            "test_parser_accepts_group_by_bare_field",
            "test_parser_accepts_group_by_qualified_field_after_where",
            "test_parser_accepts_group_by_before_order_by_and_limit",
            "test_group_by_spans_and_duplicate_source_order_are_preserved",
            "test_invalid_group_by_shapes_are_parser_errors",
            "test_cli_check_accepts_valid_grouped_relation",
            "test_emit_sql_json_succeeds_with_group_by_artifact",
        },
    )
    _assert_contains_all(
        parser_tests,
        (
            "lower(status)",
            "count()",
            "group by:\\n        1\\n",
            ": GROUP BY COLON NEWLINE NEWLINE* INDENT groupByBody DEDENT",
        ),
    )

    _assert_functions(
        sql_tests,
        {
            "test_direct_group_by_sql_matches_reviewed_golden",
            "test_cli_text_group_by_sql_matches_reviewed_golden",
            "test_cli_json_group_by_sql_success_preserves_v1_shape",
            "test_cli_json_group_by_sql_output_writes_exact_sql",
            "test_cli_check_succeeds_for_valid_grouped_relation",
        },
    )
    _assert_functions(
        cli_tests,
        {
            "test_valid_grouped_check_succeeds_for_both_dialects",
            "test_valid_grouped_emit_sql_text_and_json_smoke",
            "test_valid_grouped_emit_sql_output_writes_sql_and_suppresses_stdout",
        },
    )
    _assert_contains_all(cli_tests, ("postgres", "mysql", "--output", "GROUP BY"))


def test_grouped_semantic_diagnostics_and_aggregate_edges_are_locked() -> None:
    semantic_tests = REPO_ROOT / "tests/test_phase21_group_by_semantic_validation.py"
    hardening_tests = REPO_ROOT / "tests/test_phase21_group_by_cli_hardening.py"
    diagnostics = DIAGNOSTICS_PATH.read_text(encoding="utf-8")

    _assert_functions(
        semantic_tests,
        {
            "test_grouped_semantic_schema_for_bare_key_and_aggregates",
            "test_grouped_semantic_schema_for_qualified_key_and_alias",
            "test_equivalent_bare_and_qualified_group_keys_diagnose_later_duplicate",
            "test_unknown_group_key_suppresses_dependent_projection_cascade",
            "test_non_grouped_plain_projection_is_rejected_with_unknown_schema_field",
            "test_scalar_group_key_expression_projection_is_deferred",
            "test_unaliased_grouped_aggregate_projection_is_rejected_and_suppressed",
            "test_pure_grouping_without_aggregate_is_deferred_but_schema_is_known",
            "test_unsupported_grouped_order_by_items_emit_s2321",
            "test_grouped_aggregate_invalid_shapes_match_phase20_behavior",
        },
    )
    for code in (
        "PIE-S2102",
        "PIE-S2310",
        "PIE-S2311",
        "PIE-S2313",
        "PIE-S2314",
        "PIE-S2315",
        "PIE-S2317",
        "PIE-S2318",
        "PIE-S2319",
        "PIE-S2320",
        "PIE-S2321",
    ):
        assert code in _read(semantic_tests)

    for required in (
        "| `PIE-S2316` | Historical GROUP BY IR/SQL lowering gate, retired after SQL lowering |",
        "| `PIE-S2317` | Duplicate GROUP BY key |",
        "| `PIE-S2318` | Non-grouped projection in grouped relation |",
        "| `PIE-S2319` | Grouped scalar projection is deferred |",
        "| `PIE-S2320` | Pure grouped output without an aggregate is deferred |",
        "| `PIE-S2321` | Grouped ORDER BY is deferred |",
    ):
        assert required in diagnostics

    _assert_contains_all(
        hardening_tests,
        (
            "PIE-S2309",
            "duplicate_group_key",
            "unknown_group_key",
            "non_grouped_projection",
            "scalar_grouped_projection",
            "pure_grouping",
            "grouped_order_by",
            "unaliased_aggregate",
            "nested_aggregate",
            "aggregate_composition",
            "wrong_arity",
            "wrong_type",
            "aggregate_expression_argument",
        ),
    )


def test_ir_sql_downstream_and_malformed_backend_coverage_is_locked() -> None:
    ir_tests = REPO_ROOT / "tests/test_phase21_group_by_ir_lowering.py"
    sql_tests = REPO_ROOT / "tests/test_phase21_group_by_sql_lowering.py"
    hardening_tests = REPO_ROOT / "tests/test_phase21_group_by_cli_hardening.py"
    ir_audit = REPO_ROOT / "tests/test_phase21_group_by_ir_lowering_audit.py"

    _assert_functions(
        ir_tests,
        {
            "test_grouped_relation_lowers_group_keys_after_semantic_gate_retirement",
            "test_no_group_relation_uses_empty_group_keys_default",
            "test_bare_and_qualified_duplicate_group_keys_lower_once_in_source_order",
            "test_unknown_group_key_is_not_lowered_into_precise_group_key_ir",
            "test_grouped_aggregate_projections_and_row_schema_survive_ir_lowering",
            "test_direct_sql_emitters_succeed_for_grouped_ir",
            "test_direct_sql_emitters_use_relation_name_for_downstream_from_grouped_ir",
            "test_cli_emit_sql_succeeds_for_grouped_ir",
        },
    )
    _assert_contains_all(
        ir_audit,
        (
            "group_keys: tuple[FieldRefIR, ...] = ()",
            "PostgreSQL GROUP BY keys must be resolved fields",
            "MySQL GROUP BY keys must be resolved fields",
            "PostgreSQL GROUP BY keys must be unique",
            "MySQL GROUP BY keys must be unique",
            "GROUP BY lowering gate is retired; valid GROUP BY lowers to SQL",
        ),
    )
    _assert_functions(
        sql_tests,
        {
            "test_downstream_from_grouped_relation_uses_relation_name_without_expansion",
            "test_postgres_group_keys_render_in_ir_source_order_with_qualified_alias",
            "test_malformed_grouped_ir_fails_closed_with_pie_b1000",
        },
    )
    _assert_functions(
        hardening_tests,
        {
            "test_downstream_from_grouped_cli_json_uses_relation_name_without_expansion",
            "test_malformed_grouped_ir_direct_emitters_fail_closed_with_pie_b1000",
        },
    )
    _assert_contains_all(
        hardening_tests,
        (
            "PIE-B1000",
            "unresolved_group_key",
            "non_field_group_key",
            "duplicate_group_key",
            "grouped_order_by",
            "non_grouped_projection",
            "pure_grouped_output",
            "unsupported_aggregate",
            'FROM "grouped_orders"',
            "FROM `grouped_orders`",
            '"WITH" not in downstream_sql',
            '"(SELECT" not in downstream_sql',
            '"FROM (" not in downstream_sql',
        ),
    )


def test_golden_inventory_and_no_group_sql_stability_are_locked() -> None:
    phase21_fixtures = {
        path.name for path in (FIXTURE_ROOT / "phase21").iterdir() if path.is_file()
    }
    grouped_goldens = {
        path.name
        for path in GOLDEN_ROOT.iterdir()
        if path.is_file() and "group_by" in path.name
    }

    assert phase21_fixtures == GROUPED_FIXTURES
    assert grouped_goldens == GROUPED_SQL_GOLDENS
    for golden in GROUPED_SQL_GOLDENS:
        sql = (GOLDEN_ROOT / golden).read_text(encoding="utf-8")
        assert "GROUP BY" in sql
        assert "COUNT(*)" in sql

    check_goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(check_goldens, "SQL_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(check_goldens, "FIXTURE_INPUTS"),
    )
    reference_tests = cast(tuple[Path, ...], getattr(check_goldens, "REFERENCE_TESTS"))
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(check_goldens, "audit"))

    assert GROUPED_SQL_GOLDENS <= sql_fixtures
    assert fixture_inputs["emit_sql_group_by_aggregate.sql"] == (
        "tests/fixtures/phase21/postgres_group_by_aggregate.pietto",
    )
    assert fixture_inputs["emit_mysql_group_by_aggregate.sql"] == (
        "tests/fixtures/phase21/mysql_group_by_aggregate.pietto",
    )
    assert Path("tests/test_phase21_group_by_sql_lowering.py") in reference_tests
    assert Path("tests/test_phase19_count_sql.py") in reference_tests
    assert Path("tests/test_phase20_sum_avg_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()

    for path in (
        REPO_ROOT / "tests/test_phase19_count_sql.py",
        REPO_ROOT / "tests/test_phase20_sum_avg_sql.py",
    ):
        _assert_contains_all(
            path,
            (
                "matches_reviewed_golden",
                "success_preserves_v1_shape",
                "output_writes_exact_sql",
            ),
        )
    _assert_functions(
        REPO_ROOT / "tests/test_phase19_count_sql.py",
        {"test_malformed_aggregate_ir_shapes_still_fail_closed"},
    )
    _assert_functions(
        REPO_ROOT / "tests/test_phase20_sum_avg_sql.py",
        {"test_malformed_hand_built_sum_avg_ir_fails_closed_with_pie_b1000"},
    )


def test_slice9_non_goals_and_forbidden_surface_locks_remain_explicit() -> None:
    plan = _normalized(PLAN_PATH)
    hardening_audit = REPO_ROOT / "tests/test_phase21_group_by_hardening_audit.py"
    audit_source = _read(hardening_audit)

    for required in (
        "Slice 9 adds no production behavior, syntax, SQL feature, fixture, golden, `scripts/check_goldens.py` inventory, diagnostics, public API, dependency, lockfile, CI, runtime, database, UI, LSP, or policy DSL behavior",
        "Slice 9 adds no grouped `order by`, HAVING user syntax, `satisfying`, `filter`, JOIN, relationship-driven query behavior, aggregate expression arguments, Decimal aggregate semantics, casts, rollup, cube, grouping sets, window functions, nested results, SQLGlot, or runtime/database execution",
    ):
        assert required in plan

    for locked_surface in (
        '"grammar"',
        '"generated"',
        '"parser_ast"',
        '"semantic"',
        '"ir"',
        '"sql"',
        '"cli"',
        '"check_goldens"',
        '"fixtures"',
        '"readme"',
        '"agents"',
        '"pietto_v09"',
        '"diagnostics"',
        '"pyproject"',
        '"uv_lock"',
        '"github"',
    ):
        assert locked_surface in audit_source
    assert "test_slice8_forbidden_implementation_surfaces_are_unchanged" in audit_source


def _assert_functions(path: Path, expected: set[str]) -> None:
    assert expected <= _function_names(path)


def _assert_contains_all(path: Path, expected: tuple[str, ...]) -> None:
    source = _read(path)
    for item in expected:
        assert item in source


def _function_names(path: Path) -> set[str]:
    tree = ast.parse(_read(path), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_goldens", CHECK_GOLDENS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
