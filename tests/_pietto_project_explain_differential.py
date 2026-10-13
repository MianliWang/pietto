from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tomllib
from typing import cast

import pytest

import _pietto_differential_process_acquisition as acquisition
import _pietto_project_explain_differential_probe as probe


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_project_explain_differential_probe.py"
SCENARIOS = REPO_ROOT / "tests/_pietto_project_explain_scenarios.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice16-pure-differential-compatibility-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))

# One common, named, per-surface authority is consumed unchanged by Python
# 3.12, Python 3.13, every seed, both relocation forms, and the installed wheel.
EXPECTED_SURFACE_SHA256: dict[str, object] = {
    "observation_format": "pietto.project-explain-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "scenarios": {
        "matrix": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "2a0334b7cbe1bf1368f246a4e1412219841d94ac5aa750c011b7c65c9785f9dd"
            ),
            "json_sha256": (
                "b29580fc02151e73d6212712a5e0e3eb86ebad1774ac2d38f33a91ed795b6d10"
            ),
            "text_sha256": (
                "0e4bdda45c8c759f8a5a0fdd4a4fbef20e8ff4679f9198e31935ae96a8a08270"
            ),
        },
        "empty": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "6a6043b2e7514099f00934380b8d7203ea445212abaa4b3b9a7a7c92616a3f49"
            ),
            "json_sha256": (
                "99c05feac5eeb0f0841ef8314530f060cc401e339d281f205b563e07548302d8"
            ),
            "text_sha256": (
                "dd8714d8f5d2fbd4233ca5e09c0cfaa2b8b19561c15431f92cc48c01babb86a8"
            ),
        },
        "portable": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "981f7f6006446f5a04115421557d4227dcd51b46c26bb918425ca6cb7511e909"
            ),
            "json_sha256": (
                "1761f542e847800e375ec04773f7351bfeeab38d1374808a81e257499f8b7729"
            ),
            "text_sha256": (
                "038d7fe3a7e33c278f12ab15975468f5cac14567adfeee0dfe4f1d3256c7e360"
            ),
        },
        "diagnostic": {
            "runtime_outcome": "diagnostic_error",
            "cli_json_exit": 1,
            "cli_text_exit": 1,
            "structured_sha256": (
                "0e80e0814a37f0243c9d469455d90a070debbe08150aa011e9dfe20508c0328f"
            ),
            "json_sha256": (
                "7bb804c7571a7d3cb922262c20efd293a4027d295fdbee4273aa700d6595e9f3"
            ),
            "text_sha256": (
                "58e57f83817004f922b957a7e29f174d4650b8fa88363cfe7987af27edac55b8"
            ),
        },
        "resource": {
            "runtime_outcome": "usage_or_resource_error",
            "cli_json_exit": 2,
            "cli_text_exit": 2,
            "structured_sha256": (
                "52121819e26899ffd5ccb182a8bce54f59ef6ed0e65b70c9052c47242f169505"
            ),
            "json_sha256": (
                "ba496ad2754a547167b3ac49933d5900156b687fea545977ee935c9e93bf77cd"
            ),
            "text_sha256": (
                "ca57557b8a7e387a5c7b9d1e4fcb31983741b71d4857bd1bdfce4b41ef03a24c"
            ),
        },
    },
    "single_file": {
        "text_exit": 0,
        "json_exit": 0,
        "text_sha256": (
            "2d3e0e50dfa0246ec1bf8269ddae764d23cf111afcd945f6ea1f150ef3008fdc"
        ),
        "json_sha256": (
            "02e6e6cc7eb78370f930c82c881f9728b609dac65e36ec807ce80f8c359c76d3"
        ),
    },
}


def _decoded(document: bytes) -> dict[str, object]:
    assert document.endswith(b"\n") and not document.endswith(b"\n\n")
    return cast(dict[str, object], json.loads(document))


def _canonical_bytes(value: object) -> bytes:
    if type(value) is str:
        return value.encode("utf-8")
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _surface_manifest(observation: dict[str, object]) -> dict[str, object]:
    scenarios = cast(dict[str, dict[str, object]], observation["scenarios"])
    single = cast(dict[str, object], observation["single_file"])
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "scenarios": {
            name: {
                "runtime_outcome": scenarios[name]["runtime_outcome"],
                "cli_json_exit": scenarios[name]["cli_json_exit"],
                "cli_text_exit": scenarios[name]["cli_text_exit"],
                "structured_sha256": _digest(scenarios[name]["structured"]),
                "json_sha256": _digest(scenarios[name]["json_document"]),
                "text_sha256": _digest(scenarios[name]["text_document"]),
            }
            for name in probe.SCENARIO_ORDER
        },
        "single_file": {
            "text_exit": single["text_exit"],
            "json_exit": single["json_exit"],
            "text_sha256": _digest(single["text_document"]),
            "json_sha256": _digest(single["json_document"]),
        },
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase58")
    observations: dict[str, dict[str, object]] = {}
    for seed in SEEDS:
        observations[f"seed:{seed}"] = _decoded(documents[f"seed:{seed}"])

    interpreters = store.interpreters
    for version, executable in interpreters.items():
        key = f"python{version[0]}.{version[1]}"
        observations[key] = (
            observations["seed:0"]
            if executable == sys.executable
            else _decoded(documents[key])
        )

    observations["project-relocated"] = _decoded(documents["project-relocated"])
    observations["source-relocated"] = _decoded(documents["source-relocated"])
    observations["installed-wheel"] = _decoded(documents["installed-wheel"])
    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origin": store.import_origin(
            acquisition.Cell(sys.version_info[:2], "0", "installed")
        ),
        "installed_source_root": store.installed_source_root(),
        "empty_install_cache": store.empty_install_cache(),
    }
