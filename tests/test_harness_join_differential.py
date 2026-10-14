from __future__ import annotations

import ast
from pathlib import Path
import sys
from typing import cast


import _pietto_ir_join_differential as probe
from pietto._project import project_bag_null_oracle as oracle

from _pietto_project_join_differential import (
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
    _baseline_key,
)


# Frozen from one reviewed source-checkout observation. Full observation and
# canonical bytes are compared directly; these digests are review aids only.


def test_every_environment_matches_one_reviewed_common_manifest(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    assert EXPECTED_COMMON_MANIFEST
    assert all(
        _common_manifest(document) == EXPECTED_COMMON_MANIFEST
        for document in observations.values()
    )


def test_all_supported_interpreters_seeds_relocation_and_bytes_match_exactly(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert SEEDS == ("0", "1", "7", "4294967295")
    assert SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert sys.version_info[:2] in SUPPORTED_INTERPRETERS
    assert sys.version_info[:2] in interpreters
    baseline = observations[_baseline_key()]
    decoded = _decoded(baseline)
    primary_bytes = _canonical_bytes(decoded, "primary")
    primary_records = cast(dict[str, object], decoded["primary"])["portable_records"]
    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        for seed in SEEDS:
            document = observations[f"source:{label}:seed:{seed}"]
            assert document == baseline
            observation = _decoded(document)
            assert _canonical_bytes(observation, "primary") == primary_bytes
            assert (
                cast(dict[str, object], observation["primary"])["portable_records"]
                == primary_records
            )
        assert observations[f"relocated:{label}:seed:7"] == baseline
        assert observations[f"installed:{label}:seed:7"] == baseline


def test_relocation_cwd_ambient_creation_and_operation_order_do_not_leak(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = observations[_baseline_key()]
    for forbidden in (
        str(REPO_ROOT).encode(),
        b"primary-normal",
        b"primary-reverse",
        b"source-relocated",
        b"installed-wheel",
        probe.SEED_ENVIRONMENT.encode(),
        b".venv",
        b"0x",
    ):
        assert forbidden not in baseline
    observation = _decoded(baseline)
    assert observation["runtime_identities_distinct"] is True
    shifted = cast(dict[str, object], observation["shifted"])
    assert shifted["starting_coordinates"] == [7, 11, 5, 5]
    assert shifted["first_coordinates"] == [7, 11, 5, 5]
    assert (
        shifted["semantic"]
        == cast(dict[str, object], observation["primary"])["semantic"]
    )
    assert _canonical_bytes(observation, "shifted") != _canonical_bytes(
        observation, "primary"
    )


def test_installed_wheel_origin_is_inside_target_and_outside_checkout(
    differential_matrix: dict[str, object],
) -> None:
    origins = cast(
        dict[tuple[int, int], Path], differential_matrix["installed_origins"]
    )
    source_root = cast(Path, differential_matrix["installed_source_root"])
    empty_cache = cast(Path, differential_matrix["empty_install_cache"])
    assert empty_cache.is_dir()
    assert tuple(empty_cache.iterdir())
    assert all(
        origin.is_relative_to(source_root / "src") for origin in origins.values()
    )
    assert all(not origin.is_relative_to(REPO_ROOT) for origin in origins.values())


def test_real_authored_continuity_and_required_metamorphics_are_exact(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = _decoded(observations[_baseline_key()])
    primary = cast(dict[str, object], observation["primary"])
    relations = cast(list[list[object]], primary["relations"])
    assert any(
        cast(list[object], item[0])[0] == "z_disconnected.pietto"
        and cast(list[object], item[0])[-1] == "audit_result"
        for item in relations
    )
    assert primary["verification"] == ["verified", [], "verified"]
    assert cast(int, cast(list[object], primary["analysis_products"])[0]) > 0
    assert cast(list[object], primary["inspection_counts"])[0:5] == [
        16,
        32,
        16,
        17,
        32,
    ]
    metamorphic = cast(dict[str, object], observation["metamorphic"])
    direct = cast(list[object], metamorphic["direct_vs_explicit"])
    direct_effect = cast(list[object], direct[0])
    explicit_effect = cast(list[object], direct[1])
    assert direct_effect[1:10] == explicit_effect[1:10]
    assert direct[2:] == [True, True, True]

    parallel = cast(list[object], metamorphic["parallel"])
    assert cast(list[object], parallel[0])[2] == "concrete"
    assert cast(list[object], parallel[1])[2:4] == [
        "ambiguous",
        ["direct_relationship_ambiguous"],
    ]
    assert cast(list[object], parallel[2])[2] == "concrete"
    assert parallel[3:] == [
        2,
        ["customer_returns_coarse", "customer_returns_coarse_parallel"],
    ]

    unique = cast(list[list[object]], metamorphic["unique_transition"])
    assert [unique[0][2], unique[1][2]] == ["at_most_one", "unbounded_by_one"]
    assert [unique[0][4], unique[1][4]] == [
        "preserves_source_multiplicity",
        "may_multiply",
    ]
    assert [unique[0][10], unique[1][10]] == [["strict"], []]
    assert [unique[0][11], unique[1][11]] == [4, 3]
    assert unique[0][12] == unique[1][12]

    inner, left = cast(list[list[object]], metamorphic["inner_vs_left"])
    assert [inner[3], left[3]] == ["inner", "left"]
    assert [inner[5], left[5]] == [
        "may_drop_left_rows",
        "guarantees_left_survival",
    ]
    assert [inner[6], left[6]] == [
        "no_new_null_extension",
        "may_null_extend_right",
    ]
    assert [inner[7], left[7]] == ["not_applicable", "present"]
    assert [inner[9], left[9]] == [
        "ProjectIRJoinUnavailableProperty",
        "ProjectIRProvidedNullExtension",
    ]
    assert left[8] == ["nullable", "nullable", "nullable"]
    assert left[10] == ["strict", "lax"]
    assert any(
        cast(list[object], factor)[-1] for factor in cast(list[object], left[12])
    )

    assert metamorphic["multi_hop"] == [2, [0, 1], True]
    assert metamorphic["branching"] == [True, True, [0, 0]]
    role = cast(list[object], metamorphic["role_playing"])
    assert role[0] == [0, 1]
    assert cast(list[object], role[1])[0] != cast(list[object], role[1])[1]
    locality_uses = cast(list[object], role[2])
    assert locality_uses[:2] == locality_uses[2:]
    assert locality_uses[0] != locality_uses[1]
    self_uses = cast(list[object], role[4])
    assert self_uses[:2] == self_uses[2:]
    assert self_uses[0] != self_uses[1]
    assert cast(list[object], metamorphic["fanout"])[4] == "may_multiply"
    assert cast(list[object], metamorphic["chasm"])[0] == 1
    chasm_alignment = cast(
        list[list[object]], cast(list[object], metamorphic["chasm"])[1]
    )
    assert chasm_alignment == [
        [
            "reaggregation_required",
            ["fanout_risk", "cross_fact_multiplication"],
            ["aggregate_algebra_required"],
        ]
    ]


def test_negative_states_and_pure_rejections_are_typed_and_stable(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = _decoded(observations[_baseline_key()])
    primary = cast(dict[str, object], observation["primary"])
    queries = cast(list[list[object]], primary["queries"])
    by_owner = {item[0]: cast(list[object], item[1]) for item in queries}
    assert cast(list[object], by_owner["ambiguous_fact_join"][1])[2:4] == [
        "ambiguous",
        ["direct_relationship_ambiguous"],
    ]
    assert cast(list[object], by_owner["bad_relationship_join"][1])[2:4] == [
        "unknown",
        ["unknown_relationship"],
    ]
    assert cast(list[object], by_owner["bad_role_join"][1])[2:4] == [
        "unknown",
        ["unknown_endpoint_direction"],
    ]
    assert primary["non_concrete"] == [4, 4, 4]
    subjects = cast(list[list[object]], primary["non_concrete_multifact"])
    assert [item[1] for item in subjects] == [
        "ambiguous_path",
        "insufficient_evidence",
        "insufficient_evidence",
        "insufficient_evidence",
    ]
    assert all(
        cast(list[object], item[4])[0] == cast(list[object], item[4])[1]
        for item in subjects
    )
    assert [cast(list[list[object]], item[2])[0][2] for item in subjects] == [
        ["direct_relationship_ambiguous"],
        ["direct_relationship_absent"],
        ["unknown_relationship"],
        ["unknown_endpoint_direction"],
    ]
    query_closure = cast(list[object], primary["query_closure"])
    assert len(cast(list[object], query_closure[0])) == 39
    assert query_closure[1] == [[1, 1]]
    assert cast(list[object], query_closure[2]) == [1] * 90
    assert observation["pure_rejections"] == [
        ["unknown_format", "unknown_format", None, None],
        ["section_order", "invalid_section_order", None, None],
        ["dangling_ref", "dangling_ref", 171, 1],
    ]


def _row(*values: oracle.ProjectBagNullScalar) -> oracle.ProjectBagNullRow:
    return oracle.ProjectBagNullRow(values=values)


def _bag(
    *entries: tuple[oracle.ProjectBagNullRow, int],
) -> oracle.ProjectFiniteBag:
    return oracle.ProjectFiniteBag(
        entries=tuple(
            oracle.ProjectBagNullEntry(row=row, multiplicity=multiplicity)
            for row, multiplicity in entries
        )
    )


def _specification(
    kind: oracle.ProjectBagNullJoinKind,
    left_width: int,
    right_width: int,
    *pairs: tuple[int, int],
) -> oracle.ProjectBagNullJoinSpecification:
    return oracle.ProjectBagNullJoinSpecification(
        kind=kind,
        left_width=left_width,
        right_width=right_width,
        correspondences=tuple(
            oracle.ProjectBagNullEqualityCorrespondence(
                left_position=left,
                right_position=right,
            )
            for left, right in pairs
        ),
    )


def _contents(bag: oracle.ProjectFiniteBag) -> dict[oracle.ProjectBagNullRow, int]:
    return {item.row: item.multiplicity for item in bag.entries}


def test_bag_null_oracle_witnesses_fanout_left_null_and_composite_equality() -> None:
    one = oracle.project_bag_int(1)
    two = oracle.project_bag_int(2)
    null = oracle.project_bag_null()
    left = _bag((_row(one), 2))
    right_rows = (
        (_row(one, oracle.project_bag_text("first")), 1),
        (_row(one, oracle.project_bag_text("second")), 1),
    )
    inner = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 1, 2, (0, 0)),
        left,
        _bag(*right_rows),
    )
    assert _contents(inner) == {
        _row(one, one, oracle.project_bag_text("first")): 2,
        _row(one, one, oracle.project_bag_text("second")): 2,
    }
    reversed_inner = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 1, 2, (0, 0)),
        left,
        _bag(*reversed(right_rows)),
    )
    assert _contents(reversed_inner) == _contents(inner)
    scaled_right = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 1, 2, (0, 0)),
        _bag((_row(one), 1)),
        _bag(*((row, multiplicity * 3) for row, multiplicity in right_rows)),
    )
    assert _contents(scaled_right) == {
        row: multiplicity * 3
        for row, multiplicity in _contents(
            oracle.evaluate_project_bag_null_join(
                _specification(
                    oracle.ProjectBagNullJoinKind.INNER,
                    1,
                    2,
                    (0, 0),
                ),
                _bag((_row(one), 1)),
                _bag(*right_rows),
            )
        ).items()
    }

    unknown_left = _bag((_row(null), 3))
    right = _bag((_row(one), 1))
    inner_unknown = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 1, 1, (0, 0)),
        unknown_left,
        right,
    )
    left_unknown = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.LEFT, 1, 1, (0, 0)),
        unknown_left,
        right,
    )
    assert inner_unknown.entries == ()
    assert _contents(left_unknown) == {_row(null, null): 3}
    swapped_left = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.LEFT, 1, 1, (0, 0)),
        right,
        unknown_left,
    )
    assert _contents(swapped_left) != _contents(left_unknown)

    composite = _specification(
        oracle.ProjectBagNullJoinKind.INNER,
        2,
        2,
        (0, 0),
        (1, 1),
    )
    assert (
        oracle.evaluate_project_bag_null_join(
            composite,
            _bag((_row(one, null), 1)),
            _bag((_row(one, two), 1)),
        ).entries
        == ()
    )


def test_bag_null_oracle_chasm_and_dependent_chain_witnesses_are_distinct() -> None:
    customer = _bag((_row(oracle.project_bag_int(1)), 1))
    orders = _bag(
        (_row(oracle.project_bag_int(1), oracle.project_bag_int(10)), 1),
        (_row(oracle.project_bag_int(1), oracle.project_bag_int(11)), 1),
    )
    customer_orders = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 1, 2, (0, 0)),
        customer,
        orders,
    )
    returns = _bag(
        (_row(oracle.project_bag_int(1), oracle.project_bag_int(20)), 1),
        (_row(oracle.project_bag_int(1), oracle.project_bag_int(21)), 1),
        (_row(oracle.project_bag_int(1), oracle.project_bag_int(22)), 1),
    )
    chasm = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 3, 2, (0, 0)),
        customer_orders,
        returns,
    )
    assert sum(_contents(chasm).values()) == 2 * 3 == 6

    items = _bag(
        (_row(oracle.project_bag_int(10), oracle.project_bag_text("a")), 1),
        (_row(oracle.project_bag_int(10), oracle.project_bag_text("b")), 1),
        (_row(oracle.project_bag_int(11), oracle.project_bag_text("c")), 1),
    )
    dependent = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 3, 2, (2, 0)),
        customer_orders,
        items,
    )
    assert sum(_contents(dependent).values()) == 3
    assert sum(_contents(dependent).values()) != 2 * 3
    swapped = oracle.evaluate_project_bag_null_join(
        _specification(oracle.ProjectBagNullJoinKind.INNER, 2, 3, (0, 2)),
        items,
        customer_orders,
    )
    permuted = {
        _row(*row.values[2:], *row.values[:2]): multiplicity
        for row, multiplicity in _contents(swapped).items()
    }
    assert permuted == _contents(dependent)


def test_probe_and_outer_harness_preserve_frozen_assurance_boundaries() -> None:
    source = PROBE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PROBE))
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    forbidden_constructors = {
        "ProjectMultiFactAnalysis",
        "ProjectPhase62VerificationResult",
        "ProjectPhase62AnalysisBundle",
        "ProjectPhase62Inspection",
        "ProjectPhase62PureDocument",
        "ProjectIRBinaryJoinOccurrence",
        "ProjectConcreteJoinUse",
        "ProjectAggregateFactOccurrence",
        "sorted",
    }
    assert forbidden_constructors.isdisjoint(called)
    for required in (
        "check_project_parse_only(",
        "build_empty_project_semantic_result(",
        "build_project_row_keys(",
        "build_project_value_fds(",
        "build_project_ir_project_plan(",
        "build_project_ir_evaluation_context_stage(",
        "build_project_ir_relational_property_stage(",
        "build_project_relationships(",
        "build_project_relationship_conditions(",
        "build_project_relationship_match_guarantees(",
        "build_project_relationship_uses(",
        "build_project_ir_join_region(",
        "build_project_multifact_analysis(",
        "verify_project_phase62(",
        "build_project_phase62_analysis_bundle(",
        "build_project_phase62_inspection(",
    ):
        assert source.count(required) == 1
    assert "PRIMARY_MAIN_SOURCE" in source
    assert "DISCONNECTED_SOURCE" in source
    assert "subprocess.run(" not in source
    assert "sort_keys=False" in source
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "lru_cache",
        "functools.cache",
        "shelve",
        "pickle",
        ".venv/bin/python",
        "repr(",
        "id(",
    ):
        assert forbidden not in source


def test_slice15_spec_lifecycle_zero_delta_and_handoff_are_exact() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "real authored Project",
        "EXPECTED_COMMON_MANIFEST",
        "PYTHONHASHSEED = 0, 1, 7, 4294967295",
        "Python 3.12 and Python 3.13",
        "normal and reverse authored file-creation order",
        "relocated source",
        "isolated installed wheel",
        "direct shorthand versus explicit VIA",
        "parallel relationship ambiguity",
        "AT_MOST_ONE -> UNBOUNDED_BY_ONE",
        "INNER versus LEFT",
        "Customer -> 2 Orders -> independently 3 Returns",
        "production delta = 0",
        "A3/M6/D0",
        "Add Phase 62 JOIN end-to-end assurance",
        "Phase 62 Slice 16 = NEXT / NOT IMPLEMENTED",
    ):
        assert required in normalized
