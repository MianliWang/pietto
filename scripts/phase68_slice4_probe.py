"""Explicit S04 native acceptance entry; ordinary validation stays offline."""

import importlib.util
from pathlib import Path

if __name__ == "__main__":
    path = Path(__file__).resolve().parents[1] / "tests/_pietto_phase68_slice4_probe.py"
    spec = importlib.util.spec_from_file_location("p68_s04_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
