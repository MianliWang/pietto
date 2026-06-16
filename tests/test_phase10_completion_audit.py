from __future__ import annotations

import hashlib
import inspect
import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"
MYSQL_SOURCE = "tests/fixtures/mysql/compatibility_ordering_metadata.pietto"
MYSQL_FAILURES = "tests/fixtures/mysql/compatibility_failures.pietto"
POSTGRES_SOURCE = "examples/tables/active_users.pietto"
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
EMIT_JSON_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "dialect",
    "diagnostics",
    "cli_errors",
    "artifacts",
    "output",
}
SQL_CASES: tuple[
    tuple[str, str, Callable[[ScriptIR], SqlResult]],
    ...,
] = (
    (
        "examples/tables/active_users.pietto",
        "emit_sql_active_users.sql",
        sql_api.emit_postgres_sql,
    ),
    (
        "examples/queries/active_user_emails.pietto",
        "emit_sql_active_user_emails.sql",
        sql_api.emit_postgres_sql,
    ),
    (
        "tests/fixtures/postgres/compatibility_literals_identifiers.pietto",
        "emit_sql_compatibility_literals_identifiers.sql",
        sql_api.emit_postgres_sql,
    ),
    (
        "tests/fixtures/postgres/compatibility_expressions.pietto",
        "emit_sql_compatibility_expressions.sql",
        sql_api.emit_postgres_sql,
    ),
    (
        "tests/fixtures/postgres/compatibility_ordering_metadata.pietto",
        "emit_sql_compatibility_ordering_metadata.sql",
        sql_api.emit_postgres_sql,
    ),
    (
        "tests/fixtures/mysql/compatibility_literals_identifiers.pietto",
        "emit_mysql_compatibility_literals_identifiers.sql",
        emit_mysql_sql,
    ),
    (
        "tests/fixtures/mysql/compatibility_expressions.pietto",
        "emit_mysql_compatibility_expressions.sql",
        emit_mysql_sql,
    ),
    (
        MYSQL_SOURCE,
        "emit_mysql_compatibility_ordering_metadata.sql",
        emit_mysql_sql,
    ),
)
BOUNDARY_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
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
    "src/pietto/cli_json.py": (
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91"
    ),
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "src/pietto/sql/expressions.py": (
        "4735d47daa375ea79c9e11e6050c9d211c23de6af92884ad424de3b88a1c836e"
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
}


def test_phase10_all_nine_slices_and_status_documents_are_complete() -> None:
    plan = _read(PHASE10_PLAN)
    status_documents = (
        plan,
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )
    slice_names = (
        "Phase 10 Master Plan And Readiness Audit",
        "SQLGlot Evaluation And Isolated Adapter Spike",
        "Dialect Dispatch Design",
        "MySQL Backend Skeleton",
        "MySQL Connector Semantic Surface",
        "MySQL Expression And Relation Rendering MVP",
        "MySQL Golden Corpus And PostgreSQL Regression Lock",
        "CLI Enablement For `--dialect mysql`",
        "Completion Audit",
    )

    assert "**Phase 10 MySQL SQL Generation MVP is complete.**" in plan
    assert "**Slice 9: Completion Audit is complete.**" in plan
    assert "All nine slices are complete." in plan
    for number, name in enumerate(slice_names, start=1):
        assert f"{number}. **{name}**: complete." in plan
    for document in status_documents:
        assert "Phase 10 MySQL SQL Generation MVP is complete." in document


def test_phase10_slice_artifacts_and_decisions_are_present() -> None:
    required_paths = (
        "docs/plan/phase-10-mysql-sql-generation-mvp.md",
        "docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md",
        "docs/spec/sql-dialect-dispatch-design-v1.md",
        "src/pietto/sql/mysql.py",
        "src/pietto/semantic/source_connectors.py",
        "src/pietto/ir/builder.py",
        "src/pietto/sql/mysql_render.py",
        "src/pietto/sql/mysql_expressions.py",
        "src/pietto/sql/mysql_relations.py",
        "tests/test_phase10_mysql_golden_corpus.py",
        "tests/test_phase10_mysql_cli_enablement.py",
        "tests/test_phase10_completion_audit.py",
    )
    evaluation = _read("docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md")

    assert all((REPO_ROOT / path).is_file() for path in required_paths)
    assert (
        "**Decision: use a small handwritten MySQL renderer for the Phase 10 MVP.**"
        in evaluation
    )
    assert "SQLGlot is **rejected for the Phase 10 MySQL MVP implementation**." in (
        evaluation
    )


def test_postgres_and_mysql_reviewed_sql_remain_byte_exact() -> None:
    for source_path, golden_name, emitter in SQL_CASES:
        result = emitter(_compile(source_path))

        assert result.diagnostics == ()
        assert _render_artifacts(result) == (GOLDEN_ROOT / golden_name).read_bytes()


def test_cli_postgres_and_mysql_text_paths_match_reviewed_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for source_path, dialect, golden_name in (
        (POSTGRES_SOURCE, "postgres", "emit_sql_active_users.sql"),
        (MYSQL_SOURCE, "mysql", "emit_mysql_compatibility_ordering_metadata.sql"),
    ):
        assert cli.main(["emit-sql", source_path, "--dialect", dialect]) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out.encode("utf-8") == (GOLDEN_ROOT / golden_name).read_bytes()


def test_mysql_json_v1_and_unknown_dialect_contracts_remain_stable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(["emit-sql", MYSQL_SOURCE, "--dialect", "mysql", "--format=json"]) == 0
    )
    mysql_document = _read_json(capsys)
    assert set(mysql_document) == EMIT_JSON_KEYS
    assert mysql_document["schema_version"] == 1
    assert mysql_document["command"] == "emit-sql"
    assert mysql_document["dialect"] == "mysql"
    assert mysql_document["ok"] is True

    assert (
        cli.main(
            [
                "emit-sql",
                "missing.pietto",
                "--dialect",
                "sqlite",
                "--format=json",
            ]
        )
        == 2
    )
    unknown_document = _read_json(capsys)
    errors = cast(list[dict[str, object]], unknown_document["cli_errors"])
    assert unknown_document["dialect"] == "sqlite"
    assert errors == [
        {
            "kind": "unsupported_dialect",
            "message": "unsupported SQL dialect: sqlite",
            "path": None,
        }
    ]


def test_mysql_output_safety_backend_failure_and_check_are_preserved(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "mysql.sql"
    output.write_text("stale SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                MYSQL_SOURCE,
                "--dialect",
                "mysql",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    success = capsys.readouterr()
    assert success.out == ""
    assert success.err == ""
    assert (
        output.read_bytes()
        == (GOLDEN_ROOT / "emit_mysql_compatibility_ordering_metadata.sql").read_bytes()
    )
    assert not tuple(tmp_path.glob(".mysql.sql.*.tmp"))

    output.write_text("preserve me\n", encoding="utf-8")
    assert (
        cli.main(
            [
                "emit-sql",
                MYSQL_FAILURES,
                "--dialect",
                "mysql",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    failure = capsys.readouterr()
    assert failure.out == ""
    assert failure.err.count("PIE-B1000 error:") == 2
    assert output.read_text(encoding="utf-8") == "preserve me\n"
    assert not tuple(tmp_path.glob(".mysql.sql.*.tmp"))

    assert cli.main(["check", "examples/basic/types.pietto"]) == 0
    checked = capsys.readouterr()
    assert checked.out == "OK: examples/basic/types.pietto\n"
    assert checked.err == ""


def test_public_api_dependency_json_and_deferred_boundaries_remain_closed() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    ).lower()
    postgres_signature = inspect.signature(sql_api.emit_postgres_sql)

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    assert "sqlglot" not in runtime_text
    assert tuple(postgres_signature.parameters) == ("script_ir",)
    assert postgres_signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert "def emit_sql(" not in runtime_text
    assert "schema_version = 2" not in runtime_text
    assert '"schema_version": 2' not in runtime_text
    assert "--project" not in _read("src/pietto/cli.py")
    assert not (REPO_ROOT / "pietto.toml").exists()
    for module_name in (
        "database.py",
        "executor.py",
        "lsp.py",
        "runtime.py",
        "server.py",
        "watch.py",
    ):
        assert not (REPO_ROOT / "src" / "pietto" / module_name).exists()


def test_typing_generated_antlr_and_repository_extension_boundaries_hold() -> None:
    production = _jsonc("pyrightconfig.json")
    tests = json.loads(_read("pyrightconfig.tests.json"))
    vscode = json.loads(_read(".vscode/settings.json"))
    old_extension = "." + "pie"
    old_extension_reference = re.compile(
        re.escape(old_extension) + r"\b|" + re.escape(old_extension) + '"'
    )

    assert production["typeCheckingMode"] == "standard"
    assert production["include"] == ["src/pietto"]
    assert production["exclude"] == ["src/pietto/generated"]
    assert production["ignore"] == ["src/pietto/generated"]
    assert tests == {
        "extends": "./pyrightconfig.json",
        "include": ["tests"],
    }
    assert vscode == {
        "python.analysis.exclude": ["src/pietto/generated/**"],
        "python.analysis.ignore": ["src/pietto/generated/**"],
    }

    scanned_paths = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *(REPO_ROOT / "docs").rglob("*.md"),
        *(REPO_ROOT / "examples").rglob("*"),
        *(REPO_ROOT / "tests" / "fixtures").rglob("*"),
    )
    for path in scanned_paths:
        if not path.is_file():
            continue
        assert not path.name.endswith(old_extension)
        assert old_extension_reference.search(path.read_text(encoding="utf-8")) is None


def test_locked_phase10_boundaries_are_unchanged() -> None:
    for path, expected_hash in BOUNDARY_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


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


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return cast(dict[str, object], document)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _jsonc(path: str) -> dict[str, object]:
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", _read(path)))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
