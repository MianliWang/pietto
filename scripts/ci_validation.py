"""Explicit CI gates and bounded, current-run pytest coverage reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any

import pytest

# Direct script execution also imports this checkout's validator namespace.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import validate
from scripts import ci_workloads as workloads

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
acquisition: Any = importlib.import_module("_pietto_differential_process_acquisition")

FORMAT = "pietto.ci-coverage.v2"
MAX_REPORT_BYTES = 8 * 1024 * 1024
POLICY = workloads.load_policy(ROOT / "ci/workloads.toml")
POLICY_ID = workloads.policy_identity(POLICY)
INPUT_ID = workloads.input_identity(ROOT)
PARTITIONS = tuple(row["id"] for row in POLICY["shards"])
# Compatibility fixture views come from data, never Phase-number source branches.
MATRIX_FILES = tuple(row["path"] for row in POLICY["legacy_files"])
STANDALONE = tuple(row["function"] for row in POLICY["legacy_nodes"])
STANDALONE_NODES = tuple(
    row["function"] + "[" + mode + "]"
    for row in POLICY["legacy_nodes"]
    for mode in row["modes"]
)
MANIFEST_PROPERTIES = frozenset(
    {"request_manifest", "cell_manifest", "phase66_request_manifest"}
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()


def node_ids(value: object) -> list[str]:
    if (
        type(value) is not list
        or not value
        or any(type(n) is not str or not n for n in value)
    ):
        raise ValueError("missing or invalid node IDs")
    if value != sorted(set(value)):
        raise ValueError("duplicate or noncanonical node IDs")
    return value


def partition_nodes(
    nodes: list[str], indices: list[int] | None = None
) -> dict[str, list[str]]:
    node_ids(nodes)
    if indices is None:
        indices = workloads.resolve(POLICY, nodes, {})
    result = workloads.place(POLICY, nodes, indices)
    if not all(result.values()):
        raise ValueError("empty partition")
    return result


def collection_identity(nodes: list[str], indices: list[int]) -> dict[str, object]:
    node_ids(nodes)
    if len(indices) != len(nodes):
        raise ValueError("incomplete independent collection requirements")
    return {
        "count": len(nodes),
        "sha256": hashlib.sha256(canonical(nodes)).hexdigest(),
        "requirements_sha256": workloads.digest(indices),
    }


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_report(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("report is not a regular data file")
    with path.open("rb") as stream:
        data = stream.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("coverage report exceeds 8 MiB")
    value = json.loads(data, object_pairs_hook=_pairs)
    if type(value) is not dict:
        raise ValueError("report must be an object")
    return value


def write_report(path: Path, value: dict[str, Any]) -> None:
    data = canonical(value)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("coverage report exceeds 8 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def runtime_context(
    python: str, checkout: str | None, run_id: str | None, attempt: int | None
) -> dict[str, object]:
    if (
        platform.python_implementation() != "CPython"
        or python != f"{sys.version_info.major}.{sys.version_info.minor}"
    ):
        raise ValueError("wrong primary Python runtime")
    actual = subprocess.check_output(
        ("git", "rev-parse", "HEAD"), cwd=ROOT, text=True
    ).strip()
    checkout = checkout or os.environ.get("GITHUB_SHA") or actual
    run_id = run_id or os.environ.get("GITHUB_RUN_ID")
    attempt = (
        attempt
        if attempt is not None
        else int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
    )
    if checkout != actual or re.fullmatch(r"[0-9a-f]{40}", checkout) is None:
        raise ValueError("wrong actual checkout")
    if (
        run_id is None
        or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id) is None
        or not 1 <= attempt <= 100
    ):
        raise ValueError("missing or invalid run identity")
    return {
        "checkout": checkout,
        "run_id": run_id,
        "run_attempt": attempt,
        "python": python,
        "python_version": platform.python_version(),
    }


def report_name(context: dict[str, Any], part: str) -> str:
    if part not in ("collection", *PARTITIONS):
        raise ValueError("unknown report owner")
    return f"ci-coverage-{context['run_id']}-{context['run_attempt']}-{context['python']}-{part}.json"


def verify_report(
    report: dict[str, Any], context: dict[str, Any], kind: str
) -> list[str]:
    if kind not in ("collection", "partition"):
        raise ValueError("unknown report kind")
    supplied = report.get("context")
    if type(supplied) is not dict or set(supplied) != set(context):
        raise ValueError("wrong report context")
    if any(type(supplied[key]) is not type(value) for key, value in context.items()):
        raise ValueError("wrong report context types")
    keys = {
        "format",
        "kind",
        "context",
        "exit_code",
        "collection",
        "elapsed_seconds",
        "nodes",
        "policy",
        "inputs",
        "domain",
        "requirements",
    }
    if kind == "partition":
        keys |= {"partition", "outcomes", "workers", "properties", "skips"}
    if (
        set(report) != keys
        or report["format"] != FORMAT
        or report["kind"] != kind
        or report["context"] != context
    ):
        raise ValueError("wrong report identity or fields")
    if type(report["exit_code"]) is not int or report["exit_code"] != 0:
        raise ValueError("pytest did not succeed")
    elapsed = report["elapsed_seconds"]
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("invalid report timing")
    nodes = node_ids(report["nodes"])
    if (
        type(report["policy"]) is not dict
        or report["policy"] != POLICY_ID
        or any(type(report["policy"][k]) is not type(v) for k, v in POLICY_ID.items())
        or report["inputs"] != INPUT_ID
    ):
        raise ValueError("wrong workload policy or input identity")
    domain = report["domain"]
    if (
        type(domain) is not list
        or not domain
        or domain != sorted(domain)
        or any(
            type(v) is not list
            or len(v) != 2
            or any(type(n) is not int for n in v)
            or v not in ([3, 12], [3, 13])
            for v in domain
        )
        or len({tuple(v) for v in domain}) != len(domain)
        or [int(v) for v in context["python"].split(".")] not in domain
    ):
        raise ValueError("invalid interpreter domain")
    requirements = report["requirements"]
    if (
        type(requirements) is not dict
        or set(requirements) != {"table", "indices"}
        or requirements["table"] != workloads.table(POLICY)
        or type(requirements["indices"]) is not list
        or len(requirements["indices"]) != len(nodes)
    ):
        raise ValueError("invalid resolved requirement table")
    for index in requirements["indices"]:
        workloads.integer(index, 0, len(requirements["table"]) - 1, "descriptor index")
    identity = report["collection"]
    if (
        type(identity) is not dict
        or set(identity) != {"count", "sha256", "requirements_sha256"}
        or type(identity["count"]) is not int
        or identity["count"] < len(nodes)
        or type(identity["sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) is None
    ):
        raise ValueError("invalid full collection identity")
    if kind == "collection":
        baseline = workloads.resolve(POLICY, nodes, {})
        for node, actual, legacy in zip(
            nodes, requirements["indices"], baseline, strict=True
        ):
            if node.split("::", 1)[0] in MATRIX_FILES and actual != legacy:
                raise ValueError("forged legacy workload declaration")
        if identity != collection_identity(nodes, requirements["indices"]):
            raise ValueError("full collection mismatch")
        return nodes
    if (
        report["partition"] not in PARTITIONS
        or type(report["workers"]) is not int
        or not 1 <= report["workers"] <= 4
    ):
        raise ValueError("invalid partition or worker budget")
    outcomes = report["outcomes"]
    if type(outcomes) is not list or len(outcomes) != len(nodes):
        raise ValueError("missing terminal outcomes")
    for index, row in enumerate(outcomes):
        if (
            type(row) is not list
            or len(row) != 4
            or type(row[0]) is not int
            or row[0] != index
        ):
            raise ValueError("duplicate, foreign or missing terminal ID")
        _, setup, call, teardown = row
        if teardown != "passed" or not (
            (setup == "passed" and call in ("passed", "skipped"))
            or (setup == "skipped" and call is None)
        ):
            raise ValueError("failed or incomplete setup/call/teardown")
    for field in ("properties", "skips"):
        if type(report[field]) is not list:
            raise ValueError("invalid supplementary observations")
    for row in report["properties"]:
        if (
            type(row) is not list
            or len(row) != 3
            or type(row[0]) is not int
            or not 0 <= row[0] < len(nodes)
            or row[1] not in MANIFEST_PROPERTIES
            or type(row[2]) is not str
        ):
            raise ValueError("invalid manifest property")
    for row in report["skips"]:
        if (
            type(row) is not list
            or len(row) != 2
            or type(row[0]) is not int
            or not 0 <= row[0] < len(nodes)
            or type(row[1]) is not str
            or "skipped" not in outcomes[row[0]][1:]
        ):
            raise ValueError("invalid skip observation")
    return nodes


def reconcile(
    collection: dict[str, Any],
    reports: list[dict[str, Any]],
    context: dict[str, Any],
    checks_status: str,
    runtime_status: str,
) -> dict[str, object]:
    if (checks_status, runtime_status) != ("success", "success"):
        raise ValueError("required checks or runtime jobs were not successful")
    universe = verify_report(collection, context, "collection")
    indices = collection["requirements"]["indices"]
    expected = partition_nodes(universe, indices)
    by_node = dict(zip(universe, indices, strict=True))
    if len(reports) != len(PARTITIONS):
        raise ValueError("missing partition report")
    seen: set[str] = set()
    owners: set[str] = set()
    skipped = 0
    for report in reports:
        nodes = verify_report(report, context, "partition")
        part = report["partition"]
        if part in owners or report["collection"] != collection["collection"]:
            raise ValueError("duplicate partition or different full collection")
        if report["domain"] != collection["domain"] or report["requirements"][
            "indices"
        ] != [by_node.get(n) for n in nodes]:
            raise ValueError("resolved requirement or interpreter-domain drift")
        if nodes != expected[part] or seen.intersection(nodes):
            raise ValueError("missing, foreign or overlapping selection")
        owners.add(part)
        seen.update(nodes)
        skipped += sum("skipped" in row[1:] for row in report["outcomes"])
    if owners != set(PARTITIONS) or seen != set(universe):
        raise ValueError("partition union differs from independent full collection")
    return {
        "python": context["python"],
        "collected": len(universe),
        "selected": len(seen),
        "executed_terminal": len(seen),
        "passed": len(seen) - skipped,
        "skipped": skipped,
        "partitions": {p: len(expected[p]) for p in PARTITIONS},
    }


def pytest_addoption(parser):
    group = parser.getgroup("pietto-ci-coverage")
    group.addoption("--ci-report")
    group.addoption("--ci-context")
    group.addoption("--ci-health")
    group.addoption("--ci-partition", choices=PARTITIONS)


def pytest_configure(config):
    if config.getoption("--ci-report"):
        config.pluginmanager.register(Coverage(config), "pietto-coverage")


class Coverage:
    """One opt-in invocation's collection and terminal pytest observations."""

    def __init__(self, config):
        self.config = config
        self.path = Path(config.getoption("--ci-report"))
        self.context = json.loads(config.getoption("--ci-context"))
        self.partition = config.getoption("--ci-partition")
        self.worker = hasattr(config, "workerinput")
        self.started = time.monotonic()
        self.started_wall = time.time()
        self.nodes: list[str] = []
        self.identity: dict[str, object] = {}
        self.reports: dict[str, dict[str, str]] = {}
        self.properties: dict[tuple[str, str], str] = {}
        self.skips: dict[str, str] = {}
        self.workers = 0
        self.worker_collections: dict[str, list[str]] = {}
        self.finished: list[dict[str, object]] = []
        self.error = False
        self.indices: list[int] = []
        self.domain: list[list[int]] = []
        self.worker_details: dict[str, Any] = {}
        self.partition_report: dict[str, Any] | None = None
        self.observations: list[dict[str, object]] = []

    def pytest_sessionstart(self, session):
        self.domain = [
            list(v) for v in sorted(acquisition.available_supported_interpreters())
        ]
        if self.partition is not None and (
            self.worker or not self.config.getoption("numprocesses", default=0)
        ):
            base = self.config._tmp_path_factory.getbasetemp()
            root = base.parent if self.worker else base
            acquisition._OBSERVER_ROOT = root / "pietto-differential-acquisition"
            acquisition._OBSERVER_EVENTS = self.observations

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        full = sorted(item.nodeid for item in items)
        indices = workloads.resolve(
            POLICY,
            full,
            {
                item.nodeid: [
                    (mark.args, mark.kwargs)
                    for mark in item.iter_markers("ci_workload")
                ]
                for item in items
            },
        )
        self.identity = collection_identity(full, indices)
        if self.partition is None:
            self.nodes = full
            self.indices = indices
            return
        self.nodes = partition_nodes(full, indices)[self.partition]
        by_node = dict(zip(full, indices, strict=True))
        self.indices = [by_node[n] for n in self.nodes]
        wanted = set(self.nodes)
        rejected = [item for item in items if item.nodeid not in wanted]
        items[:] = [item for item in items if item.nodeid in wanted]
        config.hook.pytest_deselected(items=rejected)

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_setupnodes(self, config, specs):
        self.workers = len(specs)

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node, ids):
        self.worker_collections[node.gateway.id] = sorted(ids)

    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(self, node, error):
        identity = node.workeroutput.get("pietto_collection")
        if error is not None or type(identity) is not dict:
            self.error = True
        else:
            self.finished.append(identity)
            self.worker_details[node.gateway.id] = node.workeroutput.get(
                "pietto_workload"
            )
            if type(self.worker_details[node.gateway.id]) is not dict:
                self.error = True

    def pytest_runtest_logreport(self, report):
        if self.worker:
            return
        phases = self.reports.setdefault(report.nodeid, {})
        if report.when not in ("setup", "call", "teardown") or report.when in phases:
            self.error = True
        phases[report.when] = report.outcome
        if report.outcome == "skipped":
            self.skips[report.nodeid] = str(report.longrepr)[-1024:]
        for name, value in report.user_properties:
            if name in MANIFEST_PROPERTIES:
                key = (report.nodeid, name)
                if key in self.properties and self.properties[key] != value:
                    self.error = True
                self.properties[key] = value

    def pytest_sessionfinish(self, session, exitstatus):
        if self.worker:
            self.config.workeroutput["pietto_collection"] = self.identity
            self.config.workeroutput["pietto_workload"] = {
                "indices": self.indices,
                "domain": self.domain,
                "observer": {"enabled": True, "events": self.observations},
            }
            return
        if self.workers:
            if (
                len(self.finished) != self.workers
                or len(self.worker_collections) != self.workers
                or not self.finished
                or any(x != self.finished[0] for x in self.finished)
            ):
                raise ValueError("missing or inconsistent worker collection")
            self.identity = self.finished[0]
            selections = list(self.worker_collections.values())
            if any(nodes != selections[0] for nodes in selections):
                raise ValueError("worker selection drift")
            self.nodes = selections[0]
            details = list(self.worker_details.values())
            if len(details) != self.workers or any(
                type(d) is not dict or set(d) != {"indices", "domain", "observer"}
                for d in details
            ):
                raise ValueError("missing worker requirement/observation details")
            first = details[0]
            if any(
                d["indices"] != first["indices"] or d["domain"] != first["domain"]
                for d in details
            ):
                raise ValueError("worker requirement/domain drift")
            self.indices, self.domain = first["indices"], first["domain"]
        if self.error:
            raise ValueError("duplicate outcome or failed worker")
        result: dict[str, Any] = {
            "format": FORMAT,
            "kind": "collection" if self.partition is None else "partition",
            "context": self.context,
            "exit_code": int(exitstatus),
            "collection": self.identity,
            "elapsed_seconds": time.monotonic() - self.started,
            "nodes": self.nodes,
            "policy": POLICY_ID,
            "inputs": INPUT_ID,
            "domain": self.domain,
            "requirements": {"table": workloads.table(POLICY), "indices": self.indices},
        }
        if self.partition is not None:
            if set(self.reports) != set(self.nodes):
                raise ValueError("actual terminal IDs differ from selected IDs")
            indices = {node: index for index, node in enumerate(self.nodes)}
            result.update(
                partition=self.partition,
                workers=self.workers or 1,
                outcomes=[
                    [
                        index,
                        *(
                            self.reports[node].get(phase)
                            for phase in ("setup", "call", "teardown")
                        ),
                    ]
                    for index, node in enumerate(self.nodes)
                ],
                properties=[
                    [indices[node], name, value]
                    for (node, name), value in sorted(self.properties.items())
                ],
                skips=[
                    [indices[node], reason]
                    for node, reason in sorted(self.skips.items())
                ],
            )
        if exitstatus == 0:
            verify_report(result, self.context, result["kind"])
        write_report(self.path, result)
        self.partition_report = result if self.partition is not None else None

    def pytest_terminal_summary(self, terminalreporter):
        if self.partition_report is None:
            return
        timing = workloads.timing_summary(
            [
                r
                for reports in terminalreporter.stats.values()
                for r in reports
                if isinstance(r, pytest.TestReport)
            ],
            self.started_wall,
            self.config.getoption("dist", default="no"),
        )
        observers = (
            {worker: d["observer"] for worker, d in self.worker_details.items()}
            if self.workers
            else {"local": {"enabled": True, "events": self.observations}}
        )
        managed = workloads.managed_observations(
            POLICY,
            self.partition,
            self.context,
            self.domain,
            INPUT_ID,
            observers,
            self.partition_report["properties"],
        )
        runner = {
            "image": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
            "os": platform.system(),
            "arch": platform.machine(),
        }
        health = workloads.shard_health(self.partition_report, timing, managed, runner)
        workloads.verify_shard_health(health, POLICY, self.partition_report)
        health_path = self.config.getoption("--ci-health")
        if health_path is None:
            raise ValueError("missing current-run health path")
        workloads.write_json(Path(health_path), health)
        terminalreporter.write_line(
            "[ci-timing] "
            + json.dumps({"partition": self.partition, **timing}, ensure_ascii=True)
        )
        terminalreporter.write_line(
            "[ci-health] "
            + json.dumps(
                {
                    "partition": self.partition,
                    "managed_cells": len(managed["productions"]),
                    "observer_complete": managed["complete"],
                }
            )
        )


def runtime_command(
    max_workers: int | None = None, partition: str = PARTITIONS[0]
) -> tuple[str, ...]:
    parser = validate._build_parser()
    args = parser.parse_args(())
    args.pytest_maxprocesses = max_workers
    selected = validate._pytest_command(args, parser)
    scheduler = next(
        row["scheduler"] for row in POLICY["shards"] if row["id"] == partition
    )
    options = tuple(
        "--dist=" + scheduler if arg == "--dist=loadfile" else arg
        for arg in selected[3:]
    )
    return (sys.executable, "-m", "pytest", *options)


def run_gate(name: str, command: tuple[str, ...], guard: str) -> int:
    parser = argparse.ArgumentParser()
    guarded = validate._oom_guard_enabled(guard, parser)
    started = time.monotonic()
    print(f"[ci-validation] {name}: {json.dumps(command)}", flush=True)
    result = (
        validate._run_guarded_gate(name, command, guard)
        if guarded
        else subprocess.run(command, cwd=ROOT, check=False).returncode
    )
    print(
        f"[ci-validation] {name} completed in {time.monotonic() - started:.3f}s; exit={result}",
        flush=True,
    )
    return result


def readiness_inputs():
    return tuple(
        hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "tests/_pietto_phase67_arrow_compatibility_probe.py",
            "ci/phase67-arrow-compatibility-requirements.txt",
        )
    )


def workflow_context(context):
    return {
        "repository": os.environ.get("GITHUB_REPOSITORY", "MianliWang/pietto"),
        "checkout": context["checkout"],
        "run_id": context["run_id"],
        "run_attempt": context["run_attempt"],
        "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "branch": os.environ.get("GITHUB_REF_NAME", "main"),
    }


def health_name(context, part):
    return f"ci-health-{context['run_id']}-{context['run_attempt']}-{context['python']}-{part}.json"


def check_product(path, context):
    probe = importlib.import_module("_pietto_phase67_result_product_probe")
    if path is None:
        raise ValueError("missing required installed product evidence")
    return probe.verify_report(read_report(path), context, probe.input_closure(ROOT))


def complete_runtime(args, context, collection, reports, result):
    check_product(args.product, context)
    if args.health_dir is None or args.readiness is None or args.summary is None:
        raise ValueError("missing required health/readiness/completion output")
    names = {health_name(context, p) for p in PARTITIONS}
    if {p.name for p in args.health_dir.iterdir()} != names:
        raise ValueError("missing or foreign partition health files")
    shards = [
        workloads.verify_shard_health(
            workloads.read_json(
                args.health_dir / health_name(context, report["partition"])
            ),
            POLICY,
            report,
        )
        for report in reports
    ]
    readiness = workloads.verify_readiness(
        workloads.read_json(args.readiness), context, *readiness_inputs()
    )
    summary = {
        "format": workloads.HEALTH_FORMAT,
        "kind": "runtime",
        "context": context,
        "policy": POLICY_ID,
        "domain": collection["domain"],
        "collection": collection["collection"],
        "coverage": result,
        "shards": shards,
        "readiness": readiness,
    }
    workloads.write_json(args.summary, summary)
    return summary


def complete_health(args, context):
    if args.compiler_status != "success" or args.target_status != "success":
        raise ValueError("required compiler or target jobs were not successful")
    if args.health_dir is None or args.report is None:
        raise ValueError("missing runtime health summaries or output")
    if not args.health_dir.exists():
        facts = workloads.fetch_current_summaries(
            workflow_context(context),
            os.environ.get("CI_HEALTH_TOKEN"),
            args.health_dir,
        )
        print(
            "[ci-health] current raw summaries verified "
            + json.dumps(facts, ensure_ascii=True)
        )
    expected_names = {
        health_name({**context, "python": py}, "summary") for py in ("3.12", "3.13")
    }
    if {p.name for p in args.health_dir.iterdir()} != expected_names:
        raise ValueError("missing or foreign runtime summary files")
    runtimes = {}
    for py in ("3.12", "3.13"):
        value = workloads.read_json(
            args.health_dir / health_name({**context, "python": py}, "summary")
        )
        expected = {
            **context,
            "python": py,
            "python_version": value["context"]["python_version"],
        }
        if (
            value["context"] != expected
            or type(expected["python_version"]) is not str
            or re.fullmatch(re.escape(py) + r"\.[0-9]+", expected["python_version"])
            is None
        ):
            raise ValueError("foreign runtime health context")
        workloads.verify_readiness(value["readiness"], expected, *readiness_inputs())
        if value["policy"] != POLICY_ID or [
            p["partition"] for p in value["shards"]
        ] != list(PARTITIONS):
            raise ValueError("runtime health policy/topology mismatch")
        runtimes[py] = value
    identity = workflow_context(context)
    history, provenance, cost = workloads.fetch_history(
        identity, os.environ.get("CI_HEALTH_TOKEN"), POLICY
    )
    if args.history_file:
        if identity["event"] != "local" or len(args.history_file) > 3:
            raise ValueError(
                "explicit local history is only for bounded local reproduction"
            )
        history = [
            workloads.verify_workflow_health(workloads.read_json(p))
            for p in args.history_file
        ]
        provenance = {
            "availability": "EXPLICIT_LOCAL_FILES",
            "candidates": len(history),
            "accepted": [
                {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in args.history_file
            ],
            "rejected": [],
        }
    value = {
        "format": workloads.HEALTH_FORMAT,
        "kind": "workflow",
        "context": identity,
        "policy": POLICY_ID,
        "runtimes": runtimes,
        "cost": cost,
        "assessment": {},
        "history": provenance,
        "reference": {
            "label": "R1 historical reference; not a health-v1 sample",
            "run_id": "36088124495",
            "workflow_seconds": 720,
            "sum_job_seconds": 3507,
            "realized_jobs": 13,
        },
    }
    value["assessment"] = workloads.analyze(value, history, POLICY["thresholds"])
    workloads.verify_workflow_health(value, identity)
    workloads.write_json(args.report, value)
    summary_path = args.summary or (
        Path(os.environ["GITHUB_STEP_SUMMARY"])
        if os.environ.get("GITHUB_STEP_SUMMARY")
        else None
    )
    if summary_path is not None:
        with summary_path.open("a", encoding="utf-8") as stream:
            stream.write(workloads.summary_markdown(value))
    print(
        "[ci-health] "
        + json.dumps(
            {
                "status": value["assessment"]["status"],
                "current_screen": value["assessment"]["current_screen"],
                "history": provenance["availability"],
                "cost_complete": cost["complete"],
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "gates",
            "collect",
            "run",
            "verify",
            "artifact",
            "check-arrow",
            "check-product",
            "health",
        ),
    )
    parser.add_argument("--python", choices=("3.12", "3.13"), required=True)
    parser.add_argument("--common", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--health", type=Path)
    parser.add_argument("--health-dir", type=Path)
    parser.add_argument("--readiness", type=Path)
    parser.add_argument("--product", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--history-file", type=Path, action="append", default=[])
    parser.add_argument("--compiler-status")
    parser.add_argument("--target-status")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--partition", choices=PARTITIONS)
    parser.add_argument("--checkout")
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt", type=int)
    parser.add_argument("--checks-status")
    parser.add_argument("--runtime-status")
    parser.add_argument("--artifact-id")
    parser.add_argument("--artifact-digest")
    parser.add_argument("--oom-guard", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--max-workers", type=int, choices=(1, 2, 3, 4))
    args = parser.parse_args(argv)
    try:
        if args.python != f"{sys.version_info.major}.{sys.version_info.minor}":
            raise ValueError("wrong primary Python runtime")
        if args.action == "gates":
            print(
                "[ci-validation] explicit partial static gates; not a full validator",
                flush=True,
            )
            for name, command in (
                validate.GATES[:5] if args.common else validate.GATES[3:5]
            ):
                result = run_gate(name, command, args.oom_guard)
                if result:
                    return result
            return 0
        context = runtime_context(
            args.python, args.checkout, args.run_id, args.run_attempt
        )
        if args.action == "health":
            return complete_health(args, context)
        if args.action == "check-product":
            check_product(args.report, context)
            print("[ci-validation] installed Int product correspondence verified")
            return 0
        if args.action == "check-arrow":
            import importlib.util

            if importlib.util.find_spec("pyarrow") is not None:
                raise ValueError("Arrow leaked into core environment")
            if args.report is None:
                raise ValueError("missing Arrow readiness report")
            workloads.verify_readiness(
                workloads.read_json(args.report), context, *readiness_inputs()
            )
            print(
                "[ci-validation] all nine real Arrow readiness cases verified; core remains Arrow-free"
            )
            return 0
        if args.action == "verify":
            if args.evidence_dir is None:
                raise ValueError("missing evidence directory")
            names = [report_name(context, part) for part in ("collection", *PARTITIONS)]
            if {p.name for p in args.evidence_dir.iterdir()} != set(names):
                raise ValueError("missing or foreign report files")
            collection, *reports = [
                read_report(args.evidence_dir / name) for name in names
            ]
            result = reconcile(
                collection, reports, context, args.checks_status, args.runtime_status
            )
            complete_runtime(args, context, collection, reports, result)
            print(
                "[ci-validation] coverage reconciled "
                + json.dumps(result, sort_keys=True)
            )
            return 0
        if args.report is None:
            raise ValueError("missing report path")
        if args.action == "artifact":
            report = read_report(args.report)
            if report.get("format") == FORMAT:
                verify_report(report, context, report["kind"])
            elif report.get("format") == "pietto.result-product.v1":
                check_product(args.report, context)
            elif report.get("format") == workloads.READINESS_FORMAT:
                workloads.verify_readiness(report, context, *readiness_inputs())
            elif report.get("format") == workloads.HEALTH_FORMAT:
                if args.report.stat().st_size > workloads.MAX_HEALTH_BYTES:
                    raise ValueError("health exceeds 1 MiB")
                if report["kind"] == "workflow":
                    workloads.verify_workflow_health(report, workflow_context(context))
                elif (
                    report["kind"] in ("partition", "runtime")
                    and report["context"] == context
                    and report["policy"] == POLICY_ID
                ):
                    if report["kind"] == "partition":
                        if args.evidence_dir is None:
                            raise ValueError(
                                "partition health requires corresponding coverage"
                            )
                        coverage = read_report(
                            args.evidence_dir
                            / report_name(context, report["partition"])
                        )
                        verify_report(coverage, context, "partition")
                        workloads.verify_shard_health(report, POLICY, coverage)
                else:
                    raise ValueError("foreign health context or kind")
            else:
                raise ValueError("unknown current evidence format")
            if (
                args.artifact_id is None
                or not args.artifact_id.isdigit()
                or int(args.artifact_id) <= 0
                or args.artifact_digest
                != hashlib.sha256(args.report.read_bytes()).hexdigest()
            ):
                raise ValueError("artifact identity/digest mismatch")
            print(
                "[ci-validation] raw artifact verified "
                + args.artifact_id
                + " "
                + args.artifact_digest
            )
            return 0
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("report path must be fresh")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        if os.environ.get("PYTEST_ADDOPTS") or os.environ.get("PYTEST_PLUGINS"):
            raise ValueError("ambient pytest selection/plugins are not allowed")
        if args.action == "run" and args.partition is None:
            raise ValueError("missing partition")
        command = (
            runtime_command(args.max_workers, args.partition)
            if args.action == "run"
            else (sys.executable, "-m", "pytest", "--collect-only", "-qq")
        )
        command += (
            "-p",
            "scripts.ci_validation",
            "--ci-report",
            str(args.report.resolve()),
            "--ci-context",
            json.dumps(context, separators=(",", ":")),
        )
        if args.action == "run":
            basetemp = args.report.parent.parent / (args.report.stem + "-pytest")
            if basetemp.exists():
                raise ValueError("pytest invocation root must be fresh")
            command += (
                "--ci-health",
                str(args.health.resolve())
                if args.health is not None
                else str(
                    args.report.with_name(
                        args.report.name.replace("ci-coverage-", "ci-health-")
                    ).resolve()
                ),
                "--durations=30",
                "--durations-min=1",
                "--ci-partition",
                args.partition,
                "--basetemp",
                str(basetemp),
            )
        return run_gate(
            "pytest " + (args.partition or "independent full collection"),
            command,
            args.oom_guard,
        )
    except (ValueError, OSError, RuntimeError) as error:
        print(
            "[ci-validation] rejected: " + json.dumps(str(error), ensure_ascii=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
