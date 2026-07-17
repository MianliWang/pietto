from __future__ import annotations

import ast
import hashlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
)
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE26_ARTIFACTS = (
    "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md",
    "tests/test_phase26_aggregate_expression_arguments_candidate_decision.py",
    "tests/test_phase26_numeric_scalar_expression_semantics.py",
    "tests/test_phase26_decimal_scalar_expression_semantics.py",
    "tests/test_phase26_aggregate_expression_argument_semantics.py",
    "tests/test_phase26_count_distinct_text_transform_semantics.py",
    "tests/test_phase26_aggregate_expression_argument_ir.py",
    "tests/test_phase26_aggregate_expression_argument_sql.py",
    "tests/test_phase26_aggregate_expression_argument_cli_json_output.py",
    "tests/test_phase26_completion_audit.py",
)

LOCKED_BOUNDARY_SURFACES = {
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "03f2eb98ab656dfe4c33bd8088306f3525150c738f42bf09640c02d973d54a2f",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    ),
    "ast_nodes": (
        "src/pietto/ast_nodes.py",
        1,
        "9946bd71566f8c7fd72dfa22b972722922087b7588b435cce59daa1fc25c560d",
    ),
    "ast_builder": (
        "src/pietto/ast_builder.py",
        1,
        "c351d001982ee52274ec21fd6af151baea8b9153caf524415f50bfee17fbcf3d",
    ),
    "semantic": (
        "src/pietto/semantic",
        27,
        "3c6d12576f659615b3a360a3e9a3efa92c6d08740cfb2dd30be29223f6fbcd43",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
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
        "677b1e4f29d16f7bc90335afcfdb36fed42761795814adbf37d657eae267983d",
    ),
    "check_generated": (
        "scripts/check_generated.py",
        1,
        "42029010b8b9762784928384a7b5ee2bb956269a0f2185ec11491666e11cd088",
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
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "readme": (
        "README.md",
        1,
        "a9012c03259cc7d8cb983f70fcd6481719f06ead73a0decbea7f7a4f76b55ac2",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "27fef9e67bec8917eff21ad2dd41cb22f9feea37e62200ac78864cba2d5aa589",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "8c5f7ae8e5f6bbcbe7c004e681ba4bf8e417efb62240137f83ccd6d5a8472b39",
    ),
}


def test_phase26_slice9_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE26_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 26 Slice 1 is complete as candidate decision, exact contract, and static audit work only",
        "Phase 26 Slice 2 is complete as numeric scalar expression semantics audit and status work only",
        "Phase 26 Slice 3 is complete as a narrow Decimal scalar arithmetic semantics slice",
        "Phase 26 Slice 4 is complete as a semantic-only aggregate expression argument slice",
        "Phase 26 Slice 5 is complete as a semantic-only `count_distinct` Text transform expression argument slice",
        "Phase 26 Slice 6 is complete as an IR-only aggregate expression argument lowering slice",
        "Phase 26 Slice 7 is complete as a SQL-backend lowering slice",
        "Phase 26 Slice 8 is complete as CLI / JSON / output and `satisfying` hardening work",
        "Phase 26 Slice 9 is complete as completion audit and status lock work only",
        "Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is complete.",
        "Slice 9 adds only `tests/test_phase26_completion_audit.py`, this status documentation, minimal status sync in `README.md`, `AGENTS.md`, and `docs/spec/pietto-v0.9.md`, and narrow hash-lock updates in `tests/test_phase24_completion_audit.py`",
        "Slice 9 adds no new production behavior, semantic acceptance, IR model or lowering, SQL rendering, CLI implementation, JSON schema or serializer, fixture, golden, script, dependency, package metadata, CI, runtime/database, project/multi-file, public MySQL API, relationship/JOIN, or Phase 27 behavior",
    ):
        assert required in plan


def test_phase26_final_accepted_behavior_and_status_docs_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    for required in (
        "`sum(field-only numeric expression)`",
        "`avg(field-only numeric expression)`",
        "`count_distinct(lower/trim Text transform chain over one Text field)`",
        "`Decimal + Decimal -> Decimal`",
        "`Decimal - Decimal -> Decimal`",
        "`sum(amount + tax)` is semantically accepted in Slice 4, lowered as `AggregateCallIR` in Slice 6, and rendered by PostgreSQL/private MySQL in Slice 7",
        "`count_distinct(lower(status))` is semantically accepted in Slice 5, lowered as `AggregateCallIR` in Slice 6, and rendered by PostgreSQL/private MySQL in Slice 7",
        "Phase 25 rule that HAVING does not rely on SELECT alias portability",
        "Phase 26 does not change JSON v1 schema, stdout/stderr separation, CLI option names, selected dialect values, or output-file safety rules",
    ):
        assert required in plan

    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation",
            "complete",
            "sum(amount + tax)",
            "avg(score * weight)",
            "count_distinct(lower(trim(status)))",
            "no runtime/database execution",
            "no JSON schema change",
            "no public MySQL API expansion",
            "no relationship/JOIN behavior",
        ):
            assert required in status_doc


def test_phase26_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase26_aggregate_expression_arguments_candidate_decision.py": {
            "test_aggregate_expression_argument_mvp_and_deferrals_are_locked",
            "test_satisfying_interaction_and_diagnostic_precedence_are_locked",
            "test_semantic_ir_sql_and_cli_contracts_are_locked",
            "test_fixture_golden_policy_and_slice_plan_are_locked",
        },
        "tests/test_phase26_numeric_scalar_expression_semantics.py": {
            "test_int_float_binary_arithmetic_computed_projection_schema_is_locked",
            "test_numeric_arithmetic_inside_where_comparison_is_locked",
            "test_division_remains_deferred_without_diagnostic",
            "test_aggregate_expression_boundaries_remain_deferred",
            "test_direct_aggregate_inside_satisfying_still_uses_s2308",
        },
        "tests/test_phase26_decimal_scalar_expression_semantics.py": {
            "test_decimal_add_subtract_computed_projection_schema_is_locked",
            "test_decimal_arithmetic_inside_decimal_comparison_shape_is_locked",
            "test_decimal_division_remains_deferred_without_diagnostic",
            "test_aggregate_expression_boundaries_remain_deferred",
            "test_direct_aggregate_inside_satisfying_still_uses_s2308",
        },
        "tests/test_phase26_aggregate_expression_argument_semantics.py": {
            "test_sum_avg_field_only_expression_arguments_are_semantically_accepted",
            "test_grouped_sum_avg_expression_arguments_are_semantically_accepted",
            "test_unsupported_aggregate_expression_arguments_use_s2315",
            "test_nested_aggregate_and_composition_boundaries_remain_unchanged",
            "test_direct_aggregate_inside_satisfying_still_uses_s2308",
        },
        "tests/test_phase26_count_distinct_text_transform_semantics.py": {
            "test_count_distinct_lower_trim_transform_arguments_are_accepted",
            "test_satisfying_resolves_count_distinct_transform_projection_alias",
            "test_unsupported_count_distinct_transform_shapes_use_s2315",
            "test_direct_count_distinct_inside_satisfying_still_uses_s2308",
        },
        "tests/test_phase26_aggregate_expression_argument_ir.py": {
            "test_sum_avg_numeric_expression_arguments_lower_to_aggregate_call_ir",
            "test_count_distinct_transform_arguments_lower_to_aggregate_call_ir",
            "test_grouped_expression_argument_aggregates_preserve_group_keys",
            "test_unsupported_aggregate_expression_shapes_remain_before_ir",
            "test_direct_aggregate_inside_satisfying_remains_semantic_error",
        },
        "tests/test_phase26_aggregate_expression_argument_sql.py": {
            "test_direct_renderers_render_supported_expression_argument_aggregates",
            "test_backends_emit_no_group_aggregate_expression_argument_sql",
            "test_backends_emit_grouped_aggregate_expression_argument_sql",
            "test_grouped_satisfying_uses_underlying_aggregate_expression_not_alias",
            "test_unsupported_semantic_shapes_stop_before_sql_without_artifacts",
            "test_malformed_hand_built_aggregate_expression_ir_fails_closed_with_pie_b1000",
        },
        "tests/test_phase26_aggregate_expression_argument_cli_json_output.py": {
            "test_cli_text_emits_supported_expression_argument_sql",
            "test_cli_json_success_preserves_v1_shape_for_expression_arguments",
            "test_cli_text_output_replaces_file_with_supported_expression_argument_sql",
            "test_cli_json_output_writes_file_and_keeps_expression_argument_artifacts",
            "test_unsupported_expression_argument_json_output_does_not_write",
            "test_cli_text_grouped_satisfying_uses_underlying_aggregate_expression",
            "test_invalid_satisfying_expression_argument_boundaries_do_not_write_output",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_phase26_diagnostics_and_unsupported_boundaries_are_locked() -> None:
    diagnostics = _read(DIAGNOSTICS_PATH)
    phase26_tests = "\n".join(
        _read(REPO_ROOT / relative_path)
        for relative_path in PHASE26_ARTIFACTS
        if relative_path.startswith("tests/")
    )
    for code in (
        "PIE-S2308",
        "PIE-S2310",
        "PIE-S2311",
        "PIE-S2314",
        "PIE-S2315",
        "PIE-S2323",
        "PIE-B1000",
    ):
        assert f"| `{code}` |" in diagnostics
        assert code in phase26_tests

    plan = _normalized(PLAN_PATH)
    for required in (
        "`sum(amount + 1)` remains deferred through `PIE-S2315`",
        "`sum(amount / tax)` remains deferred through `PIE-S2315`",
        "`sum(avg(amount))` reports `PIE-S2311`",
        "`sum(amount) + 1` reports `PIE-S2310`",
        "`satisfying: sum(amount + tax) > 1000` reports `PIE-S2308`",
        "`count(expression)`",
        "`min(expression)`",
        "`max(expression)`",
        "modulo inside aggregate arguments",
        "Decimal multiplication",
        "mixed Decimal/Int arithmetic",
        "mixed Decimal/Float arithmetic",
        "all division inside aggregate arguments",
        "Projection aliases are not aggregate argument leaves",
    ):
        assert required in plan

    cli_tests = _read(
        REPO_ROOT
        / "tests/test_phase26_aggregate_expression_argument_cli_json_output.py"
    )
    for unsupported in (
        "value = sum(amount / tax)",
        "value = sum(amount % tax)",
        "value = avg(price * price)",
        "value = count_distinct(len(status))",
        "value = count_distinct(lower(amount))",
        "value = count(amount + tax)",
        "value = min(amount + tax)",
        "value = max(score * weight)",
        "sum(amount + tax) > 1000",
        "count_distinct(lower(trim(status))) > 10",
        "total > 1000",
    ):
        assert unsupported in cli_tests


def test_fixture_golden_inventory_and_inline_sql_policy_are_locked() -> None:
    goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(goldens, "SQL_FIXTURES"))
    json_fixtures = cast(frozenset[str], getattr(goldens, "JSON_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(goldens, "FIXTURE_INPUTS"),
    )
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(goldens, "audit"))

    assert len(sql_fixtures) == 32
    assert len(json_fixtures) == 5
    assert len(sql_fixtures | json_fixtures) == 37
    assert not any("phase26" in fixture for fixture in sql_fixtures | json_fixtures)
    assert not any(
        "phase26" in input_path
        for inputs in fixture_inputs.values()
        for input_path in inputs
    )
    assert not (REPO_ROOT / "tests/fixtures/phase26").exists()
    assert audit(REPO_ROOT) == ()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Slice 7 deliberately uses focused inline SQL assertions instead of new fixtures/goldens",
        "Existing fixture/golden bytes remain unchanged and are still covered by the existing golden audit",
        "Phase 26 adds no fixtures or goldens.",
        "`scripts/check_goldens.py` remains unchanged.",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
    ):
        assert required in plan


def test_public_api_json_runtime_project_and_relationship_boundaries_remain_deferred() -> (
    None
):
    plan = _normalized(PLAN_PATH)
    public_sql_api = _read(REPO_ROOT / "src/pietto/sql/__init__.py")
    sql_tests = _read(
        REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_sql.py"
    )
    cli_tests = _read(
        REPO_ROOT
        / "tests/test_phase26_aggregate_expression_argument_cli_json_output.py"
    )

    for required in (
        "runtime/database execution",
        "connector execution",
        "schema introspection",
        "project or multi-file implementation",
        "JOIN or relationship traversal",
        "JSON schema or serializer",
        "CLI option names",
        "public MySQL API expansion",
        "Phase 27",
    ):
        assert required in plan

    assert "emit_mysql_sql" not in public_sql_api
    assert "from pietto.sql.mysql import emit_mysql_sql" in sql_tests
    assert "EMIT_SQL_KEYS" in cli_tests
    for required in (
        'assert result["schema_version"] == 1',
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


def test_slice9_boundary_surfaces_remain_phase26_locked() -> None:
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
        "pietto_phase26_completion_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paths(path_or_paths: str | tuple[str, ...]) -> tuple[Path, ...]:
    relative_paths = (
        (path_or_paths,) if isinstance(path_or_paths, str) else path_or_paths
    )
    paths: list[Path] = []
    for relative_path in relative_paths:
        path = REPO_ROOT / relative_path
        if path.is_dir():
            paths.extend(
                sorted(
                    child
                    for child in path.rglob("*")
                    if child.is_file() and "__pycache__" not in child.parts
                )
            )
        else:
            paths.append(path)
    return tuple(paths)


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix().encode()
        digest.update(relative_path + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
