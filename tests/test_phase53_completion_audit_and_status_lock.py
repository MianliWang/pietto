from __future__ import annotations

import ast
import enum
import hashlib
import re
from collections import Counter
from pathlib import Path


import pietto.ir as ir_package
import pietto.semantic.capability_windows as capability_windows
import pietto.sql as sql_package
from pietto.ir.model import (
    WindowCallIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowSpecIR,
)
from pietto.semantic.capability_lookup import Found, Unknown, lookup_capability
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-completion-audit-and-status-lock-v1.md"
SELF_REL = "tests/test_phase53_completion_audit_and_status_lock.py"
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
SLICE2_STATE_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"

SPEC_TITLE = "Phase 53 Slice 16 Completion Audit And Status Lock v1"
SPEC_H2 = (
    "Purpose And Slice Identity",
    "Status And Completion Authority",
    "Trusted Slice 15 Baseline",
    "Phase 53 Sixteen-slice Route Ledger",
    "Publication And Repair Evidence Ledger",
    "Window Identity Signature And Nullability Closure",
    "PostgreSQL Dialect Closure",
    "Private MySQL Dialect Closure",
    "Window IR And Capability Non-authority Closure",
    "Diagnostic And Behavior Closure",
    "Privacy And Public-surface Closure",
    "Serializer And Metadata Boundary Audit",
    "Generated Golden And Fixture Stability",
    "Package Workflow Dependency And Release Audit",
    "Rust And Remote-package Deferral",
    "Future-owner Audit",
    "Fail-closed Non-owned Boundary Audit",
    "Reader Fixed Point And Test Accounting",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 54–70 Status",
    "Exact Gate 2 Allowlist",
    "Completion Invariants And Drift Locks",
    "Validation And Clean-CI Boundary",
    "Separate Authorization Boundary",
    "Stop Conditions",
)
EXPECTED_TEST_NAMES = (
    "test_slice16_artifacts_title_and_exact_heading_order_are_locked",
    "test_sixteen_row_route_titles_specifications_tests_and_shapes_are_exact",
    "test_slice1_15_publication_lifecycle_evidence_chain_and_next_authorization_are_locked",
    "test_window_identity_signature_nullability_and_capability_closure_is_locked",
    "test_postgresql_window_lowering_dialect_closure_is_locked",
    "test_private_mysql_window_lowering_dialect_closure_is_locked",
    "test_window_ir_privacy_and_capability_non_authority_closure_is_locked",
    "test_diagnostic_inventory_and_fail_closed_ordering_closure_is_locked",
    "test_privacy_public_exports_serializers_and_generated_closure_is_locked",
    "test_phase60_63_69_70_future_owner_boundaries_are_locked",
    "test_package_version_tag_release_and_rust_closure_is_locked",
    "test_generated_golden_fixture_workflow_dependency_stability_is_locked",
    "test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe",
    "test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "test_completion_encoding_gate2_gate3_ci_and_phase54_boundaries_are_locked",
    "test_static_git_helper_and_exact_slice16_dirty_set_are_locked",
)
PHASE53_ROUTE = (
    "Scope, Authority, Phase 53–70 Roadmap, Global Window Keyword, And Activation",
    "Pietto-native Window Syntax And Contextual Grammar Contract",
    "WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract",
    "Generic Type-variable, Constraint, And Exact Compatibility Foundation",
    "Nullability Algebra And Signature Result-formula Foundation",
    "Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles",
    "row_number Direct-field MVP",
    "rank / dense_rank And Peer Semantics",
    "percent_rank / cume_dist / ntile",
    "Partition Binding, Multi-key Visibility, And Diagnostics",
    "Window-local Ordering, Direction, Mandatory-order Policy, And Determinism",
    "Generic lag / lead Navigation MVP",
    "Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility",
    "Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage",
    "Window IR, PostgreSQL/private-MySQL Lowering, WINDOW_FUNCTION Facts, And Phase 54–70 Readiness",
    "Completion Audit, Status Lock, Dialect, Privacy, And No-authority Closure",
)
SLICE_SPEC_RELS = (
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md",
    "docs/spec/phase53-window-syntax-contextual-grammar-contract-v1.md",
    "docs/spec/phase53-window-spec-function-identity-ast-contract-v1.md",
    "docs/spec/phase53-generic-type-variable-exact-compatibility-contract-v1.md",
    "docs/spec/phase53-nullability-algebra-signature-result-formula-contract-v1.md",
    "docs/spec/phase53-private-window-semantic-carrier-stage-dependency-result-role-contract-v1.md",
    "docs/spec/phase53-row-number-direct-field-mvp-contract-v1.md",
    "docs/spec/phase53-rank-dense-rank-peer-semantics-contract-v1.md",
    "docs/spec/phase53-percent-rank-cume-dist-ntile-contract-v1.md",
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "docs/spec/phase53-lag-lead-navigation-offset-default-nullability-contract-v1.md",
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md",
    "docs/spec/phase53-multiple-window-outputs-final-order-alias-downstream-schema-lineage-contract-v1.md",
    "docs/spec/phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md",
    SPEC_REL,
)
SLICE_TEST_RELS = (
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    SELF_REL,
)
SLICE_FUNCTION_COUNTS = (14, 16, 25, 31, 38, 36, 41, 45, 54, 67, 81, 64, 60, 67, 33, 16)
SLICE_ITEM_LEDGER = (
    69,
    70,
    70,
    190,
    145,
    156,
    168,
    279,
    424,
    627,
    834,
    381,
    489,
    507,
    208,
    16,
)

PHASE52_BASE_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
SLICE_PUBLICATION_SHAS = (
    "c309323216fb7e6c52afba060cb188b3bb618d34",
    "86b08e27bbe97589b143dc1043fb0ad743dbf88a",
    "ee0cb021160ead5ea6c0bcc80e569f4fdfef67a3",
    "8485715b17b2dcf3b9f99b84f7ad001bcfab42d5",
    "ea90f3957bcac4d85bd4f8b1938ad0508638f13a",
    "321ec6f80737015648bc1f81b0561fdd34610e92",
    "6c27621a9a0504f704bfba059f9b262c9f5e3e68",
    "f90bd653c3ece47a86a121095f4547783f35197f",
    "c9e04d833e36bdd7cdc521eeb2c5f030aac8a998",
    "54553396f61caefe74b57cd6ed6fa144725a50e4",
    "110e1a6d285675eb8cf7e5ac58e5ac905d856701",
    "d8c58e526f2ff18ad7473c89e63f10cf935e0bb0",
    "933cf2f4ad0aab245feda09462178b90ebf9b7a6",
    "9ff8c97f5d5996b5a27e13bcf45032b825f0a3d5",
    "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68",
)
REPAIR_SHAS = (
    "d52a4a80aee1a1708d8fd480f63aa450a1c25eff",
    "0b49cc02dc641472a4f3cc1bdf149b444dade9b2",
    "05114de0effaa3c9fff6ecd0dbb781bd553e91a6",
    "e2441308179d34a6806b61f533d5799b910fbbb0",
)
DEPENDABOT_SHAS = (
    "a5606761c040042d177874253e29c25f2e8e3fff",
    "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52",
)
SLICE16_BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE16_BASE_PARENT_SHA = "9ff8c97f5d5996b5a27e13bcf45032b825f0a3d5"
SLICE16_BASE_TREE_SHA = "ae9b3e5c1fc25e3894c61623cf84583a76ba0556"
SLICE16_BASE_SUBJECT = "Add Phase 53 window IR and dual-backend lowering"
SLICE16_COMMIT_SUBJECT = "Complete Phase 53 status and compatibility audit"
SLICE13_SUBJECT_WITH_PERIOD = "Add Phase 53 grouped-result window inputs."

WINDOW_FUNCTION_SQL_NAMES = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
}
WINDOW_IR_CLASSES = (
    WindowFunctionRoleIR,
    WindowFunctionIdentityIR,
    WindowOrderItemIR,
    WindowSpecIR,
    WindowCallIR,
)
CAPABILITY_WINDOWS_REL = "src/pietto/semantic/capability_windows.py"
CAPABILITY_WINDOWS_SHA256 = (
    "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e"
)
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
ROADMAP_SHA256 = "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3"

SLICE16_ADDED_PATHS = {
    SPEC_REL,
    SELF_REL,
}
SLICE16_MODIFIED_PATHS = {
    PLAN_REL,
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    SLICE2_STATE_REL,
}


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


def _top_level_test_functions(relative: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    return tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _module_literal(relative: str, name: str) -> object:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing literal {name} in {relative}")


def _window_fact_families() -> tuple[int, int]:
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    signature = tuple(fact for fact in facts if fact.key.operation == "signature")
    lowering = tuple(fact for fact in facts if fact.key.operation == "lowering")
    assert len(facts) == len(signature) + len(lowering)
    return len(signature), len(lowering)


def test_window_identity_signature_nullability_and_capability_closure_is_locked() -> (
    None
):
    assert tuple(WINDOW_FUNCTION_SQL_NAMES) == (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    )
    signature_count, lowering_count = _window_fact_families()
    assert (signature_count, lowering_count) == (8, 16)
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    assert all(fact.key.domain is CapabilityDomain.WINDOW_FUNCTION for fact in facts)
    signature_subjects = tuple(
        fact.key.subject for fact in facts if fact.key.operation == "signature"
    )
    assert signature_subjects == tuple(WINDOW_FUNCTION_SQL_NAMES)
    lowering_dialects = Counter(
        fact.key.dialect for fact in facts if fact.key.operation == "lowering"
    )
    assert lowering_dialects == {"postgresql": 8, "mysql": 8}
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "`namespace=()`",
        "one exact positive integer literal",
        "one through three bounded arguments",
        "never implies compiler legality or backend lowering",
    ):
        assert phrase in spec, phrase


def test_postgresql_window_lowering_dialect_closure_is_locked() -> None:
    expressions = _read("src/pietto/sql/expressions.py")
    assert "_WINDOW_FUNCTION_NAMES = {" in expressions
    for source_name, sql_name in WINDOW_FUNCTION_SQL_NAMES.items():
        assert f'"{source_name}": "{sql_name}",' in expressions
    assert "OVER (" in expressions
    assert "PARTITION BY " in expressions
    assert "ORDER BY " in expressions
    postgres = _read("src/pietto/sql/postgres.py")
    assert "PIE-B1000" in postgres
    for forbidden in ("QUALIFY", "first_value", "last_value", "nth_value"):
        assert forbidden not in expressions
        assert forbidden not in _read("src/pietto/ir/model.py")
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "optional `PARTITION BY`",
        "mandatory `ORDER BY`",
        "double-quoted identifiers",
        "grouped underlying-expression lowering",
    ):
        assert phrase in spec, phrase


def test_private_mysql_window_lowering_dialect_closure_is_locked() -> None:
    mysql_expressions = _read("src/pietto/sql/mysql_expressions.py")
    assert "_WINDOW_FUNCTION_NAMES = {" in mysql_expressions
    for source_name, sql_name in WINDOW_FUNCTION_SQL_NAMES.items():
        assert f'"{source_name}": "{sql_name}",' in mysql_expressions
    for forbidden in ("QUALIFY", "first_value", "last_value", "nth_value"):
        assert forbidden not in mysql_expressions
    mysql_render = _read("src/pietto/sql/mysql_render.py")
    assert "`" in mysql_render
    assert "64" in mysql_render and "256" in mysql_render
    mysql = _read("src/pietto/sql/mysql.py")
    assert "PIE-B1000" in mysql
    assert "emit_mysql_sql" not in sql_package.__all__
    assert tuple(sql_package.__all__) == (
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    )
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "backtick quoting",
        "No public MySQL support promise",
    ):
        assert phrase in spec, phrase


def test_window_ir_privacy_and_capability_non_authority_closure_is_locked() -> None:
    assert issubclass(WindowFunctionRoleIR, enum.Enum)
    for cls in WINDOW_IR_CLASSES:
        if cls is not WindowFunctionRoleIR:
            params = getattr(cls, "__dataclass_params__")
            assert params.frozen
            assert hasattr(cls, "__slots__")
        assert cls.__name__ not in ir_package.__all__
    assert len(ir_package.__all__) == 44
    assert _sha256(CAPABILITY_WINDOWS_REL) == CAPABILITY_WINDOWS_SHA256
    assert capability_windows.__all__ == ()
    key = capability_windows._WINDOW_CAPABILITY_FACTS[0].key
    facts, complete, reason = capability_windows.window_lookup_inputs(key)
    found = lookup_capability(
        key, facts, domain_complete=complete, unknown_reason=reason
    )
    assert isinstance(found, Found)
    absent_key = CapabilityKey(
        CapabilityDomain.WINDOW_FUNCTION,
        subject="median",
        operation="signature",
        operands=(),
        context="window_signature",
    )
    facts, complete, reason = capability_windows.window_lookup_inputs(absent_key)
    absent = lookup_capability(
        absent_key, facts, domain_complete=complete, unknown_reason=reason
    )
    assert isinstance(absent, Unknown)
    forbidden_names = ("window_lookup_inputs", "capability_windows")
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if (
            relative in {CAPABILITY_WINDOWS_REL, preservation_rel}
            or "generated" in path.parts
        ):
            continue
        source = path.read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden_names), relative
    preservation_source = _read(preservation_rel)
    assert all(name in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source


def test_diagnostic_inventory_and_fail_closed_ordering_closure_is_locked() -> None:
    diagnostics = _read("docs/spec/diagnostics.md")
    assert "PIE-I1000" in diagnostics
    assert "PIE-B1000" in diagnostics
    assert "PIE-I1000" in _read("src/pietto/ir/diagnostics.py")
    window_sources = (
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/semantic/window_partition_analysis.py",
        "src/pietto/semantic/window_order_analysis.py",
        "src/pietto/semantic/window_navigation_analysis.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
    )
    observed = set()
    for relative in window_sources:
        observed.update(re.findall(r"PIE-[A-Z]\d{4}", _read(relative)))
    assert observed == {"PIE-B1000", "PIE-S2103", "PIE-S2104", "PIE-S2312"}
    spec = _read(SPEC_REL)
    for phrase in (
        "renumbers, and rewords no diagnostic code",
        "first-error ordering is unchanged",
        "`PIE-I1000` remains the",
        "`PIE-B1000` remains the",
    ):
        assert phrase in " ".join(spec.split()) or phrase in spec, phrase


def test_phase60_63_69_70_future_owner_boundaries_are_locked() -> None:
    roadmap = _read(ROADMAP_REL)
    for phrase in (
        "Phase 60 owns `ROWS`, `RANGE`, evaluation of the `GROUPS` dialect posture",
        "`QUALIFY` remains Phase 63 work",
        "Extension-specific Lowering And Additional Dialect Backend Foundation",
        "Phase 64 exclusively owns Int/Decimal or other promotion",
    )[:4]:
        assert phrase in roadmap, phrase
    assert "Public Schema / Lineage / Attribution Expansion" in roadmap
    spec = _read(SPEC_REL)
    normalized_spec = " ".join(spec.split())
    for phrase in (
        "remain Phase 60",
        "remains Phase 63",
        "remain Phase 69",
        "remains Phase 70",
        "remain Phase 64",
        "No owner is added, renamed, removed, or transferred by Slice 16.",
    ):
        assert phrase in normalized_spec, phrase
    for phrase in (
        "Same-select window-to-window dependencies, nested window calls",
        "not an anonymous deferral",
    ):
        assert phrase in " ".join(_read(SPEC_REL).split()) or phrase in spec, phrase
