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
        "aec43ff6b9d0cac26cd2ec8f35856332ddbb70e4ca000b100dd8f41256c64eb6",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "b8867c8f4c2396936f607c616a81184c0f46071ba5d2db60b70a217db9719808",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "2fd6e7a45db95619a228150e26e2f78dfdcd1f24e72499780955c911c82221a2",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "af378ad655ed3ffc230983e94ee40cfef3b4f67e01d902901c5933c317c1f90f",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "f0be24787d872cf0c83a9e0d3621d0f071d01a100bf47f290344de80fccf042f",
    ),
    "fixtures": (
        "tests/fixtures",
        44,
        "d27e4dad84810a67c25250c52a034356e809f5c7ee1f4819a4475a944c7365d5",
    ),
    "readme": (
        "README.md",
        1,
        "fd5b3441a0499e21c5018f336bc64b05a68f1a4354d860c8e2b394f659c76815",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "3fa26c5ff2140c06b09c00b4e7e11f28a3d2da29607c680385c6d2ec9c9c71e5",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "1531df8d9673f308d5da012a299cfdb089b2254a7b91967f1e0b7c38deabd7d4",
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
