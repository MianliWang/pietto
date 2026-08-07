import ast
import hashlib
import subprocess
import tomllib
from pathlib import Path
from typing import cast
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
SCOPE_PATH = (
    REPO_ROOT
    / "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md"
)
HISTORICAL_ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
SELF_PATH = (
    REPO_ROOT
    / "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py"
)

PLAN_TITLE = "# Phase 51 — Aggregate / Grouped Project Output-Schema Foundation"
ROADMAP_TITLE = "# Pietto Active Roadmap Phase 51–60 v1"
SCOPE_TITLE = (
    "# Phase 51 Slice 1 Aggregate / Grouped Output-Schema Foundation Scope Lock v1"
)
NO_BEHAVIOR_SENTENCE = "Slice 1 implements no compiler or runtime behavior."

PLAN_HEADINGS = (
    "Status",
    "Trusted Phase 50 Baseline",
    "Phase Identity",
    "Authority And Roadmap Governance",
    "Current Aggregate Compiler Surface",
    "Current Grouped-query Surface",
    "Current Project Row-schema Foundation",
    "Current Origin Provenance Dependency And Lineage Foundation",
    "Current Public And Privacy Boundaries",
    "Phase 50 Deferred Inventory",
    "Selected Phase 51 Scope",
    "Relation-form Boundary",
    "Output Identity And Alias Contract",
    "Private Result-role Model",
    "Type And Nullability Boundary",
    "Schema Availability And Duplicate Posture",
    "Dependency And Lineage Contract",
    "Downstream Propagation Contract",
    "Fail-closed And Diagnostic Contract",
    "Aggregate-adjacent Readiness Closure",
    "Explicit Non-goals",
    "Complete Slice Route",
    "Slice-by-slice Ownership Matrix",
    "Cross-slice Gate Discipline",
    "Active Phase 51–60 Handoff",
    "Post-Phase-60 Owner Register",
    "Package Version And Release Boundary",
    "Slice 1 Gate 2 Allowlist",
    "Slice 1 Focused Validation",
    "Stop Conditions",
)

ROADMAP_HEADINGS = (
    "Status And Conditional Authority",
    "Historical Evidence Boundary",
    "Governance And Three Status Axes",
    "No Automatic Phase Start Rule",
    "Base Active Route Identity",
    "Phase 51–60 Normative End-state Table",
    "Phase-by-phase Prerequisites And Non-goals",
    "Readiness-to-minimum-foundation Policy",
    "Local-first Package Ecosystem Policy",
    "Deferred-owner Matrix",
    "Post-Phase-60 Stable Owner Slots",
    "Permanent Out-of-scope Charter Boundary",
    "Append-only Reconciliation Protocol",
    "Version Package And Release Boundary",
    "Stop Conditions",
    "Reconciliation Ledger",
)

SCOPE_HEADINGS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Trusted Phase 50 Baseline",
    "Adopted-policy Boundary",
    "Historical-roadmap Preservation",
    "Active-roadmap Governance",
    "Status And Classification Axes",
    "Current Compiler-pipeline Inventory",
    "Current Aggregate Surface",
    "Current Grouped-query Surface",
    "Current Project Row-schema Foundation",
    "Current Origin Provenance Dependency And Lineage Foundation",
    "Public Artifact And Privacy Boundary",
    "Phase 50 Deferred Inventory And Owner Closure",
    "Selected Phase 51 Scope",
    "Relation-form Boundary",
    "Output Identity And Alias Contract",
    "Private Result-role Model",
    "Type And Nullability Matrix",
    "Schema Availability And Duplicate Posture",
    "Dependency Clause And Lineage Contract",
    "Downstream Propagation Contract",
    "Fail-closed And Diagnostic Contract",
    "Aggregate-adjacent Readiness Closure",
    "Complete Twelve-slice Route",
    "Active Phase 52–60 Handoff",
    "Post-Phase-60 Owner Register",
    "Package Version And Release Boundary",
    "Slice 1 Gate 2 Allowlist",
    "Focused Validation",
    "Stop Conditions",
)

ALLOWED_PHASE51_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
}

ALLOWED_PHASE52_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
    "docs/plan/phase-45-project-wide-semantic-model-mvp.md",
    "docs/plan/phase-46-project-semantic-continuation.md",
    "docs/plan/phase-47-direct-row-schema-mvp.md",
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
    "docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md",
    "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md",
    "docs/spec/phase47-direct-row-schema-scope-lock-v1.md",
    "docs/spec/phase48-completion-audit-status-lock-v1.md",
    "docs/spec/phase49-completion-audit-status-lock-v1.md",
    "docs/spec/phase50-completion-audit-and-status-lock-v1.md",
    "docs/spec/cli-json-v1.md",
    "docs/spec/semantic-metadata-artifact-v1.md",
    "docs/spec/project-json-v2-result-envelope-v1.md",
    "docs/spec/project-cli-json-v2.md",
    "src",
    "grammar",
    "scripts",
    ".github",
    "Makefile",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "examples",
)

PHASE51_SLICES = (
    "Scope Architecture And Active-roadmap Lock",
    "Private Result-role And Output-identity Foundation",
    "Group-key Project Row-schema Foundation",
    "Aggregate-only Project Row-schema Foundation",
    "Grouped Aggregate Project Row-schema Foundation",
    "Selected-let And Accepted-expression Aggregate Integration",
    "Type Nullability Availability-state And Duplicate Handling",
    "Clause-dependency And Fail-closed Hardening",
    "Origin Provenance Dependency And Lineage Integration",
    "Downstream Propagation And Qualification",
    "Cross-phase Readiness Privacy And Compatibility Closure",
    "Completion Audit And Status Lock",
)

PHASE_ROUTE = (
    (
        51,
        "Aggregate / Grouped Project Output-Schema Foundation",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (52, "Core Type-System Capability Foundation", "MINIMUM_PRODUCTION_FOUNDATION"),
    (
        53,
        "Window Function Syntax And Capability Contract",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (54, "Import / Module / Export Readiness", "MINIMUM_PRODUCTION_FOUNDATION"),
    (55, "Semantic Package Asset Schema", "MINIMUM_PRODUCTION_FOUNDATION"),
    (
        56,
        "Capability Profile Static Schema And Declared Checking",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (
        57,
        "PostgreSQL Extension Signature-Catalog Readiness",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (
        58,
        "Project Explain / Portability / Public Metadata Readiness",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (
        59,
        "Package Graph And Lineage / Provenance Integration",
        "MINIMUM_PRODUCTION_FOUNDATION",
    ),
    (
        60,
        "Multi-dialect Capability Ecosystem Completion Checkpoint",
        "READINESS_CONTRACT_ONLY",
    ),
)

DEFERRED_OWNER_ASSIGNMENTS = (
    ("A01", "PHASE_51"),
    ("A02", "PHASE_51"),
    ("A03", "PHASE_51"),
    ("A04", "PHASE_51"),
    ("A05", "PHASE_51"),
    ("A06", "PHASE_51"),
    ("A07", "PHASE_51"),
    ("A08", "PHASE_51"),
    ("A09", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A10", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A11", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A12", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A13", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A14", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A15", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A16", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A17", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A18", "POST60_ADVANCED_AGGREGATION_GROUPING"),
    ("A19", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("A20", "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT"),
    ("B01", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B02", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B03", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B04", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B05", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B06", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B07", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B08", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B09", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B10", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B11", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B12", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B13", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("B14", "POST60_ADVANCED_TYPE_NATIVE_MAPPING"),
    ("C01", "PHASE_53"),
    ("C02", "PHASE_53"),
    ("C03", "PHASE_53"),
    ("C04", "PHASE_53"),
    ("C05", "POST60_ADVANCED_WINDOWS"),
    ("C06", "POST60_ADVANCED_WINDOWS"),
    ("C07", "POST60_ADVANCED_WINDOWS"),
    ("C08", "POST60_ADVANCED_WINDOWS"),
    ("C09", "POST60_ADVANCED_WINDOWS"),
    ("C10", "POST60_ADVANCED_WINDOWS"),
    ("D01", "PHASE_54"),
    ("D02", "PHASE_54"),
    ("D03", "PHASE_55"),
    ("D04", "PHASE_55"),
    ("D05", "PHASE_59"),
    ("D06", "POST60_REMOTE_PACKAGE_MANAGER"),
    ("D07", "POST60_REMOTE_PACKAGE_MANAGER"),
    ("D08", "POST60_DEPENDENCY_SOLVER_LOCKFILE"),
    ("D09", "POST60_DEPENDENCY_SOLVER_LOCKFILE"),
    ("D10", "OUT_OF_SCOPE_CHARTER"),
    ("E01", "PHASE_56"),
    ("E02", "PHASE_56"),
    ("E03", "PHASE_57"),
    ("E04", "PHASE_57"),
    ("E05", "PHASE_57"),
    ("E06", "POST60_EXTENSION_LOWERING"),
    ("E07", "PHASE_58"),
    ("E08", "POST60_ADDITIONAL_DIALECT_BACKENDS"),
    ("E09", "OUT_OF_SCOPE_CHARTER"),
    ("F01", "PHASE_58"),
    ("F02", "PHASE_58"),
    ("F03", "PHASE_58"),
    ("F04", "PHASE_58"),
    ("F05", "PHASE_58"),
    ("F06", "POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION"),
    ("F07", "POST60_PROJECT_IR"),
    ("F08", "POST60_MULTI_RELATION_SQL"),
    ("G01", "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT"),
    ("G02", "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT"),
    ("G03", "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT"),
    ("G04", "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT"),
    ("G05", "OUT_OF_SCOPE_CHARTER"),
    ("G06", "OUT_OF_SCOPE_CHARTER"),
    ("G07", "OUT_OF_SCOPE_CHARTER"),
    ("G08", "OUT_OF_SCOPE_CHARTER"),
    ("G09", "OUT_OF_SCOPE_CHARTER"),
)

POST60_OWNER_SLOTS = (
    "POST60_ADVANCED_AGGREGATION_GROUPING",
    "POST60_ADVANCED_TYPE_NATIVE_MAPPING",
    "POST60_ADVANCED_WINDOWS",
    "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT",
    "POST60_PROJECT_IR",
    "POST60_MULTI_RELATION_SQL",
    "POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION",
    "POST60_ADVANCED_MODULE_PACKAGE_ASSETS",
    "POST60_REMOTE_PACKAGE_MANAGER",
    "POST60_DEPENDENCY_SOLVER_LOCKFILE",
    "POST60_ADDITIONAL_DIALECT_BACKENDS",
    "POST60_EXTENSION_LOWERING",
    "OUT_OF_SCOPE_CHARTER",
)

HISTORICAL_ROADMAP_SHA256 = (
    "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _headings(path: Path) -> tuple[str, ...]:
    return tuple(
        line.removeprefix("## ")
        for line in _read(path).splitlines()
        if line.startswith("## ")
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
    paths: set[str] = set()
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    for line in output.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _row_for_identifier(document: str, identifier: str) -> str:
    marker = f"| {identifier} |"
    rows = [line for line in document.splitlines() if line.startswith(marker)]
    assert len(rows) == 1, identifier
    return rows[0]


def test_artifacts_titles_heading_orders_and_no_behavior_sentence_are_locked() -> None:
    artifacts = (
        (PLAN_PATH, PLAN_TITLE, PLAN_HEADINGS),
        (ROADMAP_PATH, ROADMAP_TITLE, ROADMAP_HEADINGS),
        (SCOPE_PATH, SCOPE_TITLE, SCOPE_HEADINGS),
    )
    for path, title, headings in artifacts:
        assert path.is_file(), path
        content = _read(path)
        assert content.startswith(f"{title}\n")
        assert _headings(path) == headings
        assert NO_BEHAVIOR_SENTENCE in content
    assert SELF_PATH.is_file()


def test_trusted_phase50_baseline_and_documented_ci_are_locked() -> None:
    docs = " ".join((_normalized(PLAN_PATH), _normalized(SCOPE_PATH)))
    for required in (
        "5fc2f9d584d49f9d519b298f8205bd878aeb53cb",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "0a63f74fe65871567e9f7e4ea9dddc12d84c8b26",
        "Complete Phase 50 semantic readiness consolidation audit",
        "29189023482",
        "CI / push / main",
        "completed / success",
        "5417 passed in 60.83s",
        "5417 passed in 33.31s",
        "8 tracked files",
        "32 SQL",
        "5 JSON",
        "pietto 0.1.0",
    ):
        assert required in docs, required


def test_roadmap_governance_status_axes_and_conditional_authority_are_locked() -> None:
    roadmap = _normalized(ROADMAP_PATH)
    for required in (
        "ACTIVE",
        "COMPLETED",
        "UNSTARTED",
        "READINESS_CONTRACT_ONLY",
        "MINIMUM_PRODUCTION_FOUNDATION",
        "DEFERRED_WITH_OWNER",
        "OUT_OF_SCOPE",
        "NOT_EVIDENCED",
        "natural CI",
        "headSha",
        "append-only",
        "Reconciliation",
        "v2",
    ):
        assert required in roadmap, required
    for phase in range(51, 61):
        assert f"Phase {phase}" in roadmap
    assert "Phase 51: UNSTARTED" in roadmap
    assert "Phase 52–60: UNSTARTED" in roadmap
    assert "Phase 51 lifecycle becomes ACTIVE" in roadmap
    assert "Phase 52–60 remain UNSTARTED" in roadmap
    assert "No reconciliation entries exist." in _read(ROADMAP_PATH)


def test_phase51_twelve_slice_route_is_exact_and_separately_gated() -> None:
    plan = _read(PLAN_PATH)
    scope = _read(SCOPE_PATH)
    for index, title in enumerate(PHASE51_SLICES, start=1):
        assert f"{index}. {title}" in plan
        assert f"{index}. {title}" in scope
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SCOPE_PATH)}"
    for required in (
        "Gate 1",
        "Gate 2",
        "Gate 3",
        "separately authorized",
        "natural CI",
        "headSha",
    ):
        assert required in docs, required


def test_phase51_60_normative_route_and_delivery_classes_are_locked() -> None:
    roadmap = _normalized(ROADMAP_PATH)
    for phase, title, delivery in PHASE_ROUTE:
        assert f"Phase {phase}" in roadmap
        assert title in roadmap
        assert delivery in roadmap
    for required in (
        "row_number",
        "rank",
        "dense_rank",
        "Local file-as-module",
        "local semantic-package manifest",
        "Private profile carrier",
        "exact signature matching",
        "independently versioned",
        "local exact dependency graph",
        "owner",
    ):
        assert required in roadmap, required


def test_current_aggregate_grouped_project_and_public_inventories_are_locked() -> None:
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SCOPE_PATH)}"
    for required in (
        "CallExpr",
        "AggregateCallIR",
        "RelationIR.group_keys",
        "result_predicate",
        "COUNT(*)",
        "COUNT(DISTINCT expr)",
        "SUM(expr)",
        "AVG(expr)",
        "MIN(field)",
        "MAX(field)",
        "PIE-S2309",
        "PIE-S2310",
        "PIE-S2311",
        "PIE-S2312",
        "PIE-S2313",
        "PIE-S2314",
        "PIE-S2315",
        "PIE-S2317",
        "PIE-S2318",
        "PIE-S2319",
        "PIE-S2320",
        "PIE-S2321",
        "PIE-S2323",
        "PIE-S2324",
        "PIE-S2325",
        "PIE-S2326",
        "PIE-S2327",
        "PIE-B1000",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "Project JSON v2",
        "PostgreSQL",
        "MySQL",
    ):
        assert required in docs, required


def test_relation_forms_output_identity_and_private_result_model_are_locked() -> None:
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SCOPE_PATH)}"
    for required in (
        "no-GROUP aggregate-only",
        "grouped `QueryDef`",
        "grouped `TableDef`",
        "unselected group keys",
        "explicit alias",
        "select source order",
        "no hidden fields",
        "ProjectRowResultRole",
        "ORDINARY_ROW_VALUE",
        "GROUP_KEY",
        "AGGREGATE_RESULT",
        "ProjectRowField",
        "ProjectAggregateResultFact",
        "relation_aggregate_result_facts",
        "function",
        "output_name",
        "grouped",
        "argument_count",
        "location",
        "field_def=None",
    ):
        assert required in docs, required


def test_type_nullability_four_states_and_five_new_reasons_are_locked() -> None:
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SCOPE_PATH)}"
    for required in (
        "`count()` | `Int` | `NON_NULL`",
        "`count(field)` | `Int` | `NON_NULL`",
        "`count_distinct` | `Int` | `NON_NULL`",
        "`sum(Int)` | `Int` | `NULLABLE`",
        "`sum(Float)` | `Float` | `NULLABLE`",
        "`sum(Decimal)` | `Decimal` | `NULLABLE`",
        "`avg(Int)` | `Float` | `NULLABLE`",
        "`avg(Float)` | `Float` | `NULLABLE`",
        "`avg(Decimal)` | `Decimal` | `NULLABLE`",
        "CONCRETE",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
        "DUPLICATE_GROUP_KEY",
        "UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT",
        "INVALID_AGGREGATE_OR_GROUPED_OUTPUT",
        "AGGREGATE_OR_GROUPED_DEFERRED",
        "CONFLICTING_AGGREGATE_OR_GROUPED_FACTS",
        "no fifth state",
        "no partial",
    ):
        assert required in docs, required


def test_dependency_clause_lineage_downstream_and_fail_closed_contracts_are_locked() -> (
    None
):
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SCOPE_PATH)}"
    for required in (
        "RELATION_INPUT",
        "AGGREGATE_ARGUMENT",
        "AGGREGATE_RELATION_INPUT",
        "GROUP_KEY_INPUT",
        "SATISFYING_OUTPUT",
        "GROUPED_ORDER_OUTPUT",
        "count()",
        "no fabricated field-lineage leaf",
        "AST left-to-right",
        "first-occurrence dedupe",
        "immediate lineage",
        "transitive",
        "bare selected output name",
        "immediate upstream relation qualifier",
        "Original source qualifier",
        "UPSTREAM_UNKNOWN",
        "UPSTREAM_DEFERRED",
        "UPSTREAM_BLOCKED",
        "no new diagnostic",
        "no synthetic name",
    ):
        assert required in docs, required


def test_complete_deferred_owner_matrix_and_post60_register_are_locked() -> None:
    plan = _read(PLAN_PATH)
    roadmap = _read(ROADMAP_PATH)
    scope = _read(SCOPE_PATH)
    for document in (plan, roadmap, scope):
        for identifier, owner in DEFERRED_OWNER_ASSIGNMENTS:
            row = _row_for_identifier(document, identifier)
            assert owner in row, (identifier, owner)
    for owner in POST60_OWNER_SLOTS:
        for document in (plan, roadmap, scope):
            assert owner in document, owner


def test_privacy_readiness_release_and_non_goal_boundaries_are_locked() -> None:
    docs = " ".join(
        (_normalized(PLAN_PATH), _normalized(ROADMAP_PATH), _normalized(SCOPE_PATH))
    )
    for required in (
        "private and unserialized",
        "WINDOW_RESULT",
        "JOIN",
        "grain",
        "fanout",
        "project IR",
        "project emit-sql",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "Project JSON v2",
        "package version remains `0.1.0`.",
        "no tag",
        "release",
        "publish",
        "upload",
        "signing",
        "attestation",
    ):
        assert required in docs, required


def test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set() -> None:
    assert (
        hashlib.sha256(HISTORICAL_ROADMAP_PATH.read_bytes()).hexdigest()
        == HISTORICAL_ROADMAP_SHA256
    )
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = pyproject["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"
    assert not (REPO_ROOT / "tests/goldens").exists()
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    for relative_path in PROTECTED_PATHS:
        assert (
            _git_output(["diff", "--", relative_path]) == ""
        ) or _phase54_active_gate2_is_active(), relative_path
    assert (
        _dirty_paths()
        in (
            set(),
            ALLOWED_PHASE51_SLICE1_GATE2_PATHS,
            ALLOWED_PHASE52_SLICE1_GATE2_PATHS,
        )
    ) or _phase54_active_gate2_is_active()


def test_static_test_imports_and_git_helper_are_literal_and_read_only() -> None:
    source = _read(SELF_PATH)
    tree = ast.parse(source)
    allowed_import_roots = {
        "_phase54_active_gate2_manifest",
        "ast",
        "hashlib",
        "pathlib",
        "subprocess",
        "test_phase54_local_import_module_export_foundation_scope_lock",
        "tomllib",
        "typing",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", maxsplit=1)[0] in allowed_import_roots
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            assert node.module.split(".", maxsplit=1)[0] in allowed_import_roots

    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert len(subprocess_calls) == 1
    call = subprocess_calls[0]
    assert isinstance(call.func, ast.Attribute)
    assert call.func.attr == "run"
    assert len(call.args) == 1
    command = call.args[0]
    assert isinstance(command, ast.List)
    assert len(command.elts) == 2
    first, second = command.elts
    assert isinstance(first, ast.Constant) and first.value == "git"
    assert isinstance(second, ast.Starred)
    assert isinstance(second.value, ast.Name) and second.value.id == "args"
    keywords = {keyword.arg: keyword.value for keyword in call.keywords}
    assert set(keywords) == {"cwd", "check", "text", "stdout", "stderr"}
    assert isinstance(keywords["cwd"], ast.Name)
    assert keywords["cwd"].id == "REPO_ROOT"
    for name in ("check", "text"):
        value = keywords[name]
        assert isinstance(value, ast.Constant) and value.value is True
    for name in ("stdout", "stderr"):
        value = keywords[name]
        assert isinstance(value, ast.Attribute)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "subprocess"
        assert value.attr == "PIPE"

    helper_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_git_output"
    ]
    assert helper_calls
    for helper_call in helper_calls:
        assert len(helper_call.args) == 1
        argument = helper_call.args[0]
        assert isinstance(argument, ast.List)
        values = argument.elts
        assert values
        first_value = values[0]
        assert isinstance(first_value, ast.Constant)
        subcommand = first_value.value
        if subcommand == "status":
            assert [cast(ast.Constant, value).value for value in values] == [
                "status",
                "--porcelain",
                "--untracked-files=all",
            ]
        elif subcommand == "diff":
            assert len(values) == 3
            second_value = values[1]
            assert isinstance(second_value, ast.Constant)
            assert second_value.value in {"--", "--cached"}
            third_value = values[2]
            if second_value.value == "--cached":
                assert isinstance(third_value, ast.Constant)
                assert third_value.value == "--name-status"
            else:
                assert isinstance(third_value, ast.Name)
                assert third_value.id == "relative_path"
        elif subcommand == "tag":
            assert [cast(ast.Constant, value).value for value in values] == [
                "tag",
                "--points-at",
                "HEAD",
            ]
        else:
            raise AssertionError(subcommand)
