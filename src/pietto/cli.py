"""Command-line entry point for Pietto developer tooling."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

_FALLBACK_VERSION = "0.1.0"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scaffold CLI and return a process exit code."""

    parser = _build_parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments == []:
        parser.print_help()
        return 0

    try:
        parser.parse_args(arguments)
    except SystemExit as error:
        return int(error.code)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the Phase 5 scaffold parser without compiler integration."""

    parser = argparse.ArgumentParser(
        prog="pietto",
        description="Pietto semantic SQL authoring tools.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    return parser


def _package_version() -> str:
    """Read installed package metadata with a source-tree fallback."""

    try:
        return version("pietto")
    except PackageNotFoundError:
        return _FALLBACK_VERSION
