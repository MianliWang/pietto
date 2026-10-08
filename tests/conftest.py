"""Order Pietto's ``loadfile`` units by reviewed cost estimates.

Stock ``--dist=loadfile`` keeps each test file on one worker but queues files
by test count, so heavy files with few tests start late and stack on one
worker. This scheduler hands out the same file units, largest
``[[file_costs]]`` estimate in ``ci/workloads.toml`` first and then by test
count. A worker that still has unfinished tests of an estimated file gets the
smallest unit instead: xdist queues one more test before a worker starts its
last one, and a heavy file must not wait behind it.
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
        self, config: pytest.Config, log: Producer | None, costs: dict[str, int]
    ) -> None:
        super().__init__(config, log)
        self.costs = costs

    def _assign_work_unit(self, node: WorkerController) -> None:
        inside = any(
            scope in self.costs and not all(unit.values())
            for scope, unit in self.assigned_work[node].items()
        )
        scope = (min if inside else max)(
            self.workqueue,
            key=lambda s: (self.costs.get(s, 0), len(self.workqueue[s])),
        )
        self.workqueue.move_to_end(scope, last=False)
        super()._assign_work_unit(node)


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
    return CostOrderedFileScheduling(
        config, log, workloads.file_costs(workloads.load_policy())
    )
