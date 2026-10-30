from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, cast

import pytest


import _pietto_ir_join_differential as probe
from pietto._project import project_bag_null_oracle as oracle

from _pietto_project_join_differential import (
    REPO_ROOT,
    SEEDS,
    SUPPORTED_INTERPRETERS,
    EXPECTED_COMMON_MANIFEST_SHA256,
    _decoded,
    _digest,
    _canonical_bytes,
    _common_manifest,
    differential_matrix as differential_matrix,
    _baseline_key,
)


# Full observations and canonical bytes remain the comparison authority;
# a current common manifest is accepted only after its separate review.


def test_every_environment_matches_one_reviewed_common_manifest(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    actual = {key: _common_manifest(document) for key, document in observations.items()}
    if EXPECTED_COMMON_MANIFEST_SHA256 is None:
        print(json.dumps(actual, ensure_ascii=False, allow_nan=False, indent=2))
    assert EXPECTED_COMMON_MANIFEST_SHA256 is not None, (
        "Current v2 manifest review is pending; complete actual manifests are printed above."
    )
    for key, manifest in actual.items():
        assert _digest(manifest) == EXPECTED_COMMON_MANIFEST_SHA256, (
            f"Common manifest differs in {key}:\n"
            + json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2)
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
    expected_keys = []
    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        expected_keys.extend(f"source:{label}:seed:{seed}" for seed in SEEDS)
    for placement in ("relocated", "installed"):
        for interpreter_version in interpreters:
            label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
            expected_keys.append(f"{placement}:{label}:seed:7")
    assert list(observations) == expected_keys
    for document in observations.values():
        assert document == baseline
        observed = _decoded(document)
        for variant in ("primary", "parallel", "no_unique"):
            assert _canonical_bytes(observed, variant) == _canonical_bytes(
                decoded, variant
            )
            assert (
                cast(dict[str, object], observed[variant])["portable_records"]
                == cast(dict[str, object], decoded[variant])["portable_records"]
            )
        assert (
            cast(dict[str, object], observed["shifted"])["canonical_bytes"]
            == cast(dict[str, object], decoded["shifted"])["canonical_bytes"]
        )
        assert (
            cast(dict[str, object], observed["shifted"])["normal_canonical_bytes"]
            == cast(dict[str, object], decoded["shifted"])["normal_canonical_bytes"]
        )


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
    assert observation["observation_format"] == "pietto.join-differential.v2"
    assert observation["runtime_identities_distinct"] is True
    shifted = cast(dict[str, object], observation["shifted"])
    assert shifted["kind"] == "base_plan_allocation"
    assert shifted["starting_coordinates"] == [7, 11, 5, 5]
    assert shifted["normal_first_coordinates"] == [0, 0, 0, 0]
    assert shifted["first_coordinates"] == [7, 11, 5, 5]
    assert shifted["independent_scopes"] is True
    assert shifted["verification"] == ["verified", "verified"]
    assert shifted["normal_canonical_bytes"] != shifted["canonical_bytes"]
    assert shifted["normal_semantic"] == shifted["semantic"]
    assert shifted["semantic"]


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


def _by_owner(entries: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    indexed = {cast(list[str], entry["owner"])[1]: entry for entry in entries}
    assert len(indexed) == len(entries)
    return indexed


def _relational(properties: dict[str, object]) -> None:
    fields = cast(list[list[object]], properties["fields"])
    classes = cast(list[list[int]], properties["classes"])
    assert fields and classes
    assert [field[0] for field in fields] == list(range(len(fields)))
    members = [position for value in classes for position in value]
    assert all(classes)
    assert len(members) == len(fields)
    assert set(members) == set(range(len(fields)))
    for determinants, strength, supports in cast(
        list[list[object]], properties["keys"]
    ):
        assert determinants and supports and strength in {"strict", "lax"}
        assert all(0 <= index < len(classes) for index in cast(list[int], determinants))
    for determinants, dependents, strength, supports in cast(
        list[list[object]], properties["fds"]
    ):
        assert determinants and dependents and supports
        assert strength in {"strict", "lax"}
        assert not set(cast(list[int], determinants)) & set(cast(list[int], dependents))
        assert all(
            0 <= index < len(classes)
            for index in [*cast(list[int], determinants), *cast(list[int], dependents)]
        )
    grain = cast(dict[str, object], properties["grain"])
    assert grain["state"] in {"factorized", "global", "unknown", "conflict"}
    factors = cast(list[object], grain["factors"])
    assert all(value in factors for value in cast(list[object], grain["active"]))
    for determinants, dependents in cast(
        list[list[list[object]]], grain["dependencies"]
    ):
        assert all(value in factors for value in [*determinants, *dependents])


def _joins(region: dict[str, object]) -> list[dict[str, object]]:
    joins = cast(list[dict[str, object]], region["joins"])
    assert joins
    introductions = cast(list[int], region["binding_introductions"])
    assert introductions and len(introductions) == len(set(introductions))
    for index, join in enumerate(joins):
        assert join["position"] == index
        inputs = cast(list[list[object]], join["inputs"])
        assert len(inputs) == 2
        assert inputs[0][0] != inputs[1][0] and inputs[0][2] != inputs[1][2]
        left = cast(dict[str, object], join["left"])
        right = cast(dict[str, object], join["right"])
        output = cast(dict[str, object], join["output"])
        assert [inputs[0][1], inputs[1][1]] == [left["output"], right["output"]]
        if index:
            assert (
                left["output"]
                == cast(dict[str, object], joins[index - 1]["output"])["output"]
            )
        for properties in (left, right, output):
            _relational(properties)
        fields = cast(list[list[object]], output["fields"])
        field_inputs = cast(list[list[object]], join["field_inputs"])
        nulling = cast(list[list[object]], join["nulling"])
        assert len(fields) == len(field_inputs) == len(nulling)
        assert len(fields) == len(cast(list[object], left["fields"])) + len(
            cast(list[object], right["fields"])
        )
        assert [field[1] for field in fields] == [field[2] for field in field_inputs]
        assert all(field[0] in introductions for field in nulling)
        condition = cast(dict[str, object], join["condition"])
        assert condition["owner"] == region["owner"]
        assert condition["join_position"] == join["position"]
        assert condition["ready"] is True and not condition["diagnostics"]
        conjuncts = cast(list[list[object]], condition["conjuncts"])
        references = cast(list[list[object]], condition["references"])
        assert conjuncts and references
        assert [item[0] for item in conjuncts] == list(range(len(conjuncts)))
        assert [item[0] for item in references] == list(range(len(references)))
        assert all(
            position in [reference[0] for reference in references]
            for conjunct in conjuncts
            for position in cast(list[int], conjunct[3])
        )
        equalities = cast(list[list[object]], condition["equalities"])

        def field_read(operand: object) -> bool:
            return any(
                reference[4] == operand
                and reference[1] == "resolved"
                and len(cast(list[object], reference[3])) == 1
                for reference in references
            )

        # Every `==` of two exact field reads, hand-written or in a call's body.
        proved = [
            item
            for item in conjuncts
            if item[1] == "ComparisonExpr"
            and cast(dict[str, object], item[2])["operator"] == "=="
            and field_read(cast(dict[str, object], item[2])["left"])
            and field_read(cast(dict[str, object], item[2])["right"])
        ]
        assert [item[0] for item in equalities] == [item[0] for item in proved]
        assert [item[3] for item in equalities] == [item[4] for item in proved]
        if not proved:
            assert condition["key_matches"] == []
        for equality in equalities:
            for field in equality[1:3]:
                assert cast(list[object], field)[0] in cast(
                    list[object], condition["bindings"]
                )
        for proof in cast(list[list[object]], condition["key_matches"]):
            assert proof[0] in cast(list[object], condition["bindings"])
            assert proof[2] and proof[3] in {"strict", "lax"}
            assert proof[4:6] == ["zero_allowed", "at_most_one"]
            assert proof[6]
            assert all(
                position in [item[0] for item in equalities]
                for position in cast(list[int], proof[6])
            )
        rejections = cast(list[list[object]], condition["null_rejections"])
        assert rejections
        for rejection in rejections:
            conjunct = conjuncts[cast(int, rejection[0])]
            reference = references[cast(int, rejection[1])]
            assert reference[0] in cast(list[int], conjunct[3])
            assert rejection[2] in cast(list[object], reference[3])
            assert rejection[3] == "strict_comparison_operand"
        if join["kind"] == "left":
            right_start = len(cast(list[object], left["fields"]))
            assert all(field[2] == "nullable" for field in fields[right_start:])
            assert all(
                join["node"] in cast(list[object], field[1])
                for field in nulling[right_start:]
            )
    return joins


def test_real_authored_continuity_and_required_metamorphics_are_exact(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = _decoded(observations[_baseline_key()])
    primary = cast(dict[str, object], observation["primary"])
    assert primary["verification"] == ["verified", []]
    owners = _by_owner(cast(list[dict[str, object]], primary["owners"]))
    assert owners["audit_result"]["owner"] == ["z_disconnected.pietto", "audit_result"]
    assert "properties" in owners["audit_result"]
    schedule = cast(list[list[str]], primary["schedule"])
    assert len(schedule) == len(owners)
    assert {tuple(owner) for owner in schedule} == {
        tuple(cast(list[str], entry["owner"])) for entry in owners.values()
    }
    for consumer, producer, ordinal, evidence in cast(
        list[list[object]], primary["dependencies"]
    ):
        assert schedule.index(cast(list[str], producer)) < schedule.index(
            cast(list[str], consumer)
        )
        assert type(ordinal) is int and ordinal >= 0 and evidence
    regions = _by_owner(cast(list[dict[str, object]], primary["regions"]))
    joins = {name: _joins(region) for name, region in regions.items()}
    input_scopes = cast(list[list[object]], primary["input_scopes"])
    scoped = {
        tuple(cast(list[str], item[0])): cast(list[list[object]], item[1])
        for item in input_scopes
    }
    assert len(scoped) == len(input_scopes)
    assert all(
        tuple(cast(list[str], region["owner"])) in scoped for region in regions.values()
    )
    for bindings in scoped.values():
        assert bindings
        assert [cast(list[object], item[0])[0] for item in bindings] == list(
            range(len(bindings))
        )
        for binding in bindings:
            if binding[1] is None:
                assert binding[2]
            else:
                assert len(cast(list[object], binding[2])) == 1
                fields = cast(list[list[object]], binding[3])
                assert fields and [field[0] for field in fields] == list(
                    range(len(fields))
                )
    readiness = cast(list[list[object]], primary["readiness"])
    assert [item[0] for item in readiness] == [
        region["owner"] for region in regions.values()
    ]
    assert all(item[1] for item in readiness)
    metamorphic = cast(dict[str, object], observation["metamorphic"])
    direct = cast(list[object], metamorphic["independent_explicit_joins"])
    assert direct[0] == direct[1] and direct[2:] == [True, True]
    assert (
        joins["direct_unique_join"][0]["condition"]
        != joins["explicit_one_join"][0]["condition"]
    )
    assert (
        cast(list[list[object]], joins["direct_unique_join"][0]["inputs"])[1][0]
        != cast(list[list[object]], joins["explicit_one_join"][0]["inputs"])[1][0]
    )

    parallel = cast(dict[str, object], observation["parallel"])
    change = cast(dict[str, object], metamorphic["parallel_unused_template"])
    template_names = [
        item[2] for item in cast(list[list[object]], primary["templates"])
    ]
    assert template_names == [
        "customer_orders_raw",
        "orders_customer_unique_target",
        "nullable_amounts",
        "composite_raw",
    ]
    assert [item[2] for item in cast(list[list[object]], parallel["templates"])] == [
        *template_names,
        "customer_returns_coarse_parallel",
    ]
    assert change["primary_templates"] == len(template_names)
    assert change["parallel_templates"] == len(template_names) + 1
    assert change["selected_regions_unchanged"] is True
    parallel_conditions = cast(list[dict[str, object]], parallel["conditions"])
    assert all(
        call["template"] != "customer_returns_coarse_parallel"
        for condition in parallel_conditions
        for equality in cast(list[list[object]], condition["equalities"])
        for call in cast(list[dict[str, object]], equality[3])
    )

    unique = cast(list[object], metamorphic["unique_transition"])
    assert unique[0] == [True, False]
    no_unique = cast(dict[str, object], observation["no_unique"])
    removed_regions = _by_owner(cast(list[dict[str, object]], no_unique["regions"]))
    removed = _joins(removed_regions["unique_target_inner"])[0]
    retained = joins["unique_target_inner"][0]
    assert retained["forward_at_most_one"] is True
    assert removed["forward_at_most_one"] is False

    def target_matches(join):
        condition = cast(dict[str, object], join["condition"])
        return [
            proof
            for proof in cast(list[list[object]], condition["key_matches"])
            if cast(list[object], proof[0])[1] == "customer"
        ]

    assert target_matches(retained) and not target_matches(removed)
    assert unique[1:] == [retained["output"], removed["output"]]

    inner, left = joins["explicit_one_join"][0], joins["left_one_join"][0]
    assert [inner["kind"], left["kind"]] == ["inner", "left"]
    inner_fields = cast(
        list[list[object]], cast(dict[str, object], inner["output"])["fields"]
    )
    left_fields = cast(
        list[list[object]], cast(dict[str, object], left["output"])["fields"]
    )
    assert [field[1] for field in inner_fields] == [field[1] for field in left_fields]
    assert inner_fields[0][2] == left_fields[0][2] == "non_null"
    assert any(field[2] == "non_null" for field in inner_fields[1:])
    assert all(field[2] == "nullable" for field in left_fields[1:])
    assert [
        key[:2]
        for key in cast(
            list[list[object]], cast(dict[str, object], left["output"])["keys"]
        )
    ] == [[[1], "lax"]]
    assert left["forward_at_most_one"] is False
    # The hand-written equality matches the declared key of customers only.
    assert [
        (cast(list[object], proof[0])[1], proof[6])
        for proof in cast(
            list[list[object]],
            cast(dict[str, object], left["condition"])["key_matches"],
        )
    ] == [("customers", [0])]
    assert any(
        cast(list[object], factor)[4]
        for factor in cast(
            list[object],
            cast(dict[str, object], cast(dict[str, object], left["output"])["grain"])[
                "factors"
            ],
        )
    )

    assert metamorphic["explicit_chain"] == [2, [0, 1], True]
    assert len(joins["multihop_join"]) == 2
    role = cast(dict[str, object], metamorphic["role_playing"])
    reused = joins["reused_join"]
    reused_inputs = [cast(list[list[object]], join["inputs"])[1] for join in reused]
    assert role["reused_same_producer"] is True
    assert role["reused_right_uses"] == [item[0] for item in reused_inputs]
    assert reused_inputs[0][0] != reused_inputs[1][0]
    assert reused_inputs[0][1] == reused_inputs[1][1]
    assert reused_inputs[0][3] == reused_inputs[1][3]
    self_inputs = cast(list[list[object]], joins["self_fact_join"][0]["inputs"])
    assert role["self_uses"] == [item[0] for item in self_inputs]
    assert self_inputs[0][0] != self_inputs[1][0]
    assert self_inputs[0][1] == self_inputs[1][1]
    assert self_inputs[0][3] == self_inputs[1][3]
    assert joins["fanout_join"][0]["forward_at_most_one"] is False
    chasm = joins["chasm_join"]
    assert len(chasm) == 2 and all(
        join["forward_at_most_one"] is False for join in chasm
    )
    assert [
        cast(list[object], cast(list[list[object]], join["inputs"])[1][3])[-1]
        for join in chasm
    ] == ["orders_by_customer_product", "returns_by_customer_reason"]
    independent = cast(list[list[object]], metamorphic["independent_grouped_inputs"])
    assert len(independent) == len(chasm) and all(
        item[1] is False for item in independent
    )
    for join in chasm:
        right_grain = cast(
            dict[str, object], cast(dict[str, object], join["right"])["grain"]
        )
        assert right_grain["state"] == "factorized" and right_grain["active"]
    coarse_fine = joins["comparable_join"][0]
    assert coarse_fine["forward_at_most_one"] is False
    coarse = cast(dict[str, object], coarse_fine["left"])
    fine = cast(dict[str, object], coarse_fine["right"])
    for properties, expected in (
        (coarse, ["customer_id"]),
        (fine, ["customer_id", "product_id"]),
    ):
        fields = cast(list[list[object]], properties["fields"])
        classes = cast(list[list[int]], properties["classes"])
        keys = cast(list[list[object]], properties["keys"])
        assert any(
            [
                fields[position][1]
                for group in cast(list[int], key[0])
                for position in classes[group]
            ]
            == expected
            and key[1] == "strict"
            for key in keys
        )
    assert len(cast(list[object], metamorphic["coarse_fine_inputs"])) == 1

    nullable, composite = cast(
        list[dict[str, object]], metamorphic["ordered_equalities"]
    )
    for condition, name, pairs in (
        (nullable, "nullable_amounts", [("amount", "amount")]),
        (
            composite,
            "composite_raw",
            [("customer_id", "customer_id"), ("product_id", "reason_id")],
        ),
    ):
        assert condition["ready"] is True and not condition["diagnostics"]
        equalities = cast(list[list[object]], condition["equalities"])
        assert [item[0] for item in equalities] == list(range(len(pairs)))
        assert [
            (cast(list[object], item[1])[2], cast(list[object], item[2])[2])
            for item in equalities
        ] == pairs
        assert all(cast(list[dict[str, object]], item[3]) for item in equalities)
        assert all(
            call["template"] == name
            for item in equalities
            for call in cast(list[dict[str, object]], item[3])
        )
    assert nullable["null_rejections"]
    nullable_output = cast(dict[str, object], joins["nullable_match_join"][0]["output"])
    amounts = [
        field
        for field in cast(list[list[object]], nullable_output["fields"])
        if field[1] == "amount"
    ]
    assert len(amounts) == 2 and all(field[2] == "non_null" for field in amounts)


def test_explicit_output_controls_retain_final_ir_key_proofs_and_left_nulling(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = cast(dict[str, Any], _decoded(observations[_baseline_key()]))
    for variant in ("primary", "parallel", "no_unique"):
        section = observation[variant]
        owners = cast(dict[str, dict[str, Any]], _by_owner(section["owners"]))
        regions = _by_owner(section["regions"])
        records = [
            (kind, {key: value[1] for key, value in fields})
            for kind, fields in section["portable_records"]
        ]
        assert all(
            len(dict(fields)) == len(fields)
            for _, fields in section["portable_records"]
        )
        entries = {
            row["declared_name"]: row for kind, row in records if kind == "owner_entry"
        }
        assert len(entries) == sum(kind == "owner_entry" for kind, _ in records)
        for name in ("direct_unique_join", "explicit_one_join", "left_one_join"):
            plain = [
                row
                for kind, row in records
                if kind == "algebra" and row["owner"] == entries[name]["ref"]
            ]
            assert len(plain) == 1
            # A hand-written ON equality is recorded without a predicate use and
            # matches the declared key of customers, which no_unique removes.
            (predicate,) = [
                row
                for kind, row in records
                if kind == "predicate_join" and row["node"] == plain[0]["node"]
            ]
            assert predicate["expression"] is None and predicate["bindings"] == [0]
            assert len(predicate["matches"] or ()) == (
                0 if variant == "no_unique" else 1
            )
            conditions = [
                row
                for kind, row in records
                if kind == "condition" and row["node"] == plain[0]["node"]
            ]
            assert len(conditions) == 1 and conditions[0]["mode"] == "M3"
            assert json.loads(conditions[0]["expression"])["operator"] == "=="
        for name, kind in (
            ("predicate_key_inner_outputs", "inner"),
            ("predicate_key_left_outputs", "left"),
        ):
            owner = owners[name]
            assert owner["variant"] == "ProjectIRCompletedQueryBlockOutput"
            assert owner["properties"]["fields"] == [
                [0, "order_id", "non_null"],
                [
                    1,
                    "matched_customer_id",
                    "nullable" if kind == "left" else "non_null",
                ],
            ]
            join = cast(dict[str, Any], _joins(regions[name])[0])
            assert join["kind"] == kind
            assert join["forward_at_most_one"] is (variant != "no_unique")
            condition = join["condition"]
            assert len(condition["equalities"]) == 1
            assert [call["template"] for call in condition["equalities"][0][3]] == [
                "orders_customer_unique_target"
            ]
            entry = entries[name]
            assert (
                entry["variant"] == "completed" and entry["active_output"] is not None
            )
            joins = [
                row
                for record_kind, row in records
                if record_kind == "algebra" and row["owner"] == entry["ref"]
            ]
            assert len(joins) == 1 and joins[0]["kind"] == kind
            predicates = [
                row
                for record_kind, row in records
                if record_kind == "predicate_join" and row["node"] == joins[0]["node"]
            ]
            assert len(predicates) == 1
            predicate = predicates[0]
            equalities = [
                row
                for record_kind, row in records
                if record_kind == "predicate_equality"
                and row["node"] == joins[0]["node"]
            ]
            assert len(equalities) == 1 and predicate["equalities"] == [
                equalities[0]["ref"]
            ]
            equality = equalities[0]
            assert [
                equality[key]
                for key in (
                    "position",
                    "left_binding",
                    "left_field",
                    "right_binding",
                    "right_field",
                )
            ] == [0, 0, 1, 1, 0]
            calls = [
                row
                for record_kind, row in records
                if record_kind == "predicate_call" and row["ref"] in equality["calls"]
            ]
            assert len(calls) == len(equality["calls"]) == 1
            assert (
                json.loads(calls[0]["template"])["name"]
                == "orders_customer_unique_target"
            )
            matches = [
                row
                for record_kind, row in records
                if record_kind == "predicate_key_match"
                and row["node"] == joins[0]["node"]
            ]
            if variant == "no_unique":
                assert predicate["matches"] is None and matches == []
                assert (
                    condition["key_matches"] == [] and owner["properties"]["keys"] == []
                )
            else:
                assert len(matches) == 1 and predicate["matches"] == [matches[0]["ref"]]
                match = matches[0]
                assert match["equalities"] == [equality["ref"]]
                assert (match["minimum"], match["maximum"]) == (
                    "zero_allowed",
                    "at_most_one",
                )
                keys = [
                    row
                    for record_kind, row in records
                    if record_kind == "predicate_input_key"
                    and row["ref"] == match["key"]
                ]
                assert len(keys) == 1
                assert [
                    keys[0][key]
                    for key in (
                        "binding",
                        "ordinal",
                        "strength",
                        "class_sizes",
                        "fields",
                    )
                ] == [1, 0, "strict", [1], [0]]
                assert [key[:2] for key in owner["properties"]["keys"]] == [
                    [[0], "strict"]
                ]
            properties = [
                row
                for record_kind, row in records
                if record_kind == "relational_property"
                and row["output"] == joins[0]["output"]
            ]
            assert len(properties) == 1
            fields = [
                row
                for record_kind, row in records
                if record_kind == "row_field" and row["ref"] in properties[0]["fields"]
            ]
            assert len(fields) == len(join["output"]["fields"])
            assert [row["name"] for row in fields] == [
                item[1] for item in join["output"]["fields"]
            ]
            if kind == "left":
                assert fields[-1]["nullability"] == "nullable"
                assert joins[0]["node"] in fields[-1]["nulling_joins"]
            else:
                assert (
                    fields[-1]["nullability"] == "non_null"
                    and fields[-1]["nulling_joins"] is None
                )


def test_negative_states_and_pure_rejections_are_typed_and_stable(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    observation = cast(dict[str, Any], _decoded(observations[_baseline_key()]))
    primary = cast(dict[str, Any], observation["primary"])
    owners = cast(dict[str, dict[str, Any]], _by_owner(primary["owners"]))
    projection_candidates = {
        "unique_target_inner": [("orders", "id"), ("customer", "id")],
        "unique_target_left": [("orders", "id"), ("customer", "id")],
        "fanout_join": [("customers", "id"), ("orders", "id")],
        "aligned_join": [
            ("orders_by_customer", "customer_id"),
            ("copy", "customer_id"),
        ],
        "comparable_join": [
            ("orders_by_customer", "customer_id"),
            ("fine", "customer_id"),
        ],
        "incompatible_join": [
            ("orders_by_customer_product", "customer_id"),
            ("fine_returns", "customer_id"),
        ],
        "self_fact_join": [
            ("orders_by_customer", "customer_id"),
            ("parent", "customer_id"),
        ],
        "global_join": [("global_orders", "total"), ("counted_returns", "total")],
        "ambiguous_fact_join": [
            ("orders_by_customer", "customer_id"),
            ("coarse_returns", "customer_id"),
        ],
    }
    terminal_names = {
        name
        for name, owner in owners.items()
        if owner["variant"] == "ProjectIRQueryBlockTerminal"
    }
    assert terminal_names == {
        *projection_candidates,
        "missing_fact_join",
        "bad_relationship_join",
        "bad_role_join",
        "chasm_aggregate_refusal",
    }
    diagnostics = cast(list[list[object]], primary["diagnostics"])

    def terminal_graph(name):
        terminal = owners[name]
        assert terminal["reason"] == "semantic_output_non_concrete"
        assert terminal["zero_allocation"] is True and terminal["blocker_sites"]
        graph = terminal["semantic_terminal"]
        nodes = graph["nodes"]
        root = nodes[graph["root"]]
        assert root["owner"] == terminal["owner"]
        assert root["variant"] == terminal["blocker_kind"]
        if root["variant"] == "ProjectEffectiveOutputCompletionTerminal":
            assert root["identity"] == root["base_owner"] == terminal["identity"]
            assert (
                owners[name]["owner"]
                == primary["owners"][root["base_entry_site"]]["owner"]
            )
            assert [
                primary["dependencies"][index] for index in root["dependencies"]
            ] == [
                dependency
                for dependency in primary["dependencies"]
                if dependency[0] == terminal["owner"]
            ]
            assert all(
                primary["regions"][index]["owner"] == terminal["owner"]
                for index in root["region_sites"]
            )
            assert all(
                primary["input_scopes"][index][0] == terminal["owner"]
                for index in root["input_scope_sites"]
            )
        sites = terminal["owner_diagnostic_sites"]
        assert sites and all(diagnostics[index][1] == "error" for index in sites)
        return root, nodes

    for name, expected in projection_candidates.items():
        terminal, nodes = terminal_graph(name)
        assert terminal["variant"] == "ProjectEffectiveOutputCompletionTerminal"
        assert terminal["reason"] == "projection_non_concrete"
        qualify = nodes[terminal["joined_qualify"]]
        assert qualify["variant"] == "ProjectConcreteJoinedQualify"
        assert qualify["owner"] == terminal["owner"]
        assert qualify["kind"] == qualify["window_kind"] == "absent"
        assert qualify["window_variant"] == "ProjectConcreteJoinedWindowStage"
        assert qualify["preservation"] == [False, "bag", False]
        assert qualify["diagnostics"] == qualify["window_diagnostics"] == []
        tail = primary["tails"][qualify["aggregation"]]
        assert (
            tail["site"] == qualify["tail_site"] and tail["owner"] == terminal["owner"]
        )
        assert tail["aggregation"] == qualify["aggregation"]
        assert (
            primary["aggregations"][tail["aggregation"]]["owner"] == terminal["owner"]
        )
        blocker = nodes[terminal["blocker"]]
        assert blocker["variant"] == "ProjectNonConcreteJoinedNamespaceExpression"
        assert blocker["owner"] == terminal["owner"]
        assert blocker["reason"] == "reference_resolution_non_concrete"
        assert blocker["expression"]["name"] == expected[0][1]
        assert blocker["blocking_resolutions"] == [0]
        assert len(blocker["resolutions"]) == 1
        resolution = blocker["resolutions"][0]
        assert resolution["status"] == "ambiguous" and resolution["target"] is None
        candidates = resolution["candidates"]
        assert [(item["binding"][1], item["name"]) for item in candidates] == expected
        assert len({item["position"] for item in candidates}) == len(candidates)
        assert len({item["introduction"] for item in candidates}) == len(candidates)
        # The ambiguous read reports itself with its alternatives, as in a
        # single file, instead of the relation's fallback.
        names = [f"{binding}.{field}" for binding, field in expected]
        alternatives = ", ".join(names[:-1]) + " or " + names[-1]
        assert terminal["diagnostics"] == blocker["diagnostics"]
        assert [item[:3] for item in blocker["diagnostics"]] == [
            [
                "PIE-S2335",
                "error",
                f"Ambiguous field: {expected[0][1]}; write {alternatives}",
            ]
        ]
        assert [
            diagnostics[index][0] for index in owners[name]["owner_diagnostic_sites"]
        ] == ["PIE-S2335"]

    conditions = cast(list[dict[str, Any]], primary["conditions"])
    missing = [
        item
        for item in conditions
        if item["owner"] == ["main.pietto", "missing_fact_join"]
    ]
    assert len(missing) == 1
    condition = missing[0]
    assert (condition["mode"], condition["state"], condition["ready"]) == (
        "M1",
        "unavailable",
        False,
    )
    assert (
        condition["diagnostics"]
        == condition["references"]
        == condition["conjuncts"]
        == []
    )
    terminal, nodes = terminal_graph("missing_fact_join")
    assert terminal["variant"] == "ProjectEffectiveOutputTerminal"
    assert terminal["reason"] == "joined_completion_non_concrete"
    block = nodes[terminal["joined_completion"]]
    assert (block["variant"], block["reason"]) == (
        "ProjectNonConcreteQueryBlock",
        "join_region_non_concrete",
    )
    region = nodes[block["join_region"]]
    assert (
        region["variant"] == "ProjectIRNonConcreteJoinRegion"
        and region["zero_allocation"] is True
    )
    uses = nodes[region["blockers"]]["items"]
    assert len(uses) == 1
    use = nodes[uses[0]]
    assert (use["variant"], use["join_position"]) == ("ProjectNonConcreteJoinUse", 0)
    issues = [nodes[index] for index in nodes[use["issues"]]["items"]]
    assert [(item["kind"], item["state"]) for item in issues] == [
        ("unknown_source_binding", "unknown")
    ]
    causes = [nodes[index] for index in nodes[issues[0]["causes"]]["items"]]
    assert [item["binding"] for item in causes] == [
        [0, "orders_by_customer", "orders_by_customer", "concrete"]
    ]
    final = [
        diagnostics[index]
        for index in owners["missing_fact_join"]["owner_diagnostic_sites"]
    ]
    assert len(final) == 1 and final[0][:2] == ["PIE-S2333", "error"]
    span = use["clause"]["span"]
    assert final[0][3] == [
        span[key] for key in ("path", "line", "column", "end_line", "end_column")
    ]

    for name, states, condition_codes, final_codes in (
        # The rows of an unknown relationship call are no ON references: the
        # call alone is reported (PIE-S2103), at the call.
        ("bad_relationship_join", [], ["PIE-S2103"], ["PIE-S2103"]),
        # An unknown ON read is reported alone, without a temporary admission
        # text.
        ("bad_role_join", ["unknown", "resolved"], ["PIE-S2335"], ["PIE-S2335"]),
    ):
        own = [item for item in conditions if item["owner"] == ["main.pietto", name]]
        assert len(own) == 1
        condition = own[0]
        assert (condition["mode"], condition["state"], condition["ready"]) == (
            "M3",
            "invalid",
            False,
        )
        assert [item[1] for item in condition["references"]] == states
        assert [item[0] for item in condition["diagnostics"]] == condition_codes
        terminal, nodes = terminal_graph(name)
        assert terminal["reason"] == "current_join_condition_non_concrete"
        blockers = nodes[terminal["blocker"]]
        assert blockers["variant"] == "tuple" and len(blockers["items"]) == 1
        blocker = nodes[blockers["items"][0]]
        assert blocker["variant"] == "ProjectJoinCondition"
        assert (
            blocker["condition"] == conditions[blocker["condition_site"]] == condition
        )
        predicate = nodes[blocker["predicate_expression"]]
        assert predicate["variant"] == "ProjectRelationshipPredicateExpression"
        assert predicate["owner"] == condition["owner"]
        assert predicate["context"] == condition["clause"]["on_clause"]
        assert predicate["authored"] == predicate["context"]["expression"]
        assert predicate["expression"] == blocker["expression"]
        assert predicate["calls"] == predicate["argument_bindings"] == []
        assert predicate["any_expressions"] == predicate["any_bindings"] == []
        assert predicate["parent"] is None and predicate["diagnostics"] == []
        assert (
            primary["input_scopes"][blocker["input_scope_site"]][0]
            == condition["owner"]
        )
        reported_spans = (
            [
                item[4]["span"]
                for item in condition["references"]
                if item[1] == "unknown"
            ]
            if states
            else [condition["conjuncts"][0][2]["span"]]
        )
        assert [item[3] for item in condition["diagnostics"]] == [
            [span[key] for key in ("path", "line", "column", "end_line", "end_column")]
            for span in reported_spans
        ]
        final = [diagnostics[index] for index in owners[name]["owner_diagnostic_sites"]]
        assert [item[0] for item in final] == final_codes
        assert final[-len(condition_codes) :] == condition["diagnostics"]

    ambiguous = [
        item
        for item in conditions
        if item["owner"] == ["main.pietto", "ambiguous_fact_join"]
    ]
    assert len(ambiguous) == 1 and ambiguous[0]["ready"] is True
    # The hand-written equality is a match equality that matches no key here.
    assert [item[0] for item in ambiguous[0]["equalities"]] == [0]
    assert ambiguous[0]["key_matches"] == []
    assert [item[1] for item in ambiguous[0]["references"]] == ["resolved", "resolved"]
    assert [item[:2] for item in ambiguous[0]["null_rejections"]] == [[0, 0], [0, 1]]
    terminal, nodes = terminal_graph("chasm_aggregate_refusal")
    assert terminal["reason"] == "joined_qualify_non_concrete"
    assert terminal["joined_qualify"] == terminal["blocker"]
    qualify = nodes[terminal["blocker"]]
    assert (qualify["variant"], qualify["reason"]) == (
        "ProjectNonConcreteJoinedQualify",
        "upstream_window_non_concrete",
    )
    window = nodes[qualify["window_stage"]]
    assert (window["variant"], window["reason"]) == (
        "ProjectNonConcreteJoinedWindowStage",
        "upstream_aggregation_non_concrete",
    )
    blocked_aggregate = nodes[window["input_aggregation"]]
    assert (blocked_aggregate["variant"], blocked_aggregate["reason"]) == (
        "ProjectNonConcreteJoinedAggregation",
        "aggregate_algebra_required",
    )
    assert primary["aggregations"][blocked_aggregate["aggregation"]]["owner"] == [
        "main.pietto",
        "chasm_aggregate_refusal",
    ]
    aggregate = [
        item
        for item in cast(list[dict[str, object]], primary["aggregations"])
        if item["owner"] == ["main.pietto", "chasm_aggregate_refusal"]
    ]
    actual_aggregate = json.dumps(
        aggregate, ensure_ascii=False, allow_nan=False, indent=2
    )
    assert aggregate, json.dumps(primary["aggregations"], ensure_ascii=False, indent=2)
    links = [
        link
        for item in aggregate
        for link in cast(list[dict[str, object]], item["linkages"])
    ]
    assert links and any(link["exposures"] for link in links), (
        "The authored aggregate must reach a real multiplicity exposure; review its actual blocker instead of substituting a retired CHASM label.\n"
        + actual_aggregate
    )
    assert all(
        item["variant"] == "ProjectNonConcreteJoinedAggregation" and item["reason"]
        for item in aggregate
    ), actual_aggregate
    for link in links:
        assert (link["ordinal"], link["function"]) == (0, "sum"), actual_aggregate
        assert link["arguments"] and link["final_grain"], actual_aggregate
        assert link["closure"] == link["context"]
        assert all(
            factor in cast(list[object], link["closure"])
            for factor in cast(list[object], link["seed"])
        )
        if link["exposures"]:
            assert link["risks"] == ["fanout_risk"]
            assert link["requirements"] == ["aggregate_algebra_required"]
        else:
            assert link["risks"] == link["requirements"] == []
    assert all(item["pairs"] == [] for item in aggregate)
    diagnostics = cast(list[list[object]], primary["diagnostics"])
    assert diagnostics and any(item[1] == "error" for item in diagnostics)
    negative = cast(dict[str, object], observation["negative"])
    assert negative["non_verified_admission"] == "rejected"
    assert negative["cross_snapshot_ref"] == "rejected"
    rejections = cast(list[list[object]], negative["pure_rejections"])
    assert [item[:2] for item in rejections] == [
        ["unknown_format", "unknown_format"],
        ["section_order", "invalid_section_order"],
        ["dangling_ref", "dangling_ref"],
    ]
    records = cast(list[list[object]], primary["portable_records"])
    use_position, use = next(
        (index, record) for index, record in enumerate(records) if record[0] == "use"
    )
    output_position = next(
        index
        for index, field in enumerate(cast(list[list[object]], use[1]))
        if field[0] == "output"
    )
    assert rejections[2][2:] == [use_position, output_position]
    controls = cast(dict[str, Any], negative["terminal_observer_controls"])
    shared = controls["shared"]
    assert shared["root"] == 0 and len(shared["nodes"]) == 2
    assert shared["nodes"][0] == {"variant": "tuple", "items": [1, 1]}
    assert (
        shared["nodes"][1]["variant"] == "ProjectNonConcreteJoinedNamespaceExpression"
    )
    assert shared["nodes"][1]["blocking_resolutions"] == [0]
    assert len(shared["nodes"][1]["resolutions"][0]["candidates"]) == 2
    cycle = controls["cycle"]
    assert cycle["root"] == 0 and len(cycle["nodes"]) == 2
    assert cycle["nodes"][0]["variant"] == "ProjectJoinUseIssue"
    assert cycle["nodes"][0]["causes"] == 1
    assert cycle["nodes"][1] == {"variant": "tuple", "items": [0, 0]}
    assert controls["rejections"] == [
        ["unknown_type", "TypeError"],
        ["omitted_field", "ValueError"],
        ["terminal_upstream", "ValueError"],
        ["namespace_kernel", "ValueError"],
        ["namespace_types", "ValueError"],
        ["namespace_any", "ValueError"],
        ["namespace_predicate", "ValueError"],
        ["qualify_references", "ValueError"],
        ["qualify_kernel", "ValueError"],
        ["qualify_types", "ValueError"],
        ["blocked_qualify_kernel", "ValueError"],
        ["blocked_qualify_references", "ValueError"],
        ["blocked_qualify_types", "ValueError"],
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


@pytest.mark.parametrize("stage", ["observation", "render"])
def test_probe_failure_writes_no_partial_observation(
    stage: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args):
        raise RuntimeError("observation failed")

    monkeypatch.setattr(probe, "observation", lambda workspace: {})
    monkeypatch.setattr(probe, stage, fail)
    with pytest.raises(RuntimeError, match="observation failed"):
        probe.main(["--workspace", str(tmp_path)])
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
