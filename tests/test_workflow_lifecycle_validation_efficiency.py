from __future__ import annotations

from pathlib import Path

from _pietto_repository_facts import REPOSITORY_FACTS


TESTS_ROOT = Path(__file__).resolve().parent
POLICY_TEST = Path(__file__).resolve()


def _document_readers(filename: str) -> tuple[Path, ...]:
    readers: list[Path] = []
    for path in sorted(TESTS_ROOT.glob("test_*.py")):
        if path.resolve() == POLICY_TEST:
            continue
        literals = REPOSITORY_FACTS.python(path).string_literals
        if f"docs/{filename}" in literals or filename in literals:
            readers.append(path)
    return tuple(readers)


def test_no_test_reads_the_mutable_status_or_roadmap() -> None:
    assert _document_readers("status.md") == ()
    assert _document_readers("roadmap.md") == ()
