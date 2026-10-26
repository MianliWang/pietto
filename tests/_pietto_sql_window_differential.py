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
PROBE = REPO_ROOT / "tests/_pietto_ir_window_differential.py"
PHASE59_PROBE = REPO_ROOT / "tests/_pietto_project_graph_differential.py"
SCENARIOS = REPO_ROOT / "tests/_pietto_project_explain_scenarios.py"
SPEC = REPO_ROOT / "docs/spec/phase60-slice12-differential-compatibility-v1.md"
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# The single-file refusal of a RANGE frame with an offset, for one target.
_RANGE_OFFSET = (
    "{} RANGE offsets are not supported in single-file emit-sql; use ROWS, RANGE "
    "without an offset, or emit-sql --project with a nonnegative Int literal "
    "offset and one non-null Int ORDER key stored in at most 32 bits"
)
# Filled from one reviewed predecessor observation; every matrix member must
# consume this unchanged rather than regenerating an environment-local oracle.
EXPECTED_COMMON_MANIFEST: dict[str, object] = {
    "observation_format": "pietto.phase60-window-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "runtime_identities_distinct": True,
    "targets": [
        [
            "postgres_native",
            "native_reorder",
            [[0, "child"], [2, "base"]],
            [[2, "base"], [0, "child"]],
            [
                ["ranking", "row_number", "named_direct", 0, None, None, None],
                [
                    "first",
                    "first_value",
                    "named_direct",
                    0,
                    {
                        "unit": "RANGE",
                        "start": ["UNBOUNDED PRECEDING", None],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "NO OTHERS",
                        "frame_explicit": False,
                        "end_explicit": False,
                        "exclusion_explicit": False,
                    },
                    "respect_nulls",
                    None,
                ],
                [
                    "nth",
                    "nth_value",
                    "named_direct",
                    0,
                    {
                        "unit": "RANGE",
                        "start": ["UNBOUNDED PRECEDING", None],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "NO OTHERS",
                        "frame_explicit": False,
                        "end_explicit": False,
                        "exclusion_explicit": False,
                    },
                    "respect_nulls",
                    "from_first",
                ],
                ["previous", "lag", "named_direct", 0, None, "respect_nulls", None],
            ],
            ["e87b1294b483f3ab42473a1e05cbe908fb0559849af5e53cd336a9d7ef2ffacb"],
            "fd6534e9f93c0546ed325ed854a311642e2a4cfcbf6110fbdc592fd9698696b1",
        ],
        [
            "mysql_native",
            "native_preserve",
            [[0, "child"], [2, "base"]],
            [[0, "child"], [2, "base"]],
            [
                [
                    "result",
                    "nth_value",
                    "named_extended",
                    0,
                    {
                        "unit": "ROWS",
                        "start": ["OFFSET PRECEDING", 1],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "NO OTHERS",
                        "frame_explicit": True,
                        "end_explicit": True,
                        "exclusion_explicit": False,
                    },
                    "respect_nulls",
                    "from_first",
                ]
            ],
            ["1344775321c50d9417853a6fd789166602bcf368caf7f6d8c956c8206b46c171"],
            "59063e5415432f0b9ef25635c4ad3290a0ae59721138d5712a8cd8c9c82245a3",
        ],
        [
            "postgres_fallback",
            "inline_exact",
            [[0, "derived"], [1, "framed"]],
            [],
            [
                [
                    "result",
                    "nth_value",
                    "named_direct",
                    0,
                    {
                        "unit": "GROUPS",
                        "start": ["OFFSET PRECEDING", 1],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "TIES",
                        "frame_explicit": True,
                        "end_explicit": True,
                        "exclusion_explicit": True,
                    },
                    "respect_nulls",
                    "from_first",
                ]
            ],
            ["9bb688fdaad623bdd5d58ba029032c22c69963403f3a67ba7ddf526fd409296d"],
            "25fc035e665903fcd89c3db255aada56e2db75fc526e61d564776808a7eaf71f",
        ],
        [
            "postgres_inline",
            None,
            [],
            [],
            [
                [
                    "result",
                    "nth_value",
                    "inline",
                    None,
                    {
                        "unit": "GROUPS",
                        "start": ["OFFSET PRECEDING", 1],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "TIES",
                        "frame_explicit": True,
                        "end_explicit": True,
                        "exclusion_explicit": True,
                    },
                    "respect_nulls",
                    "from_first",
                ]
            ],
            ["9bb688fdaad623bdd5d58ba029032c22c69963403f3a67ba7ddf526fd409296d"],
            "9d1c8154c4f35ef7be3669e9f3ba406c194874fc30a5ea9381cdf04e2fe37ae4",
        ],
        [
            "postgres_frames",
            None,
            [],
            [],
            [
                [
                    "rows_value",
                    "last_value",
                    "inline",
                    None,
                    {
                        "unit": "ROWS",
                        "start": ["OFFSET PRECEDING", 1],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "CURRENT ROW",
                        "frame_explicit": True,
                        "end_explicit": True,
                        "exclusion_explicit": True,
                    },
                    "respect_nulls",
                    None,
                ],
                [
                    "range_value",
                    "first_value",
                    "inline",
                    None,
                    {
                        "unit": "RANGE",
                        "start": ["CURRENT ROW", None],
                        "end": ["CURRENT ROW", None],
                        "exclusion": "GROUP",
                        "frame_explicit": True,
                        "end_explicit": False,
                        "exclusion_explicit": True,
                    },
                    "respect_nulls",
                    None,
                ],
            ],
            ["d876db36cc1f4e20894c632cd25c21a362c190320d4c2806d43f4ddf8bd0e9df"],
            "3014fde04d339f03f5de3d545efe899a3dbf268cf88d531465f7b980454bd506",
        ],
    ],
    "negatives": [
        [
            "postgres_ignore_nulls",
            "not_lowerable",
            "PostgreSQL does not support IGNORE NULLS",
            [["null_treatment", "PostgreSQL does not support IGNORE NULLS"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "PostgreSQL SQL emission is not implemented for RelationIR: result. "
                    "PostgreSQL does not support IGNORE NULLS",
                    "location": ["postgres_ignore_nulls.pietto", 6, 1, 12, 67],
                }
            ],
            "74c3309991403cf3397cf8d5018946b4ca4187d15a7a6733570e35bee97ca818",
        ],
        [
            "postgres_from_last",
            "not_lowerable",
            "PostgreSQL does not support FROM LAST",
            [["nth_direction", "PostgreSQL does not support FROM LAST"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "PostgreSQL SQL emission is not implemented for RelationIR: result. "
                    "PostgreSQL does not support FROM LAST",
                    "location": ["postgres_from_last.pietto", 6, 1, 12, 65],
                }
            ],
            "1eea4bc839d03e9fd8fc0a6d2f871ebc71783bf120519c0fce07a3d4b9050f3e",
        ],
        [
            "postgres_range_offset",
            "not_lowerable",
            _RANGE_OFFSET.format("PostgreSQL"),
            [["frame_shape", _RANGE_OFFSET.format("PostgreSQL")]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "PostgreSQL SQL emission is not implemented for RelationIR: result. "
                    + _RANGE_OFFSET.format("PostgreSQL"),
                    "location": ["postgres_range_offset.pietto", 6, 1, 13, 54],
                }
            ],
            "bcb53d743bce9a3a873a8ce08a4e5675cd478683ec2fe7f0a598c74472567b99",
        ],
        [
            "mysql_groups",
            "not_lowerable",
            "MySQL does not support GROUPS frames",
            [["frame_shape", "MySQL does not support GROUPS frames"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. MySQL "
                    "does not support GROUPS frames",
                    "location": ["mysql_groups.pietto", 6, 1, 13, 54],
                }
            ],
            "e93916a1eb9252a3e6965fc4085b4b3dd851fda97ba9c95ed14cda5f08986281",
        ],
        [
            "mysql_exclude",
            "not_lowerable",
            "MySQL does not support authored EXCLUDE frames",
            [["exclusion", "MySQL does not support authored EXCLUDE frames"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. MySQL "
                    "does not support authored EXCLUDE frames",
                    "location": ["mysql_exclude.pietto", 6, 1, 13, 54],
                }
            ],
            "2e7eda78de16c613edc8036cdeff5c4bb628c48f4d82d1749c43d7a0498dec2d",
        ],
        [
            "mysql_ignore_nulls",
            "not_lowerable",
            "MySQL does not execute IGNORE NULLS",
            [["null_treatment", "MySQL does not execute IGNORE NULLS"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. MySQL "
                    "does not execute IGNORE NULLS",
                    "location": ["mysql_ignore_nulls.pietto", 6, 1, 12, 67],
                }
            ],
            "1f5dd941fe38920930808216dedbb4499fdcdab57606bc9def3b8fe0b7e4b456",
        ],
        [
            "mysql_from_last",
            "not_lowerable",
            "MySQL does not execute FROM LAST",
            [["nth_direction", "MySQL does not execute FROM LAST"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. MySQL "
                    "does not execute FROM LAST",
                    "location": ["mysql_from_last.pietto", 6, 1, 12, 65],
                }
            ],
            "04574fdd9b0542dd6f93e695bdb88af9ee69ce2b1d98c81d961851fe16d76804",
        ],
        [
            "mysql_range_offset",
            "not_lowerable",
            _RANGE_OFFSET.format("MySQL"),
            [["frame_shape", _RANGE_OFFSET.format("MySQL")]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. "
                    + _RANGE_OFFSET.format("MySQL"),
                    "location": ["mysql_range_offset.pietto", 6, 1, 13, 54],
                }
            ],
            "dd8edb7ab1a6e920306c53e5eb3f61fd5ef068df757e41c444857ff7c1552f20",
        ],
    ],
    "negative_project": {
        "status": "concrete",
        "use_kind": "named_direct",
        "target": 0,
        "null_treatment": "ignore_nulls",
        "null_explicit": True,
        "roles": ["window_argument", "window_order"],
    },
    "graph": {
        "canonical_sha256": "d3492106f0c9f8accd31ee793c8a8dca9b7b60d04d01fba5afb153598715e10e",
        "canonical_size": 24979,
        "named_sha256": "4d6070635291ca4865b007e55558daa6dd6a5e0da99ee1a38a72e99f237e7d6a",
        "semantic_sha256": "7b8791721352b4ddcd8545218e5137b56ef15280620b1ba398952fe57423f20b",
        "links_sha256": "efd3d750c39e099ae7057f6b11409fe7cc6daea6c53bc7aedd3e573f9342cb73",
        "provenance": [
            {
                "output": [0, 0, 2, 2],
                "function": "row_number",
                "use_kind": "named_direct",
                "target": 0,
                "origins": ["inherited", "inherited", "not_applicable"],
                "frame": ["not_applicable", None, None, None, None],
                "modifiers": [None, False, None, False],
            },
            {
                "output": [0, 0, 2, 3],
                "function": "first_value",
                "use_kind": "named_direct",
                "target": 0,
                "origins": ["inherited", "inherited", "effective_default"],
                "frame": [
                    "applicable",
                    "range",
                    "unbounded_preceding",
                    "current_row",
                    "no_others",
                ],
                "modifiers": ["respect_nulls", True, None, False],
            },
            {
                "output": [0, 0, 2, 4],
                "function": "nth_value",
                "use_kind": "named_direct",
                "target": 0,
                "origins": ["inherited", "inherited", "effective_default"],
                "frame": [
                    "applicable",
                    "range",
                    "unbounded_preceding",
                    "current_row",
                    "no_others",
                ],
                "modifiers": ["respect_nulls", True, "from_first", True],
            },
            {
                "output": [0, 0, 2, 5],
                "function": "lag",
                "use_kind": "named_direct",
                "target": 0,
                "origins": ["inherited", "inherited", "not_applicable"],
                "frame": ["not_applicable", None, None, None, None],
                "modifiers": ["respect_nulls", True, None, False],
            },
        ],
        "lineage": [
            [2, "relation_input", 0, 0, "PackageGraphDeclarationRef"],
            [2, "window_partition", 1, 0, "PackageGraphFieldRef"],
            [2, "window_order", 2, 0, "PackageGraphFieldRef"],
            [3, "window_argument", 0, 0, "PackageGraphFieldRef"],
            [3, "window_partition", 1, 0, "PackageGraphFieldRef"],
            [3, "window_order", 2, 0, "PackageGraphFieldRef"],
            [4, "window_argument", 0, 0, "PackageGraphFieldRef"],
            [4, "window_partition", 1, 0, "PackageGraphFieldRef"],
            [4, "window_order", 2, 0, "PackageGraphFieldRef"],
            [5, "window_argument", 0, 0, "PackageGraphFieldRef"],
            [5, "window_default", 1, 0, "PackageGraphFieldRef"],
            [5, "window_partition", 2, 0, "PackageGraphFieldRef"],
            [5, "window_order", 3, 0, "PackageGraphFieldRef"],
        ],
    },
    "cli": [
        [
            "postgres",
            0,
            "354e40f887f7d554da32f2ad20d1ad0c79431c1b777e6fa34a6f0b712d27c5d0",
            628,
            "",
        ],
        [
            "mysql",
            0,
            "a8d2bc5d44392a9d604f7d2a2379ba474a045d4030524e3013ba381ee45433a3",
            240,
            "",
        ],
    ],
    "observation_sha256": "31bedd3b0dae83217ebe581ea4e1854bbaf012acf162d52d03f4b0d12cc94d70",
    "observation_size": 50265,
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


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _semantic_summary(item: dict[str, object]) -> list[object]:
    ir = cast(dict[str, object], item["ir"])
    return [
        item["output"],
        ir["function"],
        item["analysis_use"],
        item["target"],
        ir["frame"],
        ir["null_treatment"],
        ir["nth_direction"],
    ]


def _target_summary(name: str, target: dict[str, object]) -> list[object]:
    decision = cast(dict[str, object] | None, target["decision"])
    artifacts = cast(list[list[object]], target["artifacts"])
    semantic = cast(list[dict[str, object]], target["semantic"])
    return [
        name,
        None if decision is None else decision["strategy"],
        [] if decision is None else decision["reachable"],
        [] if decision is None else decision["emission"],
        [_semantic_summary(item) for item in semantic],
        [
            hashlib.sha256(cast(str, artifact[2]).encode()).hexdigest()
            for artifact in artifacts
        ],
        _digest(target),
    ]


def _negative_summary(item: list[object]) -> list[object]:
    name = cast(str, item[0])
    target = cast(dict[str, object], item[1])
    decision = cast(dict[str, object], target["decision"])
    inline = cast(list[dict[str, object]], decision["inline"])
    diagnostics = cast(list[dict[str, object]], target["diagnostics"])
    unsupported = [
        [evidence["kind"], evidence["detail"]]
        for evidence in cast(list[dict[str, object]], inline[0]["evidence"])
        if evidence["outcome"] == "unsupported"
    ]
    return [
        name,
        decision["strategy"],
        decision["reason"],
        unsupported,
        diagnostics,
        _digest(target),
    ]


def _common_manifest(document: bytes) -> dict[str, object]:
    observation = _decoded(document)
    targets = cast(dict[str, dict[str, object]], observation["targets"])
    graph = cast(dict[str, object], observation["graph"])
    cli = cast(dict[str, list[object]], observation["cli"])
    # The reviewed bytes leave the version out; "package_version" pins it.
    field = b'"package_version":' + json.dumps(observation["package_version"]).encode()
    assert document.count(field) == 1
    unversioned = document.replace(field, b'"package_version":null')
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "runtime_identities_distinct": observation["runtime_identities_distinct"],
        "targets": [
            _target_summary(name, targets[name])
            for name in (
                "postgres_native",
                "mysql_native",
                "postgres_fallback",
                "postgres_inline",
                "postgres_frames",
            )
        ],
        "negatives": [
            _negative_summary(item)
            for item in cast(list[list[object]], observation["negatives"])
        ],
        "negative_project": observation["negative_project"],
        "graph": {
            "canonical_sha256": graph["canonical_sha256"],
            "canonical_size": graph["canonical_size"],
            "named_sha256": _digest(graph["named_records"]),
            "semantic_sha256": _digest(graph["semantic_records"]),
            "links_sha256": _digest(graph["named_links"]),
            "provenance": graph["provenance"],
            "lineage": graph["lineage"],
        },
        "cli": [
            [
                target,
                values[0],
                hashlib.sha256(cast(str, values[1]).encode()).hexdigest(),
                len(cast(str, values[1]).encode()),
                values[2],
            ]
            for target, values in cli.items()
        ],
        "observation_sha256": hashlib.sha256(unversioned).hexdigest(),
        "observation_size": len(unversioned),
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase60")
    observations: dict[str, bytes] = {}
    for seed in SEEDS:
        observations[f"seed:{seed}"] = documents[f"seed:{seed}"]

    interpreters = store.interpreters
    for version, executable in interpreters.items():
        key = f"python{version[0]}.{version[1]}"
        observations[key] = (
            observations["seed:0"] if executable == sys.executable else documents[key]
        )

    observations["project-relocated"] = documents["project-relocated"]
    observations["source-relocated"] = documents["source-relocated"]
    for version, seed in (((3, 12), "1"), ((3, 13), "4294967295")):
        if version not in interpreters:
            continue
        key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
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
