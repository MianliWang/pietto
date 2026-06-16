"""Audit golden fixture classification, ownership, and JSON validity."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = Path("tests/fixtures/golden")

SQL_FIXTURES = frozenset(
    {
        "emit_mysql_count_aggregate.sql",
        "emit_mysql_compatibility_expressions.sql",
        "emit_mysql_compatibility_literals_identifiers.sql",
        "emit_mysql_compatibility_ordering_metadata.sql",
        "emit_mysql_order_limit_composition.sql",
        "emit_mysql_sum_avg_aggregate.sql",
        "emit_sql_active_user_emails.sql",
        "emit_sql_active_users.sql",
        "emit_sql_count_aggregate.sql",
        "emit_sql_compatibility_expressions.sql",
        "emit_sql_compatibility_literals_identifiers.sql",
        "emit_sql_compatibility_ordering_metadata.sql",
        "emit_sql_order_limit_composition.sql",
        "emit_sql_sum_avg_aggregate.sql",
    }
)
JSON_FIXTURES = frozenset(
    {
        "check_sources_users_warning.json",
        "check_types.json",
        "emit_mysql_compatibility_ordering_metadata.json",
        "emit_sql_active_users.json",
        "phase12_mysql_order_limit_composition.json",
    }
)
CLASSIFIED_FIXTURES = SQL_FIXTURES | JSON_FIXTURES

FIXTURE_INPUTS: dict[str, tuple[str, ...]] = {
    "check_sources_users_warning.json": ("examples/sources/users.pietto",),
    "check_types.json": ("examples/basic/types.pietto",),
    "emit_mysql_compatibility_expressions.sql": (
        "tests/fixtures/mysql/compatibility_expressions.pietto",
    ),
    "emit_mysql_compatibility_literals_identifiers.sql": (
        "tests/fixtures/mysql/compatibility_literals_identifiers.pietto",
    ),
    "emit_mysql_compatibility_ordering_metadata.json": (
        "tests/fixtures/mysql/compatibility_ordering_metadata.pietto",
    ),
    "emit_mysql_compatibility_ordering_metadata.sql": (
        "tests/fixtures/mysql/compatibility_ordering_metadata.pietto",
    ),
    "emit_mysql_count_aggregate.sql": (
        "tests/fixtures/phase19/mysql_count_aggregate.pietto",
    ),
    "emit_mysql_order_limit_composition.sql": (
        "tests/fixtures/phase12/mysql_order_limit_composition.pietto",
    ),
    "emit_mysql_sum_avg_aggregate.sql": (
        "tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto",
    ),
    "emit_sql_active_user_emails.sql": ("examples/queries/active_user_emails.pietto",),
    "emit_sql_active_users.json": ("examples/tables/active_users.pietto",),
    "emit_sql_active_users.sql": ("examples/tables/active_users.pietto",),
    "emit_sql_count_aggregate.sql": (
        "tests/fixtures/phase19/postgres_count_aggregate.pietto",
    ),
    "emit_sql_compatibility_expressions.sql": (
        "tests/fixtures/postgres/compatibility_expressions.pietto",
    ),
    "emit_sql_compatibility_literals_identifiers.sql": (
        "tests/fixtures/postgres/compatibility_literals_identifiers.pietto",
    ),
    "emit_sql_compatibility_ordering_metadata.sql": (
        "tests/fixtures/postgres/compatibility_ordering_metadata.pietto",
    ),
    "emit_sql_order_limit_composition.sql": (
        "tests/fixtures/phase12/postgres_order_limit_composition.pietto",
    ),
    "emit_sql_sum_avg_aggregate.sql": (
        "tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto",
    ),
    "phase12_mysql_order_limit_composition.json": (
        "tests/fixtures/phase12/mysql_order_limit_composition.pietto",
    ),
}

REFERENCE_TESTS = (
    Path("tests/test_cli_golden_outputs.py"),
    Path("tests/test_phase10_mysql_cli_enablement.py"),
    Path("tests/test_phase10_mysql_golden_corpus.py"),
    Path("tests/test_phase12_composition_cli_json_goldens.py"),
    Path("tests/test_phase19_count_sql.py"),
    Path("tests/test_phase20_sum_avg_sql.py"),
)


def _fixture_inventory(golden_root: Path) -> frozenset[str]:
    try:
        return frozenset(path.name for path in golden_root.iterdir() if path.is_file())
    except OSError:
        return frozenset()


def _fixture_reference(value: str) -> str | None:
    prefix = f"{GOLDEN_ROOT.as_posix()}/"
    if value.startswith(prefix):
        reference = value.removeprefix(prefix)
        return reference if "/" not in reference else None
    if "/" not in value and value in CLASSIFIED_FIXTURES:
        return value
    return None


def _collect_references(
    repo_root: Path,
    reference_tests: tuple[Path, ...] = REFERENCE_TESTS,
) -> tuple[frozenset[str], tuple[str, ...]]:
    references: set[str] = set()
    errors: list[str] = []

    for relative_path in reference_tests:
        path = repo_root / relative_path
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            errors.append(f"cannot inspect owning test {relative_path}: {error}")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            reference = _fixture_reference(node.value)
            if reference is not None:
                references.add(reference)

    return frozenset(references), tuple(errors)


def _inventory_errors(
    inventory: frozenset[str],
    references: frozenset[str],
) -> tuple[str, ...]:
    errors: list[str] = []
    missing = sorted(CLASSIFIED_FIXTURES - inventory)
    unclassified = sorted(inventory - CLASSIFIED_FIXTURES)
    missing_references = sorted(references - inventory)
    orphaned = sorted(inventory - references)

    if missing:
        errors.append(f"missing classified fixtures: {', '.join(missing)}")
    if unclassified:
        errors.append(f"unclassified golden files: {', '.join(unclassified)}")
    if missing_references:
        errors.append(
            f"owning tests reference missing fixtures: {', '.join(missing_references)}"
        )
    if orphaned:
        errors.append(f"orphan golden files: {', '.join(orphaned)}")
    return tuple(errors)


def _input_errors(repo_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    unmapped = sorted(CLASSIFIED_FIXTURES - FIXTURE_INPUTS.keys())
    extra_mappings = sorted(FIXTURE_INPUTS.keys() - CLASSIFIED_FIXTURES)

    if unmapped:
        errors.append(f"fixtures without reviewed Pietto inputs: {', '.join(unmapped)}")
    if extra_mappings:
        errors.append(
            f"input mappings for unclassified fixtures: {', '.join(extra_mappings)}"
        )

    for fixture, inputs in sorted(FIXTURE_INPUTS.items()):
        if not inputs:
            errors.append(f"fixture has no reviewed Pietto input: {fixture}")
        for input_path in inputs:
            if not (repo_root / input_path).is_file():
                errors.append(f"missing Pietto input for {fixture}: {input_path}")
    return tuple(errors)


def _fixture_content_errors(golden_root: Path) -> tuple[str, ...]:
    errors: list[str] = []

    for fixture in sorted(SQL_FIXTURES):
        try:
            (golden_root / fixture).read_bytes()
        except OSError as error:
            errors.append(f"cannot read SQL fixture {fixture}: {error}")

    for fixture in sorted(JSON_FIXTURES):
        try:
            content = (golden_root / fixture).read_text(encoding="utf-8")
            json.loads(content)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append(f"invalid JSON fixture {fixture}: {error}")

    return tuple(errors)


def audit(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    """Return all golden audit errors without modifying repository files."""

    golden_root = repo_root / GOLDEN_ROOT
    inventory = _fixture_inventory(golden_root)
    references, reference_errors = _collect_references(repo_root)
    return (
        *reference_errors,
        *_inventory_errors(inventory, references),
        *_input_errors(repo_root),
        *_fixture_content_errors(golden_root),
    )


def main() -> int:
    """Run the golden fixture audit and report a nonzero status on errors."""

    errors = audit()
    if errors:
        for error in errors:
            print(f"[goldens] error: {error}", file=sys.stderr)
        return 1

    print(
        f"[goldens] verified {len(CLASSIFIED_FIXTURES)} fixtures: "
        f"{len(SQL_FIXTURES)} SQL byte-exact, "
        f"{len(JSON_FIXTURES)} JSON structural; no missing or orphan fixtures",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
