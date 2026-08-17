from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

import pietto
import pietto._project.check as project_check
import pietto._project.config as project_config
import pietto._project.model as project_model
import pietto._project.module_carrier as module_carrier
import pietto._project.source_selection as source_selection
import pietto.cli as cli
import _pietto_publication_topology as publication_topology
from _phase54_active_gate2_manifest import (
    PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,
    PHASE55_SLICE2_RECOVERY_SUBJECT,
    phase55_slice2_direct_main_commit_matches_external_sealed_tree,
    phase55_slice2_recovery_commit_matches_external_sealed_tree,
    phase55_slice2_recovery_shape_matches_failed_publication,
)
from _pietto_publication_topology import (
    TopologyError,
    assert_topology,
    build_slice2_direct_main_all,
    verify,
)
from pietto._project.config import load_project_config
from pietto._project.model import (
    ProjectConfig,
    ProjectConfigPath,
    ProjectConfigLoadResult,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectRootPackageActivation,
    ProjectSemanticResult,
    ProjectSourceConfig,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.path_trust import (
    ProjectPhysicalIdentity,
    ProjectPinnedRoot,
    _pin_project_root,
)
from pietto._project.selected_input_index import (
    ProjectSelectedInputEntry,
    ProjectSelectedInputIndex,
)
from pietto._project.source_selection import select_project_sources
from pietto._project.trusted_source import ProjectTrustedSourceSnapshot


_MODULE_SIDECAR_FIELDS = (
    "module_catalogs",
    "module_exports",
    "module_bindings",
    "module_graph",
    "module_diagnostic_facts",
    "module_type_source_resolutions",
    "module_relation_resolutions",
    "module_semantic_facts",
    "module_attribution_facts",
    "module_package_identity_facts",
    "module_inspection_facts",
)
_P08_MESSAGE = "Schema-v3 package activation does not use project source selection."
_EXTERNAL_BASELINE = "5de57b2c078742253aa64d3a5ad627cd602290cd"
_EXTERNAL_BASELINE_TREE = "9bc952f6eedca6a953c9edd94e0172b02451f74c"
_EXTERNAL_SEALED_TREE = "60c68ab7653fcd11538fabf21aba552dcbd3baa9"
_EXTERNAL_DIRECT_MAIN_KINDS = (
    "slice2_direct_main_dirty_candidate",
    "slice2_direct_main_clean_pre_push",
    "slice2_direct_main_shallow_push",
    "slice2_direct_main_reconciled",
)
_EXTERNAL_DIRECT_MAIN_SUBJECT = "Add Phase 55 explicit package activation carrier"
_EXTERNAL_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"


def test_schema_version_and_table_activation_are_closed_and_exact(
    tmp_path: Path,
) -> None:
    for version, table, mode in (
        (1, _sources_table(), ProjectCompilationMode.LEGACY_FLAT),
        (2, _sources_table(), ProjectCompilationMode.EXPLICIT_MODULES),
        (3, _package_table(), ProjectCompilationMode.PACKAGE_ROOT),
    ):
        result = load_project_config(
            _root(
                tmp_path / f"valid-{version}", f"schema_version = {version}\n\n{table}"
            )
        )
        assert result.ok and result.config is not None
        assert result.config.compilation_mode is mode
        assert (result.config.sources is None) is (version == 3)
        assert (result.config.root_package is None) is (version != 3)

    invalid = (
        "schema_version = true\n\n" + _package_table(),
        'schema_version = "3"\n\n' + _package_table(),
        "schema_version = 3.0\n\n" + _package_table(),
        "schema_version = 1979-05-27\n\n" + _package_table(),
        "schema_version = 07:32:00\n\n" + _package_table(),
        "schema_version = 1979-05-27 07:32:00+00:00\n\n" + _package_table(),
        "schema_version = -1\n\n" + _package_table(),
        "schema_version = 0\n\n" + _package_table(),
        "schema_version = 4\n\n" + _package_table(),
        "schema_version = 1\n\n" + _package_table(),
        "schema_version = 2\n\n" + _package_table(),
        "schema_version = 1\n",
        "schema_version = 2\n",
        "schema_version = 3\n",
        "schema_version = 3\n\n" + _sources_table(),
        "schema_version = 3\n\n" + _sources_table() + "\n" + _package_table(),
        'schema_version = 3\nname = "foreign"\n\n' + _package_table(),
        'schema_version = 3\npackage = "not a table"\n',
        'schema_version = 3\n\n[[package]]\npath = "."\n',
        'schema_version = 3\n\n[package.nested]\npath = "."\n',
        "schema_version = 3\n\n" + _package_table() + "\n" + _package_table(),
        "schema_version = 3\n\n" + _package_table() + 'extra = "foreign"\n',
    )
    for index, text in enumerate(invalid):
        result = load_project_config(_root(tmp_path / f"invalid-{index}", text))
        assert not result.ok and result.config is None
        assert result.errors[0].kind in {
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
        }

    for name, text in (
        (
            "inline",
            'schema_version = 3\npackage = { path = ".", namespace = "ns", name = "name", version = "v", sha256 = "pin" }\n',
        ),
        (
            "dotted",
            'schema_version = 3\npackage.path = "."\npackage.namespace = "ns"\npackage.name = "name"\npackage.version = "v"\npackage.sha256 = "pin"\n',
        ),
        (
            "quoted",
            'schema_version = 3\n\n["package"]\npath = "."\nnamespace = "ns"\nname = "name"\nversion = "v"\nsha256 = "pin"\n',
        ),
    ):
        result = load_project_config(_root(tmp_path / name, text))
        assert not result.ok and result.config is None
        assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_package_fields_path_and_deferred_values_are_structural_only(
    tmp_path: Path,
) -> None:
    required = ("path", "namespace", "name", "version", "sha256")
    for field in required:
        result = load_project_config(
            _root(tmp_path / f"missing-{field}", _package_document({field: None}))
        )
        assert not result.ok and result.config is None
        assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    for field in required:
        for index, value in enumerate(
            (
                "true",
                "1",
                "1.0",
                "1979-05-27",
                "07:32:00",
                "1979-05-27 07:32:00+00:00",
                "[]",
                '{ key = "value" }',
                '""',
            )
        ):
            result = load_project_config(
                _root(
                    tmp_path / f"value-{field}-{index}",
                    _package_document({field: value}, raw_values=True),
                )
            )
            assert not result.ok and result.config is None
            assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    for path in (".", "pkg", "a/b/c"):
        result = load_project_config(
            _root(
                tmp_path / f"path-ok-{path.replace('/', '-')}",
                _package_document({"path": path}),
            )
        )
        assert result.ok and result.config and result.config.root_package
        assert result.config.root_package.path == path
    for index, path in enumerate(
        (
            "",
            "/pkg",
            "C:/pkg",
            "//server/pkg",
            "pkg\\child",
            "pkg\x00child",
            "pkg//child",
            "pkg/",
            "./pkg",
            "../pkg",
            "a/./b",
            "a/../b",
            "a/b/.",
            "a/b/..",
            "a/../../b",
            "..",
        )
    ):
        result = load_project_config(
            _root(tmp_path / f"path-bad-{index}", _package_document({"path": path}))
        )
        assert not result.ok and result.config is None
        assert result.errors[0].kind is (
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA
            if path == ""
            else ProjectDiscoveryErrorKind.PROJECT_PATH
        )
    deferred: Mapping[str, str] = {
        "namespace": " not a slug! ",
        "name": "also not a slug! 雪",
        "version": "not-semver\\nvalue",
        "sha256": "not-a-sha256\\tvalue",
    }
    first = load_project_config(
        _root(tmp_path / "deferred-first", _package_document(deferred))
    )
    second = load_project_config(
        _root(
            tmp_path / "deferred-second",
            _package_document(
                deferred, order=("sha256", "version", "name", "namespace", "path")
            ),
        )
    )
    assert first.ok and second.ok and first.config and second.config
    assert first.config.root_package == second.config.root_package
    assert first.config.root_package is not None
    assert tuple(getattr(first.config.root_package, field) for field in required) == (
        ".",
        *tuple(deferred.values()),
    )


@pytest.mark.parametrize("schema_version", (1, 2))
def test_v1_v2_reject_valid_sources_with_every_package_declaration_shape(
    tmp_path: Path, schema_version: int
) -> None:
    expected = ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        "Project configuration contains unsupported top-level key: package.",
        "pietto.toml",
    )
    for name, declaration in (
        ("bare", _package_table()),
        ("nested", '[package.child]\nvalue = "foreign"\n'),
        ("array", '[[package]]\npath = "."\n'),
    ):
        result = load_project_config(
            _root(
                tmp_path / f"v{schema_version}-{name}",
                _sources_document(schema_version) + "\n" + declaration,
            )
        )
        assert not result.ok and result.config is None
        assert result.errors == (expected,)


@pytest.mark.parametrize("schema_version", (1, 2))
def test_v1_v2_structural_source_config_detaches_mutable_decoded_mapping(
    tmp_path: Path, schema_version: int
) -> None:
    root_path = tmp_path / f"v{schema_version}-detached"
    root_path.mkdir()
    root = ProjectRoot(".")
    config_path = ProjectConfigPath("pietto.toml")
    pinned_root = _pin_project_root(root_path)
    decoded: dict[str, object] = {
        "schema_version": schema_version,
        "sources": {"include": ["*.pietto"], "exclude": []},
    }
    result = project_config._validate_config(
        root,
        config_path,
        decoded,
        _sources_document(schema_version),
        pinned_root,
    )
    assert result.ok and result.config is not None
    assert result.config.sources == ProjectSourceConfig(("*.pietto",), ())
    decoded["schema_version"] = 3
    sources = decoded["sources"]
    assert isinstance(sources, dict)
    include = sources["include"]
    assert isinstance(include, list)
    include.append("mutated.pietto")
    sources["exclude"] = ["mutated.pietto"]
    assert result.config.schema_version == schema_version
    assert result.config.sources == ProjectSourceConfig(("*.pietto",), ())


def test_root_package_carrier_and_project_config_are_exact_private_tagged_union() -> (
    None
):
    activation = ProjectRootPackageActivation(
        "pkg", "example", "demo", "release", "pin"
    )
    assert is_dataclass(ProjectRootPackageActivation)
    assert hasattr(ProjectRootPackageActivation, "__slots__") and not hasattr(
        activation, "__dict__"
    )
    assert tuple(field.name for field in fields(ProjectRootPackageActivation)) == (
        "path",
        "namespace",
        "name",
        "version",
        "sha256",
    )
    assert isinstance(hash(activation), int)
    with pytest.raises(FrozenInstanceError):
        activation.name = "changed"  # pyright: ignore[reportAttributeAccessIssue]
    source = ProjectSourceConfig(("*.pietto",), ())
    assert tuple(field.name for field in fields(ProjectConfig)) == (
        "schema_version",
        "sources",
        "compilation_mode",
        "root_package",
    )
    for version, mode, sources, root_package in (
        (1, ProjectCompilationMode.LEGACY_FLAT, source, None),
        (2, ProjectCompilationMode.EXPLICIT_MODULES, source, None),
        (3, ProjectCompilationMode.PACKAGE_ROOT, None, activation),
    ):
        assert (
            ProjectConfig(version, sources, mode, root_package).schema_version
            == version
        )
    for kwargs in (
        dict(
            schema_version=1,
            sources=None,
            compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
            root_package=None,
        ),
        dict(
            schema_version=2,
            sources=source,
            compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
            root_package=None,
        ),
        dict(
            schema_version=3,
            sources=source,
            compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
            root_package=activation,
        ),
        dict(
            schema_version=3,
            sources=None,
            compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
            root_package=None,
        ),
        dict(
            schema_version=1,
            sources=source,
            compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
            root_package=activation,
        ),
    ):
        with pytest.raises((TypeError, ValueError)):
            ProjectConfig(**kwargs)  # type: ignore[arg-type]

    class ForeignActivation(ProjectRootPackageActivation):
        pass

    with pytest.raises((TypeError, ValueError)):
        ProjectConfig(
            3,
            None,
            ProjectCompilationMode.PACKAGE_ROOT,
            ForeignActivation("pkg", "example", "demo", "release", "pin"),
        )
    assert module_carrier.__all__ == () and not hasattr(
        pietto, "ProjectRootPackageActivation"
    )
    assert tuple(field.name for field in fields(ProjectModuleIdentity)) == ("path",)
    for carrier in (
        ProjectDiscoveryResult,
        ProjectParseCheckResult,
        ProjectSemanticResult,
    ):
        assert "root_package" not in carrier.__dataclass_fields__


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("path", None),
        ("path", True),
        ("path", 1),
        ("path", ""),
        ("path", "/pkg"),
        ("path", "pkg\\child"),
        ("path", "a/../b"),
        ("namespace", ""),
        ("namespace", None),
        ("namespace", True),
        ("namespace", 1),
        ("name", ""),
        ("name", None),
        ("name", True),
        ("name", 1),
        ("version", ""),
        ("version", None),
        ("version", True),
        ("version", 1),
        ("sha256", ""),
        ("sha256", None),
        ("sha256", True),
        ("sha256", 1),
    ),
)
def test_root_package_activation_rejects_finite_direct_invalid_constructor_axes(
    field: str, value: object
) -> None:
    values: dict[str, object] = {
        "path": "pkg",
        "namespace": "example",
        "name": "demo",
        "version": "release",
        "sha256": "pin",
    }
    values[field] = value
    with pytest.raises((TypeError, ValueError)):
        ProjectRootPackageActivation(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("package_path", (".", "pkg", "a/b/c"))
def test_schema_v3_routes_are_p08_exact_and_do_not_enter_forbidden_product_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    package_path: str,
) -> None:
    values = _package_values(package_path)
    root = _root(tmp_path / "project", _package_document(values))
    _write_decoys(root, package_path)

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "schema-v3 package route entered forbidden source/module boundary"
        )

    with monkeypatch.context() as patch:
        for target, name in (
            (source_selection, "_select_from_config"),
            (source_selection, "_discover_candidate_paths"),
            (source_selection, "_build_project_logical_modules"),
            (project_check, "_parse_selected_input"),
            (project_check, "_load_trusted_source"),
            (project_check.parser_api, "parse_source"),
            (project_check, "_build_project_logical_modules"),
            (cli, "build_empty_project_semantic_result"),
        ):
            patch.setattr(target, name, forbidden)
        config = load_project_config(root)
        assert (
            config.ok
            and config.config
            and config.root
            and config.config_path
            and config.pinned_root
        )
        _assert_exact_root_authority(
            config.root, config.config_path, config.pinned_root, root
        )
        assert type(config.config) is ProjectConfig
        assert config.config.schema_version == 3
        assert config.config.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT
        assert config.config.sources is None
        assert type(config.config.root_package) is ProjectRootPackageActivation
        assert config.config.root_package == ProjectRootPackageActivation(**values)
        selection = select_project_sources(root, config)
        parsed = project_check.check_project_parse_only(root)
        assert (
            selection.root is config.root
            and selection.config_path is config.config_path
            and selection.pinned_root is config.pinned_root
        )
        _assert_exact_root_authority(
            parsed.root, parsed.config_path, parsed.pinned_root, root
        )
        expected_p08_errors = (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                _P08_MESSAGE,
                None,
            ),
        )
        for result in (selection, parsed):
            assert result.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT
            assert (
                result.inputs == result.modules == ()
                and result.selected_input_index is None
            )
            assert result.errors == expected_p08_errors
        assert (
            parsed.parsed_inputs
            == parsed.trusted_source_snapshots
            == parsed.diagnostics
            == ()
        )
        semantic = build_empty_project_semantic_result(parsed)
        assert semantic.root is parsed.root
        assert semantic.config_path is parsed.config_path
        assert semantic.pinned_root is parsed.pinned_root
        assert semantic.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT
        assert semantic.model is None
        assert (
            semantic.modules
            == semantic.trusted_source_snapshots
            == semantic.diagnostics
            == ()
        )
        assert semantic.selected_input_index is None
        assert all(getattr(semantic, field) is None for field in _MODULE_SIDECAR_FIELDS)
        for carrier in (selection, parsed, semantic):
            assert "root_package" not in getattr(carrier, "__dataclass_fields__", {})
        assert cli._run_project_check(root, output_format="text") == 2
        text = capsys.readouterr()
        assert (
            text.out == ""
            and text.err == f"project error: config_schema: {_P08_MESSAGE}\n"
        )
        assert cli._run_project_check(root, output_format="json") == 2
        encoded = capsys.readouterr()
        assert encoded.err == ""
        document = json.loads(encoded.out)
        expected_document = {
            "schema_version": 2,
            "command": "check",
            "mode": "project",
            "ok": False,
            "project": {"root": ".", "config_path": "pietto.toml"},
            "inputs": [],
            "diagnostics": [],
            "cli_errors": [
                {
                    "kind": "config_schema",
                    "message": _P08_MESSAGE,
                    "path": None,
                }
            ],
            "result": {
                "check": {"files_total": 0, "files_ok": 0, "files_with_errors": 0}
            },
        }
        assert document == expected_document
        assert encoded.out == json.dumps(expected_document, ensure_ascii=True) + "\n"
        assert "package" not in document and "root_package" not in document
        assert '"package"' not in encoded.out
        assert "root_package" not in encoded.out + text.out + text.err
        for value in tuple(values.values())[1:]:
            assert value not in encoded.out + text.out + text.err
        if package_path != ".":
            assert package_path not in encoded.out + text.out + text.err
    assert (
        cli.main(["check", "--project", str(root)]) == 2 and capsys.readouterr() == text
    )
    assert (
        cli.main(["check", "--project", str(root), "--format", "json"]) == 2
        and capsys.readouterr() == encoded
    )


@pytest.mark.parametrize("has_error", (False, True))
def test_package_semantic_guard_precedes_error_short_circuit_and_rejects_grafts(
    has_error: bool, tmp_path: Path
) -> None:
    error = ProjectDiscoveryError(ProjectDiscoveryErrorKind.CONFIG_SCHEMA, "injected")
    base = ProjectParseCheckResult(
        ProjectRoot("."),
        ProjectConfigPath("pietto.toml"),
        (),
        (error,) if has_error else (),
        (),
        compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
    )
    semantic = build_empty_project_semantic_result(base)
    assert (
        semantic.model is None
        and semantic.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT
    )
    assert (
        semantic.modules == ()
        and semantic.selected_input_index is None
        and semantic.trusted_source_snapshots == ()
    )
    assert all(getattr(semantic, field) is None for field in _MODULE_SIDECAR_FIELDS)
    legacy = project_check.check_project_parse_only(
        _project_with_source(tmp_path / "legacy", 1)
    )
    explicit = project_check.check_project_parse_only(
        _project_with_source(tmp_path / "explicit", 2)
    )
    for source in (legacy, explicit):
        for graft in (
            {"inputs": source.inputs},
            {"parsed_inputs": source.parsed_inputs},
            {"modules": source.modules},
            {"selected_input_index": source.selected_input_index},
            {"trusted_source_snapshots": source.trusted_source_snapshots},
        ):
            with pytest.raises((TypeError, ValueError)):
                build_empty_project_semantic_result(replace(base, **graft))
    for graft in (
        {"inputs": legacy.inputs, "modules": explicit.modules},
        {"inputs": explicit.inputs, "modules": legacy.modules},
        {
            "inputs": legacy.inputs,
            "parsed_inputs": legacy.parsed_inputs,
            "modules": legacy.modules,
            "selected_input_index": legacy.selected_input_index,
            "trusted_source_snapshots": legacy.trusted_source_snapshots,
        },
    ):
        with pytest.raises((TypeError, ValueError)):
            build_empty_project_semantic_result(replace(base, **graft))
    explicit_semantic = build_empty_project_semantic_result(explicit)
    for graft in (
        {"model": object()},
        {"modules": explicit.modules},
        {"selected_input_index": explicit.selected_input_index},
        {"trusted_source_snapshots": explicit.trusted_source_snapshots},
        *(
            {field: getattr(explicit_semantic, field)}
            for field in _MODULE_SIDECAR_FIELDS
        ),
    ):
        with pytest.raises((TypeError, ValueError)):
            ProjectSemanticResult(
                base.root,
                base.config_path,
                compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
                **graft,  # pyright: ignore[reportArgumentType]
            )
    combined = {
        field: getattr(explicit_semantic, field) for field in _MODULE_SIDECAR_FIELDS
    }
    combined.update(model=object(), modules=explicit.modules)
    with pytest.raises((TypeError, ValueError)):
        ProjectSemanticResult(
            base.root,
            base.config_path,
            compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
            **combined,  # pyright: ignore[reportArgumentType]
        )


def test_invalid_mode_rejects_before_legacy_or_explicit_builder_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy = project_check.check_project_parse_only(
        _project_with_source(tmp_path / "legacy", 1)
    )
    explicit = project_check.check_project_parse_only(
        _project_with_source(tmp_path / "explicit", 2)
    )

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("forged mode reached a semantic builder")

    monkeypatch.setattr(project_model, "_build_project_semantic_catalog", forbidden)
    import pietto._project.module_catalog as module_catalog

    monkeypatch.setattr(module_catalog, "_build_project_module_catalog_set", forbidden)

    class ForeignMode(StrEnum):
        LEGACY = "legacy_flat"

    for base in (legacy, explicit):
        for forged in ("legacy_flat", ForeignMode.LEGACY, None, object()):
            candidate = replace(base)
            object.__setattr__(candidate, "compilation_mode", forged)
            with pytest.raises((TypeError, ValueError)):
                build_empty_project_semantic_result(candidate)


@pytest.mark.parametrize("schema_version", (1, 2))
def test_v1_v2_package_name_neutrality_is_exact_for_manifest_shapes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    schema_version: int,
) -> None:
    for case in ("valid", "malformed", "oversized", "unreadable", "symlink"):
        root = _project_with_source(
            tmp_path / f"v{schema_version}-{case}", schema_version
        )
        absent_config = load_project_config(root)
        absent_selection = select_project_sources(root, absent_config)
        absent_parsed = project_check.check_project_parse_only(root)
        absent_semantic = build_empty_project_semantic_result(absent_parsed)
        absent_text_exit = cli.main(["check", "--project", str(root)])
        absent_text = capsys.readouterr()
        absent_json_exit = cli.main(
            ["check", "--project", str(root), "--format", "json"]
        )
        absent_json = capsys.readouterr()
        _assert_exact_v1_v2_actual(
            root,
            schema_version,
            absent_config,
            absent_selection,
            absent_parsed,
            absent_semantic,
            absent_text_exit,
            absent_text.out,
            absent_text.err,
            absent_json_exit,
            absent_json.out,
            absent_json.err,
        )
        manifest = _write_manifest_case(root, case)
        package_config = load_project_config(root)
        package_selection = select_project_sources(root, package_config)
        package_parsed = project_check.check_project_parse_only(root)
        package_semantic = build_empty_project_semantic_result(package_parsed)
        package_text_exit = cli.main(["check", "--project", str(root)])
        package_text = capsys.readouterr()
        package_json_exit = cli.main(
            ["check", "--project", str(root), "--format", "json"]
        )
        package_json = capsys.readouterr()
        _assert_exact_v1_v2_actual(
            root,
            schema_version,
            package_config,
            package_selection,
            package_parsed,
            package_semantic,
            package_text_exit,
            package_text.out,
            package_text.err,
            package_json_exit,
            package_json.out,
            package_json.err,
        )
        assert package_config == absent_config
        assert package_selection == absent_selection
        assert package_parsed == absent_parsed
        assert package_semantic == absent_semantic
        assert package_text_exit == absent_text_exit
        assert package_text.out == absent_text.out
        assert package_text.err == absent_text.err
        assert package_json_exit == absent_json_exit
        assert package_json.out == absent_json.out
        assert package_json.err == absent_json.err
        neutral = root / "pietto-neutral.toml"
        try:
            before = manifest.lstat()
            target = os.readlink(manifest) if manifest.is_symlink() else None
            manifest.rename(neutral)
            after = neutral.lstat()
            assert before.st_ino == after.st_ino and before.st_mode == after.st_mode
            if target is not None:
                assert os.readlink(neutral) == target
        except OSError as error:
            if case == "symlink":
                pytest.skip(f"symlinks are unsupported: {error}")
            raise
        neutral_config = load_project_config(root)
        neutral_selection = select_project_sources(root, neutral_config)
        neutral_parsed = project_check.check_project_parse_only(root)
        neutral_semantic = build_empty_project_semantic_result(neutral_parsed)
        neutral_text_exit = cli.main(["check", "--project", str(root)])
        neutral_text = capsys.readouterr()
        neutral_json_exit = cli.main(
            ["check", "--project", str(root), "--format", "json"]
        )
        neutral_json = capsys.readouterr()
        _assert_exact_v1_v2_actual(
            root,
            schema_version,
            neutral_config,
            neutral_selection,
            neutral_parsed,
            neutral_semantic,
            neutral_text_exit,
            neutral_text.out,
            neutral_text.err,
            neutral_json_exit,
            neutral_json.out,
            neutral_json.err,
        )
        assert neutral_config == absent_config
        assert neutral_selection == absent_selection
        assert neutral_parsed == absent_parsed
        assert neutral_semantic == absent_semantic
        assert neutral_text_exit == absent_text_exit
        assert neutral_text.out == absent_text.out
        assert neutral_text.err == absent_text.err
        assert neutral_json_exit == absent_json_exit
        assert neutral_json.out == absent_json.out
        assert neutral_json.err == absent_json.err


def test_direct_main_external_snapshot_proof_and_negative_authorities(
    tmp_path: Path,
) -> None:
    external_message = (
        f"{_EXTERNAL_DIRECT_MAIN_SUBJECT}\n\n"
        f"{_EXTERNAL_REVIEWED_TREE_TRAILER}: {_EXTERNAL_SEALED_TREE}\n"
    )
    assert phase55_slice2_direct_main_commit_matches_external_sealed_tree(
        (_EXTERNAL_BASELINE,),
        _EXTERNAL_DIRECT_MAIN_SUBJECT,
        _EXTERNAL_SEALED_TREE,
        external_message,
        sealed_baseline=_EXTERNAL_BASELINE,
        sealed_tree=_EXTERNAL_SEALED_TREE,
    )

    source = _synthetic_complete_dirty_source(tmp_path / "source")
    baseline = _git(source, "rev-parse", "HEAD")
    baseline_tree = _git(source, "rev-parse", "HEAD^{tree}")
    assert baseline == _git(source, "rev-parse", "refs/heads/main")
    assert len(baseline) == len(baseline_tree) == 40
    assert _git(source, "branch", "--show-current") == "main"
    assert _git(source, "diff", "--cached", "--name-only") == ""
    assert _git(source, "status", "--porcelain") == "?? SLICE2-CANDIDATE.txt"
    candidate = source / "SLICE2-CANDIDATE.txt"
    assert candidate.is_file() and not candidate.is_symlink()
    _assert_no_git_operation(source)
    sealed_tree = _independent_dirty_tree(source, tmp_path / "external.index")
    assert len(sealed_tree) == 40 and sealed_tree != baseline_tree

    original_output = publication_topology._source_output
    real_builder = publication_topology.build_slice2_direct_main_topology
    call_count = 0
    baseline_reads = 0
    captured_root: Path | None = None
    advanced = ""

    def output(root: Path, *args: str) -> str:
        nonlocal baseline_reads
        if root == source and args == ("rev-parse", "refs/heads/main"):
            baseline_reads += 1
            if baseline_reads != 1:
                raise AssertionError("aggregate reread original source main")
        return original_output(root, *args)

    def builder(
        kind: str,
        root: Path,
        *,
        sealed_tree: str,
        source: Path | None = None,
        _sealed_baseline: str | None = None,
    ) -> publication_topology.TopologyFixture:
        nonlocal advanced, call_count, captured_root
        assert call_count < len(_EXTERNAL_DIRECT_MAIN_KINDS)
        assert kind == _EXTERNAL_DIRECT_MAIN_KINDS[call_count]
        call_count += 1
        if kind == _EXTERNAL_DIRECT_MAIN_KINDS[0]:
            assert source == original_source
            fixture = real_builder(
                kind,
                root,
                sealed_tree=sealed_tree,
                source=source,
                _sealed_baseline=_sealed_baseline,
            )
            assert fixture.kind == _EXTERNAL_DIRECT_MAIN_KINDS[0]
            assert (
                _independent_dirty_tree(fixture.root, tmp_path / "dirty-return.index")
                == sealed_tree
            )
            assert _git(fixture.root, "diff", "--cached", "--name-only") == ""
            _assert_no_git_operation(fixture.root)
            assert _git(fixture.root, "status", "--porcelain")
            _git(
                original_source,
                "commit",
                "--quiet",
                "--allow-empty",
                "-m",
                "Advance source after snapshot",
            )
            advanced = _git(original_source, "rev-parse", "HEAD")
            assert advanced != baseline
            assert _git(
                original_source, "rev-list", "--parents", "-n", "1", "HEAD"
            ).split()[1:] == [baseline]
            assert _git(original_source, "rev-parse", "HEAD^{tree}") == _git(
                original_source, "rev-parse", baseline + "^{tree}"
            )
            assert _git(original_source, "diff", "--cached", "--name-only") == ""
            assert (
                _independent_dirty_tree(
                    original_source, tmp_path / "original-recheck.index"
                )
                == sealed_tree
            )
            retired = original_source.with_name("source-retired")
            original_source.rename(retired)
            assert retired.exists() and not original_source.exists()
            captured_root = fixture.root
            return fixture
        assert captured_root is not None and source == captured_root
        return real_builder(
            kind,
            root,
            sealed_tree=sealed_tree,
            source=source,
            _sealed_baseline=_sealed_baseline,
        )

    original_source = source
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(publication_topology, "_source_output", output)
        patch.setattr(
            publication_topology, "build_slice2_direct_main_topology", builder
        )
        fixtures = publication_topology.build_slice2_direct_main_all(
            tmp_path / "topology",
            sealed_baseline=baseline,
            sealed_tree=sealed_tree,
            source=source,
        )
    assert baseline_reads == 1 and advanced
    assert call_count == 4
    assert captured_root is fixtures[0].root
    for fixture in fixtures:
        assert verify(fixture.observation, fixture.expectation) == ()
        assert_topology(fixture)
    observations = tuple(fixture.observation for fixture in fixtures)
    assert tuple(fixture.kind for fixture in fixtures) == _EXTERNAL_DIRECT_MAIN_KINDS
    dirty_observation, pre_push, shallow, reconciled = observations
    _, pre_push_fixture, shallow_fixture, reconciled_fixture = fixtures
    assert (
        dirty_observation.head
        == pre_push.head_parents[0]
        == reconciled.head_parents[0]
        == baseline
    )
    assert (
        _independent_dirty_tree(fixtures[0].root, tmp_path / "dirty-final.index")
        == sealed_tree
    )
    assert (
        pre_push.head_tree == shallow.head_tree == reconciled.head_tree == sealed_tree
    )
    for fixture in fixtures[1:]:
        assert fixture.observation.head_tree == sealed_tree
        assert _git(fixture.root, "rev-parse", "HEAD^{tree}") == sealed_tree
    assert pre_push.origin_main == baseline
    assert (
        pre_push.ahead == pre_push.behind == publication_topology.DIVERGENCE_UNAVAILABLE
    )
    assert (
        shallow.shallow
        and shallow.event_name == "push"
        and shallow.head == pre_push.head
    )
    assert (
        pre_push.head_parents
        == shallow.head_parents
        == reconciled.head_parents
        == (baseline,)
    )
    assert (
        pre_push.head_subject
        == shallow.head_subject
        == reconciled.head_subject
        == _EXTERNAL_DIRECT_MAIN_SUBJECT
    )
    assert pre_push.head_message == shallow.head_message == reconciled.head_message
    assert pre_push.head_trailer == shallow.head_trailer == reconciled.head_trailer
    assert (
        subprocess.run(
            ["git", "cat-file", "-e", f"{baseline}^{{commit}}"],
            cwd=shallow_fixture.root,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )
    with pytest.raises(TopologyError, match="complete history"):
        publication_topology.build_slice2_direct_main_topology(
            publication_topology.TOPOLOGY_SLICE2_DIRECT_MAIN_PRE_PUSH,
            tmp_path / "shallow-source-rejected",
            sealed_tree=sealed_tree,
            source=shallow_fixture.root,
            _sealed_baseline=shallow.head,
        )
    assert (
        reconciled.branch == "main"
        and reconciled.head == reconciled.origin_main == pre_push.head
    )
    raw_pre_push = _git_raw(pre_push_fixture.root, "cat-file", "-p", pre_push.head)
    raw_shallow = _git_raw(shallow_fixture.root, "cat-file", "-p", shallow.head)
    raw_reconciled = _git_raw(
        reconciled_fixture.root, "cat-file", "-p", reconciled.head
    )
    assert tuple(fixture.observation.head for fixture in fixtures[1:]) == (
        pre_push.head,
        pre_push.head,
        pre_push.head,
    )
    expected_message = (
        f"{_EXTERNAL_DIRECT_MAIN_SUBJECT}\n\n"
        f"{_EXTERNAL_REVIEWED_TREE_TRAILER}: {sealed_tree}\n"
    )
    for raw in (raw_pre_push, raw_shallow, raw_reconciled):
        headers, separator, message = raw.partition("\n\n")
        assert separator == "\n\n"
        lines = headers.splitlines()
        assert lines.count(f"tree {sealed_tree}") == 1
        assert lines.count(f"parent {baseline}") == 1
        tree = next(
            line.removeprefix("tree ") for line in lines if line.startswith("tree ")
        )
        parents = tuple(
            line.removeprefix("parent ") for line in lines if line.startswith("parent ")
        )
        subject = message.split("\n", maxsplit=1)[0]
        assert parents == (baseline,)
        assert subject == _EXTERNAL_DIRECT_MAIN_SUBJECT
        assert tree == sealed_tree
        assert message == expected_message
    for index, (bad_baseline, bad_tree) in enumerate(
        (
            ("A" * 40, sealed_tree),
            ("a" * 39, sealed_tree),
            ("z" * 40, sealed_tree),
            (baseline, "A" * 40),
            (baseline, "a" * 39),
            (baseline, "z" * 40),
            ("a" * 40, sealed_tree),
            (baseline, "b" * 40),
        )
    ):
        fresh = _synthetic_complete_dirty_source(tmp_path / f"negative-{index}")
        assert (
            _independent_dirty_tree(fresh, tmp_path / f"negative-{index}.index")
            == sealed_tree
        )
        with pytest.raises(TopologyError):
            build_slice2_direct_main_all(
                tmp_path / f"negative-topology-{index}",
                sealed_baseline=bad_baseline,
                sealed_tree=bad_tree,
                source=fresh,
            )
    for parents, subject, tree, text in (
        (
            (_EXTERNAL_BASELINE, "a" * 40),
            _EXTERNAL_DIRECT_MAIN_SUBJECT,
            _EXTERNAL_SEALED_TREE,
            external_message,
        ),
        ((_EXTERNAL_BASELINE,), "wrong", _EXTERNAL_SEALED_TREE, external_message),
        (
            (_EXTERNAL_BASELINE,),
            _EXTERNAL_DIRECT_MAIN_SUBJECT,
            "a" * 40,
            external_message,
        ),
        (
            (_EXTERNAL_BASELINE,),
            _EXTERNAL_DIRECT_MAIN_SUBJECT,
            _EXTERNAL_SEALED_TREE,
            external_message + "extra\n",
        ),
    ):
        assert not phase55_slice2_direct_main_commit_matches_external_sealed_tree(
            parents,
            subject,
            tree,
            text,
            sealed_baseline=_EXTERNAL_BASELINE,
            sealed_tree=_EXTERNAL_SEALED_TREE,
        )

    recovery_tree = "c" * 40
    recovery_message = (
        f"{PHASE55_SLICE2_RECOVERY_SUBJECT}\n\n"
        f"{_EXTERNAL_REVIEWED_TREE_TRAILER}: {recovery_tree}\n"
    )
    assert phase55_slice2_recovery_shape_matches_failed_publication(
        (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
        PHASE55_SLICE2_RECOVERY_SUBJECT,
        recovery_tree,
        recovery_message,
    )
    assert phase55_slice2_recovery_commit_matches_external_sealed_tree(
        (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
        PHASE55_SLICE2_RECOVERY_SUBJECT,
        recovery_tree,
        recovery_message,
        sealed_tree=recovery_tree,
    )
    assert not phase55_slice2_recovery_commit_matches_external_sealed_tree(
        (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
        PHASE55_SLICE2_RECOVERY_SUBJECT,
        recovery_tree,
        recovery_message,
        sealed_tree="d" * 40,
    )
    for parents, subject, tree, text in (
        ((), PHASE55_SLICE2_RECOVERY_SUBJECT, recovery_tree, recovery_message),
        (("d" * 40,), PHASE55_SLICE2_RECOVERY_SUBJECT, recovery_tree, recovery_message),
        (
            (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
            "wrong",
            recovery_tree,
            recovery_message,
        ),
        (
            (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
            PHASE55_SLICE2_RECOVERY_SUBJECT,
            "D" * 40,
            recovery_message,
        ),
        (
            (PHASE55_SLICE2_FAILED_PUBLISHED_HEAD,),
            PHASE55_SLICE2_RECOVERY_SUBJECT,
            recovery_tree,
            recovery_message + "extra\n",
        ),
    ):
        assert not phase55_slice2_recovery_shape_matches_failed_publication(
            parents,
            subject,
            tree,
            text,
        )


def _assert_exact_root_authority(
    root: ProjectRoot | None,
    config_path: ProjectConfigPath | None,
    pinned_root: ProjectPinnedRoot | None,
    invocation_root: Path,
) -> None:
    assert type(root) is ProjectRoot and root == ProjectRoot(path=".")
    assert type(config_path) is ProjectConfigPath
    assert config_path == ProjectConfigPath(path="pietto.toml")
    assert type(pinned_root) is ProjectPinnedRoot
    assert pinned_root.display_path == "."
    assert pinned_root.invocation_path == invocation_root.absolute()
    assert pinned_root.canonical_path == invocation_root.resolve(strict=True)
    invocation_stat = invocation_root.stat()
    canonical_stat = invocation_root.resolve(strict=True).stat()
    assert type(pinned_root.physical_identity) is ProjectPhysicalIdentity
    assert pinned_root.physical_identity == ProjectPhysicalIdentity(
        device=invocation_stat.st_dev, inode=invocation_stat.st_ino
    )
    assert pinned_root.physical_identity == ProjectPhysicalIdentity(
        device=canonical_stat.st_dev, inode=canonical_stat.st_ino
    )


def _assert_exact_v1_v2_actual(
    root: Path,
    schema_version: int,
    config: ProjectConfigLoadResult,
    selection: ProjectDiscoveryResult,
    parsed: ProjectParseCheckResult,
    semantic: ProjectSemanticResult,
    text_exit: int,
    text_out: str,
    text_err: str,
    json_exit: int,
    json_out: str,
    json_err: str,
) -> None:
    expected_mode = (
        ProjectCompilationMode.LEGACY_FLAT
        if schema_version == 1
        else ProjectCompilationMode.EXPLICIT_MODULES
    )
    assert type(config) is ProjectConfigLoadResult
    assert type(selection) is ProjectDiscoveryResult
    assert type(parsed) is ProjectParseCheckResult
    assert type(semantic) is ProjectSemanticResult
    assert config.ok and type(config.config) is ProjectConfig
    _assert_exact_root_authority(
        config.root, config.config_path, config.pinned_root, root
    )
    assert config.config.schema_version == schema_version
    assert config.config.compilation_mode is expected_mode
    assert type(config.config.sources) is ProjectSourceConfig
    assert config.config.sources == ProjectSourceConfig(("*.pietto",), ())
    assert config.config.root_package is None
    assert selection.root is config.root
    assert selection.config_path is config.config_path
    assert selection.pinned_root is config.pinned_root
    assert selection.compilation_mode is expected_mode
    assert selection.errors == ()
    assert type(selection.inputs[0]) is ProjectInput
    assert selection.inputs == (ProjectInput(path="row.pietto", status="selected"),)
    assert len(selection.modules) == 1
    selection_module = selection.modules[0]
    assert type(selection_module) is ProjectLogicalModule
    assert selection_module.compilation_mode is expected_mode
    assert selection_module.position == 0
    assert selection_module.path == "row.pietto"
    assert selection_module.identity == ProjectModuleIdentity(path="row.pietto")
    assert selection_module.project_input is selection.inputs[0]
    assert type(selection.selected_input_index) is ProjectSelectedInputIndex
    assert selection.selected_input_index.pinned_root is selection.pinned_root
    assert len(selection.selected_input_index.entries) == 1
    selected = selection.selected_input_index.entries[0]
    assert type(selected) is ProjectSelectedInputEntry
    assert selected.position == 0
    assert selected.identity == ProjectModuleIdentity(path="row.pietto")
    assert selected.project_input is selection.inputs[0]
    assert selected.canonical_path == root / "row.pietto"
    assert selection.selected_input_index.find(selected.identity) is selected
    _assert_exact_root_authority(
        parsed.root, parsed.config_path, parsed.pinned_root, root
    )
    assert parsed.compilation_mode is expected_mode
    assert parsed.errors == parsed.diagnostics == ()
    assert type(parsed.inputs[0]) is ProjectInput
    assert parsed.inputs == (ProjectInput(path="row.pietto", status="parsed"),)
    assert len(parsed.parsed_inputs) == len(parsed.modules) == 1
    parsed_input = parsed.parsed_inputs[0]
    parsed_module = parsed.modules[0]
    assert type(parsed_input) is ProjectParsedInput
    assert type(parsed_module) is ProjectLogicalModule
    assert parsed_module.compilation_mode is expected_mode
    assert parsed_input.path == parsed_module.path == "row.pietto"
    assert parsed_module.position == 0
    assert parsed_module.identity == ProjectModuleIdentity(path="row.pietto")
    assert parsed_module.project_input is parsed.inputs[0]
    assert parsed_module.parsed_input is parsed_input
    assert type(parsed.selected_input_index) is ProjectSelectedInputIndex
    assert parsed.selected_input_index.pinned_root is parsed.pinned_root
    assert len(parsed.selected_input_index.entries) == 1
    parsed_selected = parsed.selected_input_index.entries[0]
    assert type(parsed_selected) is ProjectSelectedInputEntry
    assert parsed_selected.position == 0
    assert parsed_selected.identity == ProjectModuleIdentity(path="row.pietto")
    assert type(parsed_selected.project_input) is ProjectInput
    assert parsed_selected.project_input == ProjectInput(
        path="row.pietto", status="selected"
    )
    assert parsed_selected.canonical_path == root / "row.pietto"
    assert parsed.selected_input_index.find(parsed_selected.identity) is parsed_selected
    assert len(parsed.trusted_source_snapshots) == 1
    snapshot = parsed.trusted_source_snapshots[0]
    assert type(snapshot) is ProjectTrustedSourceSnapshot
    source_text = "shape Row:\n    id: Int\n"
    assert snapshot.selected_input is parsed_selected
    assert snapshot.path == "row.pietto"
    assert snapshot.source_text == source_text
    assert snapshot.byte_count == len(source_text.encode("utf-8"))
    assert snapshot.sha256 == hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    assert semantic.root is parsed.root
    assert semantic.config_path is parsed.config_path
    assert semantic.pinned_root is parsed.pinned_root
    assert semantic.selected_input_index is parsed.selected_input_index
    assert semantic.trusted_source_snapshots is parsed.trusted_source_snapshots
    assert semantic.compilation_mode is expected_mode
    assert semantic.modules is parsed.modules
    assert semantic.diagnostics == ()
    if schema_version == 1:
        assert semantic.model is not None
        assert all(getattr(semantic, field) is None for field in _MODULE_SIDECAR_FIELDS)
    else:
        assert semantic.model is None
        assert all(
            getattr(semantic, field) is not None for field in _MODULE_SIDECAR_FIELDS
        )
    for carrier in (selection, parsed, semantic):
        assert "root_package" not in carrier.__dataclass_fields__
    if schema_version == 1:
        assert (text_exit, text_out, text_err, json_exit, json_err) == (
            0,
            "Project check OK: .\nFiles checked: 1\n",
            "",
            0,
            "",
        )
    else:
        assert (text_exit, text_out, text_err, json_exit, json_err) == (
            1,
            "",
            "",
            1,
            "",
        )
    expected_document = {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {"root": ".", "config_path": "pietto.toml"},
        "inputs": [{"path": "row.pietto", "kind": "source", "status": "parsed"}],
        "diagnostics": [],
        "cli_errors": [],
        "result": {"check": {"files_total": 1, "files_ok": 1, "files_with_errors": 0}},
    }
    document = json.loads(json_out)
    assert document == expected_document
    assert json_out == json.dumps(expected_document, ensure_ascii=True) + "\n"
    assert "pietto-package.toml" not in json_out + text_out + text_err
    assert "pietto-neutral.toml" not in json_out + text_out + text_err
    assert "package" not in document and "root_package" not in document
    assert '"package"' not in json_out
    assert "root_package" not in json_out + text_out + text_err


def _assert_no_git_operation(root: Path) -> None:
    for marker in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "REBASE_HEAD",
        "BISECT_LOG",
        "sequencer",
        "rebase-merge",
        "rebase-apply",
    ):
        path = Path(_git(root, "rev-parse", "--git-path", marker))
        assert (
            not (root / path).exists() if not path.is_absolute() else not path.exists()
        )


def _root(path: Path, text: str) -> Path:
    path.mkdir(parents=True)
    (path / "pietto.toml").write_text(text, encoding="utf-8")
    return path


def _sources_table() -> str:
    return '[sources]\ninclude = ["*.pietto"]\n'


def _sources_document(version: int) -> str:
    return f"schema_version = {version}\n\n" + _sources_table()


def _project_with_source(path: Path, schema_version: int) -> Path:
    root = _root(path, _sources_document(schema_version))
    (root / "row.pietto").write_text("shape Row:\n    id: Int\n", encoding="utf-8")
    return root


def _write_manifest_case(root: Path, case: str) -> Path:
    manifest = root / "pietto-package.toml"
    if case == "valid":
        manifest.write_text('[package]\npath = "."\n', encoding="utf-8")
    elif case == "malformed":
        manifest.write_text("not valid = [", encoding="utf-8")
    elif case == "oversized":
        manifest.write_text("x" * 2_000_000, encoding="utf-8")
    elif case == "unreadable":
        manifest.write_text("unreadable", encoding="utf-8")
        manifest.chmod(0)
    elif case == "symlink":
        target = root / "outside-package.toml"
        target.write_text("target", encoding="utf-8")
        manifest.symlink_to(target.name)
    else:
        raise AssertionError(f"unknown manifest case: {case}")
    return manifest


def _write_decoys(root: Path, package_path: str) -> None:
    for name in (
        "pietto-package.toml",
        "pietto-asset.toml",
        "pietto-dependency.toml",
        "module.pietto",
    ):
        (root / name).write_text("decoy", encoding="utf-8")
    if package_path != ".":
        nested = root / package_path
        nested.mkdir(parents=True)
        for name in ("pietto-package.toml", "asset", "dependency", "module.pietto"):
            (nested / name).write_text("decoy", encoding="utf-8")


def _synthetic_complete_dirty_source(root: Path) -> Path:
    root.mkdir()
    _git(root, "init", "--quiet", "--initial-branch", "main")
    _git(root, "config", "user.name", "Pietto Test")
    _git(root, "config", "user.email", "topology@pietto.invalid")
    (root / "BASELINE.txt").write_text("synthetic base\n", encoding="utf-8")
    _git(root, "add", "BASELINE.txt")
    _git(
        root,
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "Synthetic complete baseline",
    )
    (root / "SLICE2-CANDIDATE.txt").write_text("candidate\n", encoding="utf-8")
    return root


def _independent_dirty_tree(root: Path, index: Path) -> str:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment["GIT_INDEX_FILE"] = str(index)
    _git(root, "read-tree", "HEAD", environment=environment)
    _git(root, "add", "-A", environment=environment)
    return _git(root, "write-tree", environment=environment)


def _git(root: Path, *args: str, environment: Mapping[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _git_raw(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _package_table() -> str:
    return _package_document().split("\n\n", maxsplit=1)[1]


def _package_values(path: str = ".") -> dict[str, str]:
    token = path.replace("/", "-dot-").replace(".", "dot")
    return {
        "path": path,
        "namespace": f"namespace-{token}",
        "name": f"name-{token}",
        "version": f"version-{token}",
        "sha256": f"pin-{token}",
    }


def _package_document(
    replacements: Mapping[str, str | None] | None = None,
    *,
    raw_values: bool = False,
    order: tuple[str, ...] = ("path", "namespace", "name", "version", "sha256"),
) -> str:
    values: dict[str, str | None] = {
        "path": ".",
        "namespace": "example",
        "name": "demo",
        "version": "release",
        "sha256": "pin",
    }
    values.update(replacements or {})
    lines = ["schema_version = 3", "", "[package]"]
    for key in order:
        value = values[key]
        if value is not None:
            lines.append(
                f"{key} = {value if raw_values and key in (replacements or {}) else json.dumps(value)}"
            )
    return "\n".join(lines) + "\n"
