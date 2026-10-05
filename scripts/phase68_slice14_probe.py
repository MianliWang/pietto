#!/usr/bin/env python3
"""Explicit bounded S14 extraction-recovery families; importing acquires nothing."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("matrix", "histories"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--capture-interpreter", type=Path, required=True)
    parser.add_argument("--replay-interpreter", type=Path, required=True)
    parser.add_argument("--target", choices=("postgres", "mysql"), required=True)
    parser.add_argument("--group", choices=("refined", "guarded"), default="refined")
    parser.add_argument(
        "--cells",
        nargs="+",
        required=True,
        choices=("source:live", "source:bundle", "installed:live", "installed:bundle"),
    )
    parser.add_argument("--wheel", type=Path)
    parser.add_argument(
        "--selected", nargs="*", default=None, help="group:case[:variant]"
    )
    parser.add_argument("--only", nargs="*", default=None, help="history names")
    parser.add_argument("--part", default="0/1", help="index/count of the denominator")
    combos = ("source:live", "source:bundle", "installed:live", "installed:bundle")
    parser.add_argument("--extra-cells", nargs="*", default=(), choices=combos)
    parser.add_argument(
        "--extra-selected", nargs="*", default=(), help="group:case:variant"
    )
    parser.add_argument("--drift-cells", nargs="*", default=(), choices=combos)
    parser.add_argument(
        "--histories", choices=("source", "installed"), help="also run A-L here"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice14_probe as probe

    if args.family == "histories":
        origin = args.cells[0].split(":")[0]
        report = probe.r2_histories(
            args.directory,
            args.ledger,
            args.capture_interpreter,
            target=args.target,
            origin=origin,
            wheel=args.wheel,
            only=args.only,
        )
        print(report["status"], flush=True)
        return
    selected = None
    if args.selected is not None:
        selected = {
            (parts[0], parts[1], parts[2] if len(parts) > 2 else None)
            for parts in (item.split(":", 2) for item in args.selected)
        }
    report = probe.acquire_r2_group(
        args.directory,
        args.ledger,
        args.capture_interpreter,
        target=args.target,
        group=args.group,
        cells=[tuple(c.split(":")) for c in args.cells],
        wheel=args.wheel,
        selected=selected,
        part=tuple(int(x) for x in args.part.split("/")),
        extra_cells=[tuple(c.split(":")) for c in args.extra_cells],
        extra_selected={tuple(item.split(":", 2)) for item in args.extra_selected},
        drift_cells=[tuple(c.split(":")) for c in args.drift_cells],
        histories=args.histories,
    )
    probe.matrix_r1(
        report,
        args.directory,
        args.ledger,
        args.replay_interpreter,
        wheel=args.wheel,
    )
    print(report["status"], report["r1"], flush=True)


if __name__ == "__main__":
    main()
