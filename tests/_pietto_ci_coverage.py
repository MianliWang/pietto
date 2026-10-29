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
PRIMARY = (("3.12", "twelve"), ("3.13", "thirteen"))
# Exact setup-python patch per logical family. Reports compare the full
# python_version, so every producer and consumer of a family moves together.
SETUP_PATCH = {"3.12": "3.12.14", "3.13": "3.13.15"}
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
EXPECTED_PINS = {
    job: [SETUP_PATCH["3.12" if job.endswith("_twelve") else "3.13"]]
    for job in EXPECTED_JOBS
}
ACTIONS = {
    "actions/checkout": ("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7.0.1"),
    "actions/setup-python": ("6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", "v7.1.0"),
    "actions/setup-java": ("b843ebf9b913146b38da2eaa7aeddf76074ae1ad", "v6.1.0"),
    "astral-sh/setup-uv": ("07a047e608db84b3d8c06cd9a7c7dcc9c355c18e", "v10.3.2"),
    "actions/upload-artifact": ("cf430e030ddbb5b0abf93d22962f4752f3646cd9", "v7.0.2"),
    "actions/download-artifact": ("9000827ccba6bdab643e8b6fd33ac0654aef8333", "v8.0.2"),
}
AUXILIARY = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
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
