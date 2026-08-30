from __future__ import annotations

import ast
from dataclasses import fields
from importlib.metadata import version
from pathlib import Path
import subprocess

import pietto
import pietto._project as project_package
import pietto._project_explain as project_explain_package
from pietto._project.window_semantics import (
    WindowResultProjectFact,
    WindowSemanticProvenance,
)
from pietto._project_explain.model import (
    ProjectExplainEnvelope,
    ProjectExplainFormat,
)
from pietto.sql.window_strategy import NamedWindowLoweringStrategy


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-completion-readiness-audit-phase61-handoff-v1.md"
ROUTE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md"
)
SOURCE = (
    REPO_ROOT
    / "tests/test_phase60_slice13_completion_readiness_audit_phase61_handoff.py"
)
PROBE = REPO_ROOT / "tests/_pietto_phase60_window_differential_probe.py"
PHASE60_BASE = "852568c33ed4a6ad7d311d776f68f5971ab90dd5"

_SLICE_AUTHORITIES = (
    (
        "Scope / Semantic Laws / Route Lock",
        "phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md",
        "test_phase60_slice1_advanced_windows_scope_semantic_laws_route_lock.py",
        (),
    ),
    (
        "Authored-To-Resolved Window And Frame Model",
        "phase60-slice2-authored-resolved-window-frame-model-v1.md",
        "test_phase60_slice2_authored_resolved_window_frame_model.py",
        ("src/pietto/semantic/window_semantics.py",),
    ),
    (
        "Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules",
        "phase60-slice3-frame-validation-function-policy-v1.md",
        "test_phase60_slice3_frame_validation_function_policy.py",
        (
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/semantic/window_navigation_analysis.py",
            "src/pietto/semantic/window_semantics.py",
        ),
    ),
    (
        "ROWS Semantics And Lowering",
        "phase60-slice4-rows-semantics-lowering-v1.md",
        "test_phase60_slice4_rows_semantics_lowering.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/semantic/window_semantics.py",
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/ir/lowering.py",
        ),
    ),
    (
        "RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering",
        "phase60-slice5-range-semantics-lowering-v1.md",
        "test_phase60_slice5_range_semantics_lowering.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/semantic/window_semantics.py",
        ),
    ),
    (
        "GROUPS And Peer-Group Semantics And Lowering",
        "phase60-slice6-groups-peer-semantics-v1.md",
        "test_phase60_slice6_groups_peer_semantics.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/semantic/window_semantics.py",
        ),
    ),
    (
        "EXCLUDE Semantics Across All Units",
        "phase60-slice7-exclude-semantics-v1.md",
        "test_phase60_slice7_exclude_semantics.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/semantic/window_semantics.py",
        ),
    ),
    (
        "Query-Local Named-Window Scope And DAG Inheritance",
        "phase60-slice8-query-local-named-windows-v1.md",
        "test_phase60_slice8_query_local_named_windows.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/semantic/expressions.py",
            "src/pietto/semantic/window_semantics.py",
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/ir/lowering.py",
            "src/pietto/_project/window_semantics.py",
            "src/pietto/_project/module_semantic_fact_preservation.py",
        ),
    ),
    (
        "Value/Navigation Modifiers",
        "phase60-slice9-value-navigation-modifiers-v1.md",
        "test_phase60_slice9_value_navigation_modifiers.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_builder.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/semantic/analyzer.py",
            "src/pietto/semantic/capability_windows.py",
            "src/pietto/semantic/expressions.py",
            "src/pietto/semantic/model.py",
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/semantic/window_navigation_analysis.py",
            "src/pietto/semantic/window_semantics.py",
            "src/pietto/ir/model.py",
            "src/pietto/ir/lowering.py",
            "src/pietto/sql/expressions.py",
            "src/pietto/sql/mysql_expressions.py",
            "src/pietto/_project/window_semantics.py",
            "src/pietto/_project/module_semantic_fact_preservation.py",
        ),
    ),
    (
        "Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness",
        "phase60-slice10-capability-lineage-inspection-integration-v1.md",
        "test_phase60_slice10_capability_lineage_inspection_integration.py",
        (
            "src/pietto/semantic/analyzer.py",
            "src/pietto/semantic/capability_windows.py",
            "src/pietto/semantic/expressions.py",
            "src/pietto/semantic/model.py",
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/semantic/window_semantics.py",
            "src/pietto/ir/model.py",
            "src/pietto/ir/lowering.py",
            "src/pietto/ir/builder.py",
            "src/pietto/sql/window_strategy.py",
            "src/pietto/sql/expressions.py",
            "src/pietto/sql/mysql_expressions.py",
            "src/pietto/sql/relations.py",
            "src/pietto/sql/mysql_relations.py",
            "src/pietto/_project/window_semantics.py",
            "src/pietto/_project/window_persistence.py",
            "src/pietto/_project/module_semantic_fact_preservation.py",
            "src/pietto/_project/package_graph.py",
            "src/pietto/_project/package_graph_inspection.py",
        ),
    ),
    (
        "Real Authored Advanced-Window E2E",
        "phase60-slice11-real-authored-advanced-window-e2e-v1.md",
        "test_phase60_slice11_real_authored_advanced_window_e2e.py",
        (),
    ),
    (
        "Differential Compatibility",
        "phase60-slice12-differential-compatibility-v1.md",
        "test_phase60_slice12_differential_compatibility.py",
        (),
    ),
    (
        "Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff",
        "phase60-completion-readiness-audit-phase61-handoff-v1.md",
        "test_phase60_slice13_completion_readiness_audit_phase61_handoff.py",
        (),
    ),
)

_PUBLISHED_SLICES = (
    (
        1,
        "f32171af018457797bc1561b9d1c12b8561b4472",
        "006d4b0db0db3249c984ee7602f85c0eb80ee11d",
        "33165955698",
        "Add Phase 60 advanced window route lock",
    ),
    (
        2,
        "902bc1942ac737e3cae962c00588fa5e82dce8c4",
        "df10e378f9a090b289ae34afdaee7680a68e6eaa",
        "33168427225",
        "Add Phase 60 authored window frame model",
    ),
    (
        3,
        "1cbc6028f32e973e002b80556638df7aafb26850",
        "3b3c518cc1a3a9c59868ede19aaba3bb2cd9dda9",
        "33191566950",
        "Add Phase 60 frame validation and policy",
    ),
    (
        4,
        "494acb103657badb76baf4d05aa7d7b73260c29d",
        "b5074c7f01c4f21e55d6dd98bbc871d879835217",
        "33197322161",
        "Add Phase 60 ROWS semantics infrastructure",
    ),
    (
        5,
        "41e1771f45a2a883510b6a519fec3693b16819cf",
        "dd149ffcb72ec59fb808bceca19d2fb4184761ca",
        "33199855664",
        "Add Phase 60 RANGE semantics infrastructure",
    ),
    (
        6,
        "e3230673061312261955b3eafa239d04923488e1",
        "331b16d1eb13554930a58e66e679921325ef77d2",
        "33203129112",
        "Add Phase 60 GROUPS and peer semantics",
    ),
    (
        7,
        "e7da0130b9eb0e33c0553aeb620dcb0ea36fce08",
        "07074ddf790d7cb1a0b887443f17d48a8fde3572",
        "33229925815",
        "Add Phase 60 EXCLUDE semantics",
    ),
    (
        8,
        "8a488d857a6b299e64f45bf70cc2c59372ff47ed",
        "1bfbce2caed7d6cb7070871c2516b0b44256ff24",
        "33268604829",
        "Add Phase 60 query-local named windows",
    ),
    (
        9,
        "565652eee263f376b364509326b00192b68e8e25",
        "fa6c4c2f687a8704af0405e57d65ef0c006163da",
        "33284480050",
        "Add Phase 60 value navigation modifiers",
    ),
    (
        10,
        "9d42564a73228c2ee3137372d84c220d6650778d",
        "ac793531cffbca7ac937d49815a96be8742de307",
        "33288658967",
        "Integrate Phase 60 window capabilities and lineage",
    ),
    (
        11,
        "a8c6accfc6c41194b346434abe313d59f41b9520",
        "9083ca99661fba6478f0200aee2e631cf033948f",
        "33290389421",
        "Add Phase 60 real authored advanced-window E2E",
    ),
    (
        12,
        "0b87e603c783b203a70155238c6327e182c7e440",
        "f6fcabf76ad355aea4b6f03107b0bfe64953c944",
        "33293473545",
        "Add Phase 60 differential compatibility assurance",
    ),
)

_EXIT_TEST_FUNCTIONS = {
    "test_phase60_slice2_authored_resolved_window_frame_model.py": {
        "test_closed_type_and_carrier_inventories_are_exact_private_and_immutable",
        "test_omitted_and_explicit_default_equivalent_frames_keep_distinct_authorship",
    },
    "test_phase60_slice3_frame_validation_function_policy.py": {
        "test_all_bound_category_pairs_have_exact_structural_outcomes",
        "test_legal_aggregate_before_window_input_is_not_blanket_rejected",
    },
    "test_phase60_slice4_rows_semantics_lowering.py": {
        "test_rows_clipping_is_interval_intersection_not_endpoint_membership_clamping",
    },
    "test_phase60_slice5_range_semantics_lowering.py": {
        "test_range_offset_orientation_is_explicit_and_direction_aware",
        "test_phase64_requirement_seam_retains_exact_expressions_without_evaluation",
    },
    "test_phase60_slice6_groups_peer_semantics.py": {
        "test_peer_groups_require_complete_multi_key_comparison_evidence",
        "test_unresolved_phase64_comparison_produces_no_partial_groups",
    },
    "test_phase60_slice7_exclude_semantics.py": {
        "test_exact_four_mode_truth_table_is_removal_only",
        "test_group_and_ties_propagate_unresolved_peer_authority_fail_closed",
    },
    "test_phase60_slice8_query_local_named_windows.py": {
        "test_collection_first_namespace_resolves_forward_backward_aliases_and_roots",
        "test_invariant_matrix_declares_every_live_layer_slot_and_origin",
    },
    "test_phase60_slice9_value_navigation_modifiers.py": {
        "test_frame_value_candidates_start_after_exclusion_and_ignore_only_null_values",
        "test_backend_modifier_and_frame_limits_fail_closed",
    },
    "test_phase60_slice10_capability_lineage_inspection_integration.py": {
        "test_target_failure_keeps_project_lineage_and_semantic_provenance",
        "test_one_unsupported_named_use_blocks_the_whole_relation_strategy",
    },
    "test_phase60_slice11_real_authored_advanced_window_e2e.py": {
        "test_e2e_authority_starts_from_authored_files_and_production_entry_points",
        "test_real_project_lineage_and_private_inspection_retain_authorship",
    },
    "test_phase60_slice12_differential_compatibility.py": {
        "test_four_hash_seeds_preserve_exact_observation_bytes",
        "test_backend_negative_cases_are_identical_fail_closed_terminals",
    },
}

_CHECKPOINT_PATHS = {
    "51": (
        "src/pietto/_project/aggregate_grouped_clause_facts.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    ),
    "52": (
        "src/pietto/semantic/capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    ),
    "53": (
        "src/pietto/_window_identity.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    ),
    "54": (
        "src/pietto/_project/module_carrier.py",
        "src/pietto/_project/module_catalog.py",
        "tests/test_phase54_semantic_fact_preservation.py",
    ),
    "55": (
        "src/pietto/_project/package_manifest.py",
        "src/pietto/_project/package_load_plan.py",
        "src/pietto/_project/package_loader.py",
        "src/pietto/_project/package_inspection.py",
        "tests/test_phase55_slice11_package_pure_boundary_differential_and_e2e.py",
    ),
    "56": (
        "src/pietto/semantic/capability_profiles.py",
        "src/pietto/_project/capability_checking.py",
        "tests/test_phase56_slice10_completion_audit_phase57_handoff.py",
    ),
    "57": (
        "src/pietto/_project/extension_catalog_inspection.py",
        "tests/test_phase57_slice13_completion_audit_phase58_handoff.py",
    ),
    "58": (
        "src/pietto/_project_explain/model.py",
        "tests/test_phase58_slice17_completion_audit_phase59_handoff.py",
    ),
    "59": (
        "src/pietto/_project/package_graph.py",
        "src/pietto/_project/package_graph_inspection.py",
        "tests/test_phase59_slice12_completion_audit_phase60_handoff.py",
    ),
    "60": (
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/sql/window_strategy.py",
        "tests/test_phase60_slice12_differential_compatibility.py",
    ),
}

_SLICE13_STATIC_PATHS = (
    "docs/spec/phase60-completion-readiness-audit-phase61-handoff-v1.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice13_completion_readiness_audit_phase61_handoff.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )[1:]


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _imported_modules(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def test_all_13_owners_have_exact_spec_test_production_and_terminal_authority() -> None:
    specs = {path.name for path in (REPO_ROOT / "docs/spec").glob("phase60*.md")}
    tests = {path.name for path in (REPO_ROOT / "tests").glob("test_phase60_slice*.py")}
    assert specs == {spec for _owner, spec, _test, _production in _SLICE_AUTHORITIES}
    assert tests == {test for _owner, _spec, test, _production in _SLICE_AUTHORITIES}

    route = _table(
        _section(ROUTE_LOCK.read_text(encoding="utf-8"), "Exact 13-slice Route")
    )
    expected_route = tuple((row[0], row[1]) for row in route)
    assert expected_route == tuple(
        (str(number), owner)
        for number, (owner, _spec, _test, _production) in enumerate(
            _SLICE_AUTHORITIES, start=1
        )
    )
    assert all(
        (REPO_ROOT / path).is_file()
        for _owner, _spec, _test, production in _SLICE_AUTHORITIES
        for path in production
    )

    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Final 13-Slice Completion Matrix"))
    assert len(rows) == 13
    assert tuple((row[0], row[1]) for row in rows) == expected_route
    assert tuple(Path(row[2].strip("`")).name for row in rows) == tuple(
        spec for _owner, spec, _test, _production in _SLICE_AUTHORITIES
    )
    assert tuple(Path(row[3].strip("`")).name for row in rows) == tuple(
        test for _owner, _spec, test, _production in _SLICE_AUTHORITIES
    )
    for row, (_owner, _spec, _test, production) in zip(
        rows, _SLICE_AUTHORITIES, strict=True
    ):
        if production:
            assert row[4] == "; ".join(f"`{path}`" for path in production)
        else:
            assert row[4].startswith("`<none;") and row[4].endswith(">`")
    assert tuple(row[5:8] for row in rows[:12]) == tuple(
        (f"`{commit}`", f"`{tree}`", f"`{run_id}`")
        for _number, commit, tree, run_id, _subject in _PUBLISHED_SLICES
    )
    assert tuple(row[8] for row in rows[:12]) == ("`COMPLETED / PUBLISHED`",) * 12
    assert rows[12][5:9] == (
        "`<this single publication commit>`",
        "`<this commit's exact tree>`",
        "`<this commit's unique natural push CI>`",
        "`CURRENT / PENDING NATURAL CI`",
    )
    assert "Phase 60 ownership obligations evidenced: 13 / 13" in document


def test_published_slice_chain_matches_exact_local_git_objects() -> None:
    rows = _table(
        _section(SPEC.read_text(encoding="utf-8"), "Published Slice 1-12 Authority")
    )
    assert rows == tuple(
        (
            str(number),
            f"`{commit}`",
            f"`{tree}`",
            f"`{run_id}`",
            "`push / attempt 1 / success`",
            f"`{subject}`",
        )
        for number, commit, tree, run_id, subject in _PUBLISHED_SLICES
    )
    commits = tuple(row[1] for row in _PUBLISHED_SLICES)
    if _git("rev-parse", "--is-shallow-repository") == "true":
        normalized = " ".join(
            _section(
                SPEC.read_text(encoding="utf-8"),
                "Published Slice 1-12 Authority",
            ).split()
        )
        assert "12 Slice commits form one direct first-parent chain" in normalized
        return

    assert (
        tuple(
            _git(
                "log",
                "--reverse",
                "--first-parent",
                "--format=%H",
                f"{PHASE60_BASE}..{commits[-1]}",
            ).splitlines()
        )
        == commits
    )
    for position, (_number, commit, tree, _run_id, subject) in enumerate(
        _PUBLISHED_SLICES
    ):
        assert _git("show", "-s", "--format=%T", commit) == tree
        assert _git("show", "-s", "--format=%s", commit) == subject
        expected_parent = PHASE60_BASE if position == 0 else commits[position - 1]
        assert _git("show", "-s", "--format=%P", commit) == expected_parent
    assert _git("merge-base", "--is-ancestor", commits[-1], "HEAD") == ""


def test_delivered_exit_ledger_recomputes_live_owner_evidence() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Phase 60 Delivered Exit Ledger"))
    assert tuple(row[0] for row in rows) == (
        "Authored, resolved, and validated window/frame model",
        "ROWS",
        "RANGE structural/type seam",
        "GROUPS and peer semantics",
        "EXCLUDE",
        "Query-local named windows",
        "Value/navigation modifiers",
        "Target capability and four-state named lowering",
        "Project data lineage plus separate semantic provenance",
        "Private inspection",
        "Real authored E2E",
        "Differential compatibility",
    )
    assert all(row[1] == "`CLOSED`" and row[2] for row in rows)
    assert "Delivered authorities: 12" in document
    assert "Closed authorities: 12" in document
    assert all(
        required <= _function_names(REPO_ROOT / "tests" / filename)
        for filename, required in _EXIT_TEST_FUNCTIONS.items()
    )
    assert tuple(NamedWindowLoweringStrategy) == (
        NamedWindowLoweringStrategy.NATIVE_PRESERVE,
        NamedWindowLoweringStrategy.NATIVE_REORDER,
        NamedWindowLoweringStrategy.INLINE_EXACT,
        NamedWindowLoweringStrategy.NOT_LOWERABLE,
    )
    assert tuple(field.name for field in fields(WindowResultProjectFact)) == (
        "semantic_fact",
        "analysis",
        "semantic_provenance",
        "result_identity",
        "dependency_occurrences",
        "dependency_edges",
        "provenance",
    )
    assert tuple(field.name for field in fields(WindowSemanticProvenance)) == (
        "analysis",
        "function_identity",
        "use_kind",
        "named_target",
        "partition_origin",
        "order_origin",
        "frame_origin",
        "frame_applicability",
        "frame_unit",
        "frame_start",
        "frame_end",
        "frame_exclusion",
        "null_treatment",
        "null_treatment_is_explicit",
        "nth_direction",
        "nth_direction_is_explicit",
    )


def test_self_owned_open_search_has_only_closed_or_exact_terminal_classes() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Self-Owned-Open Audit"))
    terminals = {
        "CLOSED",
        "PUBLISHED_NEGATIVE_STATE",
        "TRANSFERRED_TO_EXACT_LATER_OWNER",
        "INTENTIONALLY_OUT_OF_SCOPE",
    }
    assert tuple(row[0] for row in rows) == (
        "`TODO` / `FIXME` in Phase 60 production, specs, and tests",
        "Slice 2–9 historical future/next-owner markers",
        "Semantic-valid backend limitations, `NOT_LOWERABLE`, `unsupported`, and `blocked` outcomes",
        "`QUALIFY` and post-window filtering",
        "RANGE numeric/Decimal/temporal/date/timestamp/interval/timezone typing, coercion, arithmetic, comparison, overflow, foldability, and empty-frame result type/nullability refinement",
        "Aggregate-as-window, aggregate `FILTER`/internal ordering, advanced grouping, aggregate-domain semantics, and aggregate-result window inputs",
        "Reusable module/package window assets",
        "Remote package transport and trust",
        "Solver, canonical lockfile, and first Rust-kernel decision",
        "Release-aware/general backend and catalog expansion",
        "Public window/frame/lineage schema and release readiness",
        "Database execution, optimizer/runtime evaluation, installation, publication, signing, and attestation",
        "Phase 61 route, slice count, and Project IR implementation",
    )
    assert all(row[1].strip("`") in terminals and row[2] for row in rows)
    assert not {"OPEN", "UNASSIGNED", "TBD", "UNKNOWN_OWNER"} & {
        row[1].strip("`") for row in rows
    }
    assert "PHASE60_SELF_OWNED_OPEN = 0" in document

    markers = ("TO" + "DO", "FIX" + "ME")
    historical_phase60_paths = tuple(
        REPO_ROOT / "docs/spec" / spec
        for _owner, spec, _test, _production in _SLICE_AUTHORITIES[:-1]
    ) + tuple(
        REPO_ROOT / "tests" / test
        for _owner, _spec, test, _production in _SLICE_AUTHORITIES[:-1]
    )
    production_paths = {
        REPO_ROOT / path
        for _owner, _spec, _test, production in _SLICE_AUTHORITIES
        for path in production
    }
    assert not any(
        marker in path.read_text(encoding="utf-8")
        for path in (*historical_phase60_paths, *production_paths, PROBE)
        for marker in markers
    )


def test_phase51_60_checkpoint_uses_live_distinct_authorities() -> None:
    rows = _table(_section(SPEC.read_text(encoding="utf-8"), "Phase 51-60 Checkpoint"))
    assert tuple(row[0] for row in rows) == tuple(str(phase) for phase in range(51, 61))
    assert all(row[1] and row[2] and row[3] for row in rows)
    assert all(
        (REPO_ROOT / path).is_file()
        for paths in _CHECKPOINT_PATHS.values()
        for path in paths
    )

    preservation_imports = _imported_modules(
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    assert {
        "pietto._project.aggregate_grouped_clause_facts",
        "pietto.semantic.capability_facts",
        "pietto.semantic.window_analysis",
        "pietto._project.module_carrier",
        "pietto._project.module_catalog",
    } <= preservation_imports
    graph_imports = _imported_modules(
        REPO_ROOT / "src/pietto/_project/package_graph.py"
    )
    assert {
        "pietto._project.package_manifest",
        "pietto._project.package_load_plan",
        "pietto._project.package_loader",
        "pietto._project.capability_checking",
        "pietto._project.extension_catalog_inspection",
        "pietto._project.window_semantics",
    } <= graph_imports

    assert ProjectExplainFormat.PROJECT_EXPLAIN_V1.value == (
        "pietto.project-explain.v1"
    )
    assert tuple(field.name for field in fields(ProjectExplainEnvelope)) == (
        "format",
        "ok",
        "diagnostics",
        "payload",
    )
    assert version("pietto") == "0.1.0"
    assert project_explain_package.__all__ == project_package.__all__ == ()
    for name in ("NamedWindowLoweringStrategy", "WindowSemanticProvenance"):
        assert not hasattr(pietto, name)
    if _git("rev-parse", "--is-shallow-repository") != "true":
        assert (
            _git(
                "diff",
                "--name-only",
                f"{PHASE60_BASE}..{_PUBLISHED_SLICES[-1][1]}",
                "--",
                "src/pietto/_project_explain",
                "docs/spec/cli-json-v1.md",
                "docs/spec/project-cli-json-v2.md",
                "docs/spec/semantic-metadata-artifact-v1.md",
                "docs/spec/pietto-config-v1.md",
                "pyproject.toml",
                "uv.lock",
                ".github/workflows",
            )
            == ""
        )


def test_deferred_subjects_and_aggregate_result_input_have_exact_later_owners() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Deferred-Subject Reconciliation"))
    assert tuple((row[0], row[2]) for row in rows) == (
        ("`QUALIFY` / post-window filtering", "Phase 63"),
        (
            "RANGE numeric/Decimal/temporal/date/timestamp/interval/timezone typing, coercion, arithmetic, comparison, overflow, and foldability",
            "Phase 64",
        ),
        ("Empty-frame result type/nullability refinement", "Phase 64"),
        (
            "Aggregate-as-window, aggregate `FILTER`/internal ordering, advanced grouping, and aggregate-domain semantics",
            "Phase 65",
        ),
        ("Reusable module/package window assets", "Phase 66"),
        ("Remote package transport/trust", "Phase 67"),
        ("Solver/lockfile and first Rust-kernel decision", "Phase 68"),
        ("Release-aware/general backend/catalog expansion", "Phase 69"),
        (
            "Public window/frame/lineage schema and release readiness",
            "Phase 70",
        ),
    )
    assert all(row[1] == "`TRANSFERRED_TO_EXACT_LATER_OWNER`" for row in rows)

    aggregate_input = " ".join(
        _section(document, "Aggregate-Result Window Input").split()
    )
    for value in (
        "first_value(aggregate_output_alias)",
        "principally by Phase 65",
        "Phase 61 and Phase 62",
        "Phase 63 owns any later SQL-stage implications",
        "neither implements nor simulates",
    ):
        assert value in aggregate_input


def test_phase61_handoff_freezes_readiness_without_route_or_implementation() -> None:
    document = SPEC.read_text(encoding="utf-8")
    handoff_section = _section(document, "Phase 61 Handoff Boundary")
    handoff = " ".join(handoff_section.split())
    for value in (
        "Phase 61 — Project IR And Semantic Composition",
        "Malloy",
        "Cube",
        "Apache Calcite",
        "Substrait",
        "current Pietto authorities",
        "implementation-specific historical baggage",
        "freezes no Phase 61 route or slice count",
        "implements no Project IR",
    ):
        assert value in handoff
    assert "| Slice |" not in handoff_section

    project_ir = " ".join(
        _section(document, "Mandatory Project-IR Readiness Laws").split()
    )
    for value in (
        "RelationPlan != NestedOutputField != NestedResultValue != TargetEncoding != PhysicalSQLStrategy",
        "QueryOutputField = ScalarOutputField | RecordOutputField | NestedOutputField",
        "OpenRelationPlan<Bindings, Row>",
        "exact relation/field anchors",
        "Correlation is not itself a grain transition",
    ):
        assert value in project_ir

    grain = " ".join(
        _section(document, "Grain And Plan-Property Readiness Laws").split()
    )
    for value in (
        "GrainOccurrenceIdentity GrainState / GrainDescriptor",
        "SAME FINER_THAN COARSER_THAN INCOMPARABLE UNKNOWN",
        "PRESERVE / REDUCE / EXPAND / CORRELATE",
        "row shape grain cardinality multiplicity ordering free bindings fact domains null extension policy context",
    ):
        assert value in grain

    nested = " ".join(_section(document, "Nested-Result Readiness Laws").split())
    for value in (
        "defaults to BAG, not List",
        "ordering contract is independent of collection cardinality",
        "cardinality != container kind != container nullability != element nullability",
        "relationship cardinality != nested output cardinality",
        "relationship traversal != outer correlation",
        "`UNNEST` / `EXPLODE` is an explicit grain-changing operator",
        "OccurrenceIdentity != RuntimeRowKey != PresentationOrdinal",
    ):
        assert value in nested

    planning = " ".join(
        _section(document, "Planning Lowering And Policy Readiness Laws").split()
    )
    for value in (
        "semantic definition != use occurrence != evaluation context != logical plan occurrence",
        "must not borrow an arbitrary fact/join context",
        "schema, values, multiplicity, ordering, null/empty behavior, cardinality, and policy semantics",
        "physical/target strategies, not semantic relation identity",
        "Access/security policy context",
    ):
        assert value in planning


def test_slice13_reader_closure_zero_delta_and_lifecycle_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    reader = _section(document, "Reader Closure And Slice 13 Delta")
    normalized_reader = " ".join(reader.split())
    assert all(path in reader for path in _SLICE13_STATIC_PATHS)
    assert "A2/M4/D0" in reader
    assert "sole direct reader" in normalized_reader
    assert all((REPO_ROOT / path).is_file() for path in _SLICE13_STATIC_PATHS)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in _SLICE13_STATIC_PATHS
    )
    for value in (
        "production        0",
        "grammar/generated 0",
        "goldens           0",
        "package/deps      0",
        "workflow          0",
        "public schema     0",
        "version           0.1.0",
    ):
        assert value in reader

    lifecycle = " ".join(_section(document, "Lifecycle And Publication").split())
    for value in (
        "Phase 60: ACTIVE / COMPLETION CANDIDATE",
        "Slices 1-12: COMPLETED",
        "Slice 13: CURRENT / COMPLETION CANDIDATE",
        "Phase 61: NEXT / NOT IMPLEMENTED",
        "Phase 60 = COMPLETED",
        "No status-only follow-up commit",
        "does not begin Phase 61 or freeze its route",
        "Complete Phase 60 advanced windows",
    ):
        assert value in lifecycle

    source_tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "rglob"
        for node in ast.walk(source_tree)
    )
