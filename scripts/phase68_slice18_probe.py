#!/usr/bin/env python3
"""Explicit bounded S18 installation/compatibility/native families; importing
acquires nothing. A family exits non-zero when its independent checker rejects."""

import argparse
import json
from pathlib import Path
import sys

CELLS = ("source:live", "source:bundle", "installed:live", "installed:bundle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("install", "compat", "native"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument(
        "--interpreter", type=Path, help="base CPython for fresh prefixes"
    )
    parser.add_argument("--cache", type=Path, help="owned uv cache")
    parser.add_argument("--dist", type=Path, help="install: the built wheel and sdist")
    parser.add_argument("--install", type=Path, help="the install family directory")
    parser.add_argument("--house", type=Path, help="the verified wheelhouse root")
    parser.add_argument("--archived", type=Path, help="compat: reuse archived prefixes")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--target", choices=("postgres", "mysql"))
    parser.add_argument("--cells", nargs="+", default=CELLS, choices=CELLS)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    import _pietto_phase68_slice18_probe as probe

    def env(recipe):
        return args.install / (probe.PREFIX + "env-" + recipe)

    if args.family == "install":
        report = probe.install(
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
            current=env("arrow"),
            house=(args.house or args.install) / (probe.PREFIX + "wheelhouse"),
            constraints=(args.house or args.install)
            / (probe.PREFIX + "constraints.txt"),
            interpreter=args.interpreter,
            cache=args.cache,
            archived_from=args.archived,
        )
    else:
        report = probe.native(
            args.directory,
            args.ledger,
            target=args.target,
            interpreters={
                route: env(recipe) / "bin/python"
                for route, recipe in probe.ROUTE_RECIPE.items()
            },
            union=env("union") / "bin/python",
            saved_interpreter=env("arrow") / "bin/python",
            wheel=args.wheel,
            cells=[tuple(c.split(":")) for c in args.cells],
        )
    print(json.dumps({"family": args.family, "seconds": report.get("seconds")}))


if __name__ == "__main__":
    main()
