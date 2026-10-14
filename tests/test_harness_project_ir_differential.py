from __future__ import annotations

import ast
from pathlib import Path
import sys
from typing import cast


import _pietto_ir_project_differential as probe
import _pietto_ir_sources as slice10


from _pietto_ir_differential import (
    REPO_ROOT,
    PROBE,
    SPEC,
    SEEDS,
    SUPPORTED_INTERPRETERS,
    EXPECTED_COMMON_MANIFEST,
    _decoded,
    _canonical_bytes,
    _common_manifest,
    differential_matrix as differential_matrix,
)


# Filled once from one reviewed source observation. Every matrix member is
# checked against this unchanged manifest; no environment-local oracle exists.


def test_every_environment_matches_one_reviewed_common_manifest(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    assert EXPECTED_COMMON_MANIFEST
    assert all(
        _common_manifest(document) == EXPECTED_COMMON_MANIFEST
        for document in observations.values()
    )


def test_four_hash_seeds_preserve_exact_observation_and_inspection_bytes(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = _decoded(observations["seed:0"])
    canonical = _canonical_bytes(baseline, "project")
    assert SEEDS == ("0", "1", "7", "4294967295")
    for seed in SEEDS:
        document = observations[f"seed:{seed}"]
        assert document == observations["seed:0"]
        assert _canonical_bytes(_decoded(document), "project") == canonical


def test_all_available_supported_interpreters_and_combined_cases_match(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert sys.version_info[:2] in SUPPORTED_INTERPRETERS
    assert sys.version_info[:2] in interpreters
    for interpreter_version in interpreters:
        key = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        assert observations[key] == observations["seed:0"]
        seed = "1" if interpreter_version == (3, 12) else "4294967295"
        combined = (
            f"combined:python{interpreter_version[0]}.{interpreter_version[1]}:"
            f"seed{seed}:relocated"
        )
        assert observations[combined] == observations["seed:0"]


def test_relocation_creation_order_cwd_ambient_and_operation_order_do_not_leak(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    for key in ("project-relocated", "source-relocated"):
        assert observations[key] == observations["seed:0"]
    document = observations["seed:0"]
    for forbidden in (
        str(REPO_ROOT).encode(),
        b"normal-created",
        b"reverse-created",
        b"project-relocated",
        b"source-relocated",
        b"PIETTO_SLICE11_IRRELEVANT",
        b"0x",
    ):
        assert forbidden not in document


def test_isolated_installed_wheel_matches_and_proves_import_origin(
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


def test_common_observation_retains_project_ir_identity_and_semantic_laws(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = _decoded(observations["seed:0"])
    project = cast(dict[str, object], observation["project"])
    assert observation["runtime_identities_distinct"] is True
    relations = cast(list[list[object]], project["relations"])
    assert [cast(list[object], item[0])[-1] for item in relations] == [
        "rows",
        "projected",
        "final",
        "consumer",
        "second",
        "aggregate_only",
        "full",
        "broken",
        "other",
        "other_result",
    ]
    assert [item[1] for item in relations] == ["concrete"] * 7 + [
        "unknown",
        "concrete",
        "concrete",
    ]
    operators = cast(list[list[object]], project["operators"])
    full = next(item for item in operators if item[5] == "full")
    assert full[-1] == [
        "relation_input",
        "row_filter",
        "group_aggregate",
        "result_filter",
        "window_evaluation",
        "final_projection",
        "relation_ordering",
        "limit",
    ]
    uses = cast(list[list[object]], project["uses"])
    assert all(len(item) == 6 for item in uses)
    assert {item[3] for item in uses} == {
        "ProjectIROperatorFlowUseOccurrence",
        "ProjectIRUseOccurrence",
    }
    assert {item[5] for item in uses if item[4] == "relation_input"} == {0}
    edges = cast(list[list[object]], project["cross_edges"])
    assert all(item[4] == "satisfied" for item in edges)
    assert any(item[-1] == 2 for item in edges)
    properties_ = cast(list[list[object]], project["provided_properties"])
    assert any(
        item[1:4] == ["multiplicity", "ProjectIRProvidedBagMultiplicity", "bag"]
        for item in properties_
    )
    assert any(item[1] == "free_bindings" and item[3] == [] for item in properties_)
    aggregate = cast(list[list[object]], project["aggregate_contexts"])
    global_context = next(item for item in aggregate if item[0] == "aggregate_only")
    assert global_context[3] == 0
    assert global_context[4] == 0
    grouped_context = next(item for item in aggregate if item[0] == "full")
    assert grouped_context[3:5] == [1, 1]
    window_results = cast(list[list[object]], project["window_result_contexts"])
    assert window_results and window_results[0][-1] == [
        "unknown",
        "unknown",
        "unknown",
        "unknown",
    ]
    assert project["verification"] == ["verified", []]
    assert project["queries"] == [
        ["a.pietto", "full", 1, []],
        ["a.pietto", "broken", 1, ["unknown"]],
    ]
    base_bytes = _canonical_bytes(observation, "project")
    shifted_bytes = _canonical_bytes(observation, "shifted")
    assert base_bytes != shifted_bytes
    assert cast(dict[str, object], observation["shifted"])["first_node"] == 7


def test_real_semantic_non_concrete_and_cycle_blocking_are_differentially_exact(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    cycle = cast(dict[str, object], _decoded(observations["seed:0"])["cycle"])
    assert cycle["non_concrete"] == [
        ["a", "blocked", "ProjectModuleRelationSemanticFacts", 0, 0, 1],
        ["b", "blocked", "ProjectModuleRelationSemanticFacts", 0, 0, 1],
    ]
    assert cycle["concrete"] == ["rows", "okay"]
    assert cycle["verification"] == ["verified", []]
    assert _canonical_bytes(_decoded(observations["seed:0"]), "cycle").startswith(
        b"header\tformat=e:pietto.project-ir-inspection.v1"
    )


def test_invalid_verifier_and_pure_rejections_use_typed_normalized_outcomes(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = _decoded(observations["seed:0"])
    assert observation["invalid_verification"] == {
        "status": "invalid",
        "issues": [
            ["evaluation_context", None, None],
            ["evaluation_context", "ProjectIRPlanNodeRef", 14],
        ],
    }
    assert observation["pure_rejections"] == [
        ["wrong_format", "unknown_format_marker", 0, 0],
        ["non_dense_ref", "non_dense_ref_coordinates", 0, None],
        ["wrong_domain_ref", "ref_domain_mismatch", 34, None],
        ["dangling_ref", "dangling_ref", 34, None],
        ["section_order", "section_order_violation", None, None],
        ["invalid_use_endpoint", "invalid_endpoint_relation", 90, None],
    ]


def test_probe_reuses_slice10_corpus_and_optimized_differential_infrastructure() -> (
    None
):
    slice10_files = slice10._project_files()
    probe_files = dict(probe.PROJECT_FILE_ITEMS)
    assert probe_files["b.pietto"] == slice10_files["b.pietto"]
    assert probe_files["c.pietto"] == slice10_files["c.pietto"]
    assert probe_files["d.pietto"] == slice10_files["d.pietto"]
    assert "query aggregate_only:" in probe_files["a.pietto"]
    assert (
        probe_files["a.pietto"].replace(
            "query aggregate_only:\n"
            "    from Input\n"
            "    select:\n"
            "        total = sum(amount)\n",
            "",
        )
        == slice10_files["a.pietto"]
    )

    tree = ast.parse(PROBE.read_text(encoding="utf-8"), filename=str(PROBE))
    forbidden_calls = {
        "ProjectModuleSemanticFactSet",
        "ProjectModuleAttributionFactSet",
        "ProjectModuleRelationSemanticFacts",
        "ProjectIRProjectPlan",
        "ProjectIRPureDocument",
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
    assert source.count("build_project_ir_pipeline(") == 2
    assert "check_project_parse_only(" in source
    assert "build_empty_project_semantic_result(" in source
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


def test_slice11_spec_lifecycle_zero_delta_and_handoff_are_exact() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "one reviewed common observation",
        "PYTHONHASHSEED = 0, 1, 7, 4294967295",
        "Python 3.12 and Python 3.13",
        "normal and reverse file-creation order",
        "source checkout, relocated source, and isolated installed wheel",
        "typed INVALID issue family and coordinate",
        "normalized pure-boundary rejection status and coordinates",
        "production delta = 0",
        "serial and xdist --dist=loadfile",
        "Add Phase 61 differential compatibility assurance",
        "Phase 61 Slice 12 — Completion Audit And Phase 62 Handoff",
    ):
        assert required in normalized
