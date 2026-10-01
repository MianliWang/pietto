#!/usr/bin/env python3
"""Explicit S07 bounded native acceptance; never ordinary pytest DB work."""

import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("basic", "worker", "preflight", "campaign"), required=True
    )
    parser.add_argument(
        "--route", choices=("postgres_rows", "postgres_adbc", "mysql_rows")
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--tree")
    parser.add_argument("--origin", choices=("source", "installed"), required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--readiness", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.origin == "source":
        sys.path.insert(0, str(root / "src"))
    from _pietto_phase68_slice7_probe import (
        small_family,
        native_group,
        worker,
        ledger,
        write,
    )

    if args.mode == "worker":
        if args.input is None:
            parser.error("worker requires --input")
        config = json.loads(args.input.read_text())
        if config["origin"] != args.origin:
            parser.error("worker origin mismatch")
        worker(args.input)
        return
    if args.directory is None or args.ledger is None or not args.tree:
        parser.error("native group requires directory, ledger and tree")
    if args.mode == "campaign":
        if args.readiness is None:
            parser.error("campaign requires exact-input readiness")
        ready = json.loads(args.readiness.read_text())
        if ready["status"] != "GREEN_FOR_CURRENT_INPUTS" or ready["tree"] != args.tree:
            parser.error("campaign readiness is not green for this tree")
        for path, expected in ready["inputs"].items():
            import hashlib

            if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
                parser.error("campaign producing inputs changed")
        args.directory.mkdir(mode=0o700)
        ledger(
            args.ledger,
            dict(
                kind="complete_s07_live_campaign_start",
                tree=args.tree,
                readiness=str(args.readiness),
                directory=str(args.directory),
            ),
            complete_s07_live_campaign_starts=1,
        )
        reports = []
        for route in ("postgres_rows", "mysql_rows", "postgres_adbc"):
            directory = args.directory / ("pietto-phase68-slice07-" + route)
            native_group(
                directory,
                args.ledger,
                "mysql" if route == "mysql_rows" else "postgres",
                route,
                args.tree,
                mode="campaign",
                python=sys.executable,
            )
            reports.append(str(directory / "pietto-phase68-slice07-observations.json"))
        write(
            args.directory / "pietto-phase68-slice07-campaign.json",
            dict(
                tree=args.tree,
                readiness=str(args.readiness),
                groups=reports,
                result="PASS_COMPLETE_NATIVE_GROUPS",
            ),
        )
        return
    if args.route is None:
        parser.error("targeted group requires --route")
    target = "mysql" if args.route == "mysql_rows" else "postgres"
    if args.mode == "basic":
        small_family(args.directory, args.ledger, target, args.route, args.tree)
    else:
        native_group(
            args.directory,
            args.ledger,
            target,
            args.route,
            args.tree,
            mode="preflight",
            python=sys.executable,
        )


if __name__ == "__main__":
    main()
