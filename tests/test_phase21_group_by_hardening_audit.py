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
        "443719b0a177373f57ede2229339d207830f02e464a59a2a0dde5f510e53e0c7",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "4aff21c78f68496cb909a0ff32b341424d40721c7d85c86e64cc4d4503769aad",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "0f78250ec5f5b73b620fd1f7753e0e311003ebe4afa45598541ec5eb59373ac0",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "af378ad655ed3ffc230983e94ee40cfef3b4f67e01d902901c5933c317c1f90f",
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
        "b1ea0970518eab155febcc4a613f2554def301c586378eaf94f552887073d3d4",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "92d33923c9268302cfb4f307f76329ed8cf60b967ad89389d52ebf7d62112c25",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "86bfaf4937e474511fb35ce7d5dc040b5c1ceb1ee5a139709a02f888132f860e",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "015f839539a699acf2026860c4316c07de6bed3aa623f16551bc10f5085575e0",
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
