from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "mysql"))

from campaign import ipc_worker


def main() -> int:
    directory = HERE / "finite-selfcheck-output"
    directory.mkdir(exist_ok=True)
    project = directory / "project"
    project.mkdir(exist_ok=True)
    for name in ("main.pietto", "pietto.toml", "contract.json"):
        (project / name).write_text(name, encoding="utf-8")
    try:
        result = ipc_worker(
            Path(sys.executable),
            {
                "project": str(project),
                "password": "pw",
                "port": 1,
                "ca": "none",
                "finite_selftest": True,
            },
            {"PATH": os.environ.get("PATH", "/usr/bin"), "PYTHONNOUSERSITE": "1"},
            directory,
            label="finite-context",
            failure="FINITE_CONTEXT",
        )
    except ValueError as error:
        record = json.loads((directory / "finite-context.json").read_text(encoding="utf-8"))
        print(json.dumps({"error": str(error), "record": record}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
