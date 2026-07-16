from __future__ import annotations

import hashlib
import inspect
import tomllib
from pathlib import Path

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE11_PLAN = "docs/plan/phase-11-release-readiness-reproducible-validation.md"

FILE_HASHES = {
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
    ),
}

GROUP_HASHES = {
    "frontend": "7ecd994ab99d95af792ea628de9de236940c1c46ced49599ea482cffab49ee4f",
    "semantic": "30144bbd90085ecc82d8dfcdab2556e7396030eb80057d2fafd343e661b1ffc8",
    "ir": "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    "sql": "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    "generated": "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    "cli": "30e6e4cedfe91b4e52a5cad3e13b302a8617476c2a48dd92361e5fa5d6183019",
}


def test_phase11_master_plan_records_completed_slices_and_order() -> None:
    plan = _read(PHASE11_PLAN)

    assert "# Phase 11: Release Readiness & Reproducible Validation" in plan
    assert (
        "**Phase 11 Release Readiness & Reproducible Validation is complete.**" in plan
    )
    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "**Slice 2: Authoritative Validation Entry Point is complete.**" in plan
    assert "**Slice 3: ANTLR Provenance And Generated-File Guard is complete.**" in plan
    assert "**Slice 4: Golden Fixture Policy And Audit is complete.**" in plan
    assert "**Slice 5: GitHub Actions CI is complete.**" in plan
    assert "**Slice 6: Packaging And Installed CLI Smoke is complete.**" in plan
    assert "**Slice 7: Completion Audit And Documentation is complete.**" in plan

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
        assert "complete" in normalized
        assert PHASE11_PLAN in document

    combined = "\n".join(documents.values())
    assert "Phase 10 MySQL SQL Generation MVP is complete" in combined
    assert "Phase 12 SQL Feature Expansion I" in combined
    assert "require separate explicit" in combined


def test_python_floor_and_future_ci_matrix_are_explicit() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    plan = _read(PHASE11_PLAN)
    language_spec = _read("docs/spec/pietto-v0.9.md")
    normalized_plan = " ".join(plan.split())

    assert project["project"]["requires-python"] == ">=3.12"
    assert "Python 3.12 and Python 3.13" in normalized_plan
    assert "Python 3.12/3.13" in language_spec
    assert "does not by itself change" in normalized_plan


def test_slice6_adds_only_the_independent_packaging_smoke_artifact() -> None:
    assert tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / ".github/workflows").glob("*"))
        if path.is_file()
    ) == (".github/workflows/ci.yml",)
    assert tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "scripts").glob("*.py"))
    ) == (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "scripts/validate.py",
    )
    assert (REPO_ROOT / "tools" / "antlr-4.13.2-complete.jar.sha256").read_text(
        encoding="ascii"
    ) == ("eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76\n")

    plan = " ".join(_read(PHASE11_PLAN).split())
    for required in (
        "Slice 6 implements the independent package build, archive inspection, "
        "clean-install, and installed-CLI smoke",
        "uv run python scripts/package_smoke.py",
        "Slice 7 completes the cross-slice workflow",
        "does not publish, upload, sign, or change package metadata",
    ):
        assert required in plan
    assert (REPO_ROOT / "docs/spec/golden-fixture-policy-v1.md").is_file()


def test_phase11_does_not_authorize_makefile_integration_by_default() -> None:
    plan = " ".join(_read(PHASE11_PLAN).split())

    assert "does not add or modify Makefile targets by default" in plan
    assert (
        "Makefile integration is allowed only when the repository already "
        "contains a Makefile and that integration receives separate explicit "
        "authorization, or when the user explicitly requests it in a later slice"
        in plan
    )
    assert (
        plan.count(
            "must not add or modify Makefile targets unless separately and explicitly "
            "authorized under the Phase 11 Makefile policy"
        )
        == 2
    )


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


def test_deferred_capabilities_remain_absent_after_phase12_feature_expansion() -> None:
    grammar = _read("grammar/Pietto.g4")
    parser_tests = _read("tests/test_parser_relations.py")
    cli_source = _read("src/pietto/cli.py")
    plan = _read(PHASE11_PLAN)

    assert "ORDER: 'order';" in grammar
    assert "BY: 'by';" in grammar
    assert "ASC: 'asc';" in grammar
    assert "DESC: 'desc';" in grammar
    assert "LIMIT: 'limit';" in grammar
    assert '"    order by id\\n"' in parser_tests

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

    assert '"--project"' in cli_source
    assert "def _run_project_check(" in cli_source
    assert "check_project_parse_only(root)" in cli_source
    assert not (REPO_ROOT / "pietto.toml").exists()
    assert "compile_project" not in cli_source
    assert "load_project_config" not in cli_source
    assert "project_loader" not in cli_source
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
