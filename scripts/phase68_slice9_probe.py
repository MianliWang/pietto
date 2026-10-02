#!/usr/bin/env python3
"""Explicit private S09 source/installed PostgreSQL ADBC product observations."""

import argparse
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("worker", "preflight", "campaign"), required=True
    )
    parser.add_argument(
        "--origin", choices=("source", "installed", "both"), required=True
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--tree")
    parser.add_argument("--readiness", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument(
        "--groups", nargs="+", choices=("ordinary", "refined", "guarded", "controls")
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.origin in ("source", "both"):
        sys.path.insert(0, str(root / "src"))
    probe = importlib.import_module("_pietto_phase68_slice9_probe")

    if args.mode == "worker":
        if args.origin == "both" or args.input is None or sys.stdin.read(1) != "1":
            parser.error("registered worker input required")
        if json.loads(args.input.read_text())["origin"] != args.origin:
            parser.error("worker origin mismatch")
        probe.worker(args.input)
    else:
        if args.directory is None or args.ledger is None or args.tree is None:
            parser.error("directory, ledger and tree required")
        probe.campaign(
            args.directory,
            args.ledger,
            args.tree,
            mode=args.mode,
            groups=args.groups
            or (
                ("controls", "ordinary", "refined", "guarded")
                if args.mode == "campaign"
                else ("ordinary", "refined", "guarded")
            ),
            origins_selected=("source", "installed")
            if args.origin == "both"
            else (args.origin,),
            readiness=args.readiness,
            wheel=args.wheel,
        )


if __name__ == "__main__":
    main()
