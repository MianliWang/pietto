from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tomllib
from typing import cast

import pytest

import _pietto_differential_process_acquisition as acquisition


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_project_graph_differential.py"
SCENARIOS = REPO_ROOT / "tests/_pietto_project_explain_scenarios.py"
SPEC = (
    REPO_ROOT / "docs/spec/phase59-slice11-differential-compatibility-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))

# One shared expectation is consumed unchanged by every Python version, seed,
# project/source relocation, repeated construction, and installed-wheel run.
EXPECTED_COMMON_MANIFEST: dict[str, object] = {
    "observation_format": "pietto.package-graph-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "runtime_refs_distinct": True,
    "integrity": "ok",
    "pure_status": "ok",
    "canonical_sha256": (
        "e5b510011b04b92939631ff34bab844a86bb2b25e2b2b7574dd8d6be02cea876"
    ),
    "canonical_size": 589019,
    "inspection_sha256": (
        "b1bd359cae7312b5a51c9636c2b588f13a98f6e656bc883ce8cb5f8d59a6dbd4"
    ),
    "counts": {
        "records": [
            ["package", 2],
            ["dependency", 1],
            ["requirement_collection", 2],
            ["requirement", 2],
            ["selector", 1],
            ["capability_evaluation", 2],
            ["catalog_evidence", 1],
            ["module", 2],
            ["declaration", 12],
            ["semantic_authority", 2],
            ["field", 30],
            ["let_binding", 2],
            ["window_semantic", 2],
        ],
        "links": [
            ["dependency", 1],
            ["requirement", 2],
            ["selector", 1],
            ["capability_evaluation", 2],
            ["catalog_evidence", 1],
            ["module", 2],
            ["declaration", 12],
            ["field", 30],
            ["let_binding", 2],
            ["source_lineage", 8],
            ["projection_lineage", 4],
            ["expression_lineage", 16],
            ["current_window_lineage", 8],
        ],
        "states": [["let_lineage", 6]],
    },
    "packages": [[[0], "dependency", "dependency"], [[1], "root", "root"]],
    "dependencies": [
        [
            [1, 0],
            {"domain": "package", "positions": [1]},
            {"domain": "package", "positions": [0]},
        ]
    ],
    "requirement_coordinates": [[0, 0], [0, 1]],
    "selector_coordinates": [[0, 0]],
    "module_coordinates": [[0, 0], [1, 0]],
    "declarations": [
        [[0, 0, 0], "Row"],
        [[0, 0, 1], "rows"],
        [[0, 0, 2], "projections"],
        [[0, 0, 3], "calculations"],
        [[0, 0, 4], "aggregates"],
        [[0, 0, 5], "windows"],
        [[1, 0, 0], "Row"],
        [[1, 0, 1], "rows"],
        [[1, 0, 2], "projections"],
        [[1, 0, 3], "calculations"],
        [[1, 0, 4], "aggregates"],
        [[1, 0, 5], "windows"],
    ],
    "fields_sha256": (
        "cd139dba6346cce397ec21a03cdf9d375469034e22aab1387db03701552f8bbc"
    ),
    "capability_outcomes": [
        [[0, 0, 0], "satisfied"],
        [[0, 1, 0], "unknown"],
    ],
    "catalog_outcomes": [[[0, 0, 0], "found", 1]],
    "lineage_sha256": (
        "260da46fbfabd86267fd179f0417f3302b556c383858f451afa022d6a7bc5b54"
    ),
    "queries": {
        "direct_upstream": [67, 68],
        "direct_downstream": [26, 62, 65, 67, 68, 70, 71, 81, 82],
        "all_paths_to_repeated_input": [
            [7, 10, 26],
            [7, 11, 30, 62],
            [7, 12, 31, 67],
            [7, 12, 31, 68],
            [7, 12, 32, 69, 65],
            [7, 12, 51, 65],
            [7, 13, 33, 70],
            [7, 13, 33, 71],
            [7, 14, 35, 81],
            [7, 14, 35, 82],
        ],
        "dependency_to_catalog": [[1, 3, 4, 6]],
        "root_to_catalog": [[0, 1, 3, 4, 6]],
        "why_not": [
            {
                "path": [2, 5],
                "terminal_ordinal": 9,
                "terminal_ref": {
                    "domain": "capability_evaluation",
                    "positions": [0, 1, 0],
                },
                "terminal_outcome": "unknown",
            }
        ],
    },
    "project_explain": {
        "runtime_outcome": "success",
        "json_sha256": (
            "62fa74167a6170e6ec143fdec0535c34c0f398e5d668c9576212322c03047423"
        ),
        "json_size": 12356,
        "text_sha256": (
            "a35880e181fdf48c11a4289953ebe8e7b85170656998393339bc4fbde0e76df7"
        ),
        "text_size": 3483,
        "cli_json_exit": 0,
        "cli_text_exit": 0,
    },
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _fields(record: dict[str, object]) -> dict[str, object]:
    return {
        cast(str, name): value
        for name, value in cast(list[list[object]], record["fields"])
    }


def _positions(record: dict[str, object], key: str = "ref") -> list[int]:
    ref = cast(dict[str, object], record[key])
    return cast(list[int], ref["positions"])


def _decoded(document: bytes) -> dict[str, object]:
    assert document.endswith(b"\n") and not document.endswith(b"\n\n")
    return cast(dict[str, object], json.loads(document))


def _common_manifest(observation: dict[str, object]) -> dict[str, object]:
    graph = cast(dict[str, object], observation["graph"])
    records = cast(list[dict[str, object]], graph["records"])
    links = cast(list[dict[str, object]], graph["links"])
    states = cast(list[dict[str, object]], graph["states"])
    queries = cast(dict[str, object], graph["queries"])
    packages = [record for record in records if record["kind"] == "package"]
    dependencies = [record for record in records if record["kind"] == "dependency"]
    requirements = [record for record in records if record["kind"] == "requirement"]
    selectors = [record for record in records if record["kind"] == "selector"]
    modules = [record for record in records if record["kind"] == "module"]
    declarations = [record for record in records if record["kind"] == "declaration"]
    evaluations = [
        record for record in records if record["kind"] == "capability_evaluation"
    ]
    catalogs = [record for record in records if record["kind"] == "catalog_evidence"]
    lineage_links = [link for link in links if str(link["kind"]).endswith("lineage")]
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "runtime_refs_distinct": observation["runtime_refs_distinct"],
        "integrity": graph["integrity"],
        "pure_status": graph["pure_status"],
        "canonical_sha256": graph["canonical_sha256"],
        "canonical_size": graph["canonical_size"],
        "inspection_sha256": _digest(
            {"records": records, "links": links, "states": states}
        ),
        "counts": graph["counts"],
        "packages": [
            [_positions(record), _fields(record)["name"], _fields(record)["role"]]
            for record in packages
        ],
        "dependencies": [
            [
                _positions(record),
                _fields(record)["declaring_package"],
                _fields(record)["resolved_package"],
            ]
            for record in dependencies
        ],
        "requirement_coordinates": [_positions(record) for record in requirements],
        "selector_coordinates": [_positions(record) for record in selectors],
        "module_coordinates": [_positions(record) for record in modules],
        "declarations": [
            [_positions(record), _fields(record)["name"]] for record in declarations
        ],
        "fields_sha256": _digest(
            [record for record in records if record["kind"] == "field"]
        ),
        "capability_outcomes": [
            [_positions(record), _fields(record)["outcome"]] for record in evaluations
        ],
        "catalog_outcomes": [
            [
                _positions(record),
                _fields(record)["lookup_variant"],
                _fields(record)["selected_catalog_position"],
            ]
            for record in catalogs
        ],
        "lineage_sha256": _digest(lineage_links),
        "queries": queries,
        "project_explain": observation["project_explain"],
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase59")
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
    for version, seed in (((3, 12), "1"), ((3, 13), "4294967295")):
        if version not in interpreters:
            continue
        key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
        observations[key] = _decoded(documents[key])

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
