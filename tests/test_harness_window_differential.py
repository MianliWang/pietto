from __future__ import annotations

import ast
from pathlib import Path
import sys
from typing import cast


import _pietto_ir_window_differential as probe
import _pietto_sql_window_cases as slice11


from _pietto_sql_window_differential import (
    REPO_ROOT,
    PROBE,
    SPEC,
    SEEDS,
    SUPPORTED_INTERPRETERS,
    EXPECTED_COMMON_MANIFEST,
    _decoded,
    _common_manifest,
    differential_matrix as differential_matrix,
)


# Filled from one reviewed predecessor observation; every matrix member must
# consume this unchanged rather than regenerating an environment-local oracle.


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
