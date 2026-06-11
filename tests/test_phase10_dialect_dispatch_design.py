from __future__ import annotations

import hashlib
import inspect
import tomllib
from pathlib import Path

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"
DISPATCH_DESIGN = "docs/spec/sql-dialect-dispatch-design-v1.md"
POSTGRES_GOLDEN_HASHES = {
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
BOUNDARY_HASHES = {
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "grammar/Pietto.g4": (
        "af3e312593182f37e9d434677b4018a2aa3690cd337a51ef0b7b4f4c9d822caf"
    ),
    "src/pietto/generated/Pietto.interp": (
        "04840d6213b7bbe763ba67c07fb159c6a15daca122283c12895ae8513940301b"
    ),
    "src/pietto/generated/Pietto.tokens": (
        "1079e3c49ebc819eb5ccc0bb1fa6e06624258473709d20bd832fc6620e2a74f5"
    ),
    "src/pietto/generated/PiettoLexer.interp": (
        "af47cde1114e7a6c030c05fc3773c30f5368d5dbebd177f848cc46c750f52eb1"
    ),
    "src/pietto/generated/PiettoLexer.py": (
        "273563855368ae0d6f162327eec09458879d2494ca48d00ae0ac240d50f2610b"
    ),
    "src/pietto/generated/PiettoLexer.tokens": (
        "a917e2ba64b246f98a8594f2371e024243ffbf259708fe4b8d62aa905222a0e3"
    ),
    "src/pietto/generated/PiettoParser.py": (
        "8c4e32dd8efc9493c7aa081882ac1df2fbd41c0ff0aafe30c38be3e5a33e565c"
    ),
    "src/pietto/generated/PiettoVisitor.py": (
        "9d6e68a95196063bb37d3cd4b07c3b22393351a8f1b60653125b0c2d86b12452"
    ),
    "src/pietto/generated/__init__.py": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
}


def test_slice3_status_and_cross_references_are_complete() -> None:
    plan = _read(PHASE10_PLAN)
    design = _read(DISPATCH_DESIGN)
    status_documents = (
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    _assert_contains_all(
        plan,
        (
            "**Slice 3: Dialect Dispatch Design is complete.**",
            "3. **Dialect Dispatch Design**: complete.",
            DISPATCH_DESIGN,
        ),
    )
    _assert_contains_all(
        design,
        (
            "**Phase 10 Slice 3 is complete.**",
            "**Phase 10 Slice 8 implements this design.**",
        ),
    )
    for document in status_documents:
        assert DISPATCH_DESIGN in document


def test_private_closed_mapping_and_enablement_gate_are_explicit() -> None:
    design = _read(DISPATCH_DESIGN)

    _assert_contains_all(
        design,
        (
            "postgres -> emit_postgres_sql",
            "mysql    -> emit_mysql_sql",
            "type _SqlEmitter = Callable[[ScriptIR], SqlResult]",
            "def _select_sql_emitter(dialect: str) -> _SqlEmitter | None:",
            "return sql_api.emit_postgres_sql",
            "return mysql_backend.emit_mysql_sql",
            "resolve emitter attributes when called",
            '_ENABLED_SQL_DIALECTS = ("postgres",)',
            '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")',
            "Backend availability does not imply CLI enablement.",
            "Text argparse choices and JSON dialect admission must derive from "
            "the same enabled set.",
            "Slice 8",
        ),
    )


def test_dispatch_stage_and_presentation_ownership_are_explicit() -> None:
    design = _read(DISPATCH_DESIGN)

    _assert_contains_all(
        design,
        (
            "Dialect validation and emitter selection occur before source reading "
            "and parsing.",
            "sql_result = selected_emitter(script_ir)",
            "The selected emitter is called once",
            "the dialect name",
            "source text, parser AST, or semantic model",
            "input or output paths",
            "text or JSON format",
            "stdout or stderr handles",
            "an argparse namespace",
            "CLI orchestration owns parsing, semantic analysis, IR construction",
            "backends never print, serialize JSON, or write files",
            "`SqlResult` does not gain a dialect field",
            "`SqlArtifact` does not gain a dialect field",
        ),
    )


def test_unknown_dialect_and_backend_failure_remain_distinct() -> None:
    design = _read(DISPATCH_DESIGN)

    _assert_contains_all(
        design,
        (
            "Unknown or disabled text dialect",
            "invalid choice",
            "Unknown or disabled JSON dialect",
            "`unsupported_dialect`",
            "exit code `2`",
            "Selected backend capability failure",
            "`PIE-B1000`",
            "exit code `1`",
            "An unknown or disabled dialect is not a compiler diagnostic",
            "successful artifacts returned alongside backend diagnostics",
            "output file remains unwritten when backend errors are present",
        ),
    )


def test_no_header_connector_dynamic_or_public_generic_dispatch_is_allowed() -> None:
    design = _read(DISPATCH_DESIGN)

    _assert_contains_all(
        design,
        (
            "The explicit CLI dialect is authoritative for backend selection.",
            "`dialect postgres` or `dialect mysql` source headers",
            "`postgres.table` or `mysql.table` connector names",
            "Header/CLI mismatch validation is deferred",
            "a connector/backend mismatch is diagnosed by the already selected backend",
            "emit_sql(script_ir, dialect)",
            "compile_to_sql(...)",
            "No public dialect enum, registry, backend object",
            "`importlib` or user-controlled module names",
            "package entry points or plugin discovery",
            "`eval` or `exec`",
            "fallback to a generic SQL dialect",
        ),
    )


def test_slice8_implements_private_dispatch_without_public_api() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    ).lower()
    cli_source = _read("src/pietto/cli.py")
    signature = inspect.signature(sql_api.emit_postgres_sql)

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "def emit_sql(",
        "sqlglot",
        "schema_version = 2",
        '"schema_version": 2',
    ):
        assert forbidden not in runtime_source
    assert "mysql.table" in runtime_source
    assert "def emit_mysql_sql(" in runtime_source
    assert "def _select_sql_emitter(" in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"


def test_postgres_grammar_generated_and_lock_boundaries_are_unchanged() -> None:
    for path, expected_hash in {
        **POSTGRES_GOLDEN_HASHES,
        **BOUNDARY_HASHES,
    }.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized
