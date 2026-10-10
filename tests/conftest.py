"""Order Pietto's ``loadfile`` units by reviewed cost estimates.

Stock ``--dist=loadfile`` keeps each test file on one worker but queues files
by test count, so heavy files with few tests start late and stack on one
worker. This scheduler hands out the same file units, largest
``[[file_costs]]`` estimate in ``ci/workloads.toml`` first and then by test
count. A worker that still has unfinished tests of an estimated file gets the
smallest unit instead: xdist queues one more test before a worker starts its
last one, and a heavy file must not wait behind it. Registry standalone nodes
(``[[legacy_nodes]]`` modes, which CI already runs on ``load`` shards) are units
of their own and inherit their file's estimate.

It also registers ``--pietto-storage-class``, the explicit storage environment
class that ``tests/_pietto_phase68_slice11_probe.py`` resolves and applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from xdist.remote import Producer
from xdist.scheduler import LoadFileScheduling
from xdist.workermanage import WorkerController


class CostOrderedFileScheduling(LoadFileScheduling):
    def __init__(
        self,
        config: pytest.Config,
        log: Producer | None,
        costs: dict[str, int],
        independent: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__(config, log)
        self.costs = costs
        self.independent = independent

    def _split_scope(self, nodeid: str) -> str:
        return nodeid if nodeid in self.independent else super()._split_scope(nodeid)

    def _cost(self, scope: str) -> int:
        return self.costs.get(scope.split("::", 1)[0], 0)

    def _assign_work_unit(self, node: WorkerController) -> None:
        inside = any(
            self._cost(scope) and not all(unit.values())
            for scope, unit in self.assigned_work[node].items()
        )
        scope = (min if inside else max)(
            self.workqueue,
            key=lambda s: (self._cost(s), len(self.workqueue[s])),
        )
        self.workqueue.move_to_end(scope, last=False)
        super()._assign_work_unit(node)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--pietto-storage-class",
        default=None,
        help="storage environment class: hosted-refusal, qualified or report",
    )


def pytest_configure(config: pytest.Config) -> None:
    import _pietto_phase68_slice11_probe as probe

    probe.STORAGE_CLASS_OPTION = config.getoption("--pietto-storage-class")
    try:
        probe.storage_class(option=probe.STORAGE_CLASS_OPTION)
    except ValueError as error:
        raise pytest.UsageError(str(error)) from None


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(
    config: pytest.Config, log: Producer
) -> LoadFileScheduling | None:
    if config.getvalue("dist") != "loadfile":
        return None
    spec = importlib.util.spec_from_file_location(
        "pietto_ci_workloads_costs",
        Path(__file__).resolve().parents[1] / "scripts/ci_workloads.py",
    )
    assert spec is not None and spec.loader is not None
    workloads = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workloads)
    policy = workloads.load_policy()
    independent = frozenset(
        row["function"] + "[" + mode + "]"
        for row in policy["legacy_nodes"]
        for mode in row["modes"]
    )
    return CostOrderedFileScheduling(
        config, log, workloads.file_costs(policy), independent
    )
