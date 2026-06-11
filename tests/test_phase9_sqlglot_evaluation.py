from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE9_PLAN = "docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md"
SQLGLOT_EVALUATION = "docs/plan/phase-9-sqlglot-evaluation.md"


def test_slice4_evaluation_and_status_documents_are_complete() -> None:
    plan = _read(PHASE9_PLAN)
    evaluation = _read(SQLGLOT_EVALUATION)
    readme = _read("README.md")
    agents = _read("AGENTS.md")
    language_spec = _read("docs/spec/pietto-v0.9.md")

    assert "4. **SQLGlot Evaluation**: complete." in plan
    assert "## Slice 4: SQLGlot Evaluation" in plan
    _assert_contains_all(
        evaluation,
        (
            "**This evaluation is planning-only and does not approve SQLGlot "
            "as a production dependency.**",
        ),
    )
    for document in (plan, readme, agents, language_spec):
        assert SQLGLOT_EVALUATION in document


def test_sqlglot_decision_and_roles_are_explicit() -> None:
    evaluation = _read(SQLGLOT_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "approved only for a future isolated Phase 10 MySQL-generation spike",
            "not approved as a production dependency, PostgreSQL replacement",
            "Pietto Semantic IR",
            "isolated Pietto SQLGlot AST adapter",
            "PostgreSQL SQL to MySQL transpilation",
            "replacing semantic analysis or Semantic IR",
            "optimizer use or semantic query rewriting",
            "executor or in-memory runtime use",
            "database connection or destination selection",
            "schema introspection",
        ),
    )


def test_sqlglot_decision_matrix_covers_required_risks() -> None:
    evaluation = _read(SQLGLOT_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "Programmatic AST construction",
            "PostgreSQL and MySQL rendering",
            "Unsupported-feature behavior",
            "Type isolation",
            "PostgreSQL byte-exact compatibility",
            "MySQL-only generation",
            "API stability and pinning",
            "License and provenance",
            "Release cadence",
            "Dependency surface",
            "Resource consumption",
            "Failure modes",
            "Generation-only threat boundary",
            "Maintenance advantage",
            "Fail for migration",
            "High risk",
            "Open",
        ),
    )


def test_sqlglot_evidence_and_gaps_are_recorded() -> None:
    evaluation = _read(SQLGLOT_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "Evidence was reviewed on June 11, 2026.",
            "SQLGlot 30.9.0",
            "June 4, 2026",
            "No SQLGlot package was installed.",
            "No package artifact was downloaded or executed.",
            "minor releases may be backwards-incompatible",
            "not with Trusted Publishing",
            "No Pietto-specific performance or robustness experiment was run.",
            "https://pypi.org/project/sqlglot/30.9.0/",
            "https://github.com/tobymao/sqlglot/tags",
        ),
    )


def test_phase10_spike_is_fail_closed_and_does_not_approve_postgres_migration() -> None:
    evaluation = _read(SQLGLOT_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "Pietto capability validation remains primary",
            "Configure the selected SQLGlot generation API to raise immediately",
            "Emit no SQL artifact for a failed relation",
            "PostgreSQL migration is not approved.",
            "match all five reviewed SQL golden fixtures byte for byte",
            "Option A: small handwritten MySQL renderer",
            "Option B: isolated ScriptIR-to-SQLGlot-AST MySQL adapter",
            "Failure of any mandatory gate",
        ),
    )


def test_slice4_does_not_add_sqlglot_or_mysql_runtime_behavior() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )
    cli_source = _read("src/pietto/cli.py")
    pyproject = _read("pyproject.toml")
    lockfile = _read("uv.lock")

    assert "sqlglot" not in runtime_source.lower()
    assert "def emit_mysql_sql(" in runtime_source
    assert "mysql.table" not in runtime_source
    assert 'choices=("postgres",)' in cli_source
    assert "emit_mysql_sql" not in cli_source
    assert "sqlglot" not in pyproject.lower()
    assert 'name = "sqlglot"' not in lockfile


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized
