from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE9_PLAN = "docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md"
DIALECT_SOURCE_SPEC = "docs/spec/sql-dialect-source-contract-v1.md"


def test_slice3_contract_and_status_documents_are_complete() -> None:
    plan = _read(PHASE9_PLAN)
    spec = _read(DIALECT_SOURCE_SPEC)
    readme = _read("README.md")
    agents = _read("AGENTS.md")
    language_spec = _read("docs/spec/pietto-v0.9.md")

    assert "3. **Dialect Capability And Source Contract**: complete." in plan
    assert "## Slice 3: Dialect Capability And Source Contract" in plan
    assert (
        "**This contract is planning/specification-only and is not implemented.**"
        in (spec)
    )
    for document in (plan, readme, agents, language_spec):
        assert DIALECT_SOURCE_SPEC in document


def test_connector_and_stage_ownership_are_decision_complete() -> None:
    spec = _read(DIALECT_SOURCE_SPEC)

    _assert_contains_all(
        spec,
        (
            "Initial physical connectors are dialect-specific.",
            "`postgres.table(Text)` remains unchanged.",
            "`mysql.table(Text)`",
            "No generic `table(...)` connector",
            "Semantic analysis owns source-language validity",
            "Semantic IR",
            "The CLI owns output-dialect selection",
            "The selected SQL backend owns SQL-generation capability",
            "Backend capability validation is demand-driven",
            "The semantic connector signature catalog is the source of truth",
        ),
    )


def test_capability_and_fail_closed_rules_are_explicit() -> None:
    spec = _read(DIALECT_SOURCE_SPEC)

    _assert_contains_all(
        spec,
        (
            "Capability Declaration Requirements",
            "A capability declaration is closed: absence means unsupported.",
            "`matches/2` must be absent from the initial MySQL capability",
            "it must not substitute `LIKE`, `REGEXP`, `REGEXP_LIKE`",
            "Future backends must fail closed.",
            "transpile emitted PostgreSQL SQL into another dialect",
            "emit partially rendered SQL for one failed relation",
            "Known connector unsupported by selected backend",
            "Valid function unsupported by selected backend",
        ),
    )


def test_physical_name_and_postgres_compatibility_are_preserved() -> None:
    spec = _read(DIALECT_SOURCE_SPEC)

    _assert_contains_all(
        spec,
        (
            "The argument of current `postgres.table(Text)` is one opaque",
            'FROM "public.users"',
            "must not split on `.`",
            "Structured catalog/schema/table qualification is deferred.",
            "`emit_postgres_sql(ScriptIR) -> SqlResult`",
            "current PostgreSQL byte-exact golden output",
        ),
    )


def test_slice3_does_not_implement_future_dialects_or_dependencies() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )
    cli_source = _read("src/pietto/cli.py")

    assert "mysql.table" not in runtime_source
    assert "emit_mysql_sql" not in runtime_source
    assert "sqlglot" not in runtime_source.lower()
    assert 'choices=("postgres",)' in cli_source


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized
