from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

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
COMPILER_DIGEST = "6cbe7ccfbd84d7b2966964ac91a56e7eeacdc798c3d161da64d61add662b0420"
PROJECT_PRIVATE_DIGEST = (
    "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
