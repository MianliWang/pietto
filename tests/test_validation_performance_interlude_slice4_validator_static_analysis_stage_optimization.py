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
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice4-validator-static-analysis-stage-optimization-v1.md"
)
LEGACY_TYPING_GATES = (
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
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
    assert validate.GATES[3:5] == LEGACY_TYPING_GATES
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
    # Phase66 Slice14 adds the private emission observation schema, pure boundary
    # and runtime modules, one process probe and its owned test file; Slice15 and
    # the unnumbered pre-Slice16 corrective closure each add only their owned test
    # file. Interlude V Slice1 adds its runtime-guard test; the two-stage
    # typing scan and production inventory are unchanged. Slice16 adds its
    # bounded static completion-audit principal. Interlude V Slice2 adds one
    # cell-coordination behavior principal without changing typing authority.
    # Phase67 Slice01 adds one inert Arrow probe and one governance/readiness principal.
    # Phase67 Slice03 adds three private codec owners and one ordinary principal.
    assert len(production_files) == 228
    # Slice05 adds one ordinary Text principal; production stays unchanged.
    assert len(test_files) == 501
    assert set(production_files).isdisjoint(test_files)


def test_no_gain_evidence_is_exact_and_candidate_is_not_adopted() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "17.74 / 23.12 / 16.29s",
        "35.39 / 31.77 / 25.30s",
        "53.13 / 54.89 / 41.59s",
        "55.43 / 52.94 / 48.58s",
        "53.13s -> 52.94s",
        "0.19s",
        "0.36%",
        "PERFORMANCE_GAIN_NOT_PROVEN",
        "NO MATERIAL GAIN — CURRENT TWO-STAGE AUTHORITY RETAINED",
        "candidate optimization is not adopted",
        "Slice 4 = COMPLETED",
        "Phase 60 = NOT ACTIVATED",
        "VALIDATION_PERFORMANCE_INTERLUDE_SLICE5_CURRENT_SUITE_ISOLATION_RESOURCE_AWARE_XDIST_SCHEDULING_CI_PARALLELISM_DECISION",
    ):
        assert evidence in document
