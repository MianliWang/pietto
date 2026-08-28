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
PYTEST_WORKER_MEMORY_BYTES = 512 * 1024 * 1024
PYTEST_MIN_MEMORY_RESERVE_BYTES = 1024 * 1024 * 1024


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _cgroup_cpu_count() -> int | None:
    cpu_max = _read_text("/sys/fs/cgroup/cpu.max")
    if cpu_max is not None:
        quota, period = cpu_max.split()
        if quota != "max":
            return max(int(quota) // int(period), 1)

    quota = _read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_text("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota is not None and period is not None and int(quota) > 0:
        return max(int(quota) // int(period), 1)
    return None


def _usable_cpu_count() -> int:
    candidates = [os.cpu_count() or 1]
    process_cpu_count = getattr(os, "process_cpu_count", None)
    if process_cpu_count is not None:
        candidates.append(process_cpu_count() or 1)
    if hasattr(os, "sched_getaffinity"):
        candidates.append(len(os.sched_getaffinity(0)))
    cgroup_count = _cgroup_cpu_count()
    if cgroup_count is not None:
        candidates.append(cgroup_count)
    return max(min(candidates), 1)


def _memory_snapshot() -> tuple[int, int] | None:
    meminfo = _read_text("/proc/meminfo")
    if meminfo is None:
        return None
    values = {
        line.split(":", 1)[0]: int(line.split()[1]) * 1024
        for line in meminfo.splitlines()
        if ":" in line and line.split()[1].isdigit()
    }
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if total is None or available is None:
        return None

    for limit_path, current_path in (
        ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
        (
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
        ),
    ):
        limit_text = _read_text(limit_path)
        current_text = _read_text(current_path)
        if limit_text is None or not limit_text.isdigit():
            continue
        limit = int(limit_text)
        if limit >= 1 << 60:
            continue
        total = min(total, limit)
        if current_text is not None and current_text.isdigit():
            available = min(available, max(limit - int(current_text), 0))
        else:
            available = min(available, limit)
    return total, available


def _resource_worker_count(maximum: int | None = None) -> int:
    memory = _memory_snapshot()
    if memory is None:
        return 1
    total, available = memory
    reserve = max(PYTEST_MIN_MEMORY_RESERVE_BYTES, total // 5)
    memory_capacity = max(
        (available - reserve) // PYTEST_WORKER_MEMORY_BYTES,
        1,
    )
    workers = min(_usable_cpu_count(), memory_capacity)
    if maximum is not None:
        workers = min(workers, maximum)
    return max(workers, 1)


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
        metavar="{resource,off,auto,logical,N}",
        help=(
            "pytest worker mode (default: resource): resource-aware, off, auto, "
            "logical CPU count, or a positive integer"
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
    if worker_value in {"resource", "off", "auto", "logical"}:
        return worker_value
    try:
        return _positive_int(worker_value)
    except argparse.ArgumentTypeError:
        parser.error(
            "--pytest-workers must be resource, off, auto, logical, or a positive integer"
        )


def _pytest_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> tuple[str, ...]:
    worker_value = args.pytest_workers
    if worker_value == "off":
        if args.pytest_dist is not None:
            parser.error("--pytest-dist requires enabled pytest workers")
        if args.pytest_maxprocesses is not None:
            parser.error("--pytest-maxprocesses requires enabled pytest workers")
        return PYTEST_COMMAND

    worker_mode = (
        "resource" if worker_value is None else _parse_worker_mode(parser, worker_value)
    )
    dist_mode = args.pytest_dist or "loadfile"
    command = [*PYTEST_COMMAND]

    if worker_mode == "resource":
        worker_count = _resource_worker_count(args.pytest_maxprocesses)
        if worker_count == 1:
            return PYTEST_COMMAND
        command.extend(("-n", str(worker_count)))
    elif worker_mode == "auto":
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
