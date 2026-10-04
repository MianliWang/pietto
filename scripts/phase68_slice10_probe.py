#!/usr/bin/env python3
"""Explicit bounded S10 native acceptance; importing does not acquire a database."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("bound", "source-profile", "representative", "campaign"),
        default="bound",
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--interpreter", type=Path, required=True)
    parser.add_argument("--target", choices=("postgres", "mysql"), default="postgres")
    parser.add_argument("--origin", choices=("source", "installed"), default="source")
    parser.add_argument("--entry", choices=("live", "bundle"), default="bundle")
    parser.add_argument(
        "--cells",
        nargs="+",
        choices=("source:live", "source:bundle", "installed:live", "installed:bundle"),
    )
    parser.add_argument("--representative-cells", nargs="+")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--readiness", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    from _pietto_phase68_slice10_probe import pilot

    if args.mode == "campaign":
        from _pietto_phase68_slice10_probe import complete_campaign

        if args.wheel is None or args.readiness is None:
            parser.error("campaign requires explicit --wheel and --readiness")
        report = complete_campaign(
            args.directory, args.ledger, args.interpreter, args.wheel, args.readiness
        )
    elif args.mode == "representative":
        from _pietto_phase68_slice10_probe import representative_pilot

        report = representative_pilot(
            args.directory,
            args.ledger,
            target=args.target,
            cells=None
            if args.representative_cells is None
            else tuple(tuple(c.split(":")) for c in args.representative_cells),
        )
    elif args.mode == "source-profile":
        from _pietto_phase68_slice10_probe import source_profile_pilot

        report = source_profile_pilot(args.directory, args.ledger)
    else:
        report = pilot(
            args.directory,
            args.ledger,
            args.interpreter,
            origin=args.origin,
            entry=args.entry,
            cells=None
            if args.cells is None
            else tuple(tuple(c.split(":")) for c in args.cells),
            wheel=args.wheel,
            target=args.target,
        )
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
