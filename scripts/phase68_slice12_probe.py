#!/usr/bin/env python3
"""Explicit bounded S12 capture families; importing acquires nothing."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("suite", "bridge", "representatives"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--interpreter", type=Path, required=True)
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
    parser.add_argument("--core-interpreter", type=Path)
    parser.add_argument("--old-wheel", type=Path)
    parser.add_argument("--group", choices=("ordinary", "guarded"))
    parser.add_argument(
        "--selected", nargs="*", default=(), help="group:case[:variant]"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice12_probe as probe

    if args.family == "suite":
        report = probe.arrow_suite(
            args.directory,
            args.ledger,
            args.interpreter,
            cells=args.cells,
            wheel=args.wheel,
        )
    elif args.family == "representatives":
        selected = tuple(
            (parts[0], parts[1], parts[2] if len(parts) > 2 else None)
            for parts in (item.split(":") for item in args.selected)
        )
        report = probe.representatives(
            args.directory,
            args.ledger,
            args.interpreter,
            target=args.target,
            group=args.group,
            selected=selected,
            cells=[c.split(":") for c in args.cells],
            wheel=args.wheel,
        )
    else:
        report = probe.bridge(
            args.directory,
            args.ledger,
            args.interpreter,
            target=args.target,
            cells=tuple(tuple(c.split(":")) for c in args.cells),
            wheel=args.wheel,
            core=args.core_interpreter,
            old_wheel=args.old_wheel,
        )
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
