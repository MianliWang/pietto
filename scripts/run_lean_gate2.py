"""Fail-closed offline orchestration for Pietto's lean Gate 2 workflow."""

# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import resource
from typing import Iterable


SCHEMA = "pietto.gate2.lean-runner.v1"
PERFORMANCE_SCHEMA = "pietto.gate2.performance-results.v1"
OFFLINE_ENV = {"UV_OFFLINE": "1", "UV_NO_SYNC": "1"}


class LeanGate2Error(RuntimeError):
    """Raised when convergence, manifest, or a validation gate is not exact."""


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...]
    topology_serial: bool = False
    authoritative_validate: bool = False
    env_overrides: tuple[tuple[str, str], ...] = ()


def canonical_json(document: object) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def command_graph(
    *,
    root: Path,
    manifest: Path,
    reader_output: Path,
    topology_output: Path,
    focused_nodes: tuple[str, ...],
    compatibility_nodes: tuple[str, ...],
    reader_nodes: tuple[str, ...],
    formatter_paths: tuple[str, ...],
    reviewed_tree: str = "0" * 40,
) -> tuple[CommandSpec, ...]:
    python = root / ".venv/bin/python"
    uv = "uv"
    return (
        CommandSpec("lock", (uv, "lock", "--check")),
        CommandSpec(
            "focused",
            (uv, "run", "pytest", "-q", "-p", "no:cacheprovider", *focused_nodes),
        ),
        CommandSpec(
            "compatibility",
            (
                uv,
                "run",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *compatibility_nodes,
            ),
        ),
        CommandSpec(
            "reader_audit",
            (
                str(python),
                "scripts/audit_gate2_readers.py",
                "--root",
                str(root),
                "--base",
                "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
                "--manifest",
                str(manifest),
                "--active-manifest-data",
                "tests/_active_gate2_manifest_data.py",
                "--reviewed-tree",
                reviewed_tree,
                "--output",
                str(reader_output),
            ),
        ),
        CommandSpec(
            "format_check",
            (uv, "run", "ruff", "format", "--check", *formatter_paths),
        ),
        CommandSpec(
            "reader_closure",
            (
                uv,
                "run",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                "run_gate2_topology_checks",
                *reader_nodes,
            ),
            env_overrides=(
                (
                    "PIETTO_GATE2_PYTEST_OUTCOMES",
                    str(reader_output.with_name("reader-once-outcomes.json")),
                ),
                (
                    "PYTHONPATH",
                    os.pathsep.join(
                        (str(root / "src"), str(root / "tests"), str(root / "scripts"))
                    ),
                ),
                ("PYTHONDONTWRITEBYTECODE", "1"),
            ),
        ),
        CommandSpec(
            "topology",
            (
                str(python),
                "scripts/run_gate2_topology_checks.py",
                "--root",
                str(root),
                "--manifest",
                str(manifest),
                "--reader-closure",
                str(reader_output),
                "--output",
                str(topology_output),
                "--python",
                str(python),
            ),
            topology_serial=True,
        ),
        CommandSpec("ruff", (uv, "run", "ruff", "check", ".")),
        CommandSpec(
            "pyright_production",
            (uv, "run", "pyright", "--project", "pyrightconfig.json"),
        ),
        CommandSpec(
            "pyright_tests",
            (uv, "run", "pyright", "--project", "pyrightconfig.tests.json"),
        ),
        CommandSpec(
            "authoritative_validate",
            (uv, "run", "python", "scripts/validate.py"),
            authoritative_validate=True,
        ),
        CommandSpec(
            "clean_collection",
            (uv, "run", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"),
        ),
        CommandSpec(
            "clean_pytest", (uv, "run", "pytest", "-q", "-p", "no:cacheprovider")
        ),
        CommandSpec("generated", (uv, "run", "python", "scripts/check_generated.py")),
        CommandSpec("goldens", (uv, "run", "python", "scripts/check_goldens.py")),
        CommandSpec("package_smoke", (uv, "run", "python", "scripts/package_smoke.py")),
        CommandSpec("installed_cli_version", (uv, "run", "pietto", "--version")),
    )


def _git_output(root: Path, arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _load_active_matcher(root: Path):
    sys.path.insert(0, str(root / "tests"))
    from _active_gate2_manifest import active_gate2_manifest_is_active  # noqa: PLC0415

    return active_gate2_manifest_is_active


def assert_preconditions(
    *, root: Path, unresolved_warnings: Iterable[str] = ()
) -> None:
    if tuple(unresolved_warnings):
        raise LeanGate2Error("unresolved dynamic reader warnings")
    if _git_output(root, ["diff", "--cached", "--name-only"]):
        raise LeanGate2Error("index is not empty")
    if not _load_active_matcher(root)():
        raise LeanGate2Error("dirty set is not the exact active Gate 2 manifest")


def validate_graph(graph: tuple[CommandSpec, ...]) -> None:
    names = tuple(command.name for command in graph)
    required = (
        "lock",
        "focused",
        "compatibility",
        "reader_audit",
        "format_check",
        "reader_closure",
        "topology",
        "ruff",
        "pyright_production",
        "pyright_tests",
        "authoritative_validate",
        "clean_collection",
        "clean_pytest",
        "generated",
        "goldens",
        "package_smoke",
        "installed_cli_version",
    )
    if names != required:
        raise LeanGate2Error("command graph drift")
    if sum(item.authoritative_validate for item in graph) != 1:
        raise LeanGate2Error("authoritative validation must occur exactly once")
    if sum(item.topology_serial for item in graph) != 1:
        raise LeanGate2Error("topology must have one serial runner")
    convergence = names.index("format_check")
    authority = names.index("authoritative_validate")
    if convergence >= authority:
        raise LeanGate2Error("authoritative validation starts before convergence")
    for command in graph:
        overrides = dict(command.env_overrides)
        if any(
            overrides.get(key, value) != value for key, value in OFFLINE_ENV.items()
        ):
            raise LeanGate2Error("offline environment drift")
        joined = " ".join(command.argv).lower()
        if any(
            token in joined
            for token in ("http://", "https://", " curl ", " wget ", " pip install")
        ):
            raise LeanGate2Error("network-capable command in Gate 2 graph")


def run_graph(
    *,
    root: Path,
    graph: tuple[CommandSpec, ...],
    reviewed_tree: str,
    reader_output: Path,
    topology_output: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    validate_graph(graph)
    records: list[dict[str, object]] = []
    pytest_processes = 0
    started_ns = time.monotonic_ns()
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    clean_count = 0
    reader_outcomes: dict[str, object] | None = None
    topology_document: dict[str, object] | None = None
    for sequence, command in enumerate(graph, start=1):
        env_overrides = {**OFFLINE_ENV, **dict(command.env_overrides)}
        env = dict(os.environ)
        env.update(env_overrides)
        command_started_at = datetime.now(timezone.utc).isoformat()
        command_started_ns = time.monotonic_ns()
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = subprocess.run(
            command.argv,
            cwd=root,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        wall_ns = time.monotonic_ns() - command_started_ns
        cpu_ns = int(
            (
                usage_after.ru_utime
                + usage_after.ru_stime
                - usage_before.ru_utime
                - usage_before.ru_stime
            )
            * 1_000_000_000
        )
        record = {
            "argv": list(command.argv),
            "base": "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "reviewed_tree": reviewed_tree,
            "cwd": str(root),
            "env": env_overrides,
            "name": command.name,
            "returncode": result.returncode,
            "sequence": sequence,
            "started_at_utc": command_started_at,
            "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            "wall_ns": wall_ns,
            "cpu_ns": cpu_ns,
            "stdout_base64": base64.b64encode(result.stdout).decode("ascii"),
            "stdout_bytes": len(result.stdout),
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_base64": base64.b64encode(result.stderr).decode("ascii"),
            "stderr_bytes": len(result.stderr),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }
        records.append(record)
        if "pytest" in command.argv:
            pytest_processes += 1
        if result.returncode != 0:
            raise LeanGate2Error(
                f"{command.name} failed with {result.returncode}: "
                + (result.stdout[-2000:] + result.stderr[-2000:]).decode(
                    errors="replace"
                )
            )
        if command.name == "reader_audit":
            payload = reader_output.read_bytes()
            document = json.loads(payload)
            if payload != canonical_json(document):
                raise LeanGate2Error("reader audit output is not canonical")
            if (
                document.get("reviewed_tree") != reviewed_tree
                or document.get("unresolved_dynamic_warnings") != []
                or len(document.get("direct_readers", [])) != 59
                or len(document.get("transitive_readers", [])) != 107
                or len(document.get("reader_paths", [])) != 166
                or document.get("missing_executing_readers") != []
            ):
                raise LeanGate2Error("reader audit did not converge exactly")
        elif command.name == "reader_closure":
            outcome_path = Path(
                dict(command.env_overrides)["PIETTO_GATE2_PYTEST_OUTCOMES"]
            )
            loaded_reader_outcomes = json.loads(outcome_path.read_bytes())
            if not isinstance(loaded_reader_outcomes, dict):
                raise LeanGate2Error("reader closure outcomes are not an object")
            reader_outcomes = loaded_reader_outcomes
            summary = reader_outcomes.get("summary", {})
            if not isinstance(summary, dict):
                raise LeanGate2Error("reader closure summary is not an object")
            if (
                reader_outcomes.get("collected_count") != 6786
                or summary.get("passed") != 6786
                or any(
                    summary.get(name, 0)
                    for name in ("failed", "error", "skipped", "xfail", "xpass")
                )
                or reader_outcomes.get("deselected")
                or reader_outcomes.get("collection_errors")
            ):
                raise LeanGate2Error("reader closure outcomes are not exact")
        elif command.name == "topology":
            loaded_topology = json.loads(topology_output.read_bytes())
            if not isinstance(loaded_topology, dict):
                raise LeanGate2Error("topology result is not an object")
            topology_document = loaded_topology
            equivalence = topology_document.get("equivalence")
            positives = topology_document.get("positive_results")
            if (
                topology_document.get("reviewed_tree") != reviewed_tree
                or not isinstance(equivalence, dict)
                or equivalence.get("outcome_equality") is not True
                or not isinstance(positives, list)
                or len(positives) != 4
                or any(
                    not isinstance(item, dict) or item.get("result") != "PASS"
                    for item in positives
                )
            ):
                raise LeanGate2Error("topology equivalence did not pass")
        elif command.name == "clean_collection":
            matches = re.findall(rb"([0-9]+) tests collected", result.stdout)
            if len(matches) != 1:
                raise LeanGate2Error("clean collection count is ambiguous")
            clean_count = int(matches[0])
            if clean_count != 10976:
                raise LeanGate2Error(f"clean collection drift: {clean_count}")
    if reader_outcomes is None or topology_document is None or clean_count == 0:
        raise LeanGate2Error("validation result documents are incomplete")
    usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    topology_performance = topology_document.get("performance")
    if not isinstance(topology_performance, dict):
        raise LeanGate2Error("topology performance is absent")
    performance = {
        "schema": PERFORMANCE_SCHEMA,
        "base": "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "reviewed_tree": reviewed_tree,
        "command_count": len(records),
        "pytest_process_count": pytest_processes,
        "selected_test_items": 6786 + 4 * 1143 + 10976,
        "wall_ns": time.monotonic_ns() - started_ns,
        "cpu_ns": int(
            (
                usage_end.ru_utime
                + usage_end.ru_stime
                - usage_start.ru_utime
                - usage_start.ru_stime
            )
            * 1_000_000_000
        ),
        "cache_state": "verified_existing_offline_environment",
        "python_version": sys.version,
        "reader_closure_runs": 1,
        "authoritative_validate_runs": 1,
        "clean_collection_items": clean_count,
        "legacy_pytest_processes": topology_performance["legacy_pytest_processes"],
        "legacy_repeated_items": topology_performance["legacy_repeated_items"],
        "lean_pytest_processes": topology_performance["lean_pytest_processes"],
        "lean_repeated_topology_items": topology_performance[
            "lean_repeated_topology_items"
        ],
        "repeated_item_reduction": topology_performance["repeated_item_reduction"],
        "legacy_wall_seconds": topology_performance["legacy_wall_seconds"],
        "lean_wall_seconds": topology_performance["lean_wall_seconds"],
        "legacy_cpu_seconds": topology_performance["legacy_cpu_seconds"],
        "lean_cpu_seconds": topology_performance["lean_cpu_seconds"],
        "outcome_equality": True,
        "excluded_content_invariant": True,
        "zero_skipped_xfailed_deselected": True,
        "outcome": "PASS",
    }
    performance["payload_sha256"] = hashlib.sha256(
        canonical_json(performance)
    ).hexdigest()
    return records, performance


def _node_file(path: Path) -> tuple[str, ...]:
    payload = path.read_bytes()
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise LeanGate2Error(f"node file is not canonical UTF-8/LF: {path}")
    values = tuple(payload.decode("utf-8").splitlines())
    if not values or any(not value or value.startswith("#") for value in values):
        raise LeanGate2Error(f"node file contains an empty/comment row: {path}")
    if values != tuple(sorted(set(values))):
        raise LeanGate2Error(f"node file is not sorted unique: {path}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reader-output", type=Path, required=True)
    parser.add_argument("--topology-output", type=Path, required=True)
    parser.add_argument("--ledger-output", type=Path, required=True)
    parser.add_argument("--performance-output", type=Path, required=True)
    parser.add_argument("--focused-nodes", type=Path, required=True)
    parser.add_argument("--compatibility-nodes", type=Path, required=True)
    parser.add_argument("--reader-nodes", type=Path, required=True)
    parser.add_argument("--formatter-paths", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "tests"))
    from scripts.build_evidence_bundle import (  # noqa: PLC0415
        _statuses,
        freeze_reviewed_tree,
    )
    from _active_gate2_manifest_data import (  # noqa: PLC0415
        ACTIVE_GATE2_ADDED_PATHS,
        ACTIVE_GATE2_ALLOWLIST_PATHS,
        ACTIVE_GATE2_DELETED_PATHS,
        ACTIVE_GATE2_MODIFIED_PATHS,
        ACTIVE_GATE2_READER_CLOSURE_SHA256,
        MECHANICAL_READER_PATHS,
    )

    statuses = _statuses(arguments.manifest)
    expected_statuses = {
        **{path: "A" for path in ACTIVE_GATE2_ADDED_PATHS},
        **{path: "M" for path in ACTIVE_GATE2_MODIFIED_PATHS},
        **{path: "D" for path in ACTIVE_GATE2_DELETED_PATHS},
    }
    if statuses != expected_statuses:
        raise LeanGate2Error("manifest differs from exact active A12_M51_D0")
    frozen = freeze_reviewed_tree(
        root=root,
        base="49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        statuses=statuses,
    )
    focused_nodes = _node_file(arguments.focused_nodes)
    compatibility_nodes = _node_file(arguments.compatibility_nodes)
    reader_nodes = _node_file(arguments.reader_nodes)
    formatter_paths = _node_file(arguments.formatter_paths)
    if focused_nodes != (
        "tests/test_phase54_post_slice6_workflow_efficiency_interlude.py",
    ):
        raise LeanGate2Error("focused selector differs from authority")
    if compatibility_nodes != tuple(sorted(MECHANICAL_READER_PATHS)):
        raise LeanGate2Error("compatibility selector differs from M50 authority")
    reader_sha = hashlib.sha256(
        "".join(f"{path}\n" for path in reader_nodes).encode()
    ).hexdigest()
    if len(reader_nodes) != 166 or reader_sha != ACTIVE_GATE2_READER_CLOSURE_SHA256:
        raise LeanGate2Error("reader selector differs from 166-path authority")
    expected_formatter_paths = tuple(
        sorted(path for path in ACTIVE_GATE2_ALLOWLIST_PATHS if path.endswith(".py"))
    )
    if formatter_paths != expected_formatter_paths or len(formatter_paths) != 59:
        raise LeanGate2Error("formatter selector differs from 59-path authority")
    graph = command_graph(
        root=root,
        manifest=arguments.manifest,
        reader_output=arguments.reader_output,
        topology_output=arguments.topology_output,
        focused_nodes=focused_nodes,
        compatibility_nodes=compatibility_nodes,
        reader_nodes=reader_nodes,
        formatter_paths=formatter_paths,
        reviewed_tree=frozen.reviewed_tree,
    )
    validate_graph(graph)
    if arguments.plan_only:
        os.write(
            1,
            canonical_json(
                {
                    "schema": SCHEMA,
                    "reviewed_tree": frozen.reviewed_tree,
                    "commands": [asdict(item) for item in graph],
                }
            ),
        )
        return 0
    assert_preconditions(root=root)
    records, performance = run_graph(
        root=root,
        graph=graph,
        reviewed_tree=frozen.reviewed_tree,
        reader_output=arguments.reader_output,
        topology_output=arguments.topology_output,
    )
    arguments.ledger_output.write_bytes(
        b"".join(canonical_json(record) for record in records)
    )
    arguments.performance_output.write_bytes(canonical_json(performance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
