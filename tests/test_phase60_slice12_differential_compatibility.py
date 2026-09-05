from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import cast

import pytest

import _pietto_differential_process_acquisition as acquisition
import _pietto_phase60_window_differential_probe as probe
import test_phase60_slice11_real_authored_advanced_window_e2e as slice11


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_phase60_window_differential_probe.py"
PHASE59_PROBE = REPO_ROOT / "tests/_pietto_phase59_graph_differential_probe.py"
SCENARIOS = REPO_ROOT / "tests/_pietto_project_explain_scenarios.py"
SPEC = REPO_ROOT / "docs/spec/phase60-slice12-differential-compatibility-v1.md"
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Filled from one reviewed predecessor observation; every matrix member must
# consume this unchanged rather than regenerating an environment-local oracle.
EXPECTED_COMMON_MANIFEST: dict[str, object] = {
    "observation_format": "pietto.phase60-window-differential.v1",
    "package_version": "0.1.0",
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
                    "location": ["postgres_ignore_nulls.pietto", 6, 1, 12, 15],
                }
            ],
            "7f5bec37cc2cc6ab1c360df0a5e17d5813c3254f7b9ec90a9a0410ff19452190",
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
                    "location": ["postgres_from_last.pietto", 6, 1, 12, 15],
                }
            ],
            "76a0c8698dc24d146fac5b8792c0017dea20e25efb41f43a51b618c4453e036d",
        ],
        [
            "postgres_range_offset",
            "not_lowerable",
            "PostgreSQL RANGE offsets require Phase 64 evidence",
            [["frame_shape", "PostgreSQL RANGE offsets require Phase 64 evidence"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "PostgreSQL SQL emission is not implemented for RelationIR: result. "
                    "PostgreSQL RANGE offsets require Phase 64 evidence",
                    "location": ["postgres_range_offset.pietto", 6, 1, 13, 26],
                }
            ],
            "f00690f9ac383af9eb951272e6100f708ef80d6053b10ccde033e3500664d359",
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
                    "location": ["mysql_groups.pietto", 6, 1, 13, 27],
                }
            ],
            "48105edde77d183e96418d1b6b05d6f38c6d9c89e96cf0b84f58b302b23ea11d",
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
                    "location": ["mysql_exclude.pietto", 6, 1, 13, 43],
                }
            ],
            "c50d2971bf326fdb77bc5be0ee0f5a94ad32311d983e80eb33533c820d6d1111",
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
                    "location": ["mysql_ignore_nulls.pietto", 6, 1, 12, 15],
                }
            ],
            "bc714f6eb13d5bbc26923897493df02f46c668f1809d864f01c1fc5b1e976a77",
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
                    "location": ["mysql_from_last.pietto", 6, 1, 12, 15],
                }
            ],
            "09c54cb713121bec9eca9e410448b6c48f718c3b8dfe6c608f670dc136305755",
        ],
        [
            "mysql_range_offset",
            "not_lowerable",
            "MySQL RANGE offsets require Phase 64 evidence",
            [["frame_shape", "MySQL RANGE offsets require Phase 64 evidence"]],
            [
                {
                    "code": "PIE-B1000",
                    "severity": "error",
                    "message": "MySQL SQL emission is not implemented for RelationIR: result. MySQL "
                    "RANGE offsets require Phase 64 evidence",
                    "location": ["mysql_range_offset.pietto", 6, 1, 13, 26],
                }
            ],
            "292338d4f530084c8bb8bf9be520b04144d941a66456ca747269463f34b8c206",
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
        "canonical_sha256": "381b2079b1d3c006288a9cfa59a27be52d5ff8cfbfef4ffcde2ed5dfa9c7b740",
        "canonical_size": 25048,
        "named_sha256": "49a028449f9e66a38af9e664efc0f0a885830ae4ddb61dd33a566e5953510ccc",
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
    "observation_sha256": "84f08fb8349134e1d4a55cc8f02378a3921b3982829359d84a09630140674f75",
    "observation_size": 46895,
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
        "observation_sha256": hashlib.sha256(document).hexdigest(),
        "observation_size": len(document),
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


def test_current_source_matches_one_reviewed_common_manifest(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    assert _common_manifest(observations["seed:0"]) == EXPECTED_COMMON_MANIFEST


def test_four_hash_seeds_preserve_exact_observation_bytes(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    assert SEEDS == ("0", "1", "7", "4294967295")
    assert all(observations[f"seed:{seed}"] == observations["seed:0"] for seed in SEEDS)


def test_all_available_supported_interpreters_and_combined_cases_match(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert sys.version_info[:2] in SUPPORTED_INTERPRETERS
    assert sys.version_info[:2] in interpreters
    for version in interpreters:
        key = f"python{version[0]}.{version[1]}"
        assert observations[key] == observations["seed:0"]
        seed = "1" if version == (3, 12) else "4294967295"
        combined = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
        assert observations[combined] == observations["seed:0"]


def test_project_source_relocation_cwd_and_ambient_state_do_not_leak(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    for key in ("project-relocated", "source-relocated"):
        assert observations[key] == observations["seed:0"]
    document = observations["seed:0"]
    for forbidden in (
        str(REPO_ROOT).encode(),
        b"project-relocated",
        b"source-relocated",
        b"PIETTO_SLICE12_IRRELEVANT",
        b"0x",
    ):
        assert forbidden not in document


def test_isolated_installed_wheel_matches_and_has_non_repository_origin(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    origin = cast(Path, differential_matrix["installed_origin"])
    source_root = cast(Path, differential_matrix["installed_source_root"])
    empty_cache = cast(Path, differential_matrix["empty_install_cache"])
    assert origin.is_relative_to(source_root / "src")
    assert not origin.is_relative_to(REPO_ROOT)
    assert empty_cache.is_dir()
    assert observations["installed-wheel"] == observations["seed:0"]


def test_independent_construction_command_order_and_positive_subjects_are_exact(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = _decoded(observations["seed:0"])
    assert baseline["runtime_identities_distinct"] is True
    targets = cast(dict[str, dict[str, object]], baseline["targets"])
    assert [
        cast(dict[str, object], targets[name]["decision"])["strategy"]
        for name in ("postgres_native", "mysql_native", "postgres_fallback")
    ] == ["native_reorder", "native_preserve", "inline_exact"]
    assert (
        targets["postgres_fallback"]["artifacts"]
        == targets["postgres_inline"]["artifacts"]
    )
    frames = [
        cast(dict[str, object], item["ir"])["frame"]
        for name in targets
        for item in cast(list[dict[str, object]], targets[name]["semantic"])
        if cast(dict[str, object], item["ir"])["frame"] is not None
    ]
    assert {cast(dict[str, object], frame)["unit"] for frame in frames} == {
        "ROWS",
        "RANGE",
        "GROUPS",
    }
    assert {cast(dict[str, object], frame)["exclusion"] for frame in frames} >= {
        "NO OTHERS",
        "CURRENT ROW",
        "GROUP",
        "TIES",
    }
    cli = cast(dict[str, list[object]], baseline["cli"])
    assert [cli[target][0] for target in ("postgres", "mysql")] == [0, 0]
    assert [cli[target][2] for target in ("postgres", "mysql")] == ["", ""]


def test_backend_negative_cases_are_identical_fail_closed_terminals(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = _decoded(observations["seed:0"])
    negatives = cast(list[list[object]], baseline["negatives"])
    assert [item[0] for item in negatives] == [
        "postgres_ignore_nulls",
        "postgres_from_last",
        "postgres_range_offset",
        "mysql_groups",
        "mysql_exclude",
        "mysql_ignore_nulls",
        "mysql_from_last",
        "mysql_range_offset",
    ]
    for _name, raw_target in negatives:
        target = cast(dict[str, object], raw_target)
        assert target["semantic"]
        decision = cast(dict[str, object], target["decision"])
        assert decision["strategy"] == "not_lowerable"
        assert target["artifacts"] == []
        diagnostics = cast(list[dict[str, object]], target["diagnostics"])
        assert [item["code"] for item in diagnostics] == ["PIE-B1000"]
        assert [item["severity"] for item in diagnostics] == ["error"]
    assert baseline["negative_project"] == {
        "status": "concrete",
        "use_kind": "named_direct",
        "target": 0,
        "null_treatment": "ignore_nulls",
        "null_explicit": True,
        "roles": ["window_argument", "window_order"],
    }


def test_project_provenance_lineage_and_private_inspection_are_stable(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    graph = cast(dict[str, object], _decoded(observations["seed:0"])["graph"])
    expected_graph = cast(dict[str, object], EXPECTED_COMMON_MANIFEST["graph"])
    assert graph["canonical_sha256"] == expected_graph["canonical_sha256"]
    provenance = cast(list[dict[str, object]], graph["provenance"])
    assert [item["function"] for item in provenance] == [
        "row_number",
        "first_value",
        "nth_value",
        "lag",
    ]
    assert [item["use_kind"] for item in provenance] == ["named_direct"] * 4
    lineage = cast(list[list[object]], graph["lineage"])
    assert [item[1] for item in lineage] == [
        "relation_input",
        "window_partition",
        "window_order",
        "window_argument",
        "window_partition",
        "window_order",
        "window_argument",
        "window_partition",
        "window_order",
        "window_argument",
        "window_default",
        "window_partition",
        "window_order",
    ]


def test_probe_reuses_slice11_sources_and_existing_harnesses_without_normalizing() -> (
    None
):
    assert probe.POSTGRES_NATIVE == slice11.POSTGRES_NATIVE
    assert probe.POSTGRES_FALLBACK == slice11.POSTGRES_FALLBACK
    assert probe.POSTGRES_FALLBACK_INLINE == slice11.POSTGRES_FALLBACK_INLINE
    assert probe.POSTGRES_FRAMES == slice11.POSTGRES_FRAMES
    assert probe.MYSQL_NATIVE == slice11.MYSQL_NATIVE
    tree = ast.parse(PROBE.read_text(encoding="utf-8"), filename=str(PROBE))
    forbidden_calls = {
        "WindowCallIR",
        "RelationIR",
        "NamedWindowLoweringDecision",
        "WindowResultProjectFact",
        "PackageGraphSnapshot",
        "PackageGraphInspectionRecord",
        "PackageGraphInspectionLink",
        "sorted",
    }
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert forbidden_calls.isdisjoint(called)
    source = PROBE.read_text(encoding="utf-8")
    assert "graph_probe._real_graph(" in source
    assert "graph_probe._record_value(" in source
    assert "graph_probe._link_value(" in source
    assert "_run_cli_pair(" in source
    assert "subprocess.run(" not in source
    assert "sort_keys=False" in source
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "lru_cache",
        "functools.cache",
        "shelve",
        "pickle",
    ):
        assert forbidden not in source


def test_slice12_spec_lifecycle_and_preserved_boundary_are_exact() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "one reviewed common expectation",
        "PYTHONHASHSEED = 0, 1, 7, 4294967295",
        "Python 3.12 and Python 3.13",
        "repository source, relocated source, and isolated installed wheel",
        "PostgreSQL then MySQL and MySQL then PostgreSQL",
        "serial and xdist --dist=loadfile",
        "first_value(aggregate_output_alias)",
        "Slice 12 current",
        "Slice 13 next/unstarted",
        "Add Phase 60 differential compatibility assurance",
    ):
        assert required in normalized
