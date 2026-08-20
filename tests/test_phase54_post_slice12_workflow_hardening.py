from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import _pietto_publication_topology as topology


SUBJECT = "Generic direct-main publication candidate"
_ACTIVE_OPERATION_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "REBASE_HEAD",
    "rebase-merge",
    "rebase-apply",
)


def _git(
    root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )


def _git_path(root: Path, relative: str) -> Path:
    path = Path(_git(root, "rev-parse", "--git-path", relative).stdout.strip())
    return path if path.is_absolute() else root / path


def _assert_no_active_git_operation(root: Path) -> None:
    assert not any(
        _git_path(root, marker).exists() for marker in _ACTIVE_OPERATION_MARKERS
    )


@pytest.fixture(scope="module")
def direct_main_lifecycle(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, topology.TopologyFixture], str, str]:
    root = tmp_path_factory.mktemp("direct-main-publication")
    source = root / "source"
    baseline = topology._init_base(source)
    topology._apply_candidate(source, None, topology._SYNTHETIC_CANDIDATE)
    tree = topology._working_tree_candidate_tree(source)
    fixtures = topology.build_direct_main_all(
        root / "projections",
        sealed_baseline=baseline,
        sealed_tree=tree,
        subject=SUBJECT,
        trailer=None,
        source=source,
    )
    assert topology.direct_main_sequence_is_complete(
        tuple(fixture.kind for fixture in fixtures)
    )
    return {fixture.kind: fixture for fixture in fixtures}, baseline, tree


def test_dirty_local_gate2_candidate_has_empty_index_and_no_active_operation(
    direct_main_lifecycle: tuple[dict[str, topology.TopologyFixture], str, str],
) -> None:
    fixtures, baseline, _ = direct_main_lifecycle
    fixture = fixtures[topology.TOPOLOGY_DIRECT_MAIN_DIRTY_CANDIDATE]
    topology.assert_topology(fixture)

    assert fixture.observation.head == baseline
    assert fixture.observation.staged_paths == ()
    assert any(
        (
            fixture.observation.added_paths,
            fixture.observation.modified_paths,
            fixture.observation.deleted_paths,
        )
    )
    assert (
        _git(fixture.root, "diff", "--cached", "--quiet", check=False).returncode == 0
    )
    _assert_no_active_git_operation(fixture.root)


def test_clean_direct_main_pre_push_uses_one_parent_and_coherent_main_refs(
    direct_main_lifecycle: tuple[dict[str, topology.TopologyFixture], str, str],
) -> None:
    fixtures, baseline, tree = direct_main_lifecycle
    fixture = fixtures[topology.TOPOLOGY_DIRECT_MAIN_PRE_PUSH]
    observation = fixture.observation
    topology.assert_topology(fixture)

    assert observation.branch == topology.MAIN_BRANCH
    assert observation.head_tree == tree
    assert observation.head_parents == (baseline,)
    assert observation.head_subject == SUBJECT
    assert observation.head_trailer == ""
    assert observation.upstream == "origin/main"
    assert observation.origin_main == baseline
    assert not any(
        (
            observation.added_paths,
            observation.modified_paths,
            observation.deleted_paths,
            observation.staged_paths,
        )
    )
    assert (
        _git(fixture.root, "rev-parse", "refs/heads/main").stdout.strip()
        == observation.head
    )
    assert (
        _git(fixture.root, "rev-parse", "refs/remotes/origin/main").stdout.strip()
        == baseline
    )
    _assert_no_active_git_operation(fixture.root)


def test_fresh_depth_one_pushed_head_has_only_the_declared_commit(
    direct_main_lifecycle: tuple[dict[str, topology.TopologyFixture], str, str],
) -> None:
    fixtures, baseline, tree = direct_main_lifecycle
    fixture = fixtures[topology.TOPOLOGY_DIRECT_MAIN_SHALLOW_PUSH]
    observation = fixture.observation
    topology.assert_topology(fixture)

    assert observation.shallow
    assert observation.branch == topology.MAIN_BRANCH
    assert observation.head_tree == tree
    assert observation.head_parents == (baseline,)
    assert _git(fixture.root, "rev-list", "--count", "HEAD").stdout.strip() == "1"
    assert (
        _git(
            fixture.root,
            "cat-file",
            "-e",
            f"{baseline}^{{commit}}",
            check=False,
        ).returncode
        != 0
    )
    assert not _git_path(fixture.root, "objects/info/alternates").exists()
    assert _git(fixture.root, "diff", "--quiet", check=False).returncode == 0
    assert (
        _git(fixture.root, "diff", "--cached", "--quiet", check=False).returncode == 0
    )
    _assert_no_active_git_operation(fixture.root)
