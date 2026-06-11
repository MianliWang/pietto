from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_production_pyright_gate_remains_strictly_scoped() -> None:
    config = _json("pyrightconfig.json")

    assert config["include"] == ["src/pietto"]
    assert config["exclude"] == ["src/pietto/generated"]
    assert config["ignore"] == ["src/pietto/generated"]
    assert config["typeCheckingMode"] == "standard"


def test_test_pyright_config_is_explicit_and_non_blocking() -> None:
    assert _json("pyrightconfig.tests.json") == {
        "extends": "./pyrightconfig.json",
        "include": ["tests"],
    }


def test_phase_plan_records_zero_diagnostic_result_without_global_suppression() -> None:
    plan = (REPO_ROOT / "docs/plan/phase-9-6-test-typing-hygiene.md").read_text(
        encoding="utf-8"
    )
    test_config = _json("pyrightconfig.tests.json")

    assert "**Phase 9.6 Test Typing Hygiene is complete.**" in plan
    assert "89 errors and no warnings" in plan
    assert "78 test files" in plan
    assert "zero errors" in plan
    assert "zero warnings" in plan
    assert "diagnosticSeverityOverrides" not in test_config
    assert "typeCheckingMode" not in test_config
    assert "ignore" not in test_config


def _json(path: str) -> dict[str, object]:
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", text))
