"""Cost-ordered loadfile keeps xdist's file units and sends every test once."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from xdist.remote import Producer
from xdist.scheduler import LoadFileScheduling

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conftest = _load("pietto_conftest_under_test", "tests/conftest.py")
workloads = _load("pietto_ci_workloads_under_test", "scripts/ci_workloads.py")

COLLECTION = [
    "tests/test_a.py::t1",
    "tests/test_a.py::t2",
    "tests/test_a.py::t3",
    "tests/test_a.py::t4",
    "tests/test_b.py::t1",
    "tests/test_b.py::t2",
    "tests/test_b.py::t3",
    "tests/test_heavy.py::t1",
    "tests/test_heavy.py::t2",
    "tests/test_mid.py::t1",
    "tests/test_mid.py::t2",
    "tests/test_mid.py::t3",
    "tests/test_c.py::t1",
    "tests/test_d.py::t1",
]
COSTS = {"tests/test_heavy.py": 900, "tests/test_mid.py": 300}


class Node:
    def __init__(self, name: str) -> None:
        self.gateway = SimpleNamespace(id=name)
        self.shutting_down = False
        self.sent: list[int] = []

    def send_runtest_some(self, indices: list[int]) -> None:
        self.sent.extend(indices)

    def shutdown(self) -> None:
        self.shutting_down = True


def _config(dist: str = "loadfile", workers: int = 2) -> Any:
    return SimpleNamespace(
        getvalue={"dist": dist, "tx": [f"{workers}*popen"]}.get,
        option=SimpleNamespace(loadscopereorder=True),
    )


def _quiet() -> Producer:
    return Producer("cost-ordered-test", enabled=False)


def _run(scheduler: Any, workers: int = 2) -> list[Node]:
    """Drive xdist's own bookkeeping: the least advanced node completes a test."""
    nodes = [Node(f"gw{i}") for i in range(workers)]
    for node in nodes:
        scheduler.add_node(node)
    for node in nodes:
        scheduler.add_node_collection(node, COLLECTION)
    scheduler.schedule()
    done = {node.gateway.id: 0 for node in nodes}
    while scheduler.has_pending:
        node = min(
            (n for n in nodes if done[n.gateway.id] < len(n.sent)),
            key=lambda n: done[n.gateway.id],
        )
        index = node.sent[done[node.gateway.id]]
        done[node.gateway.id] += 1
        scheduler.mark_test_complete(node, index)
    return nodes


def _units(node: Node) -> list[str]:
    units: list[str] = []
    for index in node.sent:
        scope = COLLECTION[index].split("::", 1)[0]
        if not units or units[-1] != scope:
            units.append(scope)
    return units


def test_estimated_files_go_first_and_a_busy_worker_gets_the_smallest_unit():
    stock = _run(LoadFileScheduling(_config(), _quiet()))
    assert [_units(n)[0] for n in stock] == ["tests/test_a.py", "tests/test_b.py"]
    nodes = _run(conftest.CostOrderedFileScheduling(_config(), _quiet(), COSTS))
    assert [_units(n)[0] for n in nodes] == ["tests/test_heavy.py", "tests/test_mid.py"]
    # Two pending heavy tests already reach xdist's top-up mark: the queued
    # follower is the smallest unit, not the next estimated file.
    assert _units(nodes[0])[1] == "tests/test_c.py"


@pytest.mark.parametrize("costs", [COSTS, {}, {"tests/test_d.py": 1}])
def test_every_test_runs_once_and_each_file_stays_on_one_worker(costs):
    nodes = _run(conftest.CostOrderedFileScheduling(_config(), _quiet(), costs))
    assert sorted(i for n in nodes for i in n.sent) == list(range(len(COLLECTION)))
    pairs = {
        (COLLECTION[i].split("::", 1)[0], n.gateway.id) for n in nodes for i in n.sent
    }
    assert len({scope for scope, _ in pairs}) == len(pairs)


def test_without_estimates_the_order_is_exactly_stock_loadfile():
    ordered = _run(conftest.CostOrderedFileScheduling(_config(), _quiet(), {}))
    stock = _run(LoadFileScheduling(_config(), _quiet()))
    assert [n.sent for n in ordered] == [n.sent for n in stock]


def test_registry_standalone_nodes_are_their_own_units_with_the_file_estimate():
    standalone = "tests/test_heavy.py::t2"
    nodes = _run(
        conftest.CostOrderedFileScheduling(
            _config(), _quiet(), COSTS, frozenset({standalone})
        )
    )
    assert sorted(i for n in nodes for i in n.sent) == list(range(len(COLLECTION)))
    owners = {
        n.gateway.id for n in nodes for i in n.sent if COLLECTION[i] == standalone
    }
    rest = {
        n.gateway.id
        for n in nodes
        for i in n.sent
        if COLLECTION[i] == "tests/test_heavy.py::t1"
    }
    # Both halves of the estimated file go out first, on different workers.
    assert owners != rest and {_units(n)[0] for n in nodes} == {"tests/test_heavy.py"}


def test_only_loadfile_is_replaced_and_it_reads_the_reviewed_registry():
    assert conftest.pytest_xdist_make_scheduler(_config("load"), _quiet()) is None
    scheduler = conftest.pytest_xdist_make_scheduler(_config(), _quiet())
    policy = workloads.load_policy()
    assert type(scheduler) is conftest.CostOrderedFileScheduling
    assert scheduler.costs == workloads.file_costs(policy)
    assert scheduler.independent == {
        row["function"] + "[" + mode + "]"
        for row in policy["legacy_nodes"]
        for mode in row["modes"]
    }


def test_reviewed_estimates_name_current_test_files():
    costs = workloads.file_costs(workloads.load_policy())
    assert costs
    for path in costs:
        assert (ROOT / path).is_file()


@pytest.mark.parametrize(
    "row",
    [
        {"path": "tests/test_a.py", "seconds": 1.5},
        {"path": "tests/test_a.py", "seconds": True},
        {"path": "tests/test_a.py", "seconds": 0},
        {"path": "tests/_pietto_helper.py", "seconds": 1},
        {"path": "tests/../src/test_x.py", "seconds": 1},
        {"path": "tests/test_a.py", "seconds": 1, "shard": "general-runtime"},
        {"path": "tests/test_a.py"},
    ],
)
def test_malformed_estimates_fail_before_scheduling(row):
    policy = deepcopy(workloads.load_policy())
    policy["file_costs"].append(row)
    with pytest.raises(ValueError, match="file cost"):
        workloads.validate_policy(policy)


def test_duplicate_or_missing_estimates_fail_before_scheduling():
    policy = deepcopy(workloads.load_policy())
    policy["file_costs"].append(deepcopy(policy["file_costs"][0]))
    with pytest.raises(ValueError, match="duplicate file cost"):
        workloads.validate_policy(policy)
    del policy["file_costs"]
    with pytest.raises(ValueError, match="registry fields"):
        workloads.validate_policy(policy)
