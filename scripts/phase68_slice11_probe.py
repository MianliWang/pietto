#!/usr/bin/env python3
"""Explicit bounded S11 job-store native bridge; importing acquires nothing."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--interpreter", type=Path, required=True)
    parser.add_argument("--target", choices=("postgres", "mysql"), required=True)
    parser.add_argument(
        "--cells",
        nargs="+",
        required=True,
        choices=("source:live", "source:bundle", "installed:live", "installed:bundle"),
    )
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--core-interpreter", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    from _pietto_phase68_slice11_probe import bridge

    report = bridge(
        args.directory,
        args.ledger,
        args.interpreter,
        target=args.target,
        cells=tuple(tuple(c.split(":")) for c in args.cells),
        wheel=args.wheel,
        core=args.core_interpreter,
    )
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
