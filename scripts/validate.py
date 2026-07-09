"""Run Pietto's authoritative local validation gates without modifying source."""

from __future__ import annotations

import argparse
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Pietto's authoritative local validation gates.",
    )
    parser.add_argument(
        "--timings",
        action="store_true",
        help="print elapsed time for each validation gate and the total run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run validation gates in order and return the first failing exit code."""

    parser = _build_parser()
    args = parser.parse_args(()) if argv is None else parser.parse_args(argv)
    total_started = time.perf_counter() if args.timings else 0.0

    for name, command in GATES:
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
