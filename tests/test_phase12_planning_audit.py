from __future__ import annotations

import hashlib
import inspect
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pietto.cli_json as cli_json
import pietto.sql as sql_api
from pietto.parser_api import parse_source

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "config.py"
PROJECT_CHECK_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "check.py"
PHASE12_PLAN = "docs/plan/phase-12-sql-feature-expansion-i.md"

FILE_HASHES = {
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
    ),
    "scripts/validate.py": (
        "567c9ea1836c39d4e2037012e2b6e7795ceb3a9f54e9e3f7d951ae39155a5987"
    ),
    "scripts/check_generated.py": (
        "b126059cd0aebe9535fceb9b0a1b1c09ee1ba22af13f70d276d7e013c49c60e7"
    ),
    "scripts/check_goldens.py": (
        "23e271e0138e6b7ac189e27f33c557e04300301adff8f49747999e0c4b50c2e9"
    ),
    "scripts/package_smoke.py": (
        "aa6ab2ddf8ed8e889e8d75de224467565b7e6034cf068b44d602807fdd554924"
    ),
}

GROUP_HASHES = {
    "frontend": "cd28ccecc82f9d3f0bfa85fe886490e81d7260e9fe61919a4913ff8d6b21c52f",
    "semantic": "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    "ir": "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9",
    "sql": "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026",
    "generated": "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4",
    "cli": "30e6e4cedfe91b4e52a5cad3e13b302a8617476c2a48dd92361e5fa5d6183019",
}

GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"


def test_phase12_master_plan_records_final_slice_order_and_status() -> None:
    plan = _read(PHASE12_PLAN)
    normalized_plan = " ".join(plan.split())
    slice_names = (
        "Master Plan And Baseline Audit",
        "ORDER BY / LIMIT Language Contract",
        "LIMIT Vertical Slice",
        "ORDER BY Vertical Slice",
        "Composition, CLI/JSON And Goldens",
        "Completion Audit And Documentation",
    )

    assert "# Phase 12: SQL Feature Expansion I" in plan
    assert "**Phase 12 SQL Feature Expansion I is complete.**" in plan
    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "**Slice 2: ORDER BY / LIMIT Language Contract is complete.**" in plan
    assert "**Slice 3: LIMIT Vertical Slice is complete.**" in plan
    assert "**Slice 4: ORDER BY Vertical Slice is complete.**" in plan
    assert "**Slice 5: Composition, CLI/JSON And Goldens is complete.**" in plan
    assert "**Slice 6: Completion Audit And Documentation is complete.**" in plan

    offsets = [
        plan.index(f"{number}. **{name}**")
        for number, name in enumerate(slice_names, start=1)
    ]
    assert offsets == sorted(offsets)
    assert len(re.findall(r"\*\*Slice \d+:[^*]+ is complete\.\*\*", plan)) == 6
    assert "planned only" not in normalized_plan
    assert (
        "Future implementation work requires separate explicit authorization"
        in normalized_plan
    )


def test_phase12_status_documents_are_scope_aware() -> None:
    documents = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert "Phase 11 Release Readiness & Reproducible Validation" in normalized
        assert "Phase 12" in normalized
        assert "Slice 2" in normalized
        assert PHASE12_PLAN in document

    combined = " ".join("\n".join(documents.values()).split())
    assert (
        "Phase 11 Release Readiness & Reproducible Validation is complete" in combined
    )
    assert "Phase 12 SQL Feature Expansion I is complete" in combined
    assert "Slices 1 through 6 are complete" in combined
    assert "Slice 3 implements only static `LIMIT`" in combined
    assert "Slice 4 implements only input-scope `ORDER BY`" in combined
    assert "Projection aliases are not available to ordering" in combined


def test_slice6_locks_configuration_workflow_and_compiler_boundaries() -> None:
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

    assert _aggregate_paths(REPO_ROOT / "tests/fixtures/golden") == GOLDENS_HASH


def test_limit_and_order_by_are_implemented_with_fixed_clause_order() -> None:
    grammar = _read("grammar/Pietto.g4")
    parser_tests = _read("tests/test_parser_relations.py")

    assert "ORDER: 'order';" in grammar
    assert "BY: 'by';" in grammar
    assert "ASC: 'asc';" in grammar
    assert "DESC: 'desc';" in grammar
    assert "LIMIT: 'limit';" in grammar
    assert '"    order by id\\n"' in parser_tests

    limit_result = parse_source(
        "query projected:\n"
        "    from input_relation\n"
        "    select:\n"
        "        id\n"
        "    limit 10\n",
        path="phase12-slice3.pietto",
    )
    assert limit_result.diagnostics == ()
    assert limit_result.ast is not None

    order_result = parse_source(
        "query projected:\n"
        "    from input_relation\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        id desc\n"
        "    limit 10\n",
        path="phase12-slice4.pietto",
    )
    assert order_result.diagnostics == ()
    assert order_result.ast is not None


def test_public_api_json_dependency_and_package_contracts_are_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_text = _runtime_text()
    signature = inspect.signature(sql_api.emit_postgres_sql)

    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.12"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
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
    assert "def emit_mysql_sql(" in runtime_text
    assert "def emit_sql(" not in runtime_text
    assert cli_json._SCHEMA_VERSION == 1
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()


def test_suffix_diagnostics_and_deferred_capabilities_remain_locked() -> None:
    repository_text = _repository_text()
    runtime_text = _runtime_text(include_project_config=False).lower()
    cli_source = _read("src/pietto/cli.py")
    plan = _read(PHASE12_PLAN)

    assert re.search(r"\." + "pie" + r"\b", repository_text) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository_text) is None
    for prefix in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
        assert prefix in plan

    for required in (
        "joins",
        "grouping",
        "aggregates",
        "windows",
        "CTEs",
        "subqueries",
        "DDL",
        "DML",
        "SQL execution",
        "database or connector connections",
        "schema introspection",
        "project or multi-file mode",
        "`pietto.toml`",
        "watch mode",
        "LSP/editor support",
        "Web UI",
        "online playground",
        "JSON v2",
        "SQLGlot",
        "package version bump",
    ):
        assert required in plan

    assert '"--project"' in cli_source
    assert "def _run_project_check(" in cli_source
    assert "check_project_parse_only(root)" in cli_source
    assert not (REPO_ROOT / "pietto.toml").exists()
    assert "sqlglot" not in runtime_text
    assert "compile_project" not in runtime_text
    assert "load_project_config" not in runtime_text
    assert "project_loader" not in runtime_text
    for module_name in (
        "database.py",
        "executor.py",
        "lsp.py",
        "runtime.py",
        "server.py",
        "watch.py",
    ):
        assert not (REPO_ROOT / "src/pietto" / module_name).exists()


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


def _aggregate_paths(root: Path) -> str:
    return _aggregate_files(path for path in root.iterdir() if path.is_file())


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_text(*, include_project_config: bool = True) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
        and (
            include_project_config
            or path not in {PROJECT_CONFIG_SOURCE, PROJECT_CHECK_SOURCE}
        )
    )


def _repository_text() -> str:
    paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
        REPO_ROOT / PHASE12_PLAN,
    ]
    for directory in ("src", "tests", "docs", "examples", "grammar", ".github"):
        paths.extend(
            path
            for path in (REPO_ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix
            in {".py", ".md", ".json", ".sql", ".toml", ".lock", ".g4", ".yml"}
        )
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(set(paths)))


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
