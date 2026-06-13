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
OTHER_BOUNDARY_HASHES = {
    "grammar/Pietto.g4": (
        "6a5f6bc45d4f66011a7898fe783b6600beaf73f3b984d6539f975cf0cd7f3110"
    ),
    "src/pietto/generated/Pietto.interp": (
        "49ad078721e71d07656487a5e490e1ebedea2d3a6c84b09be7605f3f4eb86118"
    ),
    "src/pietto/generated/Pietto.tokens": (
        "11f91d90681a86473edff1a2f5fb2d48f9404885c75640fdc2f44d81897e74c0"
    ),
    "src/pietto/generated/PiettoLexer.interp": (
        "802178225bebaa8f1e54721a1f4c70b44ca396b961f65d6c748df07be38e6461"
    ),
    "src/pietto/generated/PiettoLexer.py": (
        "a746193cc401cf6c024f6b4da8d1c0d4e977bc39099dab8e04d72c1cf7840dbb"
    ),
    "src/pietto/generated/PiettoLexer.tokens": (
        "b3eee41e95d95c729964916440568412aaddfcfe7779c32bc96958151ae3ff65"
    ),
    "src/pietto/generated/PiettoParser.py": (
        "d3392753fe2110d20e6b41618a9bd8a1e6f571eb217f98ec4fb7decb60520888"
    ),
    "src/pietto/generated/PiettoVisitor.py": (
        "b99732e2583e7c7f178baceca965fa6716a7be122a7c132d09dc96bd6b41bb2d"
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
