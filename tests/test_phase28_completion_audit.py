from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-28-numeric-aggregate-refinement-ii.md"
SPEC_PATH = REPO_ROOT / "docs/spec/numeric-literal-aggregate-arguments-v1.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE28_ARTIFACTS = (
    "docs/plan/phase-28-numeric-aggregate-refinement-ii.md",
    "docs/spec/numeric-literal-aggregate-arguments-v1.md",
    "tests/test_phase28_numeric_literal_aggregate_candidate_decision.py",
    "tests/test_phase28_numeric_literal_aggregate_semantics.py",
    "tests/test_phase28_numeric_literal_aggregate_ir.py",
    "tests/test_phase28_numeric_literal_aggregate_sql.py",
    "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py",
    "tests/test_phase28_completion_audit.py",
)

LOCKED_BOUNDARY_SURFACES = {
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "3e8ba493278a9730a9c13bc5a0ddcea707e543c97b5e3521d2ef049c576553ed",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4",
    ),
    "ast_nodes": (
        "src/pietto/ast_nodes.py",
        1,
        "6f25584047be299eae290bc9640e903392c9882c70947a2e5f50a205b5a81368",
    ),
    "ast_builder": (
        "src/pietto/ast_builder.py",
        1,
        "886150f1a6b13fdb883d8863abe63d0778dd1c6b1dd9166afd532d1f5b574502",
    ),
    "parser_api": (
        "src/pietto/parser_api.py",
        1,
        "537178041b413d964bda00aef376f90d745a64d61378ede2dbc6a715b49e7f3f",
    ),
    "semantic": (
        "src/pietto/semantic",
        31,
        "fb593d3b8c2c0be71f84c9eaed46ee9ff5e51728a17bb790cf086b975d39bb99",
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
    "phase28_plan": (
        "docs/plan/phase-28-numeric-aggregate-refinement-ii.md",
        1,
        "0c729311a8eaa910cb97c1966f6dc189a3dca4fe990e621ec73e008d24bce10f",
    ),
    "phase28_spec": (
        "docs/spec/numeric-literal-aggregate-arguments-v1.md",
        1,
        "0454e1ba59d72cae6932b945d8fb460ffdd3e0fd0bf78f983c689cd718047766",
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


def test_phase28_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE28_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    for required in (
        "Phase 28 Numeric / Aggregate Refinement II is complete. Slices 1 "
        "through 6 cover candidate decision and exact contract, semantic "
        "acceptance, IR lowering proof, PostgreSQL/private MySQL SQL "
        "lowering, CLI / JSON / output hardening, and completion "
        "audit/status lock",
        "Status: complete as candidate decision, exact contract, and static "
        "audit work only",
        "Status: complete as semantic acceptance only",
        "Status: complete as tests-only IR lowering proof",
        "Status: complete as PostgreSQL/private MySQL SQL backend lowering only",
        "Status: complete as tests-only CLI / JSON / output hardening",
        "Status: complete as completion audit and status lock work only",
    ):
        assert required in plan
    for required in (
        "Status: Phase 28 is complete for the bounded numeric literal "
        "aggregate argument MVP",
        "The implemented behavior admits only Int and Float numeric literal "
        "leaves inside selected `sum(...)` and `avg(...)` numeric expression "
        "arguments",
        "Accepted expressions must still include at least one direct input field leaf",
        "Phase 28 changes no grammar, generated ANTLR, AST, AST builder, "
        "parser, IR model, CLI implementation, JSON schema or serializer",
    ):
        assert required in spec


def test_phase28_final_status_docs_are_precise_without_broadening_scope() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 28 Numeric / Aggregate Refinement II",
            "complete",
            "bounded numeric literal aggregate argument MVP",
            "Int and Float numeric literal leaves inside selected `sum(...)` "
            "and `avg(...)` numeric expression arguments",
            "Accepted expressions must still include at least one direct "
            "input field leaf",
            "literal-only aggregate arguments such as `sum(1)` and `avg(1)` "
            "remain rejected",
            "existing scalar type inference and aggregate result typing",
            "adds no Decimal literal, Decimal multiplication, Decimal "
            "division, mixed Decimal promotion, casts, precision/scale "
            "modeling, schema introspection, arbitrary scalar calls inside "
            "`sum` / `avg`, division, modulo, `count(expression)`, "
            "`min(expression)`, `max(expression)`, `count_distinct(...)` "
            "widening",
            "SQL fixture/golden, JSON schema, CLI option, dependency, public "
            "API, runtime/project, public MySQL API, or relationship/JOIN "
            "changes",
        ):
            assert required in status_doc
        for forbidden in (
            "Phase 28 implementation has not started",
            "arbitrary scalar calls inside `sum` / `avg` are supported",
            "Decimal literals are supported",
            "Decimal multiplication is supported",
            "count(expression) is supported",
            "public `emit_mysql_sql`",
        ):
            assert forbidden not in status_doc


def test_phase28_focused_coverage_is_locked() -> None:
    expected_functions = {
        "tests/test_phase28_numeric_literal_aggregate_candidate_decision.py": {
            "test_phase28_artifacts_exist_and_record_completion_status",
            "test_candidate_set_and_recommendation_are_locked",
            "test_existing_literal_and_expression_carriers_are_repo_facts",
            "test_current_aggregate_literal_boundary_and_future_target_are_locked",
            "test_result_type_and_scalar_typing_contract_are_locked",
            "test_diagnostics_and_deferred_shapes_remain_explicit",
            "test_six_slice_plan_and_validation_commands_are_locked",
            "test_phase_wide_non_goals_and_slice1_boundaries_are_locked",
            "test_status_docs_record_phase28_completion_without_broadening_scope",
        },
        "tests/test_phase28_numeric_literal_aggregate_semantics.py": {
            "test_sum_avg_numeric_literal_expression_arguments_are_semantically_accepted",
            "test_qualified_field_and_unary_leaves_are_semantically_accepted",
            "test_grouped_numeric_literal_aggregate_arguments_are_semantically_accepted",
            "test_phase26_decimal_field_only_expression_arguments_remain_accepted",
            "test_cli_check_accepts_numeric_literal_aggregate_arguments",
            "test_unsupported_literal_and_expression_shapes_still_use_s2315",
            "test_decimal_literal_multiplication_and_mixed_promotion_remain_deferred",
            "test_existing_primary_aggregate_diagnostics_remain_primary",
        },
        "tests/test_phase28_numeric_literal_aggregate_ir.py": {
            "test_numeric_literal_aggregate_arguments_lower_to_existing_ir_nodes",
            "test_qualified_field_and_unary_leaves_lower_inside_aggregate_arguments",
            "test_grouped_numeric_literal_aggregates_lower_with_group_keys",
            "test_direct_lower_expr_for_numeric_literal_aggregate_uses_aggregate_call_ir",
            "test_phase26_field_only_expression_aggregate_arguments_still_lower",
            "test_unsupported_numeric_literal_aggregate_shapes_remain_before_ir",
        },
        "tests/test_phase28_numeric_literal_aggregate_sql.py": {
            "test_direct_renderers_render_numeric_literal_aggregate_arguments",
            "test_direct_renderers_render_qualified_and_unary_literal_aggregate_arguments",
            "test_backends_emit_no_group_numeric_literal_aggregate_sql",
            "test_grouped_satisfying_order_by_and_limit_render_numeric_literal_aggregates",
            "test_phase26_field_only_expression_aggregate_sql_remains_supported",
            "test_unsupported_source_shapes_stop_before_sql_with_semantic_diagnostics",
            "test_malformed_hand_built_numeric_literal_aggregate_ir_fails_closed",
            "test_private_mysql_api_remains_unexported",
        },
        "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py": {
            "test_check_accepts_numeric_literal_aggregate_arguments",
            "test_text_emit_sql_carries_numeric_literal_aggregate_sql",
            "test_json_emit_sql_preserves_v1_shape_for_numeric_literal_aggregates",
            "test_text_output_writes_numeric_literal_aggregate_sql_on_success",
            "test_json_output_writes_numeric_literal_aggregate_sql_and_keeps_artifacts",
            "test_invalid_numeric_literal_aggregate_text_fails_before_sql",
            "test_invalid_numeric_literal_aggregate_json_fails_without_artifacts",
            "test_invalid_numeric_literal_aggregate_json_output_does_not_replace_file",
            "test_public_mysql_api_remains_private",
        },
    }

    for relative_path, functions in expected_functions.items():
        assert functions <= _function_names(REPO_ROOT / relative_path)


def test_phase28_accepted_semantic_ir_and_sql_scope_is_locked() -> None:
    spec = _normalized(SPEC_PATH)
    semantics_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
    )
    ir_tests = _read(REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_ir.py")
    sql_tests = _read(REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_sql.py")
    cli_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py"
    )

    for required in (
        "Phase 28 supports only Int and Float numeric literal leaves inside "
        "`sum(...)` and `avg(...)` numeric expression arguments",
        "the aggregate function is `sum` or `avg`",
        "the argument expression contains at least one direct input field leaf",
        "literal leaves are only Int or Float scalar literals",
        "allowed operators remain unary `+` and `-`, and binary `+`, `-`, and `*`",
        "the complete argument expression has an existing scalar numeric type "
        "of `Int` or `Float`",
    ):
        assert required in spec

    for required in (
        "value = sum(amount + 1)",
        "value = sum(1 + amount)",
        "value = sum(amount - 1)",
        "value = sum(amount * 2)",
        "value = avg(score * 2)",
        "value = avg(score + 1.5)",
    ):
        assert required in semantics_tests
    for required in (
        "total = sum(amount + 1)",
        "total = sum(1 + amount)",
        "total = sum(amount - 1)",
        "total = sum(amount * 2)",
        "average = avg(score * 2)",
        "average = avg(score + 1.5)",
    ):
        assert required in sql_tests
    for required in (
        "plus_total = sum(amount + 1)",
        "left_literal_total = sum(1 + amount)",
        "minus_total = sum(amount - 1)",
        "multiplied_total = sum(amount * 2)",
        "weighted_average = avg(score * 2)",
        "adjusted_average = avg(score + 1.5)",
    ):
        assert required in ir_tests

    for required in (
        "LiteralIR",
        "BinaryIR",
        "UnaryIR",
        "FieldRefIR",
        "AggregateCallIR",
    ):
        assert required in ir_tests
    for required in (
        'SUM(("amount" + 1))',
        'AVG(("score" * 2))',
        "SUM((`amount` + 1))",
        "AVG((`score` * 2))",
        "GROUP BY",
        "HAVING",
        "ORDER BY",
    ):
        assert required in sql_tests
        assert required in cli_tests


def test_phase28_diagnostics_and_unsupported_boundaries_are_locked() -> None:
    diagnostics = _read(DIAGNOSTICS_PATH)
    spec = _normalized(SPEC_PATH)
    semantics_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
    )
    ir_tests = _read(REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_ir.py")
    sql_tests = _read(REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_sql.py")
    cli_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py"
    )

    assert "| `PIE-S2315` | Aggregate expression argument is deferred |" in diagnostics
    assert "No new diagnostic code is reserved by this contract" in spec
    for required in (
        "literal-only aggregate arguments such as `sum(1)` and `avg(1)`",
        "division inside aggregate arguments",
        "modulo inside aggregate arguments",
        "arbitrary scalar calls inside `sum` or `avg`",
        "`count(expression)`",
        "`min(expression)`",
        "`max(expression)`",
        "unsupported `count_distinct(...)` expression expansion",
        "Phase 28 must not force `PIE-S2315` to replace more specific scalar "
        "operand or aggregate diagnostics",
    ):
        assert required in spec
    for required in (
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(1 + 2)",
        "value = avg(1.5 * 2)",
        "value = sum(amount / tax)",
        "value = sum(amount % tax)",
        "value = sum(amount + len(status))",
        "value = count(1)",
        "value = min(amount + 1)",
        "value = max(score * 2)",
        "value = count_distinct(len(status))",
        "value = sum(price + 1)",
        "value = sum(price * discount)",
        "PIE-S2315",
    ):
        assert required in semantics_tests
        assert required in sql_tests
    assert "test_unsupported_numeric_literal_aggregate_shapes_remain_before_ir" in (
        ir_tests
    )
    assert "semantic errors must stop before IR and SQL" in cli_tests


def test_phase28_decimal_json_cli_and_public_api_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    semantics_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
    )
    sql_tests = _read(REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_sql.py")
    cli_tests = _read(
        REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py"
    )

    for required in (
        "accepted Phase 26 Decimal field-only expression arguments such as "
        "`sum(price + discount)` remain valid",
        "Phase 28 does not add Decimal literal leaves or mixed Decimal promotion",
        "Decimal literal syntax or Decimal literal aggregate arguments",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal/Int or Decimal/Float promotion",
        "casts or schema introspection",
    ):
        assert required in spec
    for required in (
        "test_phase26_decimal_field_only_expression_arguments_remain_accepted",
        "test_decimal_literal_multiplication_and_mixed_promotion_remain_deferred",
        "price + discount",
        "price * discount",
        "price + 1",
    ):
        assert required in semantics_tests
    assert "test_phase26_field_only_expression_aggregate_sql_remains_supported" in (
        sql_tests
    )

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
        "test_invalid_numeric_literal_aggregate_json_output_does_not_replace_file",
        "test_public_mysql_api_remains_private",
    ):
        assert required in cli_tests


def test_fixture_golden_inventory_and_validation_scripts_remain_unchanged() -> None:
    check_goldens = _check_goldens_module()

    assert len(check_goldens.SQL_FIXTURES) == 32
    assert len(check_goldens.JSON_FIXTURES) == 5
    assert len(check_goldens.CLASSIFIED_FIXTURES) == 37
    assert check_goldens.audit(REPO_ROOT) == ()
    assert not any(
        "phase28" in fixture for fixture in check_goldens.CLASSIFIED_FIXTURES
    )
    assert not (REPO_ROOT / "tests/fixtures/phase28").exists()

    plan = _normalized(PLAN_PATH)
    for required in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert required in plan


def test_boundary_surfaces_remain_phase28_locked() -> None:
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
