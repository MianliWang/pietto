from __future__ import annotations

import ast
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pietto.semantic.capability_aggregates as capability_aggregates
import pietto.semantic.capability_contexts as capability_contexts
import pietto.semantic.capability_facts as capability_facts
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_lookup as capability_lookup
import pietto.semantic.capability_signatures as capability_signatures
import pietto.semantic.capability_windows as capability_windows
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = "docs/plan/phase-52-core-type-system-capability-foundation.md"
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
CURRENT_ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
SPEC_REL = "docs/spec/phase52-completion-audit-and-status-lock-v1.md"
SELF_REL = "tests/test_phase52_completion_audit_and_status_lock.py"
SLICE1_TEST_REL = (
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py"
)
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE4_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SLICE5_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
SLICE6_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
SLICE7_TEST_REL = "tests/test_phase52_aggregate_signature_algebra_facts.py"
SLICE8_TEST_REL = (
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py"
)
SLICE_TEST_RELS = (
    SLICE1_TEST_REL,
    SLICE2_TEST_REL,
    SLICE3_TEST_REL,
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
    SELF_REL,
)
SLICE_SPEC_RELS = (
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "docs/spec/phase52-private-capability-key-disposition-evidence-fact-foundation-v1.md",
    "docs/spec/phase52-fail-closed-capability-lookup-v1.md",
    "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md",
    "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md",
    "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md",
    "docs/spec/phase52-aggregate-signature-algebra-facts-v1.md",
    "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md",
    SPEC_REL,
)

SPEC_TITLE = "Phase 52 Slice 9 Completion Audit And Status Lock v1"
SPEC_H2 = (
    "Purpose And Slice Identity",
    "Status And Completion Authority",
    "Trusted Slice 8 Baseline",
    "Phase 52 Slice Ledger",
    "Phase 52 Artifact Inventory",
    "Historical Allowlist And Repair Preservation",
    "Private Capability Architecture Completion",
    "Domain Fact And Key Inventory Audit",
    "Completeness Schema And Four-result Lookup Audit",
    "Evidence Support Disposition And Conflict Audit",
    "Privacy Consumer And No-authority Audit",
    "No-behavior Compiler Project Public Runtime Audit",
    "Repair And Checkout Compatibility Audit",
    "Compiler Semantic Phase15 Project Lock Audit",
    "Package Workflow Dependency And Release Audit",
    "Deferred-owner Audit",
    "Phase 53 Window Handoff",
    "Protected Surface Audit",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 53–60 Status",
    "Active-roadmap Reconciliation",
    "Exact Gate 2 Allowlist",
    "Completion Invariants And Drift Locks",
    "Validation And Clean-CI Boundary",
    "Separate Authorization Boundary",
    "Stop Conditions",
)
EXPECTED_TEST_NAMES = (
    "test_slice9_artifacts_title_and_exact_heading_order_are_locked",
    "test_slice1_8_route_artifact_lifecycle_repair_and_focused_item_ledgers_are_exact",
    "test_private_capability_modules_fact_key_completeness_lookup_and_conflict_closure_is_locked",
    "test_evidence_support_disposition_backend_and_cross_phase_ownership_are_locked",
    "test_privacy_consumers_exports_authority_and_no_behavior_boundaries_are_locked",
    "test_phase53_window_handoff_roadmap_reconciliation_and_next_gate_are_locked",
    "test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe",
    "test_shallow_push_synthetic_merge_and_historical_provenance_guards_are_locked",
    "test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "test_completion_encoding_gate2_gate3_ci_and_no_release_boundaries_are_locked",
    "test_static_git_helper_and_exact_slice9_dirty_set_are_locked",
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
SLICE_SHAPES = (
    (12, 12),
    (20, 25),
    (24, 34),
    (28, 64),
    (28, 64),
    (28, 69),
    (28, 69),
    (28, 69),
    (11, 11),
)

FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
WINDOW_REL = "src/pietto/semantic/capability_windows.py"
MODULE_RELS = (
    FACTS_REL,
    LOOKUP_REL,
    INVENTORY_REL,
    SIGNATURE_REL,
    CONTEXT_REL,
    AGGREGATE_REL,
    WINDOW_REL,
)
MODULE_OBJECTS = (
    capability_facts,
    capability_lookup,
    capability_inventory,
    capability_signatures,
    capability_contexts,
    capability_aggregates,
    capability_windows,
)
MODULE_SHA256 = {
    FACTS_REL: "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21",
    LOOKUP_REL: "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26",
    INVENTORY_REL: "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26",
    SIGNATURE_REL: "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2",
    CONTEXT_REL: "132371eccca00ca9f8722a34f1ea0f540933515e560639ee12e53aee6594c60c",
    AGGREGATE_REL: "d7d69fa4b97924ef5462af9c871a910b73cad43a21431e98a72c8bdab8996c80",
    WINDOW_REL: "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e",
}
PATH_DIGESTS = {
    "compiler": "6cbe7ccfbd84d7b2966964ac91a56e7eeacdc798c3d161da64d61add662b0420",
    "semantic": "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    "phase15": "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d",
    "project": "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830",
}
PROTECTED_SHA256 = {
    ".github/workflows/ci.yml": "56339c3e565471c3a95a0f79a05eaf9596d734a173d1936d5df167526508ddac",
    "pyproject.toml": "851e706f2cbafb24c48068cdd6fd8a6ada1f93317618000be71db3681c40a1a8",
    "uv.lock": "12795f072df20fb688b37e484dd4561cd33e34bf601be3cb0fa1f9075eee38a2",
    ".python-version": "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169",
}
PRE_RECONCILIATION_3_SHA256 = (
    "cb2c51246f1e312858641750d1a416125f99058fb0182949e9afe35ae49e97cf"
)
RECONCILIATION_3_H3 = (
    "### Reconciliation 3 — Phase 52 Conditional Completion And Phase 53 Handoff"
)
RECONCILIATION_4_H3 = (
    "### Reconciliation 4 — Phase 52 Completion, Phase 53–70 Current-authority "
    "Handoff, Release, And Rust Route"
)

GATE2_BASE_HEAD_SHA = "36e466535d923f708a0201ae15a5708f06f2b1f8"
GATE2_BASE_PARENT_SHA = "7a221ffdca91335a526ed12a1059340bda642fdb"
GATE2_BASE_TREE_SHA = "e2873c562a4a21e7ad284ccbf736f193da58a5ed"
GATE2_BASE_SUBJECT = "Fix Phase 52 shallow checkout history guard"
HISTORICAL_SETUP_JAVA_HEAD_SHA = "11a0c48941c3c1c650be8d0ec8ddf5201f9525f2"
HISTORICAL_SETUP_JAVA_PARENT_SHA = "7bea69da0465f57580961e4ca4a2c18a84dfb68c"
HISTORICAL_SETUP_JAVA_TREE_SHA = "2953c238f27239d796c9af05543b48c1add2a69d"
SLICE9_MODIFIED_PATHS = {
    PLAN_REL,
    ROADMAP_REL,
    SLICE1_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
SLICE9_ADDED_PATHS = {SPEC_REL, SELF_REL}
PHASE53_BASE_HEAD_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
PHASE53_MODIFIED_PATHS = {
    ROADMAP_REL,
    SLICE1_TEST_REL,
    SELF_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
PHASE53_ADDED_PATHS = {
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md",
    CURRENT_ROADMAP_REL,
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
}
SLICE2_BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE2_STATE_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"

OWNER_HANDOFFS = (
    "PHASE_53",
    "PHASE_54",
    "PHASE_55",
    "PHASE_56",
    "PHASE_57",
    "PHASE_58",
    "PHASE_59",
    "PHASE_60",
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
EVIDENCE_SOURCE_COUNTS = {
    CapabilityEvidenceSource.GRAMMAR_AST: 267,
    CapabilityEvidenceSource.SEMANTIC_CATALOG: 87,
    CapabilityEvidenceSource.SEMANTIC_PROCEDURE: 397,
    CapabilityEvidenceSource.SEMANTIC_MODEL: 130,
    CapabilityEvidenceSource.IR: 247,
    CapabilityEvidenceSource.BACKEND: 236,
    CapabilityEvidenceSource.PROJECT: 129,
    CapabilityEvidenceSource.PUBLIC: 18,
    CapabilityEvidenceSource.ROADMAP: 90,
    CapabilityEvidenceSource.TEST: 465,
    CapabilityEvidenceSource.SPEC: 307,
}
TIER1_BYTES = 5525
TIER1_SHA256 = "2097b7aace8604cb54af6392a9e400543fa7eefac4423f810d8a37451c05d48b"
TIER2_BYTES = 18026
TIER2_SHA256 = "6ab2027b7c8cb7858fbea2d3902130a4a860e462102ac4e582990f4bcfa501bf"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(relative),
            flags=re.MULTILINE,
        )
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _compiler_paths() -> tuple[Path, ...]:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return tuple(paths)


def _project_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src/pietto/_project").rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _parametrize_values(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 1
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        target = decorator.func
        if not (
            isinstance(target, ast.Attribute)
            and target.attr == "parametrize"
            and len(decorator.args) >= 2
        ):
            continue
        values = decorator.args[1]
        assert isinstance(values, (ast.List, ast.Tuple))
        count *= len(values.elts)
    return count


def _pytest_shape(relative: str) -> tuple[int, int, tuple[str, ...]]:
    functions = tuple(
        node
        for node in ast.parse(_read(relative), filename=relative).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    return (
        len(functions),
        sum(_parametrize_values(function) for function in functions),
        tuple(function.name for function in functions if function.decorator_list),
    )


def _literal_tuple(relative: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is not None:
            result = ast.literal_eval(value)
            assert isinstance(result, tuple)
            assert all(isinstance(item, str) for item in result)
            return cast(tuple[str, ...], result)
    raise AssertionError(f"missing literal tuple {name}")


def _literal_string_set(relative: str, name: str) -> set[str]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        result = ast.literal_eval(node.value)
        assert isinstance(result, set)
        assert all(isinstance(item, str) for item in result)
        return cast(set[str], result)
    raise AssertionError(f"missing literal string set {name}")


def _families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        cast(tuple[CapabilityFact, ...], capability_inventory._CAPABILITY_FACTS),
        cast(
            tuple[CapabilityFact, ...],
            capability_signatures._CAPABILITY_SIGNATURE_FACTS,
        ),
        cast(tuple[CapabilityFact, ...], capability_contexts._CAPABILITY_CONTEXT_FACTS),
        cast(
            tuple[CapabilityFact, ...],
            capability_aggregates._AGGREGATE_CAPABILITY_FACTS,
        ),
        cast(
            tuple[CapabilityFact, ...],
            capability_windows._WINDOW_CAPABILITY_FACTS,
        ),
    )


def _all_facts() -> tuple[CapabilityFact, ...]:
    return tuple(fact for family in _families() for fact in family)


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    if key.domain in {
        CapabilityDomain.LOGICAL_TYPE,
        CapabilityDomain.LITERAL,
        CapabilityDomain.PARAMETER,
    }:
        facts, complete = cast(Any, capability_inventory.inventory_lookup_inputs)(key)
        reason = None
    elif key.domain in {
        CapabilityDomain.SCALAR_FUNCTION,
        CapabilityDomain.UNARY_OPERATOR,
        CapabilityDomain.BINARY_OPERATOR,
        CapabilityDomain.COMPARISON,
        CapabilityDomain.NULL_TEST,
    }:
        facts, complete, reason = cast(
            Any, capability_signatures.signature_lookup_inputs
        )(key)
    elif key.domain in {CapabilityDomain.EXPRESSION_STAGE, CapabilityDomain.CLAUSE}:
        facts, complete, reason = cast(
            Any, capability_contexts.stage_clause_lookup_inputs
        )(key)
    elif key.domain is CapabilityDomain.AGGREGATE:
        facts, complete, reason = cast(
            Any, capability_aggregates.aggregate_lookup_inputs
        )(key)
    elif key.domain is CapabilityDomain.WINDOW_FUNCTION:
        facts, complete, reason = cast(Any, capability_windows.window_lookup_inputs)(
            key
        )
    else:
        facts, complete, reason = (), False, None
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _tier1_operands() -> tuple[str, ...]:
    direct = _literal_tuple(SLICE7_TEST_REL, "DIRECT_TIER1_NODES")
    filtered = tuple(node for node in direct if not node.startswith(SLICE1_TEST_REL))
    assert len(direct) == 44 and len(filtered) == 42
    deselections = (
        "--deselect="
        + SLICE2_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE3_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE4_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
    )
    return (*SLICE_TEST_RELS, *deselections, *filtered)


def _tier2_manifest() -> tuple[str, ...]:
    prior = _literal_tuple(SLICE6_TEST_REL, "TIER2_MANIFEST")
    removed = {
        "--deselect="
        + SLICE1_TEST_REL
        + "::test_static_audit_shape_allowlist_and_heading_matching_are_locked",
        "--deselect="
        + SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    }
    assert removed <= set(prior)
    return tuple(sorted(set(prior) - removed))


def test_private_capability_modules_fact_key_completeness_lookup_and_conflict_closure_is_locked() -> (
    None
):
    assert {_path: _sha256(_path) for _path in MODULE_RELS} == MODULE_SHA256
    for relative, module in zip(MODULE_RELS, MODULE_OBJECTS, strict=True):
        assert getattr(module, "__all__") == ()
        tree = ast.parse(_read(relative), filename=relative)
        imported = {
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        if relative == FACTS_REL:
            assert not any("capability_" in name for name in imported)
        else:
            capability_imports = {name for name in imported if "capability_" in name}
            assert capability_imports == {"pietto.semantic.capability_facts"}

    families = _families()
    facts = _all_facts()
    assert tuple(
        (len(family), len({fact.key for fact in family})) for family in families
    ) == (
        (41, 41),
        (39, 39),
        (18, 18),
        (69, 68),
        (24, 24),
    )
    assert (len(facts), len(set(facts)), len({fact.key for fact in facts})) == (
        191,
        191,
        190,
    )
    collisions = tuple(
        group
        for key in dict.fromkeys(fact.key for fact in facts)
        if len(group := tuple(fact for fact in facts if fact.key == key)) > 1
    )
    assert len(collisions) == 1
    conflict = collisions[0]
    assert tuple(fact.support for fact in conflict) == (
        CapabilitySupport.SUPPORTED,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert conflict[0].key.subject == "count"
    assert "Shape" in conflict[0].key.operands
    assert _lookup(conflict[0].key) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        conflict,
    )
    assert all(
        isinstance(_lookup(key), (Found, Conflict))
        for key in dict.fromkeys(fact.key for fact in facts)
    )
    reserved = {
        CapabilityDomain.DIALECT_LOWERING,
        CapabilityDomain.CONVERSION,
        CapabilityDomain.EXTENSION_SIGNATURE,
    }
    assert not any(fact.key.domain in reserved for fact in facts)


def test_evidence_support_disposition_backend_and_cross_phase_ownership_are_locked() -> (
    None
):
    facts = _all_facts()
    assert Counter(fact.support for fact in facts) == {
        CapabilitySupport.SUPPORTED: 162,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED: 29,
    }
    assert Counter(fact.disposition.kind for fact in facts) == {
        CapabilityDispositionKind.NONE: 176,
        CapabilityDispositionKind.DEFERRED: 14,
        CapabilityDispositionKind.OUT_OF_SCOPE: 1,
    }
    evidence = tuple(item for fact in facts for item in fact.evidence)
    assert len(evidence) == 2373
    assert Counter(item.source for item in evidence) == EVIDENCE_SOURCE_COUNTS
    dual = tuple(
        fact
        for fact in facts
        if {
            (item.dialect, item.backend)
            for item in fact.evidence
            if item.source is CapabilityEvidenceSource.BACKEND
        }
        == {("postgresql", "postgresql"), ("mysql", "private-mysql")}
    )
    positive = tuple(
        fact
        for fact in dual
        if fact.support is CapabilitySupport.SUPPORTED
        and all(
            item.reason is None
            for item in fact.evidence
            if item.source is CapabilityEvidenceSource.BACKEND
        )
    )
    assert (len(dual), len(positive)) == (110, 106)
    combined = _read(SPEC_REL) + _read(ROADMAP_REL)
    assert all(owner in combined for owner in OWNER_HANDOFFS)
    assert "No owner is added,\nrenamed, removed, transferred" in _read(SPEC_REL)


def test_privacy_consumers_exports_authority_and_no_behavior_boundaries_are_locked() -> (
    None
):
    forbidden_names = {
        "inventory_lookup_inputs",
        "signature_lookup_inputs",
        "stage_clause_lookup_inputs",
        "aggregate_lookup_inputs",
        "window_lookup_inputs",
    }
    stems = {Path(relative).stem for relative in MODULE_RELS}
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in {*MODULE_RELS, preservation_rel} or "generated" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden_names)
        assert all(f"semantic.{stem}" not in source for stem in stems)
    preservation_source = _read(preservation_rel)
    assert all(name in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source
    assert "capability_" not in _read("src/pietto/__init__.py")
    assert "capability_" not in _read("src/pietto/semantic/__init__.py")
    spec = _read(SPEC_REL)
    for phrase in (
        "Forbidden production and public consumer count is exactly zero.",
        "not compiler authority",
        "claims no authority over grammar, generated parser, AST",
        "Slice 9 adds no production\nsource and implements no Phase 53",
    ):
        assert phrase in spec


def test_phase53_window_handoff_roadmap_reconciliation_and_next_gate_are_locked() -> (
    None
):
    roadmap = _read(ROADMAP_REL)
    marker = f"\n{RECONCILIATION_3_H3}\n"
    prefix, separator, remainder = roadmap.partition(marker)
    assert separator == marker
    assert hashlib.sha256(prefix.encode()).hexdigest() == PRE_RECONCILIATION_3_SHA256
    assert roadmap.count(RECONCILIATION_3_H3) == 1
    reconciliation, separator, reconciliation4 = remainder.partition(
        f"\n{RECONCILIATION_4_H3}\n"
    )
    assert separator == f"\n{RECONCILIATION_4_H3}\n"
    assert roadmap.count(RECONCILIATION_4_H3) == 1
    assert "\n### " not in reconciliation
    assert "\n### " not in reconciliation4
    assert roadmap.endswith("\n")
    for phrase in (
        "Phase 52 remains ACTIVE and incomplete",
        "Phase 52 are `COMPLETED`",
        "Phases 53–60 remain `UNSTARTED`",
        "Phase 53 is the next planned phase but does not automatically become ACTIVE",
        "Phase 53 Slice 1 Gate 0 and Gate 1",
    ):
        assert phrase in reconciliation
    current = _read(CURRENT_ROADMAP_REL)
    current_handoff = " ".join((reconciliation4 + current).split())
    for phrase in (
        "Phase 53 remains `UNSTARTED`",
        "sole current roadmap authority",
        "Phase 53 Slice 1 Gate 3",
        "Release 0.1.0",
        "big-bang",
        "no automatic implementation authorization",
    ):
        assert phrase in current_handoff, phrase
    facts = _all_facts()
    assert not any(
        fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        and "WINDOW" in fact.key.operands
        for fact in facts
    )
    window = CapabilityKey(
        CapabilityDomain.EXPRESSION_STAGE,
        subject="aggregate_dependent_expression",
        operation="observed_stage",
        operands=("WINDOW",),
        context="expression",
    )
    assert _lookup(window) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert all(
        phrase in _read(SPEC_REL)
        for phrase in ("No `OVER`", "aggregate-as-window", "Phase 53 is not started")
    )
