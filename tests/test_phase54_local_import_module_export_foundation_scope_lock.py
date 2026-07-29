from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
SCOPE_REL = (
    "docs/spec/phase54-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md"
)
GOVERNANCE_REL = (
    "docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md"
)
ROADMAP_V1_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
ROADMAP_V2_REL = "docs/spec/pietto-active-roadmap-phase53-70-v2.md"
SLICE2_SPEC_REL = (
    "docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-"
    "immutable-carrier-v1.md"
)
SLICE2_TEST_REL = "tests/test_phase54_schema_v2_explicit_module_carrier.py"
SELF_REL = "tests/test_phase54_local_import_module_export_foundation_scope_lock.py"

PLAN_TITLE = "Phase 54 — Local Import / Module / Export Foundation"
SCOPE_TITLE = (
    "Phase 54 Slice 1 Scope, Authority, Phase-start Expansion Audit, Decisions, "
    "Activation, And Route Lock v1"
)
GOVERNANCE_TITLE = (
    "Pietto Phase-start Expansion, Pull-forward, And Readiness Governance v1"
)
ROADMAP_V2_TITLE = "Pietto Active Roadmap Phase 53–70 v2"
SLICE2_SPEC_TITLE = (
    "Phase 54 Slice 2 Schema-v2 Explicit-module Activation And Immutable "
    "Project / Module Carrier v1"
)

SLICE2_EXPECTED_TEST_NAMES = (
    "test_schema_versions_map_to_exact_project_compilation_modes",
    "test_schema_version_validation_and_unknown_keys_remain_fail_closed",
    "test_schema_versions_select_identical_normalized_ordered_inputs",
    "test_logical_module_carrier_is_frozen_slots_hashable_and_enforces_invariants",
    "test_selection_builds_one_zero_based_logical_module_per_input",
    "test_parse_check_rebuilds_modules_with_parsed_input_references",
    "test_parse_and_read_failures_retain_ordered_logical_modules",
    "test_explicit_mode_returns_before_legacy_flat_catalog_collection",
    "test_legacy_mode_still_enters_flat_catalog_and_reports_duplicate_pie_s2001",
    "test_schema_v2_project_text_cli_fails_closed_without_success_output",
    "test_schema_v2_project_json_keeps_exact_envelope_and_fails_exit",
    "test_schema_v1_project_cli_output_remains_exact",
    "test_project_json_and_public_exports_do_not_expose_module_carriers",
    "test_single_file_check_behavior_remains_exact",
    "test_import_export_grammar_ast_and_module_diagnostic_codes_remain_absent",
    "test_slice2_contract_allowlist_and_retained_later_boundaries_are_exact",
)

EXPECTED_TEST_NAMES = (
    "test_slice1_artifact_titles_heading_order_and_lifecycle_are_exact",
    "test_authority_hierarchy_grounding_and_historical_predecessors_are_exact",
    "test_product_decisions_p1_through_p5_are_exact",
    "test_architecture_decisions_a1_through_a5_are_exact",
    "test_phase_start_governance_vocabulary_ledgers_scoring_and_template_are_exact",
    "test_sixteen_slice_titles_prerequisites_and_parallelism_are_exact",
    "test_phase55_70_named_reexport_release_and_rust_ownership_is_reconciled",
    "test_current_production_readiness_and_retained_later_ledgers_are_exact",
    "test_grammar_generated_ast_parser_and_public_exports_are_byte_locked",
    "test_legacy_config_discovery_selection_loader_and_project_json_are_byte_locked",
    "test_flat_catalog_collect_before_resolve_semantic_and_project_fact_surfaces_are_locked",
    "test_module_surfaces_and_pie_s2701_s2707_are_reserved_but_not_implemented",
    "test_public_json_artifact_cli_sql_dependency_workflow_version_and_release_surfaces_are_locked",
    "test_gate_allowlist_reader_evidence_publication_stop_and_next_state_contracts_are_exact",
)

PHASE54_ROUTE = (
    "Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock",
    "Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier",
    "Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary",
    "Import / Export Contextual Grammar, Generated Parser, And Immutable AST",
    "Module-qualified Nominal Declaration Identity And Per-module Catalogs",
    "Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics",
    "Named Imports, Aliases, Binding Environments, And Collision Rules",
    "Module Graph, Cycles, Diagnostics, And Deterministic Ordering",
    "Cross-module Type Alias, Enum, Shape, And Source Resolution",
    "Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility",
    "Module Attribution, Dependency, Origin, Provenance, And Lineage",
    "Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation",
    "Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness",
    "Private Module Inspection And Canonical Serialization",
    "Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening",
    "Completion Audit, Status Lock, And Phase 55 Handoff",
)
PHASE54_PREREQUISITES = (
    ("Phase 53 completion",),
    (1,),
    (2,),
    (1,),
    (2, 4),
    (5,),
    (6,),
    (7,),
    (8,),
    (3, 8, 9),
    (10,),
    (10,),
    (3, 11, 12),
    (13,),
    tuple(range(8, 15)),
    tuple(range(1, 16)),
)

PHASE_OWNERS = (
    (55, "Semantic Package Asset Schema And Deterministic Local Loading"),
    (56, "Capability Profile Static Schema And Declared Checking"),
    (57, "PostgreSQL Extension Signature Catalog Foundation"),
    (58, "Public Explain / Portability / Package Inspection Artifact v1"),
    (59, "Local Package Graph, Attribution, Provenance, And Lineage"),
    (
        60,
        "Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint",
    ),
    (61, "Project IR And Semantic Composition Foundation"),
    (62, "Relationship, JOIN, Grain, And Fanout-safe Semantics"),
    (63, "Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering"),
    (
        64,
        "Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping",
    ),
    (65, "Advanced Aggregation And Grouping"),
    (66, "Advanced Module And Semantic-package Assets"),
    (
        67,
        "Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary",
    ),
    (
        68,
        "Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel",
    ),
    (
        69,
        "Extension-specific Lowering And Additional Dialect Backend Foundation",
    ),
    (
        70,
        "Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit, Rust Migration Decision, And v0.2 Release Readiness",
    ),
)

CLASSIFICATIONS = (
    "IMPLEMENT_NOW",
    "PRIVATE_READINESS_NOW",
    "CONTRACT_ONLY_NOW",
    "DEFER_BY_NECESSITY",
    "OUT_OF_SCOPE",
)
FREEZE_LEDGERS = ("CURRENT_PRODUCTION", "CURRENT_READINESS", "RETAINED_LATER")

ADDED_PATHS = {
    "docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md",
    "src/pietto/_project/module_carrier.py",
    "tests/test_phase54_schema_v2_explicit_module_carrier.py",
}
NON_READER_MODIFIED_PATHS = {
    "docs/plan/phase-54-local-import-module-export-foundation.md",
    "src/pietto/_project/config.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/source_selection.py",
    "src/pietto/_project/check.py",
    "tests/test_phase44_project_config_loader.py",
}
MECHANICAL_READER_PATHS = {
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_completion_audit_and_status_lock.py",
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
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
}
MODIFIED_PATHS = {*NON_READER_MODIFIED_PATHS, *MECHANICAL_READER_PATHS}
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS
FORMATTER_PATHS = {relative for relative in ALLOWLIST_PATHS if relative.endswith(".py")}

PROTECTED_SHA256 = {
    "grammar/Pietto.g4": "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e",
    "src/pietto/ast_nodes.py": "b0c41070fca75c89534eba75cf2086f41721de740da9a3573d67411d366204f5",
    "src/pietto/ast_builder.py": "201c74d6a27e57dfc7cd0f9693b388ebe7853b783173a3c4f7191a5f8026e70b",
    "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
    "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
    "src/pietto/_project/module_carrier.py": "5c6e97c12cced227fa6dc4d9694d19088572d74197d452b83843c206014a7e8e",
    "src/pietto/_project/config.py": "de099a8d1bfbbb6b80ef2c9d1fa323b53d790d433a9263ce6b539fac27e213a7",
    "src/pietto/_project/model.py": "9f47b27526a5959771b23c6fe150f8c8411bf31908ec808e55657cf963c23280",
    "src/pietto/_project/source_selection.py": "92e08a360139cc021de2fcb8b13df5e70412c8d0fb7b4a9cb829cec229ca6508",
    "src/pietto/_project/check.py": "79d2372e43078b9b68b0fd65f552223a6c17a5eb382986020c4f0c1c1f5d6332",
    "src/pietto/_project/json_v2.py": "74251e684a22de4dcdc7e1822a6843ca89cbdfa7e136a046676d848b57953bd5",
    SLICE2_TEST_REL: "02c211a0a0010fbc6fddb10f8fdb1ea4daba736862551721e8d167a42c30135b",
    ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
}


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$", _read(relative), flags=re.MULTILINE
        )
    )


def _section(relative: str, heading: str) -> str:
    source = _read(relative)
    marker = f"## {heading}\n"
    start = source.index(marker) + len(marker)
    end = source.find("\n## ", start)
    return source[start:] if end < 0 else source[start:end]


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _readable_paths() -> tuple[str, ...]:
    paths = (
        *_git_output(["ls-files"]).splitlines(),
        *_git_output(["ls-files", "--others", "--exclude-standard"]).splitlines(),
    )
    return tuple(path for path in paths if path and (REPO_ROOT / path).is_file())


def _top_level_test_functions(relative: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    return tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
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


def _production_text() -> str:
    paths = (
        REPO_ROOT / "grammar/Pietto.g4",
        *(REPO_ROOT / "src/pietto").rglob("*.py"),
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_slice1_artifact_titles_heading_order_and_lifecycle_are_exact() -> None:
    assert _headings(PLAN_REL, 1) == (PLAN_TITLE,)
    assert _headings(SCOPE_REL, 1) == (SCOPE_TITLE,)
    assert _headings(GOVERNANCE_REL, 1) == (GOVERNANCE_TITLE,)
    assert _headings(ROADMAP_V2_REL, 1) == (ROADMAP_V2_TITLE,)
    assert _headings(SLICE2_SPEC_REL, 1) == (SLICE2_SPEC_TITLE,)
    for relative in (PLAN_REL, SCOPE_REL, GOVERNANCE_REL, ROADMAP_V2_REL):
        assert _headings(relative, 2)
    plan_h2 = _headings(PLAN_REL, 2)
    assert plan_h2[:5] == (
        "Status And Slice 2 Lifecycle",
        "Trusted Phase 53 Baseline And Controlling Evidence",
        "Phase Identity, Minimum Production Boundary, And Activation",
        "Current Production, Readiness, And Retained-later Freeze",
        "Phase-start Expansion, Pull-forward, And Readiness Audit",
    )
    assert plan_h2[-15:] == tuple(
        f"Slice {index} — {title}"
        for index, title in enumerate(PHASE54_ROUTE[1:], start=2)
    )
    lifecycle = _section(PLAN_REL, "Status And Slice 2 Lifecycle")
    for phrase in (
        "Phase 53 and Slices 1-16 are `COMPLETED`",
        "Phase 54 is `ACTIVE`",
        "Slice 1 is\n`COMPLETED`",
        "Slice 2 becomes `COMPLETED`",
        "Slices 3-16 then remain `UNSTARTED`",
        "PHASE54_SLICE3_GATE0_GATE1",
    ):
        assert phrase in lifecycle
    tests = _top_level_test_functions(SELF_REL)
    assert tests == EXPECTED_TEST_NAMES
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    test_nodes = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(test_nodes) == 14
    assert all(not node.decorator_list for node in test_nodes)
    slice2_tests = _top_level_test_functions(SLICE2_TEST_REL)
    assert slice2_tests == SLICE2_EXPECTED_TEST_NAMES
    slice2_tree = ast.parse(_read(SLICE2_TEST_REL), filename=SLICE2_TEST_REL)
    slice2_nodes = tuple(
        node
        for node in slice2_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(slice2_nodes) == 16
    assert all(not node.decorator_list for node in slice2_nodes)


def test_authority_hierarchy_grounding_and_historical_predecessors_are_exact() -> None:
    assert _sha256(ROADMAP_V1_REL) == (
        "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3"
    )
    assert _sha256("docs/plan/phase-50-semantic-readiness-consolidation.md") == (
        "4a3cc652461741cd0d4df71112c4d69251ecefc7a222aad94727d2e67d6ae34c"
    )
    assert _sha256("docs/spec/phase50-import-module-export-readiness-v1.md") == (
        "8c3656805db451946d60e341b8ac0ca9181997378d07576133c9c4aeef3e3f77"
    )
    assert _sha256("tests/test_phase50_import_module_export_readiness.py") == (
        "82cbc7398b6677ec2d11c80d73707bea6b7806b3e513c80e407bd4afb6dc5f9a"
    )
    scope = _read(SCOPE_REL)
    roadmap = _read(ROADMAP_V2_REL)
    assert "Historical readiness is evidence" in scope
    assert "governance-schema successor" in roadmap
    assert "No predecessor byte is appended, edited, deleted" in roadmap
    assert "Live source and completed-phase evidence" in roadmap
    assert "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3" in roadmap
    assert "current-state-" + "and-roadmap-audit.txt" not in _read(SELF_REL)


def test_product_decisions_p1_through_p5_are_exact() -> None:
    assert _headings(SCOPE_REL, 3)[:5] == (
        "P1 — Activation And Module Identity",
        "P2 — Import / Export Syntax",
        "P3 — Visibility, Eligibility, And Explicit Named Re-export",
        "P4 — Collision, Cycles, Ordering, And Diagnostics",
        "P5 — Root, Symlink, Path, TOCTOU, Dedup, And Digest",
    )
    scope = _read(SCOPE_REL)
    for phrase in (
        "Schema version 2 explicitly activates project-wide module mode",
        "one module identified by its exact normalized project-root-relative",
        'import "models/customer.pietto":',
        "shape Customer",
        "query orders as imported_orders",
        "exported_name as local_name",
        "explicit named re-export",
        "every hop is explicit",
        "No local/import/alias/export",
        "one canonical root",
        "opened descriptor matches selection",
        "digests exact opened bytes",
        "immutable selected-input index",
    ):
        assert phrase in scope
    for kind in ("`type`", "`enum`", "`shape`", "`source`", "`table`", "`query`"):
        assert kind in scope
    for forbidden in (
        "dotted module reference",
        "wildcard",
        "side-effect import",
        "brace form",
        "package target",
        "`export from`",
    ):
        assert forbidden in scope


def test_architecture_decisions_a1_through_a5_are_exact() -> None:
    assert _headings(SCOPE_REL, 3)[5:10] == (
        "A1 — Layered Immutable Identities",
        "A2 — Selected-input Index And Trusted Local Loader",
        "A3 — Pure Resolver Procedure And Diagnostic Adapter",
        "A4 — Identity-safe Project-model Facts",
        "A5 — Private Inspection, Canonical Serialization, And Rust-ready Seam",
    )
    scope = _read(SCOPE_REL)
    for phrase in (
        "(module,\nnamespace, declaration_kind, declared_name)",
        "AST object identity",
        "immutable,\nordered exact module index",
        "global/callback registry",
        "filesystem walker",
        "package loader",
        "Parse all modules",
        "structured issues",
        "diagnostics\nseparately",
        "distinct legacy-flat resolver",
        "`_project/module_*.py`",
        "aggregate,",
        "capability facts",
        "canonical private serialization",
        "no Python-object identity",
        "frozen differential vectors",
    ):
        assert phrase in scope


def test_phase_start_governance_vocabulary_ledgers_scoring_and_template_are_exact() -> (
    None
):
    governance = _read(GOVERNANCE_REL)
    scope_ledger = _section(SCOPE_REL, "No-unnecessary-deferral Ledger")
    for value in CLASSIFICATIONS + FREEZE_LEDGERS:
        assert value in governance
    for reason in (
        "remote I/O or registry state",
        "dependency solving, ranges, or lockfile semantics",
        "public artifact or serializer-schema publication",
        "runtime plugins, executable hooks, or ambient callbacks",
        "release, signing, attestation, or supply-chain authority",
        "additional dialect production ownership",
        "unresolved semantics",
        "genuine product boundary",
    ):
        assert reason in governance
    assert "belongs to Phase N” is never sufficient" in governance
    weights = tuple(
        int(value)
        for value in re.findall(
            r"^\| (?:semantic|foreseeable|preservation|slice|dependency|implementation|reader|CI|public).*?\| (\d) \|$",
            _section(GOVERNANCE_REL, "Route Scoring Weights And Hard Gates"),
            flags=re.MULTILINE,
        )
    )
    assert weights == (2, 2, 2, 2, 1, 1, 1, 1, 2)
    assert sum(weight * 5 for weight in weights) == 70
    plan_scores = dict(
        (int(count), int(score))
        for count, score in re.findall(
            r"^\| (1[0-6]) \| (\d+) \|", _read(PLAN_REL), flags=re.MULTILINE
        )
    )
    assert plan_scores == {10: 49, 11: 53, 12: 54, 13: 57, 14: 60, 15: 62, 16: 63}
    ledger_rows = re.findall(
        r"^\| ((?:5[5-9]|6\d|70)[A-E]|RLS) / .*?\| (IMPLEMENT_NOW|PRIVATE_READINESS_NOW|CONTRACT_ONLY_NOW|DEFER_BY_NECESSITY|OUT_OF_SCOPE) \|.*$",
        scope_ledger,
        flags=re.MULTILINE,
    )
    assert len(ledger_rows) == 54
    assert len({row_id for row_id, _ in ledger_rows}) == 54
    assert Counter(value for _, value in ledger_rows) == Counter(
        {
            "IMPLEMENT_NOW": 5,
            "PRIVATE_READINESS_NOW": 7,
            "CONTRACT_ONLY_NOW": 4,
            "DEFER_BY_NECESSITY": 34,
            "OUT_OF_SCOPE": 4,
        }
    )
    defer_lines = tuple(
        line for line in scope_ledger.splitlines() if "| DEFER_BY_NECESSITY |" in line
    )
    assert len(defer_lines) == 34
    assert all("DEFERRED BY NECESSITY —" in line for line in defer_lines)
    for field in (
        "PHASE:",
        "TRUSTED_BASELINE:",
        "CURRENT_PRODUCTION:",
        "CURRENT_READINESS:",
        "RETAINED_LATER:",
        "NO_UNNECESSARY_DEFERRAL_LEDGER:",
        "ROUTE_COUNTS_SCREENED: 8,9,10,11,12,13,14,15,16",
        "RECOMMENDED_EXACT_ROUTE:",
        "MAXIMUM_SAFE_PULL_FORWARD:",
        "STOP_CONDITIONS:",
        "NEXT_GATE:",
    ):
        assert field in governance


def test_sixteen_slice_titles_prerequisites_and_parallelism_are_exact() -> None:
    plan_h2 = _headings(PLAN_REL, 2)
    slice_headings = tuple(
        heading for heading in plan_h2 if re.match(r"^Slice \d+ —", heading)
    )
    assert slice_headings == tuple(
        f"Slice {index} — {title}"
        for index, title in enumerate(PHASE54_ROUTE[1:], start=2)
    )
    scope_route = _section(SCOPE_REL, "Exact Sixteen-slice Route And Prerequisites")
    for index, title in enumerate(PHASE54_ROUTE, start=1):
        assert f"{index}. {title}" in scope_route
    assert PHASE54_PREREQUISITES == (
        ("Phase 53 completion",),
        (1,),
        (2,),
        (1,),
        (2, 4),
        (5,),
        (6,),
        (7,),
        (8,),
        (3, 8, 9),
        (10,),
        (10,),
        (3, 11, 12),
        (13,),
        (8, 9, 10, 11, 12, 13, 14),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    )
    dependency = _section(SCOPE_REL, "Dependency Graph And Parallelism")
    assert "Slice 4 may proceed alongside Slices\n2-3" in dependency
    assert "Slices 11 and 12 may proceed in parallel" in dependency
    assert "Publication and Git operations remain\nsequential" in dependency


def test_phase55_70_named_reexport_release_and_rust_ownership_is_reconciled() -> None:
    roadmap = _read(ROADMAP_V2_REL)
    for phase, title in PHASE_OWNERS:
        assert f"| {phase} | {title} |" in roadmap
    owner = _section(
        ROADMAP_V2_REL, "No-unnecessary-deferral And Retained-owner Reconciliation"
    )
    for phrase in (
        "Basic explicit named re-export is `IMPLEMENT_NOW`",
        "wildcard\nimport/export",
        "source-qualified forms",
        "`export from`",
        "callable/constraint/derive/relationship module assets",
        "package-aware advanced\nfacades",
    ):
        assert phrase in owner
    assert "Phase 68 remains the preferred first production Rust" in roadmap
    release = _section(ROADMAP_V2_REL, "Release Train")
    assert "No phase gate implicitly publishes" in release
    assert "Only Release Gate 3" in release
    assert "This roadmap creates none" in release


def test_current_production_readiness_and_retained_later_ledgers_are_exact() -> None:
    scope = _read(SCOPE_REL)
    production = _section(SCOPE_REL, "Current Production Ledger")
    readiness = _section(SCOPE_REL, "Current Readiness Ledger")
    retained = _section(SCOPE_REL, "Retained Later Ledger")
    assert re.findall(r"\| CP-(\d\d) \|", production) == [
        f"{n:02d}" for n in range(1, 9)
    ]
    assert re.findall(r"\| CR-(\d\d) \|", readiness) == [
        f"{n:02d}" for n in range(1, 7)
    ]
    assert re.findall(r"\| RL-(\d\d) \|", retained) == [
        f"{n:02d}" for n in range(1, 17)
    ]
    assert "Historical readiness is evidence" in scope
    maximum = _section(SCOPE_REL, "Maximum Safe Pull-forward Boundary")
    for value in CLASSIFICATIONS[:3]:
        assert value in maximum
    for prohibited in (
        "final package schemas",
        "public\nartifacts",
        "remote operations",
        "solver/lockfile behavior",
        "production Rust",
        "additional dialects",
        "release/supply-chain behavior",
    ):
        assert prohibited in maximum


def test_grammar_generated_ast_parser_and_public_exports_are_byte_locked() -> None:
    for relative in (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/__init__.py",
    ):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    assert len(generated) == 8
    assert _digest(generated) == (
        "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4"
    )
    grammar = _read("grammar/Pietto.g4")
    ast_nodes = _read("src/pietto/ast_nodes.py")
    parser_api = _read("src/pietto/parser_api.py")
    assert not re.search(
        r"(?m)^\s*(?:module|import|export)(?:Statement|Block|Decl)?\s*:", grammar
    )
    assert not re.search(r"class (?:Module|Import|Export)\w*\(", ast_nodes)
    assert "parse_module" not in parser_api


def test_legacy_config_discovery_selection_loader_and_project_json_are_byte_locked() -> (
    None
):
    for relative in (
        "src/pietto/_project/module_carrier.py",
        "src/pietto/_project/config.py",
        "src/pietto/_project/model.py",
        "src/pietto/_project/source_selection.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/json_v2.py",
        SLICE2_TEST_REL,
    ):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    config = _read("src/pietto/_project/config.py")
    selection = _read("src/pietto/_project/source_selection.py")
    check = _read("src/pietto/_project/check.py")
    model = _read("src/pietto/_project/model.py")
    carrier = _read("src/pietto/_project/module_carrier.py")
    assert "_SCHEMA_VERSION = 1" not in config
    assert "_COMPILATION_MODE_BY_SCHEMA_VERSION" in config
    assert "1: ProjectCompilationMode.LEGACY_FLAT" in config
    assert "2: ProjectCompilationMode.EXPLICIT_MODULES" in config
    assert '_TOP_LEVEL_KEYS = frozenset({"schema_version", "sources"})' in config
    assert 'LEGACY_FLAT = "legacy_flat"' in carrier
    assert 'EXPLICIT_MODULES = "explicit_modules"' in carrier
    assert "class ProjectLogicalModule" in carrier
    assert "_build_project_logical_modules" in selection
    assert "resolved_path.relative_to(root)" in selection
    assert "identities: dict[tuple[int, int], str]" in selection
    assert "ProjectParsedInput" in check and "script=parse_result.ast" in check
    assert "class ProjectInput" in model and "class ProjectParsedInput" in model
    assert "compilation_mode: ProjectCompilationMode" in model
    assert "modules: tuple[ProjectLogicalModule, ...]" in model
    assert (
        "parse_result.compilation_mode is not ProjectCompilationMode.LEGACY_FLAT"
        in model
    )
    assert "os.fstat" not in check
    assert "sha256" not in check.lower()
    scope_readiness = _section(SCOPE_REL, "Current Readiness Ledger")
    assert "not a pinned descriptor loader" in scope_readiness
    assert (
        "not bound to later open" in scope_readiness
        or "not a pinned descriptor" in scope_readiness
    )


def test_flat_catalog_collect_before_resolve_semantic_and_project_fact_surfaces_are_locked() -> (
    None
):
    compiler = _compiler_paths()
    semantic = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    project = tuple((REPO_ROOT / "src/pietto/_project").glob("*.py"))
    assert _digest(compiler) == (
        "6b98059fa09b09fb2c724003f1276bd85077382b597711147d5a9bd5d820f550"
    )
    assert _digest(semantic) == (
        "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
    )
    assert _digest(project) == (
        "0b1d9571472263c00f22d69e01754a136455f3c0ac112b2b370cbe2be563a629"
    )
    assert len(project) == 19
    model = _read("src/pietto/_project/model.py")
    for namespace in (
        'TYPE = "type"',
        'RELATION = "relation"',
        'CALLABLE = "callable"',
    ):
        assert namespace in model
    for kind in (
        'TYPE_ALIAS = "type"',
        'ENUM = "enum"',
        'SHAPE = "shape"',
        'SOURCE = "source"',
        'TABLE = "table"',
        'QUERY = "query"',
        'CONSTRAINT = "constraint"',
        'DERIVE = "derive"',
    ):
        assert kind in model
    current = _section(SCOPE_REL, "Current Production Ledger")
    assert "flat project-wide catalog before relation resolution" in current
    assert "row-schema, field-origin, aggregate, grouped, window" in current
    assert "may not flatten" in _section(
        SCOPE_REL, "Legacy-flat And Schema-v2 Activation"
    )


def test_module_surfaces_and_pie_s2701_s2707_are_reserved_but_not_implemented() -> None:
    production = _production_text()
    assert not re.search(r"PIE-S270[1-7]", production)
    carrier = _read("src/pietto/_project/module_carrier.py")
    assert "class ProjectCompilationMode(StrEnum)" in carrier
    assert "class ProjectLogicalModule" in carrier
    for forbidden in (
        "ModuleGraph",
        "ImportDef",
        "ExportDef",
        "declaration_catalog",
        "content_digest",
        "opened_identity",
    ):
        assert forbidden not in carrier
    reservation = _section(
        SCOPE_REL,
        "Collision Cycle Ordering And PIE-S2701 Through PIE-S2707 Reservation",
    )
    descriptions = (
        "invalid, unselected, or unresolved local module target",
        "duplicate or conflicting module identity",
        "module import cycle",
        "duplicate, unknown, ineligible, or invalid export request",
        "unknown, private, or non-exported imported declaration",
        "local/import/alias/export binding collision",
        "unresolved explicit-module reference or unsupported advanced form",
    )
    for index, description in enumerate(descriptions, start=1):
        assert f"`PIE-S270{index}`" in reservation
        assert description in reservation
    assert "does not add these codes" in reservation
    for code in ("PIE-S2001", "PIE-S2002", "PIE-S2301", "PIE-S2302"):
        assert code in reservation


def test_public_json_artifact_cli_sql_dependency_workflow_version_and_release_surfaces_are_locked() -> (
    None
):
    for relative in (".github/workflows/ci.yml", "pyproject.toml", "uv.lock"):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        pyproject = tomllib.load(stream)
    assert pyproject["project"]["version"] == "0.1.0"
    assert not (REPO_ROOT / "Cargo.toml").exists()
    assert not any(path.name == "Cargo.toml" for path in REPO_ROOT.rglob("Cargo.toml"))
    paths = _readable_paths()
    assert sum(path.startswith(".github/workflows/") for path in paths) == 1
    assert sum(path.startswith("src/pietto/generated/") for path in paths) == 8
    goldens = tuple((REPO_ROOT / "tests/fixtures/golden").glob("*"))
    assert sum(path.suffix == ".sql" for path in goldens) == 32
    assert sum(path.suffix == ".json" for path in goldens) == 5
    boundary = _section(
        SCOPE_REL,
        "No Grammar Source Runtime Public Schema Dependency Version Or Release Change",
    )
    for phrase in (
        "CLI",
        "JSON/artifact schema",
        "public exports",
        "workflow",
        "dependency",
        "lockfile",
        "package metadata/version",
        "Rust",
        "Release",
        "signing",
        "attestation",
    ):
        assert phrase in boundary


def test_gate_allowlist_reader_evidence_publication_stop_and_next_state_contracts_are_exact() -> (
    None
):
    assert (len(ADDED_PATHS), len(MODIFIED_PATHS), 0) == (3, 54, 0)
    assert len(NON_READER_MODIFIED_PATHS) == 6
    assert len(MECHANICAL_READER_PATHS) == 48
    assert len(FORMATTER_PATHS) == 55
    assert len(ALLOWLIST_PATHS) == 57
    readable = _readable_paths()
    assert len(readable) == 889
    assert sum(path.endswith(".py") for path in readable) == 545
    assert sum(path.endswith(".md") for path in readable) == 248
    test_modules = tuple(
        path
        for path in readable
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    assert len(test_modules) == 451
    assert sum(len(_top_level_test_functions(path)) for path in test_modules) == 4882
    dirty = set(_git_output(["diff", "--name-only"]).splitlines()) | set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    dirty.discard("")
    if dirty:
        assert dirty == ALLOWLIST_PATHS
        assert _git_output(["diff", "--cached", "--name-only"]) == ""
    scope = _read(SCOPE_REL)
    for path in (
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate2-evidence-and-diff.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate3-publication-evidence.txt",
    ):
        assert path in scope
    for phrase in (
        "O_CREAT | O_EXCL | O_NOFOLLOW",
        "mode `0644`",
        "A5_M32_D0",
        "14 primary tests",
        "10,814",
        "generated inventory 8",
        "goldens 37",
        "package smoke PASS",
        "phase54/slice1-scope-authority-expansion-route-lock",
        "Add Phase 54 scope authority and expansion route lock",
        "one ready PR",
        "exact tree equality",
        "ff-only",
        "phase54=ACTIVE",
        "slice1=COMPLETED",
        "next=PHASE54_SLICE2_GATE0_GATE1",
    ):
        assert phrase in scope
    assert (
        "PHASE54_SLICE1_GATE0_GATE1_CORRECTION_PASS "
        "base=af92f30c22e5d3df5219554a0663855a5b9f51a6 "
        "original_allowlist=A5_M21_D0 corrected_allowlist=A5_M32_D0 "
        "readers=31 candidates=classified tests=14 clean=10814 focused=14 "
        "formatter_paths=32 "
        "report=/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/"
        "gate0-gate1-plan-correction-1.txt next=GATE2_RESUME_OFFLINE" in scope
    )
    slice2 = _read(SLICE2_SPEC_REL)
    slice2_flat = " ".join(slice2.split())
    for phrase in (
        "Authority is `A3_M54_D0`.",
        "contains exactly 16 top-level, non-parametrized tests",
        "ProjectLogicalModule",
        "permits only `LEGACY_FLAT` to reach `_build_project_semantic_catalog`",
        "Projected clean collection is 10,830",
        "executing mechanical reader closure contains exactly 48 modules",
        "write-mode formatter invocation contains exactly 55 literal Python paths",
        "Generated inventory remains 8",
        "Goldens remain 37: 32 SQL and 5 JSON",
        "Package smoke must pass and installed CLI remains 0.1.0",
        "`O_CREAT | O_EXCL | O_NOFOLLOW`, mode 0644",
        "phase54/slice2-schema-v2-module-carrier",
        "Add Phase 54 schema v2 module activation carrier",
        "one ready PR",
        "exact-tree squash",
        "fetch/ff-only reconciliation",
        "`next=PHASE54_SLICE3_GATE0_GATE1`",
        "Do not begin Slice 3",
    ):
        assert phrase in slice2_flat
    plan = _read(PLAN_REL)
    for forbidden in ("dirty overlay", "skip", "xfail", "deselection", "masking"):
        assert forbidden in plan
    stop = _section(SCOPE_REL, "Stop Conditions")
    assert (
        "Mechanical hash, manifest, inventory, heading, phrase, formatter, topology"
        in stop
    )
    assert "without a routine user pause" in stop
    slice2_stop = _section(SLICE2_SPEC_REL, "Stop And Next State")
    assert "mechanical reader/hash/inventory/topology repair" in slice2_stop
    assert "not a product decision" in slice2_stop
