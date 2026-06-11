from __future__ import annotations

import hashlib
import inspect
import tomllib
from pathlib import Path

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE11_PLAN = "docs/plan/phase-11-release-readiness-reproducible-validation.md"

FILE_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "grammar/Pietto.g4": (
        "af3e312593182f37e9d434677b4018a2aa3690cd337a51ef0b7b4f4c9d822caf"
    ),
}

GROUP_HASHES = {
    "frontend": "7629023467e3a81fb9c1380315a4590bf1ded00373beb203f02a86c5e881c379",
    "semantic": "a3b346207b5804ebed4116cb5a4b1f2521216feb5eaeb4af1b3a05fa8904fa8a",
    "ir": "2bc3466eb4ecda401f4736859707dc2006cd6154b9e01e39184f6563dc90f7f5",
    "sql": "edbe63a6b48ff20becf926589bfd5ff86cc9debdbf249c0d67842d52b8e56cb0",
    "generated": "3995ef8be0cad120dbfde44e6af79ca6f84769d96a8673606e4dfb9b06c70c28",
    "cli": "235d4e50c3474306253dfc6b118e2518b3e300e90f7fbe9903263a39cbdc42a0",
}


def test_phase11_master_plan_records_slice1_and_seven_ordered_slices() -> None:
    plan = _read(PHASE11_PLAN)

    assert "# Phase 11: Release Readiness & Reproducible Validation" in plan
    assert (
        "**Phase 11 Release Readiness & Reproducible Validation is in progress.**"
        in plan
    )
    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "Slices 2 through 7 are planned only." in plan

    slice_names = (
        "Master Plan And Baseline Audit",
        "Authoritative Validation Entry Point",
        "ANTLR Provenance And Generated-File Guard",
        "Golden Fixture Policy And Audit",
        "GitHub Actions CI",
        "Packaging And Installed CLI Smoke",
        "Completion Audit And Documentation",
    )
    offsets = [
        plan.index(f"{number}. **{name}**")
        for number, name in enumerate(
            slice_names,
            start=1,
        )
    ]

    assert offsets == sorted(offsets)


def test_phase11_status_documents_are_scope_aware() -> None:
    documents = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert "Phase 11 Release Readiness & Reproducible Validation" in normalized
        assert "Slice 1" in normalized
        assert PHASE11_PLAN in document

    combined = "\n".join(documents.values())
    assert "Phase 10 MySQL SQL Generation MVP is complete" in combined
    assert "Slices 2 through 7" in combined
    assert "planned" in combined


def test_python_floor_and_future_ci_matrix_are_explicit() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    plan = _read(PHASE11_PLAN)
    language_spec = _read("docs/spec/pietto-v0.9.md")
    normalized_plan = " ".join(plan.split())

    assert project["project"]["requires-python"] == ">=3.12"
    assert "Python 3.12 and Python 3.13" in normalized_plan
    assert "Python 3.12/3.13" in language_spec
    assert "does not by itself change" in normalized_plan


def test_slice1_does_not_implement_later_workflow_artifacts() -> None:
    assert not (REPO_ROOT / ".github" / "workflows").exists()
    assert not (REPO_ROOT / "scripts").exists()
    assert not (REPO_ROOT / "tools" / "antlr-4.13.2-complete.jar.sha256").exists()

    plan = " ".join(_read(PHASE11_PLAN).split())
    for required in (
        "This baseline does not claim that CI",
        "an ANTLR checksum gate",
        "a generated-file regeneration guard",
        "a formal golden policy",
        "an installed-package smoke test is implemented",
    ):
        assert required in plan


def test_slice1_locks_configuration_and_compiler_boundaries() -> None:
    for path, expected_hash in FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "frontend": (
            "src/pietto/__init__.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "src/pietto/errors.py",
            "src/pietto/indentation.py",
            "src/pietto/parser_api.py",
        ),
        "semantic": _module_paths("src/pietto/semantic"),
        "ir": _module_paths("src/pietto/ir"),
        "sql": _module_paths("src/pietto/sql"),
        "generated": tuple(
            path.relative_to(REPO_ROOT).as_posix()
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "cli": (
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        ),
    }

    for name, paths in groups.items():
        assert _aggregate_sha256(paths) == GROUP_HASHES[name]


def test_public_sql_cli_and_json_v1_boundaries_remain_unchanged() -> None:
    signature = inspect.signature(sql_api.emit_postgres_sql)
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert "def emit_sql(" not in runtime_text
    assert "def emit_mysql_sql(" in runtime_text
    assert "schema_version = 2" not in runtime_text
    assert '"schema_version": 2' not in runtime_text
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in runtime_text


def test_sql_expansion_and_deferred_capabilities_remain_absent() -> None:
    grammar = _read("grammar/Pietto.g4")
    parser_tests = _read("tests/test_parser_relations.py")
    cli_source = _read("src/pietto/cli.py")
    plan = _read(PHASE11_PLAN)

    assert "ORDER:" not in grammar
    assert "LIMIT:" not in grammar
    assert '"    order by id\\n"' in parser_tests
    assert '"    limit 10\\n"' in parser_tests

    for required in (
        "`ORDER BY`, `LIMIT`, or any other SQL feature expansion",
        "SQL execution",
        "database connection",
        "schema introspection",
        "project or multi-file mode",
        "`pietto.toml`",
        "watch mode",
        "LSP/editor integration",
        "Web UI",
        "online playground",
        "JSON v2",
        "SQLGlot",
    ):
        assert required in plan

    assert "--project" not in cli_source
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


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_paths(directory: str) -> tuple[str, ...]:
    root = REPO_ROOT / directory
    return tuple(
        path.relative_to(REPO_ROOT).as_posix() for path in sorted(root.glob("*.py"))
    )


def _aggregate_sha256(paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(paths):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((REPO_ROOT / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
