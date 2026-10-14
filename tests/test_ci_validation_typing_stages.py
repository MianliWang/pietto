from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
BASE_CONFIG_PATH = REPO_ROOT / "pyrightconfig.json"
TEST_CONFIG_PATH = REPO_ROOT / "pyrightconfig.tests.json"
TWO_STAGE_TYPING_GATES = (
    ("production typing", ("uv", "run", "pyright", "--threads", "4")),
    (
        "test typing",
        (
            "uv",
            "run",
            "pyright",
            "--project",
            "pyrightconfig.tests.json",
            "--threads",
            "4",
        ),
    ),
)
REJECTED_COMBINED_COMMAND = (
    "uv",
    "run",
    "pyright",
    "--project",
    "pyrightconfig.json",
    "src/pietto",
    "tests",
)


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_slice4_closure_validate",
        VALIDATE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_with_trailing_commas(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    return cast(dict[str, object], json.loads(re.sub(r",(\s*[}\]])", r"\1", text)))


validate = cast(Any, _load_validate_module())


def test_no_gain_closure_restores_exact_two_stage_typing_authority() -> None:
    assert validate.GATES[3:5] == TWO_STAGE_TYPING_GATES
    assert REJECTED_COMBINED_COMMAND not in {command for _, command in validate.GATES}
    assert sum("pyright" in command for _, command in validate.GATES) == 2

    base_config = _json_with_trailing_commas(BASE_CONFIG_PATH)
    test_config = _json_with_trailing_commas(TEST_CONFIG_PATH)
    assert base_config == {
        "include": ["src/pietto"],
        "exclude": ["src/pietto/generated"],
        "ignore": ["src/pietto/generated"],
        "extraPaths": ["src"],
        "venvPath": ".",
        "venv": ".venv",
        "pythonVersion": "3.12",
        "typeCheckingMode": "standard",
    }
    assert test_config == {
        "extends": "./pyrightconfig.json",
        "include": ["tests"],
    }

    production_files = tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    )
    test_files = tuple(sorted((REPO_ROOT / "tests").rglob("*.py")))
    assert set(production_files).isdisjoint(test_files)
