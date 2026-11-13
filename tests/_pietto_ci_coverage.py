from __future__ import annotations

from copy import deepcopy
import importlib.util
import re
from typing import Any, cast

from pathlib import Path

from _pietto_ci_workflow import job as _job

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYTHON_VERSION_PATH = REPO_ROOT / ".python-version"
EXPECTED_JOBS = (
    "checks_twelve",
    "runtime_twelve",
    "python_twelve",
    "checks_thirteen",
    "runtime_thirteen",
    "python_thirteen",
    "target_conformance",
    "target_conformance_aggregate",
)


def _setup_pins(workflow: str) -> dict[str, list[str]]:
    pins = {
        job: re.findall(
            r'(?m)^          python-version: "([^"]*)"$', _job(workflow, job)
        )
        for job in EXPECTED_JOBS
    }
    assert workflow.count("python-version:") == sum(map(len, pins.values()))
    return pins


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pietto_ci_validation", ROOT / "scripts/ci_validation.py"
)
assert SPEC is not None and SPEC.loader is not None
ci = cast(Any, importlib.util.module_from_spec(SPEC))
SPEC.loader.exec_module(ci)
CONTEXT = {
    "checkout": "1" * 40,
    "run_id": "37",
    "run_attempt": 1,
    "python": "3.13",
    "python_version": "3.13.13",
}
FUTURE = "tests/test_new_ordinary.py::test_future"


def _universe():
    # This is the full collected input, constructed before asking the classifier.
    return sorted(
        [
            *(path + "::test_existing" for path in ci.MATRIX_FILES),
            *ci.STANDALONE_NODES,
            FUTURE,
            FUTURE + "_other",
            FUTURE + "_third",
            FUTURE + "_fourth",
        ]
    )


def _reports():
    universe = _universe()
    descriptors = ci.workloads.resolve(ci.POLICY, universe, {})
    base = {
        "format": ci.FORMAT,
        "context": dict(CONTEXT),
        "exit_code": 0,
        "collection": ci.collection_identity(universe, descriptors),
        "policy": ci.POLICY_ID,
        "inputs": ci.INPUT_ID,
        "domain": [[3, 13]],
        "elapsed_seconds": 1.0,
    }
    descriptors = ci.workloads.resolve(ci.POLICY, universe, {})
    by_node = dict(zip(universe, descriptors, strict=True))
    collection = {
        **base,
        "kind": "collection",
        "nodes": universe,
        "requirements": {
            "table": ci.workloads.table(ci.POLICY),
            "indices": descriptors,
        },
    }
    partitions = []
    for part, nodes in ci.partition_nodes(universe).items():
        partitions.append(
            {
                **deepcopy(base),
                "kind": "partition",
                "partition": part,
                "nodes": nodes,
                "requirements": {
                    "table": ci.workloads.table(ci.POLICY),
                    "indices": [by_node[n] for n in nodes],
                },
                "outcomes": [
                    [i, "passed", "passed", "passed"] for i in range(len(nodes))
                ],
                "workers": 4,
                "properties": [],
                "skips": [],
            }
        )
    return collection, partitions


def _verify(collection, partitions, checks="success", runtime="success"):
    return ci.reconcile(collection, partitions, CONTEXT, checks, runtime)
