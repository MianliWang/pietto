from __future__ import annotations

import ast
import hashlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from pietto.semantic.catalog import BUILTIN_FUNCTIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-24-aggregate-function-expansion-ii.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
GOLDEN_ROOT = REPO_ROOT / "tests/fixtures/golden"

PHASE24_ARTIFACTS = (
    "docs/plan/phase-24-aggregate-function-expansion-ii.md",
    "tests/test_phase24_aggregate_function_expansion_candidate_decision.py",
    "tests/test_phase24_count_distinct_semantics.py",
    "tests/test_phase24_count_distinct_ir.py",
    "tests/test_phase24_count_distinct_sql.py",
    "tests/test_phase24_decimal_aggregate_contract.py",
    "tests/test_phase24_decimal_aggregate_semantics.py",
    "tests/test_phase24_decimal_aggregate_ir.py",
    "tests/test_phase24_decimal_aggregate_sql.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
)

PHASE24_SQL_GOLDENS = {
    "emit_sql_count_distinct_aggregate.sql",
    "emit_mysql_count_distinct_aggregate.sql",
    "emit_sql_grouped_count_distinct_aggregate.sql",
    "emit_mysql_grouped_count_distinct_aggregate.sql",
    "emit_sql_decimal_aggregate.sql",
    "emit_mysql_decimal_aggregate.sql",
    "emit_sql_grouped_decimal_aggregate.sql",
    "emit_mysql_grouped_decimal_aggregate.sql",
}

PHASE24_GOLDEN_INPUTS = {
    "emit_sql_count_distinct_aggregate.sql": (
        "tests/fixtures/phase24/postgres_count_distinct_aggregate.pietto",
    ),
    "emit_mysql_count_distinct_aggregate.sql": (
        "tests/fixtures/phase24/mysql_count_distinct_aggregate.pietto",
    ),
    "emit_sql_grouped_count_distinct_aggregate.sql": (
        "tests/fixtures/phase24/postgres_grouped_count_distinct_aggregate.pietto",
    ),
    "emit_mysql_grouped_count_distinct_aggregate.sql": (
        "tests/fixtures/phase24/mysql_grouped_count_distinct_aggregate.pietto",
    ),
    "emit_sql_decimal_aggregate.sql": (
        "tests/fixtures/phase24/postgres_decimal_aggregate.pietto",
    ),
    "emit_mysql_decimal_aggregate.sql": (
        "tests/fixtures/phase24/mysql_decimal_aggregate.pietto",
    ),
    "emit_sql_grouped_decimal_aggregate.sql": (
        "tests/fixtures/phase24/postgres_grouped_decimal_aggregate.pietto",
    ),
    "emit_mysql_grouped_decimal_aggregate.sql": (
        "tests/fixtures/phase24/mysql_grouped_decimal_aggregate.pietto",
    ),
}

LOCKED_BOUNDARY_SURFACES = {
    "cli": (
        "src/pietto/cli.py",
        1,
        "af378ad655ed3ffc230983e94ee40cfef3b4f67e01d902901c5933c317c1f90f",
    ),
    "semantic": (
        "src/pietto/semantic",
        20,
        "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "59c3921f21de398e06f6deca28f18871120bbf411110974c3df6ba7fa85970c4",
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
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "4078b89d21126706746e07052ac8870a70f7275bd02dfc0433552f5edf06c082",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "pyproject": (
        "pyproject.toml",
        1,
        "cf5894a9cb7ef0399126a7d424da4e3958fc92d8e6bed295939a6e6bac469099",
    ),
    "uv_lock": (
        "uv.lock",
        1,
        "b48bb27656ff3344a95ba92347f45173904801cd8bdccfd2b55106549c445ac0",
    ),
    "github": (
        ".github",
        1,
        "129f96212b5025e66254b2485195977770cf7765bd8977215c6dfaefd9e6e5ae",
    ),
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "readme": (
        "README.md",
        1,
        "d02d7fcebf8081452d439a2df3c120d04484d49ac167be49b39a0880588bbfb7",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "05905fd7db7c1c6c4f0a1f6648221daac4afcdce81a3cca72597b023d864995c",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "d212a96a247d4363268aedca6379745ea4a148be6d6c90a4a547a1fd2ebe763d",
    ),
}


def test_phase24_slice9_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE24_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 24 Slice 1 is complete as candidate decision and contract work only",
        "Phase 24 Slice 2 is complete as `count_distinct(field)` semantic validation and row-schema work",
        "Phase 24 Slice 3 is complete as `count_distinct(field)` IR lowering work",
        "Phase 24 Slice 4 is complete as `count_distinct(field)` SQL rendering and golden coverage",
        "Phase 24 Slice 5 is complete as Decimal aggregate semantic/type contract work only",
        "Phase 24 Slice 6 is complete as Decimal aggregate implementation, SQL rendering, and golden coverage",
        "Phase 24 Slice 7 is complete as an aggregate expression arguments readiness audit",
        "Phase 24 Slice 8 is complete as CLI/JSON/output hardening and static audit coverage",
        "Phase 24 Slice 9 is complete as completion audit and status lock work only",
        "Phase 24 Aggregate Function Expansion II is complete.",
        "Slice 9 adds only `tests/test_phase24_completion_audit.py`, this status documentation, and the candidate-decision status update needed to record the completed phase",
    ):
        assert required in plan


def test_phase24_final_scope_type_sql_and_json_contracts_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 24 final accepted new aggregate behavior is exactly direct aliased `count_distinct(field)` and `count_distinct(source.field)` projections",
        "direct-field Decimal `sum`, `avg`, `min`, and `max` aggregate projections",
        "no-GROUP and grouped `select:` contexts",
        "Count-distinct emits `COUNT(DISTINCT ...)` for PostgreSQL and MySQL",
        "Decimal aggregate results are logical `Decimal nullable` values",
        "SQL emits ordinary `SUM`, `AVG`, `MIN`, and `MAX` function calls without casts",
        "`count_distinct(field) -> Int not null`",
        "`count_distinct(source.field) -> Int not null`",
        "`sum(Decimal) -> Decimal nullable`",
        "`avg(Decimal) -> Decimal nullable`",
        "`min(Decimal) -> Decimal nullable`",
        "`max(Decimal) -> Decimal nullable`",
    ):
        assert required in plan

    count_distinct_goldens = (
        "emit_sql_count_distinct_aggregate.sql",
        "emit_mysql_count_distinct_aggregate.sql",
        "emit_sql_grouped_count_distinct_aggregate.sql",
        "emit_mysql_grouped_count_distinct_aggregate.sql",
    )
    for golden in count_distinct_goldens:
        assert "COUNT(DISTINCT" in _read(GOLDEN_ROOT / golden)

    for golden in (
        "emit_sql_decimal_aggregate.sql",
        "emit_mysql_decimal_aggregate.sql",
        "emit_sql_grouped_decimal_aggregate.sql",
        "emit_mysql_grouped_decimal_aggregate.sql",
    ):
        sql = _read(GOLDEN_ROOT / golden)
        for function_name in ("SUM(", "AVG(", "MIN(", "MAX("):
            assert function_name in sql
        assert "CAST(" not in sql
        assert "::" not in sql


def test_phase24_uses_existing_diagnostics_and_aggregate_names() -> None:
    for aggregate_name in ("count", "sum", "avg", "min", "max", "count_distinct"):
        assert aggregate_name not in BUILTIN_FUNCTIONS

    diagnostics = _read(DIAGNOSTICS_PATH)
    phase24_tests = "\n".join(
        _read(REPO_ROOT / relative_path)
        for relative_path in PHASE24_ARTIFACTS
        if relative_path.startswith("tests/")
    )
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
        assert code in phase24_tests

    plan = _normalized(PLAN_PATH)
    for required in (
        "`PIE-S2308` for invalid aggregate context",
        "`PIE-S2309` for wrong arity",
        "`PIE-S2310` for aggregate composition",
        "`PIE-S2311` for nested aggregate",
        "`PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections",
        "`PIE-S2313` for unaliased aggregate projections",
        "`PIE-S2314` for unsupported direct field argument type",
        "`PIE-S2315` for expression arguments",
        "Malformed backend IR remains fail-closed through existing `PIE-B1000`",
    ):
        assert required in plan


def test_phase24_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase24_count_distinct_semantics.py": {
            "test_no_group_count_distinct_accepts_comparable_direct_field_types",
            "test_no_group_qualified_count_distinct_field_is_accepted",
            "test_grouped_count_distinct_projection_is_accepted",
            "test_grouped_qualified_count_distinct_projection_is_accepted",
            "test_count_distinct_invalid_projection_shapes_use_existing_diagnostics",
            "test_count_distinct_in_invalid_context_remains_rejected",
        },
        "tests/test_phase24_count_distinct_ir.py": {
            "test_no_group_count_distinct_lowers_to_one_arg_aggregate_ir",
            "test_no_group_qualified_count_distinct_lowers_to_qualified_field_ref",
            "test_grouped_count_distinct_lowers_with_group_keys_preserved",
            "test_direct_lower_expr_for_valid_count_distinct_uses_aggregate_call_ir",
            "test_invalid_count_distinct_shapes_do_not_emit_aggregate_call_ir",
        },
        "tests/test_phase24_count_distinct_sql.py": {
            "test_direct_renderers_support_count_distinct_field_types",
            "test_direct_backend_count_distinct_sql_matches_reviewed_golden",
            "test_count_distinct_goldens_lock_function_and_qualification_shape",
            "test_malformed_hand_built_count_distinct_ir_fails_closed_with_pie_b1000",
            "test_phase24_count_distinct_goldens_are_registered_and_audited",
        },
        "tests/test_phase24_decimal_aggregate_contract.py": {
            "test_slice5_status_is_contract_only_without_behavior_changes",
            "test_decimal_aggregate_result_contracts_are_locked",
            "test_decimal_precision_scale_and_portability_non_promises_are_locked",
            "test_slice6_production_helpers_authorize_decimal_aggregates",
        },
        "tests/test_phase24_decimal_aggregate_semantics.py": {
            "test_no_group_decimal_aggregates_are_accepted",
            "test_qualified_decimal_aggregate_arguments_are_accepted",
            "test_grouped_decimal_aggregate_projections_are_accepted",
            "test_decimal_aggregate_expression_arguments_remain_deferred",
            "test_decimal_multiplication_is_not_enabled_outside_aggregates",
            "test_decimal_aggregate_in_invalid_context_remains_rejected",
        },
        "tests/test_phase24_decimal_aggregate_ir.py": {
            "test_no_group_decimal_aggregates_lower_to_existing_aggregate_call_ir",
            "test_qualified_decimal_aggregates_lower_to_qualified_field_refs",
            "test_grouped_decimal_aggregates_lower_with_group_keys_preserved",
            "test_direct_lower_expr_for_decimal_aggregate_uses_aggregate_call_ir",
            "test_invalid_decimal_aggregate_shapes_do_not_emit_aggregate_call_ir",
        },
        "tests/test_phase24_decimal_aggregate_sql.py": {
            "test_direct_renderers_support_decimal_aggregate_shapes",
            "test_direct_backend_decimal_aggregate_sql_matches_reviewed_golden",
            "test_decimal_aggregate_goldens_lock_no_cast_function_shape",
            "test_malformed_hand_built_decimal_aggregate_ir_fails_closed_with_pie_b1000",
            "test_phase24_decimal_aggregate_goldens_are_registered_and_audited",
        },
        "tests/test_phase24_aggregate_expression_arguments_readiness.py": {
            "test_slice7_status_is_docs_static_audit_only",
            "test_aggregate_expression_arguments_still_fail_with_s2315",
            "test_direct_field_aggregate_vocabulary_remains_accepted",
            "test_slice7_boundary_surfaces_remain_post_slice6_hash_locked",
        },
        "tests/test_phase24_cli_json_output_hardening.py": {
            "test_cli_text_phase24_postgres_aggregate_sql_matches_reviewed_golden",
            "test_cli_json_phase24_postgres_aggregate_sql_preserves_v1_shape",
            "test_cli_text_phase24_output_writes_exact_sql",
            "test_cli_json_phase24_output_writes_sql_and_keeps_artifacts",
            "test_cli_text_aggregate_expression_argument_emits_sql_after_sql_slice",
            "test_cli_json_aggregate_expression_argument_writes_output_after_sql_slice",
            "test_cli_json_backend_pie_b1000_does_not_write_output",
            "test_slice8_boundary_surfaces_remain_post_slice7_hash_locked",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_phase24_golden_inventory_and_json_v1_shape_are_locked() -> None:
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
    assert PHASE24_SQL_GOLDENS <= sql_fixtures
    for golden, inputs in PHASE24_GOLDEN_INPUTS.items():
        assert fixture_inputs[golden] == inputs
        assert (GOLDEN_ROOT / golden).is_file()
    assert Path("tests/test_phase24_count_distinct_sql.py") in reference_tests
    assert Path("tests/test_phase24_decimal_aggregate_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()

    cli_tests = _read(REPO_ROOT / "tests/test_phase24_cli_json_output_hardening.py")
    for required in (
        'assert result["schema_version"] == 1',
        "EMIT_SQL_KEYS",
        '"schema_version"',
        '"command"',
        '"ok"',
        '"path"',
        '"dialect"',
        '"diagnostics"',
        '"cli_errors"',
        '"artifacts"',
        '"output"',
        '"schema_version_v2"',
        '"project"',
        '"project_root"',
        '"files"',
        'assert result["output"] == {"path": str(output_path), "written": True}',
        'assert result["output"] == {"path": str(output_path), "written": False}',
        'assert result["artifacts"] == []',
        "PIE-B1000",
    ):
        assert required in cli_tests


def test_phase24_deferred_capabilities_and_slice9_boundaries_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "aggregate expression argument implementation",
        "`sum(amount + tax)`",
        "`count_distinct(lower(status))`",
        "generic `DISTINCT` keyword syntax",
        "`count(distinct field)`",
        "aggregate modifier system",
        "nested aggregates",
        "aggregate composition",
        "Decimal arithmetic",
        "Decimal precision/scale modeling",
        "casts",
        "schema introspection",
        "runtime/database execution",
        "connector execution",
        "JOIN behavior",
        "relationship behavior",
        "JSON schema changes",
        "CLI option changes",
        "public API expansion",
        "dependency/config/CI/package changes",
        "Slice 9 locks the completed Phase 24 docs, tests, goldens, diagnostics, public API, JSON v1, CLI, dependency, config, CI, package, runtime, database, connector execution, schema introspection, relationship/JOIN, and deferred capability boundaries",
        "It changes no production behavior, semantic implementation, Semantic IR, IR model, SQL renderer, CLI option, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency, lockfile, package metadata, CI",
    ):
        assert required in plan


def test_slice9_boundary_surfaces_remain_post_slice8_hash_locked() -> None:
    for _name, (
        path_or_paths,
        expected_count,
        expected_hash,
    ) in LOCKED_BOUNDARY_SURFACES.items():
        paths = _paths(path_or_paths)

        assert len(paths) == expected_count
        assert _digest(paths) == expected_hash


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
        "pietto_phase24_completion_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paths(path_or_paths: str | tuple[str, ...]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, tuple):
        return tuple(REPO_ROOT / path for path in path_or_paths)

    path = REPO_ROOT / path_or_paths
    if path.is_file():
        return (path,)
    return tuple(
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and "__pycache__" not in item.parts
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix().encode()
        digest.update(relative_path + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
