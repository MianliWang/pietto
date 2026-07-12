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
    REPO_ROOT / "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md"
)
TEST_PATH = (
    REPO_ROOT / "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

CLI_PATH = REPO_ROOT / "src/pietto/cli.py"
SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
POSTGRES_PATH = REPO_ROOT / "src/pietto/sql/postgres.py"
MYSQL_PATH = REPO_ROOT / "src/pietto/sql/mysql.py"
CONNECTOR_PATH = REPO_ROOT / "src/pietto/semantic/source_connectors.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"

SLICE8_SHA = "9e2c0f0ddcc2047e35985e6b97daa8bf29979914"
SLICE8_SUBJECT = "Add Phase 50 PostgreSQL extension capability readiness"
SLICE8_CI_RUN_ID = "29157374991"
SLICE9_SHA = "f886589ac2f64eeb3770c914e7c049e2da105daa"
SLICE9_SUBJECT = "Add Phase 50 multi-dialect capability readiness"
SLICE9_CI_RUN_ID = "29170827348"
SLICE10_SHA = "9bc6ed82f3741e3c242981bb88edfb50c73fc586"
SLICE10_SUBJECT = "Add Phase 50 explain public metadata boundary"
SLICE10_CI_RUN_ID = "29179160024"
SLICE9_TITLE = "# Phase 50 Slice 9 Multi-dialect Capability Ecosystem Readiness v1"

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Dialect And Backend Evidence",
    "Conceptual Vocabulary",
    "Multi-dialect Route Comparison",
    "Recommended Ecosystem Boundary",
    "Dialect Identity And Version Readiness",
    "Backend Dialect And Connector Separation",
    "Base-profile And Overlay Composition",
    "Capability Taxonomy",
    "Type And Native-mapping Portability",
    "Scalar Function Portability",
    "Aggregate Portability",
    "Operator And Cast Portability",
    "Window And Query-shape Portability",
    "Syntax And Clause Capabilities",
    "Source Connector Capabilities",
    "SQL Lowering And Spelling Ownership",
    "Portability Classification",
    "Conflict And Fail-closed Posture",
    "Deterministic Ordering",
    "Package Profile And Catalog Integration",
    "Provenance Digest And Trust Boundary",
    "Public And Private Metadata Boundary",
    "Diagnostic And Fail-closed Matrix",
    "Example Dialect-family Matrix",
    "Cross-phase Dependencies",
    "Bounded Phase 60 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

CAPABILITY_TAXONOMY = (
    "logical types",
    "native type mappings",
    "scalar functions",
    "aggregates",
    "operators",
    "casts",
    "window features",
    "syntax and clauses",
    "relation/query shapes",
    "source connectors",
    "identifier and quoting rules",
    "parameter/literal spelling",
    "nullability and coercion",
    "SQL lowering",
    "public portability reporting",
)

PORTABILITY_CLASSIFICATIONS = (
    "SUPPORTED_IDENTICALLY",
    "SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING",
    "SUPPORTED_WITH_SEMANTIC_DIFFERENCES",
    "UNSUPPORTED",
    "UNKNOWN_OR_NOT_DECLARED",
    "BLOCKED_BY_MISSING_CAPABILITY",
)

DIALECT_FAMILIES = (
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "DuckDB",
    "BigQuery",
    "Snowflake",
    "Trino",
)

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

PHASE50_SLICE9_TEST_PATHS = tuple(
    REPO_ROOT / relative_path
    for relative_path in sorted(
        path for path in ALLOWED_PHASE50_SLICE9_GATE2_PATHS if path.startswith("tests/")
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
    "tests/goldens",
    "examples",
)


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


def test_slice9_artifacts_baseline_and_mutable_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert TEST_PATH.is_file()

    status = _normalized_section(PLAN_PATH, "Status")
    baseline = _normalized_section(PLAN_PATH, "Trusted Baseline")
    spec = _read(SPEC_PATH)

    for required in (
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        SLICE8_SHA,
        SLICE8_CI_RUN_ID,
        "CI / push",
        "completed / success",
        "exact `headSha` match",
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
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in f"{status} {baseline}", required

    for required in (SLICE10_SHA, SLICE10_SUBJECT, SLICE10_CI_RUN_ID):
        assert required in baseline, required

    for required in (
        "Slices 1 through 8 are complete",
        "Slice 9 is current but incomplete in Gate 2",
        "Slices 10 and 11 remain pending",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in spec, required

    assert "Phase 50 is complete after Slice 11 Gate 2" not in status
    assert "Slice 9 completed" in status
    assert "Slice 10 completed" in status
    assert "Slice 11 is complete" not in status


def test_spec_exact_sections_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)

    assert spec.startswith(f"{SLICE9_TITLE}\n")
    offsets: list[int] = []
    for section in REQUIRED_SPEC_SECTIONS:
        heading = f"## {section}"
        assert spec.count(heading) == 1, heading
        offsets.append(spec.index(heading))
    assert offsets == sorted(offsets)
    assert spec.count("Slice 9 implements no compiler or runtime behavior.") == 1

    deferrals = _normalized_section(SPEC_PATH, "Explicit Deferrals And Non-goals")
    for required in (
        "new dialect/backend",
        "grammar",
        "parser",
        "AST",
        "semantic capability carrier",
        "profile/overlay/catalog schema",
        "profile loader",
        "checker",
        "IR",
        "SQL lowering",
        "CLI",
        "JSON",
        "public metadata",
        "database/server/schema introspection",
        "template/macro translation",
        "plugin",
        "network",
        "Phase 56/60 implementation",
    ):
        assert required in deferrals, required


def test_current_dialect_backend_and_connector_boundaries_are_locked() -> None:
    cli = _read(CLI_PATH)
    sql_api = _read(SQL_API_PATH)
    postgres = _read(POSTGRES_PATH)
    mysql = _read(MYSQL_PATH)
    connector = _read(CONNECTOR_PATH)
    ir_model = _read(IR_MODEL_PATH)
    current = _normalized_section(SPEC_PATH, "Current Dialect And Backend Evidence")
    separation = _normalized_section(
        SPEC_PATH, "Backend Dialect And Connector Separation"
    )

    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli
    assert "emit_postgres_sql" in sql_api
    assert "def emit_postgres_sql" in postgres
    assert "def emit_mysql_sql" in mysql
    assert "unsupported_dialect" in cli
    assert "postgres.table" in connector
    assert "mysql.table" in connector
    assert "class ConnectorIR" in ir_model

    for required in (
        "PostgreSQL is the bounded public SQL backend",
        "MySQL is a bounded private backend",
        "The CLI rejects an unknown dialect before parsing",
        "No production Capability, Profile, Overlay, Extension, NativeType, or",
        "DialectProfile carrier exists",
        "Header text, connector names, and filename suffixes do not infer",
        "The static postgres.table connector accepts one Text argument",
        "mysql.table connector additionally requires a non-empty Text literal",
    ):
        assert required in f"{current} {separation}", required

    production_text = " ".join(
        _read(path)
        for path in (
            CLI_PATH,
            SQL_API_PATH,
            POSTGRES_PATH,
            MYSQL_PATH,
            CONNECTOR_PATH,
            IR_MODEL_PATH,
        )
    )
    for forbidden in (
        "class Capability",
        "class Profile",
        "class Overlay",
        "class Extension",
        "class NativeType",
        "class DialectProfile",
    ):
        assert forbidden not in production_text, forbidden

    for relative_path in (
        "src/pietto/sql/sqlite.py",
        "src/pietto/sql/duckdb.py",
        "src/pietto/sql/bigquery.py",
        "src/pietto/sql/snowflake.py",
        "src/pietto/sql/trino.py",
        "src/pietto/dialect_profile.py",
        "src/pietto/capability_profile.py",
    ):
        assert not (REPO_ROOT / relative_path).exists(), relative_path


def test_route_b_identity_and_version_boundaries_are_locked() -> None:
    route = _normalized_section(SPEC_PATH, "Multi-dialect Route Comparison")
    boundary = _normalized_section(SPEC_PATH, "Recommended Ecosystem Boundary")
    identity = _normalized_section(SPEC_PATH, "Dialect Identity And Version Readiness")

    for required in (
        "Route A",
        "Route B",
        "Route C",
        "Route D",
        "Route E",
        "Route F",
        "selected",
        "static, strongly typed, declarative, deterministic, reviewable, and non-executable",
        "non-executable dialect profiles",
        "No silent degradation",
        "least-common-denominator fallback",
        "best-effort rewriting",
        "unknown-as-supported behavior",
        "canonical exact lowercase identifier",
        "exact equality only",
        "no version range",
        "solver",
        "precedence selection",
        "automatic version choice",
        "optional static exact requirement only",
        "descriptive algorithm/value",
        "remains 0.1.0",
    ):
        assert required in f"{route} {boundary} {identity}", required


def test_capability_taxonomy_and_additive_overlay_posture_are_locked() -> None:
    taxonomy = _normalized_section(SPEC_PATH, "Capability Taxonomy")
    composition = _normalized_section(SPEC_PATH, "Base-profile And Overlay Composition")
    lowering = _normalized_section(SPEC_PATH, "SQL Lowering And Spelling Ownership")

    for capability in CAPABILITY_TAXONOMY:
        assert capability in taxonomy, capability

    for required in (
        "base profile is immutable",
        "add only explicitly declared capability facts",
        "may not replace",
        "exact duplicate declaration",
        "fail closed",
        "no winner",
        "missing explicit lowering",
        "unsupported syntax/query context",
        "backend/profile mismatch",
        "no composition carrier",
        "explicit approved backend-lowering owner",
        "SQL spelling similarity never creates semantic support",
    ):
        assert required in f"{composition} {lowering}", required


def test_portability_conflict_ordering_and_examples_are_locked() -> None:
    portability = _normalized_section(SPEC_PATH, "Portability Classification")
    conflict = _normalized_section(SPEC_PATH, "Conflict And Fail-closed Posture")
    ordering = _normalized_section(SPEC_PATH, "Deterministic Ordering")
    examples = _normalized_section(SPEC_PATH, "Example Dialect-family Matrix")

    for classification in PORTABILITY_CLASSIFICATIONS:
        assert classification in portability, classification

    for required in (
        "No classification authorizes a public report",
        "Invalid identity, duplicate declaration, replacement, conflict, ambiguity",
        "fails closed",
        "semantic winner",
        "Canonical exact dialect/profile/overlay/capability identity",
        "never supplies semantic precedence",
        "SQLite",
        "rejection evidence only",
        "DuckDB",
        "BigQuery",
        "Snowflake",
        "Trino",
        "NOT_EVIDENCED",
        "no support claim",
    ):
        assert required in f"{portability} {conflict} {ordering} {examples}", required

    for family in DIALECT_FAMILIES:
        assert family in examples, family


def test_ownership_privacy_phase60_and_release_boundaries_are_locked() -> None:
    ownership = _normalized_section(
        SPEC_PATH, "Package Profile And Catalog Integration"
    )
    provenance = _normalized_section(SPEC_PATH, "Provenance Digest And Trust Boundary")
    privacy = _normalized_section(SPEC_PATH, "Public And Private Metadata Boundary")
    diagnostics = _normalized_section(SPEC_PATH, "Diagnostic And Fail-closed Matrix")
    handoff = _normalized_section(SPEC_PATH, "Bounded Phase 60 Handoff")
    release = _normalized_section(SPEC_PATH, "Package Version And Release Boundary")
    stop = _normalized_section(SPEC_PATH, "Separate Authorization And Stop Conditions")

    for required in (
        "Phase 55 owns semantic-package asset schema",
        "Phase 56 owns capability/dialect/extension profile schema and declared checking",
        "Phase 57 owns PostgreSQL extension signature-catalog readiness",
        "Slice 10 and Phase 58 own explain, portability, compatibility, and public reporting",
        "Phase 59 owns package graph, attribution, provenance, and lineage integration",
        "Phase 60 is a multi-dialect capability ecosystem completion checkpoint",
        "Package requires, package provides, package contains profile",
        "no fetch",
        "digest computation/verification",
        "signing",
        "attestation",
        "remain private readiness information",
        "no Project JSON v2 field",
        "public portability report",
        "fail closed; no code selected",
        "no diagnostic code",
        "readiness-only, unstarted, and separately authorized",
        "does not start Phase 60",
        "Package version remains `0.1.0`",
        "does not stage, commit, push",
        "Slices 10 and 11 remain pending",
    ):
        assert required in (
            f"{ownership} {provenance} {privacy} {diagnostics} {handoff} {release} {stop}"
        ), required


def test_all_phase50_slice9_allowlists_are_exact() -> None:
    assert len(ALLOWED_PHASE50_SLICE9_GATE2_PATHS) == 11
    assert len(PHASE50_SLICE9_TEST_PATHS) == 9

    for test_path in PHASE50_SLICE9_TEST_PATHS:
        assert test_path.is_file(), test_path
        assert (
            _string_set_assignment(
                _read(test_path), "ALLOWED_PHASE50_SLICE9_GATE2_PATHS"
            )
            == ALLOWED_PHASE50_SLICE9_GATE2_PATHS
        ), test_path

    plan_allowlist = _normalized_section(PLAN_PATH, "Slice 9 Gate 2 Allowlist")
    assert "limited to exactly" in plan_allowlist
    assert "No twelfth repository path is approved" in plan_allowlist
    for relative_path in ALLOWED_PHASE50_SLICE9_GATE2_PATHS:
        assert relative_path in plan_allowlist, relative_path

    slice8_source = _read(
        REPO_ROOT / "tests/test_phase50_postgresql_extension_capability_readiness.py"
    )
    historical_slice8 = _string_set_assignment(
        slice8_source, "ALLOWED_PHASE50_SLICE8_GATE2_PATHS"
    )
    assert len(historical_slice8) == 10
    assert (
        "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md"
        not in historical_slice8
    )
    assert (
        "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py"
        not in historical_slice8
    )


def test_protected_paths_version_tag_staging_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    assert not (REPO_ROOT / "tests/goldens").exists()

    for relative_path in PROTECTED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path

    assert _dirty_paths() in (
        set(),
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
    )
