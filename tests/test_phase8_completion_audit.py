from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.cli_json as cli_json
import pietto.ir as ir_api
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE8_PLAN = "docs/plan/phase-8-project-model-configuration-planning.md"
PHASE8_SPECS = (
    "docs/spec/pietto-config-v1.md",
    "docs/spec/project-path-semantics-v1.md",
    "docs/spec/project-multifile-semantics-v1.md",
    "docs/spec/project-cli-json-v2.md",
    "docs/spec/project-resource-model-v1.md",
)
CHECK_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
}
EMIT_KEYS = CHECK_KEYS | {"dialect", "artifacts", "output"}
BASELINE_HASHES = {
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


def test_phase8_documents_and_all_seven_slices_are_complete() -> None:
    required_paths = (PHASE8_PLAN, *PHASE8_SPECS)
    for path in required_paths:
        assert (REPO_ROOT / path).is_file()

    plan = _read(PHASE8_PLAN)
    assert "**Phase 8 planning/specification is complete.**" in plan
    assert "All seven slices are complete." in plan

    slice_names = (
        "Readiness And Decision Frame",
        "Configuration Contract",
        "Root And Path Semantics",
        "Multi-file Semantics",
        "CLI And JSON Design",
        "Project Resource Model",
        "Completion Audit",
    )
    for number, name in enumerate(slice_names, start=1):
        assert f"{number}. **{name}**: complete." in plan

    readme = _read("README.md")
    agents = _read("AGENTS.md")
    for path in required_paths:
        assert path in "\n".join((plan, readme, agents))


def test_phase8_documents_preserve_the_planning_only_boundary() -> None:
    documents = [_read(PHASE8_PLAN), *(_read(path) for path in PHASE8_SPECS)]
    combined = "\n".join(documents)

    assert "planning/specification-only" in combined
    assert "single-file" in combined
    assert "JSON schema version 1 remain" in combined
    for absent_capability in (
        "does not currently read",
        "does not currently discover",
        "does not currently accept",
        "does not currently load",
        "does not currently",
        "not implemented",
    ):
        assert absent_capability in combined

    _assert_contains_all(
        combined,
        (
            "pietto.toml",
            "project roots",
            "expand globs",
            "compile multiple files",
            "JSON schema version 2",
            "project-level resource budgets",
        ),
    )


def test_phase8_configuration_contract_is_strict_and_non_executable() -> None:
    spec = _read("docs/spec/pietto-config-v1.md")

    _assert_contains_all(
        spec,
        (
            "schema_version = 1",
            "unknown top-level keys",
            "unknown keys inside a known table",
            "Configuration is declarative data",
            "command, build, lifecycle, pre-check, or post-emit hooks",
            "executable plugins or extension loading",
            "environment-variable interpolation or expansion",
            "credentials or passwords",
            "database or connector URLs",
            "must not expose resource-budget overrides",
            "configuration parser, loader, model, or public API",
            "**The contract is not implemented.**",
        ),
    )


def test_phase8_path_contract_is_explicit_contained_and_deterministic() -> None:
    spec = _read("docs/spec/project-path-semantics-v1.md")

    _assert_contains_all(
        spec,
        (
            "require an explicit project root",
            "must not search parent directories",
            "`/` is the only separator",
            "absolute POSIX paths are rejected",
            "`.` and `..` path segments are rejected",
            "physical resolution",
            "## Symlink Policy",
            "## Hard Links And Duplicate File Identity",
            "sorting compares Unicode code points",
            "stable normalized project-relative paths",
        ),
    )


def test_phase8_multifile_contract_is_whole_project_and_import_free() -> None:
    spec = _read("docs/spec/project-multifile-semantics-v1.md")

    _assert_contains_all(
        spec,
        (
            "one deterministic, non-empty source-file set",
            "Each namespace is flat and project-wide",
            "## Cross-file References",
            "## Cycle Handling",
            "strict whole-project gates",
            "## Diagnostic Aggregation",
            "The first project artifact baseline",
            "no import or include statements",
            "**The contract is not implemented.**",
        ),
    )


def test_phase8_project_cli_and_json_v2_remain_design_only() -> None:
    spec = _read("docs/spec/project-cli-json-v2.md")

    _assert_contains_all(
        spec,
        (
            "pietto check --project ROOT",
            "mutually exclusive",
            "a directory supplied as positional `path`",
            "JSON schema version 1 is exclusively the implemented single-file contract",
            "Project mode therefore uses `schema_version: 2`",
            "write exactly one complete JSON document to stdout",
            '"project"',
            '"inputs"',
            '"diagnostics"',
            '"cli_errors"',
            '"artifacts"',
            '"output"',
            "JSON v2 serializer, model, or runtime output",
            "**The design is not implemented.**",
        ),
    )


def test_phase8_project_resource_model_preserves_baseline_and_plans_limits() -> None:
    spec = _read("docs/spec/project-resource-model-v1.md")

    _assert_contains_all(
        spec,
        (
            "`1,048,576` bytes per file",
            "`200,000` tokens per file",
            "`PIE-P1006`",
            "`PIE-P1007`",
            "Selected project source files | `256`",
            "8 MiB",
            "Total raw non-EOF tokens | `1,000,000`",
            "Glob candidate paths examined | `10,000`",
            "Diagnostics emitted | `1,000`",
            "SQL artifacts | `5,000`",
            "16 MiB",
            "32 MiB",
            "exact limits remain TBD until Pietto defines stable, testable counters",
            "provide complete denial-of-service protection",
            "**The contract is not implemented.**",
        ),
    )


def test_phase8_json_v1_runtime_contract_is_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli_json._SCHEMA_VERSION == 1
    assert cli_json._CLI_ERROR_KINDS == {
        "file_read",
        "output_path",
        "output_write",
        "usage",
        "unsupported_dialect",
    }

    assert cli.main(["check", "examples/basic/types.pie", "--format=json"]) == 0
    checked = _read_json_document(capsys)
    assert set(checked) == CHECK_KEYS
    assert checked["schema_version"] == 1
    assert "version" not in checked

    assert (
        cli.main(
            [
                "emit-sql",
                "examples/tables/active_users.pie",
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 0
    )
    emitted = _read_json_document(capsys)
    assert set(emitted) == EMIT_KEYS
    assert emitted["schema_version"] == 1
    assert "version" not in emitted

    json_v1_spec = _read("docs/spec/cli-json-v1.md")
    assert "remains exclusively single-file" in json_v1_spec
    assert "JSON v1 does not contain the Pietto package version" in json_v1_spec


def test_phase8_prohibited_runtime_capabilities_remain_absent() -> None:
    assert not (REPO_ROOT / "pietto.toml").exists()
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(ir_api, "compile_to_ir")
    assert not hasattr(sql_api, "compile_to_sql")

    runtime_sources = _runtime_sources()
    source_text = "\n".join(_read_path(path) for path in runtime_sources).lower()
    for forbidden_fragment in (
        "--project",
        "pietto.toml",
        "schema_version = 2",
        '"schema_version": 2',
        "project_resource",
        "discover_project_root",
        "load_project_config",
        "compile_project",
        "compile_to_ir",
        "compile_to_sql",
        "sqlglot",
        '"mysql"',
    ):
        assert forbidden_fragment not in source_text

    forbidden_imports = {
        "click",
        "fastapi",
        "flask",
        "pydantic",
        "pygls",
        "requests",
        "rich",
        "socket",
        "sqlalchemy",
        "sqlglot",
        "tomli",
        "tomllib",
        "typer",
        "urllib",
        "watchdog",
    }
    assert _runtime_import_roots(runtime_sources).isdisjoint(forbidden_imports)
    assert _runtime_call_attributes(runtime_sources).isdisjoint(
        {"connect", "execute", "glob", "rglob", "walk"}
    )


def test_phase8_dependencies_lock_grammar_and_generated_files_match_baseline() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    assert project["project"]["description"] == "A gradual, semantic SQL authoring DSL"
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["build-system"] == {
        "requires": ["uv_build>=0.11.19,<0.12.0"],
        "build-backend": "uv_build",
    }
    assert project["dependency-groups"]["dev"] == [
        "mypy>=2.1.0",
        "pyright>=1.1.410",
        "pytest>=9.0.3",
        "pytest-cov>=7.1.0",
        "ruff>=0.15.16",
    ]

    for path, expected_hash in BASELINE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def test_phase8_diagnostics_and_future_roadmap_are_audited() -> None:
    legacy_pattern = re.compile(r"(?<!PIE-)\bP[0-9]{4}\b")
    assert _legacy_diagnostic_codes(legacy_pattern) == []

    resource_spec = _read("docs/spec/project-resource-model-v1.md")
    assert resource_spec.count("PIE-P1006") >= 2
    assert resource_spec.count("PIE-P1007") >= 2

    plan = _read(PHASE8_PLAN)
    _assert_contains_all(
        plan,
        (
            "Phase 9: SQL Backend Architecture & Dialect Strategy",
            "Phase 10: Multi-dialect SQL Backend MVP",
            "possibly add SQLGlot only if Phase 9 approves it",
            "Phase 11+: SQL Language Feature Expansion",
            "requires a separate threat model",
        ),
    )


def _read(path: str) -> str:
    return _read_path(REPO_ROOT / path)


def _read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized_text = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized_text


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _runtime_sources() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )


def _runtime_import_roots(paths: tuple[Path, ...]) -> set[str]:
    imports: set[str] = set()
    for path in paths:
        tree = ast.parse(_read_path(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module.partition(".")[0])
    return imports


def _runtime_call_attributes(paths: tuple[Path, ...]) -> set[str]:
    attributes: set[str] = set()
    for path in paths:
        tree = ast.parse(_read_path(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attributes.add(node.func.attr)
    return attributes


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_diagnostic_codes(
    pattern: re.Pattern[str],
) -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []
    roots = (
        REPO_ROOT / "src",
        REPO_ROOT / "tests",
        REPO_ROOT / "docs",
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
    )
    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if not path.is_file() or path.suffix not in {".md", ".pie", ".py", ".txt"}:
                continue
            matches.extend(
                (path.relative_to(REPO_ROOT), match.group())
                for match in pattern.finditer(_read_path(path))
            )
    return matches
