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
            "7d9ed1afb5f467701b65c3ae9d831bdd6d18429dc35cfabd439fa7f3780f32aa",
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
            "5c6e78b3e0bb745fee824833087dd5efa202835f0f18dd536393c844ea2d1a3a",
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
            "0a9be95b8c5e10e075a0c9436cab70312fe0bbaa6862353f7683ec66eeea24c1",
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
            "c1e3b641068c33ea4b6d225dd2e6b9bef7b1ea18c3e77f9f5e436926e444c440",
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
            "ea786360190f55eaeb5f502749d47f04917906504f9afcbe5faad491929c9017",
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
            "91f0adcc280515ccf4fd5d9b97143288c47d6eb4d0958378228ead20cbdc9af4",
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
            "ffaef720fcc6c7247b8777b9965fb6f23e36a66ee2a0ff37a2228e97ba1ff3ad",
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
            "4210647b0f1501106e603f7347633dbd4211d74a3067fd7aca9800d803db7bca",
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
            "bb470bd789be7a787cb3a5f17c11eea4ff508347a400cf37828fa14dbf9d8c6e",
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
            "468ff91c44cbd8fd51e33e10b6266a6444070fb59fd74a05b93bfa0e953b0db3",
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
            "d8a2479c2139a6483c7cdb826b57c03791916cc18edd7b5b6d4bcb4c359525aa",
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
            "8674f31539d9aa957389b96dcae064d0e0feed8880ce04bfc37250997b51ec2b",
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
            "121b6d543f8331037accdd38979a386677e003c006e508d7bd3fb330ca58b199",
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
            "a2da477a9042e5eb7269c7e537ba252cd0a1f796b9bfe1dea326a3a0f6b21eeb",
            617,
            "",
        ],
        [
            "mysql",
            0,
            "cacddefeda512e14ad3f70ad7755cc3ded88c43cf161a4503cf75bca43fa0b3d",
            229,
            "",
        ],
    ],
    "observation_sha256": "5d0fda10c364439340f4b0a23a3385ccd74ee1c1a34bf27115fbd7ee72486dc1",
    "observation_size": 48240,
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
