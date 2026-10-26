from __future__ import annotations

from copy import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tomllib
from typing import cast

import pytest

import _pietto_differential_process_acquisition as acquisition
import _pietto_project_query_block as slice14
from pietto._project import project_query_block_ir_inspection as inspection
from pietto._project import project_query_block_ir_pure_boundary as pure
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_SOURCE = (
    REPO_ROOT / "src/pietto/_project/project_query_block_ir_inspection.py"
)
PURE_SOURCE = REPO_ROOT / "src/pietto/_project/project_query_block_ir_pure_boundary.py"
PROBE = REPO_ROOT / "tests/_pietto_ir_query_block_differential.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice15-inspection-pure-boundary-real-e2e-differential-metamorphic-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Frozen after review of one source-checkout observation. Full observations,
# records, and canonical bytes are compared directly; digests are review aids.
EXPECTED_REVIEW_SUMMARY: dict[str, object] = {
    "observation_format": "pietto.phase63-query-block-ir-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "owner_count": 35,
    "record_count": 2623,
    "canonical_size": 762530,
    "canonical_sha256": "06259e1c20fc30ef8184205c08dc7184b3ff35041305c322f189a3e664dbda38",
    "phase61_size": 90142,
    "phase61_sha256": "b01e22a5c6fc603b99da93267ce4f4f5e90a6ccb06e692e3690ca878cc464144",
    "phase62_size": 66441,
    "phase62_sha256": "7563790e6c9ec043df244857f4d979e1b21efb8e08d63f1530738f25c7095d62",
    "metamorphics": {
        "active_root_invariance": [92, 92, 92, 4, 4],
        "selected_hidden": {
            "selected": [1, 1, True],
            "hidden": [
                1,
                0,
                1,
                ["window_evaluation", "qualify", "final_projection"],
            ],
            "selected_and_hidden": [1, 1],
        },
        "qualify": [
            ["window_evaluation", "final_projection"],
            ["window_evaluation", "qualify", "final_projection"],
            True,
        ],
        "window_vs_relation_order": [None, "ProjectRelationOrdering"],
        "limit": [1, 2, True, "factorized", "factorized"],
        "grouped_global": ["factorized", ["group_domain"], "global", [], 0],
        "downstream": [True, True],
        "reuse_rebound": [
            "ProjectIRReusedEffectiveOutput",
            True,
            "ProjectIRReboundExistingOutput",
            True,
        ],
        "effective_join": [
            "ProjectIRCompletedQueryBlockOutput",
            "ProjectIRCompletedQueryBlockOutput",
            True,
            True,
        ],
        "inner_left": [
            ["non_null", "non_null"],
            ["non_null", "nullable"],
            [0, 1],
        ],
        "multi_join": [7, [0, 0, 1]],
        "duplicate_intermediate_names": [7, 4],
    },
    "negative": {
        "non_verified_admission": "rejected",
        "cross_snapshot_ref": "rejected",
        "terminals": [
            ["semantic_bad", "semantic_output_non_concrete"],
            ["semantic_bad_downstream", "semantic_output_non_concrete"],
        ],
        "pure_rejections": [
            ["unknown_format", "unknown_format", 0, 0],
            ["section_order", "invalid_section_order", 0, 0],
            ["dangling_ref", "dangling_ref", 512, 1],
        ],
    },
}


def _unsafe[Value](value: Value, **changes: object) -> Value:
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


@pytest.fixture(scope="module")
def bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> ProjectIRQueryBlockAnalysisBundle:
    built = slice14._build(tmp_path_factory.mktemp("p63s15"))
    verification = verify_project_query_block_ir(built.snapshot)
    return build_project_query_block_ir_analysis_bundle(verification)


@pytest.fixture(scope="module")
def foreign_bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> ProjectIRQueryBlockAnalysisBundle:
    built = slice14._build(tmp_path_factory.mktemp("p63s15-foreign"))
    verification = verify_project_query_block_ir(built.snapshot)
    return build_project_query_block_ir_analysis_bundle(verification)


@pytest.fixture(scope="module")
def product(
    bundle: ProjectIRQueryBlockAnalysisBundle,
) -> inspection.ProjectIRQueryBlockInspectionProduct:
    return inspection.build_project_query_block_ir_inspection(bundle)


@pytest.fixture(scope="module")
def observed(
    product: inspection.ProjectIRQueryBlockInspectionProduct,
) -> inspection.ProjectIRQueryBlockInspection:
    return product.inspection


def _entry(
    observed: inspection.ProjectIRQueryBlockInspection,
    name: str,
):
    matches = tuple(
        entry
        for entry in observed.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _record_position(
    document: pure.ProjectQueryBlockIRPureDocument,
    kind: pure.ProjectQueryBlockIRRecordKind,
) -> int:
    return next(
        position
        for position, record in enumerate(document.records)
        if record.kind is kind
    )


def _field_position(
    record: pure.ProjectQueryBlockIRPureRecord,
    key: str,
) -> int:
    return next(
        position for position, field in enumerate(record.fields) if field.key == key
    )


def _replace_record(
    document: pure.ProjectQueryBlockIRPureDocument,
    position: int,
    record: pure.ProjectQueryBlockIRPureRecord,
) -> pure.ProjectQueryBlockIRPureDocument:
    return replace(
        document,
        records=(
            *document.records[:position],
            record,
            *document.records[position + 1 :],
        ),
    )


def _replace_field(
    document: pure.ProjectQueryBlockIRPureDocument,
    record_position: int,
    key: str,
    value: pure.ProjectQueryBlockIRPureValue,
) -> pure.ProjectQueryBlockIRPureDocument:
    record = document.records[record_position]
    position = _field_position(record, key)
    replacement = replace(
        record,
        fields=(
            *record.fields[:position],
            replace(record.fields[position], value=value),
            *record.fields[position + 1 :],
        ),
    )
    return _replace_record(document, record_position, replacement)


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _review_summary(document: bytes) -> dict[str, object]:
    observation = _decoded(document)
    canonical = cast(str, observation["canonical_bytes"]).encode("utf-8")
    phase61 = cast(str, observation["phase61_canonical_bytes"]).encode("utf-8")
    phase62 = cast(str, observation["phase62_canonical_bytes"]).encode("utf-8")
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "owner_count": len(cast(list[object], observation["scenario_manifest"])),
        "record_count": len(cast(list[object], observation["portable_records"])),
        "canonical_size": len(canonical),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "phase61_size": len(phase61),
        "phase61_sha256": hashlib.sha256(phase61).hexdigest(),
        "phase62_size": len(phase62),
        "phase62_sha256": hashlib.sha256(phase62).hexdigest(),
        "metamorphics": observation["metamorphics"],
        "negative": observation["negative"],
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase63")
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
