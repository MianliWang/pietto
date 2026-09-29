"""Independent observations and actual migrated-reader mutation boundaries."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from _pietto_repository_facts import RepositoryFactIndex
import test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock as scanner

ROOT = Path(__file__).resolve().parents[1]


def _reference(index, path):
    # Independent legacy acquisition: never reads a shared derivation.
    text = path.read_text(encoding="utf-8")
    assert index.text(path) == text
    assert index.lowercase(text) == text.lower()
    tree = ast.parse(text)
    expected = frozenset(
        {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        | {
            n.name.rsplit(".", 1)[-1]
            for n in ast.walk(tree)
            if isinstance(n, ast.alias)
        }
    )
    assert expected == index.python(path).identifiers
    expected_imports = frozenset(
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    )
    expected_imports |= frozenset(
        n.module
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module is not None
    )
    assert expected_imports == index.python(path).imported_modules


def test_text_capture_does_not_parse_and_python_shares_successful_read(
    tmp_path, monkeypatch
):
    path = tmp_path / "module.py"
    path.write_text("import os\nVALUE: int = 1\n")
    index = RepositoryFactIndex.snapshot(tmp_path)
    original_read, original_parse = Path.read_text, ast.parse
    counts = [0, 0]

    def read(subject, *a, **kw):
        counts[0] += 1
        return original_read(subject, *a, **kw)

    def parse(*a, **kw):
        counts[1] += 1
        return original_parse(*a, **kw)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(ast, "parse", parse)
    assert index.text(path) == "import os\nVALUE: int = 1\n"
    assert counts == [1, 0]
    assert index.python(path).top_level_assigned_names == {"VALUE"}
    assert index.python(path) is index.python(path)
    assert counts == [1, 1]


def test_malformed_text_and_failed_python_capture_keep_distinct_contracts(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("def incomplete(\n")
    index = RepositoryFactIndex.snapshot(tmp_path)
    with pytest.raises(SyntaxError):
        index.python(path)
    assert not index._python_by_path and not index._text_by_path
    path.write_text("RECOVERED = True\n")
    assert index.python(path).identifiers == {"RECOVERED"}
    path.write_text("not valid python (\n")
    text_index = RepositoryFactIndex.snapshot(tmp_path)
    assert text_index.text(path) == path.read_text()
    with pytest.raises(SyntaxError):
        text_index.python(path)
    path.write_text("FRESH = 2\n")
    assert text_index.text(path) == "not valid python (\n"
    assert RepositoryFactIndex.snapshot(tmp_path).python(path).identifiers == {"FRESH"}


def test_fresh_namespace_observes_added_removed_changed_and_explicit_ignored(tmp_path):
    path = tmp_path / "one.py"
    nested = tmp_path / "nested"
    nested.mkdir()
    path.write_text("ONE = 1\n")
    (nested / "one.py").write_text("NESTED = 2\n")
    (tmp_path / ".gitignore").write_text("ignored.py\n")
    ignored = tmp_path / "ignored.py"
    ignored.write_text("IGNORED = 3\n")
    first = RepositoryFactIndex.snapshot(tmp_path)
    assert tuple(first.text(p) for p in (ignored, path)) == (
        "IGNORED = 3\n",
        "ONE = 1\n",
    )
    assert set(tmp_path.glob("*.py")) == {path, ignored}
    assert set(tmp_path.rglob("*.py")) == {path, ignored, nested / "one.py"}
    path.write_text("CHANGED = 4\n")
    ignored.unlink()
    added = tmp_path / "added.py"
    added.write_text("ADDED = 5\n")
    second = RepositoryFactIndex.snapshot(tmp_path)
    assert first.text(path) == "ONE = 1\n"
    assert set(tmp_path.glob("*.py")) == {path, added}
    assert [second.text(p) for p in (added, path)] == ["ADDED = 5\n", "CHANGED = 4\n"]
    with pytest.raises(FileNotFoundError):
        second.text(ignored)
    assert ignored not in second._text_by_path


def test_copied_roots_lexical_aliases_and_symlinks_do_not_fall_back(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "one.py").write_text("ORIGINAL = 1\n")
    relocated = tmp_path / "relocated"
    shutil.copytree(source, relocated)
    (source / "one.py").write_text("CHANGED = 2\n")
    a, b = RepositoryFactIndex.snapshot(source), RepositoryFactIndex.snapshot(relocated)
    assert a.text(source / "one.py") != b.text(relocated / "one.py")
    with pytest.raises(ValueError):
        b.text(source / "one.py")
    link = relocated / "same.py"
    link.symlink_to(source / "one.py")
    assert b.text(link) == link.read_text() == "CHANGED = 2\n"
    assert link in b._text_by_path and relocated / "one.py" in b._text_by_path
    with pytest.raises(ValueError):
        b.python(link)  # The pre-existing resolved Python-root restriction remains.
    with pytest.raises(ValueError):
        b.text(relocated / ".." / "source" / "one.py")


@pytest.mark.parametrize(
    "texts",
    [
        [],
        ["psy", "copg"],
        ["# PSYCOPG\n", "safe"],
        ['value = "server_version"'],
        ["Straße İ\n", "x\r\ny"],
    ],
)
def test_lowercase_substring_observation_matches_independent_join(tmp_path, texts):
    index = RepositoryFactIndex.snapshot(tmp_path)
    needles = (
        "create extension",
        "pg_extension",
        "server_version",
        "psycopg",
        "asyncpg",
        "extension_catalog",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    )
    for needle in needles:
        assert needle and "\n" not in needle
        assert (needle in "\n".join(texts).lower()) == any(
            needle in index.lowercase(text) for text in texts
        )
    assert index.lowercase("Straße") == "straße" != "Straße".casefold()
    assert "psy\ncopg" in "\n".join(["psy", "copg"]).lower()
    assert not any("psy\ncopg" in index.lowercase(t) for t in ["psy", "copg"])


def test_independent_reference_detects_corrupt_or_omitted_facts(tmp_path):
    path = tmp_path / "one.py"
    path.write_text("import os\nVALUE = 'PSYCOPG'\n")
    for damage in ("text", "lower", "identifiers", "imports", "extra_identifier"):
        index = RepositoryFactIndex.snapshot(tmp_path)
        _reference(index, path)
        fact = index.python(path)
        if damage == "text":
            index._text_by_path[path] = ""
        elif damage == "lower":
            index._lower_by_text[fact.text] = ""
        elif damage == "identifiers":
            index._python_by_path[path] = replace(fact, identifiers=frozenset())
        elif damage == "imports":
            index._python_by_path[path] = replace(fact, imported_modules=frozenset())
        else:
            index._python_by_path[path] = replace(
                fact, identifiers=fact.identifiers | {"spurious"}
            )
        with pytest.raises(AssertionError):
            _reference(index, path)


def test_actual_scanner_overlay_is_visible_after_warming_without_leakage(monkeypatch):
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    path = ROOT / "src/pietto/_project/project_execution.py"
    original = scanner._read
    for token in ("psycopg", "server_version"):
        with monkeypatch.context() as patch:

            def injected(subject):
                value = original(subject)
                return value + "\n" + token.upper() if subject == path else value

            patch.setattr(scanner, "_read", injected)
            with pytest.raises(AssertionError) as exc:
                scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
            assert token in str(exc.value) and path.name in str(exc.value)
        scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    with monkeypatch.context() as patch:
        # Conflicting overlays compose at the actual read seam; none can reuse
        # an earlier policy success or contaminate the base's captured bytes.
        patch.setattr(
            scanner,
            "_read",
            lambda subject: (
                original(subject) + ("\nPSYCOPG\nASYNCpg" if subject == path else "")
            ),
        )
        with pytest.raises(AssertionError, match="psycopg"):
            scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()


def test_actual_scanner_detects_removed_namespace_member_after_warming(monkeypatch):
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    removed = ROOT / "src/pietto/semantic/extension_catalog.py"
    original = Path.rglob

    def paths(directory, pattern):
        for path in original(directory, pattern):
            if path != removed:
                yield path

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rglob", paths)
        with pytest.raises(AssertionError):
            scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()


def test_old_negative_control_exposes_corrupted_shared_lowercase(monkeypatch):
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    with monkeypatch.context() as patch:
        patch.setattr(
            RepositoryFactIndex,
            "lowercase",
            lambda self, text: text.lower().replace("psycopg", ""),
        )
        # The original injected-negative assertion must itself fail when its
        # observation is corrupted; this is not another shared PASS oracle.
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            scanner.test_execution_permission_is_path_and_purpose_limited(
                patch, "project_execution.py", "psycopg"
            )
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()


def test_original_positional_index_constructor_contract(tmp_path):
    path = tmp_path / "one.py"
    path.write_text("ONE = 1\n")
    fact = RepositoryFactIndex.snapshot(tmp_path).python(path)
    cache = {path: fact}
    index = RepositoryFactIndex(tmp_path, cache)
    assert index.python(path) is fact and index._python_by_path is cache


def test_phase_end_procedure_uses_current_owners_before_audit_only_closeout():
    development = (ROOT / "docs/development.md").read_text()
    procedure = development.split("## Phase-end acquisition consolidation\n", 1)[
        1
    ].split("\n## ", 1)[0]
    for requirement in (
        "rerun independent assertions",
        "actual Phase baseline",
        "audit-only",
        "memory",
        "remaining debt",
        "low-value",
        "scope/budget",
        "ci_workload",
        "ci/workloads.toml",
        "does not require a CI health alert",
    ):
        assert requirement in procedure
    for relative in (
        "docs/architecture/phase-initiation-gate-v1.md",
        "docs/architecture/ci-workload-governance-v1.md",
    ):
        document = (ROOT / relative).read_text()
        assert "development.md#phase-end-acquisition-consolidation" in document
        assert "audit-only" in document
        assert "另行授权" in document or "单独授权" in document


def test_actual_scanner_does_not_choose_last_duplicate_path_overlay(monkeypatch):
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
    path = ROOT / "src/pietto/_project/project_execution.py"
    original_paths, original_read = Path.rglob, scanner._read
    seen = []

    def duplicated(directory, pattern):
        yield from original_paths(directory, pattern)
        if directory == ROOT / "src/pietto" and pattern == "*.py":
            yield path

    def conflicting(subject):
        value = original_read(subject)
        if subject == path:
            seen.append(subject)
            if len(seen) == 1:
                return value + "\nASYNCpg"
        return value

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rglob", duplicated)
        patch.setattr(scanner, "_read", conflicting)
        with pytest.raises(AssertionError, match="asyncpg"):
            scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
        assert seen == [path, path]
    scanner.test_private_catalog_foundation_has_no_concrete_runtime_or_public_behavior()
