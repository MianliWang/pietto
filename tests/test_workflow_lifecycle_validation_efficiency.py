from __future__ import annotations

import ast
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
ACTIVE_READER = TESTS_ROOT / "test_active_phase_lifecycle.py"
POLICY = REPO_ROOT / "docs/spec/workflow-lifecycle-reader-validation-efficiency-v1.md"
DEVELOPMENT = REPO_ROOT / "docs/development.md"
POLICY_TEST = Path(__file__).resolve()

_MUTABLE_LIFECYCLE = re.compile(
    r"Phase 58 is active,.*(?:current|next / unstarted)"
    r"|PHASE58_SLICE\d+_END_TO_END"
    r'|\("Slice \d+", "`(?:CURRENT|NEXT / UNSTARTED)`"\)'
    r"|\| Slice \d+ \| `(?:CURRENT|NEXT / UNSTARTED)` \|"
    r"|does not authorize Slice \d+"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _product_tests() -> tuple[Path, ...]:
    return tuple(
        sorted(
            {
                *TESTS_ROOT.glob("test_phase56_*.py"),
                *TESTS_ROOT.glob("test_phase57_*.py"),
                *TESTS_ROOT.glob("test_phase58_slice*.py"),
                *TESTS_ROOT.glob("test_phase59_slice*.py"),
            }
        )
    )


def _document_readers(filename: str) -> tuple[Path, ...]:
    readers: list[Path] = []
    for path in sorted(TESTS_ROOT.glob("test_*.py")):
        if path.resolve() == POLICY_TEST:
            continue
        tree = ast.parse(_read(path), filename=str(path))
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if f"docs/{filename}" in literals or filename in literals:
            readers.append(path)
    return tuple(readers)


def test_active_lifecycle_reader_is_the_only_mutable_document_reader() -> None:
    assert _document_readers("status.md") == (ACTIVE_READER,)
    assert _document_readers("roadmap.md") == (ACTIVE_READER,)

    tree = ast.parse(_read(ACTIVE_READER), filename=str(ACTIVE_READER))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith("test_phase") for name in imported_modules)


def test_product_tests_have_no_mutable_lifecycle_or_roadmap_dependency() -> None:
    product_tests = _product_tests()
    assert product_tests
    status_readers = set(_document_readers("status.md"))
    roadmap_readers = set(_document_readers("roadmap.md"))
    for path in product_tests:
        source = _read(path)
        assert path not in status_readers
        assert path not in roadmap_readers
        assert _MUTABLE_LIFECYCLE.search(source) is None, path
        tree = ast.parse(source, filename=str(path))
        imported_modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        if path.name.startswith("test_phase59_"):
            assert ACTIVE_READER.stem not in imported_modules, path

    phase58_sources = "\n".join(
        _read(path) for path in product_tests if path.name.startswith("test_phase58_")
    )
    assert "LIFECYCLE_READERS" not in phase58_sources
    assert "EXPECTED_CHANGED_PATHS" not in phase58_sources


def test_layered_validation_policy_and_product_separation_are_locked() -> None:
    policy = _read(POLICY)
    dirty = " ".join(_section(policy, "Dirty Focused Validation").split())
    assert "current task tests" in dirty
    assert "changed historical tests" in dirty
    assert "changed-file Ruff" in dirty
    for skipped in (
        "full pytest",
        "scripts/validate.py",
        "full production Pyright",
        "generated audit",
        "golden audit",
        "package smoke",
    ):
        assert skipped in dirty

    authoritative = " ".join(_section(policy, "Authoritative Local Validation").split())
    assert "UV_PYTHON=3.13 uv run python scripts/validate.py --timings" in (
        authoritative
    )
    assert "exactly once" in authoritative

    auxiliary = " ".join(_section(policy, "Risk-gated Auxiliary Audits").split())
    for risk in ("generated surface", "golden-producing", "packaged module set"):
        assert risk in auxiliary

    ci = " ".join(_section(policy, "Natural CI").split())
    assert "Python 3.12 and 3.13" in ci
    assert "must not be weakened" in ci

    development = _read(DEVELOPMENT)
    assert "workflow-lifecycle-reader-validation-efficiency-v1.md" in development
    assert ACTIVE_READER.name not in {path.name for path in _product_tests()}
