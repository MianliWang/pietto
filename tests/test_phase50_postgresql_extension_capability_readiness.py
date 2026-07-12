from __future__ import annotations

import ast
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md"
)
TEST_PATH = (
    REPO_ROOT / "tests/test_phase50_postgresql_extension_capability_readiness.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
CONNECTOR_PATH = REPO_ROOT / "src/pietto/semantic/source_connectors.py"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_PATH = REPO_ROOT / "src/pietto/sql/postgres.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
POSTGRES_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/relations.py"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PROJECT_JSON_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"

SLICE7_SHA = "a5bc07855a0994343475ba546504e64b16fc7e63"
SLICE7_SUBJECT = "Add Phase 50 semantic package model readiness"
SLICE7_CI_RUN_ID = "29141663534"
SLICE8_SHA = "9e2c0f0ddcc2047e35985e6b97daa8bf29979914"
SLICE8_SUBJECT = "Add Phase 50 PostgreSQL extension capability readiness"
SLICE8_CI_RUN_ID = "29157374991"
SLICE9_SHA = "f886589ac2f64eeb3770c914e7c049e2da105daa"
SLICE9_SUBJECT = "Add Phase 50 multi-dialect capability readiness"
SLICE9_CI_RUN_ID = "29170827348"
SLICE10_SHA = "9bc6ed82f3741e3c242981bb88edfb50c73fc586"
SLICE10_SUBJECT = "Add Phase 50 explain public metadata boundary"
SLICE10_CI_RUN_ID = "29179160024"
SLICE8_TITLE = "# Phase 50 Slice 8 PostgreSQL Extension Capability Readiness v1"

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current PostgreSQL Base Behavior",
    "Current Extension-Surface Evidence",
    "Conceptual Vocabulary",
    "Extension-model Route Comparison",
    "Recommended PostgreSQL Extension Boundary",
    "Extension Identity Readiness",
    "Extension And Catalog Version Readiness",
    "PostgreSQL Base And Extension Overlay",
    "Signature-Catalog Entry Taxonomy",
    "Extension Type And Native-mapping Readiness",
    "Scalar Function Signature Readiness",
    "Aggregate Signature Readiness",
    "Operator Signature Readiness",
    "Cast Readiness",
    "Overload And Conflict Posture",
    "Extension Requirement And Availability",
    "Extension Dependency Readiness",
    "Example Extension-family Matrix",
    "Deterministic Ordering",
    "Package Profile And Catalog Integration",
    "Provenance Digest And Trust Boundary",
    "Public And Private Metadata Boundary",
    "Diagnostic And Fail-closed Matrix",
    "Cross-phase Dependencies",
    "Bounded Phase 57 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

CATALOG_ENTRY_FAMILIES = (
    "extension-scoped logical/native type pair",
    "fixed typed scalar function signature",
    "fixed typed aggregate signature",
    "unary/binary operator typed signature",
    "explicit cast signature",
)

EXAMPLE_EXTENSIONS = ("PostGIS", "pgvector", "pg_trgm", "TimescaleDB")

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

PHASE50_TEST_PATHS = tuple(
    REPO_ROOT / path
    for path in sorted(
        relative_path
        for relative_path in ALLOWED_PHASE50_SLICE8_GATE2_PATHS
        if relative_path.startswith("tests/")
    )
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
    "docs/spec/phase50-semantic-package-model-readiness-v1.md",
    "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md",
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
    "examples",
)


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


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


def test_slice8_artifacts_baseline_and_mutable_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert TEST_PATH.is_file()

    status = _normalized_section(PLAN_PATH, "Status")
    baseline = _normalized_section(PLAN_PATH, "Trusted Baseline")
    spec = _read(SPEC_PATH)
    assert spec.splitlines()[0] == SLICE8_TITLE
    for required in (
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        SLICE7_SHA,
        SLICE7_CI_RUN_ID,
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        SLICE8_SHA,
        SLICE8_CI_RUN_ID,
        "Slice 8 completed",
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed",
        SLICE9_SHA,
        SLICE9_CI_RUN_ID,
        "Slice 9 completed",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in status, required
    for required in (SLICE10_SHA, SLICE10_SUBJECT, SLICE10_CI_RUN_ID):
        assert required in baseline, required
    assert "Phase 50 is complete after Slice 11 Gate 2" not in status
    assert "Slice 8 completed" in status
    assert "Slice 9 completed" in status
    assert "Slice 10 completed" in status
    assert "Slice 11 is complete" not in status


def test_spec_exact_sections_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        line.removeprefix("## ") for line in spec.splitlines() if line.startswith("## ")
    )
    assert headings == REQUIRED_SPEC_SECTIONS
    assert spec.count("Slice 8 implements no compiler or runtime behavior.") == 1

    purpose = _normalized_section(SPEC_PATH, "Purpose And Slice Identity")
    for required in (
        "docs/spec/static-audit-only readiness work",
        "Slices 1 through 7 are complete",
        "Slice 8 is current but incomplete in Gate 2",
        "Slices 9 through 11 remain pending and separately authorized",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, unstarted",
        "designs no production extension API",
    ):
        assert required in purpose, required


def test_current_postgresql_base_and_connector_facts_are_bounded() -> None:
    connector = _read(CONNECTOR_PATH)
    catalog = _read(CATALOG_PATH)
    aggregates = _read(AGGREGATES_PATH)
    postgres = _read(POSTGRES_PATH)
    expressions = _read(POSTGRES_EXPRESSIONS_PATH)
    relations = _read(POSTGRES_RELATIONS_PATH)
    base = _normalized_section(SPEC_PATH, "Current PostgreSQL Base Behavior")

    assert '_POSTGRES_TABLE = "postgres.table"' in connector
    assert '_MYSQL_TABLE = "mysql.table"' in connector
    assert "def emit_postgres_sql(" in postgres
    for signature in (
        'BuiltinFunction("lower", ("Text",), "Text")',
        'BuiltinFunction("trim", ("Text",), "Text")',
        'BuiltinFunction("len", ("Text",), "Int")',
        'BuiltinFunction("matches", ("Text", "Text"), "Bool")',
    ):
        assert signature in catalog, signature
    for aggregate_name in ("count", "count_distinct", "sum", "avg", "min", "max"):
        assert f'"{aggregate_name}"' in aggregates, aggregate_name
    assert 'connector.name != "postgres.table"' in relations
    assert "_COMPARISON_OPERATORS" in expressions
    for required in (
        "bounded PostgreSQL compilation",
        "static `postgres.table` connector contract",
        "performs no connection, discovery, introspection, schema inspection, or database execution",
        "PostgreSQL lowering proves only the reviewed compiler surface",
    ):
        assert required in base, required


def test_current_extension_behavior_and_carriers_are_absent() -> None:
    production = "\n".join(
        _read(path)
        for path in (
            GRAMMAR_PATH,
            AST_PATH,
            CONNECTOR_PATH,
            CATALOG_PATH,
            AGGREGATES_PATH,
            IR_MODEL_PATH,
            POSTGRES_PATH,
            POSTGRES_EXPRESSIONS_PATH,
            POSTGRES_RELATIONS_PATH,
            PROJECT_MODEL_PATH,
            PROJECT_JSON_PATH,
        )
    )
    for absent in (
        "class PostgreSqlExtension",
        "class ExtensionProfile",
        "class ExtensionCatalog",
        "extension_profile_identity",
        "extension_signature_catalog",
        "declared_available_extensions",
        "extension_requirements",
        "extension_aware_lowering",
    ):
        assert absent not in production, absent

    evidence = _normalized_section(SPEC_PATH, "Current Extension-Surface Evidence")
    for required in (
        "Extension-profile vocabulary is readiness-only",
        "Concrete PostgreSQL extension support is explicitly deferred",
        "custom extension signature-catalog schema is not evidenced",
        "There is no current extension grammar",
        "Project JSON field, or public metadata field",
    ):
        assert required in evidence, required


def test_connector_backend_and_extension_false_positive_boundaries_are_locked() -> None:
    evidence = _normalized_section(SPEC_PATH, "Current Extension-Surface Evidence")
    for required in (
        "`postgres.table` is not extension availability",
        "`--dialect postgres` selects a compiler backend, not a server instance",
        "PostgreSQL lowering is not extension support",
        "SQL spelling similarity is not semantic capability",
        "Pietto logical type is not automatically a PostgreSQL native type",
        "package requirement is not an installation request",
        "catalog entry is not a database object",
        "No connector name, SQL function name, operator spelling, or backend identity may infer extension availability",
    ):
        assert required in evidence, required


def test_route_b_identity_and_version_postures_are_locked() -> None:
    routes = _normalized_section(SPEC_PATH, "Extension-model Route Comparison")
    identity = _normalized_section(SPEC_PATH, "Extension Identity Readiness")
    versions = _normalized_section(SPEC_PATH, "Extension And Catalog Version Readiness")

    for required in (
        "Route A — named capability flags",
        "rejected as insufficient",
        "Route B — static typed profile/catalog",
        "selected",
        "Route C — SQL-template macro catalog",
        "Route D — database-introspected model",
        "Route E — executable extension plugin",
        "strongly typed, deterministic",
        "non-executable",
    ):
        assert required in routes, required
    for required in (
        "(postgresql_base_profile_identity, canonical_extension_name)",
        "lowercase ASCII",
        "logically case-sensitive",
        "not a semantic-package identity",
        "not extension identity",
    ):
        assert required in f"{identity} {versions}", required
    for required in (
        "required exact opaque normalized string",
        "extension-profile schema",
        "extension-profile release",
        "signature-catalog schema",
        "signature-catalog release",
        "optional declared exact/minimum fact",
        "optional externally supplied algorithm/value",
        "no SemVer assumption",
    ):
        assert required in versions, required


def test_immutable_base_additive_overlay_and_taxonomy_are_locked() -> None:
    overlay = _normalized_section(SPEC_PATH, "PostgreSQL Base And Extension Overlay")
    taxonomy = _normalized_section(SPEC_PATH, "Signature-Catalog Entry Taxonomy")

    for required in (
        "base profile is immutable",
        "add only explicitly typed capabilities",
        "may not replace a base capability",
        "Equivalent duplicate declarations are rejected",
        "Conflicting signatures, type identities, native mappings, emitted spellings, or lowering ownership fail closed",
        "provide no semantic precedence or winner",
    ):
        assert required in overlay, required
    for family in CATALOG_ENTRY_FAMILIES:
        assert family in taxonomy, family
    for excluded in (
        "window function",
        "table/set/relation-producing function",
        "special syntax/new operator token",
        "DDL/index/operator class/planner hint/configuration",
        "SQL template/macro",
        "executable hook/lifecycle action",
    ):
        assert excluded in taxonomy, excluded
    assert (
        "not a production enum, schema, catalog entry, or accepted extension signature"
        in taxonomy
    )


def test_extension_type_scalar_aggregate_operator_and_cast_facts_are_locked() -> None:
    type_section = _normalized_section(
        SPEC_PATH, "Extension Type And Native-mapping Readiness"
    )
    scalar = _normalized_section(SPEC_PATH, "Scalar Function Signature Readiness")
    aggregate = _normalized_section(SPEC_PATH, "Aggregate Signature Readiness")
    operator = _normalized_section(SPEC_PATH, "Operator Signature Readiness")
    cast_section = _normalized_section(SPEC_PATH, "Cast Readiness")

    for required in (
        "extension-scoped opaque logical type identity",
        "explicit native PostgreSQL spelling",
        "not a new Pietto builtin",
        "not automatically comparable, orderable, groupable, arithmetic, aggregate-capable, castable, IR-representable, lowerable, or public metadata",
        "grants no adjacent capability",
    ):
        assert required in type_section, required
    for section in (scalar, aggregate):
        for required in (
            "canonical semantic identity",
            "exact extension owner",
            "ordered exact logical argument types",
            "result nullability",
            "exact PostgreSQL emitted identifier",
            "exact profile/catalog prerequisite",
            "unsupported-context reason",
        ):
            assert required in section, required
    for required in (
        "unary/binary role",
        "already-parsed Pietto operator identity",
        "exact left and optional right logical types",
        "exact PostgreSQL operator spelling",
        "cannot define a new token, precedence, associativity, parser behavior",
    ):
        assert required in operator, required
    for required in (
        "exact source/target logical types",
        "explicit-only posture",
        "semantic safety/lossiness classification",
        "Implicit casts",
        "implicit overload participation",
        "No cast is implemented",
    ):
        assert required in cast_section, required


def test_exact_matching_requirements_dependencies_and_examples_are_locked() -> None:
    overload = _normalized_section(SPEC_PATH, "Overload And Conflict Posture")
    requirements = _normalized_section(
        SPEC_PATH, "Extension Requirement And Availability"
    )
    dependencies = _normalized_section(SPEC_PATH, "Extension Dependency Readiness")
    examples = _normalized_section(SPEC_PATH, "Example Extension-family Matrix")

    for required in (
        "exact typed signatures only",
        "variadics, default arguments, polymorphism, generics",
        "implicit coercion",
        "No ambiguity or conflict receives a winner",
        "adds or reserves no diagnostic code",
    ):
        assert required in overload, required
    for required in (
        "semantic package requires an exact extension-profile identity/version",
        "project/compiler input explicitly declares an exact profile and catalog available",
        "signature catalog describes exact typed capabilities",
        "backend has separately approved lowering",
        "actual PostgreSQL server installation state is unknown",
        "never inferred from `postgres.table`",
    ):
        assert required in requirements, required
    for required in (
        "exact dependent extension identity",
        "exact dependent extension release",
        "Only direct exact requirements",
        "deterministic transitive traversal",
        "Missing exact dependencies and cycles fail closed",
        "Version ranges",
        "solving, installation",
    ):
        assert required in dependencies, required
    for extension in EXAMPLE_EXTENSIONS:
        assert extension in examples, extension
    assert examples.count("`NOT_EVIDENCED`") == len(EXAMPLE_EXTENSIONS)
    assert "claims neither their actual contents nor Pietto support" in examples


def test_ordering_ownership_provenance_and_metadata_boundaries_are_locked() -> None:
    ordering = _normalized_section(SPEC_PATH, "Deterministic Ordering")
    ownership = _normalized_section(
        SPEC_PATH, "Package Profile And Catalog Integration"
    )
    provenance = _normalized_section(SPEC_PATH, "Provenance Digest And Trust Boundary")
    metadata = _normalized_section(SPEC_PATH, "Public And Private Metadata Boundary")

    for required in (
        "source/declaration order for diagnostics and display",
        "Canonical exact identity, entry-family, and signature keys govern equality and traversal",
        "Textual order has no semantic precedence",
    ):
        assert required in ordering, required
    for required in (
        "Slice 8 owns the extension readiness contract only",
        "Phase 55 owns the generic semantic-package asset schema",
        "initial six asset kinds remain unchanged",
        "Phase 56 owns capability/dialect/extension profile schemas",
        "Phase 57 owns PostgreSQL extension signature-catalog readiness",
        "Phase 58 owns explain, portability, compatibility, and public reporting",
        "Phase 59 owns package graph, attribution, provenance, and lineage integration",
    ):
        assert required in ownership, required
    for required in (
        "source repository locator",
        "source revision",
        "curator/generation-description text",
        "optional externally supplied digest algorithm/value",
        "no network access",
        "server introspection",
        "digest computation/verification",
        "signing, attestation",
        "trust policy",
    ):
        assert required in provenance, required
    for required in (
        "remain private future facts",
        "adds no Project JSON v2",
        "Semantic Metadata Artifact v1",
        "public metadata",
        "public API field",
        "Phase 58",
    ):
        assert required in metadata, required


def test_phase57_handoff_deferrals_and_release_boundary_are_locked() -> None:
    handoff = _normalized_section(SPEC_PATH, "Bounded Phase 57 Handoff")
    deferrals = _normalized_section(SPEC_PATH, "Explicit Deferrals And Non-goals")
    release = _normalized_section(SPEC_PATH, "Package Version And Release Boundary")
    stop = _normalized_section(SPEC_PATH, "Separate Authorization And Stop Conditions")

    for required in (
        "Phase 57 — PostgreSQL Extension Signature-Catalog Readiness remains `READINESS_CONTRACT_ONLY`, readiness-only, unstarted, separately authorized",
        "exact base/extension vocabulary",
        "Route B",
        "immutable-base/additive-overlay contract",
        "exact matching/conflict policy",
        "no-introspection/install/runtime matrices",
        "excludes production profile/catalog carriers, concrete signatures",
        "does not finalize Phase 57 implementation slices",
    ):
        assert required in handoff, required
    for required in (
        "connections; server/database/schema introspection",
        "`CREATE EXTENSION`; install/upgrade/enable/disable",
        "runtime plugins/hooks",
        "does not begin Slice 9 or Phases 52 through 57",
    ):
        assert required in deferrals, required
    assert "Package version remains `0.1.0`" in release
    assert (
        "No package version bump, tag, release, publish, upload, signing, or attestation"
        in release
    )
    for required in (
        "Slice 8 is current but incomplete in Gate 2",
        "Slices 9 through 11 remain pending",
        "Phases 52 through 57 remain unstarted",
        "Phase 57 remains readiness-only",
    ):
        assert required in stop, required


def test_all_phase50_slice8_allowlists_are_exact() -> None:
    assert len(PHASE50_TEST_PATHS) == 8
    for test_path in PHASE50_TEST_PATHS:
        assert (
            _string_set_assignment(
                _read(test_path), "ALLOWED_PHASE50_SLICE8_GATE2_PATHS"
            )
            == ALLOWED_PHASE50_SLICE8_GATE2_PATHS
        ), test_path

    allowlist = _normalized_section(PLAN_PATH, "Slice 8 Gate 2 Allowlist")
    assert "limited to exactly" in allowlist
    assert "No eleventh repository path is approved" in allowlist
    for relative_path in ALLOWED_PHASE50_SLICE8_GATE2_PATHS:
        assert relative_path in allowlist, relative_path


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
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
    )
