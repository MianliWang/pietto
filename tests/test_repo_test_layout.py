from __future__ import annotations

from pathlib import Path
import re

from _pietto_repo_facts import REPOSITORY_FACTS


TESTS_ROOT = Path(__file__).resolve().parent
POLICY_TEST = Path(__file__).resolve()
LATER_PHASE = re.compile(r"phase(69|[7-9]\d|\d{3,})", re.IGNORECASE)
AREAS = frozenset(
    {
        "parser",
        "semantic",
        "project",
        "ir",
        "plan",
        "sql",
        "cli",
        "results",
        "execution",
        "jobs",
        "release",
        "ci",
        "repo",
        "harness",
    }
)
HISTORY_WORD = re.compile(
    r"(phase|slice|interlude|audit|readiness|lock|scaffold|skeleton|mvp|hardening"
    r"|candidate|decision|closure)s?\d*",
    re.IGNORECASE,
)
# Recorded exceptions to the naming law, by name.
NAMING_EXCEPTIONS = {
    "test_sql_emission_closure.py": "named by a ci/workloads.toml file_costs entry",
    "_pietto_differential_harness.py": "differential helper family",
    "_pietto_differential_probe_batch.py": "differential helper family",
    "_pietto_differential_process_acquisition.py": "differential helper family",
    "_pietto_differential_vectors.py": "differential helper family",
    "_pietto_target_conformance.py": "CI-invoked target conformance entry point",
    "_pietto_target_conformance_cases.py": "target conformance family",
    "_pietto_target_conformance_facility.py": "target conformance family",
    "_pietto_target_conformance_observation.py": "target conformance family",
    "_pietto_target_conformance_resources.py": "target conformance family",
    "_pietto_mysql_native_prepared.py": "loaded with the target conformance family",
}


def _document_readers(filename: str) -> tuple[Path, ...]:
    readers: list[Path] = []
    for path in sorted(TESTS_ROOT.glob("test_*.py")):
        if path.resolve() == POLICY_TEST:
            continue
        literals = REPOSITORY_FACTS.python(path).string_literals
        if f"docs/{filename}" in literals or filename in literals:
            readers.append(path)
    return tuple(readers)


def _breaks_naming_law(name: str) -> bool:
    words = name.removesuffix(".py").split("_")
    area = words[1] if name.startswith("test_") else words[2]
    return (
        area not in AREAS
        or any(HISTORY_WORD.fullmatch(word) for word in words)
        or LATER_PHASE.search(name) is not None
    )


def test_the_naming_law_reads_history_words_in_any_case_or_number() -> None:
    broken = [
        "test_parser_phase75_thing.py",
        "test_parser_slices.py",
        "test_cli_phases.py",
        "test_parser_route_locks.py",
        "test_sql_completion_audits.py",
        "_pietto_parser_interludes.py",
        "test_ir_decisions.py",
        "test_semantic_Phase75.py",
        "test_cli_Readiness.py",
    ]
    assert [name for name in broken if not _breaks_naming_law(name)] == []
    kept = ["test_parser_blocks.py", "test_cli_format.py", "_pietto_sql_locking.py"]
    assert [name for name in kept if _breaks_naming_law(name)] == []


def test_tests_and_helpers_are_named_by_area_without_history_words() -> None:
    paths = sorted(TESTS_ROOT.rglob("*.py"))
    # Every Python file under tests/ sits at its top level, where the law reads it.
    assert [path for path in paths if path.parent != TESTS_ROOT] == []
    names = [path.name for path in paths]
    assert "conftest.py" in names
    assert [
        name
        for name in names
        if name != "conftest.py" and not name.startswith(("test_", "_pietto_"))
    ] == []
    assert {
        name
        for name in names
        if name.startswith(("test_", "_pietto_")) and _breaks_naming_law(name)
    } == set(NAMING_EXCEPTIONS)


def test_no_test_reads_the_mutable_status_or_roadmap() -> None:
    assert _document_readers("status.md") == ()
    assert _document_readers("roadmap.md") == ()
