from __future__ import annotations

import hashlib
import inspect
import tomllib
from pathlib import Path

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ir import ScriptIR
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"
POSTGRES_BOUNDARY_HASHES = {
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "src/pietto/sql/expressions.py": (
        "9e44f56c4fd50f8cdaa6718fed4d30cb60b56737d614cb295b7597d4c6a5f921"
    ),
    "src/pietto/sql/model.py": (
        "0b5f096fbd9b2fdcc0c92cf65e50de90d64b134fd7479a3314ee05c348ab69f1"
    ),
    "src/pietto/sql/postgres.py": (
        "9b89550ddaf1759e8066d02590288f545eace484e4633f6f6e37b1fa8c194790"
    ),
    "src/pietto/sql/relations.py": (
        "95ff28e44cbb8a5cc00909a6712fcbe6ce363614621f09b911be6fdb9194b40e"
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
OTHER_BOUNDARY_HASHES = {
    "grammar/Pietto.g4": (
        "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
    ),
    "src/pietto/generated/Pietto.interp": (
        "e9f4effe612f93db3405d8de970ccbd00481c166a922544770c9839098710561"
    ),
    "src/pietto/generated/Pietto.tokens": (
        "b98fea02838695f59ccd3cbe33cd04a41f7b7f7abe66a0c6f4e958ba63d295ec"
    ),
    "src/pietto/generated/PiettoLexer.interp": (
        "8f52b5a20d3b303b1e82d32c977f150a9c0e436b4cdd4b51a362704aa398419c"
    ),
    "src/pietto/generated/PiettoLexer.py": (
        "481ef07000d7714d6f232ef8ce2ae1d5eae4be2fa66f3739ffdb487e9a6caee4"
    ),
    "src/pietto/generated/PiettoLexer.tokens": (
        "cac5befec4fac035ae59232c724c23b49e13a9b1f170e1b7a576e96dc5fa88e5"
    ),
    "src/pietto/generated/PiettoParser.py": (
        "4f2881dc9c2c930699af9e7cf227ab972e3e75b0b23eae9a004d45ea4cf51c02"
    ),
    "src/pietto/generated/PiettoVisitor.py": (
        "75b5b4f26d806f3f8d748d43c36aecc226cb143f6cdd2da71d5bbd02df2f5398"
    ),
    "src/pietto/generated/__init__.py": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
}


def test_slice4_status_and_private_boundary_are_documented() -> None:
    plan = _read(PHASE10_PLAN)
    status_documents = (
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    assert "**Slice 4: MySQL Backend Skeleton is complete.**" in plan
    assert "4. **MySQL Backend Skeleton**: complete." in plan
    for document in status_documents:
        normalized = " ".join(document.split())
        assert "Phase 10 MySQL SQL Generation MVP is complete" in normalized
        assert "private MySQL backend skeleton" in normalized


def test_mysql_entry_point_is_private_and_keeps_existing_models() -> None:
    signature = inspect.signature(emit_mysql_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert emit_mysql_sql(ScriptIR(definitions=())) == SqlResult((), ())
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")


def test_mysql_skeleton_remains_private_after_cli_dispatch() -> None:
    cli_source = _read("src/pietto/cli.py")
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )

    assert "import pietto.sql.mysql as mysql_backend" in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "mysql.table" in runtime_source
    assert "def emit_sql(" not in runtime_source
    assert "def _select_sql_emitter(" in runtime_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_mysql_skeleton_has_no_dependency_or_forbidden_stage_imports() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    mysql_source = _read("src/pietto/sql/mysql.py").lower()

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.cli",
        "pietto.cli_json",
        "pathlib",
        "open(",
        "sqlglot",
    ):
        assert forbidden not in mysql_source


def test_postgres_grammar_and_lock_boundaries_are_unchanged() -> None:
    for path, expected_hash in {
        **POSTGRES_BOUNDARY_HASHES,
        **OTHER_BOUNDARY_HASHES,
    }.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
