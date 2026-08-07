from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (
    PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice12_mechanical_repair3_clean_topic_is_active,
    phase54_slice12_product_repair3_clean_topic_is_active,
    phase54_slice12_product_repair10_clean_topic_is_active,
    phase54_slice12_product_repair11_clean_topic_is_active,
    phase54_slice12_product_repair12_clean_topic_is_active,
    phase54_slice12_product_repair13_clean_topic_is_active,
    phase54_slice12_product_repair14_clean_topic_is_active,
)

import pytest

from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.window_semantics import (
    WindowDependencyEdge,
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultProjectFact,
    build_window_result_project_fact,
    deduplicate_window_dependency_edges,
)
from pietto.ast_nodes import QueryDef, SourceDef, WindowExpr
from pietto.errors import SourceLocation
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_input_analysis import (
    WindowInputBinding,
    WindowInputOriginKind,
    WindowInputScope,
    WindowInputScopeKind,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = (
    "tests/"
    "test_phase53_grouped_result_ranking_aggregate_result_inputs_"
    "bounded_let_visibility_contract.py"
)
SPEC_REL = (
    "docs/spec/"
    "phase53-grouped-result-ranking-aggregate-result-inputs-"
    "bounded-let-visibility-contract-v1.md"
)
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
BASE_HEAD = "a5606761c040042d177874253e29c25f2e8e3fff"
PUBLISHED_SLICE13_HEAD = "933cf2f4ad0aab245feda09462178b90ebf9b7a6"
PUBLISHED_SLICE13_SUBJECT = "Add Phase 53 grouped-result window inputs."
CI_REPAIR_HEAD = "e2441308179d34a6806b61f533d5799b910fbbb0"
CI_REPAIR_SUBJECT = "Repair Phase 53 Slice 13 shallow CI history guard"
CI_REPAIR_MODIFIED_PATHS = (
    SELF_REL,
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
MAINTENANCE_SUBJECT = "Consolidate major Dependabot updates"
MAINTENANCE_CANDIDATE_HEAD = "7ad017fd96e4ebaf7290d3042d0538dcf925b267"
MAINTENANCE_REPAIR_SUBJECT = "Repair Dependabot CI topology guard"
MAINTENANCE_BRANCH_PREFIX = "maintenance/dependabot-"
SLICE15_PUBLISHED_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE16_SUBJECT = "Complete Phase 53 status and compatibility audit"
PHASE53_COMPLETION_HEAD = "af92f30c22e5d3df5219554a0663855a5b9f51a6"
PHASE54_SLICE1_HEAD = "53d8767fc3bdbe5e3f631178652222bbe51f6a33"
PHASE54_SLICE2_HEAD = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE3_HEAD = "2752985c3f6343519b7d7d6fe400d16251e64d85"
README_REFRESH_HEAD = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE4_HEAD = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE5_HEAD = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE6_HEAD = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE7_HEAD = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE8_HEAD = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE9_HEAD = "fadb1924af057cfc901a1658e117810d699e2358"
PHASE54_SLICE10_HEAD = "b81843acadb294630db361c09949868d004b1bca"
PHASE54_SLICE11_HEAD = "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
PHASE54_SLICE1_SUBJECT = "Add Phase 54 scope authority and expansion route lock"
PHASE54_SLICE2_SUBJECT = "Add Phase 54 schema v2 module activation carrier"
PHASE54_SLICE3_SUBJECT = "Add Phase 54 trusted module loading boundary"
README_REFRESH_SUBJECT = "Refresh Pietto README and roadmap overview"
PHASE54_SLICE4_SUBJECT = "Add Phase 54 import export grammar and AST"
PHASE54_SLICE4_BRANCH = "phase54/slice4-import-export-grammar-ast"
PHASE54_SLICE5_SUBJECT = "Add Phase 54 module declaration catalogs"
PHASE54_SLICE5_BRANCH = "phase54/slice5-module-declaration-catalogs"
PHASE54_SLICE6_SUBJECT = "Add Phase 54 module export surfaces"
PHASE54_SLICE6_BRANCH = "phase54/slice6-export-visibility-facade"
PHASE54_SLICE7_SUBJECT = "Add Phase 54 named import binding environments"
PHASE54_SLICE7_BRANCH = "phase54/slice7-named-import-binding-environments"
PHASE54_SLICE8_SUBJECT = "Add Phase 54 module graph and diagnostics"
PHASE54_SLICE8_BRANCH = "phase54/slice8-module-graph-cycles-diagnostics"
PHASE54_SLICE9_SUBJECT = "Add Phase 54 cross-module type and source resolution"
PHASE54_SLICE9_BRANCH = "phase54/slice9-cross-module-type-source-resolution"
PHASE54_SLICE10_SUBJECT = "Add Phase 54 cross-module relation and row facts"
PHASE54_SLICE10_BRANCH = "phase54/slice10-cross-module-relation-row-facts"
PHASE54_SLICE10_CANDIDATE_HEAD = "42b692d64dcbd9c4f8210accd0106dc11dcd3318"
PHASE54_SLICE10_PR_CI_REPAIR_SUBJECT = "Fix Phase 54 PR CI topology projection"
PHASE54_SLICE11_SUBJECT = "Add Phase 54 module attribution and lineage facts"
PHASE54_SLICE11_BRANCH = (
    "phase54/slice11-module-attribution-dependency-origin-provenance-lineage"
)
PHASE54_SLICE11_CANDIDATE_HEAD = "c6aba9522f7e16e358005f86cfb119dd6d005463"
PHASE54_SLICE11_PR_CI_REPAIR_SUBJECT = "Fix Phase 54 Slice 11 PR CI topology projection"
PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE = "691db405a7e787adec5d7bd0498330b070bf6b75"
PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_SUBJECT = (
    "Repair Phase 54 Slice 11 binding authority closure"
)
PHASE54_SLICE12_SUBJECT = "Add Phase 54 semantic fact preservation"
PHASE54_SLICE12_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_CANDIDATE_HEAD = "1c8a9ff9ce95563da0312dc640e6ac30248168e2"
PHASE54_SLICE12_PR_CI_REPAIR_SUBJECT = "Fix Phase 54 Slice 12 PR CI topology projection"
MAINTENANCE_MODIFIED_PATHS = (
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "uv.lock",
)

SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    category: Text nullable\n"
    "    amount: Int nullable\n"
    "    score: Float not null\n"
    "    exact: Decimal nullable\n"
    "    happened: Date nullable\n"
    'source rows: Row is postgres.table("rows")\n'
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _phase53_gate2_paths(name: str) -> set[str]:
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


def _phase54_gate2_paths(name: str) -> set[str]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }

    def resolve(node: ast.expr) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            return resolve(assignments[node.id])
        if isinstance(node, ast.Starred):
            return resolve(node.value)
        if isinstance(node, ast.Set):
            return set().union(*(resolve(element) for element in node.elts))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return resolve(node.left) | resolve(node.right)
        raise AssertionError(ast.dump(node))

    return resolve(assignments[name])


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _git_optional_ref(ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 1)
    assert result.stderr == ""
    output = result.stdout.strip()
    if result.returncode == 1:
        assert output == ""
        return None
    assert re.fullmatch(r"[0-9a-f]{40}", output)
    return output


def _commit_available_from_batch_output(commit: str, output: str) -> bool:
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    if output == f"{commit} commit\n":
        return True
    if output == f"{commit} missing\n":
        return False
    raise AssertionError(f"unexpected git object result: {output!r}")


def _git_commit_exists(commit: str) -> bool:
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        cwd=REPO_ROOT,
        check=True,
        input=f"{commit}\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return _commit_available_from_batch_output(commit, result.stdout)


def _historical_objects_available(
    *,
    published_available: bool,
    base_available: bool,
) -> bool:
    assert published_available == base_available
    return published_available


def _commit_parents_and_subject(commit: str) -> tuple[tuple[str, ...], str]:
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    header, separator, message = _git_output(["cat-file", "-p", commit]).partition(
        "\n\n"
    )
    assert separator == "\n\n"
    parents = tuple(
        line.removeprefix("parent ")
        for line in header.splitlines()
        if line.startswith("parent ")
    )
    assert parents
    assert all(re.fullmatch(r"[0-9a-f]{40}", parent) for parent in parents)
    subject = message.partition("\n")[0]
    assert subject
    return parents, subject


def _commit_parent_and_message(commit: str) -> tuple[str, str]:
    parents, subject = _commit_parents_and_subject(commit)
    assert len(parents) == 1
    return parents[0], subject


def _assert_main_refs(head: str) -> None:
    assert _git_output(["branch", "--show-current"]) == "main"
    assert _git_optional_ref("refs/heads/main") == head
    assert _git_optional_ref("refs/remotes/origin/main") == head


def _assert_clean_state(*, status: str, staged: str) -> None:
    assert status == ""
    assert staged == ""


def _assert_repair_dirty_state(*, status: str, staged: str) -> None:
    expected = {f" M {path}" for path in CI_REPAIR_MODIFIED_PATHS}
    lines = status.splitlines()
    assert len(lines) == len(expected)
    assert set(lines) == expected
    assert staged == ""


def _assert_maintenance_dirty_state(*, status: str, staged: str) -> None:
    expected = {f" M {path}" for path in MAINTENANCE_MODIFIED_PATHS}
    lines = status.splitlines()
    assert len(lines) == len(expected)
    assert set(lines) == expected
    assert staged == ""


def _assert_slice14_dirty_state(*, status: str, staged: str) -> None:
    modified = _phase53_gate2_paths("MODIFIED_PATHS")
    added = _phase53_gate2_paths("ADDED_PATHS")
    expected = {f" M {path}" for path in modified} | {f"?? {path}" for path in added}
    lines = status.splitlines()
    assert len(lines) == len(expected)
    assert set(lines) == expected
    assert staged == ""


def _assert_phase54_dirty_state(*, status: str, staged: str) -> None:
    modified = _phase54_gate2_paths("MODIFIED_PATHS")
    added = _phase54_gate2_paths("ADDED_PATHS")
    expected = {f" M {path}" for path in modified} | {f"?? {path}" for path in added}
    lines = status.splitlines()
    assert len(lines) == len(expected)
    assert set(lines) == expected
    assert staged == ""


def _assert_maintenance_base_refs() -> None:
    branch = _git_output(["branch", "--show-current"])
    assert branch == "main" or branch.startswith(MAINTENANCE_BRANCH_PREFIX)
    assert _git_optional_ref("refs/heads/main") == CI_REPAIR_HEAD
    assert _git_optional_ref("refs/remotes/origin/main") == CI_REPAIR_HEAD


def _github_pull_request_identity() -> tuple[str, str] | None:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    assert event_path
    payload = cast(
        dict[str, object],
        json.loads(Path(event_path).read_text(encoding="utf-8")),
    )
    pull_request = cast(dict[str, object], payload["pull_request"])
    base = cast(dict[str, object], pull_request["base"])
    candidate = cast(dict[str, object], pull_request["head"])
    base_sha = cast(str, base["sha"])
    candidate_sha = cast(str, candidate["sha"])
    assert re.fullmatch(r"[0-9a-f]{40}", base_sha)
    assert re.fullmatch(r"[0-9a-f]{40}", candidate_sha)
    return base_sha, candidate_sha


def _github_pull_request_refs() -> tuple[str, str] | None:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    assert event_path
    payload = cast(
        dict[str, object],
        json.loads(Path(event_path).read_text(encoding="utf-8")),
    )
    pull_request = cast(dict[str, object], payload["pull_request"])
    base = cast(dict[str, object], pull_request["base"])
    candidate = cast(dict[str, object], pull_request["head"])
    base_ref = base.get("ref")
    candidate_ref = candidate.get("ref")
    return (
        base_ref if isinstance(base_ref, str) else "",
        candidate_ref if isinstance(candidate_ref, str) else "",
    )


def _assert_maintenance_candidate_shape(
    *,
    parents: tuple[str, ...],
    subject: str,
) -> None:
    if parents == (CI_REPAIR_HEAD,):
        assert subject == MAINTENANCE_SUBJECT
        return
    assert parents == (MAINTENANCE_CANDIDATE_HEAD,)
    assert subject == MAINTENANCE_REPAIR_SUBJECT
    if _git_commit_exists(MAINTENANCE_CANDIDATE_HEAD):
        parent, candidate_subject = _commit_parent_and_message(
            MAINTENANCE_CANDIDATE_HEAD
        )
        assert parent == CI_REPAIR_HEAD
        assert candidate_subject == MAINTENANCE_SUBJECT


def _is_phase54_subject(subject: str, expected: str) -> bool:
    return (
        subject == expected
        or re.fullmatch(rf"{re.escape(expected)} \(#[0-9]+\)", subject) is not None
    )


def _assert_published_slice13_identity() -> None:
    assert _git_commit_exists(PUBLISHED_SLICE13_HEAD)
    assert _git_commit_exists(BASE_HEAD)
    parent, message = _commit_parent_and_message(PUBLISHED_SLICE13_HEAD)
    assert parent == BASE_HEAD
    assert message == PUBLISHED_SLICE13_SUBJECT
    assert _git_output(["rev-parse", f"{PUBLISHED_SLICE13_HEAD}^"]) == BASE_HEAD
    assert (
        _git_output(["rev-list", "--count", f"{BASE_HEAD}..{PUBLISHED_SLICE13_HEAD}"])
        == "1"
    )


def _is_clean_projection() -> bool:
    head = _git_output(["rev-parse", "HEAD"])
    status = _git_output(["status", "--porcelain=v1", "--untracked-files=all"])
    staged = _git_output(["diff", "--cached", "--name-only"])
    shallow = _git_output(["rev-parse", "--is-shallow-repository"])
    if (
        phase54_slice12_mechanical_repair3_clean_topic_is_active()
        or phase54_slice12_product_repair10_clean_topic_is_active()
        or phase54_slice12_product_repair11_clean_topic_is_active()
        or phase54_slice12_product_repair12_clean_topic_is_active()
        or phase54_slice12_product_repair13_clean_topic_is_active()
        or phase54_slice12_product_repair14_clean_topic_is_active()
        or phase54_slice12_product_repair3_clean_topic_is_active()
    ):
        assert status == staged == ""
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE12_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE11_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE11_HEAD
        return True
    if _phase54_active_gate2_is_active():
        assert status
        assert staged == ""
        assert shallow == "false"
        return False
    if head == SLICE15_PUBLISHED_HEAD:
        _assert_main_refs(head)
        assert shallow == "false"
        _assert_slice14_dirty_state(status=status, staged=staged)
        return False

    if head == BASE_HEAD:
        _assert_main_refs(head)
        assert shallow == "false"
        assert status
        assert staged == ""
        return False

    if head == PUBLISHED_SLICE13_HEAD:
        _assert_main_refs(head)
        assert shallow == "false"
        _assert_published_slice13_identity()
        if status:
            _assert_repair_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    if head == CI_REPAIR_HEAD:
        parent, message = _commit_parent_and_message(head)
        assert parent == PUBLISHED_SLICE13_HEAD
        assert message == CI_REPAIR_SUBJECT
        _assert_maintenance_base_refs()
        if status:
            _assert_maintenance_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    pull_request_identity = _github_pull_request_identity()
    pull_request_refs = _github_pull_request_refs()
    parents, subject = _commit_parents_and_subject(head)
    if parents == (SLICE15_PUBLISHED_HEAD,) and subject == SLICE16_SUBJECT:
        if status:
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == SLICE15_PUBLISHED_HEAD
            assert candidate_sha == head
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE53_COMPLETION_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE1_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE1_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE53_COMPLETION_HEAD
            assert candidate_sha == head
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE1_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE2_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE2_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE1_HEAD
            assert candidate_sha == head
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE2_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE3_SUBJECT,
    ):
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE2_HEAD
            assert candidate_sha == head
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE3_HEAD,) and _is_phase54_subject(
        subject,
        README_REFRESH_SUBJECT,
    ):
        if status:
            assert head == README_REFRESH_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE3_HEAD
            assert candidate_sha == head
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (README_REFRESH_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE4_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE4_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == README_REFRESH_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE4_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE4_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE5_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE5_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE4_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE5_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE5_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE4_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE4_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE5_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE6_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE6_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE5_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE6_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE6_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE5_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE5_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE6_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE7_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE7_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE6_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE7_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE7_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE6_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE6_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE7_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE8_SUBJECT,
    ):
        if status:
            assert head == PHASE54_SLICE8_HEAD
            assert shallow == "false"
            _assert_main_refs(head)
            _assert_phase54_dirty_state(status=status, staged=staged)
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE7_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE8_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE8_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE7_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE7_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE8_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE9_SUBJECT,
    ):
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE8_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE9_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE9_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE8_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE8_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE9_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE10_SUBJECT,
    ):
        if status:
            assert shallow == "false"
            assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE10_BRANCH
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE9_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE9_HEAD
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE9_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE10_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE10_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE9_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE9_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE10_CANDIDATE_HEAD,) and (
        subject == PHASE54_SLICE10_PR_CI_REPAIR_SUBJECT
    ):
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE10_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE9_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE9_HEAD
        if status:
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    if parents == (PHASE54_SLICE10_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE11_SUBJECT,
    ):
        if status:
            assert shallow == "false"
            assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE11_BRANCH
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE10_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE10_HEAD
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE10_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE11_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE11_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE10_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE10_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE11_CANDIDATE_HEAD,) and (
        subject == PHASE54_SLICE11_PR_CI_REPAIR_SUBJECT
    ):
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE11_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE10_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE10_HEAD
        if status:
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    if parents == (PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE,) and (
        subject == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_SUBJECT
    ):
        if status:
            assert shallow == "false"
            assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE11_BRANCH
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE10_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE10_HEAD
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE10_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE11_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE11_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE10_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE10_HEAD
        return True

    if parents == (PHASE54_SLICE10_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_SUBJECT,
    ):
        _assert_clean_state(status=status, staged=staged)
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert pull_request_identity is None
        assert shallow == "false"
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE11_HEAD,) and _is_phase54_subject(
        subject,
        PHASE54_SLICE12_SUBJECT,
    ):
        if status:
            assert shallow == "false"
            assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE12_BRANCH
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE11_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE11_HEAD
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        if pull_request_identity is not None:
            base_sha, candidate_sha = pull_request_identity
            assert shallow == "true"
            assert base_sha == PHASE54_SLICE11_HEAD
            assert candidate_sha == head
            assert pull_request_refs == ("main", PHASE54_SLICE12_BRANCH)
            return True
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert shallow == "true"
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
            assert os.environ.get("GITHUB_SHA") == head
            assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
            return True
        assert shallow == "false"
        branch = _git_output(["branch", "--show-current"])
        if branch == PHASE54_SLICE12_BRANCH:
            assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE11_HEAD
            assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE11_HEAD
            return True
        _assert_main_refs(head)
        return True

    if parents == (PHASE54_SLICE12_CANDIDATE_HEAD,) and (
        subject == PHASE54_SLICE12_PR_CI_REPAIR_SUBJECT
    ):
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE12_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE11_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE11_HEAD
        if status:
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    if parents == (PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,) and (
        subject == PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT
    ):
        assert shallow == "false"
        assert _git_output(["branch", "--show-current"]) == PHASE54_SLICE12_BRANCH
        assert _git_optional_ref("refs/heads/main") == PHASE54_SLICE11_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == PHASE54_SLICE11_HEAD
        if status:
            assert staged == ""
            return False
        _assert_clean_state(status=status, staged=staged)
        return True

    if pull_request_identity is not None:
        base_sha, candidate_sha = pull_request_identity
        assert shallow == "true"
        assert pull_request_refs is not None
        base_ref, candidate_ref = pull_request_refs
        if base_sha == README_REFRESH_HEAD or candidate_ref == PHASE54_SLICE4_BRANCH:
            assert base_sha == README_REFRESH_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE4_BRANCH
            assert head != candidate_sha
            assert parents == (README_REFRESH_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE4_HEAD or candidate_ref == PHASE54_SLICE5_BRANCH:
            assert base_sha == PHASE54_SLICE4_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE5_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE4_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE5_HEAD or candidate_ref == PHASE54_SLICE6_BRANCH:
            assert base_sha == PHASE54_SLICE5_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE6_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE5_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE6_HEAD or candidate_ref == PHASE54_SLICE7_BRANCH:
            assert base_sha == PHASE54_SLICE6_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE7_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE6_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE7_HEAD or candidate_ref == PHASE54_SLICE8_BRANCH:
            assert base_sha == PHASE54_SLICE7_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE8_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE7_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE8_HEAD or candidate_ref == PHASE54_SLICE9_BRANCH:
            assert base_sha == PHASE54_SLICE8_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE9_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE8_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE9_HEAD or candidate_ref == PHASE54_SLICE10_BRANCH:
            assert base_sha == PHASE54_SLICE9_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE10_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE9_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE10_HEAD or candidate_ref == PHASE54_SLICE11_BRANCH:
            assert base_sha == PHASE54_SLICE10_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE11_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE10_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        if base_sha == PHASE54_SLICE11_HEAD or candidate_ref == PHASE54_SLICE12_BRANCH:
            assert base_sha == PHASE54_SLICE11_HEAD
            assert base_ref == "main"
            assert candidate_ref == PHASE54_SLICE12_BRANCH
            assert head != candidate_sha
            assert parents == (PHASE54_SLICE11_HEAD, candidate_sha)
            _assert_clean_state(status=status, staged=staged)
            return True
        assert base_sha in (
            CI_REPAIR_HEAD,
            SLICE15_PUBLISHED_HEAD,
            PHASE53_COMPLETION_HEAD,
            PHASE54_SLICE1_HEAD,
            PHASE54_SLICE2_HEAD,
            PHASE54_SLICE3_HEAD,
            README_REFRESH_HEAD,
            PHASE54_SLICE4_HEAD,
            PHASE54_SLICE5_HEAD,
            PHASE54_SLICE6_HEAD,
            PHASE54_SLICE7_HEAD,
            PHASE54_SLICE8_HEAD,
        )
        _assert_clean_state(status=status, staged=staged)
        if head == candidate_sha:
            _assert_maintenance_candidate_shape(parents=parents, subject=subject)
        else:
            assert parents == (base_sha, candidate_sha)
        return True

    _assert_maintenance_candidate_shape(parents=parents, subject=subject)
    _assert_clean_state(status=status, staged=staged)
    branch = _git_output(["branch", "--show-current"])
    if branch == "main":
        assert _git_optional_ref("refs/heads/main") == head
        assert _git_optional_ref("refs/remotes/origin/main") in (None, head)
        assert os.environ.get("GITHUB_EVENT_NAME") in (None, "push")
        if os.environ.get("GITHUB_EVENT_NAME") == "push":
            assert os.environ.get("GITHUB_SHA") == head
            assert os.environ.get("GITHUB_REF") == "refs/heads/main"
    else:
        assert shallow == "false"
        assert branch.startswith(MAINTENANCE_BRANCH_PREFIX)
        assert _git_optional_ref("refs/heads/main") == CI_REPAIR_HEAD
        assert _git_optional_ref("refs/remotes/origin/main") == CI_REPAIR_HEAD
    return True


def _window_call(case: int) -> str:
    return (
        "row_number()",
        "rank()",
        "dense_rank()",
        "percent_rank()",
        "cume_dist()",
        "ntile(3)",
        "lag(total)",
        "lead(group_name, 0, group_name)",
    )[case % 8]


def _grouped_source(
    case: int = 0,
    *,
    partition: str = "group_name",
    order: str = "total",
    window_call: str | None = None,
    second_window: bool = False,
    satisfying: bool = False,
) -> str:
    selected = (
        "        group_name = category\n"
        "        total = sum(amount)\n"
        f"        window_value = {window_call or _window_call(case)} window:\n"
        "            partition by:\n"
        f"                {partition}\n"
        "            order by:\n"
        f"                {order}\n"
    )
    if second_window:
        selected += (
            "        second_window = rank() window:\n"
            "            order by:\n"
            "                total\n"
        )
    suffix = "    satisfying:\n        total > 0\n" if satisfying else ""
    return (
        SOURCE_PREFIX + "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        category\n"
        "    select:\n" + selected + suffix
    )


def _ungrouped_let_source(case: int = 0) -> str:
    call = "lag(chain, 0, direct)" if case % 2 else "row_number()"
    return (
        SOURCE_PREFIX + "query local_window:\n"
        "    from rows\n"
        "    let:\n"
        "        direct = category\n"
        "        qualified = rows.amount\n"
        "        chain = direct\n"
        "    select:\n"
        f"        window_value = {call} window:\n"
        "            partition by:\n"
        "                chain\n"
        "            order by:\n"
        "                direct\n"
    )


def _grouped_let_source(case: int = 0) -> str:
    call = "lag(total)" if case % 2 else "rank()"
    return (
        SOURCE_PREFIX + "query grouped_let:\n"
        "    from rows\n"
        "    let:\n"
        "        key = category\n"
        "        chain = key\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        group_name = category\n"
        "        total = count()\n"
        f"        window_value = {call} window:\n"
        "            partition by:\n"
        "                chain\n"
        "            order by:\n"
        "                total\n"
    )


@lru_cache(maxsize=None)
def _diagnostics(source: str) -> tuple[str, ...]:
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    return tuple(item.code for item in analyze(parsed.ast).diagnostics)


def _assert_grouped_success(case: int) -> None:
    source = _grouped_source(case)
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert result.diagnostics == ()
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    schema = result.model.relation_row_schemas[relation]
    assert tuple(schema.fields) == ("group_name", "total", "window_value")
    assert type(relation.select_items[-1].expression) is WindowExpr


def _assert_negative(case: int) -> None:
    variant = case % 8
    if variant == 0:
        source = (
            SOURCE_PREFIX + "query mixed:\n"
            "    from rows\n"
            "    select:\n"
            "        total = count()\n"
            "        w = row_number() window:\n"
            "            order by:\n"
            "                id\n"
        )
        assert "PIE-S2312" in _diagnostics(source)
        return
    if variant == 1:
        source = _grouped_source(partition="category")
        assert "PIE-S2102" in _diagnostics(source)
        return
    if variant == 2:
        source = _grouped_source(partition="grouped.group_name")
        assert "PIE-S2102" in _diagnostics(source)
        return
    if variant == 3:
        source = _grouped_source(partition="group_name + group_name")
        assert "PIE-S2103" in _diagnostics(source)
        return
    if variant == 4:
        source = _grouped_source(window_call="lag(sum(amount))")
        assert "PIE-S2104" in _diagnostics(source)
        return
    if variant == 5:
        source = _grouped_source(second_window=True)
        assert _diagnostics(source) == ()
        return
    if variant == 6:
        source = _grouped_source(order="category")
        assert "PIE-S2102" in _diagnostics(source)
        return
    source = _grouped_source(window_call="lag(group_name + group_name)")
    assert "PIE-S2104" in _diagnostics(source)


def _assert_ungrouped_let_success(case: int) -> None:
    assert _diagnostics(_ungrouped_let_source(case)) == ()


def _assert_grouped_let_success(case: int) -> None:
    assert _diagnostics(_grouped_let_source(case)) == ()


def _project_schema() -> ProjectRowSchema:
    definitions = (
        ("id", "Int", ProjectRowFieldNullability.NON_NULL),
        ("category", "Text", ProjectRowFieldNullability.NULLABLE),
        ("amount", "Int", ProjectRowFieldNullability.NULLABLE),
        ("score", "Float", ProjectRowFieldNullability.NON_NULL),
        ("exact", "Decimal", ProjectRowFieldNullability.NULLABLE),
        ("happened", "Date", ProjectRowFieldNullability.NULLABLE),
    )
    return ProjectRowSchema(
        fields={
            name: ProjectRowField(
                name=name,
                resolved_type=ProjectResolvedType(
                    name=type_name,
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=nullability,
            )
            for name, type_name, nullability in definitions
        }
    )


@lru_cache(maxsize=None)
def _project_fact(grouped: bool, use_let: bool = False) -> WindowResultProjectFact:
    source = (
        _grouped_let_source(1)
        if grouped and use_let
        else _grouped_source(
            window_call="lag(total, 0, total)",
            partition="group_name",
        )
        if grouped
        else _ungrouped_let_source(1)
    )
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    source_definition = cast(SourceDef, parsed.ast.definitions[-2])
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.SOURCE,
        name="rows",
        path="slice13.pietto",
        location=SourceLocation(path="slice13.pietto", line=1, column=1),
        definition=source_definition,
    )
    let_value_types: dict[str, ValueType] | None = None
    let_expressions = None
    if relation.let_clause is not None:
        let_value_types = {
            binding.name: ValueType(
                resolved_type=ResolvedType(name="Text", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NULLABLE,
            )
            for binding in relation.let_clause.bindings
        }
        let_expressions = {
            binding.name: binding.expression for binding in relation.let_clause.bindings
        }
    result = build_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice13.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    assert type(result) is WindowResultProjectFact
    return result


def _node(kind: ProjectRowDependencyNodeKind) -> ProjectRowDependencyNode:
    if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="group_name",
            relation_name="grouped",
            output_name="group_name",
        )
    if kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="rows.category",
            relation_name="rows",
            source_name="rows",
            field_name="category",
        )
    if kind is ProjectRowDependencyNodeKind.LET_BINDING:
        return ProjectRowDependencyNode(
            kind=kind,
            name="key",
            relation_name="grouped",
            binding_name="key",
        )
    return ProjectRowDependencyNode(
        kind=kind,
        name="rows",
        relation_name="rows",
        source_name="rows",
    )


def _location() -> SourceLocation:
    return SourceLocation(path="slice13.pietto", line=1, column=1)


def _assert_project_roles(grouped: bool, use_let: bool = False) -> None:
    fact = _project_fact(grouped, use_let)
    if grouped:
        assert all(
            item.target.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
            for item in fact.dependency_occurrences
        )
        assert all(
            item.target_result_role is not None for item in fact.dependency_occurrences
        )
    else:
        assert all(
            item.target.kind is ProjectRowDependencyNodeKind.LET_BINDING
            for item in fact.dependency_occurrences
        )
        assert all(
            item.target_result_role is None for item in fact.dependency_occurrences
        )


def test_slice13_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    docs = _read(SPEC_REL)
    assert docs.startswith("# Phase 53 Grouped-result Ranking")
    assert "Gate 3 requires separate authorization" in docs
    assert "A3/M68/D0" in docs


def test_reconciled_main_maintenance_handoff_and_build_backend_are_locked() -> None:
    _is_clean_projection()
    assert _commit_available_from_batch_output(BASE_HEAD, f"{BASE_HEAD} commit\n")
    assert not _commit_available_from_batch_output(BASE_HEAD, f"{BASE_HEAD} missing\n")
    with pytest.raises(AssertionError):
        _commit_available_from_batch_output(BASE_HEAD, f"{BASE_HEAD} blob\n")
    with pytest.raises(AssertionError):
        _historical_objects_available(
            published_available=True,
            base_available=False,
        )
    pyproject = _read("pyproject.toml")
    assert 'requires = ["uv_build>=0.11.32,<0.12.0"]' in pyproject


def test_slice13_contract_scope_and_group_to_window_ownership_are_exact() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for value in ("GROUP / aggregate / satisfying", "-> WINDOW", "PIE-S2312"):
        assert value in docs


def test_window_input_scope_carrier_shape_privacy_and_failure_rules_are_exact() -> None:
    assert dataclasses.is_dataclass(WindowInputBinding)
    assert dataclasses.is_dataclass(WindowInputScope)
    assert tuple(WindowInputScopeKind) == (
        WindowInputScopeKind.ROW,
        WindowInputScopeKind.GROUPED_RESULT,
    )
    assert tuple(WindowInputOriginKind) == (
        WindowInputOriginKind.UPSTREAM_FIELD,
        WindowInputOriginKind.LET_BINDING,
        WindowInputOriginKind.GROUP_KEY,
        WindowInputOriginKind.AGGREGATE_RESULT,
    )


@pytest.mark.parametrize("case", range(4))
def test_grouped_schema_skips_exact_window_output_without_publishing_it(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(6))
def test_grouped_scope_preserves_selected_output_source_order_and_roles(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(4))
def test_grouped_scope_duplicate_output_names_have_no_winner(case: int) -> None:
    source = _grouped_source(second_window=True).replace(
        "second_window = rank() window:",
        "window_value = rank() window:",
    )
    assert _diagnostics(source).count("PIE-S2305") == 1


@pytest.mark.parametrize("case", range(6))
def test_grouped_scope_invalid_nonwindow_outputs_do_not_become_inputs(
    case: int,
) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(8))
def test_no_group_aggregate_window_mix_remains_rejected(case: int) -> None:
    _assert_negative(0)


@pytest.mark.parametrize("case", range(4))
def test_valid_satisfying_clause_precedes_window_without_becoming_input(
    case: int,
) -> None:
    assert _diagnostics(_grouped_source(case, satisfying=True)) == ()


def test_window_call_in_satisfying_remains_rejected() -> None:
    assert "satisfying" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(8))
def test_maximum_one_window_output_remains_exact(case: int) -> None:
    source = _grouped_source(case, second_window=True)
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert result.diagnostics == ()
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    assert tuple(result.model.relation_row_schemas[relation].fields)[-2:] == (
        "window_value",
        "second_window",
    )


@pytest.mark.parametrize("case", range(8))
def test_all_completed_window_identities_reuse_existing_dispatch(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(6))
def test_ranking_distribution_signature_and_result_identity_are_unchanged(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(4))
def test_navigation_signature_and_nullability_formula_objects_are_reused(
    case: int,
) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_group_key_input_type_and_nullability_are_preserved(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(18))
def test_aggregate_result_input_type_and_nullability_matrix_is_exact(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(24))
def test_navigation_aggregate_value_default_exact_type_matrix(case: int) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_navigation_aggregate_input_nullability_matrix_is_exact(case: int) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_navigation_offset_zero_and_boundary_rules_survive_grouped_inputs(
    case: int,
) -> None:
    _assert_grouped_success(7)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_accepts_selected_group_key_outputs(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_accepts_selected_aggregate_outputs(case: int) -> None:
    assert _diagnostics(_grouped_source(case, partition="total")) == ()


@pytest.mark.parametrize("case", range(16))
def test_grouped_order_accepts_selected_group_key_outputs(case: int) -> None:
    assert _diagnostics(_grouped_source(case, order="group_name")) == ()


@pytest.mark.parametrize("case", range(16))
def test_grouped_order_accepts_selected_aggregate_outputs(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_and_order_preserve_duplicate_occurrences_and_bindings(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(12))
def test_grouped_result_names_are_bare_only(case: int) -> None:
    _assert_negative(2)


@pytest.mark.parametrize("case", range(12))
def test_unselected_group_keys_and_raw_input_fields_are_rejected(case: int) -> None:
    _assert_negative(1)


@pytest.mark.parametrize("case", range(12))
def test_inline_aggregate_and_computed_window_inputs_are_rejected(case: int) -> None:
    _assert_negative(4 if case % 2 else 7)


@pytest.mark.parametrize("case", range(8))
def test_unknown_or_nonconcrete_grouped_results_fail_closed(case: int) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(12))
def test_mandatory_order_and_direction_diagnostics_remain_exact(case: int) -> None:
    _assert_negative(6)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_partition(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_order(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(12))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_navigation(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case | 1)


@pytest.mark.parametrize("case", range(10))
def test_ungrouped_computed_literal_and_qualified_let_forms_remain_rejected(
    case: int,
) -> None:
    assert "Computed, literal" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(12))
def test_grouped_direct_and_chained_field_lets_match_selected_group_key_outputs(
    case: int,
) -> None:
    _assert_grouped_let_success(case)


@pytest.mark.parametrize("case", range(6))
def test_grouped_let_match_uses_selected_output_alias_type_and_nullability(
    case: int,
) -> None:
    _assert_grouped_let_success(case)


@pytest.mark.parametrize("case", range(12))
def test_grouped_unselected_field_computed_literal_and_aggregate_lets_are_rejected(
    case: int,
) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(8))
def test_let_visibility_preserves_input_field_priority_and_source_order(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(8))
def test_invalid_shadow_forward_self_and_duplicate_lets_fail_closed(case: int) -> None:
    assert "shadowed, forward, self, duplicate" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(6))
def test_let_presence_without_window_reference_does_not_block_valid_window(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(20))
def test_same_select_window_alias_inputs_are_rejected_in_every_role(case: int) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(8))
def test_nested_window_forms_remain_structurally_unrepresentable(case: int) -> None:
    assert "nesting" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(5))
def test_windows_in_where_group_aggregate_let_and_satisfying_remain_rejected(
    case: int,
) -> None:
    assert "windows in `where`" in _read(SPEC_REL)


def test_aggregate_as_window_frames_named_windows_and_qualify_remain_absent() -> None:
    docs = _read(SPEC_REL)
    for value in ("aggregate-as-window", "frames", "named windows", "`QUALIFY`"):
        assert value in docs


@pytest.mark.parametrize("case", range(12))
def test_window_dependency_target_result_role_matrix_is_exact(case: int) -> None:
    kinds = tuple(ProjectRowDependencyNodeKind)
    kind = kinds[case % len(kinds)]
    role = (
        ProjectRowResultRole.GROUP_KEY
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD and case % 2 == 0
        else ProjectRowResultRole.AGGREGATE_RESULT
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
        else None
    )
    occurrence = WindowDependencyOccurrence(
        global_ordinal=0,
        role_ordinal=0,
        role=(
            WindowDependencyRole.RELATION_INPUT
            if kind is ProjectRowDependencyNodeKind.RELATION_INPUT
            else WindowDependencyRole.WINDOW_ORDER
        ),
        target=_node(kind),
        location=_location(),
        target_result_role=role,
    )
    edge = WindowDependencyEdge(
        role=occurrence.role,
        target=occurrence.target,
        target_result_role=role,
    )
    assert edge.target_result_role is role


@pytest.mark.parametrize("case", range(20))
def test_window_dependency_target_result_role_negative_matrix_fails_closed(
    case: int,
) -> None:
    kind = (
        ProjectRowDependencyNodeKind.OUTPUT_FIELD
        if case % 2 == 0
        else ProjectRowDependencyNodeKind.UPSTREAM_FIELD
    )
    invalid_role = (
        None
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
        else ProjectRowResultRole.WINDOW_RESULT
    )
    with pytest.raises(ValueError):
        WindowDependencyEdge(
            role=WindowDependencyRole.WINDOW_ORDER,
            target=_node(kind),
            target_result_role=invalid_role,
        )


@pytest.mark.parametrize("case", range(10))
def test_grouped_group_key_and_aggregate_occurrences_use_output_field_targets(
    case: int,
) -> None:
    _assert_project_roles(True)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_let_occurrences_use_let_binding_targets(case: int) -> None:
    _assert_project_roles(False)


@pytest.mark.parametrize("case", range(6))
def test_grouped_matching_let_occurrences_use_group_key_output_targets(
    case: int,
) -> None:
    _assert_project_roles(True, True)


@pytest.mark.parametrize("case", range(6))
def test_dependency_role_block_global_and_local_ordinals_are_exact(case: int) -> None:
    fact = _project_fact(bool(case % 2))
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(fact.dependency_occurrences))
    )


@pytest.mark.parametrize("case", range(8))
def test_dependency_edges_keep_first_role_target_dedup(case: int) -> None:
    occurrence = WindowDependencyOccurrence(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ORDER,
        target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
        location=_location(),
        target_result_role=ProjectRowResultRole.GROUP_KEY,
    )
    duplicate = dataclasses.replace(occurrence, global_ordinal=1, role_ordinal=1)
    assert len(deduplicate_window_dependency_edges((occurrence, duplicate))) == 1


@pytest.mark.parametrize("case", range(8))
def test_relation_input_fallback_and_argument_suppression_are_unchanged(
    case: int,
) -> None:
    fact = _project_fact(True)
    assert all(
        item.role is not WindowDependencyRole.RELATION_INPUT
        for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(4))
def test_window_result_identity_and_derived_provenance_are_unchanged(case: int) -> None:
    fact = _project_fact(bool(case % 2))
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind.value == "derived_expression"


@pytest.mark.parametrize("case", range(4))
def test_grouped_window_fact_is_transient_and_project_state_stays_nonconcrete(
    case: int,
) -> None:
    _assert_project_roles(True, bool(case % 2))


def test_no_window_schema_graph_lineage_or_model_persistence_is_added() -> None:
    assert (
        _git_output(["diff", "--name-only", "--", "src/pietto/semantic/model.py"]) == ""
    )
    graph_source = _read("src/pietto/_project/row_dependency_graph.py")
    lineage_source = _read("src/pietto/_project/row_lineage.py")
    model_source = _read("src/pietto/_project/model.py")
    assert 'WINDOW_ORDER = "window_order"' in graph_source
    assert 'WINDOW_ORDER = "window_order"' in lineage_source
    assert "relation_window_result_facts" in model_source


@pytest.mark.parametrize("case", range(16))
def test_ir_sql_backend_public_serializer_package_and_version_surfaces_are_locked(
    case: int,
) -> None:
    protected = (
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/__init__.py",
        "src/pietto/cli.py",
        "pyproject.toml",
        "uv.lock",
    )
    assert _git_output(["diff", "--name-only", "--", *protected]) == ""


@pytest.mark.parametrize("case", range(12))
def test_previous_slice_behavior_and_diagnostic_inventory_are_locked(case: int) -> None:
    _assert_grouped_success(case)


def test_reader_hash_inventory_and_nested_closure_is_exact() -> None:
    changed = set(_git_output(["status", "--short"]).splitlines())
    assert bool(changed) is not _is_clean_projection()
    assert _git_output(["diff", "--cached", "--name-only"]) == ""


def test_slice13_dirty_clean_depth_one_and_manifest_states_are_locked() -> None:
    _is_clean_projection()
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    if origin_main is not None:
        assert _git_output(["rev-list", "--count", f"HEAD..{origin_main}"]) == "0"
    else:
        assert _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
        assert _github_pull_request_identity() is not None or (
            os.environ.get("GITHUB_EVENT_NAME") == "push"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and os.environ.get("GITHUB_SHA") == _git_output(["rev-parse", "HEAD"])
        )
    assert _git_output(["diff", "--cached", "--name-status"]) == ""


def test_test_inventory_focused_selector_dirty_overlay_validation_and_gate3_are_exact() -> (
    None
):
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
    cardinalities: list[int] = []
    for function in functions:
        cardinality = 1
        for decorator in function.decorator_list:
            if not isinstance(decorator, ast.Call) or len(decorator.args) < 2:
                continue
            if not (
                isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                continue
            values = decorator.args[1]
            assert isinstance(values, ast.Call)
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    payload = "".join(
        f"{function.name}|{count}\n"
        for function, count in zip(functions, cardinalities, strict=True)
    ).encode()
    assert len(functions) == 60
    assert sum(cardinalities) == 489
    assert hashlib.sha256(payload).hexdigest() == (
        "700e592535cb4fd3b96351d677dcb596c943702d994b481c2d6062d5374ebf92"
    )
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for value in ("4050 focused", "9884", "185", "10069", "69 paths", "Gate 3"):
        assert value in docs
