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
PROBE = REPO_ROOT / "tests/_pietto_ir_project_differential.py"
SPEC = REPO_ROOT / "docs/spec/phase61-slice11-differential-compatibility-v1.md"
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Filled once from one reviewed source observation. Every matrix member is
# checked against this unchanged manifest; no environment-local oracle exists.
EXPECTED_COMMON_MANIFEST: dict[str, object] = {
    "observation_format": "pietto.phase61-project-ir-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "runtime_identities_distinct": True,
    "relations": [
        [
            ["c.pietto", 2, 1, "relation", "source", "rows"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "c.pietto",
                    2,
                    1,
                    "relation",
                    "source",
                    "rows",
                    "source_field",
                    0,
                    "id",
                ],
                [
                    "c.pietto",
                    2,
                    1,
                    "relation",
                    "source",
                    "rows",
                    "source_field",
                    1,
                    "amount",
                ],
                [
                    "c.pietto",
                    2,
                    1,
                    "relation",
                    "source",
                    "rows",
                    "source_field",
                    2,
                    "category",
                ],
            ],
        ],
        [
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "c.pietto",
                    2,
                    2,
                    "relation",
                    "table",
                    "projected",
                    "relation_output",
                    0,
                    "id",
                ],
                [
                    "c.pietto",
                    2,
                    2,
                    "relation",
                    "table",
                    "projected",
                    "relation_output",
                    1,
                    "amount",
                ],
                [
                    "c.pietto",
                    2,
                    2,
                    "relation",
                    "table",
                    "projected",
                    "relation_output",
                    2,
                    "category",
                ],
            ],
        ],
        [
            ["a.pietto", 0, 0, "relation", "query", "final"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "a.pietto",
                    0,
                    0,
                    "relation",
                    "query",
                    "final",
                    "relation_output",
                    0,
                    "id",
                ]
            ],
        ],
        [
            ["a.pietto", 0, 1, "relation", "query", "consumer"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "a.pietto",
                    0,
                    1,
                    "relation",
                    "query",
                    "consumer",
                    "relation_output",
                    0,
                    "id",
                ]
            ],
        ],
        [
            ["a.pietto", 0, 2, "relation", "query", "second"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "a.pietto",
                    0,
                    2,
                    "relation",
                    "query",
                    "second",
                    "relation_output",
                    0,
                    "id",
                ]
            ],
        ],
        [
            ["a.pietto", 0, 3, "relation", "query", "aggregate_only"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "a.pietto",
                    0,
                    3,
                    "relation",
                    "query",
                    "aggregate_only",
                    "relation_output",
                    0,
                    "total",
                ]
            ],
        ],
        [
            ["a.pietto", 0, 4, "relation", "query", "full"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "a.pietto",
                    0,
                    4,
                    "relation",
                    "query",
                    "full",
                    "relation_output",
                    0,
                    "category",
                ],
                [
                    "a.pietto",
                    0,
                    4,
                    "relation",
                    "query",
                    "full",
                    "relation_output",
                    1,
                    "total",
                ],
                [
                    "a.pietto",
                    0,
                    4,
                    "relation",
                    "query",
                    "full",
                    "relation_output",
                    2,
                    "ranking",
                ],
            ],
        ],
        [
            ["a.pietto", 0, 5, "relation", "query", "broken"],
            "unknown",
            "ProjectModuleRelationSemanticFacts",
            [],
        ],
        [
            ["d.pietto", 3, 1, "relation", "source", "other"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "d.pietto",
                    3,
                    1,
                    "relation",
                    "source",
                    "other",
                    "source_field",
                    0,
                    "key",
                ]
            ],
        ],
        [
            ["d.pietto", 3, 2, "relation", "query", "other_result"],
            "concrete",
            "ProjectModuleRelationSemanticFacts",
            [
                [
                    "d.pietto",
                    3,
                    2,
                    "relation",
                    "query",
                    "other_result",
                    "relation_output",
                    0,
                    "key",
                ]
            ],
        ],
    ],
    "operators": [
        ["c.pietto", 2, 1, "relation", "source", "rows", ["relation_input"]],
        [
            "c.pietto",
            2,
            2,
            "relation",
            "table",
            "projected",
            ["relation_input", "final_projection"],
        ],
        [
            "a.pietto",
            0,
            0,
            "relation",
            "query",
            "final",
            ["relation_input", "final_projection"],
        ],
        [
            "a.pietto",
            0,
            1,
            "relation",
            "query",
            "consumer",
            ["relation_input", "final_projection"],
        ],
        [
            "a.pietto",
            0,
            2,
            "relation",
            "query",
            "second",
            ["relation_input", "final_projection"],
        ],
        [
            "a.pietto",
            0,
            3,
            "relation",
            "query",
            "aggregate_only",
            ["relation_input", "group_aggregate", "final_projection"],
        ],
        [
            "a.pietto",
            0,
            4,
            "relation",
            "query",
            "full",
            [
                "relation_input",
                "row_filter",
                "group_aggregate",
                "result_filter",
                "window_evaluation",
                "final_projection",
                "relation_ordering",
                "limit",
            ],
        ],
        ["a.pietto", 0, 5, "relation", "query", "broken", []],
        ["d.pietto", 3, 1, "relation", "source", "other", ["relation_input"]],
        [
            "d.pietto",
            3,
            2,
            "relation",
            "query",
            "other_result",
            ["relation_input", "final_projection"],
        ],
    ],
    "coordinate_counts": [23, 35, 21, 21],
    "coordinates_sha256": (
        "7f58557377d478b95f162581af46c806e373d8ff97749a42b49dc5ed51e5fdb3"
    ),
    "cross_edges": [
        [
            ["c.pietto", 2, 1, "relation", "source", "rows"],
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            14,
            14,
            "satisfied",
            0,
            0,
        ],
        [
            ["a.pietto", 0, 1, "relation", "query", "consumer"],
            ["a.pietto", 0, 0, "relation", "query", "final"],
            15,
            15,
            "satisfied",
            0,
            0,
        ],
        [
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            ["a.pietto", 0, 1, "relation", "query", "consumer"],
            16,
            16,
            "satisfied",
            0,
            2,
        ],
        [
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            ["a.pietto", 0, 2, "relation", "query", "second"],
            17,
            17,
            "satisfied",
            0,
            2,
        ],
        [
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            ["a.pietto", 0, 3, "relation", "query", "aggregate_only"],
            18,
            18,
            "satisfied",
            0,
            2,
        ],
        [
            ["c.pietto", 2, 2, "relation", "table", "projected"],
            ["a.pietto", 0, 4, "relation", "query", "full"],
            19,
            19,
            "satisfied",
            0,
            2,
        ],
        [
            ["d.pietto", 3, 1, "relation", "source", "other"],
            ["d.pietto", 3, 2, "relation", "query", "other_result"],
            20,
            20,
            "satisfied",
            0,
            0,
        ],
    ],
    "provided_properties_sha256": (
        "d10113910ffb563eba3e7ec32351bf5fb71c0b30cce1d55cff4113c2a6dcfe6f"
    ),
    "effects_sha256": (
        "3f90540e6cbbf3e6d7a1717b9339aac62581509a1621353bea7413fd56c51fea"
    ),
    "aggregate_contexts": [
        [
            "aggregate_only",
            10,
            4,
            0,
            0,
            [["sum", "total", False, 1]],
            "concrete",
            ["unknown", "unknown"],
            [0, 0],
        ],
        [
            "full",
            14,
            7,
            1,
            1,
            [["sum", "total", True, 1]],
            "concrete",
            ["unknown", "unknown"],
            [0, 0],
        ],
    ],
    "window_operator_contexts": [
        ["full", 16, 9, "base_result", True, [0, 0], ["unknown", "unknown"]]
    ],
    "window_result_contexts": [
        [
            "full",
            2,
            24,
            ["relation_input", "window_partition", "window_order"],
            "row_number",
            "frame_insensitive_explicit_forbidden",
            ["unknown", "unknown", "unknown", "unknown"],
        ]
    ],
    "verification": ["verified", []],
    "topological": [
        0,
        1,
        2,
        5,
        6,
        3,
        4,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
    ],
    "reachability_sha256": (
        "b552843fe7e1c5497e54defaf03b4be566bbb1ae369cc0d5b40fc3af42bc225f"
    ),
    "equivalence_sha256": (
        "c8fdfdc2b79662b9e9d2e3c1e1f30766c3446bae7db97bf4eae9692574fda9b8"
    ),
    "rewrite_readiness_sha256": (
        "9f39e3c094f4250926df3a0132151a02bd9b40ed9f57f33f18099f6973b43a0c"
    ),
    "queries": [
        ["a.pietto", "full", 1, []],
        ["a.pietto", "broken", 1, ["unknown"]],
    ],
    "canonical_sha256": (
        "2c7b3489a7409f95a904da1a43386161f5b6604bb2cc6653403e6cfbb96f2cad"
    ),
    "canonical_size": 72471,
    "shifted": {
        "starting_coordinates": [7, 11, 5, 5],
        "first_node": 7,
        "canonical_sha256": (
            "87119dd1956ddbd35c139f7297972c311e3f83c8382e89da04ffa1655ba11c52"
        ),
        "canonical_size": 72626,
    },
    "cycle": {
        "relations": [
            [
                ["main.pietto", 0, 1, "relation", "source", "rows"],
                "concrete",
                "ProjectModuleRelationSemanticFacts",
                [
                    [
                        "main.pietto",
                        0,
                        1,
                        "relation",
                        "source",
                        "rows",
                        "source_field",
                        0,
                        "id",
                    ]
                ],
            ],
            [
                ["main.pietto", 0, 2, "relation", "query", "okay"],
                "concrete",
                "ProjectModuleRelationSemanticFacts",
                [
                    [
                        "main.pietto",
                        0,
                        2,
                        "relation",
                        "query",
                        "okay",
                        "relation_output",
                        0,
                        "id",
                    ]
                ],
            ],
            [
                ["main.pietto", 0, 3, "relation", "query", "a"],
                "blocked",
                "ProjectModuleRelationSemanticFacts",
                [],
            ],
            [
                ["main.pietto", 0, 4, "relation", "query", "b"],
                "blocked",
                "ProjectModuleRelationSemanticFacts",
                [],
            ],
        ],
        "non_concrete": [
            ["a", "blocked", "ProjectModuleRelationSemanticFacts", 0, 0, 1],
            ["b", "blocked", "ProjectModuleRelationSemanticFacts", 0, 0, 1],
        ],
        "concrete": ["rows", "okay"],
        "verification": ["verified", []],
        "canonical_sha256": (
            "edbae782b622be5697a2d5ebf1168aa215ba205d37b194ba78ecacbdde5cde31"
        ),
        "canonical_size": 6741,
    },
    "invalid_verification": {
        "status": "invalid",
        "issues": [
            ["evaluation_context", None, None],
            ["evaluation_context", "ProjectIRPlanNodeRef", 14],
        ],
    },
    "pure_rejections": [
        ["wrong_format", "unknown_format_marker", 0, 0],
        ["non_dense_ref", "non_dense_ref_coordinates", 0, None],
        ["wrong_domain_ref", "ref_domain_mismatch", 34, None],
        ["dangling_ref", "dangling_ref", 34, None],
        ["section_order", "section_order_violation", None, None],
        ["invalid_use_endpoint", "invalid_endpoint_relation", 90, None],
    ],
    "observation_sha256": (
        "2e688b295dc9bda260e204a60ca2d309fc18f724a19794761f99621b598f1d2a"
    ),
    "observation_size": 204905,
}


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _canonical_bytes(observation: dict[str, object], section: str) -> bytes:
    if section == "project":
        project = cast(dict[str, object], observation["project"])
        return cast(str, project["canonical_bytes"]).encode("utf-8")
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
    project = cast(dict[str, object], observation["project"])
    shifted = cast(dict[str, object], observation["shifted"])
    cycle = cast(dict[str, object], observation["cycle"])
    project_bytes = _canonical_bytes(observation, "project")
    shifted_bytes = _canonical_bytes(observation, "shifted")
    cycle_bytes = _canonical_bytes(observation, "cycle")
    # The reviewed bytes leave the version out; "package_version" pins it.
    field = b'"package_version":' + json.dumps(observation["package_version"]).encode()
    assert document.count(field) == 1
    unversioned = document.replace(field, b'"package_version":null')
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "runtime_identities_distinct": observation["runtime_identities_distinct"],
        "relations": project["relations"],
        "operators": project["operators"],
        "coordinate_counts": [
            len(cast(list[object], project["nodes"])),
            len(cast(list[object], project["outputs"])),
            len(cast(list[object], project["input_slots"])),
            len(cast(list[object], project["uses"])),
        ],
        "coordinates_sha256": _digest(
            [
                project["nodes"],
                project["outputs"],
                project["input_slots"],
                project["uses"],
            ]
        ),
        "cross_edges": project["cross_edges"],
        "provided_properties_sha256": _digest(project["provided_properties"]),
        "effects_sha256": _digest(project["effects"]),
        "aggregate_contexts": project["aggregate_contexts"],
        "window_operator_contexts": project["window_operator_contexts"],
        "window_result_contexts": project["window_result_contexts"],
        "verification": project["verification"],
        "topological": project["topological"],
        "reachability_sha256": _digest(project["reachability"]),
        "equivalence_sha256": _digest(project["equivalence"]),
        "rewrite_readiness_sha256": _digest(project["rewrite_readiness"]),
        "queries": project["queries"],
        "canonical_sha256": hashlib.sha256(project_bytes).hexdigest(),
        "canonical_size": len(project_bytes),
        "shifted": {
            "starting_coordinates": shifted["starting_coordinates"],
            "first_node": shifted["first_node"],
            "canonical_sha256": hashlib.sha256(shifted_bytes).hexdigest(),
            "canonical_size": len(shifted_bytes),
        },
        "cycle": {
            "relations": cycle["relations"],
            "non_concrete": cycle["non_concrete"],
            "concrete": cycle["concrete"],
            "verification": cycle["verification"],
            "canonical_sha256": hashlib.sha256(cycle_bytes).hexdigest(),
            "canonical_size": len(cycle_bytes),
        },
        "invalid_verification": observation["invalid_verification"],
        "pure_rejections": observation["pure_rejections"],
        "observation_sha256": hashlib.sha256(unversioned).hexdigest(),
        "observation_size": len(unversioned),
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase61")
    observations: dict[str, bytes] = {}
    for seed in SEEDS:
        observations[f"seed:{seed}"] = documents[f"seed:{seed}"]

    interpreters = store.interpreters
    for interpreter_version, executable in interpreters.items():
        key = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        observations[key] = (
            observations["seed:0"] if executable == sys.executable else documents[key]
        )

    observations["project-relocated"] = documents["project-relocated"]
    observations["source-relocated"] = documents["source-relocated"]
    for interpreter_version, seed in (((3, 12), "1"), ((3, 13), "4294967295")):
        if interpreter_version not in interpreters:
            continue
        key = (
            f"combined:python{interpreter_version[0]}.{interpreter_version[1]}:"
            f"seed{seed}:relocated"
        )
        observations[key] = documents[key]

    observations["installed-wheel"] = documents["installed-wheel"]
    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origin": store.import_origin(
            acquisition.Cell(sys.version_info[:2], "0", "installed")
        ),
        "installed_source_root": store.installed_source_root(),
        "empty_install_cache": store.empty_install_cache(),
    }
