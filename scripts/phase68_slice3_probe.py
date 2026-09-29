"""Explicit S03 laboratory; ordinary imports never acquire external resources."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_probe():
    spec = importlib.util.spec_from_file_location(
        "p68_s3_probe", ROOT / "tests/_pietto_phase68_slice3_probe.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    load_probe().main()
