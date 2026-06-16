from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import re
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

import pietto.cli as cli
import pietto.cli_json as cli_json
import pietto.sql as sql_api
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests/fixtures/golden"
POSTGRES_INPUT = Path("tests/fixtures/phase12/postgres_order_limit_composition.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase12/mysql_order_limit_composition.pietto")
POSTGRES_SQL = "emit_sql_order_limit_composition.sql"
MYSQL_SQL = "emit_mysql_order_limit_composition.sql"
MYSQL_JSON = "phase12_mysql_order_limit_composition.json"
HISTORICAL_GOLDENS = (
    "check_sources_users_warning.json",
    "check_types.json",
    "emit_mysql_compatibility_expressions.sql",
    "emit_mysql_compatibility_literals_identifiers.sql",
    "emit_mysql_compatibility_ordering_metadata.json",
    "emit_mysql_compatibility_ordering_metadata.sql",
    "emit_sql_active_user_emails.sql",
    "emit_sql_active_users.json",
    "emit_sql_active_users.sql",
    "emit_sql_compatibility_expressions.sql",
    "emit_sql_compatibility_literals_identifiers.sql",
    "emit_sql_compatibility_ordering_metadata.sql",
)
HISTORICAL_GOLDENS_HASH = (
    "11d4343245dc18fd574999cbef5bff7c316d90975b3856ed729e8d2c1d579cf0"
)
BOUNDARY_HASH = "c2ae2d4231cfe0a7cd31fdb012db2cdf12f4b0c356a0b860003507749e441159"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


goldens = cast(
    Any,
    _load_module(
        "pietto_phase12_composition_goldens",
        REPO_ROOT / "scripts/check_goldens.py",
    ),
)


@pytest.mark.parametrize(
    ("input_path", "fixture", "emitter"),
    [
        (POSTGRES_INPUT, POSTGRES_SQL, sql_api.emit_postgres_sql),
        (MYSQL_INPUT, MYSQL_SQL, emit_mysql_sql),
    ],
)
def test_composition_compiles_to_reviewed_byte_exact_sql(
    input_path: Path,
    fixture: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert (result.artifacts[0].sql + "\n").encode("utf-8") == (
        GOLDEN_ROOT / fixture
    ).read_bytes()


def test_composition_uses_input_scope_not_projection_aliases() -> None:
    source = (REPO_ROOT / POSTGRES_INPUT).read_text(encoding="utf-8")

    assert "normalized = lower(email)" in source
    assert "created_at desc" in source
    assert "\n        id\n    limit 100" in source
    assert "normalized asc" not in source
    assert "normalized desc" not in source


@pytest.mark.parametrize(
    ("input_path", "dialect", "fixture"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_SQL),
        (MYSQL_INPUT, "mysql", MYSQL_SQL),
    ],
)
def test_cli_text_stdout_matches_reviewed_sql(
    input_path: Path,
    dialect: str,
    fixture: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == (GOLDEN_ROOT / fixture).read_bytes()


def test_cli_output_atomically_replaces_file_without_stream_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "composition.sql"
    output.write_bytes(b"stale output\n")
    original_inode = output.stat().st_ino
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(POSTGRES_INPUT),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_bytes() == (GOLDEN_ROOT / POSTGRES_SQL).read_bytes()
    assert output.stat().st_ino != original_inode
    assert tuple(tmp_path.iterdir()) == (output,)


def test_mysql_json_v1_matches_reviewed_structure_and_sql(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(MYSQL_INPUT),
                "--dialect",
                "mysql",
                "--format",
                "json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    expected = json.loads((GOLDEN_ROOT / MYSQL_JSON).read_text(encoding="utf-8"))
    assert captured.err == ""
    assert document == expected
    assert document["schema_version"] == 1
    assert (document["artifacts"][0]["sql"] + "\n").encode("utf-8") == (
        GOLDEN_ROOT / MYSQL_SQL
    ).read_bytes()


def test_historical_golden_bytes_remain_unchanged() -> None:
    paths = tuple(GOLDEN_ROOT / name for name in HISTORICAL_GOLDENS)

    assert _aggregate_hash(paths) == HISTORICAL_GOLDENS_HASH


def test_golden_inventory_owns_every_new_fixture_without_orphans() -> None:
    expected_sql = {POSTGRES_SQL, MYSQL_SQL}

    assert expected_sql <= set(goldens.SQL_FIXTURES)
    assert MYSQL_JSON in goldens.JSON_FIXTURES
    assert set(goldens.FIXTURE_INPUTS[POSTGRES_SQL]) == {POSTGRES_INPUT.as_posix()}
    assert set(goldens.FIXTURE_INPUTS[MYSQL_SQL]) == {MYSQL_INPUT.as_posix()}
    assert set(goldens.FIXTURE_INPUTS[MYSQL_JSON]) == {MYSQL_INPUT.as_posix()}
    assert goldens.audit(REPO_ROOT) == ()


def test_golden_workflow_remains_review_only_and_non_updating() -> None:
    sources = "\n".join(
        (
            (REPO_ROOT / "scripts/check_goldens.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "docs/spec/golden-fixture-policy-v1.md").read_text(
                encoding="utf-8"
            ),
        )
    )

    for forbidden in (
        "update_" + "golden",
        "approve_" + "golden",
        "rewrite_" + "golden",
        "snapshot " + "update",
        "--" + "update",
    ):
        assert forbidden not in sources.lower()
    for forbidden in ("write_" + "text", "write_" + "bytes", "subprocess"):
        assert forbidden not in (REPO_ROOT / "scripts/check_goldens.py").read_text(
            encoding="utf-8"
        )


def test_production_api_json_dependency_and_compiler_boundaries_are_unchanged() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    signature = inspect.signature(sql_api.emit_postgres_sql)
    boundary_paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar/Pietto.g4",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
    ]
    boundary_paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    assert _aggregate_hash(boundary_paths) == BOUNDARY_HASH
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in (REPO_ROOT / "uv.lock").read_text(encoding="utf-8").lower()
    assert tuple(signature.parameters) == ("script_ir",)
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert cli_json._SCHEMA_VERSION == 1


def test_suffix_diagnostics_and_slice_status_remain_canonical() -> None:
    repository_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in ("src", "tests", "docs", "examples", "grammar")
        for path in sorted((REPO_ROOT / root).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".md", ".pietto", ".g4"}
    )
    plan = (REPO_ROOT / "docs/plan/phase-12-sql-feature-expansion-i.md").read_text(
        encoding="utf-8"
    )

    assert re.search(r"\." + "pie" + r"\b", repository_text) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository_text) is None
    assert "**Slice 5: Composition, CLI/JSON And Goldens is complete.**" in plan
    assert "**Slice 6: Completion Audit And Documentation is complete.**" in plan


def _compile(input_path: Path) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / input_path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    assert not [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
