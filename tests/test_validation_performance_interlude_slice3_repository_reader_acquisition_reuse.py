from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
import shutil
import subprocess

import pytest

from _pietto_repository_facts import (
    PythonSourceFacts,
    REPOSITORY_FACTS,
    RepositoryFactIndex,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice3-repository-reader-acquisition-reuse-v1.md"
)
HELPER = REPO_ROOT / "tests/_pietto_repository_facts.py"
WORKFLOW_OWNER = REPO_ROOT / "tests/test_workflow_lifecycle_validation_efficiency.py"
MIGRATED_OWNER_PATHS = tuple(
    REPO_ROOT / path
    for path in (
        "tests/test_workflow_lifecycle_validation_efficiency.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
    )
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


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
                "tests/test_workflow_lifecycle_validation_efficiency.py",
                "tests/test_phase52_fail_closed_capability_lookup.py",
                "tests/test_phase52_private_capability_fact_foundation.py",
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


def test_each_migrated_owner_retains_its_legacy_path_selector() -> None:
    workflow_tree = ast.parse(
        REPOSITORY_FACTS.python(WORKFLOW_OWNER).text,
        filename=str(WORKFLOW_OWNER),
    )
    workflow_globs = sorted(
        (node.func.value.id, node.args[0].value)
        for node in ast.walk(workflow_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "glob"
        and isinstance(node.func.value, ast.Name)
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    )
    assert workflow_globs == sorted(
        (
            ("TESTS_ROOT", "test_*.py"),
            ("TESTS_ROOT", "test_phase56_*.py"),
            ("TESTS_ROOT", "test_phase57_*.py"),
            ("TESTS_ROOT", "test_phase58_slice*.py"),
            ("TESTS_ROOT", "test_phase59_slice*.py"),
            ("TESTS_ROOT", "test_phase60_slice*.py"),
            ("TESTS_ROOT", "test_phase61_slice*.py"),
        )
    )
    assert not any(
        isinstance(node, ast.Attribute) and node.attr in {"python_paths_under", "rglob"}
        for node in ast.walk(workflow_tree)
    )

    expected_rglob_counts = (1, 1, 1, 1, 2, 1, 1)
    for path, expected_count in zip(
        MIGRATED_OWNER_PATHS[1:],
        expected_rglob_counts,
        strict=True,
    ):
        tree = ast.parse(REPOSITORY_FACTS.python(path).text, filename=str(path))
        assert (
            sum(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "rglob"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "*.py"
                for node in ast.walk(tree)
            )
            == expected_count
        ), path
        assert not any(
            isinstance(node, ast.Attribute) and node.attr == "python_paths_under"
            for node in ast.walk(tree)
        ), path


def test_migrated_owner_sources_do_not_mutate_snapshot_files() -> None:
    mutating_methods = {"write_text", "write_bytes", "unlink", "rename", "replace"}
    assert len(MIGRATED_OWNER_PATHS) == 8
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


def test_helper_contains_acquisition_only_and_slice3_handoff_is_exact() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    for forbidden in (
        "expected lifecycle",
        "allowed consumer",
        "forbidden import",
        "pytest result",
    ):
        assert forbidden not in helper.lower()

    document = SPEC.read_text(encoding="utf-8")
    performance = " ".join(_section(document, "Performance Proof").split())
    boundary = " ".join(_section(document, "Policy And Freshness Boundary").split())
    lifecycle = " ".join(_section(document, "Changed-Path And Lifecycle Lock").split())
    assert "Text reads decrease" in performance
    assert "AST parses decrease" in performance
    assert "no material wall-time regression" in performance
    assert "Policy assertions remain in the nine existing owners" in boundary
    assert "fresh explicit snapshot" in boundary
    assert "sole mutable lifecycle document reader" in lifecycle
    assert "Phase 60 = NOT ACTIVATED" in lifecycle
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_SLICE4_VALIDATOR_STATIC_ANALYSIS_STAGE_OPTIMIZATION"
        in lifecycle
    )
