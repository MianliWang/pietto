from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE9_PLAN = "docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md"
MYSQL_CONTRACT = "docs/spec/mysql-sql-generation-mvp-v1.md"


def test_slice6_contract_and_status_documents_are_complete() -> None:
    plan = _read(PHASE9_PLAN)
    contract = _read(MYSQL_CONTRACT)
    documents = (
        plan,
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
        _read("docs/spec/sql-dialect-source-contract-v1.md"),
        _read("docs/spec/sql-backend-abstraction-contract-v1.md"),
        _read("docs/plan/phase-9-sqlglot-evaluation.md"),
    )

    assert "All seven slices are complete." in plan
    assert "6. **MySQL MVP Contract**: complete." in plan
    assert "## Slice 6: MySQL MVP Contract" in plan
    _assert_contains_all(
        contract,
        (
            "**Phase 10 Slices 4 through 6 implement the private closed "
            "MySQL backend.**",
        ),
    )
    for document in documents:
        assert MYSQL_CONTRACT in document


def test_mysql_target_connector_and_entry_point_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "Oracle MySQL 8.0 or later SQL generation",
            "MariaDB and other MySQL-compatible products are not certified",
            "mysql.table(Text)",
            "one non-empty compile-time text literal",
            "emit_mysql_sql(script_ir: ScriptIR) -> SqlResult",
            "Public export of `emit_mysql_sql` remains a separate Phase 10 API "
            "decision.",
            "Connector names also do not select the output backend.",
            "`dialect mysql` is descriptive source metadata",
            "Header/CLI mismatch validation is deferred.",
        ),
    )


def test_mysql_definition_relation_and_expression_capability_is_closed() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "| Emitting | `RelationIR` |",
            "Non-emitting metadata",
            "Unknown future definitions must not be silently treated as metadata.",
            "one non-empty ordered projection list",
            "zero or one `WHERE` filter",
            "`LiteralIR`",
            "`FieldRefIR`",
            "`ComparisonIR`",
            "`IsNullIR`",
            "`BetweenIR`",
            "`UnaryIR`",
            "`BinaryIR`",
            "Any new or absent expression node is unsupported",
            "Nested non-atomic expressions must use deterministic parentheses.",
        ),
    )


def test_mysql_functions_operators_and_matches_policy_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "| `lower(value)` | `LOWER(value)`",
            "| `trim(value)` | `TRIM(value)`",
            "| `len(value)` | `CHAR_LENGTH(value)`",
            "It must not map to `LENGTH`",
            "`matches/2` is explicitly absent from the MySQL MVP.",
            "`LIKE`",
            "`REGEXP`",
            "`RLIKE`",
            "`REGEXP_LIKE`",
            "| `!=` | `<>` |",
            "`value IS NULL`",
            "`value IS NOT NULL`",
            "`value BETWEEN lower AND upper`",
            "| `%` | `%` |",
            "The MVP does not use `DIV`, `MOD`, `&&`, `||`",
        ),
    )


def test_mysql_identifier_and_physical_name_policy_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "Every rendered identifier uses MySQL backtick quoting",
            "Embedded backticks are doubled",
            "rejects empty identifiers",
            "rejects NUL",
            "preserves supplied spelling and case",
            "64 characters for database, table, view, and column",
            "256 characters for ordinary select-list aliases",
            "Overlong identifiers fail with `PIE-B1000`",
            "`lower_case_table_names`",
            'mysql.table("analytics.users")',
            "FROM `analytics.users`",
            "The dot is part of the quoted identifier.",
            "Structured database/table qualification is deferred",
        ),
    )


def test_mysql_literal_sql_mode_and_character_set_policy_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "| `None` | `NULL` |",
            "| `False` | `FALSE` |",
            "| `True` | `TRUE` |",
            "single quote escaped as `''`",
            "backslash escaped as `\\\\`",
            "newline escaped as `\\n`",
            "ASCII 26 escaped as `\\Z`",
            "NUL rejected rather than emitted as `\\0`",
            "NO_BACKSLASH_ESCAPES is disabled",
            "This matches the MySQL 8.0 default",
            "`ANSI_QUOTES` is enabled",
            "`character_set_connection=utf8mb4`",
            "Pietto emits neither a character-set introducer nor a collation override.",
        ),
    )


def test_mysql_artifact_diagnostic_cli_and_json_rules_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "no trailing newline inside `SqlArtifact.sql`",
            "Artifact order and diagnostic order each follow source definition order.",
            "The MySQL MVP uses `PIE-B1000`",
            "one primary backend diagnostic per failed emitting definition",
            "Phase 10 Slice 8 passes the backend, golden, compatibility, typing, "
            "and security gates",
            "mysql -> emit_mysql_sql",
            "connector, source header, or file extension",
            "JSON schema version 1 requires no new field.",
            '"dialect": "mysql"',
            "backend errors do not write the requested output file",
        ),
    )


def test_mysql_golden_corpus_and_cli_enablement_gate_are_explicit() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "No snapshot library, generated expected output, or automatic update "
            "command",
            "1. **Literals And Identifiers**",
            "2. **Expressions**",
            "3. **Ordering And Metadata**",
            "one structural JSON v1 success fixture",
            "## Gate Before `--dialect mysql`",
            "compile-time literal validation",
            "Every required byte-exact SQL golden",
            "All existing PostgreSQL unit and golden tests remain byte-exact.",
            "CLI enablement should be the final implementation step",
        ),
    )


def test_mysql_runtime_database_and_richer_sql_remain_deferred() -> None:
    contract = _read(MYSQL_CONTRACT)

    _assert_contains_all(
        contract,
        (
            "DDL",
            "joins",
            "`GROUP BY` and aggregates",
            "`ORDER BY` and `LIMIT`",
            "windows",
            "unions",
            "CTEs",
            "subqueries",
            "materialization",
            "SQL execution",
            "database connection",
            "schema introspection",
            "connector runtime",
            "credentials and secrets",
            "project and multi-file implementation",
            "watch mode",
            "LSP/editor integration",
            "Web UI",
        ),
    )


def test_slice6_does_not_implement_mysql_or_change_dependencies() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )
    cli_source = _read("src/pietto/cli.py")
    sql_exports = _read("src/pietto/sql/__init__.py")
    pyproject = _read("pyproject.toml")
    lockfile = _read("uv.lock")

    assert "mysql.table" in runtime_source
    assert "def emit_mysql_sql(" in runtime_source
    assert "def emit_sql(" not in runtime_source
    assert "sqlglot" not in runtime_source.lower()
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "mysql.table" not in cli_source
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
