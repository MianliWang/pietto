from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import cast

import pytest

import _pietto_phase59_graph_differential_probe as probe
import test_phase58_slice13_project_explain_runtime_builder as runtime_fixture
import test_phase58_slice16_pure_differential_compatibility_assurance as phase58_diff
import test_phase59_slice10_real_multi_package_provenance_lineage_e2e as slice10


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_phase59_graph_differential_probe.py"
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
    "package_version": "0.1.0",
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


def _environment(source_root: Path | None, seed: str, ambient: str) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIETTO_SLICE11_IRRELEVANT"] = ambient
    if source_root is not None:
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(source_root / "src"), phase58_diff._site_packages())
        )
    return environment


def _run_probe(
    executable: str,
    probe_path: Path,
    workspace: Path,
    *,
    source_root: Path | None,
    seed: str,
    ambient: str,
) -> dict[str, object]:
    run_root = workspace.parent / f"run-{workspace.name}"
    run_root.mkdir()
    completed = subprocess.run(
        (executable, str(probe_path), "--workspace", str(workspace)),
        check=True,
        capture_output=True,
        cwd=run_root,
        env=_environment(source_root, seed, ambient),
    )
    assert completed.stderr == b""
    assert completed.stdout.endswith(b"\n")
    assert not completed.stdout.endswith(b"\n\n")
    return cast(dict[str, object], json.loads(completed.stdout))


def _relocate_source(target: Path) -> Path:
    shutil.copytree(
        REPO_ROOT / "src",
        target / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    tests = target / "tests"
    tests.mkdir()
    shutil.copyfile(PROBE, tests / PROBE.name)
    shutil.copyfile(SCENARIOS, tests / SCENARIOS.name)
    return tests / PROBE.name


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
    observations: dict[str, dict[str, object]] = {}
    for seed in SEEDS:
        observations[f"seed:{seed}"] = _run_probe(
            sys.executable,
            PROBE,
            tmp_path_factory.mktemp(f"seed-{seed}"),
            source_root=REPO_ROOT,
            seed=seed,
            ambient=f"seed-{seed}",
        )

    interpreters = phase58_diff._available_supported_interpreters()
    for version, executable in interpreters.items():
        key = f"python{version[0]}.{version[1]}"
        observations[key] = (
            observations["seed:0"]
            if executable == sys.executable
            else _run_probe(
                executable,
                PROBE,
                tmp_path_factory.mktemp(key),
                source_root=REPO_ROOT,
                seed="0",
                ambient=key,
            )
        )

    observations["project-relocated"] = _run_probe(
        sys.executable,
        PROBE,
        tmp_path_factory.mktemp("project-relocated"),
        source_root=REPO_ROOT,
        seed="0",
        ambient="project-relocated",
    )
    relocated_root = tmp_path_factory.mktemp("source-relocated")
    relocated_probe = _relocate_source(relocated_root)
    observations["source-relocated"] = _run_probe(
        sys.executable,
        relocated_probe,
        tmp_path_factory.mktemp("source-relocated-project"),
        source_root=relocated_root,
        seed="0",
        ambient="source-relocated",
    )
    for version, seed in (((3, 12), "1"), ((3, 13), "4294967295")):
        executable = interpreters.get(version)
        if executable is not None:
            key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
            observations[key] = _run_probe(
                executable,
                relocated_probe,
                tmp_path_factory.mktemp(key.replace(":", "-")),
                source_root=relocated_root,
                seed=seed,
                ambient=key,
            )

    wheel_root = tmp_path_factory.mktemp("installed-wheel")
    (
        installed_python,
        installed_origin,
        installed_source_root,
        empty_install_cache,
    ) = phase58_diff._installed_python(wheel_root)
    observations["installed-wheel"] = _run_probe(
        installed_python,
        PROBE,
        tmp_path_factory.mktemp("installed-project"),
        source_root=installed_source_root,
        seed="0",
        ambient="installed-wheel",
    )
    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origin": installed_origin,
        "installed_source_root": installed_source_root,
        "empty_install_cache": empty_install_cache,
    }


def test_current_source_matches_one_reviewed_common_manifest(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    assert _common_manifest(observations["seed:0"]) == EXPECTED_COMMON_MANIFEST


def test_four_hash_seeds_preserve_complete_semantics_order_and_multiplicity(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    assert SEEDS == ("0", "1", "7", "4294967295")
    assert all(observations[f"seed:{seed}"] == observations["seed:0"] for seed in SEEDS)


def test_available_supported_interpreters_use_the_same_common_expectation(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert sys.version_info[:2] in SUPPORTED_INTERPRETERS
    assert sys.version_info[:2] in interpreters
    for version in interpreters:
        assert _common_manifest(observations[f"python{version[0]}.{version[1]}"]) == (
            EXPECTED_COMMON_MANIFEST
        )
        seed = "1" if version == (3, 12) else "4294967295"
        combined = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
        assert observations[combined] == observations["seed:0"]


def test_project_and_source_relocation_ignore_paths_cwd_and_ambient_state(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    for key in ("project-relocated", "source-relocated"):
        assert observations[key] == observations["seed:0"]
    document = _canonical_bytes(observations["seed:0"])
    for forbidden in (
        str(REPO_ROOT).encode(),
        b"source-relocated",
        b"project-relocated",
        b"PIETTO_SLICE11_IRRELEVANT",
        b"0x",
    ):
        assert forbidden not in document


def test_isolated_installed_wheel_matches_source_and_proves_import_origin(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    origin = cast(Path, differential_matrix["installed_origin"])
    source_root = cast(Path, differential_matrix["installed_source_root"])
    empty_cache = cast(Path, differential_matrix["empty_install_cache"])
    assert origin.is_relative_to(source_root / "src")
    assert not origin.is_relative_to(REPO_ROOT)
    assert empty_cache.is_dir()
    assert observations["installed-wheel"] == observations["seed:0"]


def test_real_graph_projection_retains_exact_domains_lineage_paths_and_why_not(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    baseline = observations["seed:0"]
    graph = cast(dict[str, object], baseline["graph"])
    records = cast(list[dict[str, object]], graph["records"])
    links = cast(list[dict[str, object]], graph["links"])
    queries = cast(dict[str, object], graph["queries"])
    assert baseline["runtime_refs_distinct"] is True
    assert graph["integrity"] == graph["pure_status"] == "ok"
    packages = [record for record in records if record["kind"] == "package"]
    assert [(_positions(record), _fields(record)["name"]) for record in packages] == [
        ([0], "dependency"),
        ([1], "root"),
    ]
    dependency = next(record for record in records if record["kind"] == "dependency")
    assert _positions(dependency) == [1, 0]
    assert _fields(dependency)["declaring_package"] == {
        "domain": "package",
        "positions": [1],
    }
    assert _fields(dependency)["resolved_package"] == {
        "domain": "package",
        "positions": [0],
    }
    modules = [record for record in records if record["kind"] == "module"]
    assert [_positions(record) for record in modules] == [[0, 0], [1, 0]]
    declarations = [record for record in records if record["kind"] == "declaration"]
    assert [_fields(record)["name"] for record in declarations[:6]] == [
        "Row",
        "rows",
        "projections",
        "calculations",
        "aggregates",
        "windows",
    ]
    assert [_fields(record)["name"] for record in declarations[6:]] == [
        _fields(record)["name"] for record in declarations[:6]
    ]
    fields = [record for record in records if record["kind"] == "field"]
    assert [_fields(record)["name"] for record in fields[:15]] == [
        _fields(record)["name"] for record in fields[15:]
    ]
    assert all(
        _positions(left)[0] != _positions(right)[0]
        for left, right in zip(fields[:15], fields[15:], strict=True)
    )
    assert [
        _positions(record) for record in records if record["kind"] == "requirement"
    ] == [[0, 0], [0, 1]]
    assert [
        _positions(record) for record in records if record["kind"] == "selector"
    ] == [[0, 0]]
    lineage = [link for link in links if str(link["kind"]).endswith("lineage")]
    assert {
        "source_lineage",
        "projection_lineage",
        "expression_lineage",
        "current_window_lineage",
    } == {cast(str, link["kind"]) for link in lineage}
    assert all(
        _positions(link, "source")[0] == _positions(link, "target")[0]
        for link in lineage
    )
    repeated = [
        link
        for link in lineage
        if link["kind"] == "expression_lineage"
        and cast(dict[str, object], link["source"])["domain"] == "field"
        and _positions(link, "source") == [0, 0, 3, 0]
        and _positions(link, "target") == [0, 0, 1, 1]
    ]
    assert len(repeated) == 2
    assert [_fields(link)["input_position"] for link in repeated] == [0, 1]
    all_paths = cast(list[list[int]], queries["all_paths_to_repeated_input"])
    assert len(all_paths) > 1 and len(set(map(tuple, all_paths))) == len(all_paths)
    why_not = cast(list[dict[str, object]], queries["why_not"])
    assert len(why_not) == 1
    assert why_not[0]["terminal_ref"] == {
        "domain": "capability_evaluation",
        "positions": [0, 1, 0],
    }
    assert why_not[0]["terminal_outcome"] == "unknown"


def test_project_explain_and_cli_remain_zero_delta_on_the_same_real_project(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    public = cast(dict[str, object], observations["seed:0"]["project_explain"])
    assert public["runtime_outcome"] == "success"
    assert public["cli_json_exit"] == public["cli_text_exit"] == 0
    assert public == EXPECTED_COMMON_MANIFEST["project_explain"]


def test_probe_reuses_slice10_authored_scenario_without_hand_built_final_graph() -> (
    None
):
    assert probe.MODULE_SOURCE == slice10.MODULE_SOURCE
    assert probe.LOGICAL_REQUIREMENT == runtime_fixture.LOGICAL_REQUIREMENT
    assert probe.EXTENSION_REQUIREMENT == runtime_fixture.EXTENSION_REQUIREMENT
    assert probe.EXTENSION_SELECTOR == runtime_fixture.EXTENSION_SELECTOR
    tree = ast.parse(PROBE.read_text(encoding="utf-8"), filename=str(PROBE))
    forbidden_calls = {
        "PackageGraphSnapshot",
        "PackageGraphPackage",
        "PackageGraphModule",
        "PackageGraphField",
        "PackageGraphExpressionLineage",
    }
    assert not {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in forbidden_calls
    }
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sorted"
        for node in ast.walk(tree)
    )


def test_slice11_spec_lifecycle_and_non_goals_are_exact() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "one common expectation",
        "PYTHONHASHSEED = 0, 1, 7, 4294967295",
        "Python 3.12 and Python 3.13",
        "repository and project relocation",
        "isolated installed wheel",
        "runtime refs remain intentionally unequal",
        "Project Explain v1 and CLI remain zero-delta",
        "generated/golden delta is 0 / 0",
        "Slice 11 current",
        "Slice 12 next/unstarted",
        "Phase 59 completion -> validation/test performance optimization interlude -> Phase 60 activation",
        "Add Phase 59 differential compatibility assurance",
    ):
        assert required in normalized
