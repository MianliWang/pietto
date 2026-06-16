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
        "565405ba3cc630232de28e650820d11956be26751942f4ef14a4990f457ee02f"
    ),
    "src/pietto/sql/model.py": (
        "0b5f096fbd9b2fdcc0c92cf65e50de90d64b134fd7479a3314ee05c348ab69f1"
    ),
    "src/pietto/sql/postgres.py": (
        "9b89550ddaf1759e8066d02590288f545eace484e4633f6f6e37b1fa8c194790"
    ),
    "src/pietto/sql/relations.py": (
        "a908cb22f3ce040934bf54f234c90d90991d93fef4086f3f3292951acbbb0da1"
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
        "aa9b7fe9e35ff64269fa64e8db9555897f6c16f70f293b6cb4a071a1ef25e7c1"
    ),
    "src/pietto/generated/Pietto.interp": (
        "3f0d7472e366071120cd14431336aa7c26db2eed9e1e2d7be41df2aaf4035999"
    ),
    "src/pietto/generated/Pietto.tokens": (
        "bc621eb50242bf6c3b23da6cc73f1171aca16442383edca1a5d0ef039637c4ad"
    ),
    "src/pietto/generated/PiettoLexer.interp": (
        "719af5c5469518fcb22461c8e7789f4c8c99a7da88a07aa2eda6d9715214977e"
    ),
    "src/pietto/generated/PiettoLexer.py": (
        "b9a226c18a974076ae3929bc3832dccfa52a8c63964e33567b19358f6a7aabb8"
    ),
    "src/pietto/generated/PiettoLexer.tokens": (
        "39240e2441252c6b7ff7682d5c51bb7b0609927e8f2496779eefa6945dafd2ee"
    ),
    "src/pietto/generated/PiettoParser.py": (
        "1245ceb6e9e7d54f098049b08d33faa4af556709beff5f1035319822185e96f5"
    ),
    "src/pietto/generated/PiettoVisitor.py": (
        "5e4920985dd60837ec4e62b6df58eb2c630e9eddec03338d972a5dd75885ff6d"
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
