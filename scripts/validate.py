"""Run Pietto's authoritative local validation gates without modifying source."""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import signal
import subprocess
import sys
import time
import threading
from typing import NamedTuple
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
PYTEST_MAX_RESOURCE_WORKERS = 4


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
    workers = min(
        _usable_cpu_count(),
        memory_capacity,
        PYTEST_MAX_RESOURCE_WORKERS,
    )
    if maximum is not None:
        workers = min(workers, maximum)
    return max(workers, 1)


# Internal local safety policy; startup worker selection remains independent.
OOM_SAMPLE_SECONDS = 1.0
OOM_CRITICAL_BYTES = 768 * 1024**2
OOM_HARD_BYTES = 3 * 1024**3 // 2
OOM_PRESSURE_BYTES = 3 * 1024**3
OOM_PSI_FULL_AVG10 = 4.0
OOM_CONSECUTIVE_SAMPLES = 3
OOM_TERM_GRACE_SECONDS = 5.0
RESOURCE_PRESSURE_EXIT = 75


class MemorySample(NamedTuple):
    total: int
    available: int
    psi: float | None
    events: tuple[int, int] | None


def _memory_psi() -> float | None:
    text = _read_text("/proc/pressure/memory")
    for line in (text or "").splitlines():
        fields = line.split()
        if fields and fields[0] == "full":
            values = dict(field.split("=", 1) for field in fields[1:] if "=" in field)
            try:
                value = float(values["avg10"])
            except (KeyError, ValueError):
                return None
            return value if math.isfinite(value) and 0 <= value <= 100 else None
    return None


def _memory_events() -> tuple[int, int] | None:
    text = _read_text("/sys/fs/cgroup/memory.events")
    values = dict(
        line.split() for line in (text or "").splitlines() if len(line.split()) == 2
    )
    if not all(values.get(key, "").isdigit() for key in ("oom", "oom_kill")):
        return None
    return int(values["oom"]), int(values["oom_kill"])


def _memory_sample() -> MemorySample | None:
    try:
        memory = _memory_snapshot()
    except (ValueError, IndexError):
        return None
    if memory is None:
        return None
    total, available = memory
    if total <= 0 or not 0 <= available <= total:
        return None
    return MemorySample(total, available, _memory_psi(), _memory_events())


def _event_deltas(
    sample: MemorySample, baseline: MemorySample
) -> tuple[int | None, int | None]:
    if sample.events is None or baseline.events is None:
        return None, None
    return (
        max(0, sample.events[0] - baseline.events[0]),
        max(0, sample.events[1] - baseline.events[1]),
    )


def _pressure_trigger(
    sample: MemorySample, baseline: MemorySample, consecutive: int
) -> tuple[str | None, int]:
    oom, killed = _event_deltas(sample, baseline)
    if killed:
        return "cgroup_oom_kill_increased", consecutive
    if oom:
        return "cgroup_oom_increased", consecutive
    if sample.available <= OOM_CRITICAL_BYTES:
        return "critical_available", consecutive
    hard = sample.available <= max(OOM_HARD_BYTES, sample.total // 10)
    pressure = (
        sample.psi is not None
        and sample.psi >= OOM_PSI_FULL_AVG10
        and sample.available <= max(OOM_PRESSURE_BYTES, sample.total // 5)
    )
    consecutive = consecutive + 1 if hard or pressure else 0
    reason = "sustained_low_available" if hard else "sustained_memory_pressure"
    return (reason if consecutive >= OOM_CONSECUTIVE_SAMPLES else None), consecutive


def _oom_guard_enabled(mode: str, parser: argparse.ArgumentParser) -> bool:
    if mode == "off":
        return False
    if mode == "auto" and any(
        value and value.lower() not in {"0", "false", "no", "off"}
        for value in (os.environ.get("GITHUB_ACTIONS"), os.environ.get("CI"))
    ):
        return False
    reason = None
    if sys.platform != "linux":
        reason = "Linux process-group supervision is unsupported on this platform"
    elif not all(
        hasattr(os, name)
        for name in (
            "setsid",
            "killpg",
            "getpgrp",
            "waitid",
            "P_PID",
            "WEXITED",
            "WNOHANG",
            "WNOWAIT",
        )
    ):
        reason = "owned process-group/non-reaping wait capability is unavailable"
    elif threading.current_thread() is not threading.main_thread():
        reason = "signal supervision requires the main thread"
    elif signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        reason = "SIGCHLD handling does not preserve child wait ownership"
    elif _memory_sample() is None:
        reason = "effective memory telemetry is unavailable"
    if reason is not None:
        if mode == "on":
            parser.error("OOM guard unavailable: " + reason)
        print("[validate] OOM guard unavailable: " + reason, flush=True)
        return False
    return True


def _terminate_gate(child: subprocess.Popen[bytes]) -> str:
    # Never poll/reap during this sequence: the unreaped leader pins its PID,
    # even if it exits before a grandchild, so this PGID cannot be reused.
    if child.pid == os.getpgrp():
        raise RuntimeError("refusing to signal the validator process group")
    termination = "SIGTERM"
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return "already_exited"
    deadline = time.monotonic() + OOM_TERM_GRACE_SECONDS
    while time.monotonic() < deadline:
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    else:
        try:
            os.killpg(child.pid, signal.SIGKILL)
            termination = "SIGTERM_SIGKILL"
        except ProcessLookupError:
            pass
    child.wait()
    return termination


def _raise_cancellation(signum: int) -> None:
    if signum == signal.SIGINT:
        raise KeyboardInterrupt
    raise SystemExit(128 + signum)


def _run_guarded_gate(name: str, command: tuple[str, ...], mode: str) -> int:
    baseline = _memory_sample()
    if baseline is None:
        print(
            "[validate] OOM guard unavailable: effective memory telemetry lost",
            flush=True,
        )
        if mode == "on":
            return 2
        return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode
    started = time.perf_counter()
    child: subprocess.Popen[bytes] | None = None
    cancelled: int | None = None
    previous = {}

    def cancel(signum: int, _frame: object) -> None:
        # Defer raising until Popen has returned its owned handle. This also
        # lets cleanup finish if a second cancellation arrives during grace.
        nonlocal cancelled
        if cancelled is None:
            cancelled = signum

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, cancel)
        child = subprocess.Popen(command, cwd=REPO_ROOT, start_new_session=True)
        consecutive = 0
        unavailable_noticed = False
        while True:
            if cancelled is not None:
                _raise_cancellation(cancelled)
            if (
                os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                is not None
            ):
                return child.wait()
            sample = _memory_sample()
            if sample is None:
                consecutive = 0
                if not unavailable_noticed:
                    print(
                        "[validate] OOM guard unavailable: runtime memory telemetry lost",
                        flush=True,
                    )
                    unavailable_noticed = True
                if mode == "on":
                    _terminate_gate(child)
                    return 2
            else:
                trigger, consecutive = _pressure_trigger(sample, baseline, consecutive)
                if trigger is not None:
                    if cancelled is not None:
                        _raise_cancellation(cancelled)
                    # A completed ordinary gate keeps its actual exit code.
                    if (
                        os.waitid(
                            os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
                        )
                        is not None
                    ):
                        return child.wait()
                    termination = _terminate_gate(child)
                    if termination == "already_exited":
                        return child.wait()
                    oom, killed = _event_deltas(sample, baseline)
                    record = {
                        "format": "pietto.validation-resource-pressure.v1",
                        "gate": name,
                        "reason": "RESOURCE_PRESSURE_ABORTED",
                        "trigger": trigger,
                        "elapsed_seconds": round(time.perf_counter() - started, 3),
                        "effective_total_bytes": sample.total,
                        "effective_available_bytes": sample.available,
                        "hard_threshold_bytes": max(OOM_HARD_BYTES, sample.total // 10),
                        "critical_threshold_bytes": OOM_CRITICAL_BYTES,
                        "psi_full_avg10": sample.psi,
                        "memory_events_oom_delta": oom,
                        "memory_events_oom_kill_delta": killed,
                        "child_pid": child.pid,
                        "termination": termination,
                    }
                    print(
                        "[validate] resource-pressure "
                        + json.dumps(record, sort_keys=True),
                        flush=True,
                    )
                    return RESOURCE_PRESSURE_EXIT
            time.sleep(OOM_SAMPLE_SECONDS)
    except ChildProcessError:
        # Another reaper invalidated ownership; never signal a reusable PID.
        print("[validate] OOM guard unavailable: child wait ownership lost", flush=True)
        return 2
    except BaseException:
        if child is not None and child.returncode is None:
            _terminate_gate(child)
        raise
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if cancelled is not None:
            _raise_cancellation(cancelled)


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
        "--oom-guard",
        choices=("auto", "on", "off"),
        default="auto",
        help="local Linux runtime memory guard (default: auto; disabled automatically in CI)",
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
    guarded = _oom_guard_enabled(args.oom_guard, parser)
    if guarded:
        print("[validate] OOM guard enabled: Linux owned process groups", flush=True)
    total_started = time.perf_counter() if args.timings else 0.0

    for name, command in gates:
        print(f"[validate] {name}: {shlex.join(command)}", flush=True)
        gate_started = time.perf_counter() if args.timings else 0.0
        returncode = (
            _run_guarded_gate(name, command, args.oom_guard)
            if guarded
            else subprocess.run(command, cwd=REPO_ROOT, check=False).returncode
        )
        if args.timings:
            gate_elapsed = time.perf_counter() - gate_started
            print(f"[validate] {name} completed in {gate_elapsed:.3f}s", flush=True)
        if returncode != 0:
            if args.timings:
                total_elapsed = time.perf_counter() - total_started
                print(
                    f"[validate] total completed in {total_elapsed:.3f}s",
                    flush=True,
                )
            return returncode
    if args.timings:
        total_elapsed = time.perf_counter() - total_started
        print(f"[validate] total completed in {total_elapsed:.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
