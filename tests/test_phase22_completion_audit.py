from __future__ import annotations

import ast
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from pietto.semantic.catalog import BUILTIN_FUNCTIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-22-min-max-aggregate-mvp.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
GOLDEN_ROOT = REPO_ROOT / "tests/fixtures/golden"

PHASE22_ARTIFACTS = (
    "docs/plan/phase-22-min-max-aggregate-mvp.md",
    "tests/test_phase22_min_max_candidate_decision.py",
    "tests/test_phase22_min_max_semantics.py",
    "tests/test_phase22_min_max_ir.py",
    "tests/test_phase22_min_max_sql.py",
    "tests/test_phase22_completion_audit.py",
)

PHASE22_SQL_GOLDENS = {
    "emit_sql_min_max_aggregate.sql",
    "emit_mysql_min_max_aggregate.sql",
    "emit_sql_grouped_min_max_aggregate.sql",
    "emit_mysql_grouped_min_max_aggregate.sql",
}


def test_phase22_slice6_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE22_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 22 Slice 1 is complete as candidate decision and contract work only",
        "Phase 22 Slice 2 is complete as min/max semantic validation and row-schema work",
        "Phase 22 Slice 3 is complete as min/max IR lowering work",
        "Phase 22 Slice 4 is complete as PostgreSQL/MySQL SQL lowering and golden coverage",
        "Phase 22 Slice 5 is complete as CLI, JSON v1, output-file, malformed-IR, and no-regression hardening",
        "Phase 22 Slice 6 is complete as completion audit, status lock, and narrow behavior-neutral format cleanup",
        "Phase 22 Min/Max Aggregate MVP is complete.",
        "Slice 6 adds only `tests/test_phase22_completion_audit.py`, status documentation, and behavior-neutral formatting of the known Phase 22 format blockers",
    ):
        assert required in plan


def test_min_max_final_scope_type_and_nullability_contract_is_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 22 final accepted source shapes are exactly direct aliased `min(field)` and `max(field)` aggregate projections",
        "no-GROUP and grouped `select:` contexts",
        "one direct bare field or existing single-input qualified field reference",
        "`Int`, `Float`, `Date`, and `Timestamp`",
        "`min(Int) -> Int nullable`",
        "`max(Int) -> Int nullable`",
        "`min(Float) -> Float nullable`",
        "`max(Float) -> Float nullable`",
        "`min(Date) -> Date nullable`",
        "`max(Date) -> Date nullable`",
        "`min(Timestamp) -> Timestamp nullable`",
        "`max(Timestamp) -> Timestamp nullable`",
        "The result type is the same canonical type as the argument and is nullable",
        "`min` and `max` remain aggregate names only, not scalar builtins",
    ):
        assert required in plan


def test_min_max_uses_existing_aggregate_diagnostics_and_not_scalar_builtins() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS
    assert "min" not in BUILTIN_FUNCTIONS
    assert "max" not in BUILTIN_FUNCTIONS

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
    assert "No new diagnostic code is added for Phase 22" in plan


def test_slice2_through_slice5_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase22_min_max_semantics.py": {
            "test_no_group_direct_aliased_min_max_int_projections_are_accepted",
            "test_no_group_min_max_accept_date_and_timestamp_arguments",
            "test_qualified_min_max_field_arguments_are_accepted",
            "test_grouped_min_max_projections_are_accepted",
            "test_min_max_reject_unsupported_direct_field_argument_types",
            "test_min_max_invalid_projection_shapes_use_existing_aggregate_diagnostics",
            "test_projection_alias_is_not_a_min_max_argument",
            "test_min_max_in_invalid_context_is_rejected",
            "test_invalid_min_max_projection_aliases_keep_unknown_schema",
            "test_count_sum_and_avg_semantics_remain_unchanged",
            "test_min_and_max_are_not_scalar_builtin_functions",
        },
        "tests/test_phase22_min_max_ir.py": {
            "test_no_group_min_max_projections_lower_to_aggregate_call_ir",
            "test_qualified_min_max_arguments_lower_to_qualified_field_refs",
            "test_grouped_min_max_projections_lower_to_aggregate_call_ir",
            "test_direct_lower_expr_for_valid_min_max_uses_aggregate_call_ir",
            "test_invalid_min_max_projection_shapes_do_not_emit_aggregate_call_ir",
            "test_min_max_in_where_context_does_not_emit_aggregate_call_ir",
            "test_count_sum_avg_ir_behavior_remains_unchanged",
        },
        "tests/test_phase22_min_max_sql.py": {
            "test_direct_backend_min_max_sql_matches_reviewed_golden",
            "test_cli_text_min_max_sql_matches_reviewed_golden",
            "test_cli_json_min_max_sql_success_preserves_v1_shape",
            "test_cli_json_min_max_sql_output_writes_exact_sql",
            "test_min_max_goldens_lock_extrema_function_and_qualification_shape",
            "test_historical_count_sum_avg_sql_goldens_remain_byte_stable",
            "test_invalid_min_max_emit_sql_json_output_fails_before_sql_without_writing",
            "test_malformed_hand_built_min_max_ir_fails_closed_with_pie_b1000",
            "test_phase22_min_max_goldens_are_registered_and_audited",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_min_max_golden_inventory_and_json_v1_shape_are_locked() -> None:
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
    assert PHASE22_SQL_GOLDENS <= sql_fixtures
    assert fixture_inputs["emit_sql_min_max_aggregate.sql"] == (
        "tests/fixtures/phase22/postgres_min_max_aggregate.pietto",
    )
    assert fixture_inputs["emit_mysql_min_max_aggregate.sql"] == (
        "tests/fixtures/phase22/mysql_min_max_aggregate.pietto",
    )
    assert fixture_inputs["emit_sql_grouped_min_max_aggregate.sql"] == (
        "tests/fixtures/phase22/postgres_grouped_min_max_aggregate.pietto",
    )
    assert fixture_inputs["emit_mysql_grouped_min_max_aggregate.sql"] == (
        "tests/fixtures/phase22/mysql_grouped_min_max_aggregate.pietto",
    )
    assert Path("tests/test_phase22_min_max_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()

    for golden in PHASE22_SQL_GOLDENS:
        assert (GOLDEN_ROOT / golden).is_file()

    sql_tests = _read(REPO_ROOT / "tests/test_phase22_min_max_sql.py")
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
        "PIE-B1000",
    ):
        assert required in sql_tests


def test_phase22_forbidden_features_and_surfaces_remain_deferred() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "`count(field)`",
        "distinct aggregates or `count_distinct(field)`",
        "aggregate expression arguments such as `sum(amount + tax)`",
        "aggregate filters",
        "result predicates, `satisfying`, post-select `where`, `such that`, or SQL `HAVING` user syntax",
        "grouped `order by`",
        "`Text`, `Decimal`, `Bool`, `Bytes`, `Json`, `UUID`, or `Any` `min/max` semantics",
        "casts",
        "relationship-driven query behavior",
        "JOIN or relation composition",
        "project configuration or multi-file implementation",
        "runtime/database execution",
        "UI, Web playground, or LSP implementation",
        "policy/security DSL or runtime security implementation",
        "Slice 6 changes no grammar, generated ANTLR, AST, semantic acceptance, Semantic IR behavior, SQL renderer behavior, SQL fixtures or goldens, CLI options, JSON v1 schema, public API, dependency, lockfile, package metadata, CI, runtime/database behavior, UI, LSP, or relationship/JOIN behavior",
    ):
        assert required in plan


def test_status_documents_record_phase22_without_runtime_or_schema_claims() -> None:
    for relative_path in (
        "AGENTS.md",
        "docs/spec/pietto-v0.9.md",
    ):
        document = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 22",
            "Min/Max Aggregate MVP",
            "`min(field)` / `max(field)`",
            "Int, Float, Date, and Timestamp",
            "nullable same-type result",
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
        "pietto_phase22_completion_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
