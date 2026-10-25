from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import cast

import pytest

import _pietto_differential_process_acquisition as acquisition


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_ir_join_differential.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Reviewed common manifest; full observation bytes remain the comparison authority.
EXPECTED_COMMON_MANIFEST_SHA256: str | None = (
    "59f99966ddb1a76373d21ddc525b203e1bf859235d50de06ca31c3e2e12ec820"
)


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _canonical_bytes(observation: dict[str, object], section: str) -> bytes:
    selected = cast(dict[str, object], observation[section])
    return cast(str, selected["canonical_bytes"]).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _common_manifest(document: bytes) -> dict[str, object]:
    observation = _decoded(document)
    manifest = dict(observation)
    for name in ("primary", "parallel", "no_unique"):
        section = dict(cast(dict[str, object], observation[name]))
        records = cast(list[object], section.pop("portable_records"))
        canonical = cast(str, section.pop("canonical_bytes")).encode("utf-8")
        replacements = {
            "portable_records_count": len(records),
            "portable_records_sha256": _digest(records),
            "canonical_bytes_sha256": hashlib.sha256(canonical).hexdigest(),
            "canonical_bytes_size": len(canonical),
        }
        assert not section.keys() & replacements.keys()
        section.update(replacements)
        manifest[name] = section

    shifted = dict(cast(dict[str, object], observation["shifted"]))
    for name in ("normal_canonical_bytes", "canonical_bytes"):
        canonical = cast(str, shifted.pop(name)).encode("utf-8")
        replacements = {
            f"{name}_sha256": hashlib.sha256(canonical).hexdigest(),
            f"{name}_size": len(canonical),
        }
        assert not shifted.keys() & replacements.keys()
        shifted.update(replacements)
    manifest["shifted"] = shifted

    # The reviewed bytes leave the version out; "package_version" pins it.
    field = b'"package_version":' + json.dumps(observation["package_version"]).encode()
    assert document.count(field) == 1
    unversioned = document.replace(field, b'"package_version":null')
    assert "observation_sha256" not in manifest and "observation_size" not in manifest
    manifest["observation_sha256"] = hashlib.sha256(unversioned).hexdigest()
    manifest["observation_size"] = len(unversioned)
    return manifest


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase62")
    observations: dict[str, bytes] = {}
    interpreters = store.interpreters
    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        for seed in SEEDS:
            key = f"source:{label}:seed:{seed}"
            observations[key] = documents[key]

    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"relocated:{label}:seed:7"
        observations[key] = documents[key]

    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"installed:{label}:seed:7"
        observations[key] = documents[key]

    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origins": store.installed_origins(),
        "installed_source_root": store.installed_source_root(),
        "empty_install_cache": store.empty_install_cache(),
    }


def _baseline_key() -> str:
    return f"source:python{sys.version_info[0]}.{sys.version_info[1]}:seed:0"
