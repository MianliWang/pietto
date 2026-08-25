from __future__ import annotations

from dataclasses import fields
import inspect
from pathlib import Path

import pytest

import pietto
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
from pietto._project_explain.model import ProjectExplainEnvelope, ProjectExplainFormat
from pietto._project_explain.portability_projection import (
    ProjectExplainPortabilityClassification,
    ProjectExplainPortabilityReason,
)
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeBuildResult,
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)


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


def test_runtime_result_and_owner_remain_private_and_do_not_steal_slice14() -> None:
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
    assert "runtime_builder" not in cli_source
    explain_start = cli_source.index("def _configure_explain_parser")
    explain_end = cli_source.index("\ndef ", explain_start + 1)
    assert '"--project"' not in cli_source[explain_start:explain_end]
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
