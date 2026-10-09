#!/usr/bin/env python3
"""Explicit bounded S19 families; importing acquires nothing. A family exits
non-zero when an original or independent checker rejects its raw facts.
storage/tuning/controls run each named origin/target in turn, each in its own
subdirectory of --directory."""

import argparse
import json
from pathlib import Path
import sys

FAMILIES = (
    "install",
    "compat",
    "matrix",
    "joint",
    "storage",
    "tuning",
    "controls",
    "consumer",
    "check",
)
CELLS = ("source:live", "source:bundle", "installed:live", "installed:bundle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=FAMILIES)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--install", type=Path, help="the install family directory")
    parser.add_argument("--house", type=Path, help="root holding the wheelhouse")
    parser.add_argument("--dist", type=Path, help="install: the wheel and sdist")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--interpreter", type=Path, help="base CPython for prefixes")
    parser.add_argument("--cache", type=Path, help="owned uv cache")
    parser.add_argument("--target", nargs="+", choices=("postgres", "mysql"))
    parser.add_argument("--origin", nargs="+", choices=("source", "installed"))
    parser.add_argument("--part", default="0/1", help="index/count of the matrix")
    parser.add_argument("--selected", nargs="*", help="group:case[:variant]")
    parser.add_argument("--cells", nargs="+", default=CELLS, choices=CELLS)
    parser.add_argument("--drift", action="store_true")
    parser.add_argument("--joint", action="store_true", help="matrix: J01/J02 too")
    parser.add_argument(
        "--queue",
        type=Path,
        help="matrix: the target's shared claims (each part still passes its own"
        " --part i/n label)",
    )
    parser.add_argument("--tree", help="controls: the producing tree")
    parser.add_argument(
        "--families", nargs="+", choices=("s03", "s09", "s08"), help="controls"
    )
    parser.add_argument(
        "--routes",
        nargs="+",
        choices=("postgres_rows", "postgres_adbc", "mysql_rows"),
        help="tuning: a subset of the targets' routes",
    )
    parser.add_argument("--label", help="consumer: the explicit LOCAL run label")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice18_probe as s18
    import _pietto_phase68_slice19_probe as probe

    def env(recipe):
        return args.install / (s18.PREFIX + "env-" + recipe) / "bin/python"

    cells = [tuple(c.split(":")) for c in args.cells]
    (target,) = args.target if args.family in ("matrix", "joint") else (None,)
    if args.install is not None:
        interpreters = {route: env(r) for route, r in s18.ROUTE_RECIPE.items()}
    if args.family == "install":
        report = s18.install(
            args.directory,
            args.ledger,
            dist=args.dist,
            interpreter=args.interpreter,
            cache=args.cache,
            house_root=args.house,
        )
    elif args.family == "compat":
        report = probe.compat(
            args.directory,
            args.ledger,
            wheel=args.wheel,
            current=env("arrow").parent.parent,
            house=args.house / (s18.PREFIX + "wheelhouse"),
            constraints=args.house / (s18.PREFIX + "constraints.txt"),
            interpreter=args.interpreter,
            cache=args.cache,
        )
    elif args.family == "matrix":
        selected = None
        if args.selected is not None:
            selected = {
                (p[0], p[1], p[2] if len(p) > 2 else None)
                for p in (item.split(":", 2) for item in args.selected)
            }
        report = probe.matrix(
            args.directory,
            args.ledger,
            target=target,
            interpreters=interpreters,
            saved_interpreter=env("arrow"),
            wheel=args.wheel,
            part=tuple(int(x) for x in args.part.split("/")),
            cells=cells,
            selected=selected,
            drift=args.drift,
            joint=args.joint,
            queue=args.queue,
        )
    elif args.family == "joint":
        report = s18.native(
            args.directory,
            args.ledger,
            target=target,
            interpreters=interpreters,
            union=env("union"),
            saved_interpreter=env("arrow"),
            wheel=args.wheel,
            cells=cells,
        )
    elif args.family == "storage":
        args.directory.mkdir(mode=0o700)
        report = {
            origin: probe.storage(
                args.directory / origin,
                args.ledger,
                env("arrow"),
                origin=origin,
                capture_interpreter=env("execute-postgres"),
                wheel=args.wheel,
            )
            for origin in args.origin
        }
    elif args.family == "tuning":
        args.directory.mkdir(mode=0o700)
        report = {
            target: probe.tuning(
                args.directory / target,
                args.ledger,
                target=target,
                interpreters=interpreters,
                wheel=args.wheel,
                routes=[r for r in args.routes or () if r in probe.ROUTES[target]]
                or None,
            )
            for target in args.target
        }
    elif args.family == "controls":
        args.directory.mkdir(mode=0o700)
        report = {
            target: probe.controls(
                args.directory / target,
                args.ledger,
                target=target,
                tree=args.tree,
                union=env("union"),
                wheel=args.wheel,
                families=args.families,
            )
            for target in args.target
        }
    elif args.family == "consumer":
        report = probe.consumer(
            args.directory, args.ledger, label=args.label, uv_cache=args.cache
        )
    else:
        import _pietto_phase68_slice19_check as check

        report = check.campaign_check(
            args.directory,
            args.wheel,
            args.house / (s18.PREFIX + "wheelhouse"),
            args.install,
        )
        args.ledger.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"family": args.family, "seconds": report.get("seconds")}))


if __name__ == "__main__":
    main()
