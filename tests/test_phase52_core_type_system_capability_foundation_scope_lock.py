from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_product_repair1_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-52-core-type-system-capability-foundation.md"
SCOPE_PATH = (
    REPO_ROOT
    / "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md"
)
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
CURRENT_ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
SELF_PATH = (
    REPO_ROOT
    / "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
COMPATIBILITY_PATHS = (
    REPO_ROOT
    / "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    REPO_ROOT / "tests/test_phase51_aggregate_only_project_row_schema.py",
    REPO_ROOT / "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    REPO_ROOT / "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    REPO_ROOT
    / "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    REPO_ROOT / "tests/test_phase51_completion_audit_and_status_lock.py",
)
BOUNDARY_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)

PLAN_TITLE = "Phase 52 — Core Type-System Capability Foundation"
SCOPE_TITLE = "Phase 52 Slice 1 Core Type-System Capability Foundation Scope Lock v1"
PLAN_H2 = (
    "Status And Slice 1 Lifecycle",
    "Trusted Phase 51 Baseline And Controlling Recon",
    "Phase Identity And Scope Architecture",
    "Read-model-first Authority And Evidence Boundary",
    "Exact Nine-slice Route",
    "Slice Objectives Delivery Classes And Ownership",
    "Prerequisites And Phase 53–60 Dependency Handoff",
    "Capability Key Evidence And Disposition Vocabulary",
    "Lookup Algebra And Fail-closed Semantics",
    "Current-support And Roadmap-disposition Orthogonality",
    "Logical Type Literal Parameter And Nullability Inventory Boundary",
    "Scalar Function And Operator Signature Boundary",
    "Expression Stage And Clause Capability Boundary",
    "Aggregate Signature And Algebra Boundary",
    "Fact-family Separation And Non-overlapping Responsibility",
    "Current Conflict Ledger And Uncertainty Boundary",
    "Solver-readiness Without A Solver",
    "Public Privacy And Compatibility Boundary",
    "No-behavior And Protected Surface Boundary",
    "Deferred-owner Boundary",
    "Active-roadmap Reconciliation 2 Contract",
    "Slice 1 Exact Gate 2 Scope And Allowlist",
    "Gate Workflow And Completion Conditions",
    "Validation And Evidence Workflow",
    "Package Version And Release Boundary",
    "Stop Conditions",
)
SCOPE_H2 = (
    "Purpose And Slice Identity",
    "Trusted Baseline And Controlling Recon",
    "Exact Nine-slice Route",
    "Read-model-first Authority Contract",
    "Authority Dimensions And Non-authority Guarantees",
    "Lookup Algebra Contract",
    "Current-support And Roadmap-disposition Contract",
    "Private Reason-code Vocabulary Assignment",
    "Expression Stage Contract",
    "Fact-family Responsibility Contract",
    "Current Conflict Ledger Contract",
    "Solver-readiness Non-implementation Contract",
    "Slice 1 Tests Docs Status-only Contract",
    "No Production Carrier And No Compiler Behavior Contract",
    "IR SQL Diagnostic CLI And Runtime Non-change Contract",
    "Public Artifact Privacy And API Contract",
    "Compiler Project Package And Release Lock Contract",
    "Active-roadmap Reconciliation 2 Append-only Contract",
    "Post-CI Lifecycle And Next-slice Contract",
    "Exact Gate 2 Allowlist And Compatibility Migration",
    "Validation Evidence And Gate 3 Handoff",
    "Stop Conditions",
)
PHASE52_ROUTE = (
    "Scope Architecture, Authority Boundary, And Active-roadmap Lock",
    "Private Capability Key, Disposition, Evidence, And Fact Foundation",
    "Fail-closed Lookup And Absent/Unknown/Conflict Semantics",
    "Logical Type, Literal, Parameter, And Nullability Inventory",
    "Scalar Function And Operator Signature Facts",
    "Expression Stage And Clause Capability Facts",
    "Aggregate Signature And Algebra Facts",
    "Parity, Privacy, Cross-phase Readiness, And Drift Closure",
    "Completion Audit And Status Lock",
)
PHASE52_GATE2_PATHS = {
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
PHASE52_UNTRACKED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
}
PHASE52_SLICE1_CI_REPAIR_PATHS = {
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
}
SLICE9_SPEC_REL = "docs/spec/phase52-completion-audit-and-status-lock-v1.md"
SLICE9_TEST_REL = "tests/test_phase52_completion_audit_and_status_lock.py"
SLICE9_BASE_HEAD_SHA = "36e466535d923f708a0201ae15a5708f06f2b1f8"
SLICE9_MODIFIED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
}
SLICE9_ADDED_PATHS = {SLICE9_SPEC_REL, SLICE9_TEST_REL}
SLICE9_ALLOWLIST_PATHS = SLICE9_MODIFIED_PATHS | SLICE9_ADDED_PATHS
PHASE53_BASE_HEAD_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
PHASE53_MODIFIED_PATHS = {
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
}
PHASE53_ADDED_PATHS = {
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md",
    "docs/spec/pietto-active-roadmap-phase53-70-v1.md",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
}
PHASE53_ALLOWLIST_PATHS = PHASE53_MODIFIED_PATHS | PHASE53_ADDED_PATHS
SLICE9_STATUS_H3 = "Slice 9 Gate 2 Bounded Implementation Status"
RECONCILIATION_2_H3 = (
    "### Reconciliation 2 — Phase 52 Activation And Exact-current Capability Route Lock"
)
RECONCILIATION_3_H3 = (
    "### Reconciliation 3 — Phase 52 Conditional Completion And Phase 53 Handoff"
)
RECONCILIATION_4_H3 = (
    "### Reconciliation 4 — Phase 52 Completion, Phase 53–70 Current-authority "
    "Handoff, Release, And Rust Route"
)
PRE_RECONCILIATION_2_SHA256 = (
    "b05e57e27afb232b897e7bcec911d8f756beed204a1d0798380b7a510b9a4f80"
)
PRE_RECONCILIATION_3_SHA256 = (
    "cb2c51246f1e312858641750d1a416125f99058fb0182949e9afe35ae49e97cf"
)
COMPILER_DIGEST = "6fc8d255dc6cb8f5bd9a4edaf4af2867f975aa02f29cf63222d77040930636c8"
PROJECT_PRIVATE_DIGEST = (
    "df31b0f53c4b97ea1a791962da863036a6a72db529635a12112e148c63162a0f"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice13_paths(name: str) -> set[str]:
    if _git_output(["rev-parse", "HEAD"]) in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
    }:
        modified, added = _phase54_slice2_paths()
        if name == "MODIFIED_PATHS":
            return modified
        if name == "ADDED_PATHS":
            return added
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, (set, tuple))
            assert all(isinstance(item, str) for item in value)
            return set(value)
    raise AssertionError(f"missing Slice 13 path manifest {name}")


def _phase54_slice2_paths() -> tuple[set[str], set[str]]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, set[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in expected
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            assert all(isinstance(item, str) for item in value)
            values[node.targets[0].id] = value
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _headings_at_level(path: Path, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(path),
            flags=re.MULTILINE,
        )
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
    return result.stdout.rstrip()


def _dirty_paths() -> set[str]:
    return {
        line[3:]
        for line in _git_output(
            ["status", "--porcelain=v1", "--untracked-files=all"]
        ).splitlines()
    }


def _top_level_test_names(path: Path) -> tuple[str, ...]:
    return tuple(
        node.name
        for node in ast.parse(_read(path), filename=path.as_posix()).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _pytest_item_count(path: Path) -> int:
    return len(_top_level_test_names(path))


def _pre_reconciliation_2_prefix() -> str:
    marker = f"\n{RECONCILIATION_2_H3}\n"
    prefix, separator, _ = _read(ROADMAP_PATH).partition(marker)
    assert separator == marker
    return prefix


def _pre_reconciliation_3_prefix() -> str:
    marker = f"\n{RECONCILIATION_3_H3}\n"
    prefix, separator, _ = _read(ROADMAP_PATH).partition(marker)
    assert separator == marker
    return prefix


def test_artifact_paths_titles_and_exact_h2_heading_orders_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SCOPE_PATH.is_file()
    assert _headings_at_level(PLAN_PATH, 1) == (PLAN_TITLE,)
    assert _headings_at_level(SCOPE_PATH, 1) == (SCOPE_TITLE,)
    assert _headings_at_level(PLAN_PATH, 2) == PLAN_H2
    assert _headings_at_level(SCOPE_PATH, 2) == SCOPE_H2
    assert _headings_at_level(PLAN_PATH, 3) == (SLICE9_STATUS_H3,)
    assert _headings_at_level(SCOPE_PATH, 3) == ()


def test_exact_nine_slice_route_and_slice_classifications_are_locked() -> None:
    for document in (_read(PLAN_PATH), _read(SCOPE_PATH)):
        positions = []
        for number, slice_title in enumerate(PHASE52_ROUTE, start=1):
            marker = f"{number}. {slice_title}"
            assert marker in document, marker
            positions.append(document.index(marker))
        assert positions == sorted(positions)
        assert "neither reordered, merged, split, nor expanded" in document
        assert "Slice 1 is tests/docs/status-only" in document
    assert "MINIMUM_PRODUCTION_FOUNDATION" in _read(PLAN_PATH)
    assert "Phase 53" in _read(PLAN_PATH)
    assert "Phase 60" in _read(PLAN_PATH)


def test_read_model_first_authority_dimensions_and_non_authority_are_locked() -> None:
    documents = "\n".join((_read(PLAN_PATH), _read(SCOPE_PATH), _read(ROADMAP_PATH)))
    for required in (
        "sole compiler-acceptance authority",
        "exact current authority",
        "private, deterministic, exact-current evidence/read models",
        "semantic acceptance",
        "result type",
        "nullability",
        "diagnostics",
        "backend lowering",
        "project propagation",
        "dialect evidence",
        "public projection",
        "expression-stage evidence",
        "conflict/evidence precedence",
        "cannot accept or reject expressions or queries",
        "determine result type or nullability",
        "emit or suppress diagnostics",
        "determine SQL lowering",
        "rescue a backend failure",
        "project-propagation authority",
        "alter IR",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "Project JSON v2",
        "public Python API",
        "No declarative-authority cutover occurs",
        "public-contract parity evidence",
    ):
        assert required in documents, required


def test_lookup_support_disposition_and_private_reason_assignment_are_locked() -> None:
    documents = "\n".join((_read(PLAN_PATH), _read(SCOPE_PATH), _read(ROADMAP_PATH)))
    for required in (
        "Found(fact)",
        "Absent(key)",
        "Unknown(reason)",
        "Conflict(reason, evidence)",
        "ABSENT is first-class",
        "Absent does not mean unsupported",
        "Unsupported is an evidenced fact",
        "Unknown does not mean Absent",
        "SQL three-valued truth",
        "Conflict retains all evidence",
        "selects no winner",
        "fails closed",
        "SUPPORTED",
        "EXPLICITLY_UNSUPPORTED",
        "NONE",
        "DEFERRED(owner, reason)",
        "OUT_OF_SCOPE(owner, reason)",
        "Only Found plus SUPPORTED",
        "Support does not imply portability",
        "semantic acceptance does not imply backend lowering",
        "one-dialect backend support does not imply cross-dialect support",
        "orthogonal to lookup and support",
        "Slice 2 exclusively selects the bounded private reason-code member vocabulary",
        "No reason-code member is a public diagnostic or API identifier",
    ):
        assert required in documents, required


def test_stage_vocabulary_clause_boundary_and_no_solver_are_locked() -> None:
    documents = "\n".join((_read(PLAN_PATH), _read(SCOPE_PATH), _read(ROADMAP_PATH)))
    for required in (
        "CONSTANT",
        "ROW",
        "GROUP",
        "WINDOW",
        "UNKNOWN",
        "WINDOW is reserved for Phase 53",
        "assigned to no current",
        "Global aggregate expressions are GROUP",
        "keyed aggregate expressions are GROUP",
        "Relation identity",
        "cardinality",
        "grain",
        "ProjectRowResultRole",
        "project row-schema availability",
        "Observed stage is distinct from clause-required stage",
        "stage evidence does not replace procedural semantic validation",
        "where",
        "satisfying",
        "order by",
        "group by",
        "required stage",
        "required result type",
        "expression-shape restrictions",
        "clause scope",
        "alias restrictions",
        "no stage solver",
        "inference variables",
        "unification",
        "typeclasses",
        "traits",
        "generic overload resolution",
        "row polymorphism",
        "grain lattice",
        "shadow solver",
        "authoritative typed IR",
    ):
        assert required in documents, required


def test_fact_family_responsibilities_are_non_overlapping() -> None:
    documents = "\n".join((_read(PLAN_PATH), _read(SCOPE_PATH), _read(ROADMAP_PATH)))
    for required in (
        "CapabilityKey",
        "CapabilityDisposition",
        "CapabilityLookupResult",
        "LogicalTypeCapabilityFact",
        "FunctionSignatureFact",
        "OperatorSignatureFact",
        "ClauseCapabilityFact",
        "AggregateSignatureFact",
        "ExpressionStageFact",
        "exact current scalar functions",
        "unary operators",
        "binary operators",
        "comparisons",
        "null tests",
        "aggregate identity",
        "arity",
        "argument logical types",
        "argument shape",
        "result logical type",
        "result nullability",
        "empty-input algebra",
        "null elimination",
        "let/group context",
        "dialect/backend evidence",
        "descriptive private evidence only",
        "responsibilities do not overlap",
    ):
        assert required in documents, required


def test_conflict_ledger_is_complete_evidence_only_and_fail_closed() -> None:
    scope = _read(SCOPE_PATH)
    ledger = re.search(
        r"^## Current Conflict Ledger Contract\n(.*?)^## Solver-readiness",
        scope,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert ledger is not None
    entries = tuple(
        entry.replace(chr(96), "")
        for entry in re.findall(r"^\d+\. (.+)$", ledger.group(1), flags=re.MULTILINE)
    )
    assert entries == (
        "count(alias/Shape).",
        "semantic LIKE versus PostgreSQL/private MySQL lowering.",
        "matches(Text, Text) across PostgreSQL and private MySQL.",
        "non-Decimal type arguments accepted by grammar/AST but not generally consumed semantically.",
        "division / without a concrete semantic result rule.",
        "null literal versus unresolved-expression unknown carriers.",
        "generic comparison outer Bool UNKNOWN versus pairwise compatibility.",
        "no-GROUP global aggregate post-filtering versus satisfying's GROUP BY requirement.",
    )
    for required in (
        "evidence only",
        "changes no behavior",
        "repairs no issue",
        "chooses no winner",
        "claims no portability",
        "adds no diagnostic",
        "adds no new deferred owner",
        "fails closed",
    ):
        assert required in ledger.group(1), required


def test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked() -> None:
    documents = "\n".join((_read(PLAN_PATH), _read(SCOPE_PATH), _read(ROADMAP_PATH)))
    for required in (
        "no production capability carrier",
        "no compiler behavior",
        "grammar",
        "generated",
        "parser",
        "AST",
        "semantic",
        "diagnostic",
        "IR",
        "SQL",
        "CLI",
        "JSON",
        "public API",
        "runtime",
        "database",
        "package",
        "dependency",
        "release",
        "backend behavior",
        "private and unserialized",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "Project JSON v2",
        "0.1.0",
        "no tag",
        "publish",
        "upload",
        "signing",
        "attestation",
    ):
        assert required in documents, required

    compiler_paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    compiler_paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    compiler_paths.sort(key=lambda path: path.relative_to(REPO_ROOT).as_posix())
    compiler_digest = hashlib.sha256()
    for path in compiler_paths:
        compiler_digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        compiler_digest.update(b"\0")
        compiler_digest.update(path.read_bytes())
        compiler_digest.update(b"\0")
    assert (len(compiler_paths), compiler_digest.hexdigest()) == (
        103,
        COMPILER_DIGEST,
    )
    for relative_path in BOUNDARY_PATHS:
        assert re.findall(
            r'^BOUNDARY_HASH = "([0-9a-f]{64})"$',
            _read(REPO_ROOT / relative_path),
            flags=re.MULTILINE,
        ) == [COMPILER_DIGEST]

    project_paths = sorted(
        (
            path
            for path in (REPO_ROOT / "src/pietto/_project").rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(REPO_ROOT).as_posix(),
    )
    project_digest = hashlib.sha256()
    for path in project_paths:
        project_digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        project_digest.update(b"\0")
        project_digest.update(path.read_bytes())
        project_digest.update(b"\0")
    assert (len(project_paths), project_digest.hexdigest()) == (
        28,
        PROJECT_PRIVATE_DIGEST,
    )
    assert (
        '"project_private": (\n        "src/pietto/_project",\n'
        f'        28,\n        "{PROJECT_PRIVATE_DIGEST}",\n    ),'
    ) in _read(REPO_ROOT / "tests/test_phase33_completion_audit.py")

    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""


def test_roadmap_reconciliation2_preserves_exact_prefix_and_eof_shape() -> None:
    roadmap = _read(ROADMAP_PATH)
    assert (
        hashlib.sha256(_pre_reconciliation_2_prefix().encode()).hexdigest()
        == PRE_RECONCILIATION_2_SHA256
    )
    assert (
        roadmap.count(
            "### Reconciliation 1 — Phase 51 Conditional Completion And Phase 52 Handoff"
        )
        == 1
    )
    assert roadmap.count(RECONCILIATION_2_H3) == 1
    assert (
        hashlib.sha256(_pre_reconciliation_3_prefix().encode()).hexdigest()
        == PRE_RECONCILIATION_3_SHA256
    )
    assert roadmap.count(RECONCILIATION_3_H3) == 1
    assert roadmap.count(RECONCILIATION_4_H3) == 1
    reconciliation3 = roadmap[
        roadmap.index(RECONCILIATION_3_H3) : roadmap.index(RECONCILIATION_4_H3)
    ]
    reconciliation4 = roadmap[roadmap.index(RECONCILIATION_4_H3) :]
    assert "\n### " not in reconciliation3
    assert "\n### " not in reconciliation4
    assert roadmap.endswith("\n")
    assert CURRENT_ROADMAP_PATH.is_file()


def test_reconciliation2_conditional_lifecycle_and_next_gate_are_locked() -> None:
    roadmap = _read(ROADMAP_PATH)
    reconciliation = roadmap[
        roadmap.index(RECONCILIATION_2_H3) : roadmap.index(RECONCILIATION_3_H3)
    ]
    lifecycle = (
        "Before the Slice 1 Gate 3 condition, Phase 52 remains UNSTARTED. After and "
        "only after the exact Slice 1 completion commit receives one normal push to "
        "main and its natural CI / push run is completed / success with headSha "
        "exactly equal to that commit, Phase 52 becomes ACTIVE and remains "
        "incomplete; Slice 1 is complete; Slices 2–9 and Phases 53–60 remain "
        "UNSTARTED. No post-CI repository status-flip commit is planned or required. "
        "The next separately authorized gate is Phase 52 Slice 2 Gate 0 and Gate 1."
    )
    assert lifecycle in reconciliation
    assert "Phase 52 becomes ACTIVE" in reconciliation
    assert "Phase 52 " + "is ACTIVE" not in reconciliation
    assert (
        "No post-CI repository status-flip commit is planned or required."
        in reconciliation
    )
    assert "Phase 52 Slice 2 Gate 0 and Gate 1" in reconciliation
    reconciliation3 = roadmap[
        roadmap.index(RECONCILIATION_3_H3) : roadmap.index(RECONCILIATION_4_H3)
    ]
    assert "Phase 52 remains ACTIVE and incomplete" in reconciliation3
    assert "Phase 52 are `COMPLETED`" in reconciliation3
    assert "Phases 53–60 remain `UNSTARTED`" in reconciliation3
    assert "Phase 53 Slice 1 Gate 0 and Gate 1" in reconciliation3
    reconciliation4 = roadmap[roadmap.index(RECONCILIATION_4_H3) :]
    normalized4 = " ".join(reconciliation4.split())
    for required in (
        "b8029699ccc51bfa500856155b18e666898cb883",
        "Phase 53 remains `UNSTARTED`",
        "pietto-active-roadmap-phase53-70-v1.md",
        "sole current roadmap authority",
        "Phase 53 Slice 1 Gate 3",
        "no automatic implementation authorization",
    ):
        assert required in normalized4, required
    assert _headings_at_level(CURRENT_ROADMAP_PATH, 1) == (
        "Pietto Active Roadmap Phase 53–70 v1",
    )


def test_phase51_compatibility_migrations_preserve_historical_locks() -> None:
    sources = {path.name: _read(path) for path in COMPATIBILITY_PATHS}
    assignments: dict[str, dict[str, set[str]]] = {}
    for name, source in sources.items():
        constants: dict[str, set[str]] = {}
        for node in ast.parse(source, filename=name).body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Set):
                continue
            value = ast.literal_eval(node.value)
            if not isinstance(value, set) or not all(
                isinstance(item, str) for item in value
            ):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value
        assignments[name] = constants

    scope_name = "test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py"
    selected_name = "test_phase51_selected_let_accepted_expression_aggregate.py"
    cross_name = "test_phase51_cross_phase_readiness_privacy_compatibility_closure.py"
    completion_name = "test_phase51_completion_audit_and_status_lock.py"
    assert len(assignments[scope_name]["ALLOWED_PHASE51_SLICE1_GATE2_PATHS"]) == 4
    assert (
        assignments[scope_name]["ALLOWED_PHASE52_SLICE1_GATE2_PATHS"]
        == PHASE52_GATE2_PATHS
    )
    assert len(assignments[selected_name]["EXPECTED_GATE2_PATHS"]) == 15
    assert (
        assignments[selected_name]["PHASE52_SLICE1_GATE2_PATHS"] == PHASE52_GATE2_PATHS
    )
    assert len(assignments[cross_name]["EXPECTED_GATE2_PATHS"]) == 20
    assert len(assignments[cross_name]["EXPECTED_UNTRACKED_PATHS"]) == 2
    assert assignments[cross_name]["PHASE52_GATE2_PATHS"] == PHASE52_GATE2_PATHS
    assert assignments[cross_name]["PHASE52_UNTRACKED_PATHS"] == PHASE52_UNTRACKED_PATHS
    assert len(assignments[completion_name]["SLICE12_GATE2_PATHS"]) == 4
    assert len(assignments[completion_name]["SLICE12_UNTRACKED_PATHS"]) == 2
    assert assignments[completion_name]["PHASE52_GATE2_PATHS"] == PHASE52_GATE2_PATHS
    assert (
        assignments[completion_name]["PHASE52_UNTRACKED_PATHS"]
        == PHASE52_UNTRACKED_PATHS
    )

    expected_forbidden = {
        "test_phase51_aggregate_only_project_row_schema.py": (
            {"docs/spec/pietto-active-roadmap-phase51-60-v1.md"},
            30,
            {
                "src/pietto/_project/model.py",
                "src/pietto/semantic",
                "src/pietto/ir",
                "src/pietto/sql",
                "docs/spec/pietto-roadmap-phase45-60-v1.md",
                "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md",
                "scripts",
                ".github",
                "pyproject.toml",
                "uv.lock",
                "tests/fixtures",
                "tests/goldens",
                "examples",
            },
        ),
        "test_phase51_grouped_aggregate_project_row_schema.py": (
            {
                "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
            },
            33,
            {
                "src/pietto/_project/model.py",
                "src/pietto/semantic",
                "src/pietto/ir",
                "src/pietto/sql",
                "docs/spec/pietto-roadmap-phase45-60-v1.md",
                "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md",
                "docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md",
                "tests/test_phase51_private_result_role_output_identity.py",
                "tests/test_phase51_group_key_project_row_schema.py",
                "scripts",
                ".github",
                "pyproject.toml",
                "uv.lock",
                "tests/fixtures",
                "tests/goldens",
                "examples",
            },
        ),
    }
    for name, (removed, expected_length, retained) in expected_forbidden.items():
        tree = ast.parse(sources[name], filename=name)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff"
        )
        assignment = next(
            node
            for node in function.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "forbidden_paths"
                for target in node.targets
            )
        )
        paths = ast.literal_eval(assignment.value)
        assert isinstance(paths, tuple)
        assert len(paths) == expected_length
        assert len(set(paths)) == len(paths)
        assert all(path not in paths for path in removed)
        assert retained.issubset(paths)

    completion_source = sources[completion_name]
    assert "ROADMAP_RECONCILIATION_HEADING" in completion_source
    assert "ROADMAP_PREFIX_DIGEST" in completion_source
    assert "Phase 52 " + "is ACTIVE" in completion_source


def test_static_audit_shape_allowlist_and_heading_matching_are_locked() -> None:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_PATH.as_posix())
    expected_functions = (
        "_read",
        "_slice13_paths",
        "_phase54_slice2_paths",
        "_normalized",
        "_headings_at_level",
        "_git_output",
        "_dirty_paths",
        "_top_level_test_names",
        "_pytest_item_count",
        "_pre_reconciliation_2_prefix",
        "_pre_reconciliation_3_prefix",
        "test_artifact_paths_titles_and_exact_h2_heading_orders_are_locked",
        "test_exact_nine_slice_route_and_slice_classifications_are_locked",
        "test_read_model_first_authority_dimensions_and_non_authority_are_locked",
        "test_lookup_support_disposition_and_private_reason_assignment_are_locked",
        "test_stage_vocabulary_clause_boundary_and_no_solver_are_locked",
        "test_fact_family_responsibilities_are_non_overlapping",
        "test_conflict_ledger_is_complete_evidence_only_and_fail_closed",
        "test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked",
        "test_roadmap_reconciliation2_preserves_exact_prefix_and_eof_shape",
        "test_reconciliation2_conditional_lifecycle_and_next_gate_are_locked",
        "test_phase51_compatibility_migrations_preserve_historical_locks",
        "test_static_audit_shape_allowlist_and_heading_matching_are_locked",
    )
    assert (
        tuple(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
        == expected_functions
    )
    assert _top_level_test_names(SELF_PATH) == expected_functions[11:]
    assert _pytest_item_count(SELF_PATH) == 12
    assert all(
        not node.decorator_list
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )

    allowed_import_roots = {
        "__future__",
        "_phase54_active_gate2_manifest",
        "ast",
        "hashlib",
        "pathlib",
        "re",
        "subprocess",
        "tomllib",
    }
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".", maxsplit=1)[0] in allowed_import_roots
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            assert node.module.split(".", maxsplit=1)[0] in allowed_import_roots

    subprocess_calls = tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    )
    assert len(subprocess_calls) == 1
    command = subprocess_calls[0].args[0]
    assert isinstance(command, ast.List)
    assert isinstance(command.elts[0], ast.Constant)
    assert command.elts[0].value == "git"
    assert isinstance(command.elts[1], ast.Starred)
    assert _git_output(["diff", "--cached", "--name-status"]) == ""

    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added
    dirty_paths = _dirty_paths()
    if _phase54_product_repair1_gate2_is_active():
        assert _headings_at_level(PLAN_PATH, 2) == PLAN_H2
        assert _headings_at_level(SCOPE_PATH, 2) == SCOPE_H2
        return
    assert dirty_paths in (
        set(),
        PHASE52_GATE2_PATHS,
        PHASE52_SLICE1_CI_REPAIR_PATHS,
        SLICE9_ALLOWLIST_PATHS,
        PHASE53_ALLOWLIST_PATHS,
        slice13_allowlist,
    )
    untracked_paths = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    assert untracked_paths in (
        set(),
        PHASE52_UNTRACKED_PATHS,
        SLICE9_ADDED_PATHS,
        PHASE53_ADDED_PATHS,
        slice13_added,
    )
    if dirty_paths == slice13_allowlist:
        assert set(_git_output(["diff", "--name-only"]).splitlines()) == (
            slice13_modified
        )
        assert untracked_paths == slice13_added
        assert _git_output(["branch", "--show-current"]) == "main"
        expected_head = (
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
            if any(
                path.startswith("docs/spec/phase54-slice9-") for path in slice13_added
            )
            else "027b33cafcfd58916a89e299487dad38d24ade6c"
            if any(
                path.startswith("docs/spec/phase54-slice8-") for path in slice13_added
            )
            else "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
            if any(
                path.startswith("docs/spec/phase54-slice7-") for path in slice13_added
            )
            else "c44a4271d9592cb393d2232f127a59d8466cc60a"
            if any(
                path.startswith("docs/spec/phase54-slice6-") for path in slice13_added
            )
            else "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
            if any(
                path.startswith("docs/spec/phase54-slice5-") for path in slice13_added
            )
            else "15bae172ee151e370fe59d3bf909d735aee6aa90"
            if any(
                path.startswith("docs/spec/phase54-slice4-") for path in slice13_added
            )
            else "d8a5e9ab3de70ce30575513c73560c86430eca63"
            if any(path.startswith("docs/spec/phase54-slice") for path in slice13_added)
            else "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52"
        )
        for reference in ("HEAD", "main", "origin/main"):
            assert _git_output(["rev-parse", reference]) == expected_head
    if dirty_paths == SLICE9_ALLOWLIST_PATHS:
        assert set(_git_output(["diff", "--name-only"]).splitlines()) == (
            SLICE9_MODIFIED_PATHS
        )
        assert untracked_paths == SLICE9_ADDED_PATHS
        assert _git_output(["branch", "--show-current"]) == "main"
        assert _git_output(["rev-parse", "HEAD"]) == SLICE9_BASE_HEAD_SHA
        assert _git_output(["rev-parse", "main"]) == SLICE9_BASE_HEAD_SHA
        assert _git_output(["rev-parse", "origin/main"]) == SLICE9_BASE_HEAD_SHA
    if dirty_paths == PHASE53_ALLOWLIST_PATHS:
        assert set(_git_output(["diff", "--name-only"]).splitlines()) == (
            PHASE53_MODIFIED_PATHS
        )
        assert untracked_paths == PHASE53_ADDED_PATHS
        assert _git_output(["branch", "--show-current"]) == "main"
        assert _git_output(["rev-parse", "HEAD"]) == PHASE53_BASE_HEAD_SHA
        assert _git_output(["rev-parse", "main"]) == PHASE53_BASE_HEAD_SHA
        assert _git_output(["rev-parse", "origin/main"]) == PHASE53_BASE_HEAD_SHA
    assert _headings_at_level(PLAN_PATH, 2) == PLAN_H2
    assert _headings_at_level(SCOPE_PATH, 2) == SCOPE_H2


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
