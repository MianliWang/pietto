from __future__ import annotations

import ast
import hashlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-25-result-predicate-satisfying-mvp.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE25_ARTIFACTS = (
    "docs/plan/phase-25-result-predicate-satisfying-mvp.md",
    "tests/test_phase25_satisfying_candidate_decision.py",
    "tests/test_phase25_satisfying_parser_ast.py",
    "tests/test_phase25_satisfying_semantics.py",
    "tests/test_phase25_satisfying_ir.py",
    "tests/test_phase25_satisfying_sql.py",
    "tests/test_phase25_completion_audit.py",
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
        21,
        "eb04af25b547ebc30aa700a8956be1880eab8426dd80e99278b2c0a668603b91",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "526e4bf82d1b8aa9d8c563021c7efc3092d9479eedb0ea7ca36a0cce0dd18c01",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "63e99f989500f83686963fba853fed27d76bc5e0c0ac2e58827fb336b2bb044a",
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
}


def test_phase25_slice7_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE25_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 25 Slice 1 is complete as candidate decision and exact contract work only",
        "Phase 25 Slice 2 is complete as parser/AST-only syntax preservation",
        "Phase 25 Slice 3 is complete as semantic validation and fail-closed hardening only",
        "Phase 25 Slice 4 is complete as IR-model-only representation work",
        "Phase 25 Slice 5 is complete as constructed-IR SQL lowering only",
        "Phase 25 Slice 6 is complete as source-pipeline enablement and CLI/JSON/output hardening",
        "Phase 25 Slice 7 is complete as completion audit and status lock work only",
        "Phase 25 Result Predicate / `satisfying` MVP is complete.",
        "Slice 7 adds focused completion audit coverage and records Phase 25 as complete",
        "Slice 7 adds no grammar, generated parser, AST, semantic behavior, IR behavior, SQL backend implementation, CLI implementation, CLI option, JSON schema, fixture, golden, script, dependency, package, CI, runtime/database, project/multi-file, public MySQL API, or relationship/JOIN behavior",
    ):
        assert required in plan


def test_satisfying_is_documented_as_result_predicate_syntax_not_having() -> None:
    plan = _normalized(PLAN_PATH)
    parser_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_parser_ast.py")

    for required in (
        "Pietto should add result-level filtering",
        "`where` remains pre-aggregate input-row filtering",
        "Future `satisfying:` is post-aggregate result filtering",
        "Pietto source does not gain a `having` clause",
        "Pietto does not expose a source-level `having` keyword or `HAVING:` clause",
        "Direct SQL `having` source syntax",
        "Rejected. Pietto source should use `satisfying:`",
    ):
        assert required in plan

    assert '"    having:\\n"' in parser_tests
    assert "test_invalid_satisfying_shapes_are_parser_errors" in parser_tests


def test_phase25_diagnostics_and_retired_pie_s2322_status_are_locked() -> None:
    diagnostics = _read(DIAGNOSTICS_PATH)
    plan = _normalized(PLAN_PATH)
    semantic_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_semantics.py")

    assert (
        "| `PIE-S2322` | Historical `satisfying` IR/SQL lowering gate, retired after source pipeline enablement |"
        in diagnostics
    )
    assert (
        "`PIE-S2322`: otherwise-valid `satisfying:` was semantically recognized, but IR/SQL lowering was deferred before Slice 6 source pipeline enablement"
        in plan
    )
    assert 'code="PIE-S2322"' not in _read(
        REPO_ROOT / "src/pietto/semantic/satisfying.py"
    )

    for code in (
        "PIE-S2323",
        "PIE-S2324",
        "PIE-S2325",
        "PIE-S2326",
        "PIE-S2327",
    ):
        assert f"| `{code}` |" in diagnostics
        assert code in plan
        assert code in semantic_tests

    for reused_code in ("PIE-S2308", "PIE-S2202", "PIE-S2105"):
        assert reused_code in semantic_tests


def test_phase25_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase25_satisfying_candidate_decision.py": {
            "test_satisfying_source_order_and_group_by_only_contract_are_locked",
            "test_satisfying_scope_is_select_output_names_only",
            "test_predicate_subset_and_deferred_expression_forms_are_locked",
            "test_required_non_goals_remain_explicitly_deferred",
            "test_slice_sequence_records_completed_slice6_and_future_completion_audit",
        },
        "tests/test_phase25_satisfying_parser_ast.py": {
            "test_table_satisfying_after_select_preserves_predicate_ast",
            "test_query_satisfying_after_select_preserves_predicate_ast",
            "test_satisfying_parses_before_order_by_and_limit",
            "test_invalid_satisfying_shapes_are_parser_errors",
            "test_satisfying_ast_does_not_expose_antlr_nodes",
        },
        "tests/test_phase25_satisfying_semantics.py": {
            "test_grouped_satisfying_over_aggregate_alias_is_accepted",
            "test_grouped_satisfying_over_group_key_alias_is_accepted",
            "test_no_group_satisfying_is_rejected",
            "test_unknown_select_output_name_in_satisfying_is_rejected",
            "test_input_field_reference_in_satisfying_must_use_select_output",
            "test_computed_projection_output_in_satisfying_is_deferred",
            "test_aggregate_calls_inside_satisfying_use_invalid_context_diagnostic",
            "test_satisfying_resolves_aggregate_expression_projection_alias",
            "test_unsupported_satisfying_expression_forms_are_deferred",
            "test_non_bool_satisfying_predicate_reuses_predicate_diagnostic",
            "test_invalid_and_or_operands_reuse_operator_diagnostic",
            "test_emit_sql_text_invalid_satisfying_fails_before_ir_and_sql",
            "test_emit_sql_json_invalid_satisfying_fails_without_artifacts",
        },
        "tests/test_phase25_satisfying_ir.py": {
            "test_result_predicate_ir_is_frozen_and_frontend_independent",
            "test_relation_ir_result_predicate_defaults_to_none_for_existing_builds",
            "test_satisfying_source_lowers_aggregate_alias_result_predicate",
            "test_satisfying_source_lowers_group_key_alias_result_predicate",
            "test_emit_sql_text_invalid_satisfying_still_fails_before_ir_and_sql",
            "test_emit_sql_json_invalid_satisfying_still_fails_without_artifacts",
        },
        "tests/test_phase25_satisfying_sql.py": {
            "test_constructed_aggregate_result_predicate_renders_having",
            "test_constructed_group_key_result_predicate_renders_underlying_field_not_alias",
            "test_constructed_result_predicate_having_is_after_group_by_and_before_limit",
            "test_source_satisfying_text_emit_sql_succeeds_with_having",
            "test_source_satisfying_having_uses_underlying_expressions_not_aliases",
            "test_source_satisfying_json_emit_sql_preserves_v1_shape",
            "test_source_satisfying_text_output_writes_having_sql",
            "test_source_satisfying_json_output_writes_having_sql",
            "test_invalid_source_satisfying_still_fails_before_text_sql",
            "test_invalid_source_satisfying_json_output_does_not_replace_file",
            "test_private_mysql_source_pipeline_renders_satisfying_having",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_alias_normalization_and_result_predicate_lowering_are_covered() -> None:
    model = _read(REPO_ROOT / "src/pietto/semantic/model.py")
    satisfying = _read(REPO_ROOT / "src/pietto/semantic/satisfying.py")
    builder = _read(REPO_ROOT / "src/pietto/ir/builder.py")
    ir_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_ir.py")
    sql_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_sql.py")

    for required in (
        "class SatisfyingResultPredicateInfo",
        "output_expressions: Mapping[str, Expression]",
        "expression_value_types: Mapping[Expression, ValueType]",
    ):
        assert required in model

    assert "output.expression" in satisfying
    assert "result_predicate=result_predicate" in builder
    assert "def _lower_result_predicate(" in builder
    assert "predicate_info.output_expressions.get(expression.name)" in builder

    for required in (
        "test_satisfying_source_lowers_aggregate_alias_result_predicate",
        'assert left.function == "sum"',
        'assert argument.name == "amount"',
        "test_satisfying_source_lowers_group_key_alias_result_predicate",
        'assert left.name == "region"',
        'assert left.name != "r"',
    ):
        assert required in ir_tests

    for required in (
        "test_source_satisfying_having_uses_underlying_expressions_not_aliases",
        """assert 'SUM("amount") > 1000' in having""",
        """assert '"total_amount"' not in having""",
        """assert '"r"' not in having""",
    ):
        assert required in sql_tests


def test_json_v1_and_output_success_error_preservation_are_covered() -> None:
    sql_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_sql.py")
    cli_json_tests = _read(REPO_ROOT / "tests/test_cli_emit_sql_json.py")
    cli_output_tests = _read(REPO_ROOT / "tests/test_cli_emit_sql_json_output.py")

    for required in (
        "test_source_satisfying_json_emit_sql_preserves_v1_shape",
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
        "test_source_satisfying_text_output_writes_having_sql",
        "test_source_satisfying_json_output_writes_having_sql",
        'assert result["output"] == {"path": str(output), "written": True}',
        "test_invalid_source_satisfying_json_output_does_not_replace_file",
        'assert result["output"] == {"path": str(output), "written": False}',
        'assert result["artifacts"] == []',
        'assert output.read_text(encoding="utf-8") == "old SQL\\n"',
    ):
        assert required in sql_tests

    assert "test_emit_sql_json_valid_file_returns_one_document" in cli_json_tests
    assert "test_emit_sql_json_output_success_writes_raw_sql_and_keeps_artifacts" in (
        cli_output_tests
    )


def test_fixture_golden_inventory_and_validation_scripts_remain_unchanged() -> None:
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
    assert not any("phase25" in fixture for fixture in sql_fixtures | json_fixtures)
    assert not any(
        "phase25" in input_path
        for inputs in fixture_inputs.values()
        for input_path in inputs
    )
    assert not (REPO_ROOT / "tests/fixtures/phase25").exists()
    assert audit(REPO_ROOT) == ()

    validation_plan = _read(PLAN_PATH)
    assert "uv run python scripts/check_generated.py" in validation_plan
    assert "uv run python scripts/check_goldens.py" in validation_plan


def test_public_api_runtime_project_and_relationship_boundaries_remain_deferred() -> (
    None
):
    plan = _normalized(PLAN_PATH)
    public_sql_api = _read(REPO_ROOT / "src/pietto/sql/__init__.py")
    phase25_sql_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_sql.py")

    for required in (
        "public MySQL API expansion",
        "runtime/database execution",
        "connector execution",
        "schema introspection",
        "project or multi-file implementation",
        "JOIN or relationship traversal",
        "JSON schema changes",
        "CLI option changes",
        "dependency, package, CI, runtime/database, project/multi-file, public MySQL API, or relationship/JOIN behavior",
    ):
        assert required in plan

    assert "emit_mysql_sql" not in public_sql_api
    assert '"--dialect", "mysql"' not in phase25_sql_tests
    assert "from pietto.sql.mysql import emit_mysql_sql" in phase25_sql_tests
    assert "test_private_mysql_source_pipeline_renders_satisfying_having" in (
        phase25_sql_tests
    )


def test_slice7_boundary_surfaces_remain_phase25_locked() -> None:
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
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
    }


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase25_completion_check_goldens",
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
