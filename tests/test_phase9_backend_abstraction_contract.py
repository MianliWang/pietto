from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE9_PLAN = "docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md"
BACKEND_CONTRACT = "docs/spec/sql-backend-abstraction-contract-v1.md"


def test_slice5_contract_and_status_documents_are_complete() -> None:
    plan = _read(PHASE9_PLAN)
    contract = _read(BACKEND_CONTRACT)
    agents = _read("AGENTS.md")
    language_spec = _read("docs/spec/pietto-v0.9.md")
    source_contract = _read("docs/spec/sql-dialect-source-contract-v1.md")

    assert "5. **Backend Abstraction Contract**: complete." in plan
    assert "## Slice 5: Backend Abstraction Contract" in plan
    _assert_contains_all(
        contract,
        ("**This contract is planning/specification-only and is not implemented.**",),
    )
    for document in (
        plan,
        agents,
        language_spec,
        source_contract,
    ):
        assert BACKEND_CONTRACT in document


def test_internal_boundary_and_public_api_decisions_are_explicit() -> None:
    contract = _read(BACKEND_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "The internal backend boundary remains `ScriptIR -> SqlResult`.",
            "emit_postgres_sql(script_ir: ScriptIR) -> SqlResult",
            "The abstraction is a behavioral contract",
            "must not require wrapping or rewriting `emit_postgres_sql`",
            "does not accept source text, AST, semantic models, CLI namespaces",
            "does not mutate the input IR",
            "does not rerun parser, semantic, or IR stages",
            "does not perform file or network IO",
        ),
    )


def test_capability_declaration_is_closed_and_complete() -> None:
    contract = _read(BACKEND_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "Every implemented backend must have one immutable, reviewable "
            "declaration.",
            "absent capability = unsupported",
            "### Identity",
            "### Source Connectors",
            "### Definition Kinds",
            "### Expression Nodes",
            "### Functions",
            "### Operators And Predicates",
            "### Identifier Policy",
            "### Literal Policy",
            "### Relation And Artifact Policy",
            "### Diagnostic Policy",
            "Silently omitting an unclassified definition is prohibited.",
            'The declaration must not use a generic "all expressions" marker.',
        ),
    )


def test_validation_result_and_ordering_policies_fail_closed() -> None:
    contract = _read(BACKEND_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "Capability validation must fail closed and precede artifact acceptance.",
            "no artifact is accepted for a definition unless its complete",
            "emit a partial SQL artifact for a failed definition",
            "Processing may continue in definition order",
            "Artifacts and diagnostics may coexist.",
            "text stdout may contain successful artifacts",
            "an output-file request is not written when backend errors exist",
            "Backends must not alphabetize, topologically reorder, deduplicate, "
            "or merge artifacts",
        ),
    )


def test_postgres_mysql_and_cli_dispatch_boundaries_are_explicit() -> None:
    contract = _read(BACKEND_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "The handwritten PostgreSQL backend remains the byte-exact "
            "compatibility reference.",
            "all five reviewed byte-exact SQL golden fixtures",
            'preserve `"public.users"` as one quoted identifier',
            "emit_mysql_sql(script_ir: ScriptIR) -> SqlResult",
            "Exporting it from `pietto.sql` is a separate public API decision",
            "CLI dialect selection remains explicit and closed.",
            "postgres -> emit_postgres_sql",
            "mysql    -> emit_mysql_sql",
            "Phase 9 does not approve:",
            "emit_sql(script_ir, dialect)",
            "An unknown CLI dialect remains exit `2`",
            "backend diagnostics and exit `1`",
        ),
    )


def test_sqlglot_and_diagnostic_isolation_are_explicit() -> None:
    contract = _read(BACKEND_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "SQLGlot remains an implementation detail inside one private adapter",
            "Capability declarations must use Pietto connector, IR, function, operator",
            "SQLGlot types must not appear in:",
            "Semantic IR",
            "`SqlArtifact` or `SqlResult`",
            "parse rendered PostgreSQL SQL",
            "`PIE-B1000` remains the current and default backend capability diagnostic",
            "New `PIE-Bxxxx` codes should be added only for stable, materially "
            "distinct",
            "They must not be created merely to encode a dialect name.",
        ),
    )


def test_slice5_does_not_implement_backend_abstraction_or_dependencies() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )
    sql_exports = _read("src/pietto/sql/__init__.py")
    cli_source = _read("src/pietto/cli.py")
    pyproject = _read("pyproject.toml")
    lockfile = _read("uv.lock")

    _assert_contains_all(
        sql_exports,
        (
            '"SqlArtifact"',
            '"SqlArtifactKind"',
            '"SqlResult"',
            '"emit_postgres_sql"',
        ),
    )
    assert "def emit_mysql_sql(" in runtime_source
    assert "def emit_sql(" not in runtime_source
    assert "class SqlBackend" not in runtime_source
    assert "BackendCapabilities" not in runtime_source
    assert "sqlglot" not in runtime_source.lower()
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert "emit_mysql_sql" not in sql_exports
    assert '"emit_sql"' not in sql_exports
    assert "sqlglot" not in pyproject.lower()
    assert 'name = "sqlglot"' not in lockfile


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized
