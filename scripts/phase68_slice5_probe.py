"""Explicit S05 native entry; ordinary imports never acquire a database."""

import importlib.util
from pathlib import Path
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    spec = importlib.util.spec_from_file_location(
        "p68_s05", root / "tests/_pietto_phase68_slice5_probe.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
