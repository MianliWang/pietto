#!/usr/bin/env python3
"""Explicit bounded S15 delivery families; importing acquires nothing."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("suite", "native"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--capture-interpreter", type=Path, required=True)
    parser.add_argument("--delivery-interpreter", type=Path, required=True)
    parser.add_argument("--origin", choices=("source", "installed"), default="source")
    parser.add_argument("--target", choices=("postgres", "mysql"))
    parser.add_argument(
        "--cells",
        nargs="+",
        default=("source:live",),
        choices=("source:live", "source:bundle", "installed:live", "installed:bundle"),
    )
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--old-wheel", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice15_probe as probe

    if args.family == "suite":
        report = probe.suite(
            args.directory,
            args.ledger,
            args.delivery_interpreter,
            origin=args.origin,
            wheel=args.wheel,
            old_wheel=args.old_wheel,
        )
    else:
        report = probe.native(
            args.directory,
            args.ledger,
            args.capture_interpreter,
            args.delivery_interpreter,
            target=args.target,
            cells=[tuple(c.split(":")) for c in args.cells],
            wheel=args.wheel,
        )
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
