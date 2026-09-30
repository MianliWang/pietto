#!/usr/bin/env python3
"""Explicit S06 native acceptance launcher; ordinary import/pytest does no I/O."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT / "tests"))
    from _pietto_phase68_slice6_probe import main as probe_main

    return probe_main()


if __name__ == "__main__":
    raise SystemExit(main())
