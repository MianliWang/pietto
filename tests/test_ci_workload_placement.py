"""A requirement placed on several shards is dealt to them by sorted node index."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pietto_ci_workloads_split_under_test", ROOT / "scripts/ci_workloads.py"
)
assert spec is not None and spec.loader is not None
workloads: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workloads)
POLICY = workloads.load_policy()
GENERAL = ["general-runtime-1", "general-runtime-2", "general-runtime-3"]


def _universe() -> list[str]:
    legacy = [row["path"] + "::test_existing" for row in POLICY["legacy_files"]]
    modes = [
        row["function"] + "[" + mode + "]"
        for row in POLICY["legacy_nodes"]
        for mode in row["modes"]
    ]
    ordinary = [f"tests/test_{name}.py::test_{n}" for name in "ab" for n in range(3)]
    return sorted([*legacy, *modes, *ordinary])


def test_general_runtime_nodes_alternate_and_every_node_is_placed_once():
    nodes = _universe()
    placed = workloads.place(POLICY, nodes, workloads.resolve(POLICY, nodes, {}))
    ordinary = [
        n
        for n in nodes
        if n.split("::", 1)[0] in ("tests/test_a.py", "tests/test_b.py")
    ]
    for part, shard in enumerate(GENERAL):
        assert placed[shard] == ordinary[part :: len(GENERAL)]
    assert sorted(n for part in placed.values() for n in part) == nodes
    assert [row["id"] for row in POLICY["shards"]][-3:] == GENERAL


@pytest.mark.parametrize(
    "damage",
    [
        "empty",
        "repeated",
        "unknown",
        "string",
        "old_field",
        "split_group",
        "load_shard",
        "extra_shard",
    ],
)
def test_malformed_split_placements_fail_before_execution(damage):
    policy = deepcopy(POLICY)
    general = next(p for p in policy["placements"] if p["kind"] == "general-runtime")
    shared = next(p for p in policy["placements"] if p["kind"] == "shared-acquisition")
    if damage == "empty":
        general["shards"] = []
    elif damage == "repeated":
        general["shards"] = [GENERAL[0], GENERAL[0]]
    elif damage == "unknown":
        general["shards"] = [*GENERAL, "general-runtime-4"]
    elif damage == "string":
        general["shards"] = GENERAL[0]
    elif damage == "old_field":
        general["shard"] = general.pop("shards")[0]
    elif damage == "split_group":
        shared["shards"] = ["shared-acquisition", GENERAL[0]]
    elif damage == "load_shard":
        general["shards"] = [*GENERAL, "plan-portability"]
    else:
        policy["shards"].append({**policy["shards"][-1], "id": "general-runtime-4"})
    with pytest.raises(ValueError):
        workloads.validate_policy(policy)
