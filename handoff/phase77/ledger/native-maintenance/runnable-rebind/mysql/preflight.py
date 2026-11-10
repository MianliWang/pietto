"""Freeze one candidate identity before the literal-none MySQL acquisition."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign import binding, sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidate, wheel, out = args.candidate.resolve(), args.wheel.resolve(), args.out.resolve()
    if out.exists() or out.is_relative_to(candidate) or sha256(wheel) != args.wheel_sha256:
        raise ValueError("PREFLIGHT_OUTPUT_OR_WHEEL")
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    out.write_text(__import__("json").dumps(binding(candidate, wheel), sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
