from __future__ import annotations

import hashlib
import importlib.util
import inspect
import re
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_product_repair1_gate2_is_active,
)

import pietto.cli_json as cli_json
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "config.py"
PROJECT_CHECK_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "check.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-11-release-readiness-reproducible-validation.md"
)
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"

EXPECTED_COMMANDS = (
    "uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)
EXPECTED_GATES = (
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
EXPECTED_ACTIONS = (
    "actions/checkout",
    "actions/setup-python",
    "actions/setup-java",
    "astral-sh/setup-uv",
)
EXPECTED_BLOBS = {
    "scripts/validate.py": "e1607a47da34ff868ca09a128c8897a6a0dbad21",
    "scripts/check_generated.py": "51081d5337e0659e73f8666ba639c0d4c3fe3a4b",
    "scripts/check_goldens.py": "4f49ddc0a8a6836b68a83a98cc9c05389d4519a3",
    "scripts/package_smoke.py": "f490e50aacd07132948fe2fd826eb5053b5e1c59",
}
EXPECTED_FILES = {
    "grammar/Pietto.g4": (
        "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724"
    ),
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
}
EXPECTED_GROUPS = {
    "frontend": "9ec7a4f6c56fc9a1347fcc590bb77704d6d11343bcf6325482d0ecd4d44fa3e5",
    "semantic": "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    "ir": "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9",
    "sql": "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026",
    "generated": "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1",
    "cli": "30e6e4cedfe91b4e52a5cad3e13b302a8617476c2a48dd92361e5fa5d6183019",
}
POSTGRES_GOLDENS = {
    "emit_sql_active_user_emails.sql": (
        "d5aaf1e4cc3c334c72c3978858358b4df21ea3572daa0ecdda0fee0ceff74ee0"
    ),
    "emit_sql_active_users.sql": (
        "5a0878c84b208c906d8affe0f54706118f14bee40951ab8e25c70c90e95f43d3"
    ),
    "emit_sql_compatibility_expressions.sql": (
        "943f92d70fd433d803cf5409b02254f9f7801822270eb5ca567d6cdde9387c46"
    ),
    "emit_sql_compatibility_literals_identifiers.sql": (
        "691b04423af4cb4861d5aa56c0ae865181a738abca153f37ae7c69c1a8857477"
    ),
    "emit_sql_compatibility_ordering_metadata.sql": (
        "b4e2d6a0bfa3ddff91b75892ddc071ec9199d41512e826a2ad81bac76e23752c"
    ),
}
MYSQL_GOLDENS = {
    "emit_mysql_compatibility_expressions.sql": (
        "bbfaebf5b14fd21528a2081a4f73d34fde989a6199ce296b527d2cf035cc11f5"
    ),
    "emit_mysql_compatibility_literals_identifiers.sql": (
        "671a3f515b62a207959efad1aa1125635ae6ed469f5e53613848da835900859a"
    ),
    "emit_mysql_compatibility_ordering_metadata.json": (
        "35ee14bcfac5a6bc3dc0c6a0529434ed5b054827618fe79fd7e0339b4dddcc64"
    ),
    "emit_mysql_compatibility_ordering_metadata.sql": (
        "d3f9d327725f9f37ac931a48d80a69462ddd99a193cf8b868833d1350302bbab"
    ),
}
ALL_GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"
BOUNDARY_HASH = "6fc8d255dc6cb8f5bd9a4edaf4af2867f975aa02f29cf63222d77040930636c8"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validate = cast(
    Any,
    _load_module(
        "pietto_phase11_completion_validate", REPO_ROOT / "scripts/validate.py"
    ),
)


def test_phase11_master_plan_and_status_documents_are_complete() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    normalized_plan = " ".join(plan.split())
    slice_names = (
        "Master Plan And Baseline Audit",
        "Authoritative Validation Entry Point",
        "ANTLR Provenance And Generated-File Guard",
        "Golden Fixture Policy And Audit",
        "GitHub Actions CI",
        "Packaging And Installed CLI Smoke",
        "Completion Audit And Documentation",
    )

    assert (
        "**Phase 11 Release Readiness & Reproducible Validation is complete.**" in plan
    )
    for name in slice_names:
        assert f"**Slice {slice_names.index(name) + 1}: {name} is complete.**" in plan
    assert "Phase 12" in normalized_plan
    assert "future" in normalized_plan
    assert "not authorized" in normalized_plan

    documents = {
        "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        "docs/spec/pietto-v0.9.md": (REPO_ROOT / "docs/spec/pietto-v0.9.md").read_text(
            encoding="utf-8"
        ),
    }
    normalized_agents = " ".join(documents["AGENTS.md"].split())
    assert (
        "Current phase status: Phase 11 Release Readiness & Reproducible "
        "Validation is complete."
    ) in normalized_agents
    assert "Phase 11 complete" in documents["docs/spec/pietto-v0.9.md"]

    combined = " ".join("\n".join((*documents.values(), plan)).split()).lower()
    for required in (
        "release-readiness",
        "reproducible validation",
        "actual package publication",
        "registry credentials",
        "release signing",
        "provenance attestations",
        "automated versioning",
        "not authorized",
    ):
        assert required in combined


def test_four_workflow_scripts_are_independent_and_byte_locked() -> None:
    scripts = tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "scripts").glob("*.py"))
    )
    assert scripts == (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "scripts/validate.py",
    )

    sources = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in EXPECTED_BLOBS
        if path.startswith("scripts/")
    }
    for path, expected_hash in EXPECTED_BLOBS.items():
        assert _git_blob_hash(REPO_ROOT / path) == expected_hash

    assert validate.GATES == EXPECTED_GATES
    for script_path, source in sources.items():
        for other_path in sources:
            if other_path != script_path:
                assert Path(other_path).name not in source


def test_generated_guard_keeps_provenance_and_non_mutating_regeneration() -> None:
    source = (REPO_ROOT / "scripts/check_generated.py").read_text(encoding="utf-8")
    checksum = (REPO_ROOT / "tools/antlr-4.13.2-complete.jar.sha256").read_text(
        encoding="ascii"
    )

    assert checksum == (
        "eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76\n"
    )
    for required in (
        "CHECKSUM_FILE",
        "_verify_jar",
        "TemporaryDirectory",
        "git",
        "ls-files",
        "_compare_generated_files",
        "read_bytes()",
    ):
        assert required in source
    for forbidden in ("write_" + "bytes", ".un" + "link(", "rm" + "tree"):
        assert forbidden not in source


def test_golden_audit_remains_inventory_only_and_non_updating() -> None:
    source = (REPO_ROOT / "scripts/check_goldens.py").read_text(encoding="utf-8")

    for required in (
        "CLASSIFIED_FIXTURES",
        "FIXTURE_INPUTS",
        "_collect_references",
        "_inventory_errors",
        "_fixture_content_errors",
        "json.loads",
    ):
        assert required in source
    for forbidden in (
        "subprocess",
        "write_" + "text",
        "write_" + "bytes",
        ".un" + "link(",
        "update_" + "golden",
    ):
        assert forbidden not in source


def test_package_smoke_remains_temp_clean_install_and_external_cli_only() -> None:
    source = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")

    for required in (
        "TemporaryDirectory",
        '"--sdist"',
        '"--wheel"',
        '"--out-dir"',
        "sys.executable,",
        '"-m",',
        '"venv",',
        '"pip",',
        '"install",',
        "scratch_dir.relative_to(REPO_ROOT)",
        "_venv_cli(venv_dir)",
        "postgres.stdout != expected_postgres",
        "json.loads(mysql.stdout)",
    ):
        assert required in source
    assert "--editable" not in source
    assert '"-e"' not in source
    assert 'REPO_ROOT / "dist"' not in source


def test_ci_is_unchanged_minimal_permission_orchestration() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    run_commands = tuple(
        re.findall(r"(?m)^        run: (uv run python scripts/.+)$", workflow)
    )
    actions = tuple(
        repository
        for repository, _sha in re.findall(
            r"(?m)^        uses: ([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@"
            r"([0-9a-f]{40}) # v[0-9.]+$",
            workflow,
        )
    )

    assert run_commands == EXPECTED_COMMANDS
    assert actions == EXPECTED_ACTIONS
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == [
        "3.12",
        "3.13",
    ]
    assert 'java-version: "21"' in workflow
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert "persist-credentials: false" in workflow

    lowered = workflow.lower()
    for forbidden in (
        "contents: write",
        "write-all",
        "pull-requests:",
        "id-token:",
        "secrets.",
        "pyp" + "i",
        "tw" + "ine",
        "pub" + "lish",
        "dep" + "loy",
        "upload-" + "artifact",
    ):
        assert forbidden not in lowered


def test_package_configuration_lockfile_makefile_and_compiler_are_unchanged() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    for path, expected_hash in EXPECTED_FILES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.12"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert project["project"]["scripts"] == {"pietto": "pietto.cli:main"}
    assert "sqlglot" not in (REPO_ROOT / "pyproject.toml").read_text().lower()
    assert "sqlglot" not in (REPO_ROOT / "uv.lock").read_text().lower()

    groups = {
        "frontend": [
            REPO_ROOT / path
            for path in (
                "src/pietto/__init__.py",
                "src/pietto/ast_nodes.py",
                "src/pietto/ast_builder.py",
                "src/pietto/errors.py",
                "src/pietto/indentation.py",
                "src/pietto/parser_api.py",
            )
        ],
        "semantic": list((REPO_ROOT / "src/pietto/semantic").glob("*.py")),
        "ir": list((REPO_ROOT / "src/pietto/ir").glob("*.py")),
        "sql": list((REPO_ROOT / "src/pietto/sql").glob("*.py")),
        "generated": [
            path
            for path in (REPO_ROOT / "src/pietto/generated").iterdir()
            if path.is_file()
        ],
        "cli": [
            REPO_ROOT / "src/pietto/cli.py",
            REPO_ROOT / "src/pietto/cli_json.py",
        ],
    }
    for name, paths in groups.items():
        assert _aggregate_hash(paths) == EXPECTED_GROUPS[name]

    boundary_paths = [REPO_ROOT / path for path in EXPECTED_FILES]
    boundary_paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    assert _aggregate_hash(boundary_paths) == BOUNDARY_HASH


def test_postgres_mysql_and_json_v1_contracts_are_unchanged() -> None:
    golden_root = REPO_ROOT / "tests/fixtures/golden"

    for name, expected_hash in {**POSTGRES_GOLDENS, **MYSQL_GOLDENS}.items():
        assert _sha256(golden_root / name) == expected_hash
    assert _aggregate_hash(golden_root.iterdir()) == ALL_GOLDENS_HASH

    signature = inspect.signature(sql_api.emit_postgres_sql)
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
    assert cli_json._SCHEMA_VERSION == 1

    runtime_text = _runtime_text()
    assert "def emit_mysql_sql(" in runtime_text
    assert "def emit_sql(" not in runtime_text
    assert "schema_version = 2" not in runtime_text
    assert '"schema_version": 2' not in runtime_text


def test_deferred_sql_runtime_project_and_web_capabilities_remain_absent() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")
    cli_source = (REPO_ROOT / "src/pietto/cli.py").read_text(encoding="utf-8")
    runtime_text = _runtime_text(include_project_config=False).lower()

    assert "ORDER: 'order';" in grammar
    assert grammar.count("GROUP: 'group';") == 1
    assert grammar.count("WINDOW: 'window';") == 1
    assert grammar.count("PARTITION: 'partition';") == 1
    for token in (
        "JOIN:",
        "WITH:",
        "INSERT:",
        "UPDATE:",
        "DELETE:",
        "CREATE:",
        "ALTER:",
        "DROP:",
    ):
        assert token not in grammar
    for module_name in (
        "database.py",
        "executor.py",
        "lsp.py",
        "runtime.py",
        "server.py",
        "watch.py",
    ):
        assert not (REPO_ROOT / "src/pietto" / module_name).exists()

    assert '"--project"' in cli_source
    assert "def _run_project_check(" in cli_source
    assert "check_project_parse_only(root)" in cli_source
    assert not (REPO_ROOT / "pietto.toml").exists()
    assert "sqlglot" not in runtime_text
    assert "project_loader" not in runtime_text
    assert "load_project_config" not in runtime_text
    assert "compile_project" not in runtime_text
    for public_wrapper in ("def compile_to_ir(", "def compile_to_sql("):
        assert public_wrapper not in runtime_text


def test_repository_has_no_legacy_extension_or_bare_diagnostic_codes() -> None:
    repository_text = _repository_text()
    legacy_extension = re.compile(r"\." + "pie" + r"\b")
    bare_diagnostic = re.compile(r"(?<!PIE-)\bP[0-9]{4}\b")

    assert legacy_extension.search(repository_text) is None
    assert bare_diagnostic.search(repository_text) is None


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


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_blob_hash(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
