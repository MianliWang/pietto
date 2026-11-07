from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
import shutil
import subprocess

import pytest

from _pietto_repo_facts import (
    PythonSourceFacts,
    REPOSITORY_FACTS,
    RepositoryFactIndex,
)
import _pietto_project_extension_scope as scanner


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "tests/_pietto_repo_facts.py"
MIGRATED_OWNER_PATHS = tuple(
    REPO_ROOT / path
    for path in (
        "tests/test_repo_test_layout.py",
        "tests/test_semantic_aggregate_signature_algebra_facts.py",
        "tests/test_semantic_expression_stage_clause_capability_facts.py",
        "tests/test_semantic_fail_closed_capability_lookup.py",
        "tests/test_semantic_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_semantic_capability_fact_parity.py",
        "tests/test_semantic_capability_facts.py",
        "tests/test_semantic_scalar_function_operator_signature_facts.py",
    )
)


def _legacy_imports(tree: ast.Module) -> frozenset[str]:
    return frozenset(
        {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
    )


def _legacy_identifiers(tree: ast.Module) -> frozenset[str]:
    return frozenset(
        {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        | {
            node.name.rsplit(".", 1)[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.alias)
        }
    )


def _legacy_top_level_assigned_names(tree: ast.Module) -> frozenset[str]:
    return frozenset(
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Name)
    )


def _assign_only_call_facts(
    tree: ast.Module,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    return tuple(
        (
            tuple(
                target.id if isinstance(target, ast.Name) else ast.dump(target)
                for target in node.targets
            ),
            node.value.func.id,
        )
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    )


def test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition() -> None:
    corpus = (
        *sorted((REPO_ROOT / "src/pietto").rglob("*.py")),
        *(
            REPO_ROOT / path
            for path in (
                "tests/test_repo_test_layout.py",
                "tests/test_semantic_fail_closed_capability_lookup.py",
                "tests/test_semantic_capability_facts.py",
            )
        ),
    )
    for path in corpus:
        shared = REPOSITORY_FACTS.python(path)
        legacy_text = path.read_text(encoding="utf-8")
        legacy_tree = ast.parse(legacy_text, filename=str(path))
        assert shared.text == legacy_text
        assert shared.string_literals == frozenset(
            node.value
            for node in ast.walk(legacy_tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        assert shared.imported_modules == _legacy_imports(legacy_tree)
        assert shared.identifiers == _legacy_identifiers(legacy_tree)
        assert shared.top_level_assigned_names == _legacy_top_level_assigned_names(
            legacy_tree
        )


def test_facts_are_frozen_and_contain_no_policy_or_result_state() -> None:
    expected_fields = (
        "path",
        "text",
        "string_literals",
        "imported_modules",
        "identifiers",
        "top_level_assigned_names",
    )
    assert tuple(item.name for item in fields(PythonSourceFacts)) == expected_fields
    assert REPOSITORY_FACTS.root == REPO_ROOT
    fact = REPOSITORY_FACTS.python(HELPER)
    assert REPOSITORY_FACTS.python(HELPER) is fact
    with pytest.raises(FrozenInstanceError):
        fact.text = "changed"  # type: ignore[misc]
    assert not {"allowed", "forbidden", "status", "result", "phase"} & {
        item.name for item in fields(PythonSourceFacts)
    }


def test_mutation_requires_a_fresh_explicit_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "module.py"
    source.write_text("VALUE = 'first'\n", encoding="utf-8")
    first = RepositoryFactIndex.snapshot(tmp_path)
    assert first.python(source).text == "VALUE = 'first'\n"

    source.write_text("VALUE = 'second'\n", encoding="utf-8")
    second = RepositoryFactIndex.snapshot(tmp_path)
    assert first.python(source).text == "VALUE = 'first'\n"
    assert second.python(source).text == "VALUE = 'second'\n"
    with pytest.raises(ValueError):
        first.python(REPO_ROOT / "pyproject.toml")


def test_owner_ast_universes_match_legacy_and_keep_assign_only_order(
    tmp_path: Path,
) -> None:
    source = tmp_path / "owner.py"
    source.write_text(
        "PLAIN = CapabilityPlain()\n"
        "ANNOTATED: object = CapabilityAnnotated()\n"
        "FIRST = SECOND = CapabilityShared()\n"
        "LATER = CapabilityLater()\n",
        encoding="utf-8",
    )
    index = RepositoryFactIndex.snapshot(tmp_path)
    direct_tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    shared_tree = ast.parse(index.python(source).text, filename=str(source))

    assert ast.dump(shared_tree) == ast.dump(direct_tree)
    assert (
        _assign_only_call_facts(shared_tree)
        == _assign_only_call_facts(direct_tree)
        == (
            (("PLAIN",), "CapabilityPlain"),
            (("FIRST", "SECOND"), "CapabilityShared"),
            (("LATER",), "CapabilityLater"),
        )
    )
    assert any(isinstance(node, ast.AnnAssign) for node in shared_tree.body)
    assert index.python(source).top_level_assigned_names == {
        "PLAIN",
        "ANNOTATED",
        "FIRST",
        "SECOND",
        "LATER",
    }


def test_owner_path_universes_preserve_glob_rglob_and_explicit_order(
    tmp_path: Path,
) -> None:
    direct = tmp_path / "test_phase59_slice_direct.py"
    direct.write_text("VALUE = 'direct'\n", encoding="utf-8")
    nested_root = tmp_path / "nested"
    nested_root.mkdir()
    nested = nested_root / "test_phase59_slice_nested.py"
    nested.write_text("VALUE = 'nested'\n", encoding="utf-8")
    explicit = tmp_path / "explicit.py"
    explicit.write_text("VALUE = 'explicit'\n", encoding="utf-8")
    index = RepositoryFactIndex.snapshot(tmp_path)

    non_recursive = tuple(sorted(tmp_path.glob("test_phase59_slice*.py")))
    assert tuple(index.python(path).path for path in non_recursive) == (direct,)
    assert nested not in non_recursive

    recursive = tuple(tmp_path.rglob("*.py"))
    assert tuple(index.python(path).path for path in recursive) == recursive

    explicit_inventory = (nested, explicit, direct)
    assert tuple(index.python(path).path for path in explicit_inventory) == (
        nested,
        explicit,
        direct,
    )


def test_explicit_owner_paths_are_not_filtered_by_shared_acquisition(
    tmp_path: Path,
) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    ignored = tmp_path / "ignored.py"
    ignored.write_text("VALUE = 'owner selected'\n", encoding="utf-8")

    owner_paths = tuple(tmp_path.rglob("*.py"))
    assert owner_paths == (ignored,)
    index = RepositoryFactIndex.snapshot(tmp_path)
    assert tuple(index.python(path).path for path in owner_paths) == owner_paths


def test_migrated_owner_sources_do_not_mutate_snapshot_files() -> None:
    mutating_methods = {"write_text", "write_bytes", "unlink", "rename", "replace"}
    for path in MIGRATED_OWNER_PATHS:
        tree = ast.parse(REPOSITORY_FACTS.python(path).text, filename=str(path))
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in mutating_methods
            for node in ast.walk(tree)
        ), path
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
            ):
                continue
            mode = node.args[1] if len(node.args) > 1 else None
            if mode is None:
                mode = next(
                    (
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "mode"
                    ),
                    None,
                )
            assert not (
                isinstance(mode, ast.Constant)
                and isinstance(mode.value, str)
                and set(mode.value) & set("wax+")
            ), path


def test_relocated_snapshot_and_access_order_preserve_facts(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    relocated_root = tmp_path / "relocated"
    source_root.mkdir()
    original = source_root / "one.py"
    original.write_text("import os\nVALUE = 'one'\n", encoding="utf-8")
    second = source_root / "two.py"
    second.write_text("import sys\nVALUE = 'two'\n", encoding="utf-8")
    shutil.copytree(source_root, relocated_root)

    source_index = RepositoryFactIndex.snapshot(source_root)
    relocated_index = RepositoryFactIndex.snapshot(relocated_root)
    source_fact = source_index.python(original)
    relocated_fact = relocated_index.python(relocated_root / "one.py")
    assert source_fact.text == relocated_fact.text
    assert source_fact.imported_modules == relocated_fact.imported_modules
    assert source_fact.identifiers == relocated_fact.identifiers

    source_paths = (original, second)
    forward = tuple(source_index.python(path).text for path in source_paths)
    reverse_index = RepositoryFactIndex.snapshot(source_root)
    reverse = tuple(reverse_index.python(path).text for path in reversed(source_paths))
    assert forward == tuple(reversed(reverse))


def test_helper_contains_acquisition_only() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    for forbidden in (
        "expected lifecycle",
        "allowed consumer",
        "forbidden import",
        "pytest result",
    ):
        assert forbidden not in helper.lower()


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
    scanner.check_private_catalog_foundation()
    path = REPO_ROOT / "src/pietto/_project/project_execution.py"
    original = scanner._read
    for token in ("psycopg", "server_version"):
        with monkeypatch.context() as patch:

            def injected(subject):
                value = original(subject)
                return value + "\n" + token.upper() if subject == path else value

            patch.setattr(scanner, "_read", injected)
            with pytest.raises(AssertionError) as exc:
                scanner.check_private_catalog_foundation()
            assert token in str(exc.value) and path.name in str(exc.value)
        scanner.check_private_catalog_foundation()
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
            scanner.check_private_catalog_foundation()
    scanner.check_private_catalog_foundation()


def test_actual_scanner_detects_removed_namespace_member_after_warming(monkeypatch):
    scanner.check_private_catalog_foundation()
    removed = REPO_ROOT / "src/pietto/semantic/extension_catalog.py"
    original = Path.rglob

    def paths(directory, pattern):
        for path in original(directory, pattern):
            if path != removed:
                yield path

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rglob", paths)
        with pytest.raises(AssertionError):
            scanner.check_private_catalog_foundation()
    scanner.check_private_catalog_foundation()


def test_old_negative_control_exposes_corrupted_shared_lowercase(monkeypatch):
    scanner.check_private_catalog_foundation()
    with monkeypatch.context() as patch:
        patch.setattr(
            RepositoryFactIndex,
            "lowercase",
            lambda self, text: text.lower().replace("psycopg", ""),
        )
        # The original injected-negative assertion must itself fail when its
        # observation is corrupted; this is not another shared PASS oracle.
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            scanner.check_execution_permission(patch, "project_execution.py", "psycopg")
    scanner.check_private_catalog_foundation()


def test_original_positional_index_constructor_contract(tmp_path):
    path = tmp_path / "one.py"
    path.write_text("ONE = 1\n")
    fact = RepositoryFactIndex.snapshot(tmp_path).python(path)
    cache = {path: fact}
    index = RepositoryFactIndex(tmp_path, cache)
    assert index.python(path) is fact and index._python_by_path is cache


def test_actual_scanner_does_not_choose_last_duplicate_path_overlay(monkeypatch):
    scanner.check_private_catalog_foundation()
    path = REPO_ROOT / "src/pietto/_project/project_execution.py"
    original_paths, original_read = Path.rglob, scanner._read
    seen = []

    def duplicated(directory, pattern):
        yield from original_paths(directory, pattern)
        if directory == REPO_ROOT / "src/pietto" and pattern == "*.py":
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
            scanner.check_private_catalog_foundation()
        assert seen == [path, path]
    scanner.check_private_catalog_foundation()


@pytest.mark.parametrize(
    "owner",
    ("project_sql_plan_portable.py", "project_sql_plan_portable_schema.py"),
)
@pytest.mark.parametrize(
    "forbidden",
    ("create extension", "pg_extension", "server_version", "psycopg", "asyncpg"),
)
def test_portable_metadata_permission_preserves_behavior_bans(
    monkeypatch, owner: str, forbidden: str
) -> None:
    scanner.check_execution_permission(monkeypatch, owner, forbidden)


def test_catalog_metadata_permission_does_not_cover_other_observation_owners(
    monkeypatch,
) -> None:
    scanner.check_execution_permission(
        monkeypatch, "project_sql_plan_pure_boundary.py", "extension_catalog"
    )


@pytest.mark.parametrize(
    "source",
    (
        "construct_extension_catalog (None)",
        "catalogs.select_extension_catalog(None)",
        "extension_signature_provider_authority(None)",
        "from pietto.semantic.capability_providers import canonical_capability_provider_inputs as acquire",
    ),
)
def test_catalog_metadata_permission_rejects_operational_references(
    monkeypatch, source: str
) -> None:
    scanner.check_execution_permission(
        monkeypatch, "project_sql_plan_portable.py", source
    )


@pytest.mark.parametrize(
    "owner,forbidden",
    (
        ("project_execution_postgres.py", "create extension"),
        ("project_execution_postgres.py", "pg_extension"),
        ("project_execution_postgres.py", "asyncpg"),
        ("project_execution_postgres.py", "extension_catalog"),
        ("project_execution_postgres.py", "pgvector"),
        ("project_execution_postgres.py", "pg_trgm"),
        ("project_execution_postgres.py", "postgis"),
        ("project_execution_postgres.py", "timescaledb"),
        ("project_execution.py", "psycopg"),
        ("project_execution.py", "server_version"),
        ("project_execution_source.py", "psycopg"),
        ("project_execution_source.py", "server_version"),
    ),
)
def test_execution_permission_is_path_and_purpose_limited(
    monkeypatch, owner: str, forbidden: str
) -> None:
    scanner.check_execution_permission(monkeypatch, owner, forbidden)


@pytest.mark.parametrize("forbidden", ("psycopg", "server_version"))
@pytest.mark.parametrize(
    "relative_path",
    (
        "src/pietto/semantic/project_execution_postgres.py",
        "src/pietto/_project/project_execution_postgres_shadow.py",
    ),
)
def test_execution_permission_does_not_follow_similar_paths(
    monkeypatch, relative_path: str, forbidden: str
) -> None:
    scanner.check_private_catalog_foundation()
    source_root = REPO_ROOT / "src/pietto"
    shadow = REPO_ROOT / relative_path
    assert not shadow.exists()
    original_rglob = Path.rglob
    original_read = scanner._read
    observed = []

    def injected_paths(directory: Path, pattern: str):
        yield from original_rglob(directory, pattern)
        if directory == source_root and pattern == "*.py":
            yield shadow

    def injected_read(candidate: Path) -> str:
        if candidate == shadow:
            observed.append(candidate)
            return forbidden
        return original_read(candidate)

    monkeypatch.setattr(Path, "rglob", injected_paths)
    monkeypatch.setattr(scanner, "_read", injected_read)
    with pytest.raises(AssertionError):
        scanner.check_private_catalog_foundation()
    assert observed
    assert not shadow.exists()
