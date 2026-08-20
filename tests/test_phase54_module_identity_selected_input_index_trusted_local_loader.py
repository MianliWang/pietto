from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
import os
from pathlib import Path
import stat
from types import MappingProxyType

import pytest

import pietto
import pietto._project.check as project_check
import pietto._project.config as project_config
import pietto._project.path_trust as path_trust
import pietto._project.source_selection as project_source_selection
import pietto._project.trusted_source as trusted_source
from pietto._project.config import load_project_config
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectParsedInput,
    ProjectSemanticModel,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.selected_input_index import ProjectSelectedInputIndex
from pietto._project.source_selection import select_project_sources
from pietto._project.trusted_source import (
    ProjectTrustedSourceError,
    ProjectTrustedSourceFailure,
    ProjectTrustedSourceSnapshot,
)
from pietto.errors import Diagnostic
import pietto.parser_api as parser_api

REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_PATH = (
    REPO_ROOT
    / "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py"
)
GATE0_GATE1_EVIDENCE = (
    "/home/mianliwang/.local/state/pietto/evidence/"
    "pietto-phase54-slice3-gate0-gate1-plan.txt"
)
CORRECTION_1_EVIDENCE = (
    "/home/mianliwang/.local/state/pietto/evidence/"
    "pietto-phase54-slice3-gate0-gate1-plan-correction-1.txt"
)
CORRECTION_2_EVIDENCE = (
    "/home/mianliwang/.local/state/pietto/evidence/"
    "pietto-phase54-slice3-gate0-gate1-plan-correction-2.txt"
)
GATE2_EVIDENCE = (
    "/home/mianliwang/.local/state/pietto/evidence/"
    "pietto-phase54-slice3-gate2-evidence-and-diff.txt"
)
GATE3_EVIDENCE = (
    "/home/mianliwang/.local/state/pietto/evidence/"
    "pietto-phase54-slice3-gate3-publication-evidence.txt"
)


def test_module_identity_is_exact_normalized_path_only() -> None:
    first = ProjectModuleIdentity(path="models/customer.pietto")
    second = ProjectModuleIdentity(path="models/customer.pietto")

    assert first == second
    assert hash(first) == hash(second)
    assert first != ProjectModuleIdentity(path="models/Customer.pietto")
    assert first != ProjectModuleIdentity(path="models/custómer.pietto")
    assert first != ProjectModuleIdentity(path="models/custómer.pietto")
    for invalid in (
        "",
        "/root.pietto",
        "../root.pietto",
        "models//root.pietto",
        "models/root.sql",
        "models/root.PIETTO",
        "C:/root.pietto",
        "models\\root.pietto",
    ):
        with pytest.raises(ValueError):
            ProjectModuleIdentity(path=invalid)
    with pytest.raises(ValueError):
        ProjectModuleIdentity(path=1)  # type: ignore[arg-type]


def test_logical_module_identity_property_preserves_slice2_fields() -> None:
    parsed = parser_api.parse_source(
        "shape Row:\n    id: Int\n",
        path="models/row.pietto",
    )
    assert parsed.ast is not None
    selected = ProjectInput(path="models/row.pietto", status="selected")
    parsed_input = ProjectParsedInput(path=selected.path, script=parsed.ast)
    selected_module = ProjectLogicalModule(
        ProjectCompilationMode.EXPLICIT_MODULES,
        selected.path,
        0,
        selected,
    )
    parsed_module = ProjectLogicalModule(
        ProjectCompilationMode.LEGACY_FLAT,
        selected.path,
        8,
        ProjectInput(path=selected.path, status="parsed"),
        parsed_input,
    )

    assert tuple(field.name for field in fields(ProjectLogicalModule)) == (
        "compilation_mode",
        "path",
        "position",
        "project_input",
        "parsed_input",
    )
    assert selected_module.identity == parsed_module.identity
    assert selected_module.identity.path == selected.path
    assert not hasattr(selected_module, "physical_identity")
    assert not hasattr(selected_module, "digest")


def test_selected_input_index_is_ordered_immutable_and_filesystem_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "z.pietto", "shape Z:\n    id: Int\n")
    _write(root, "a.pietto", "shape A:\n    id: Int\n")
    selection = select_project_sources(root, load_project_config(root))
    index = _required_index(selection)

    assert type(index.entries) is tuple
    assert tuple(entry.identity.path for entry in index.entries) == (
        "a.pietto",
        "z.pietto",
    )
    assert tuple(entry.position for entry in index.entries) == (0, 1)
    assert isinstance(index._entries_by_identity, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        setattr(index, "entries", ())

    def forbid_filesystem(*args: object, **kwargs: object) -> object:
        raise AssertionError("index lookup touched the filesystem")

    monkeypatch.setattr(path_trust.os, "stat", forbid_filesystem)
    monkeypatch.setattr(path_trust.os, "lstat", forbid_filesystem)
    assert index.find_path("a.pietto") is index.entries[0]
    assert index.find(ProjectModuleIdentity(path="z.pietto")) is index.entries[1]
    assert index.find_path("missing.pietto") is None
    assert index.find_path("../invalid.pietto") is None


def test_selected_input_index_rejects_duplicate_logical_and_physical_identities(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "a.pietto", "shape A:\n    id: Int\n")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).entries[0]

    with pytest.raises(TypeError, match="entries must be a tuple"):
        ProjectSelectedInputIndex(
            pinned_root=_required_pinned_root(selection),
            entries=[entry],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="logical keys must be unique"):
        ProjectSelectedInputIndex(
            pinned_root=_required_pinned_root(selection),
            entries=(entry, replace(entry, position=1)),
        )

    alias_input = ProjectInput(path="alias.pietto", status="selected")
    alias = replace(
        entry,
        identity=ProjectModuleIdentity(path=alias_input.path),
        position=1,
        project_input=alias_input,
    )
    with pytest.raises(ValueError, match="physical identities must be unique"):
        ProjectSelectedInputIndex(
            pinned_root=_required_pinned_root(selection),
            entries=(entry, alias),
        )


def test_regular_config_pins_root_and_reads_opened_bytes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    original_fdopen = project_config.os.fdopen
    read_calls = 0

    class TrackedFile:
        def __init__(self, wrapped: object) -> None:
            self.wrapped = wrapped

        def __enter__(self) -> TrackedFile:
            self.wrapped.__enter__()  # type: ignore[attr-defined]
            return self

        def __exit__(self, *args: object) -> object:
            return self.wrapped.__exit__(*args)  # type: ignore[attr-defined]

        def read(self) -> bytes:
            nonlocal read_calls
            read_calls += 1
            return self.wrapped.read()  # type: ignore[no-any-return, attr-defined]

        def fileno(self) -> int:
            return self.wrapped.fileno()  # type: ignore[no-any-return, attr-defined]

    def tracked_fdopen(*args: object, **kwargs: object) -> TrackedFile:
        return TrackedFile(original_fdopen(*args, **kwargs))  # type: ignore[arg-type]

    monkeypatch.setattr(project_config.os, "fdopen", tracked_fdopen)
    result = load_project_config(root)

    assert result.ok
    assert result.pinned_root is not None
    assert result.pinned_root.display_path == "."
    assert result.pinned_root.canonical_path == root.resolve(strict=True)
    assert read_calls == 1


def test_invocation_root_symlink_is_accepted_once_and_retarget_fails_closed(
    tmp_path: Path,
) -> None:
    first = _configured_project(tmp_path / "first", schema_version=2)
    second = _configured_project(tmp_path / "second", schema_version=2)
    _write(first, "row.pietto", "shape First:\n    id: Int\n")
    _write(second, "row.pietto", "shape Second:\n    id: Int\n")
    invocation = tmp_path / "project"
    invocation.symlink_to(first, target_is_directory=True)

    config_result = load_project_config(invocation)
    assert config_result.ok
    assert config_result.pinned_root is not None
    assert config_result.pinned_root.canonical_path == first.resolve(strict=True)

    invocation.unlink()
    invocation.symlink_to(second, target_is_directory=True)
    selection = select_project_sources(invocation, config_result)
    assert _single_error(selection.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_ROOT,
        "Project root identity changed during project loading.",
        None,
    )
    assert selection.selected_input_index is None


def test_root_replacement_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Original:\n    id: Int\n")
    config_result = load_project_config(root)
    displaced = tmp_path / "displaced"
    root.rename(displaced)
    _configured_project(root, schema_version=2)
    _write(root, "row.pietto", "shape Replacement:\n    id: Int\n")

    selection = select_project_sources(root, config_result)
    assert (
        _single_error(selection.errors).kind is ProjectDiscoveryErrorKind.PROJECT_ROOT
    )
    assert _single_error(selection.errors).path is None
    assert selection.selected_input_index is None


def test_config_symlink_and_non_regular_config_are_rejected_exactly(
    tmp_path: Path,
) -> None:
    symlink_root = tmp_path / "symlink"
    symlink_root.mkdir()
    target = tmp_path / "outside.toml"
    target.write_text(_config_text(2), encoding="utf-8")
    (symlink_root / "pietto.toml").symlink_to(target)
    symlink_result = load_project_config(symlink_root)
    assert _single_error(symlink_result.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.CONFIG_READ,
        "Project configuration path must not be a symbolic link.",
        "pietto.toml",
    )

    directory_root = tmp_path / "directory"
    directory_root.mkdir()
    (directory_root / "pietto.toml").mkdir()
    directory_result = load_project_config(directory_root)
    assert _single_error(directory_result.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.CONFIG_READ,
        "Project configuration path must be a regular file.",
        "pietto.toml",
    )

    loop_a = tmp_path / "loop-a"
    loop_b = tmp_path / "loop-b"
    loop_a.symlink_to(loop_b, target_is_directory=True)
    loop_b.symlink_to(loop_a, target_is_directory=True)
    loop_result = load_project_config(loop_a)
    assert _single_error(loop_result.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_ROOT,
        "Project root does not exist or is not accessible.",
        None,
    )


def test_config_opened_identity_and_read_mutation_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    other = tmp_path / "other.toml"
    other.write_text(_config_text(1), encoding="utf-8")

    def open_other(*args: object, **kwargs: object) -> int:
        return os.open(other, os.O_RDONLY)

    monkeypatch.setattr(project_config, "_open_pinned_file", open_other)
    mismatch = load_project_config(root)
    assert _single_error(mismatch.errors).message == (
        "Project configuration opened identity does not match the inspected file."
    )

    monkeypatch.undo()
    original_fstat = project_config._fstat_state
    calls = 0

    def changed_after_read(file_descriptor: int) -> object:
        nonlocal calls
        calls += 1
        state = original_fstat(file_descriptor)
        return replace(state, mtime_ns=state.mtime_ns + 1) if calls == 2 else state

    monkeypatch.setattr(project_config, "_fstat_state", changed_after_read)
    mutation = load_project_config(root)
    assert _single_error(mutation.errors).message == (
        "Project configuration file changed while being read."
    )

    monkeypatch.undo()
    original_lstat = project_config._lstat_state
    lstat_calls = 0

    def symlink_after_read(path: Path) -> object:
        nonlocal lstat_calls
        lstat_calls += 1
        state = original_lstat(path)
        return replace(state, file_type=stat.S_IFLNK) if lstat_calls == 2 else state

    monkeypatch.setattr(project_config, "_lstat_state", symlink_after_read)
    replaced = load_project_config(root)
    assert _single_error(replaced.errors).message == (
        "Project configuration file changed while being read."
    )


def test_regular_selected_source_builds_trusted_snapshot_and_exact_digest(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    source_bytes = b"shape Row:\n    id: Int\n"
    _write_bytes(root, "row.pietto", source_bytes)

    result = project_check.check_project_parse_only(root)
    assert result.ok
    assert len(result.trusted_source_snapshots) == 1
    snapshot = result.trusted_source_snapshots[0]
    entry = _required_index(result).entries[0]
    assert snapshot.selected_input is entry
    assert snapshot.identity == ProjectModuleIdentity(path="row.pietto")
    assert snapshot.position == 0
    assert snapshot.byte_count == len(source_bytes)
    assert snapshot.sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert snapshot.source_text == source_bytes.decode()
    assert snapshot.opened_target_state.physical_identity == (
        entry.final_target_state.physical_identity
    )


def test_inside_root_source_symlink_is_accepted_with_logical_identity(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "target.source", "shape Target:\n    id: Int\n")
    (root / "alias.pietto").symlink_to("target.source")
    result = project_check.check_project_parse_only(root)

    assert result.ok
    entries = _required_index(result).entries
    alias = next(entry for entry in entries if entry.identity.path == "alias.pietto")
    assert alias.final_leaf_is_symlink
    assert alias.symlink_target == "target.source"
    assert alias.identity == ProjectModuleIdentity(path="alias.pietto")
    assert (
        alias.final_target_state.physical_identity
        == path_trust._stat_state(root / "target.source").physical_identity
    )


def test_outside_root_source_symlink_is_rejected_exactly(tmp_path: Path) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    outside = tmp_path / "outside.pietto"
    outside.write_text("shape Outside:\n    id: Int\n", encoding="utf-8")
    (root / "escape.pietto").symlink_to(outside)

    selection = select_project_sources(root, load_project_config(root))
    assert _single_error(selection.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        "Project source path escapes the project root.",
        "escape.pietto",
    )
    assert selection.selected_input_index is None

    loop_root = _configured_project(tmp_path / "loop", schema_version=2)
    (loop_root / "loop.pietto").symlink_to("loop.pietto")
    loop_selection = select_project_sources(
        loop_root,
        load_project_config(loop_root),
    )
    assert _single_error(loop_selection.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.SOURCE_READ,
        "Project source file does not exist or is not accessible.",
        "loop.pietto",
    )


def test_symlink_directory_traversal_remains_excluded(tmp_path: Path) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "hidden.pietto", "shape Hidden:\n    id: Int\n")
    (root / "linked").symlink_to(outside, target_is_directory=True)

    selection = select_project_sources(root, load_project_config(root))
    assert selection.ok
    assert tuple(item.path for item in selection.inputs) == ("root.pietto",)
    assert _required_index(selection).find_path("linked/hidden.pietto") is None


def test_source_symlink_retarget_after_selection_fails_before_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "one.source", "shape One:\n    id: Int\n")
    _write(root, "two.source", "shape Two:\n    id: Int\n")
    alias = root / "alias.pietto"
    alias.symlink_to("one.source")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).find_path("alias.pietto")
    assert entry is not None
    alias.unlink()
    alias.symlink_to("two.source")
    monkeypatch.setattr(
        project_check.parser_api,
        "parse_source",
        lambda *args, **kwargs: pytest.fail("parser must not run"),
    )

    parsed = project_check._parse_selected_input(
        _required_pinned_root(selection),
        entry,
    )
    assert parsed[3][0].message == (
        "Project source symbolic link changed after selection."
    )


def test_regular_source_replacement_after_selection_fails_before_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    source = _write(root, "row.pietto", "shape Old:\n    id: Int\n")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).entries[0]
    displaced = root / "old.pietto"
    source.rename(displaced)
    source.write_text("shape New:\n    id: Int\n", encoding="utf-8")
    monkeypatch.setattr(
        project_check.parser_api,
        "parse_source",
        lambda *args, **kwargs: pytest.fail("parser must not run"),
    )

    parsed = project_check._parse_selected_input(
        _required_pinned_root(selection),
        entry,
    )
    assert parsed[3][0].message == "Project source file changed after selection."


def test_non_regular_selected_source_is_rejected_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    (root / "directory.pietto").mkdir()
    selection = select_project_sources(root, load_project_config(root))
    assert _single_error(selection.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.SOURCE_READ,
        "Project source path must resolve to a regular file.",
        "directory.pietto",
    )
    assert selection.selected_input_index is None

    identity_root = _configured_project(tmp_path / "identity", schema_version=2)
    _write(identity_root, "row.pietto", "shape Row:\n    id: Int\n")
    identity_config = load_project_config(identity_root)
    original_lstat = project_source_selection._lstat_state
    row_calls = 0

    def identity_unavailable(path: Path) -> object:
        nonlocal row_calls
        if path.name == "row.pietto":
            row_calls += 1
            if row_calls == 2:
                raise path_trust.ProjectIdentityUnavailableError(
                    "Project filesystem identity is unavailable."
                )
        return original_lstat(path)

    monkeypatch.setattr(
        project_source_selection,
        "_lstat_state",
        identity_unavailable,
    )
    unavailable = select_project_sources(identity_root, identity_config)
    assert _single_error(unavailable.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
        "Project filesystem identity is unavailable.",
        None,
    )

    monkeypatch.undo()
    normalized_root = _configured_project(tmp_path / "normalized", schema_version=2)
    _write(normalized_root, "bad\\name.pietto", "shape Row:\n    id: Int\n")
    invalid_path = select_project_sources(
        normalized_root,
        load_project_config(normalized_root),
    )
    assert _single_error(invalid_path.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        "Project source path must be a normalized relative path.",
        "bad\\name.pietto",
    )


def test_physical_duplicate_has_no_selected_index_winner(tmp_path: Path) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    first = _write(root, "a.pietto", "shape Row:\n    id: Int\n")
    os.link(first, root / "b.pietto")

    selection = select_project_sources(root, load_project_config(root))
    assert tuple(item.path for item in selection.inputs) == ("a.pietto",)
    assert _single_error(selection.errors) == ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        "Project source path duplicates an already selected file.",
        "b.pietto",
    )
    assert selection.selected_input_index is None


def test_opened_descriptor_identity_mismatch_fails_before_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    other = _write(root, "other.txt", "not selected\n")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).entries[0]
    monkeypatch.setattr(
        trusted_source,
        "_open_pinned_file",
        lambda *args, **kwargs: os.open(other, os.O_RDONLY),
    )
    monkeypatch.setattr(
        project_check.parser_api,
        "parse_source",
        lambda *args, **kwargs: pytest.fail("parser must not run"),
    )

    parsed = project_check._parse_selected_input(
        _required_pinned_root(selection),
        entry,
    )
    assert parsed[3][0].message == (
        "Project source opened identity does not match the selected file."
    )


def test_source_byte_limit_and_oversize_diagnostic_remain_exact(
    tmp_path: Path,
) -> None:
    exact_root = _configured_project(tmp_path / "exact", schema_version=2)
    exact = b"#" * 1_048_576
    _write_bytes(exact_root, "row.pietto", exact)
    exact_selection = select_project_sources(
        exact_root,
        load_project_config(exact_root),
    )
    exact_entry = _required_index(exact_selection).entries[0]

    accepted = trusted_source._load_trusted_source(
        _required_pinned_root(exact_selection),
        exact_entry,
        byte_limit=1_048_576,
    )
    assert isinstance(accepted, ProjectTrustedSourceSnapshot)

    oversize_root = _configured_project(tmp_path / "oversize", schema_version=2)
    _write_bytes(oversize_root, "row.pietto", exact + b"#")
    oversize_selection = select_project_sources(
        oversize_root,
        load_project_config(oversize_root),
    )
    oversize = trusted_source._load_trusted_source(
        _required_pinned_root(oversize_selection),
        _required_index(oversize_selection).entries[0],
        byte_limit=1_048_576,
    )
    assert isinstance(oversize, Diagnostic)
    assert oversize.code == "PIE-P1006"
    assert oversize.message == (
        "Source exceeds the maximum supported size of 1048576 UTF-8 bytes."
    )
    assert oversize.location.path == "row.pietto"


def test_invalid_utf8_and_read_error_order_remain_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write_bytes(root, "a.pietto", b"\xff")
    _write(root, "b.pietto", "shape B:\n    id: Int\n")
    original_load = project_check._load_trusted_source

    def fail_second(*args: object, **kwargs: object) -> object:
        entry = args[1]
        if getattr(entry, "identity").path == "b.pietto":
            raise OSError("synthetic read failure")
        return original_load(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(project_check, "_load_trusted_source", fail_second)
    result = project_check.check_project_parse_only(root)

    assert tuple(error.path for error in result.errors) == (
        "a.pietto",
        "b.pietto",
    )
    assert tuple(error.message for error in result.errors) == (
        "Project source file must be valid UTF-8.",
        "Project source file is not readable.",
    )
    assert result.trusted_source_snapshots == ()


def test_parser_consumes_snapshot_text_without_second_path_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Original:\n    id: Int\n")
    config_result = load_project_config(root)
    selection = select_project_sources(root, config_result)
    entry = _required_index(selection).entries[0]
    replacement = "shape Snapshot:\n    id: Int\n"
    snapshot = ProjectTrustedSourceSnapshot(
        selected_input=entry,
        byte_count=len(replacement.encode()),
        sha256=hashlib.sha256(replacement.encode()).hexdigest(),
        source_text=replacement,
        opened_target_state=entry.final_target_state,
    )
    monkeypatch.setattr(
        project_check, "load_project_config", lambda root: config_result
    )
    monkeypatch.setattr(
        project_check,
        "select_project_sources",
        lambda root, config: selection,
    )
    monkeypatch.setattr(
        project_check,
        "_load_trusted_source",
        lambda *args, **kwargs: snapshot,
    )
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: pytest.fail("project path reopened"),
    )

    result = project_check.check_project_parse_only(root)
    assert result.ok
    definition = result.parsed_inputs[0].script.definitions[0]
    assert definition.name == "Snapshot"
    assert result.trusted_source_snapshots == (snapshot,)


def test_source_digest_changes_only_with_exact_accepted_bytes(tmp_path: Path) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    first = b"shape Row:\n    id: Int\n"
    second = b"shape Row:\n    id: Text\n"
    path = _write_bytes(root, "row.pietto", first)
    first_result = project_check.check_project_parse_only(root)
    path.write_bytes(second)
    second_result = project_check.check_project_parse_only(root)

    assert (
        first_result.trusted_source_snapshots[0].sha256
        == hashlib.sha256(first).hexdigest()
    )
    assert (
        second_result.trusted_source_snapshots[0].sha256
        == hashlib.sha256(second).hexdigest()
    )
    assert (
        first_result.trusted_source_snapshots[0].sha256
        != second_result.trusted_source_snapshots[0].sha256
    )


def test_source_descriptors_close_on_success_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    other = _write(root, "other.txt", "other\n")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).entries[0]
    opened: list[int] = []
    original_open = trusted_source._open_pinned_file

    def track_open(*args: object, **kwargs: object) -> int:
        descriptor = original_open(*args, **kwargs)  # type: ignore[arg-type]
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(trusted_source, "_open_pinned_file", track_open)
    trusted_source._load_trusted_source(
        _required_pinned_root(selection),
        entry,
        byte_limit=1_048_576,
    )
    _assert_closed(opened.pop())

    def open_other(*args: object, **kwargs: object) -> int:
        descriptor = os.open(other, os.O_RDONLY)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(trusted_source, "_open_pinned_file", open_other)
    with pytest.raises(ProjectTrustedSourceError):
        trusted_source._load_trusted_source(
            _required_pinned_root(selection),
            entry,
            byte_limit=1_048_576,
        )
    _assert_closed(opened.pop())


def test_pre_post_read_mutation_is_rejected_when_observed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    selection = select_project_sources(root, load_project_config(root))
    entry = _required_index(selection).entries[0]
    original_fstat = trusted_source._fstat_state
    calls = 0

    def changed_after_read(file_descriptor: int) -> object:
        nonlocal calls
        calls += 1
        state = original_fstat(file_descriptor)
        return replace(state, ctime_ns=state.ctime_ns + 1) if calls == 2 else state

    monkeypatch.setattr(trusted_source, "_fstat_state", changed_after_read)
    with pytest.raises(ProjectTrustedSourceError) as raised:
        trusted_source._load_trusted_source(
            _required_pinned_root(selection),
            entry,
            byte_limit=1_048_576,
        )
    assert raised.value.reason is ProjectTrustedSourceFailure.READ_MUTATION

    monkeypatch.undo()
    original_lstat = trusted_source._lstat_state
    lstat_calls = 0

    def canonical_leaf_changed(path: Path) -> object:
        nonlocal lstat_calls
        lstat_calls += 1
        state = original_lstat(path)
        return (
            replace(state, ctime_ns=state.ctime_ns + 1) if lstat_calls == 4 else state
        )

    monkeypatch.setattr(trusted_source, "_lstat_state", canonical_leaf_changed)
    with pytest.raises(ProjectTrustedSourceError) as canonical_raised:
        trusted_source._load_trusted_source(
            _required_pinned_root(selection),
            entry,
            byte_limit=1_048_576,
        )
    assert canonical_raised.value.reason is ProjectTrustedSourceFailure.READ_MUTATION


def test_schema_v1_and_schema_v2_retain_trust_facts_and_existing_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = []
    for schema_version in (1, 2):
        root = _configured_project(tmp_path / f"v{schema_version}", schema_version)
        _write(root, "row.pietto", "shape Row:\n    id: Int\n")
        config_result = load_project_config(root)
        selection = select_project_sources(root, config_result)
        monkeypatch.setattr(
            project_check,
            "load_project_config",
            lambda checked_root, result=config_result: result,
        )
        monkeypatch.setattr(
            project_check,
            "select_project_sources",
            lambda checked_root, config, result=selection: result,
        )
        parse_result = project_check.check_project_parse_only(root)
        semantic_result = build_empty_project_semantic_result(parse_result)

        assert config_result.pinned_root is selection.pinned_root
        assert parse_result.pinned_root is config_result.pinned_root
        assert parse_result.selected_input_index is selection.selected_input_index
        assert semantic_result.pinned_root is parse_result.pinned_root
        assert semantic_result.selected_input_index is parse_result.selected_input_index
        assert (
            semantic_result.trusted_source_snapshots
            is parse_result.trusted_source_snapshots
        )
        assert parse_result.ok
        results.append((parse_result, semantic_result))

    assert results[0][1].model is not None
    assert results[1][1].model is None
    assert results[1][0].compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES


def test_single_file_public_privacy_scope_remains_exact() -> None:
    assert ProjectSemanticModel.__dataclass_fields__.keys().isdisjoint(
        {"pinned_root", "selected_input_index", "trusted_source_snapshots"}
    )
    assert not hasattr(pietto, "ProjectModuleIdentity")
    assert not hasattr(pietto, "ProjectSelectedInputIndex")
    assert not hasattr(pietto, "ProjectTrustedSourceSnapshot")
    assert path_trust.__all__ == ()
    assert trusted_source.__all__ == ()
    single = parser_api.parse_source("shape One:\n    id: Int\n", path="one.pietto")
    assert single.ast is not None
    assert single.diagnostics == ()


def _configured_project(
    root: Path,
    schema_version: int,
    *,
    include: tuple[str, ...] = ("**/*.pietto",),
) -> Path:
    root.mkdir(parents=True)
    include_text = ", ".join(json.dumps(pattern) for pattern in include)
    (root / "pietto.toml").write_text(
        f"schema_version = {schema_version}\n\n[sources]\ninclude = [{include_text}]\n",
        encoding="utf-8",
    )
    return root


def _config_text(schema_version: int) -> str:
    return (
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["**/*.pietto"]\n'
    )


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative: str, content: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _single_error(
    errors: tuple[ProjectDiscoveryError, ...],
) -> ProjectDiscoveryError:
    assert len(errors) == 1
    return errors[0]


def _required_index(value: object) -> ProjectSelectedInputIndex:
    index = getattr(value, "selected_input_index")
    assert isinstance(index, ProjectSelectedInputIndex)
    return index


def _required_pinned_root(value: object) -> path_trust.ProjectPinnedRoot:
    pinned_root = getattr(value, "pinned_root")
    assert isinstance(pinned_root, path_trust.ProjectPinnedRoot)
    return pinned_root


def _assert_closed(file_descriptor: int) -> None:
    with pytest.raises(OSError):
        os.fstat(file_descriptor)
