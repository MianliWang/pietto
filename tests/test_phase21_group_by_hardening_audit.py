from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"

GROUPED_FIXTURES = {
    "mysql_group_by_aggregate.pietto",
    "postgres_group_by_aggregate.pietto",
}
GROUPED_SQL_GOLDENS = {
    "emit_mysql_group_by_aggregate.sql",
    "emit_sql_group_by_aggregate.sql",
}

LOCKED_FORBIDDEN_SURFACES = {
    "grammar": (
        "grammar",
        1,
        "4078b89d21126706746e07052ac8870a70f7275bd02dfc0433552f5edf06c082",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "parser_ast": (
        (
            "src/pietto/ast_builder.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/parser_api.py",
        ),
        3,
        "6c2ee7dc25365c5ab4097de4b7e6c4949b49446e6555eae19a99395c0d2f7f55",
    ),
    "semantic": (
        "src/pietto/semantic",
        20,
        "ee02e4084d1ddd3c37e359d879a9daad31ae47272a3e0b42fe6f8aa4cde2be28",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "63e99f989500f83686963fba853fed27d76bc5e0c0ac2e58827fb336b2bb044a",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "59c3921f21de398e06f6deca28f18871120bbf411110974c3df6ba7fa85970c4",
    ),
    "fixtures": (
        "tests/fixtures",
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "readme": (
        "README.md",
        1,
        "a9012c03259cc7d8cb983f70fcd6481719f06ead73a0decbea7f7a4f76b55ac2",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "140af85301e560bcf13481c589e99c039e734a47d0ebc9d2787b7062d948031d",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "8c5f7ae8e5f6bbcbe7c004e681ba4bf8e417efb62240137f83ccd6d5a8472b39",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "0c82aa6cde14aac504cca5028f28365c1127e59a748827a2108ced224bbbd7a4",
    ),
    "pyproject": (
        "pyproject.toml",
        1,
        "cf5894a9cb7ef0399126a7d424da4e3958fc92d8e6bed295939a6e6bac469099",
    ),
    "uv_lock": (
        "uv.lock",
        1,
        "b48bb27656ff3344a95ba92347f45173904801cd8bdccfd2b55106549c445ac0",
    ),
    "github": (
        ".github",
        1,
        "129f96212b5025e66254b2485195977770cf7765bd8977215c6dfaefd9e6e5ae",
    ),
}


def test_grouped_phase21_fixtures_and_goldens_are_the_reviewed_set() -> None:
    phase21_fixtures = {
        path.name for path in (FIXTURE_ROOT / "phase21").iterdir() if path.is_file()
    }
    grouped_goldens = {
        path.name
        for path in GOLDEN_ROOT.iterdir()
        if path.is_file() and "group_by" in path.name
    }

    assert phase21_fixtures == GROUPED_FIXTURES
    assert grouped_goldens == GROUPED_SQL_GOLDENS
    for golden in GROUPED_SQL_GOLDENS:
        sql = (GOLDEN_ROOT / golden).read_text(encoding="utf-8")
        assert "GROUP BY" in sql
        assert "COUNT(*)" in sql


def test_check_goldens_inventory_owns_only_slice7_grouped_goldens() -> None:
    source = CHECK_GOLDENS_PATH.read_text(encoding="utf-8")

    for required in (
        '"emit_sql_group_by_aggregate.sql"',
        '"emit_mysql_group_by_aggregate.sql"',
        '"tests/fixtures/phase21/postgres_group_by_aggregate.pietto"',
        '"tests/fixtures/phase21/mysql_group_by_aggregate.pietto"',
        'Path("tests/test_phase21_group_by_sql_lowering.py")',
    ):
        assert required in source
    assert "tests/test_phase21_group_by_cli_hardening.py" not in source
    assert "tests/test_phase21_group_by_hardening_audit.py" not in source


def test_slice8_status_and_tests_only_boundaries_are_documented() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")

    for required in (
        "Phase 21 Slice 8 is complete as CLI, invalid-shape, malformed IR, and no-regression hardening",
        "Slice 8 is tests/audit-only and adds no production behavior",
        "It adds no fixtures, SQL/JSON goldens, `scripts/check_goldens.py` inventory changes, diagnostics, public API, dependency, lockfile, CI, runtime, database, UI, LSP, or policy DSL behavior",
        "Slice 8 adds no grouped `order by`, HAVING user syntax, `satisfying`, `filter`, JOIN, relationship-driven query behavior, aggregate expression arguments, Decimal aggregate semantics, casts, SQLGlot, or runtime/database execution",
        "8. **Slice 8: CLI / invalid-shape hardening / no-regression checks**: complete.",
        "9. **Slice 9: GROUP BY completion audit**: complete final audit slice",
    ):
        assert required in plan


def test_slice8_forbidden_implementation_surfaces_are_unchanged() -> None:
    for _name, (
        path_or_paths,
        expected_count,
        expected_hash,
    ) in LOCKED_FORBIDDEN_SURFACES.items():
        paths = _paths(path_or_paths)
        assert len(paths) == expected_count
        assert _digest(paths) == expected_hash


def _paths(path_or_paths: str | tuple[str, ...]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, tuple):
        return tuple(REPO_ROOT / path for path in path_or_paths)

    path = REPO_ROOT / path_or_paths
    if path.is_file():
        return (path,)
    return tuple(
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and "__pycache__" not in item.parts
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix().encode()
        digest.update(relative + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
