#!/usr/bin/env python3
"""Explicit bounded S13 replay families; importing acquires nothing."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("suite", "bridge", "representatives"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--capture-interpreter", type=Path, required=True)
    parser.add_argument("--replay-interpreter", type=Path, required=True)
    parser.add_argument("--target", choices=("postgres", "mysql"))
    parser.add_argument(
        "--cells",
        nargs="+",
        required=True,
        choices=(
            "source",
            "installed",
            "source:live",
            "source:bundle",
            "installed:live",
            "installed:bundle",
        ),
    )
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--old-wheel", type=Path)
    parser.add_argument(
        "--selected", nargs="*", default=(), help="group:case[:variant]"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice13_probe as probe

    common = dict(
        directory=args.directory,
        ledger=args.ledger,
        capture_interpreter=args.capture_interpreter,
        replay_interpreter=args.replay_interpreter,
        wheel=args.wheel,
    )
    if args.family == "suite":
        report = probe.suite(cells=args.cells, old_wheel=args.old_wheel, **common)
    elif args.family == "bridge":
        report = probe.bridge(
            target=args.target,
            cells=tuple(tuple(c.split(":")) for c in args.cells),
            old_wheel=args.old_wheel,
            **common,
        )
    else:
        report = probe.representatives(
            target=args.target,
            selected=tuple(tuple(item.split(":")) for item in args.selected),
            cells=[c.split(":") for c in args.cells],
            **common,
        )
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
