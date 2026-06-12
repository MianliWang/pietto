from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_module
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
MYSQL_CASES = (
    (
        "tests/fixtures/mysql/compatibility_literals_identifiers.pietto",
        "emit_mysql_compatibility_literals_identifiers.sql",
        ("LiteralCompatibility",),
    ),
    (
        "tests/fixtures/mysql/compatibility_expressions.pietto",
        "emit_mysql_compatibility_expressions.sql",
        ("expression_compatibility",),
    ),
    (
        "tests/fixtures/mysql/compatibility_ordering_metadata.pietto",
        "emit_mysql_compatibility_ordering_metadata.sql",
        ("FirstRelation", "SecondRelation"),
    ),
)
MYSQL_FIXTURE_LOCKS = {
    "tests/fixtures/mysql/compatibility_literals_identifiers.pietto": (
        "9b94b5f0c541f3fd4f0fe25dae09210c8c31d0215fb80bca756f3f0ff021887e"
    ),
    "tests/fixtures/mysql/compatibility_expressions.pietto": (
        "ae69c57ed172abf27c1a6933667e536f3dd81a831054dbf61676e117444c3c3f"
    ),
    "tests/fixtures/mysql/compatibility_ordering_metadata.pietto": (
        "dc95878f340321cc2b0d5b08f9aad4d6cfd5404c0aaca65436a029567661b215"
    ),
    "tests/fixtures/mysql/compatibility_failures.pietto": (
        "3545df9dafa09a45c21b741c75b918bdbc9c193a61fe6b04197928f616e9e6d4"
    ),
    "tests/fixtures/golden/emit_mysql_compatibility_literals_identifiers.sql": (
        "51dbe0b2aab74214b4948f5db3320dc48c7935b96d080248c815b3942d63a5c7"
    ),
    "tests/fixtures/golden/emit_mysql_compatibility_expressions.sql": (
        "bbfaebf5b14fd21528a2081a4f73d34fde989a6199ce296b527d2cf035cc11f5"
    ),
    "tests/fixtures/golden/emit_mysql_compatibility_ordering_metadata.sql": (
        "d3f9d327725f9f37ac931a48d80a69462ddd99a193cf8b868833d1350302bbab"
    ),
}
POSTGRES_CASES = (
    (
        "examples/tables/active_users.pietto",
        "emit_sql_active_users.sql",
    ),
    (
        "examples/queries/active_user_emails.pietto",
        "emit_sql_active_user_emails.sql",
    ),
    (
        "tests/fixtures/postgres/compatibility_literals_identifiers.pietto",
        "emit_sql_compatibility_literals_identifiers.sql",
    ),
    (
        "tests/fixtures/postgres/compatibility_expressions.pietto",
        "emit_sql_compatibility_expressions.sql",
    ),
    (
        "tests/fixtures/postgres/compatibility_ordering_metadata.pietto",
        "emit_sql_compatibility_ordering_metadata.sql",
    ),
)
POSTGRES_LOCKS = {
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "src/pietto/sql/expressions.py": (
        "ee2ca2c7d436f815504133eace7a72935a41db33fcead193147836935311fee0"
    ),
    "src/pietto/sql/model.py": (
        "0b5f096fbd9b2fdcc0c92cf65e50de90d64b134fd7479a3314ee05c348ab69f1"
    ),
    "src/pietto/sql/postgres.py": (
        "9b89550ddaf1759e8066d02590288f545eace484e4633f6f6e37b1fa8c194790"
    ),
    "src/pietto/sql/relations.py": (
        "28f5844d8d0037d5dcb96a49bd1dfa3068945a7bd7b9e65fbbd8bd539015356e"
    ),
    "src/pietto/sql/render.py": (
        "199a8c019331d2dc0d4112bca449268c34d9ba5688c976dd4194b8502c5daed5"
    ),
    "tests/fixtures/golden/emit_sql_active_users.sql": (
        "5a0878c84b208c906d8affe0f54706118f14bee40951ab8e25c70c90e95f43d3"
    ),
    "tests/fixtures/golden/emit_sql_active_user_emails.sql": (
        "d5aaf1e4cc3c334c72c3978858358b4df21ea3572daa0ecdda0fee0ceff74ee0"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_literals_identifiers.sql": (
        "691b04423af4cb4861d5aa56c0ae865181a738abca153f37ae7c69c1a8857477"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_expressions.sql": (
        "943f92d70fd433d803cf5409b02254f9f7801822270eb5ca567d6cdde9387c46"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_ordering_metadata.sql": (
        "b4e2d6a0bfa3ddff91b75892ddc071ec9199d41512e826a2ad81bac76e23752c"
    ),
}


def test_slice7_status_and_cross_references_are_complete() -> None:
    plan = _read("docs/plan/phase-10-mysql-sql-generation-mvp.md")
    status_documents = (
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    assert (
        "**Slice 7: MySQL Golden Corpus And PostgreSQL Regression Lock is complete.**"
        in plan
    )
    assert (
        "7. **MySQL Golden Corpus And PostgreSQL Regression Lock**: complete." in plan
    )
    for document in status_documents:
        normalized = " ".join(document.split())
        assert "Phase 10 MySQL SQL Generation MVP is complete" in normalized
        assert "MySQL golden" in normalized


@pytest.mark.parametrize(
    ("source_path", "golden_name", "artifact_names"),
    MYSQL_CASES,
)
def test_private_mysql_output_matches_byte_exact_golden(
    source_path: str,
    golden_name: str,
    artifact_names: tuple[str, ...],
) -> None:
    result = emit_mysql_sql(_compile(source_path))

    assert tuple(artifact.name for artifact in result.artifacts) == artifact_names
    assert result.diagnostics == ()
    assert _render_artifacts(result) == (GOLDEN_ROOT / golden_name).read_bytes()


def test_mysql_inputs_and_reviewed_golden_bytes_are_locked() -> None:
    for path, expected_hash in MYSQL_FIXTURE_LOCKS.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


@pytest.mark.parametrize(("source_path", "golden_name"), POSTGRES_CASES)
def test_postgres_output_still_matches_every_existing_sql_golden(
    source_path: str,
    golden_name: str,
) -> None:
    result = emit_postgres_sql(_compile(source_path))

    assert result.diagnostics == ()
    assert _render_artifacts(result) == (GOLDEN_ROOT / golden_name).read_bytes()


def test_postgres_public_backend_and_existing_golden_bytes_are_locked() -> None:
    signature = inspect.signature(sql_api.emit_postgres_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    for path, expected_hash in POSTGRES_LOCKS.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def test_mysql_failures_preserve_artifact_and_diagnostic_order() -> None:
    result = emit_mysql_sql(
        _compile(
            "tests/fixtures/mysql/compatibility_failures.pietto",
        )
    )

    assert [artifact.name for artifact in result.artifacts] == [
        "first_ok",
        "second_ok",
    ]
    assert [
        diagnostic.message.split(": ", maxsplit=1)[1].split(".", maxsplit=1)[0]
        for diagnostic in result.diagnostics
    ] == [
        "first_bad",
        "second_bad",
    ]
    assert all(diagnostic.code == "PIE-B1000" for diagnostic in result.diagnostics)


def test_slice7_keeps_mysql_private_after_cli_enablement() -> None:
    cli_source = _read("src/pietto/cli.py")

    assert not hasattr(sql_api, "emit_mysql_sql")
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_mysql_json_v1_success_fixture_is_added_by_slice8() -> None:
    plan = _read("docs/plan/phase-10-mysql-sql-generation-mvp.md")
    contract = _read("docs/spec/mysql-sql-generation-mvp-v1.md")

    assert '"dialect": "mysql"' in plan
    assert "actual JSON fixture is implemented in Slice 8" in plan
    assert "Slice 8 implements that fixture" in contract
    assert tuple(GOLDEN_ROOT.glob("emit_mysql_*.json")) == (
        GOLDEN_ROOT / "emit_mysql_compatibility_ordering_metadata.json",
    )


def test_negative_mysql_regression_matrix_remains_executable() -> None:
    relation_tests = _read("tests/test_sql_mysql_relations.py")
    expression_tests = _read("tests/test_sql_mysql_expressions.py")
    rendering_tests = _read("tests/test_sql_mysql_rendering.py")
    backend_source = inspect.getsource(mysql_module.emit_mysql_sql)

    for required in (
        "test_unsupported_or_invalid_connectors_emit_no_partial_artifact",
        "test_matches_relation_fails_closed_without_approximation",
        "test_invalid_projection_expression_emits_no_partial_artifact",
        "test_invalid_literal_emits_no_partial_artifact",
        "test_invalid_field_identifier_emits_no_partial_artifact",
        "test_unexpected_renderer_errors_remain_visible",
        'operator="like"',
    ):
        assert required in relation_tests
    assert "test_unsupported_expressions_fail_closed" in expression_tests
    assert "test_render_literal_rejects_invalid_text" in rendering_tests
    assert "except MySqlRenderError as error:" in backend_source
    assert "except (TypeError, ValueError)" not in backend_source
    assert "except Exception" not in backend_source


def _compile(path: str) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
