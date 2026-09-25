"""Explicit CI gates and bounded, current-run pytest coverage reconciliation."""

from __future__ import annotations

import argparse
import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.ci-coverage.v1"
MAX_REPORT_BYTES = 8 * 1024 * 1024
PARTITIONS = ("matrix", "remaining")
MATRIX_FILES = (
    "tests/test_phase58_slice16_pure_differential_compatibility_assurance.py",
    "tests/test_phase59_slice11_differential_compatibility_assurance.py",
    "tests/test_phase60_slice12_differential_compatibility.py",
    "tests/test_phase61_slice11_differential_compatibility.py",
    "tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
    "tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py",
    "tests/test_phase64_slice10_ir_observation_and_differential.py",
    "tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py",
    "tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py",
    "tests/test_phase66_slice14_private_emission_observation_process_integration.py",
)
STANDALONE = (
    MATRIX_FILES[7] + "::test_standalone_forward_reverse_batch_and_atomic_failure",
    MATRIX_FILES[9] + "::test_standalone_forward_reverse_batches_beside_older_families",
)
STANDALONE_NODES = tuple(
    f"{test}[{mode}]"
    for test in STANDALONE
    for mode in ("checkout", "relocated", "installed")
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


def partition_nodes(nodes: list[str]) -> dict[str, list[str]]:
    node_ids(nodes)
    if any(
        len(selectors) != len(set(selectors))
        for selectors in (MATRIX_FILES, STANDALONE, STANDALONE_NODES)
    ):
        raise ValueError("overlapping special selectors")
    files = {node.split("::", 1)[0] for node in nodes}
    if not set(MATRIX_FILES) <= files:
        raise ValueError("stale shared-matrix file selector")
    actual = {node for node in nodes if node.split("[", 1)[0] in STANDALONE}
    if actual != set(STANDALONE_NODES):
        raise ValueError("stale or overlapping standalone selector")
    result: dict[str, list[str]] = {part: [] for part in PARTITIONS}
    for node in nodes:
        part = (
            "matrix"
            if node.split("::", 1)[0] in MATRIX_FILES and node not in actual
            else "remaining"
        )
        result[part].append(node)
    if not all(result.values()):
        raise ValueError("empty partition")
    return result


def collection_identity(nodes: list[str]) -> dict[str, object]:
    node_ids(nodes)
    return {"count": len(nodes), "sha256": hashlib.sha256(canonical(nodes)).hexdigest()}


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
    identity = report["collection"]
    if (
        type(identity) is not dict
        or set(identity) != {"count", "sha256"}
        or type(identity["count"]) is not int
        or identity["count"] < len(nodes)
        or type(identity["sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) is None
    ):
        raise ValueError("invalid full collection identity")
    if kind == "collection":
        if identity != collection_identity(nodes):
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
    expected = partition_nodes(universe)
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
        self.nodes: list[str] = []
        self.identity: dict[str, object] = {}
        self.reports: dict[str, dict[str, str]] = {}
        self.properties: dict[tuple[str, str], str] = {}
        self.skips: dict[str, str] = {}
        self.workers = 0
        self.worker_collections: dict[str, list[str]] = {}
        self.finished: list[dict[str, object]] = []
        self.error = False

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        full = sorted(item.nodeid for item in items)
        self.identity = collection_identity(full)
        if self.partition is None:
            self.nodes = full
            return
        self.nodes = partition_nodes(full)[self.partition]
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


def runtime_command(max_workers: int | None = None) -> tuple[str, ...]:
    parser = validate._build_parser()
    args = parser.parse_args(())
    args.pytest_maxprocesses = max_workers
    selected = validate._pytest_command(args, parser)
    return (sys.executable, "-m", "pytest", *selected[3:])


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("gates", "collect", "run", "verify", "artifact")
    )
    parser.add_argument("--python", choices=("3.12", "3.13"), required=True)
    parser.add_argument("--common", action="store_true")
    parser.add_argument("--report", type=Path)
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
            print(
                "[ci-validation] coverage reconciled "
                + json.dumps(result, sort_keys=True)
            )
            return 0
        if args.report is None:
            raise ValueError("missing report path")
        if args.action == "artifact":
            report = read_report(args.report)
            verify_report(report, context, report["kind"])
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
            runtime_command(args.max_workers)
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
        print(f"[ci-validation] rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
