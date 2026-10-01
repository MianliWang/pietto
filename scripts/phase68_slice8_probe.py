#!/usr/bin/env python3
"""Explicit S08 source/installed MySQL product acquisition, never ordinary pytest."""

import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=(
            "worker",
            "preflight",
            "refinement-smoke",
            "reset-smoke",
            "campaign",
            "controls",
        ),
        required=True,
    )
    parser.add_argument("--origin", choices=("source", "installed"), required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--tree")
    parser.add_argument("--readiness", type=Path)
    parser.add_argument("--reuse-source", type=Path)
    parser.add_argument("--reuse-ordinary", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.origin == "source":
        sys.path.insert(0, str(root / "src"))
    from _pietto_phase68_slice8_probe import worker, campaign, control_family

    if args.mode == "worker":
        if args.input is None:
            parser.error("worker requires input")
        config = json.loads(args.input.read_text())
        if config["origin"] != args.origin:
            parser.error("origin mismatch")
        if sys.stdin.read(1) != "1":
            parser.error("worker registration gate missing")
        worker(args.input)
    else:
        if args.directory is None or args.ledger is None or not args.tree:
            parser.error("group requires directory/ledger/tree")
        if args.mode == "controls":
            control_family(args.directory, args.ledger, args.tree)
        else:
            campaign(
                args.directory,
                args.ledger,
                args.tree,
                mode=args.mode,
                readiness=args.readiness,
                reuse_source=args.reuse_source,
                reuse_ordinary=args.reuse_ordinary,
            )


if __name__ == "__main__":
    main()
