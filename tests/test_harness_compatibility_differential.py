from __future__ import annotations

import ast
from pathlib import Path
import sys
from typing import cast


import _pietto_project_graph_differential as probe
import _pietto_project_explain_runtime as runtime_fixture
import _pietto_project_package_lineage_e2e as slice10


from _pietto_project_graph_cases import (
    REPO_ROOT,
    PROBE,
    SPEC,
    SEEDS,
    SUPPORTED_INTERPRETERS,
    EXPECTED_COMMON_MANIFEST,
    _canonical_bytes,
    _fields,
    _positions,
    _common_manifest,
    differential_matrix as differential_matrix,
)


# One shared expectation is consumed unchanged by every Python version, seed,
# project/source relocation, repeated construction, and installed-wheel run.


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
