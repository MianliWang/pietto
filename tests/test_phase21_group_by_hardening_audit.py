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
        "97cfe87fdfe879790c1113f346e8cafab2b1da2b2ef668935f87adee5a70f397",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "655bfa5fd1bbc263f24f188a3526ab18657a1e1ab24c4ee18804416613166913",
    ),
    "parser_ast": (
        (
            "src/pietto/ast_builder.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/parser_api.py",
        ),
        3,
        "619441a62ac3efee6a1c1ec351f65753b08f1b32e7cdc3049f4b433b360ec0c8",
    ),
    "semantic": (
        "src/pietto/semantic",
        19,
        "2581eb50394d84ba506fc2a785a60da3549c071e541a8d0c39f8bb1f50a1bd68",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "a7af3fe9b002bb3e1a781f4962b44349b93f1baa098771c38b08bba44e3bcc7b",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "06e63e366434b792ae6a8da9d0c2e9443ab46446a58787715dafb635330729f4",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "af378ad655ed3ffc230983e94ee40cfef3b4f67e01d902901c5933c317c1f90f",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "857e4af82d9071f8a1cb8de2b5d48664950b52acdd16f4dfc82de3482b805e07",
    ),
    "fixtures": (
        "tests/fixtures",
        36,
        "58d091780585abefbac7ba986e3b997e3526350e95a7f303d7dcfec7485ef502",
    ),
    "readme": (
        "README.md",
        1,
        "2ee3e649c602a4a10c7b6b6a6b84ab38ae818dbfcc7c138bebfd34a0bc6cc6d3",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "876b37530852ac0b2d94a48d2d8582035fbf62b1999080c44699028ce8dea9df",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "057061e57a04f8585006a40da6c5aecc837ec7c1e0d216651ef35c6fc79d6f9a",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "df3f943f077769b54cd826dd18ebcdf82e153d2542f417c7e171b5ec4a7448d6",
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
        "9. **Slice 9: GROUP BY completion audit**: future final audit slice",
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
