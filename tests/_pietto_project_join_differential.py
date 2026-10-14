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
PROBE = REPO_ROOT / "tests/_pietto_ir_join_differential.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Frozen from one reviewed source-checkout observation. Full observation and
# canonical bytes are compared directly; these digests are review aids only.
EXPECTED_COMMON_MANIFEST: dict[str, object] = {
    "observation_format": "pietto.phase62-join-differential.v1",
    "package_version": tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"],
    "runtime_identities_distinct": True,
    "relation_count": 32,
    "relations": [
        [["main.pietto", 0, 3, "relation", "source", "customers"], "concrete", 1],
        [["main.pietto", 0, 4, "relation", "source", "orders"], "concrete", 4],
        [["main.pietto", 0, 5, "relation", "source", "returns"], "concrete", 4],
        [
            ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
            "concrete",
            3,
        ],
        [
            [
                "main.pietto",
                0,
                7,
                "relation",
                "query",
                "orders_by_customer_copy",
            ],
            "concrete",
            2,
        ],
        [
            [
                "main.pietto",
                0,
                8,
                "relation",
                "query",
                "orders_by_customer_product",
            ],
            "concrete",
            3,
        ],
        [
            ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
            "concrete",
            2,
        ],
        [
            [
                "main.pietto",
                0,
                10,
                "relation",
                "query",
                "returns_by_customer_reason",
            ],
            "concrete",
            3,
        ],
        [["main.pietto", 0, 11, "relation", "query", "global_orders"], "concrete", 1],
        [
            ["main.pietto", 0, 12, "relation", "query", "global_returns"],
            "concrete",
            1,
        ],
        [
            ["z_disconnected.pietto", 1, 1, "relation", "source", "audit_rows"],
            "concrete",
            1,
        ],
        [
            ["z_disconnected.pietto", 1, 2, "relation", "query", "audit_result"],
            "concrete",
            1,
        ],
    ],
    "relationships": [
        [
            ["main.pietto", 0, 0, "customer_orders_coarse"],
            "concrete",
            [[0, "customer", "customers"], [1, "orders", "orders_by_customer"]],
        ],
        [
            ["main.pietto", 0, 1, "customer_orders_fine"],
            "concrete",
            [
                [0, "customer", "customers"],
                [1, "orders", "orders_by_customer_product"],
            ],
        ],
        [
            ["main.pietto", 0, 2, "customer_returns_coarse"],
            "concrete",
            [[0, "customer", "customers"], [1, "returns", "returns_by_customer"]],
        ],
        [
            ["main.pietto", 0, 3, "customer_returns_fine"],
            "concrete",
            [
                [0, "customer", "customers"],
                [1, "returns", "returns_by_customer_reason"],
            ],
        ],
        [
            ["main.pietto", 0, 4, "independent_facts"],
            "concrete",
            [
                [0, "orders", "orders_by_customer_product"],
                [1, "returns", "returns_by_customer_reason"],
            ],
        ],
        [
            ["main.pietto", 0, 5, "coarse_copy"],
            "concrete",
            [
                [0, "original", "orders_by_customer"],
                [1, "copy", "orders_by_customer_copy"],
            ],
        ],
        [
            ["main.pietto", 0, 6, "coarse_fine"],
            "concrete",
            [
                [0, "coarse", "orders_by_customer"],
                [1, "fine", "orders_by_customer_product"],
            ],
        ],
        [
            ["main.pietto", 0, 7, "orders_returns_aligned"],
            "concrete",
            [
                [0, "orders", "orders_by_customer"],
                [1, "returns", "returns_by_customer"],
            ],
        ],
        [
            ["main.pietto", 0, 8, "parallel_one"],
            "concrete",
            [
                [0, "orders", "orders_by_customer"],
                [1, "returns", "returns_by_customer"],
            ],
        ],
        [
            ["main.pietto", 0, 9, "parallel_two"],
            "concrete",
            [
                [0, "orders", "orders_by_customer"],
                [1, "returns", "returns_by_customer"],
            ],
        ],
        [
            ["main.pietto", 0, 10, "self_fact"],
            "concrete",
            [
                [0, "child", "orders_by_customer"],
                [1, "parent", "orders_by_customer"],
            ],
        ],
        [
            ["main.pietto", 0, 11, "globals"],
            "concrete",
            [[0, "orders", "global_orders"], [1, "returns", "global_returns"]],
        ],
        [
            ["main.pietto", 0, 12, "customer_orders_raw"],
            "concrete",
            [[0, "customer", "customers"], [1, "orders", "orders"]],
        ],
        [
            ["main.pietto", 0, 13, "orders_customer_unique_target"],
            "concrete",
            [[0, "orders", "orders"], [1, "customer", "customers"]],
        ],
        [
            ["main.pietto", 0, 14, "nullable_amounts"],
            "concrete",
            [[0, "orders", "orders"], [1, "returns", "returns"]],
        ],
        [
            ["main.pietto", 0, 15, "composite_raw"],
            "concrete",
            [[0, "orders", "orders"], [1, "returns", "returns"]],
        ],
    ],
    "directions_sha256": "d7b08c61186ab55d8d75985fbcd3d2fe5963adf5c4b82035612ebce827a377e3",
    "conditions": [
        ["customer_orders_coarse", 1],
        ["customer_orders_fine", 1],
        ["customer_returns_coarse", 1],
        ["customer_returns_fine", 1],
        ["independent_facts", 1],
        ["coarse_copy", 1],
        ["coarse_fine", 1],
        ["orders_returns_aligned", 1],
        ["parallel_one", 1],
        ["parallel_two", 1],
        ["self_fact", 1],
        ["globals", 1],
        ["customer_orders_raw", 1],
        ["orders_customer_unique_target", 1],
        ["nullable_amounts", 1],
        ["composite_raw", 2],
    ],
    "composite_condition": [
        "composite_raw",
        [
            [
                0,
                "orders",
                "customer_id",
                "returns",
                "customer_id",
                "standard_equality_true_only_null_rejecting",
            ],
            [
                1,
                "orders",
                "product_id",
                "returns",
                "reason_id",
                "standard_equality_true_only_null_rejecting",
            ],
        ],
    ],
    "direct_candidate_bucket_count": 23,
    "direct_candidate_buckets_sha256": "b5949496c483a69ae0d20fd05c20576177941be0e21fe37068712d7d34737998",
    "join_uses": [
        [
            ["main.pietto", 13, "direct_unique_join"],
            [["inner", "concrete", [], 1, None]],
        ],
        [
            ["main.pietto", 14, "explicit_one_join"],
            [["inner", "concrete", [], 1, None]],
        ],
        [["main.pietto", 15, "left_one_join"], [["left", "concrete", [], 1, None]]],
        [["main.pietto", 16, "variant_direct"], [["inner", "concrete", [], 1, None]]],
        [["main.pietto", 17, "variant_explicit"], [["inner", "concrete", [], 1, None]]],
        [
            ["main.pietto", 18, "unique_target_inner"],
            [["inner", "concrete", [], 1, None]],
        ],
        [
            ["main.pietto", 19, "unique_target_left"],
            [["left", "concrete", [], 1, None]],
        ],
        [["main.pietto", 20, "fanout_join"], [["inner", "concrete", [], 1, None]]],
        [["main.pietto", 21, "aligned_join"], [["inner", "concrete", [], 1, None]]],
        [["main.pietto", 22, "comparable_join"], [["inner", "concrete", [], 1, None]]],
        [
            ["main.pietto", 23, "chasm_join"],
            [["inner", "concrete", [], 1, None], ["inner", "concrete", [], 1, None]],
        ],
        [
            ["main.pietto", 24, "incompatible_join"],
            [["inner", "concrete", [], 1, None]],
        ],
        [
            ["main.pietto", 25, "reused_join"],
            [["inner", "concrete", [], 1, None], ["inner", "concrete", [], 1, None]],
        ],
        [["main.pietto", 26, "multihop_join"], [["inner", "concrete", [], 2, None]]],
        [["main.pietto", 27, "self_fact_join"], [["left", "concrete", [], 1, None]]],
        [["main.pietto", 28, "global_join"], [["inner", "concrete", [], 1, None]]],
        [
            ["main.pietto", 29, "ambiguous_fact_join"],
            [
                [
                    "inner",
                    "ambiguous",
                    ["direct_relationship_ambiguous"],
                    0,
                    ["ambiguous", 3],
                ]
            ],
        ],
        [
            ["main.pietto", 30, "missing_fact_join"],
            [["inner", "unknown", ["direct_relationship_absent"], 0, ["absent", 0]]],
        ],
        [
            ["main.pietto", 31, "bad_relationship_join"],
            [["inner", "unknown", ["unknown_relationship"], 0, None]],
        ],
        [
            ["main.pietto", 32, "bad_role_join"],
            [["inner", "unknown", ["unknown_endpoint_direction"], 0, None]],
        ],
    ],
    "binary_join_count": 19,
    "binary_joins_sha256": "547a510d8ed6232ea16f0defe39b76236c97481ef7c0acf76ef15c8e3eccc8c7",
    "selected_binary_joins": [
        [
            ["main.pietto", 13, "direct_unique_join"],
            "concrete",
            [
                [
                    [0, 0],
                    2,
                    2,
                    "inner",
                    "preserves_source_multiplicity",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    4,
                    1,
                ]
            ],
            [],
        ],
        [
            ["main.pietto", 15, "left_one_join"],
            "concrete",
            [
                [
                    [0, 0],
                    2,
                    2,
                    "left",
                    "preserves_source_multiplicity",
                    "guarantees_left_survival",
                    "may_null_extend_right",
                    "present",
                    4,
                    1,
                ]
            ],
            [],
        ],
        [
            ["main.pietto", 20, "fanout_join"],
            "concrete",
            [
                [
                    [0, 0],
                    2,
                    2,
                    "inner",
                    "may_multiply",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    5,
                    1,
                ]
            ],
            [],
        ],
        [
            ["main.pietto", 23, "chasm_join"],
            "concrete",
            [
                [
                    [0, 0],
                    2,
                    2,
                    "inner",
                    "may_multiply",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    4,
                    1,
                ],
                [
                    [1, 0],
                    2,
                    2,
                    "inner",
                    "may_multiply",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    7,
                    1,
                ],
            ],
            [],
        ],
        [
            ["main.pietto", 26, "multihop_join"],
            "concrete",
            [
                [
                    [0, 0],
                    2,
                    2,
                    "inner",
                    "preserves_source_multiplicity",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    4,
                    1,
                ],
                [
                    [0, 1],
                    2,
                    2,
                    "inner",
                    "preserves_source_multiplicity",
                    "may_drop_left_rows",
                    "no_new_null_extension",
                    "not_applicable",
                    6,
                    1,
                ],
            ],
            [],
        ],
    ],
    "relational_outputs_sha256": "291dbef002e786627d3a02e2e2daf836b619e5d0b4bc4d78d77d134099601295",
    "facts": [
        [
            ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
            4,
            0,
            "sum",
            "total",
        ],
        [
            ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
            4,
            1,
            "count",
            "order_count",
        ],
        [
            ["main.pietto", 0, 7, "relation", "query", "orders_by_customer_copy"],
            7,
            0,
            "sum",
            "total",
        ],
        [
            ["main.pietto", 0, 8, "relation", "query", "orders_by_customer_product"],
            10,
            0,
            "sum",
            "total",
        ],
        [
            ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
            13,
            0,
            "sum",
            "total",
        ],
        [
            ["main.pietto", 0, 10, "relation", "query", "returns_by_customer_reason"],
            16,
            0,
            "count",
            "return_count",
        ],
        [
            ["main.pietto", 0, 11, "relation", "query", "global_orders"],
            19,
            0,
            "count",
            "total",
        ],
        [
            ["main.pietto", 0, 12, "relation", "query", "global_returns"],
            22,
            0,
            "count",
            "total",
        ],
    ],
    "fact_localities": [
        [
            ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
            ["sum", "total"],
            [
                ["home", None],
                ["right", 24],
                ["right", 26],
                ["right", 28],
                ["left", 39],
                ["left", 41],
                ["right", 50],
                ["right", 52],
                ["right", 54],
                ["left", 57],
                ["right", 58],
            ],
        ],
        [
            ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
            ["count", "order_count"],
            [
                ["home", None],
                ["right", 24],
                ["right", 26],
                ["right", 28],
                ["left", 39],
                ["left", 41],
                ["right", 50],
                ["right", 52],
                ["right", 54],
                ["left", 57],
                ["right", 58],
            ],
        ],
        [
            ["main.pietto", 0, 7, "relation", "query", "orders_by_customer_copy"],
            ["sum", "total"],
            [["home", None], ["right", 40]],
        ],
        [
            ["main.pietto", 0, 8, "relation", "query", "orders_by_customer_product"],
            ["sum", "total"],
            [["home", None], ["right", 42], ["right", 44], ["left", 47]],
        ],
        [
            ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
            ["sum", "total"],
            [["home", None], ["right", 30], ["right", 32], ["right", 56]],
        ],
        [
            ["main.pietto", 0, 10, "relation", "query", "returns_by_customer_reason"],
            ["count", "return_count"],
            [["home", None], ["right", 46], ["right", 48]],
        ],
        [
            ["main.pietto", 0, 11, "relation", "query", "global_orders"],
            ["count", "total"],
            [["home", None], ["left", 59]],
        ],
        [
            ["main.pietto", 0, 12, "relation", "query", "global_returns"],
            ["count", "total"],
            [["home", None], ["right", 60]],
        ],
    ],
    "alignment_count": 28,
    "alignments": [
        ["exactly_aligned", "unique", [], [], 0],
        ["exactly_aligned", "ambiguous", [], [], 0],
        ["exactly_aligned", "ambiguous", [], [], 0],
        [
            "exactly_aligned",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        ["exactly_aligned", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        [
            "exactly_aligned",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk", "cross_fact_multiplication"],
            ["aggregate_algebra_required"],
            1,
        ],
        ["incompatible", "none", ["fanout_risk"], ["aggregate_algebra_required"], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["exactly_aligned", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["exactly_aligned", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["exactly_aligned", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        ["structurally_alignable", "ambiguous", [], [], 0],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        ["exactly_aligned", "ambiguous", [], [], 0],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "exactly_aligned",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        [
            "reaggregation_required",
            "unique",
            ["fanout_risk"],
            ["aggregate_algebra_required"],
            0,
        ],
        ["exactly_aligned", "unique", [], [], 0],
    ],
    "chasms": [
        [
            ["main.pietto", 0, 23, "relation", "query", "chasm_join"],
            [
                [
                    [
                        "main.pietto",
                        0,
                        8,
                        "relation",
                        "query",
                        "orders_by_customer_product",
                    ],
                    ["sum", "total"],
                    "right",
                    44,
                ],
                [
                    [
                        "main.pietto",
                        0,
                        10,
                        "relation",
                        "query",
                        "returns_by_customer_reason",
                    ],
                    ["count", "return_count"],
                    "right",
                    46,
                ],
            ],
            [37, 38],
        ]
    ],
    "verification": ["verified", [], "verified"],
    "analysis_products": [62, 46, 90, 8, 28, 1],
    "inspection_counts": [
        16,
        32,
        16,
        17,
        32,
        20,
        22,
        19,
        19,
        19,
        90,
        27,
        51,
        128,
        100,
        63,
        8,
        39,
        28,
        28,
        1,
        8,
        207,
    ],
    "queries": [
        ["direct_unique_join", 1, "concrete", [], 1, None],
        ["variant_direct", 1, "concrete", [], 1, None],
        [
            "ambiguous_fact_join",
            1,
            "ambiguous",
            ["direct_relationship_ambiguous"],
            0,
            ["ambiguous", ["orders_returns_aligned", "parallel_one", "parallel_two"]],
        ],
        ["bad_relationship_join", 1, "unknown", ["unknown_relationship"], 0, None],
        ["bad_role_join", 1, "unknown", ["unknown_endpoint_direction"], 0, None],
    ],
    "non_concrete": [4, 4, 4],
    "non_concrete_multifact": [
        [
            ["main.pietto", 0, 29, "relation", "query", "ambiguous_fact_join"],
            "ambiguous_path",
            [[0, "ambiguous", ["direct_relationship_ambiguous"]]],
            [
                [
                    ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
                    4,
                    0,
                    "sum",
                    "total",
                ],
                [
                    ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
                    4,
                    1,
                    "count",
                    "order_count",
                ],
                [
                    ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
                    13,
                    0,
                    "sum",
                    "total",
                ],
            ],
            [46, 46],
        ],
        [
            ["main.pietto", 0, 30, "relation", "query", "missing_fact_join"],
            "insufficient_evidence",
            [[0, "unknown", ["direct_relationship_absent"]]],
            [
                [
                    ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
                    4,
                    0,
                    "sum",
                    "total",
                ],
                [
                    ["main.pietto", 0, 6, "relation", "query", "orders_by_customer"],
                    4,
                    1,
                    "count",
                    "order_count",
                ],
                [
                    [
                        "main.pietto",
                        0,
                        10,
                        "relation",
                        "query",
                        "returns_by_customer_reason",
                    ],
                    16,
                    0,
                    "count",
                    "return_count",
                ],
            ],
            [46, 46],
        ],
        [
            ["main.pietto", 0, 31, "relation", "query", "bad_relationship_join"],
            "insufficient_evidence",
            [[0, "unknown", ["unknown_relationship"]]],
            [
                [
                    ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
                    13,
                    0,
                    "sum",
                    "total",
                ]
            ],
            [46, 46],
        ],
        [
            ["main.pietto", 0, 32, "relation", "query", "bad_role_join"],
            "insufficient_evidence",
            [[0, "unknown", ["unknown_endpoint_direction"]]],
            [
                [
                    ["main.pietto", 0, 9, "relation", "query", "returns_by_customer"],
                    13,
                    0,
                    "sum",
                    "total",
                ]
            ],
            [46, 46],
        ],
    ],
    "query_closure": {
        "locality_count": 39,
        "locality_sha256": "fa5f3a2e36d78591de9c5648030fe51809378d9e124acc3287ae710d9dbe79cc",
        "chasm": [[1, 1]],
        "nulling_count": 90,
        "nulling_sha256": "f11789319a712a0c1a69aca4f6b0945211516b1f56fb4fd5990c7cfe75aef677",
    },
    "metamorphic": {
        "direct_vs_explicit": [
            [
                "zero_allowed",
                "at_most_one",
                "inner",
                "preserves_source_multiplicity",
                "may_drop_left_rows",
                "no_new_null_extension",
                "not_applicable",
                ["non_null", "nullable", "non_null"],
                "ProjectIRJoinUnavailableProperty",
                ["strict", "strict"],
                5,
            ],
            [
                "zero_allowed",
                "at_most_one",
                "inner",
                "preserves_source_multiplicity",
                "may_drop_left_rows",
                "no_new_null_extension",
                "not_applicable",
                ["non_null", "nullable", "non_null"],
                "ProjectIRJoinUnavailableProperty",
                ["strict", "strict"],
                5,
            ],
            [True, True, True],
        ],
        "parallel": [
            [
                "concrete",
                [],
                [[0, "customer_returns_coarse", 0, 1, "zero_allowed", "at_most_one"]],
                None,
            ],
            [
                "ambiguous",
                ["direct_relationship_ambiguous"],
                [],
                [
                    "ambiguous",
                    ["customer_returns_coarse", "customer_returns_coarse_parallel"],
                ],
            ],
            [
                "concrete",
                [],
                [[0, "customer_returns_coarse", 0, 1, "zero_allowed", "at_most_one"]],
                None,
            ],
            [2, ["customer_returns_coarse", "customer_returns_coarse_parallel"]],
        ],
        "unique_transition": [
            ["at_most_one", "preserves_source_multiplicity", ["strict"], 4],
            ["unbounded_by_one", "may_multiply", [], 3],
            True,
        ],
        "inner_vs_left": [
            [
                "inner",
                "preserves_source_multiplicity",
                "may_drop_left_rows",
                "no_new_null_extension",
                "not_applicable",
                ["non_null", "nullable", "non_null"],
                "ProjectIRJoinUnavailableProperty",
                ["strict", "strict"],
                5,
            ],
            [
                "left",
                "preserves_source_multiplicity",
                "guarantees_left_survival",
                "may_null_extend_right",
                "present",
                ["nullable", "nullable", "nullable"],
                "ProjectIRProvidedNullExtension",
                ["strict", "lax"],
                4,
            ],
        ],
        "multi_hop": [2, [0, 1], True],
        "branching": [True, True, [0, 0]],
        "role_playing": [[0, 1], [50, 52], [50, 52, 50, 52], [57, 58, 57, 58]],
        "fanout": [
            "zero_allowed",
            "unbounded_by_one",
            "inner",
            "may_multiply",
            "may_drop_left_rows",
            "no_new_null_extension",
            "not_applicable",
            ["non_null", "non_null", "non_null", "nullable"],
            "ProjectIRJoinUnavailableProperty",
            ["strict"],
            4,
        ],
        "chasm": [
            1,
            [
                [
                    "reaggregation_required",
                    ["fanout_risk", "cross_fact_multiplication"],
                    ["aggregate_algebra_required"],
                ]
            ],
        ],
        "comparable": [
            ["exactly_aligned", "unique", ["aggregate_algebra_required"]],
            ["reaggregation_required", "unique", ["aggregate_algebra_required"]],
            ["reaggregation_required", "unique", ["aggregate_algebra_required"]],
        ],
    },
    "pure_rejections": [
        ["unknown_format", "unknown_format", None, None],
        ["section_order", "invalid_section_order", None, None],
        ["dangling_ref", "dangling_ref", 171, 1],
    ],
    "portable": {
        "primary_count": 1807,
        "primary_sha256": "93a44608aba93169d059603299f000603859693421f1db1c1b40a8698770a073",
        "parallel_count": 1772,
        "parallel_sha256": "236db364131c1a6bcf5498a492d7caa7ec4c891c035840bacea798cb917d801c",
        "no_unique_count": 1758,
        "no_unique_sha256": "d6335c3792cd1b72bc172584552abad3d78aa1f8aeb542815d697721ee2241f0",
        "shifted_count": 1807,
        "shifted_sha256": "a443639c07a1b739802c9a46d9f628fe34c7ae36a9615c9be9cd05c5ffbab14a",
    },
    "canonical": {
        "primary_sha256": "24c29a46c7621d5eaca131a2165f5a12a4be436b66a721035393883f9c8f18e5",
        "primary_size": 260978,
        "parallel_sha256": "3850495ed50aaff3c2fe0f5f821d605301fe87000b9b46389f17dda363a0855d",
        "parallel_size": 256426,
        "no_unique_sha256": "8aad17e0d0f78c77bad9210a4593adfebe1833a55e090d792f47189d7cdb77c6",
        "no_unique_size": 251458,
        "shifted_sha256": "1caf203f6e4d4ba5cc0ac73225f7e9ec303a0d8237484399f9b55e742afb1d0f",
        "shifted_size": 261112,
    },
    "shifted": {
        "starting_coordinates": [7, 11, 5, 5],
        "first_coordinates": [7, 11, 5, 5],
        "verification": "verified",
    },
    "observation_sha256": "2cbc4abaf1f1ec2c94b755563707a9ad71fa9d2cc948dfc483663cc98a249d1f",
    "observation_size": 2897716,
}


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _canonical_bytes(observation: dict[str, object], section: str) -> bytes:
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


def _ledger_manifest(ledgers: list[list[object]]) -> list[list[object]]:
    return [
        [
            [
                cast(list[object], ledger[0])[0],
                cast(list[object], ledger[0])[2],
                cast(list[object], ledger[0])[-1],
            ],
            [
                [
                    use[1],
                    use[2],
                    use[3],
                    len(cast(list[object], use[4])),
                    (
                        None
                        if use[5] is None
                        else [
                            cast(list[object], use[5])[0],
                            len(cast(list[object], cast(list[object], use[5])[1])),
                        ]
                    ),
                ]
                for use in cast(list[list[object]], ledger[2])
            ],
        ]
        for ledger in ledgers
    ]


def _binary_manifest(regions: list[list[object]]) -> list[list[object]]:
    return [
        [
            [
                cast(list[object], region[0])[0],
                cast(list[object], region[0])[2],
                cast(list[object], region[0])[-1],
            ],
            region[1],
            [
                [
                    cast(list[object], join[0])[-2:],
                    len(cast(list[object], join[2])),
                    len(cast(list[object], join[3])),
                    join[7],
                    join[8],
                    join[9],
                    join[10],
                    join[11],
                    len(cast(list[object], join[12])),
                    len(cast(list[object], join[13])),
                ]
                for join in cast(list[list[object]], region[2])
            ],
            region[3],
        ]
        for region in regions
    ]


def _metamorphic_manifest(value: object) -> dict[str, object]:
    metamorphic = cast(dict[str, object], value)
    direct = cast(list[object], metamorphic["direct_vs_explicit"])
    direct_effect = cast(list[object], direct[0])
    explicit_effect = cast(list[object], direct[1])
    parallel = cast(list[object], metamorphic["parallel"])
    unique = cast(list[list[object]], metamorphic["unique_transition"])
    inner, left = cast(list[list[object]], metamorphic["inner_vs_left"])
    role = cast(list[object], metamorphic["role_playing"])
    return {
        "direct_vs_explicit": [
            direct_effect[1:12],
            explicit_effect[1:12],
            direct[2:],
        ],
        "parallel": [
            cast(list[object], parallel[0])[2:6],
            cast(list[object], parallel[1])[2:6],
            cast(list[object], parallel[2])[2:6],
            parallel[3:],
        ],
        "unique_transition": [
            [unique[0][2], unique[0][4], unique[0][10], unique[0][11]],
            [unique[1][2], unique[1][4], unique[1][10], unique[1][11]],
            unique[0][12] == unique[1][12],
        ],
        "inner_vs_left": [inner[3:12], left[3:12]],
        "multi_hop": metamorphic["multi_hop"],
        "branching": metamorphic["branching"],
        "role_playing": [
            role[0],
            role[1],
            role[2],
            role[4],
        ],
        "fanout": cast(list[object], metamorphic["fanout"])[1:12],
        "chasm": metamorphic["chasm"],
        "comparable": metamorphic["comparable"],
    }


def _common_manifest(document: bytes) -> dict[str, object]:
    observation = _decoded(document)
    primary = cast(dict[str, object], observation["primary"])
    parallel = cast(dict[str, object], observation["parallel"])
    no_unique = cast(dict[str, object], observation["no_unique"])
    shifted = cast(dict[str, object], observation["shifted"])
    primary_records = primary["portable_records"]
    parallel_records = parallel["portable_records"]
    no_unique_records = no_unique["portable_records"]
    shifted_records = shifted["portable_records"]
    primary_bytes = _canonical_bytes(observation, "primary")
    parallel_bytes = _canonical_bytes(observation, "parallel")
    no_unique_bytes = _canonical_bytes(observation, "no_unique")
    shifted_bytes = _canonical_bytes(observation, "shifted")
    relations = cast(list[list[object]], primary["relations"])
    analysis_products = cast(list[object], primary["analysis_products"])
    binaries = _binary_manifest(cast(list[list[object]], primary["join_regions"]))
    # The reviewed bytes leave the version out; "package_version" pins it.
    field = b'"package_version":' + json.dumps(observation["package_version"]).encode()
    assert document.count(field) == 1
    unversioned = document.replace(field, b'"package_version":null')
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "runtime_identities_distinct": observation["runtime_identities_distinct"],
        "relation_count": len(relations),
        "relations": [
            [item[0], item[1], len(cast(list[object], item[2]))]
            for item in (*relations[:10], *relations[-2:])
        ],
        "relationships": primary["relationships"],
        "directions_sha256": _digest(primary["directions"]),
        "conditions": [
            [item[0], len(cast(list[object], item[1]))]
            for item in cast(list[list[object]], primary["conditions"])
        ],
        "composite_condition": cast(list[object], primary["conditions"])[-1],
        "direct_candidate_bucket_count": len(
            cast(list[object], primary["direct_candidate_buckets"])
        ),
        "direct_candidate_buckets_sha256": _digest(primary["direct_candidate_buckets"]),
        "join_uses": _ledger_manifest(cast(list[list[object]], primary["ledgers"])),
        "binary_join_count": sum(len(cast(list[object], item[2])) for item in binaries),
        "binary_joins_sha256": _digest(binaries),
        "selected_binary_joins": [
            item
            for item in binaries
            if cast(list[object], item[0])[-1]
            in (
                "direct_unique_join",
                "left_one_join",
                "fanout_join",
                "chasm_join",
                "multihop_join",
            )
        ],
        "relational_outputs_sha256": _digest(primary["relational_outputs"]),
        "facts": primary["facts"],
        "fact_localities": [
            [
                cast(list[object], item[0])[0],
                cast(list[object], item[0])[-2:],
                [
                    [locality[1], locality[2]]
                    for locality in cast(list[list[object]], item[1])
                ],
            ]
            for item in cast(list[list[object]], primary["fact_localities"])
        ],
        "alignment_count": len(cast(list[object], primary["alignments"])),
        "alignments": [
            [item[2], item[3], item[4], item[5], item[6]]
            for item in cast(list[list[object]], primary["alignments"])
        ],
        "chasms": [
            [
                item[0],
                [
                    [
                        cast(list[object], locality[0])[0],
                        cast(list[object], locality[0])[-2:],
                        locality[1],
                        locality[2],
                    ]
                    for locality in cast(list[list[object]], item[1])
                ],
                item[2],
            ]
            for item in cast(list[list[object]], primary["chasms"])
        ],
        "verification": primary["verification"],
        "analysis_products": [
            analysis_products[0],
            len(cast(list[object], analysis_products[1])),
            *analysis_products[2:],
        ],
        "inspection_counts": primary["inspection_counts"],
        "queries": [
            [
                item[0],
                cast(list[object], item[1])[0],
                cast(list[object], cast(list[object], item[1])[1])[2],
                cast(list[object], cast(list[object], item[1])[1])[3],
                len(
                    cast(
                        list[object],
                        cast(list[object], cast(list[object], item[1])[1])[4],
                    )
                ),
                cast(list[object], cast(list[object], item[1])[1])[5],
            ]
            for item in cast(list[list[object]], primary["queries"])
        ],
        "non_concrete": primary["non_concrete"],
        "non_concrete_multifact": primary["non_concrete_multifact"],
        "query_closure": {
            "locality_count": len(
                cast(list[object], cast(list[object], primary["query_closure"])[0])
            ),
            "locality_sha256": _digest(cast(list[object], primary["query_closure"])[0]),
            "chasm": cast(list[object], primary["query_closure"])[1],
            "nulling_count": len(
                cast(list[object], cast(list[object], primary["query_closure"])[2])
            ),
            "nulling_sha256": _digest(cast(list[object], primary["query_closure"])[2]),
        },
        "metamorphic": _metamorphic_manifest(observation["metamorphic"]),
        "pure_rejections": observation["pure_rejections"],
        "portable": {
            "primary_count": len(cast(list[object], primary_records)),
            "primary_sha256": _digest(primary_records),
            "parallel_count": len(cast(list[object], parallel_records)),
            "parallel_sha256": _digest(parallel_records),
            "no_unique_count": len(cast(list[object], no_unique_records)),
            "no_unique_sha256": _digest(no_unique_records),
            "shifted_count": len(cast(list[object], shifted_records)),
            "shifted_sha256": _digest(shifted_records),
        },
        "canonical": {
            "primary_sha256": hashlib.sha256(primary_bytes).hexdigest(),
            "primary_size": len(primary_bytes),
            "parallel_sha256": hashlib.sha256(parallel_bytes).hexdigest(),
            "parallel_size": len(parallel_bytes),
            "no_unique_sha256": hashlib.sha256(no_unique_bytes).hexdigest(),
            "no_unique_size": len(no_unique_bytes),
            "shifted_sha256": hashlib.sha256(shifted_bytes).hexdigest(),
            "shifted_size": len(shifted_bytes),
        },
        "shifted": {
            "starting_coordinates": shifted["starting_coordinates"],
            "first_coordinates": shifted["first_coordinates"],
            "verification": shifted["verification"],
        },
        "observation_sha256": hashlib.sha256(unversioned).hexdigest(),
        "observation_size": len(unversioned),
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    store = acquisition.acquisition(tmp_path_factory)
    documents = store.documents("phase62")
    observations: dict[str, bytes] = {}
    interpreters = store.interpreters
    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        for seed in SEEDS:
            key = f"source:{label}:seed:{seed}"
            observations[key] = documents[key]

    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"relocated:{label}:seed:7"
        observations[key] = documents[key]

    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"installed:{label}:seed:7"
        observations[key] = documents[key]

    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origins": store.installed_origins(),
        "installed_source_root": store.installed_source_root(),
        "empty_install_cache": store.empty_install_cache(),
    }


def _baseline_key() -> str:
    return f"source:python{sys.version_info[0]}.{sys.version_info[1]}:seed:0"
