from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import hashlib
import tomllib
from pathlib import Path

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"
SPIKE_EVALUATION = "docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md"
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


def test_slice2_status_and_cross_references_are_complete() -> None:
    plan = _read(PHASE10_PLAN)
    evaluation = _read(SPIKE_EVALUATION)
    status_documents = (
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    _assert_contains_all(
        plan,
        (
            "**Slice 2: SQLGlot Evaluation And Isolated Adapter Spike is complete.**",
            "2. **SQLGlot Evaluation And Isolated Adapter Spike**: complete.",
            "Phase 10 will implement a small handwritten MySQL renderer",
            SPIKE_EVALUATION,
        ),
    )
    _assert_contains_all(
        evaluation,
        (
            "**Phase 10 Slice 2 is complete.**",
            "**Decision: use a small handwritten MySQL renderer for the Phase 10 MVP.**",
        ),
    )
    for document in status_documents:
        assert SPIKE_EVALUATION in document


def test_exact_candidate_dependency_and_supply_chain_evidence_is_recorded() -> None:
    evaluation = _read(SPIKE_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "SQLGlot 30.10.0",
            "June 9, 2026",
            "June 11, 2026",
            "MIT",
            "Base runtime dependencies",
            "None",
            "696535",
            "5888815",
            "540e5dfee4c6b65a3b5d93517a2573bb7546681e95d530d0e4e1702415d8835e",
            "be915f765813ba7ec7c6037732a738cb36811737b5ea6258ba99268043ef74a6",
            "not expose a provenance attestation",
            "982bd166dff9f513ce070742673a1367a0527738",
            "minor releases may contain backwards-incompatible",
            "exact pin",
            "no SQLGlot extras or native acceleration",
        ),
    )


def test_direct_ast_failure_format_literal_and_resource_findings_are_recorded() -> None:
    evaluation = _read(SPIKE_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "ErrorLevel.IMMEDIATE",
            "UnsupportedError",
            "ARRAY(1)",
            "And(A, Or(B, C))",
            "A AND (B OR C)",
            "projection indentation remained two spaces rather than four",
            "ASCII 26",
            "`\\Z`",
            "`public.users` can remain one opaque quoted table identifier",
            "Cold import median, five subprocesses",
            "`0.0769` seconds",
            "`17.35` ms",
            "`88307` bytes",
            "`RecursionError` at depth 200",
            "loaded parser and schema modules",
            "did not automatically import",
            "`sqlglot.optimizer`",
            "`sqlglot.executor`",
            "`sqlglot.lineage`",
        ),
    )


def test_handwritten_renderer_decision_and_rejected_roles_are_explicit() -> None:
    evaluation = _read(SPIKE_EVALUATION)

    _assert_contains_all(
        evaluation,
        (
            "SQLGlot is **rejected for the Phase 10 MySQL MVP implementation**.",
            "lower expected maintenance cost",
            "no SQLGlot entry is added to `pyproject.toml` or `uv.lock`",
            "no SQLGlot adapter is added to production source",
            "a PostgreSQL-to-MySQL transpiler",
            "the PostgreSQL backend or a wrapper around `emit_postgres_sql`",
            "an optimizer or semantic rewrite layer",
            "an executor or runtime",
            "a database, connector, schema, or introspection layer",
            "a public type in IR, SQL results, diagnostics, CLI, JSON, or tests",
            "may reevaluate an exact then-current SQLGlot release",
            "Reevaluation does not authorize PostgreSQL migration.",
        ),
    )


def test_slice2_does_not_add_sqlglot_mysql_or_dialect_runtime_behavior() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "def emit_sql(",
        "sqlglot",
        "schema_version = 2",
        '"schema_version": 2',
    ):
        assert forbidden not in runtime_source.lower()
    assert "mysql.table" in runtime_source.lower()
    assert "def emit_mysql_sql(" in runtime_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in _read("src/pietto/cli.py")
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")


def test_postgres_byte_exact_golden_corpus_is_unchanged() -> None:
    for path, expected_hash in POSTGRES_GOLDEN_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized
