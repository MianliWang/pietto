from __future__ import annotations

import ast
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase50-semantic-package-model-readiness-v1.md"
TEST_PATH = REPO_ROOT / "tests/test_phase50_semantic_package_model_readiness.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
PROJECT_CONFIG_PATH = REPO_ROOT / "src/pietto/_project/config.py"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"

SLICE6_SHA = "7c7f6976dd67ccc4628757f2d857b593f71f5e0f"
SLICE6_SUBJECT = "Add Phase 50 import module export readiness"
SLICE6_CI_RUN_ID = "29139545163"
SLICE7_TITLE = "# Phase 50 Slice 7 Semantic Package Model Readiness v1"

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Package-Surface Evidence",
    "Python Distribution And Semantic Package Separation",
    "Conceptual Vocabulary",
    "Package-model Route Comparison",
    "Recommended Semantic Package Boundary",
    "Package Identity Readiness",
    "Package Version And Schema-version Readiness",
    "Package Asset Taxonomy",
    "Source-like Asset Readiness",
    "Declarative Catalog Asset Readiness",
    "Documentation And Support Asset Readiness",
    "Package Public Surface And Visibility",
    "Package Dependency Facts",
    "Package Graph And Cycle Posture",
    "Capability Requirement Readiness",
    "Dialect And Extension Requirement Readiness",
    "Provenance Digest And Trust Boundary",
    "Deterministic Ordering",
    "Manifest And Representation Readiness",
    "Project Module And Package Integration",
    "Public And Private Metadata Boundary",
    "Diagnostic And Fail-closed Matrix",
    "Package-manager Boundary",
    "Cross-phase Dependencies",
    "Bounded Phase 55 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

SEMANTIC_ASSET_KINDS = ("TYPE_ALIAS", "ENUM", "SHAPE")
SUPPORT_ASSET_KINDS = ("DOCUMENTATION", "EXAMPLE", "STATIC_TEST_VECTOR")

ALLOWED_PHASE50_SLICE7_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-semantic-package-model-readiness-v1.md",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
}

ALLOWED_PHASE50_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
}

ALLOWED_PHASE50_SLICE9_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
}

ALLOWED_PHASE50_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
}

ALLOWED_PHASE50_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-completion-audit-and-status-lock-v1.md",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
}

COMPATIBILITY_TEST_PATHS = (
    REPO_ROOT
    / "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    REPO_ROOT / "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    REPO_ROOT
    / "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    REPO_ROOT / "tests/test_phase50_type_system_gap_capability_readiness.py",
    REPO_ROOT / "tests/test_phase50_window_function_readiness.py",
    REPO_ROOT / "tests/test_phase50_import_module_export_readiness.py",
)

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
    "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "docs/spec/phase50-window-function-readiness-v1.md",
    "docs/spec/phase50-import-module-export-readiness-v1.md",
    "docs/plan/phase-4[4-9]*",
    "docs/spec/phase4[4-9]*",
    "tests/test_phase4[4-9]*.py",
    "src",
    "grammar",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "examples",
)


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()


def _dirty_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _section(path: Path, heading: str) -> str:
    text = _read(path)
    marker = f"## {heading}"
    start = text.index(marker) + len(marker)
    remainder = text[start:]
    next_offset = remainder.find("\n## ")
    return remainder if next_offset == -1 else remainder[:next_offset]


def _normalized_section(path: Path, heading: str) -> str:
    return " ".join(_section(path, heading).split())


def _string_set_assignment(source: str, assignment_name: str) -> set[str]:
    module = ast.parse(source)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == assignment_name
            for target in node.targets
        ):
            continue
        assert isinstance(node.value, ast.Set)
        values: set[str] = set()
        for element in node.value.elts:
            assert isinstance(element, ast.Constant)
            assert isinstance(element.value, str)
            values.add(element.value)
        return values
    raise AssertionError(f"assignment not found: {assignment_name}")


def test_slice7_artifacts_baseline_and_mutable_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert TEST_PATH.is_file()

    plan_status = _normalized_section(PLAN_PATH, "Status")
    spec = _read(SPEC_PATH)
    normalized_spec = " ".join(spec.split())
    assert spec.splitlines()[0] == SLICE7_TITLE
    for required in (
        "Slices 1 through 6 are complete",
        "Phase 50 Slice 6 **Import / Module / Export Readiness** completed",
        SLICE6_SHA,
        SLICE6_CI_RUN_ID,
        "CI / push",
        "completed / success",
        "exact `headSha` match",
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "29141663534",
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "29157374991",
        "Slice 8 completed",
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed",
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "29170827348",
        "Slice 9 completed",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in f"{plan_status} {normalized_spec}", required
    assert SLICE6_SUBJECT in spec
    assert "Phase 50 is complete after Slice 11 Gate 2" not in plan_status
    assert "Slice 8 completed" in plan_status
    assert "Slice 9 completed" in plan_status
    assert "Slice 10 completed" in plan_status
    assert "Slice 11 is complete" not in plan_status


def test_spec_exact_sections_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        line.removeprefix("## ") for line in spec.splitlines() if line.startswith("## ")
    )
    assert headings == REQUIRED_SPEC_SECTIONS
    assert spec.count("Slice 7 implements no compiler or runtime behavior.") == 1

    purpose = _normalized_section(SPEC_PATH, "Purpose And Slice Identity")
    for required in (
        "docs/spec/static-audit-only readiness work",
        "Slice 7 is current but incomplete in Gate 2",
        "Slices 8 through 11 remain pending and separately authorized",
        "separately authorized Gate 3 commit, push, and exact natural CI success",
        "Nothing in this contract starts Slice 8, Phases 52 through 54, or Phase 55 implementation",
    ):
        assert required in purpose, required


def test_current_semantic_package_behavior_is_absent_from_production_surfaces() -> None:
    current_evidence = _normalized_section(
        SPEC_PATH, "Current Package-Surface Evidence"
    )
    for required in (
        "Pietto currently has no semantic-package behavior",
        "readiness vocabulary only",
        "There is no current semantic-package grammar, parser rule, AST node",
        "Project JSON field",
        "Semantic Metadata Artifact field",
        "filesystem loader, resolver, registry",
    ):
        assert required in current_evidence, required

    production_text = "\n".join(
        _read(path)
        for path in (
            GRAMMAR_PATH,
            AST_PATH,
            PROJECT_MODEL_PATH,
            PROJECT_JSON_V2_PATH,
            SEMANTIC_MODEL_PATH,
            IR_MODEL_PATH,
            METADATA_MODEL_PATH,
            METADATA_BUILDER_PATH,
            CLI_PATH,
        )
    )
    for forbidden_identifier in (
        "class SemanticPackage",
        "class PackageManifest",
        "semantic_package_assets",
        "semantic_package_dependencies",
        "package_requirement_identities",
        "resolve_semantic_package",
        "load_semantic_package",
    ):
        assert forbidden_identifier not in production_text, forbidden_identifier
    assert "--package" not in _read(CLI_PATH)


def test_python_distribution_project_module_and_package_boundaries_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])
    distribution = _normalized_section(
        SPEC_PATH, "Python Distribution And Semantic Package Separation"
    )
    integration = _normalized_section(
        SPEC_PATH, "Project Module And Package Integration"
    )

    assert project["name"] == "pietto"
    assert project["version"] == "0.1.0"
    for required in (
        "is not a Pietto semantic package",
        "Wheel/sdist metadata",
        "console entry points",
        "package smoke belong to Python packaging only",
        "not a Python wheel, Python package, runtime plugin, database extension",
    ):
        assert required in distribution, required
    for required in (
        "Current project behavior remains flat, package-free, and unchanged",
        "Neither is the other",
        "already-materialized exact package set",
        "No package-qualified import syntax",
        "project config key, filesystem loader, or resolver is selected",
    ):
        assert required in integration, required
    assert "package" not in _read(PROJECT_CONFIG_PATH).lower()


def test_route_b_identity_and_version_distinctions_are_locked() -> None:
    routes = _normalized_section(SPEC_PATH, "Package-model Route Comparison")
    identity = _normalized_section(SPEC_PATH, "Package Identity Readiness")
    versions = _normalized_section(
        SPEC_PATH, "Package Version And Schema-version Readiness"
    )

    for required in (
        "Route A documentation-only bundle | rejected",
        "Route B static semantic asset bundle | selected",
        "Route C source package | deferred",
        "Route D hybrid source/catalog package | deferred",
        "Route E executable plugin package | rejected",
        "static, declarative, reviewable, deterministic, non-executable",
    ):
        assert required in routes, required
    for required in (
        "(namespace, name)",
        "namespace/name",
        "canonical lowercase ASCII slug components",
        "logically case-sensitive",
        "does not guarantee global registry uniqueness",
        "not a repository URL, project path, module path",
    ):
        assert required in identity, required
    for required in (
        "Python distribution version remains `0.1.0`",
        "required exact integer",
        "initial readiness candidate is `1`",
        "required exact SemVer string",
        "exact string equality",
        "Current project `pietto.toml` schema version remains independent",
        "No SemVer parser",
    ):
        assert required in versions, required


def test_initial_asset_taxonomy_and_executable_boundary_are_locked() -> None:
    taxonomy = _normalized_section(SPEC_PATH, "Package Asset Taxonomy")
    source_like = _normalized_section(SPEC_PATH, "Source-like Asset Readiness")
    catalogs = _normalized_section(SPEC_PATH, "Declarative Catalog Asset Readiness")
    support = _normalized_section(
        SPEC_PATH, "Documentation And Support Asset Readiness"
    )

    for kind in (*SEMANTIC_ASSET_KINDS, *SUPPORT_ASSET_KINDS):
        assert f"`{kind}`" in taxonomy, kind
    for required in (
        "readiness vocabulary only, not a production enum or schema discriminator",
        "Support assets never become compiler bindings or semantic exports",
        "No asset is currently loadable",
    ):
        assert required in taxonomy, required
    for required in (
        "Source files, local modules, module export surfaces",
        "tables, queries, constraints, derives",
        "are not initial assets",
    ):
        assert required in source_like, required
    for required in (
        "Function and aggregate signatures",
        "capability profiles, dialect profiles, extension profiles",
        "extension signature catalogs remain deferred",
        "does not initially provide or embed any profile or catalog",
    ):
        assert required in catalogs, required
    for required in (
        "declared input and expected data only",
        "no runner, hook, command, shell script",
        "never a semantic binding export",
    ):
        assert required in support, required


def test_visibility_dependency_and_no_package_manager_postures_are_locked() -> None:
    visibility = _normalized_section(SPEC_PATH, "Package Public Surface And Visibility")
    dependencies = _normalized_section(SPEC_PATH, "Package Dependency Facts")
    manager = _normalized_section(SPEC_PATH, "Package-manager Boundary")

    for required in (
        "semantic assets are private by default",
        "explicit ordered list of locally owned semantic asset identities",
        "Imported or dependency-owned assets cannot be exported",
        "Wildcard export, export-all",
        "dependency re-export",
        "transitive or registry-derived visibility are prohibited",
    ):
        assert required in visibility, required
    for required in (
        "target package `namespace/name`",
        "exact target release version",
        "optional expected digest fact",
        "exact equality only",
        "already-materialized package set",
        "There is no solving, fetching, downloading, installation, caching, updating",
        "lockfile generation, or lockfile consumption",
    ):
        assert required in dependencies, required
    for required in (
        "remain `OUTSIDE_51_60`",
        "Python plugins, entry points, hooks, lifecycle actions",
        "Phase 55 requires no package manager",
    ):
        assert required in manager, required


def test_graph_cycle_requirement_and_phase_ownership_are_locked() -> None:
    graph = _normalized_section(SPEC_PATH, "Package Graph And Cycle Posture")
    capability = _normalized_section(SPEC_PATH, "Capability Requirement Readiness")
    dialect = _normalized_section(
        SPEC_PATH, "Dialect And Extension Requirement Readiness"
    )

    for required in (
        "future private package graph",
        "separate future asset graph",
        "separate from project-local module, relation dependency, row dependency/lineage",
        "package dependency cycle",
        "cross-asset cycle",
        "fail closed with no semantic winner",
        "No package or asset graph is implemented",
    ):
        assert required in graph, required
    for required in (
        "language/compiler, scalar/operator, aggregate, and future window",
        "`requires`, `provides`, `contains a profile`, and `active project declares available` are distinct facts",
        "do not provide or embed capability profiles",
        "Phase 56 owns profile schema",
    ):
        assert required in capability, required
    for required in (
        "exact dialect-profile and extension-profile requirement identities",
        "does not contain extension signature catalogs initially",
        "Phase 57 owns PostgreSQL extension signature catalogs",
        "No connection, introspection, discovery, installation",
    ):
        assert required in dialect, required


def test_provenance_manifest_metadata_and_diagnostic_boundaries_are_locked() -> None:
    provenance = _normalized_section(SPEC_PATH, "Provenance Digest And Trust Boundary")
    ordering = _normalized_section(SPEC_PATH, "Deterministic Ordering")
    manifest = _normalized_section(SPEC_PATH, "Manifest And Representation Readiness")
    metadata = _normalized_section(SPEC_PATH, "Public And Private Metadata Boundary")
    diagnostics = _normalized_section(SPEC_PATH, "Diagnostic And Fail-closed Matrix")

    for required in (
        "source repository locator, source revision",
        "externally supplied package digest",
        "authorizes no network fetch",
        "not VCS verification",
        "digest is not package identity",
        "neither computed nor verified",
        "signatures, attestations, verification, signing",
    ):
        assert required in provenance, required
    for required in (
        "Package releases order by `namespace/name`",
        "Assets retain source order",
        "Duplicate validation occurs before canonicalization",
    ):
        assert required in ordering, required
    for required in (
        "package-specific strict TOML manifest",
        "separate from current project `pietto.toml`",
        "unknown-key rejection",
        "does not select the filename, exact key spelling",
        "parser, serializer, canonical byte format, digest algorithm",
    ):
        assert required in manifest, required
    for required in (
        "Project JSON v2 and Semantic Metadata Artifact v1 contain no package identity",
        "Phase 45 through 49 carriers remain private",
        "Slice 7 adds no Project JSON or public metadata field",
    ):
        assert required in metadata, required
    for required in (
        "fail closed",
        "No failure receives a semantic winner",
        "adds or reserves no existing or new Pietto diagnostic code",
    ):
        assert required in diagnostics, required


def test_bounded_phase55_handoff_deferrals_and_release_boundary_are_locked() -> None:
    handoff = _normalized_section(SPEC_PATH, "Bounded Phase 55 Handoff")
    deferrals = _normalized_section(SPEC_PATH, "Explicit Deferrals And Non-goals")
    release = _normalized_section(SPEC_PATH, "Package Version And Release Boundary")
    stop = _normalized_section(SPEC_PATH, "Separate Authorization And Stop Conditions")

    for required in (
        "Phase 55 — Semantic Package Asset Schema remains `READINESS_CONTRACT_ONLY`, readiness-only, unstarted",
        "Route B static non-executable bundle",
        "private-by-default explicit local semantic exports",
        "exact dependency facts without solving or fetching",
        "package-specific strict TOML direction",
        "does not define production implementation slices or authorize behavior",
    ):
        assert required in handoff, required
    for required in (
        "production package model, loader, resolver, package graph, solver",
        "profile/catalog assets",
        "diagnostics, IR, SQL, CLI, JSON, public metadata",
        "Slice 8 is not begun",
        "Phases 52, 53, and 54 are not begun or modified",
        "Phase 55 implementation is not begun",
        "No production package API is designed",
    ):
        assert required in deferrals, required
    for required in (
        "Package version remains `0.1.0`",
        "No package version bump, tag, release, publish, upload, signing, or attestation",
    ):
        assert required in release, required
    for required in (
        "Slice 7 is not complete in Gate 2",
        "Slices 8 through 11 remain pending",
        "Phase 55 remains readiness-only and unstarted",
        "focused validation fails",
    ):
        assert required in stop, required


def test_all_phase50_slice7_allowlists_and_plan_scope_are_exact() -> None:
    for test_path in (*COMPATIBILITY_TEST_PATHS, TEST_PATH):
        assert (
            _string_set_assignment(
                _read(test_path), "ALLOWED_PHASE50_SLICE7_GATE2_PATHS"
            )
            == ALLOWED_PHASE50_SLICE7_GATE2_PATHS
        ), test_path

    allowlist = _normalized_section(PLAN_PATH, "Slice 7 Gate 2 Allowlist")
    assert "limited to exactly" in allowlist
    assert "No tenth repository path is approved" in allowlist
    assert len(ALLOWED_PHASE50_SLICE7_GATE2_PATHS) == 9
    for relative_path in ALLOWED_PHASE50_SLICE7_GATE2_PATHS:
        assert relative_path in allowlist, relative_path

    for test_path in (*COMPATIBILITY_TEST_PATHS, TEST_PATH):
        assert (
            _string_set_assignment(
                _read(test_path), "ALLOWED_PHASE50_SLICE8_GATE2_PATHS"
            )
            == ALLOWED_PHASE50_SLICE8_GATE2_PATHS
        ), test_path


def test_protected_paths_version_tag_staging_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    for relative_path in PROTECTED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path
    assert _dirty_paths() in (
        set(),
        ALLOWED_PHASE50_SLICE7_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
    )
