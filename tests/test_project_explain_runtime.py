from __future__ import annotations

from dataclasses import fields
import inspect
import json
from pathlib import Path

import pytest

import pietto
import pietto.cli as cli
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.runtime_builder as runtime_builder
from pietto._project.capability_inspection import (
    CapabilityInspectionRequirementDeclaration,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    build_package_capability_checking_matrix,
)
from pietto._project.config import load_project_config
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_loader import (
    LoadedRootPackage,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluationState,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainCatalogSelectionOutcome,
)
from pietto._project_explain.model import (
    ProjectExplainEnvelope,
    ProjectExplainFormat,
    ProjectExplainLocation,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from pietto._project_explain.portability_projection import (
    ProjectExplainPortabilityClassification,
    ProjectExplainPortabilityReason,
)
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeBuildResult,
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"
EXTENSION_REQUIREMENT = '''[[capability_requirements.entries]]
domain = "extension_signature"
operation = "vector-native-type"
operands = []
dialect = "postgresql"
extension = "vector"'''
EXTENSION_SELECTOR = '''[[extension_signature_selectors]]
requirement_position = 0
family = "native_type"
physical_name = "vector"'''
LOGICAL_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "Int"
operands = []"""


def _manifest(
    schema_version: int,
    *,
    namespace: str = "example",
    name: str = "root",
    requirements: tuple[str, ...] | None = None,
    selectors: tuple[str, ...] = (),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        'version = "1.0.0"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    for dep_namespace, dep_name, release, digest, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{dep_name}"',
                f'version = "{release}"',
                f'sha256 = "{digest}"',
                f'path = "{path}"',
            )
        )
    if requirements is not None:
        lines.extend(
            (
                "",
                "[capability_requirements]",
                'namespace = "requirements"',
                'name = "runtime"',
            )
        )
        for requirement in requirements:
            lines.extend(("", requirement))
    for selector in selectors:
        lines.extend(("", selector))
    return ("\n".join(lines) + "\n").encode()


def _project_config(
    package_path: str,
    digest: str,
    *,
    targets: bool,
    vector_overlay: bool = True,
) -> str:
    lines = [
        "schema_version = 4",
        "",
        "[package]",
        f'path = "{package_path}"',
        'namespace = "example"',
        'name = "root"',
        'version = "1.0.0"',
        f'sha256 = "{digest}"',
        "",
        "[capability_environment]",
    ]
    if not targets:
        return "\n".join(lines) + "\n"
    lines.extend(
        (
            "",
            "[[capability_environment.profiles]]",
            'namespace = "profiles"',
            'name = "base"',
            'release = "r1"',
            'kind = "base"',
            'database_family = "PostgreSQL"',
            'database_release = "18"',
        )
    )
    if vector_overlay:
        lines.extend(
            (
                "",
                "[[capability_environment.profiles]]",
                'namespace = "profiles"',
                'name = "vector"',
                'release = "r1"',
                'kind = "overlay"',
                'database_family = "PostgreSQL"',
                'database_release = "18"',
                'extension_identity = "vector"',
                'extension_release = "0.8.6"',
                'base_namespace = "profiles"',
                'base_name = "base"',
                'base_release = "r1"',
                "",
                "[[capability_environment.profiles.facts]]",
                'support = "supported"',
                'domain = "extension_signature"',
                'operation = "vector-native-type"',
                "operands = []",
                'dialect = "postgresql"',
                'extension = "vector"',
            )
        )
    lines.extend(
        (
            "",
            "[[capability_environment.targets]]",
            'database_family = "PostgreSQL"',
            'database_release = "18"',
            'base_profile_namespace = "profiles"',
            'base_profile_name = "base"',
            'base_profile_release = "r1"',
        )
    )
    if vector_overlay:
        lines.extend(
            (
                "",
                "[[capability_environment.targets.overlays]]",
                'namespace = "profiles"',
                'name = "vector"',
                'release = "r1"',
            )
        )
    return "\n".join(lines) + "\n"


def _write_package(path: Path, manifest: bytes, source: bytes = SOURCE) -> str:
    path.mkdir(parents=True)
    (path / "pietto-package.toml").write_bytes(manifest)
    (path / "main.pietto").write_bytes(source)
    return _compute_package_content_sha256(manifest, (("main.pietto", source),))


def _write_project(
    tmp_path: Path,
    manifest: bytes,
    *,
    targets: bool,
    vector_overlay: bool = True,
    source: bytes = SOURCE,
    name: str = "project",
) -> Path:
    root = tmp_path / name
    package_path = root / "package"
    digest = _write_package(package_path, manifest, source)
    root.mkdir(exist_ok=True)
    (root / "pietto.toml").write_text(
        _project_config(
            "package",
            digest,
            targets=targets,
            vector_overlay=vector_overlay,
        ),
        encoding="utf-8",
    )
    return root


def _loaded_root(root: Path) -> LoadedRootPackage:
    config_result = load_project_config(root)
    assert config_result.ok and config_result.config is not None
    assert config_result.pinned_root is not None
    activation = config_result.config.root_package
    assert activation is not None
    located = _locate_root_package(config_result.pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return loaded.loaded_package


def _schema3_extension_manifest() -> bytes:
    return _manifest(
        3,
        requirements=(EXTENSION_REQUIREMENT,),
        selectors=(EXTENSION_SELECTOR,),
    )


def test_real_schema3_runtime_chain_builds_successful_exact_envelope(
    tmp_path: Path,
) -> None:
    root = _write_project(tmp_path, _schema3_extension_manifest(), targets=True)

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    assert result.envelope.ok and result.envelope.diagnostics == ()
    payload = result.envelope.payload
    assert payload is not None
    assert len(payload.package_requirements.packages) == 1
    assert len(payload.package_requirements.requirements) == 1
    assert len(payload.compatibility.targets) == 1
    cell = payload.compatibility.rows[0].cells[0]
    assert cell.state is ProjectExplainEvaluationState.CHECKED
    assert cell.checked_status is ProjectExplainCheckedStatus.SATISFIED
    assert len(payload.extension_catalog_evidence.contexts) == 1
    evidence = payload.extension_catalog_evidence.contexts[0].requirements[0]
    assert evidence.selection.outcome is ProjectExplainCatalogSelectionOutcome.SELECTED
    assert payload.portability.classification is (
        ProjectExplainPortabilityClassification.PORTABLE
    )
    assert result == _build_project_explain_runtime(root)


@pytest.mark.parametrize(
    ("manifest", "collection_count", "requirement_count", "declaration"),
    (
        (_manifest(1), 0, 0, CapabilityInspectionRequirementDeclaration.UNDECLARED),
        (
            _manifest(2, requirements=()),
            1,
            0,
            CapabilityInspectionRequirementDeclaration.DECLARED,
        ),
        (
            _manifest(2, requirements=(EXTENSION_REQUIREMENT,)),
            1,
            1,
            CapabilityInspectionRequirementDeclaration.DECLARED,
        ),
    ),
    ids=("undeclared", "declared-empty", "declared-nonempty"),
)
def test_zero_targets_preserve_all_three_declaration_states_without_cells(
    tmp_path: Path,
    manifest: bytes,
    collection_count: int,
    requirement_count: int,
    declaration: CapabilityInspectionRequirementDeclaration,
) -> None:
    root = _write_project(
        tmp_path,
        manifest,
        targets=False,
        name=f"zero-{collection_count}-{requirement_count}",
    )
    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    payload = result.envelope.payload
    assert payload is not None
    assert len(payload.package_requirements.requirement_collections) == collection_count
    assert len(payload.package_requirements.requirements) == requirement_count
    assert payload.compatibility.targets == ()
    assert payload.compatibility.package_target_evaluations == ()
    assert len(payload.compatibility.rows) == requirement_count
    assert all(row.cells == () for row in payload.compatibility.rows)
    assert payload.extension_catalog_evidence.contexts == ()
    assert payload.portability.classification is (
        ProjectExplainPortabilityClassification.INDETERMINATE
    )
    assert payload.portability.reason is (
        ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
    )

    package = _loaded_root(root)
    binding = _package_capability_requirement_binding(package)
    matrix = build_package_capability_checking_matrix(package, binding, ())
    facts = build_capability_inspection(matrix)
    assert matrix.contexts == matrix.columns == ()
    assert len(matrix.rows) == requirement_count
    assert all(row.cells == () for row in matrix.rows)
    assert facts.inspection.requirement_declaration is declaration
    assert facts.inspection.target_count == 0
    assert facts.inspection.requirement_count == requirement_count
    assert facts.canonical_bytes


def test_dependency_package_keeps_its_own_selector_with_shared_project_target(
    tmp_path: Path,
) -> None:
    root = tmp_path / "dependency-project"
    dependency_manifest = _manifest(
        3,
        namespace="example",
        name="dependency",
        requirements=(EXTENSION_REQUIREMENT,),
        selectors=(EXTENSION_SELECTOR,),
    )
    dependency_digest = _write_package(root / "dependency", dependency_manifest)
    root_manifest = _manifest(
        1,
        dependencies=(
            ("example", "dependency", "1.0.0", dependency_digest, "../dependency"),
        ),
    )
    root_digest = _write_package(root / "root", root_manifest)
    (root / "pietto.toml").write_text(
        _project_config("root", root_digest, targets=True),
        encoding="utf-8",
    )

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    payload = result.envelope.payload
    assert payload is not None
    assert tuple(
        (package.coordinate.name, package.position)
        for package in payload.package_requirements.packages
    ) == (("dependency", 0), ("root", 1))
    request = payload.package_requirements.requirements[0]
    assert request.declared_by == 0 and request.requested_by == 1
    assert payload.compatibility.rows[0].cells[0].checked_status is (
        ProjectExplainCheckedStatus.SATISFIED
    )
    assert payload.extension_catalog_evidence.contexts[0].package_position == 0


def test_schema2_extension_requirement_is_valid_but_nonempty_runtime_is_diagnostic(
    tmp_path: Path,
) -> None:
    root = _write_project(
        tmp_path,
        _manifest(2, requirements=(EXTENSION_REQUIREMENT,)),
        targets=True,
    )

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
    assert not result.envelope.ok and result.envelope.payload is None
    assert tuple(diagnostic.code for diagnostic in result.envelope.diagnostics) == (
        "not_evidenced",
    )


def test_schema2_nonextension_requirement_remains_valid_with_a_real_target(
    tmp_path: Path,
) -> None:
    root = _write_project(
        tmp_path,
        _manifest(2, requirements=(LOGICAL_REQUIREMENT,)),
        targets=True,
    )

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    payload = result.envelope.payload
    assert payload is not None
    assert len(payload.compatibility.targets) == 1
    assert len(payload.compatibility.rows) == 1
    assert payload.extension_catalog_evidence.contexts == ()


def test_missing_project_extension_release_authority_fails_without_fallback(
    tmp_path: Path,
) -> None:
    root = _write_project(
        tmp_path,
        _schema3_extension_manifest(),
        targets=True,
        vector_overlay=False,
    )

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
    assert not result.envelope.ok and result.envelope.payload is None
    assert tuple(diagnostic.code for diagnostic in result.envelope.diagnostics) == (
        "extension_catalog_target_mismatch",
    )


def test_package_parse_failure_is_diagnostic_and_missing_root_is_resource(
    tmp_path: Path,
) -> None:
    broken = _write_project(
        tmp_path,
        _manifest(1),
        targets=False,
        source=b"shape Broken {\n",
        name="broken",
    )
    diagnostic = _build_project_explain_runtime(broken)
    resource = _build_project_explain_runtime(tmp_path / "missing")

    assert diagnostic.outcome is ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
    assert diagnostic.envelope.payload is None
    assert diagnostic.envelope.diagnostics[0].severity.value == "error"
    assert diagnostic.envelope.diagnostics[0].code.startswith("PIE-P")
    assert resource.outcome is ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR
    assert resource.envelope.payload is None
    assert resource.envelope.diagnostics[0].code == "project_root"


def test_package_locations_keep_their_path_kind_and_name_a_dependency(
    tmp_path: Path,
) -> None:
    # A root manifest schema error names the manifest by its project path.
    invalid = _write_project(
        tmp_path,
        _manifest(1).replace(b"schema_version = 1\n", b""),
        targets=False,
        name="invalid",
    )
    diagnostics = _build_project_explain_runtime(invalid).envelope.diagnostics
    assert [
        (d.code, d.location.path.kind, d.location.path.value)
        for d in diagnostics
        if d.location is not None and d.location.path is not None
    ] == [
        (
            "config_schema",
            ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            "package/pietto-package.toml",
        )
    ]
    # A dependency's own failure names that package.
    root = tmp_path / "dependency-project"
    dependency_digest = _write_package(
        root / "dependency",
        _manifest(1, namespace="example", name="dependency"),
        b"shape Broken:\n\n    id Int\n",
    )
    root_digest = _write_package(
        root / "root",
        _manifest(
            1,
            dependencies=(
                ("example", "dependency", "1.0.0", dependency_digest, "../dependency"),
            ),
        ),
    )
    (root / "pietto.toml").write_text(
        _project_config("root", root_digest, targets=False), encoding="utf-8"
    )
    result = _build_project_explain_runtime(root)
    assert [(d.code, d.message) for d in result.envelope.diagnostics] == [
        (
            "PIE-P1000",
            "In dependency package example/dependency@1.0.0: Missing ':' before 'Int'.",
        )
    ]


_SCHEMA3_CONVERSION = (
    " This schema version 3 package-root project converts in one step: set "
    "schema_version to 4 and add an empty [capability_environment] table."
)


@pytest.mark.parametrize(
    ("config", "commands", "conversion"),
    (
        (
            'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n',
            " Use check --project for this schema version 1 project.",
            "",
        ),
        (
            'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
            " Use check --project and emit-sql --project for this schema version 2"
            " project.",
            "",
        ),
        (
            'schema_version = 3\n[package]\npath = "pkg"\nnamespace = "test"\n'
            f'name = "example"\nversion = "1.0.0"\nsha256 = "{"a" * 64}"\n',
            "",
            _SCHEMA3_CONVERSION,
        ),
    ),
    ids=("schema1", "schema2", "schema3"),
)
def test_a_root_below_schema4_is_refused_with_the_commands_that_read_it(
    tmp_path: Path, config: str, commands: str, conversion: str
) -> None:
    (tmp_path / "pietto.toml").write_text(config, encoding="utf-8")

    result = _build_project_explain_runtime(tmp_path)

    assert result.outcome is ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR
    assert result.envelope.payload is None
    assert [
        (item.code, item.severity, item.location, item.message, item.suggestion)
        for item in result.envelope.diagnostics
    ] == [
        (
            "config_schema",
            Severity.ERROR,
            ProjectExplainLocation(
                path=ProjectExplainLogicalPath(
                    kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                    value="pietto.toml",
                ),
                line=None,
                column=None,
                end_line=None,
                end_column=None,
            ),
            "Project Explain runtime requires project schema version 4." + commands,
            "explain --project reads only a schema version 4 package-root project, "
            "and changing schema_version alone does not convert a project."
            + conversion,
        )
    ]
    if conversion:
        # The one step is the whole conversion of the configuration.
        (tmp_path / "pietto.toml").write_text(
            config.replace("schema_version = 3", "schema_version = 4")
            + "[capability_environment]\n",
            encoding="utf-8",
        )
        converted = load_project_config(tmp_path)
        assert converted.ok and converted.config is not None
        assert converted.config.schema_version == 4


def test_runtime_result_remains_private_and_slice14_consumer_is_narrow() -> None:
    assert tuple(member.value for member in ProjectExplainRuntimeOutcome) == (
        "success",
        "diagnostic_error",
        "usage_or_resource_error",
    )
    assert tuple(field.name for field in fields(ProjectExplainRuntimeBuildResult)) == (
        "outcome",
        "envelope",
    )
    assert tuple(inspect.signature(_build_project_explain_runtime).parameters) == (
        "project_root",
    )
    assert runtime_builder.__all__ == ()
    for module in (pietto, project_package, project_explain_package):
        assert not hasattr(module, "ProjectExplainRuntimeOutcome")
        assert not hasattr(module, "ProjectExplainRuntimeBuildResult")
        assert not hasattr(module, "_build_project_explain_runtime")
    source = Path(runtime_builder.__file__).read_text(encoding="utf-8")
    assert "def select_extension_catalog" not in source
    assert "def check_package_capability_requirements" not in source
    assert "def _project_package_requirement_provenance" not in source
    assert "tomllib" not in source
    assert "serialize_project_explain_json_document" not in source
    assert "read_text(" not in source and "read_bytes(" not in source
    cli_source = (REPO_ROOT / "src/pietto/cli.py").read_text(encoding="utf-8")
    assert "pietto._project_explain.runtime_builder" in cli_source
    assert cli_source.count("_build_project_explain_runtime(root)") == 1
    explain_start = cli_source.index("def _configure_explain_parser")
    explain_end = cli_source.index("\ndef ", explain_start + 1)
    assert '"--project"' in cli_source[explain_start:explain_end]
    assert tuple(field.name for field in fields(ProjectExplainEnvelope)) == (
        "format",
        "ok",
        "diagnostics",
        "payload",
    )
    assert ProjectExplainFormat.PROJECT_EXPLAIN_V1.value == (
        "pietto.project-explain.v1"
    )


def test_spec_inventory_and_slice14_handoff_are_exact() -> None:
    spec_path = (
        REPO_ROOT / "docs/spec/phase58-slice13-project-explain-runtime-builder-v1.md"
    )
    spec = spec_path.read_text(encoding="utf-8")
    for required in (
        "_build_project_explain_runtime(project_root)",
        "PackageInspectionFactSet",
        "ProjectCapabilityEnvironmentAuthority",
        "ProjectExplainEnvelope[ProjectExplainPayload]",
        "undeclared binding",
        "declared-empty binding",
        "declared non-empty binding",
        "Availability is not\nselection",
        "Slice 14 remains next and unstarted",
        "PHASE58_SLICE13_SELF_OWNED_OPEN = 0",
    ):
        assert required in spec
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert 'f"{prefix}/_project_explain/runtime_builder.py"' in smoke
    assert "import pietto._project_explain.runtime_builder" in smoke


# Every gated relation-block form; explain never reads relation bodies.
RELATION_BLOCK_MODULE = (
    "query q(a: Int,):\n"
    "    let l:\n"
    "        capture rows\n"
    "        from generate_series(1, 2, 1) as n\n"
    "        select:\n"
    "            n\n"
    "    let inner:\n"
    "        values(id: Int)\n"
    "    from rows\n"
    "    where scalar l.n in l and exists inner\n"
    "    select:\n"
    "        id\n"
)


def test_package_root_explain_keeps_its_boundary_without_reading_bodies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = (
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        + RELATION_BLOCK_MODULE
        + "export query q\n"
    )
    root = _write_project(
        tmp_path,
        _schema3_extension_manifest(),
        targets=True,
        source=source.encode(),
    )

    assert cli.main(["explain", "--project", str(root), "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is True
    assert captured.err == ""
