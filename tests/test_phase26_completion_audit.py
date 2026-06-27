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
        "4078b89d21126706746e07052ac8870a70f7275bd02dfc0433552f5edf06c082",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "ast_nodes": (
        "src/pietto/ast_nodes.py",
        1,
        "f12e5e0460169056e28f6b2081d755eb2bc84c70550adc1d837d44e300c302ae",
    ),
    "ast_builder": (
        "src/pietto/ast_builder.py",
        1,
        "9a9c7bd4b0ad3a55354b89474b1b6a94319cf167250697e891e2af93fd0599b4",
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
    "cli": (
        "src/pietto/cli.py",
        1,
        "e3357cbee66ef1a219a85085bdbfd51278812e0dec74b2f9ca0196c68e92bb48",
    ),
    "cli_json": (
        "src/pietto/cli_json.py",
        1,
        "573fd193b98a746cfd84a6990a22248d2b63a7fc0ed1069f442ffff9c4dd99e7",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "0c82aa6cde14aac504cca5028f28365c1127e59a748827a2108ced224bbbd7a4",
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
        "a11700c1fc9d16db55ef323f11c8d8f4746d0d96ce2e3cd497fa51c910e63cf8",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "2f8022e7f683f4a2baca4c02c0ed9e4cbded996310298f68c26d5151a1723ec0",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "bb3fc653e0cde9e74dffdcaa2d2bb83285c4cf84cb35d298a22c3193fc9a2d19",
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
