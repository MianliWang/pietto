from __future__ import annotations

import ast
import hashlib
import importlib.util
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "scripts" / "check_goldens.py"
POLICY_PATH = REPO_ROOT / "docs" / "spec" / "golden-fixture-policy-v1.md"
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
GOLDEN_HASH = "626188783ed0e9cf20f1d6a38ef5009ada08812a2cd2cffa2cc6d0daf8a3f6e2"
BOUNDARY_HASH = "7626892bbfdb4b35dab134543d3aafd1c2781b818cad337c9ed0190997954727"
VALIDATION_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
    ),
    ("tests", ("uv", "run", "pytest")),
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


goldens = cast(Any, _load_module("pietto_check_goldens", AUDIT_PATH))
validate = cast(
    Any,
    _load_module(
        "pietto_validate_for_golden_policy", REPO_ROOT / "scripts/validate.py"
    ),
)


def test_policy_defines_comparison_review_and_ownership_contracts() -> None:
    policy = " ".join(POLICY_PATH.read_text(encoding="utf-8").split())

    for required in (
        "SQL golden fixtures are byte-exact contracts",
        "Artifact separators",
        "final newline",
        "JSON golden fixtures are structural contracts",
        "JSON object member order and insignificant whitespace are not semantic contracts",
        "explicit human review",
        "both",
        "Pietto input",
        "complete expected SQL or JSON output",
        "no golden update, approval, rewrite, or snapshot workflow",
        "focused behavioral tests",
        "Inventory and orphan checks",
        "does not invoke the compiler",
        "adds no SQL feature",
    ):
        assert required in policy


def test_audit_exists_and_uses_only_standard_library_imports() -> None:
    tree = ast.parse(AUDIT_PATH.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imported_modules == {
        "__future__",
        "ast",
        "json",
        "pathlib",
        "sys",
    }


def test_current_inventory_is_fully_classified_referenced_and_paired() -> None:
    inventory = frozenset(path.name for path in GOLDEN_ROOT.iterdir() if path.is_file())
    references, errors = goldens._collect_references(REPO_ROOT)

    assert errors == ()
    assert inventory == goldens.CLASSIFIED_FIXTURES
    assert references == inventory
    assert set(goldens.SQL_FIXTURES) == {
        name for name in inventory if name.endswith(".sql")
    }
    assert set(goldens.JSON_FIXTURES) == {
        name for name in inventory if name.endswith(".json")
    }
    assert set(goldens.FIXTURE_INPUTS) == inventory
    assert goldens.audit(REPO_ROOT) == ()


def test_inventory_audit_reports_missing_references_and_orphans() -> None:
    inventory = frozenset({"present.sql", "orphan.sql"})
    references = frozenset({"present.sql", "missing.sql"})

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        goldens,
        "CLASSIFIED_FIXTURES",
        frozenset({"present.sql", "missing.sql"}),
    )
    try:
        errors = goldens._inventory_errors(inventory, references)
    finally:
        monkeypatch.undo()

    assert "missing classified fixtures: missing.sql" in errors
    assert "unclassified golden files: orphan.sql" in errors
    assert "owning tests reference missing fixtures: missing.sql" in errors
    assert "orphan golden files: orphan.sql" in errors


def test_invalid_json_fixture_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = tmp_path / "invalid.json"
    with invalid.open("x", encoding="utf-8") as stream:
        stream.write("{not json")

    monkeypatch.setattr(goldens, "SQL_FIXTURES", frozenset())
    monkeypatch.setattr(goldens, "JSON_FIXTURES", frozenset({"invalid.json"}))

    assert goldens._fixture_content_errors(tmp_path)[0].startswith(
        "invalid JSON fixture invalid.json:"
    )


def test_audit_is_read_only_and_does_not_invoke_compiler_or_other_scripts() -> None:
    source = AUDIT_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "write_" + "text",
        "write_" + "bytes",
        ".un" + "link(",
        "rm" + "tree",
        "subprocess",
        "emit_" + "postgres_sql",
        "emit_" + "mysql_sql",
        "build_" + "ir",
        "parse_" + "file",
        "ana" + "lyze",
        "scripts/validate.py",
        "scripts/check_generated.py",
    ):
        assert forbidden not in source
    assert ".read_bytes()" in source
    assert "json.loads(" in source
    assert ".strip(" not in source
    assert ".splitlines(" not in source
    assert ".stat(" not in source


def test_real_audit_runs_from_outside_the_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        (sys.executable, str(AUDIT_PATH)),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "verified 25 fixtures" in result.stdout
    assert "20 SQL byte-exact" in result.stdout
    assert "5 JSON structural" in result.stdout


def test_slice4_keeps_prior_commands_independent_and_later_slices_absent() -> None:
    scripts = tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "scripts").glob("*.py"))
    )
    generated_source = (REPO_ROOT / "scripts/check_generated.py").read_text(
        encoding="utf-8"
    )

    assert scripts == (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "scripts/validate.py",
    )
    assert validate.GATES == VALIDATION_GATES
    assert all("check_goldens.py" not in command for _, command in validate.GATES)
    assert "check_goldens" not in generated_source
    assert "package_smoke" not in generated_source
    assert "package_smoke" not in AUDIT_PATH.read_text(encoding="utf-8")
    assert _sha256(REPO_ROOT / "Makefile") == (
        "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7"
    )
    assert (REPO_ROOT / ".github/workflows/ci.yml").is_file()
    assert (REPO_ROOT / "scripts" / "package_smoke.py").is_file()


def test_slice4_preserves_golden_and_compiler_boundary_bytes() -> None:
    assert _aggregate_hash(GOLDEN_ROOT.iterdir()) == GOLDEN_HASH

    paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar" / "Pietto.g4",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
    ]
    paths.extend(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    assert _aggregate_hash(paths) == BOUNDARY_HASH


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
