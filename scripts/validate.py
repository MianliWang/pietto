"""Run Pietto's authoritative local validation gates without modifying source."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
    ),
    ("tests", ("uv", "run", "pytest")),
)

PYTEST_GATE_NAME = "tests"
PYTEST_COMMAND = ("uv", "run", "pytest")
PYTEST_DIST_CHOICES = ("loadfile", "loadscope")


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Pietto's authoritative local validation gates.",
    )
    parser.add_argument(
        "--timings",
        action="store_true",
        help="print elapsed time for each validation gate and the total run",
    )
    parser.add_argument(
        "--pytest-workers",
        metavar="{off,auto,logical,N}",
        help=(
            "opt into pytest-xdist workers: off, auto, logical CPU count, "
            "or a positive integer"
        ),
    )
    parser.add_argument(
        "--pytest-dist",
        choices=PYTEST_DIST_CHOICES,
        help="pytest-xdist distribution mode to use when workers are enabled",
    )
    parser.add_argument(
        "--pytest-maxprocesses",
        type=_positive_int,
        help="positive upper bound for enabled pytest worker modes",
    )
    return parser


def _parse_worker_mode(
    parser: argparse.ArgumentParser,
    worker_value: str,
) -> str | int:
    if worker_value in {"off", "auto", "logical"}:
        return worker_value
    try:
        return _positive_int(worker_value)
    except argparse.ArgumentTypeError:
        parser.error(
            "--pytest-workers must be off, auto, logical, or a positive integer"
        )


def _pytest_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> tuple[str, ...]:
    worker_value = args.pytest_workers
    if worker_value is None or worker_value == "off":
        if args.pytest_dist is not None:
            parser.error("--pytest-dist requires enabled pytest workers")
        if args.pytest_maxprocesses is not None:
            parser.error("--pytest-maxprocesses requires enabled pytest workers")
        return PYTEST_COMMAND

    worker_mode = _parse_worker_mode(parser, worker_value)
    dist_mode = args.pytest_dist or "loadfile"
    command = [*PYTEST_COMMAND]

    if worker_mode == "auto":
        command.extend(("-n", "auto"))
        if args.pytest_maxprocesses is not None:
            command.extend(("--maxprocesses", str(args.pytest_maxprocesses)))
    elif worker_mode == "logical":
        worker_count = max(os.cpu_count() or 1, 1)
        if args.pytest_maxprocesses is not None:
            worker_count = min(worker_count, args.pytest_maxprocesses)
        command.extend(("-n", str(worker_count)))
    else:
        worker_count = worker_mode
        if args.pytest_maxprocesses is not None:
            worker_count = min(worker_count, args.pytest_maxprocesses)
        command.extend(("-n", str(worker_count)))

    command.append(f"--dist={dist_mode}")
    return tuple(command)


def _resolved_gates(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    pytest_command = _pytest_command(args, parser)
    return tuple(
        (name, pytest_command if name == PYTEST_GATE_NAME else command)
        for name, command in GATES
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run validation gates in order and return the first failing exit code."""

    parser = _build_parser()
    args = parser.parse_args(()) if argv is None else parser.parse_args(argv)
    gates = _resolved_gates(args, parser)
    total_started = time.perf_counter() if args.timings else 0.0

    for name, command in gates:
        print(f"[validate] {name}: {shlex.join(command)}", flush=True)
        gate_started = time.perf_counter() if args.timings else 0.0
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if args.timings:
            gate_elapsed = time.perf_counter() - gate_started
            print(f"[validate] {name} completed in {gate_elapsed:.3f}s", flush=True)
        if result.returncode != 0:
            if args.timings:
                total_elapsed = time.perf_counter() - total_started
                print(
                    f"[validate] total completed in {total_elapsed:.3f}s",
                    flush=True,
                )
            return result.returncode
    if args.timings:
        total_elapsed = time.perf_counter() - total_started
        print(f"[validate] total completed in {total_elapsed:.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
