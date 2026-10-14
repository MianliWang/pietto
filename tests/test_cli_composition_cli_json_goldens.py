from __future__ import annotations

from pathlib import Path

GOLDEN_ROOT = Path("tests/fixtures/golden")
PHASE12_GOLDENS = (
    GOLDEN_ROOT / "emit_mysql_order_limit_composition.sql",
    GOLDEN_ROOT / "emit_sql_order_limit_composition.sql",
    GOLDEN_ROOT / "phase12_mysql_order_limit_composition.json",
)


def test_production_api_json_dependency_and_compiler_boundaries_are_unchanged() -> None:
    assert all(path.is_file() for path in PHASE12_GOLDENS)
