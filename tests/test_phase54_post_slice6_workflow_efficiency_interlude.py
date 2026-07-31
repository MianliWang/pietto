from __future__ import annotations

# pyright: reportMissingImports=false

import ast
from dataclasses import asdict, replace
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import audit_gate2_readers as reader_audit  # noqa: E402
import build_evidence_bundle as evidence_builder  # noqa: E402
import run_gate2_topology_checks as topology_runner  # noqa: E402
import run_lean_gate2 as lean_runner  # noqa: E402
import verify_evidence_bundle as evidence_verifier  # noqa: E402
from _active_gate2_manifest import (  # noqa: E402
    ActiveGate2RepositoryState,
    _matches_active_gate2_candidate,
    _matches_active_gate2_manifest,
    _matches_active_gate2_reconciled_main,
    active_gate2_candidate_is_active,
    active_gate2_local_lifecycle_is_active,
    active_gate2_manifest_is_active,
)
from _active_gate2_manifest_data import (  # noqa: E402
    ACTIVE_GATE2_ADDED_PATHS,
    ACTIVE_GATE2_ALLOWLIST_PATHS,
    ACTIVE_GATE2_BASE,
    ACTIVE_GATE2_CANDIDATE_BRANCH,
    ACTIVE_GATE2_CANDIDATE_SUBJECT,
    ACTIVE_GATE2_COUNTS,
    ACTIVE_GATE2_DELETED_PATHS,
    ACTIVE_GATE2_DIRECT_READER_PATHS,
    ACTIVE_GATE2_DIRECT_READER_SHA256,
    ACTIVE_GATE2_MARKER,
    ACTIVE_GATE2_MODIFIED_PATHS,
    ACTIVE_GATE2_READER_CLOSURE_SHA256,
    ACTIVE_GATE2_READER_ITEMS,
    ACTIVE_GATE2_TRANSITIVE_READER_SHA256,
    ADDED_PATHS,
    ALLOWLIST_PATHS,
    MECHANICAL_READER_PATHS,
    MODIFIED_PATHS,
    NON_READER_MODIFIED_PATHS,
    REOPEN1_HASH_LOCK_READER_PATHS,
)
from _topology_sensitive_registry import (  # noqa: E402
    EXPECTED_FILE_COUNT,
    EXPECTED_NODE_COUNT,
    EXPECTED_PAYLOAD_BYTES,
    EXPECTED_SELECTED_ITEMS,
    EXPECTED_SHA256,
    LEGACY_DIRTY_OVERLAY_NODE_IDS,
    TOPOLOGY_REGISTRY_FILES,
    TOPOLOGY_REGISTRY_PAYLOAD,
    TOPOLOGY_REGISTRY_SHA256,
    TOPOLOGY_SELECTED_ITEMS,
    TOPOLOGY_SENSITIVE_NODE_IDS,
)


SPEC_REL = "docs/spec/phase54-post-slice6-workflow-efficiency-interlude-v1.md"
RECOVERY_REL = "docs/spec/pietto-end-to-end-resilience-and-recovery-standard-v1.md"
LEAN_REL = "docs/spec/pietto-lean-validation-and-evidence-standard-v1.md"
SELF_REL = "tests/test_phase54_post_slice6_workflow_efficiency_interlude.py"
EXPECTED_TEST_NAMES = (
    "test_stable_manifest_data_is_exact_and_single_owner",
    "test_stable_manifest_accepts_only_exact_active_gate2_state",
    "test_stable_manifest_rejects_subset_superset_wrong_base_and_stale_goal",
    "test_stable_manifest_rejects_staged_other_topology_and_environment_activation",
    "test_compatibility_manifest_reexports_stable_authority_without_weakening",
    "test_reader_auditor_schema_and_deterministic_order_are_exact",
    "test_reader_auditor_discovers_literal_raw_hash_blob_digest_and_inventory_readers",
    "test_reader_auditor_discovers_nested_readers_and_dependency_first_order",
    "test_reader_auditor_reports_sccs_without_losing_edges",
    "test_reader_auditor_classifies_content_and_topology_readers",
    "test_reader_auditor_fails_closed_for_unresolved_dynamic_reader",
    "test_reader_auditor_matches_slice5_and_slice6_known_closure",
    "test_independent_bruteforce_scan_has_zero_missing_executing_readers",
    "test_topology_registry_identity_count_and_single_authority_are_exact",
    "test_topology_registry_contains_reviewed_seed_and_detected_topology_callers",
    "test_topology_registry_excludes_known_content_only_reader",
    "test_topology_runner_candidate_projection_is_deterministic",
    "test_topology_runner_pr_main_and_reconciled_projections_are_deterministic",
    "test_topology_runner_negative_matrix_is_exact_and_fail_closed",
    "test_topology_runner_never_mutates_primary_repository_index",
    "test_lean_gate2_command_graph_contains_every_authoritative_gate_once",
    "test_lean_gate2_refuses_manifest_index_network_and_unresolved_warning_drift",
    "test_lean_gate2_keeps_topology_serial_and_records_commands",
    "test_evidence_bundle_builds_six_deterministic_sidecar_formats",
    "test_evidence_verifier_checks_identity_mode_schema_hash_terminal_and_no_duplication",
    "test_evidence_verifier_rejects_missing_placeholder_malformed_and_duplicate_terminal",
    "test_recovery_standard_contract_is_complete_and_fail_closed",
    "test_lean_validation_standard_contract_preserves_all_quality_gates",
    "test_agents_binding_is_narrow_and_no_product_surface_changed",
    "test_interlude_contract_allowlist_legacy_equivalence_performance_and_next_state_are_exact",
)
EXPECTED_DIRECT_READER_SHA256 = (
    "649415db62667eff8e5dbfa47fb83ae30b05c0cac58fd01da87cd55df58672cd"
)
EXPECTED_TRANSITIVE_READER_SHA256 = (
    "44cbf17112a093bd97ee3c2d88e37f290551222f4a636faf063d7200f1875fb3"
)
EXPECTED_READER_CLOSURE_SHA256 = (
    "760af336b0b47c9443a6dfbe99c477bc67ead160e5e0401a9d53c2cfecbb2b54"
)


def _state() -> ActiveGate2RepositoryState:
    return ActiveGate2RepositoryState(
        marker=ACTIVE_GATE2_MARKER,
        branch_oid=ACTIVE_GATE2_BASE,
        branch_head="main",
        branch_upstream="origin/main",
        ahead=0,
        behind=0,
        head_parents=("c44a4271d9592cb393d2232f127a59d8466cc60a",),
        head_subject="Complete Phase 54 local import module export Slice 6",
        main_oid=ACTIVE_GATE2_BASE,
        origin_main_oid=ACTIVE_GATE2_BASE,
        committed_added_paths=frozenset(),
        committed_modified_paths=frozenset(),
        committed_deleted_paths=frozenset(),
        added_paths=ACTIVE_GATE2_ADDED_PATHS,
        modified_paths=ACTIVE_GATE2_MODIFIED_PATHS,
        deleted_paths=ACTIVE_GATE2_DELETED_PATHS,
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )


def _candidate_state() -> ActiveGate2RepositoryState:
    return replace(
        _state(),
        branch_oid="1" * 40,
        branch_head=ACTIVE_GATE2_CANDIDATE_BRANCH,
        branch_upstream="",
        ahead=-1,
        behind=-1,
        head_parents=(ACTIVE_GATE2_BASE,),
        head_subject=ACTIVE_GATE2_CANDIDATE_SUBJECT,
        committed_added_paths=ACTIVE_GATE2_ADDED_PATHS,
        committed_modified_paths=ACTIVE_GATE2_MODIFIED_PATHS,
        committed_deleted_paths=ACTIVE_GATE2_DELETED_PATHS,
        added_paths=frozenset(),
        modified_paths=frozenset(),
        deleted_paths=frozenset(),
    )


def _reconciled_state() -> ActiveGate2RepositoryState:
    return replace(
        _candidate_state(),
        branch_oid="2" * 40,
        branch_head="main",
        branch_upstream="origin/main",
        ahead=0,
        behind=0,
        head_subject=f"{ACTIVE_GATE2_CANDIDATE_SUBJECT} (#999)",
        main_oid="2" * 40,
        origin_main_oid="2" * 40,
    )


def _bundle(tmp_path: Path) -> dict[str, Path]:
    base = ACTIVE_GATE2_BASE
    statuses = {
        **{path: "A" for path in ACTIVE_GATE2_ADDED_PATHS},
        **{path: "M" for path in ACTIVE_GATE2_MODIFIED_PATHS},
        **{path: "D" for path in ACTIVE_GATE2_DELETED_PATHS},
    }
    frozen = evidence_builder.freeze_reviewed_tree(
        root=REPO_ROOT, base=base, statuses=statuses
    )
    tree = frozen.reviewed_tree
    reader = reader_audit.audit_repository(
        root=REPO_ROOT,
        base=base,
        changed_paths=statuses,
        active_manifest_data="tests/_active_gate2_manifest_data.py",
        reviewed_tree=tree,
    )
    topology = {
        "schema": evidence_builder.TOPOLOGY_SCHEMA,
        "base": base,
        "reviewed_tree": tree,
        "registry": {"node_id_count": 323, "selected_items_per_projection": 1143},
        "positive_results": [{"result": "PASS"} for _ in range(4)],
        "negative_results": [{"result": "REJECTED"} for _ in range(24)],
        "equivalence": {
            "outcome_equality": True,
            "excluded_content_invariant": True,
        },
        "primary_state_before": {"index": "same"},
        "primary_state_after": {"index": "same"},
    }
    topology["payload_sha256"] = hashlib.sha256(
        evidence_builder.canonical_json(topology)
    ).hexdigest()
    performance = {
        "schema": evidence_builder.PERFORMANCE_SCHEMA,
        "base": base,
        "reviewed_tree": tree,
        "outcome_equality": True,
        "reader_closure_runs": 1,
        "authoritative_validate_runs": 1,
        "legacy_repeated_items": 27144,
        "lean_repeated_topology_items": 4572,
        "repeated_item_reduction": 22572,
    }
    command_names = (
        "lock",
        "focused",
        "compatibility",
        "reader_audit",
        "format_check",
        "reader_closure",
        "topology",
        "ruff",
        "pyright_production",
        "pyright_tests",
        "authoritative_validate",
        "clean_collection",
        "clean_pytest",
        "generated",
        "goldens",
        "package_smoke",
        "installed_cli_version",
    )
    empty_sha = hashlib.sha256(b"").hexdigest()
    records = [
        {
            "name": name,
            "argv": ["uv", "test"] if name != "reader_audit" else ["true"],
            "base": base,
            "reviewed_tree": tree,
            "cwd": str(REPO_ROOT),
            "env": {"UV_NO_SYNC": "1", "UV_OFFLINE": "1"},
            "returncode": 0,
            "wall_ns": 1,
            "cpu_ns": 1,
            "stdout_base64": "",
            "stdout_bytes": 0,
            "stdout_sha256": empty_sha,
            "stderr_base64": "",
            "stderr_bytes": 0,
            "stderr_sha256": empty_sha,
        }
        for name in command_names
    ]
    payloads = evidence_builder.build_payloads(
        root=REPO_ROOT,
        base=base,
        reviewed_tree=tree,
        statuses=statuses,
        command_records=records,
        reader_payload=evidence_builder.canonical_json(reader),
        topology_payload=evidence_builder.canonical_json(topology),
        performance_payload=evidence_builder.canonical_json(performance),
    )
    paths = evidence_builder.write_bundle(tmp_path / "bundle", payloads)
    return {
        "identity_manifest": paths[0],
        "canonical_patch": paths[1],
        "command_ledger": paths[2],
        "reader_closure": paths[3],
        "topology_results": paths[4],
        "performance_results": paths[5],
    }


def test_stable_manifest_data_is_exact_and_single_owner() -> None:
    assert ACTIVE_GATE2_COUNTS == (12, 51, 0)
    assert (len(ADDED_PATHS), len(MODIFIED_PATHS), 0) == ACTIVE_GATE2_COUNTS
    assert len(NON_READER_MODIFIED_PATHS) == 1
    assert len(MECHANICAL_READER_PATHS) == 50
    assert len(REOPEN1_HASH_LOCK_READER_PATHS) == 10
    assert REOPEN1_HASH_LOCK_READER_PATHS <= MECHANICAL_READER_PATHS
    assert len(ALLOWLIST_PATHS) == 63
    assert ACTIVE_GATE2_ALLOWLIST_PATHS == frozenset(ALLOWLIST_PATHS)
    assert "src/pietto" not in "\n".join(ALLOWLIST_PATHS)


def test_stable_manifest_accepts_only_exact_active_gate2_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import _active_gate2_manifest as manifest_module

    assert _matches_active_gate2_manifest(_state())
    assert tuple(inspect.signature(active_gate2_manifest_is_active).parameters) == ()
    assert (
        tuple(inspect.signature(active_gate2_local_lifecycle_is_active).parameters)
        == ()
    )
    monkeypatch.setattr(
        manifest_module,
        "_read_active_gate2_repository_state",
        _state,
    )
    assert active_gate2_manifest_is_active()
    assert _matches_active_gate2_candidate(_candidate_state())
    assert not _matches_active_gate2_manifest(_candidate_state())
    monkeypatch.setattr(
        manifest_module,
        "_read_active_gate2_repository_state",
        _candidate_state,
    )
    assert active_gate2_candidate_is_active()
    assert active_gate2_manifest_is_active()
    assert active_gate2_local_lifecycle_is_active()
    assert _matches_active_gate2_reconciled_main(_reconciled_state())
    monkeypatch.setattr(
        manifest_module,
        "_read_active_gate2_repository_state",
        _reconciled_state,
    )
    assert active_gate2_local_lifecycle_is_active()
    assert active_gate2_manifest_is_active()


def test_stable_manifest_rejects_subset_superset_wrong_base_and_stale_goal() -> None:
    cases = (
        replace(_state(), added_paths=frozenset()),
        replace(_state(), modified_paths=frozenset()),
        replace(_state(), added_paths=ACTIVE_GATE2_ADDED_PATHS | {"extra.txt"}),
        replace(_state(), branch_oid="0" * 40),
        replace(_state(), marker="PHASE54_SLICE6_GATE2"),
    )
    assert all(not _matches_active_gate2_manifest(case) for case in cases)
    candidate_cases = (
        replace(_candidate_state(), committed_added_paths=frozenset()),
        replace(_candidate_state(), committed_modified_paths=frozenset()),
        replace(
            _candidate_state(),
            committed_added_paths=ACTIVE_GATE2_ADDED_PATHS | {"extra.txt"},
        ),
        replace(_candidate_state(), head_parents=("0" * 40,)),
        replace(_candidate_state(), head_subject="Wrong subject"),
        replace(_candidate_state(), main_oid="0" * 40),
    )
    assert all(not _matches_active_gate2_candidate(case) for case in candidate_cases)
    reconciled_cases = (
        replace(_reconciled_state(), head_parents=("0" * 40,)),
        replace(_reconciled_state(), head_subject="Wrong subject"),
        replace(_reconciled_state(), origin_main_oid="0" * 40),
        replace(_reconciled_state(), shallow=True),
    )
    assert all(
        not _matches_active_gate2_reconciled_main(case) for case in reconciled_cases
    )


def test_stable_manifest_rejects_staged_other_topology_and_environment_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = (
        replace(_state(), staged_paths=frozenset({"AGENTS.md"})),
        replace(_state(), other_paths=frozenset({"?? unrelated.txt"})),
        replace(_state(), branch_head="topic"),
        replace(_state(), branch_upstream=""),
        replace(_state(), shallow=True),
        replace(_state(), worktree_count=2),
        replace(_state(), active_git_operation=True),
    )
    assert all(not _matches_active_gate2_manifest(case) for case in cases)
    monkeypatch.setenv("PIETTO_ACTIVE_GATE2", ACTIVE_GATE2_MARKER)
    assert all(not _matches_active_gate2_manifest(case) for case in cases)


def test_compatibility_manifest_reexports_stable_authority_without_weakening() -> None:
    import _phase54_active_gate2_manifest as compatibility

    assert compatibility.PHASE54_ACTIVE_GATE2_BASE == ACTIVE_GATE2_BASE
    assert compatibility.PHASE54_ACTIVE_GATE2_MARKER == ACTIVE_GATE2_MARKER
    assert compatibility.PHASE54_ACTIVE_GATE2_ADDED_PATHS == ACTIVE_GATE2_ADDED_PATHS
    assert compatibility._matches_phase54_active_gate2_manifest(_state())
    source = (REPO_ROOT / "tests/_phase54_active_gate2_manifest.py").read_text()
    assert "Compatibility exports" in source
    assert "os.environ" not in source


def test_reader_auditor_schema_and_deterministic_order_are_exact() -> None:
    document = reader_audit.audit_repository(
        root=REPO_ROOT,
        base=ACTIVE_GATE2_BASE,
        changed_paths=ALLOWLIST_PATHS,
        active_manifest_data="tests/_active_gate2_manifest_data.py",
        strict_dynamic=False,
    )
    assert document["schema"] == reader_audit.SCHEMA
    assert document["reader_paths"] == sorted(document["reader_paths"])
    assert document["direct_readers"] == sorted(document["direct_readers"])
    assert len(document["payload_sha256"]) == 64


def test_reader_auditor_discovers_literal_raw_hash_blob_digest_and_inventory_readers() -> (
    None
):
    source = ast.parse(
        'P = "tests/target.py"\nH = "' + "a" * 64 + '"\nPath(P).read_bytes()\n'
        'subprocess.run(["git", "show", "HEAD:tests/target.py"])\n'
        'Path("tests").rglob("*.py")\n'
    )
    assert "tests/target.py" in reader_audit._literal_paths(source)
    text = ast.unparse(source)
    assert reader_audit.SHA256_LITERAL.search(text)
    assert "read_bytes" in text and "git" in text and "rglob" in text


def test_reader_auditor_discovers_nested_readers_and_dependency_first_order() -> None:
    nodes = {"leaf.py", "middle.py", "root.py"}
    imports = {"leaf.py": set(), "middle.py": {"leaf.py"}, "root.py": {"middle.py"}}
    assert reader_audit._dependency_first_order(nodes, imports) == (
        ("leaf.py",),
        ("middle.py",),
        ("root.py",),
    )


def test_reader_auditor_reports_sccs_without_losing_edges() -> None:
    nodes = {"a.py", "b.py", "c.py"}
    edges = {"a.py": {"b.py"}, "b.py": {"a.py"}, "c.py": {"b.py"}}
    components = reader_audit._strongly_connected_components(nodes, edges)
    assert ("a.py", "b.py") in components
    assert ("c.py",) in components


def test_reader_auditor_classifies_content_and_topology_readers() -> None:
    document = reader_audit.audit_repository(
        root=REPO_ROOT,
        base=ACTIVE_GATE2_BASE,
        changed_paths=ALLOWLIST_PATHS,
        active_manifest_data="tests/_active_gate2_manifest_data.py",
        strict_dynamic=False,
    )
    topology = set(document["topology_sensitive"])
    content = set(document["content_sensitive"])
    assert topology
    assert content
    assert not topology & content
    assert topology | content == set(document["reader_paths"])


def test_reader_auditor_fails_closed_for_unresolved_dynamic_reader() -> None:
    tree = ast.parse("def f(value):\n    return Path(value).read_bytes()\n")
    warnings = reader_audit._unresolved_dynamic_warnings("tests/test_dynamic.py", tree)
    assert warnings == ("tests/test_dynamic.py:2:Path(value).read_bytes",)


def test_reader_auditor_matches_slice5_and_slice6_known_closure() -> None:
    document = reader_audit.audit_repository(
        root=REPO_ROOT,
        base=ACTIVE_GATE2_BASE,
        changed_paths=ALLOWLIST_PATHS,
        active_manifest_data="tests/_active_gate2_manifest_data.py",
        strict_dynamic=False,
    )
    assert len(document["direct_readers"]) == 59
    assert len(document["transitive_readers"]) == 107
    assert len(document["reader_paths"]) == 166
    direct = "".join(f"{path}\n" for path in document["direct_readers"]).encode()
    transitive = "".join(
        f"{path}\n" for path in document["transitive_readers"]
    ).encode()
    closure = "".join(f"{path}\n" for path in document["reader_paths"]).encode()
    assert hashlib.sha256(direct).hexdigest() == EXPECTED_DIRECT_READER_SHA256
    assert hashlib.sha256(transitive).hexdigest() == EXPECTED_TRANSITIVE_READER_SHA256
    assert hashlib.sha256(closure).hexdigest() == EXPECTED_READER_CLOSURE_SHA256
    assert set(document["direct_readers"]) == ACTIVE_GATE2_DIRECT_READER_PATHS
    assert ACTIVE_GATE2_DIRECT_READER_SHA256 == EXPECTED_DIRECT_READER_SHA256
    assert ACTIVE_GATE2_TRANSITIVE_READER_SHA256 == EXPECTED_TRANSITIVE_READER_SHA256
    assert ACTIVE_GATE2_READER_CLOSURE_SHA256 == EXPECTED_READER_CLOSURE_SHA256
    assert ACTIVE_GATE2_READER_ITEMS == 6786
    assert document["new_mechanical_targets"] == sorted(REOPEN1_HASH_LOCK_READER_PATHS)
    assert document["missing_executing_readers"] == []
    assert (
        "tests/test_phase54_local_export_visibility_module_facades.py"
        in document["direct_readers"]
    )


def test_independent_bruteforce_scan_has_zero_missing_executing_readers() -> None:
    roots = set(reader_audit.historical_reader_roots(REPO_ROOT, ACTIVE_GATE2_BASE))
    selector_only = {
        "tests/test_phase21_completion_audit.py",
        "tests/test_phase26_aggregate_expression_arguments_candidate_decision.py",
        "tests/test_phase30_candidate_decision.py",
        "tests/test_phase30_decimal_precision_scale_contract.py",
        "tests/test_phase44_project_source_selection_scope_lock.py",
    }
    importers = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "tests").glob("test_*.py")
        if path.name != Path(SELF_REL).name
        if "from test_phase54_local_import_module_export_foundation_scope_lock import"
        in path.read_text()
    }
    discovered = reader_audit.audit_repository(
        root=REPO_ROOT,
        base=ACTIVE_GATE2_BASE,
        changed_paths=ALLOWLIST_PATHS,
        active_manifest_data="tests/_active_gate2_manifest_data.py",
        strict_dynamic=False,
    )
    independent = roots | importers | selector_only
    assert len(roots) == 54
    assert len(selector_only) == 5
    assert independent == set(discovered["reader_paths"])
    assert len(independent) == 166
    assert len(discovered["direct_readers"]) == 59
    assert discovered["missing_executing_readers"] == []
    with pytest.raises(
        reader_audit.ReaderAuditError, match="missing executing readers"
    ):
        reader_audit.audit_repository(
            root=REPO_ROOT,
            base=ACTIVE_GATE2_BASE,
            changed_paths=ALLOWLIST_PATHS,
            active_manifest_data="tests/_active_gate2_manifest_data.py",
            strict_dynamic=False,
            seed_reader_paths=roots,
        )
    with pytest.raises(
        reader_audit.ReaderAuditError,
        match="absent from prospective manifest",
    ):
        reader_audit.audit_repository(
            root=REPO_ROOT,
            base=ACTIVE_GATE2_BASE,
            changed_paths=ALLOWLIST_PATHS - REOPEN1_HASH_LOCK_READER_PATHS,
            active_manifest_data="tests/_active_gate2_manifest_data.py",
            strict_dynamic=False,
        )


def test_topology_registry_identity_count_and_single_authority_are_exact() -> None:
    assert len(TOPOLOGY_SENSITIVE_NODE_IDS) == EXPECTED_NODE_COUNT == 323
    assert TOPOLOGY_REGISTRY_FILES == EXPECTED_FILE_COUNT == 159
    assert len(TOPOLOGY_REGISTRY_PAYLOAD) == EXPECTED_PAYLOAD_BYTES == 41085
    assert TOPOLOGY_SELECTED_ITEMS == EXPECTED_SELECTED_ITEMS == 1143
    assert TOPOLOGY_REGISTRY_SHA256 == EXPECTED_SHA256
    assert hashlib.sha256(TOPOLOGY_REGISTRY_PAYLOAD).hexdigest() == EXPECTED_SHA256


def test_topology_registry_contains_reviewed_seed_and_detected_topology_callers() -> (
    None
):
    registry = set(TOPOLOGY_SENSITIVE_NODE_IDS)
    assert len(LEGACY_DIRTY_OVERLAY_NODE_IDS) == 185
    assert set(LEGACY_DIRTY_OVERLAY_NODE_IDS) <= registry
    assert topology_runner.CENTRAL_NODE in registry
    assert any(
        "GITHUB" in (REPO_ROOT / node.split("::", 1)[0]).read_text()
        for node in registry
    )


def test_topology_registry_excludes_known_content_only_reader() -> None:
    node = f"{SELF_REL}::test_recovery_standard_contract_is_complete_and_fail_closed"
    assert node not in TOPOLOGY_SENSITIVE_NODE_IDS


def test_topology_runner_candidate_projection_is_deterministic() -> None:
    plan = topology_runner.projection_plan(
        candidate="2" * 40,
        pr_merge="3" * 40,
        squash="4" * 40,
        tree="5" * 40,
    )
    assert plan[0].name == "candidate"
    assert plan[0].parents == (ACTIVE_GATE2_BASE,)
    assert plan[0].branch == topology_runner.BRANCH
    assert not plan[0].shallow


def test_topology_runner_pr_main_and_reconciled_projections_are_deterministic(
    tmp_path: Path,
) -> None:
    plan = topology_runner.projection_plan(
        candidate="2" * 40,
        pr_merge="3" * 40,
        squash="4" * 40,
        tree="5" * 40,
    )
    assert tuple(item.name for item in plan) == (
        "candidate",
        "pr_merge",
        "main_push",
        "reconciled_main",
    )
    assert plan[1].parents == (ACTIVE_GATE2_BASE, "2" * 40)
    assert plan[1].shallow and plan[1].event == "pull_request"
    assert plan[1].branch == ""
    assert plan[1].github_ref == "refs/pull/999/merge"
    assert plan[1].github_sha == "3" * 40
    assert plan[2].shallow and plan[2].github_ref == "refs/heads/main"
    assert not plan[3].shallow and plan[3].branch == "main"

    statuses = {
        **{path: "A" for path in ACTIVE_GATE2_ADDED_PATHS},
        **{path: "M" for path in ACTIVE_GATE2_MODIFIED_PATHS},
        **{path: "D" for path in ACTIVE_GATE2_DELETED_PATHS},
    }
    source = tmp_path / "source"
    candidate, tree = topology_runner._copy_active_tree(
        root=REPO_ROOT,
        source=source,
        base=ACTIVE_GATE2_BASE,
        statuses=statuses,
    )
    pr_merge, squash, projections = topology_runner._prepare_positive_repositories(
        source=source,
        root=tmp_path,
        candidate=candidate,
        tree=tree,
    )
    expected = {
        item.name: item
        for item in topology_runner.projection_plan(
            candidate=candidate,
            pr_merge=pr_merge,
            squash=squash,
            tree=tree,
        )
    }
    identities = {}
    for name in ("candidate", "pr_merge", "main_push", "reconciled_main"):
        repo, environment = projections[name]
        identity = topology_runner.validate_projection(
            profile=name,
            repo=repo,
            env=environment,
            candidate=candidate,
            reviewed_tree=tree,
            statuses=statuses,
        )
        reference = expected[name]
        assert identity.head == reference.head
        assert identity.parents == reference.parents
        assert identity.tree == reference.tree
        assert identity.shallow == reference.shallow
        identities[name] = identity

    for name in ("main_push", "reconciled_main"):
        repo, _ = projections[name]
        identity = identities[name]
        assert (
            topology_runner._git(repo, "config", "--get-all", "remote.origin.fetch")
            == topology_runner.ORIGIN_MAIN_FETCH
        )
        assert topology_runner._git(repo, "config", "branch.main.remote") == "origin"
        assert (
            topology_runner._git(repo, "config", "branch.main.merge")
            == "refs/heads/main"
        )
        assert identity.upstream == "origin/main"
        assert identity.refs == (
            ("refs/heads/main", identity.head),
            ("refs/remotes/origin/main", identity.head),
        )


def test_topology_runner_negative_matrix_is_exact_and_fail_closed() -> None:
    assert len(topology_runner.NEGATIVE_CASES) == 24
    assert len(set(topology_runner.NEGATIVE_CASES)) == 24
    assert topology_runner.NEGATIVE_CASES[-3:] == (
        "successor_unpublished",
        "no_diff",
        "protected_tree_mismatch",
    )
    assert topology_runner.NEGATIVE_CASES[20] == "depth_one_active_gate2"
    assert "depth_one_pr" not in topology_runner.NEGATIVE_CASES
    source = (REPO_ROOT / "scripts/run_gate2_topology_checks.py").read_text()
    assert source.count("expect_success=True") == 2
    assert "expect_success=None" not in source
    assert "expect_success=False" in source
    assert "collection_errors" in source
    assert "actual_rejection_code" in source


def test_topology_runner_never_mutates_primary_repository_index() -> None:
    source = (REPO_ROOT / "scripts/run_gate2_topology_checks.py").read_text()
    assert "primary_index_before" in source and "primary_index_after" in source
    assert "os.path.abspath(arguments.python)" in source
    assert "arguments.python.resolve()" not in source
    assert "git worktree" not in source
    assert "git reset" not in source
    assert "primary index changed" in source


def test_lean_gate2_command_graph_contains_every_authoritative_gate_once(
    tmp_path: Path,
) -> None:
    graph = lean_runner.command_graph(
        root=REPO_ROOT,
        manifest=tmp_path / "manifest",
        reader_output=tmp_path / "reader",
        topology_output=tmp_path / "topology",
        focused_nodes=(SELF_REL,),
        compatibility_nodes=("tests/test_phase47_project_json_privacy_hardening.py",),
        reader_nodes=(
            "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        ),
        formatter_paths=(SELF_REL,),
    )
    lean_runner.validate_graph(graph)
    assert sum(command.authoritative_validate for command in graph) == 1
    assert tuple(command.name for command in graph).count("clean_pytest") == 1
    assert tuple(command.name for command in graph).count("package_smoke") == 1


def test_lean_gate2_refuses_manifest_index_network_and_unresolved_warning_drift() -> (
    None
):
    with pytest.raises(lean_runner.LeanGate2Error, match="unresolved"):
        lean_runner.assert_preconditions(root=REPO_ROOT, unresolved_warnings=("x",))
    source = (REPO_ROOT / "scripts/run_lean_gate2.py").read_text()
    assert "dirty set is not the exact active Gate 2 manifest" in source
    assert "index is not empty" in source
    assert 'OFFLINE_ENV = {"UV_OFFLINE": "1", "UV_NO_SYNC": "1"}' in source
    assert "network-capable command in Gate 2 graph" in source


def test_lean_gate2_keeps_topology_serial_and_records_commands(tmp_path: Path) -> None:
    graph = lean_runner.command_graph(
        root=REPO_ROOT,
        manifest=tmp_path / "manifest",
        reader_output=tmp_path / "reader",
        topology_output=tmp_path / "topology",
        focused_nodes=(SELF_REL,),
        compatibility_nodes=(SELF_REL,),
        reader_nodes=(SELF_REL,),
        formatter_paths=(SELF_REL,),
    )
    topology = [command for command in graph if command.topology_serial]
    assert len(topology) == 1 and topology[0].name == "topology"
    source = (REPO_ROOT / "scripts/run_lean_gate2.py").read_text()
    for field in (
        "argv",
        "returncode",
        "wall_seconds",
        "cpu_seconds",
        "stdout_sha256",
        "stderr_sha256",
    ):
        assert field in source


def test_evidence_bundle_builds_six_deterministic_sidecar_formats(
    tmp_path: Path,
) -> None:
    sidecars = _bundle(tmp_path)
    assert tuple(sidecars) == (
        "identity_manifest",
        "canonical_patch",
        "command_ledger",
        "reader_closure",
        "topology_results",
        "performance_results",
    )
    assert (
        sidecars["identity_manifest"]
        .read_text()
        .startswith(evidence_builder.IDENTITY_HEADER)
    )
    assert sidecars["canonical_patch"].read_bytes().startswith(b"diff --git ")
    ledger = json.loads(sidecars["command_ledger"].read_text().splitlines()[0])
    assert ledger["schema"] == evidence_builder.LEDGER_SCHEMA
    assert ledger["sequence"] == 1


def test_evidence_verifier_checks_identity_mode_schema_hash_terminal_and_no_duplication(
    tmp_path: Path,
) -> None:
    sidecars = _bundle(tmp_path)
    tree = json.loads(sidecars["reader_closure"].read_bytes())["reviewed_tree"]
    terminal = "PIETTO_TEST_GATE2_PASS base=" + ACTIVE_GATE2_BASE
    main = tmp_path / "main.txt"
    records = []
    for name, path in sidecars.items():
        identity = evidence_verifier.file_identity(path)
        records.append(
            "SIDECAR "
            + json.dumps(
                {"name": name, **asdict(identity)},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    evidence_builder.write_exclusive(
        main,
        ("Evidence\n" + "\n".join(records) + "\n" + terminal + "\n").encode(),
    )
    statuses = {
        **{path: "A" for path in ACTIVE_GATE2_ADDED_PATHS},
        **{path: "M" for path in ACTIVE_GATE2_MODIFIED_PATHS},
        **{path: "D" for path in ACTIVE_GATE2_DELETED_PATHS},
    }
    result = evidence_verifier.verify_bundle(
        sidecars=sidecars,
        expected_hashes={
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sidecars.items()
        },
        root=REPO_ROOT,
        statuses=statuses,
        base=ACTIVE_GATE2_BASE,
        reviewed_tree=tree,
        main_evidence=main,
        expected_terminal=terminal,
    )
    assert result["result"] == "PASS"
    assert result["main_evidence"]["mode"] == "0644"


def test_evidence_verifier_rejects_missing_placeholder_malformed_and_duplicate_terminal(
    tmp_path: Path,
) -> None:
    sidecars = _bundle(tmp_path)
    with pytest.raises(
        evidence_verifier.EvidenceVerificationError, match="six-sidecar"
    ):
        evidence_verifier.verify_bundle(
            sidecars={k: v for k, v in sidecars.items() if k != "performance_results"}
        )
    main = tmp_path / "bad-main.txt"
    evidence_builder.write_exclusive(
        main,
        b"<placeholder>\nPIETTO_TEST_PASS x\nPIETTO_TEST_PASS x\n",
    )
    with pytest.raises(
        evidence_verifier.EvidenceVerificationError, match="placeholder"
    ):
        evidence_verifier.verify_bundle(
            sidecars=sidecars,
            main_evidence=main,
            expected_terminal="PIETTO_TEST_PASS x",
        )


def test_recovery_standard_contract_is_complete_and_fail_closed() -> None:
    text = (REPO_ROOT / RECOVERY_REL).read_text()
    for phrase in (
        "Gate 0 / Gate 1",
        "at most three mechanical corrections",
        "transcription-only correction",
        "Recovery 1 and Recovery 2",
        "PR CI Repair 1",
        "Main CI Repair 1",
        "Never manually dispatch, rerun, or cancel CI",
        "one no-state-change retry",
        "O_CREAT | O_EXCL | O_NOFOLLOW",
        "Force push, amend, rebase, direct-main push",
        "Hard STOP conditions",
    ):
        assert phrase in text


def test_lean_validation_standard_contract_preserves_all_quality_gates() -> None:
    text = " ".join((REPO_ROOT / LEAN_REL).read_text().split())
    for phrase in (
        "Freeze product scope before implementation",
        "unresolved dynamic reader is STOP",
        "exactly one topology node-ID registry",
        "complete content/reader closure once",
        "retain full PR CI and full main CI",
        "UV_OFFLINE=1",
        "scripts/validate.py` exactly once",
        "No assertion may become skipped, xfailed, deselected, or weakened",
        "exactly six deterministic sidecars",
    ):
        assert phrase in text


def test_agents_binding_is_narrow_and_no_product_surface_changed() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text()
    assert "## End-to-end Goal workflow binding" in agents
    assert RECOVERY_REL in agents and LEAN_REL in agents
    assert "unresolved dynamic reader is STOP" in agents
    assert not any(path.startswith("src/pietto/") for path in ALLOWLIST_PATHS)
    for path in ("pyproject.toml", "uv.lock", ".github/workflows/ci.yml"):
        assert path not in ALLOWLIST_PATHS


def test_interlude_contract_allowlist_legacy_equivalence_performance_and_next_state_are_exact() -> (
    None
):
    tree = ast.parse((REPO_ROOT / SELF_REL).read_text())
    names = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert names == EXPECTED_TEST_NAMES
    assert len(names) == 30
    assert set(ACTIVE_GATE2_ALLOWLIST_PATHS) == set(ALLOWLIST_PATHS)
    spec = " ".join((REPO_ROOT / SPEC_REL).read_text().split())
    for phrase in (
        "`A12_M51_D0`",
        "6,786 reader items",
        "1,143 pytest",
        "Four positive projections",
        "Twenty-four exact negative cases",
        "Legacy equivalence and performance",
        "PHASE54_SLICE7_GATE0_GATE1",
        "Slice 7 remains `UNSTARTED`",
    ):
        assert phrase in spec
