"""Installed private Int product witness; importing its report checker needs no Arrow."""

from __future__ import annotations

import argparse
from copy import copy
from dataclasses import replace
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast

FORMAT = "pietto.result-product.v1"
PIN = "25.0.1"
BIG = 9007199254740993
LOW, HIGH = -(2**63), 2**63 - 1
PRODUCTS = (
    "project_result_contract",
    "project_result_binding",
    "project_arrow_result",
    "project_result_contract_pure_boundary",
    "project_result_contract_portable",
    "project_result_contract_correspondence",
    "project_scalar_meaning",
    "project_result_reader",
    "project_arrow_interop",
    "project_result_ingress",
)
CASES = (
    "postgres",
    "mysql",
    "neutral_reuse",
    "foreign_root",
    "ordered_fields",
    "empty",
    "all_null",
    "null_bool_arity",
    "producer_mismatch",
    "coordinated_mutation",
    "owned",
    "limits",
    "batch_corruption",
    "no_reconstruction",
    "contract_documents",
    "contract_substitutions",
    "contract_identity",
    "contract_independence",
    "contract_pure",
    "contract_limits",
    "contract_malformed",
    "contract_order_substitution",
    "contract_live_grafts",
    "integer_widths",
    "integer_adaptation",
    "scalar_mixed",
    "scalar_refusals",
    "scalar_batches",
    "scalar_identity",
    "scalar_codec",
    "text_values",
    "text_binding",
    "text_requests",
    "text_empty_null",
    "text_resources",
    "text_supplied",
    "text_value_substitution",
    "text_codec",
    "decimal_values",
    "decimal_bindings",
    "decimal_requests",
    "decimal_context",
    "decimal_empty_null",
    "decimal_resources",
    "decimal_supplied",
    "decimal_substitution",
    "decimal_codec",
    "meaning_premise",
    "timestamp_values",
    "timestamp_policy",
    "uuid_values",
    "uuid_policy",
    "temporal_empty_mixed",
    "temporal_resources",
    "temporal_correspondence",
    "temporal_codec",
    "finite_mixed_values",
    "finite_empty",
    "finite_all_null",
    "carrier_labels",
    "carrier_label_refusals",
    "finite_resources",
    "finite_correspondence",
    "finite_codec",
    "reader_values",
    "reader_empty_null",
    "reader_extent",
    "reader_terminal",
    "reader_lifecycle",
    "reader_limits",
    "reader_rechunk",
    "reader_identity",
    "reader_correspondence",
    "reader_incremental",
    "ownership_copy",
    "ownership_borrow",
    "ownership_transfer",
    "c_schema_array",
    "c_schema_requests",
    "c_stream_values",
    "c_stream_terminal",
    "c_protocol_lifetime",
    "cpu_protocol_resources",
    "interop_correspondence",
    "ingress_rows",
    "ingress_batch",
    "ingress_reader",
    "ingress_parity",
    "ingress_refusals",
    "ingress_ownership",
    "ingress_resources",
    "ingress_independence",
)


def source(target):
    return f"""shape Row:
    id: Int not null
    other: Int nullable
source rows: Row is {target}.table("opaque.result.fixture")
table result:
    from rows
    select:
        renamed = id
        other
"""


def emission_input(target, *, lower=LOW, upper=HIGH):
    storage = "pg_int8" if target == "postgres" else "my_bigint"
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {
                "family": target,
                "release": "18.6" if target == "postgres" else "8.4.12",
            },
            "sources": [
                {
                    "scan": "relation_rows",
                    "selector": {
                        "module": "main.pietto",
                        "kind": "source",
                        "name": "rows",
                    },
                    "relation": {
                        "namespace": "public" if target == "postgres" else "phase66",
                        "name": "rows",
                    },
                    "fields": [
                        {
                            "ordinal": i,
                            "name": name,
                            "column": name,
                            "representation": {
                                "storage": {"kind": storage},
                                "nullable": bool(i),
                                "domain": {
                                    "kind": "int_range",
                                    "min": str(lower),
                                    "max": str(upper),
                                },
                            },
                        }
                        for i, name in enumerate(("id", "other"))
                    ],
                    "premises": [
                        {"key": key, "scope": "source", "value": True}
                        for key in ("row_domain_matches", "read_only_object")
                    ],
                }
            ],
            "environment": [
                {
                    "key": "client_encoding",
                    "scope": "statement",
                    "value": "UTF8" if target == "postgres" else "utf8mb4",
                },
                {
                    "key": "operator_environment",
                    "scope": "statement",
                    "value": "builtin_only",
                },
            ],
        }
    ).encode()


def build_neutral(directory, sources):
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    directory.mkdir()
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, text in sources.items():
        (directory / name).write_text(text, encoding="utf-8")
    parsed = check_project_parse_only(directory)
    assert parsed.ok
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    (owner,) = tuple(o for o in ir.owners if o.definition.name == "result")
    plan = build_project_sql_plan(completed, bundle, owner)
    checked = verify_project_sql_plan(plan, completed, bundle, owner)
    assert checked.verified
    return checked


def build_source(directory, target):
    from pietto._project.project_sql_emission import emit_project_sql

    checked = build_neutral(directory, {"main.pietto": source(target)})
    outcome = emit_project_sql(checked, emission_input(target))
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    return checked, outcome.artifact


def observations(target, *, lower=LOW, upper=HIGH):
    from pietto._project.project_result_binding import ProducerObservation

    return tuple(
        ProducerObservation(
            i,
            name,
            target,
            "pg_int8" if target == "postgres" else "my_bigint",
            lower,
            upper,
        )
        for i, name in enumerate(("renamed", "other"))
    )


def refused(action):
    from pietto._project.project_result_contract import ResultError

    try:
        action()
    except ResultError as exc:
        return exc.category
    raise AssertionError("negative witness unexpectedly accepted")


def run_cases(root):
    pa = importlib.import_module("pyarrow")
    from pietto._project import (
        project_result_contract as c,
        project_result_binding as p,
        project_arrow_result as a,
    )
    from pietto._project.project_sql_emission import emit_project_sql

    results = {}
    fixed = [[BIG, None], [BIG, -BIG], [0, 0], [-1, 1], [LOW, HIGH], [HIGH, LOW]]
    built = {}
    for target in ("postgres", "mysql"):
        checked, artifact = build_source(root / target, target)
        contract = c.build_result_contract(checked)
        producer = p.bind_producer(contract, artifact, observations(target))
        arrow = a.bind_arrow(producer)
        batch = a.build_owned_batch(arrow, fixed)
        actual = [
            list(row)
            for row in zip(*(col.to_pylist() for col in batch.columns), strict=True)
        ]
        assert actual == fixed
        results[target] = {
            "rows": actual,
            "types": [str(f.type) for f in batch.schema],
            "nullable": [f.nullable for f in batch.schema],
            "labels": batch.schema.names,
            "storage": [f.observation.storage for f in producer.fields],
        }
        built[target] = checked, artifact, contract, producer, arrow
    checked, artifact, contract, producer, arrow = built["postgres"]
    from pietto._project.project_result_contract_portable import export_result_contract

    neutral_before = export_result_contract(contract, checked).canonical_bytes
    second = emit_project_sql(
        checked, emission_input("postgres", lower=-BIG, upper=BIG)
    ).artifact
    alternative = p.bind_producer(
        contract, second, observations("postgres", lower=-BIG, upper=BIG)
    )
    assert (
        alternative.contract is producer.contract
        and alternative.artifact is not artifact
    )
    assert export_result_contract(contract, checked).canonical_bytes == neutral_before
    results["neutral_reuse"] = {
        "same_contract": True,
        "outside_narrow_domain": refused(
            lambda: a.build_owned_batch(a.bind_arrow(alternative), [[HIGH, None]])
        ),
    }
    foreign_checked, foreign_artifact = build_source(root / "foreign", "postgres")
    results["foreign_root"] = [
        refused(lambda: c.verify_result_contract(contract, foreign_checked)),
        refused(
            lambda: p.bind_producer(
                contract, foreign_artifact, observations("postgres")
            )
        ),
    ]
    leaves = contract.shape.fields
    results["ordered_fields"] = [
        refused(
            lambda fields=fields: c.verify_result_contract(
                replace(contract, shape=c.ResultShape(fields)), checked
            )
        )
        for fields in (leaves[:1], leaves[::-1], (leaves[0], leaves[0]))
    ]
    empty = a.build_owned_batch(arrow, [])
    nulls = a.build_owned_batch(arrow, [[0, None], [1, None]])
    results["empty"] = [empty.num_rows, [str(f.type) for f in empty.schema]]
    results["all_null"] = [nulls.column(1).null_count, str(nulls.column(1).type)]
    results["null_bool_arity"] = [
        refused(lambda row=row: a.build_owned_batch(arrow, [row]))
        for row in (
            [None, None],
            [True, None],
            [0],
            [0, 1, 2],
            [1.0, None],
            [str(BIG), None],
            [HIGH + 1, None],
        )
    ]
    bad_observations = (
        replace(observations("postgres")[0], storage="pg_int4"),
        observations("postgres")[1],
    )
    wrong_ordinal = (
        replace(observations("postgres")[0], ordinal=1),
        observations("postgres")[1],
    )
    results["producer_mismatch"] = [
        refused(lambda obs=obs: p.bind_producer(contract, artifact, obs))
        for obs in (bad_observations, wrong_ordinal)
    ]
    damaged = replace(
        producer,
        fields=(
            replace(producer.fields[0], observation=bad_observations[0]),
            producer.fields[1],
        ),
    )
    coordinated = a.ArrowResultBinding(
        damaged,
        pa.schema(
            [
                pa.field("renamed", pa.int32(), False),
                pa.field("other", pa.int64(), True),
            ]
        ),
    )
    results["coordinated_mutation"] = refused(
        lambda: a.verify_arrow_binding(coordinated, damaged)
    )
    # Upstream root damage cannot be made valid by coordinating lower-layer objects.
    corrupt_column = replace(artifact.ast.columns[0], ordinal=1)
    corrupt_artifact = copy(artifact)
    object.__setattr__(
        corrupt_artifact,
        "ast",
        replace(artifact.ast, columns=(corrupt_column, artifact.ast.columns[1])),
    )
    results["coordinated_mutation"] += "/" + refused(
        lambda: p.bind_producer(contract, corrupt_artifact, observations("postgres"))
    )
    caller = [[BIG, None], [0, 1]]
    owned = a.build_owned_batch(arrow, caller)
    caller[0][0] = 2
    caller[1] = [3, 4]
    caller.clear()
    results["owned"] = [col.to_pylist() for col in owned.columns]
    assert results["owned"] == [[BIG, 0], [None, 1]]
    results["limits"] = [
        refused(
            lambda limit=limit: a.build_owned_batch(arrow, [[0, None]], limits=limit)
        )
        for limit in (
            a.BatchLimits(fields=1),
            a.BatchLimits(rows=0),
            a.BatchLimits(bytes=17),
        )
    ]
    wrong_schema = pa.RecordBatch.from_arrays(
        [pa.array([0], type=pa.int32()), pa.array([None], type=pa.int64())],
        names=["renamed", "other"],
    )
    bad_null = pa.RecordBatch.from_arrays(
        [pa.array([None], type=pa.int64()), pa.array([0], type=pa.int64())],
        schema=arrow.schema,
    )
    retained = pa.RecordBatch.from_arrays(
        [
            pa.array([0, 0, 0], type=pa.int64()),
            pa.array([None, None, None], type=pa.int64()),
        ],
        schema=arrow.schema,
    ).slice(0, 1)
    results["batch_corruption"] = [
        refused(lambda batch=batch: a.verify_batch(batch, arrow, producer))
        for batch in (wrong_schema, bad_null)
    ]
    results["batch_corruption"].append(
        refused(
            lambda: a.verify_batch(
                retained, arrow, producer, limits=a.BatchLimits(bytes=20)
            )
        )
    )
    # New reads must not reparse/re-emit. Genuine upstream verifier remains active.
    from pietto._project import (
        project_sql_emission as emission,
        project_sql_plan as planning,
        check,
    )

    original = (
        emission.emit_project_sql,
        planning.build_project_sql_plan,
        check.check_project_parse_only,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("read reconstructed authority")

    try:
        emission.emit_project_sql = planning.build_project_sql_plan = (
            check.check_project_parse_only
        ) = forbidden
        c.verify_result_contract(contract, checked)
        p.verify_producer_binding(producer, contract, artifact)
        a.verify_batch(owned, arrow, producer)
    finally:
        (
            emission.emit_project_sql,
            planning.build_project_sql_plan,
            check.check_project_parse_only,
        ) = original
    results["no_reconstruction"] = True
    results.update(run_contract_cases(root, built))
    results.update(run_scalar_cases(root))
    results.update(run_text_cases(root))
    results.update(run_decimal_cases(root))
    results.update(run_temporal_cases(root))
    results.update(run_finite_cases(root))
    results.update(run_reader_cases(root))
    results.update(run_interop_cases(root))
    results.update(run_ingress_cases(root))
    assert set(results) == set(CASES)
    return results


# Fixed S04 corpus; floats have an independent IEEE-754 byte oracle.
SCALAR_LABELS = (
    "renamed",
    "maybe_integer",
    "active",
    "maybe_flag",
    "measure",
    "maybe_ratio",
)
FLOAT_BITS = (
    "0000000000000000",
    "8000000000000000",
    "0000000000000000",
    "8000000000000000",
    "3fc0000000000000",
    "0000000000000001",
    "7fefffffffffffff",
)


def width_storage(target, bits):
    return {
        "postgres": {16: "pg_int2", 32: "pg_int4", 64: "pg_int8"},
        "mysql": {16: "my_smallint", 32: "my_int", 64: "my_bigint"},
    }[target][bits]


def width_fixture(directory, target, bits, *, lower=None, upper=None, checked=None):
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import bind_producer

    lower = -(1 << (bits - 1)) if lower is None else lower
    upper = (1 << (bits - 1)) - 1 if upper is None else upper
    if checked is None:
        checked = build_neutral(directory, {"main.pietto": source(target)})
    document = json.loads(emission_input(target, lower=lower, upper=upper))
    for field in document["sources"][0]["fields"]:
        field["representation"]["storage"]["kind"] = width_storage(target, bits)
    result = emit_project_sql(checked, json.dumps(document).encode())
    assert result.status == "VERIFIED" and result.artifact is not None
    contract = build_result_contract(checked)
    observed = tuple(
        replace(o, storage=width_storage(target, bits))
        for o in observations(target, lower=lower, upper=upper)
    )
    return (
        checked,
        result.artifact,
        contract,
        bind_producer(contract, result.artifact, observed),
    )


def scalar_fixture(directory, target, *, all_nullable=False):
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import (
        ProducerObservation,
        bind_producer,
    )

    names = ("integer", "maybe_integer", "flag", "maybe_flag", "ratio", "maybe_ratio")
    kinds = ("Int", "Int", "Bool", "Bool", "Float", "Float")
    text = "shape Row:\n" + "".join(
        f"    {name}: {kind} {'nullable' if all_nullable or i % 2 else 'not null'}\n"
        for i, (name, kind) in enumerate(zip(names, kinds, strict=True))
    )
    text += f'source rows: Row is {target}.table("opaque.result.fixture")\ntable result:\n    from rows\n    select:\n'
    text += "".join(
        f"        {label} = {name}\n"
        for label, name in zip(SCALAR_LABELS, names, strict=True)
    )
    checked = build_neutral(directory, {"main.pietto": text})
    contract = build_result_contract(checked)
    document = json.loads(emission_input(target))
    fields, observed = [], []
    for i, (name, kind, label) in enumerate(
        zip(names, kinds, SCALAR_LABELS, strict=True)
    ):
        if kind == "Int":
            storage, domain, carrier = (
                width_storage(target, 64),
                {"kind": "int_range", "min": str(LOW), "max": str(HIGH)},
                "int",
            )
            lower, upper = LOW, HIGH
        elif kind == "Bool":
            storage, domain = (
                ("pg_bool" if target == "postgres" else "my_bool01"),
                {"kind": "bool01"},
            )
            carrier = "bool" if target == "postgres" else "int01"
            lower = upper = None
        else:
            storage, domain, carrier = (
                ("pg_float8" if target == "postgres" else "my_double"),
                {"kind": "finite_float", "format": "binary64"},
                "float",
            )
            lower = upper = None
        fields.append(
            {
                "ordinal": i,
                "name": name,
                "column": name,
                "representation": {
                    "storage": {"kind": storage},
                    "nullable": bool(all_nullable or i % 2),
                    "domain": domain,
                },
            }
        )
        observed.append(
            ProducerObservation(
                i,
                label,
                target,
                storage,
                lower,
                upper,
                domain=domain["kind"],
                carrier=carrier,
            )
        )
    document["sources"][0]["fields"] = fields
    result = emit_project_sql(checked, json.dumps(document).encode())
    assert result.status == "VERIFIED" and result.artifact is not None
    producer = bind_producer(contract, result.artifact, tuple(observed))
    return checked, result.artifact, contract, producer


def scalar_rows(target):
    floats = (
        0.0,
        -0.0,
        0.0,
        -0.0,
        0.125,
        float.fromhex("0x0.0000000000001p-1022"),
        float.fromhex("0x1.fffffffffffffp+1023"),
    )
    integers = (BIG, BIG, -BIG, 0, -1, LOW, HIGH)
    return [
        [
            n,
            None if i % 2 else n,
            bool(i % 2) if target == "postgres" else i % 2,
            None if i % 2 else (True if target == "postgres" else 1),
            x,
            None if i % 2 else x,
        ]
        for i, (n, x) in enumerate(zip(integers, floats, strict=True))
    ]


def scalar_snapshot(batch):
    import struct

    return {
        "types": [str(f.type) for f in batch.schema],
        "labels": batch.schema.names,
        "nullable": [f.nullable for f in batch.schema],
        "columns": [
            [
                None if v is None else struct.pack(">d", v).hex() if i in (4, 5) else v
                for v in column.to_pylist()
            ]
            for i, column in enumerate(batch.columns)
        ],
    }


def scalar_value_oracle(snapshot):
    integers = [BIG, BIG, -BIG, 0, -1, LOW, HIGH]
    expected = {
        "types": ["int64", "int64", "bool", "bool", "double", "double"],
        "labels": list(SCALAR_LABELS),
        "nullable": [False, True, False, True, False, True],
        "columns": [
            integers,
            [n if i % 2 == 0 else None for i, n in enumerate(integers)],
            [False, True, False, True, False, True, False],
            [True, None, True, None, True, None, True],
            list(FLOAT_BITS),
            [x if i % 2 == 0 else None for i, x in enumerate(FLOAT_BITS)],
        ],
    }
    if not _exact(snapshot, expected):
        raise ValueError("scalar value/NULL/IEEE754 correspondence")


class CoercibleScalar:
    def __int__(self):
        raise AssertionError("implicit integer conversion")

    def __float__(self):
        raise AssertionError("implicit float conversion")

    def __bool__(self):
        raise AssertionError("implicit truthiness")


def run_scalar_cases(root):
    from decimal import Decimal
    from pietto._project import project_arrow_result as a, project_result_binding as p
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
    )
    from pietto._project import project_result_contract_pure_boundary as pure

    pa = importlib.import_module("pyarrow")
    widths, adaptation, mixed, negatives, batches, identities, documents = (
        {},
        {},
        {},
        {},
        {},
        {},
        {},
    )
    for target in ("postgres", "mysql"):
        for bits in (16, 32, 64):
            checked, artifact, contract, producer = width_fixture(
                root / f"{target}-{bits}", target, bits
            )
            low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            rows = [[low, None], [high, low], [0, high], [-1, 0], [low, None]]
            default = a.bind_arrow(producer)
            widened = a.bind_arrow(
                producer,
                integer_widths=tuple(
                    a.IntegerWidthRequest(f.field, 64) for f in producer.fields
                ),
            )
            normal, wide = (
                a.build_owned_batch(default, rows),
                a.build_owned_batch(widened, rows),
            )
            widths[f"{target}/{bits}"] = {
                "types": [str(f.type) for f in normal.schema],
                "wide_types": [str(f.type) for f in wide.schema],
                "columns": [col.to_pylist() for col in normal.columns],
                "wide_columns": [col.to_pylist() for col in wide.columns],
                "outside": refused(
                    lambda: a.build_owned_batch(default, [[high + 1, None]])
                ),
            }
        # Last loop's neutral root is retained across a different legal domain.
        before = export_result_contract(contract, checked).canonical_bytes
        _, _, narrow_contract, narrow_producer = width_fixture(
            root / "unused", target, 64, lower=-100, upper=100, checked=checked
        )
        assert (
            export_result_contract(narrow_contract, checked).canonical_bytes == before
        )
        selected = a.bind_arrow(
            narrow_producer,
            integer_widths=tuple(
                a.IntegerWidthRequest(f.field, 16) for f in narrow_producer.fields
            ),
        )
        selected_batch = a.build_owned_batch(
            selected, [[-100, None], [100, -100], [0, 100]]
        )
        original_batch = a.build_owned_batch(
            a.bind_arrow(narrow_producer), [[-100, None], [100, -100], [0, 100]]
        )
        invalid = (a.IntegerWidthRequest(producer.fields[0].field, 16), None)
        foreign = (a.IntegerWidthRequest(narrow_producer.fields[0].field, 16), None)
        edges = []
        for lower, upper in ((-32768, 32767), (-32769, 32767), (-32768, 32768)):
            _, _, _, edge = width_fixture(
                root / "unused-edge",
                target,
                64,
                lower=lower,
                upper=upper,
                checked=checked,
            )
            edge_requests = tuple(
                a.IntegerWidthRequest(f.field, 16) for f in edge.fields
            )
            if (lower, upper) == (-32768, 32767):
                edge_batch = a.build_owned_batch(
                    a.bind_arrow(edge, integer_widths=edge_requests),
                    [[-32768, None], [32767, 0]],
                )
                edges.append(
                    {
                        "types": [str(f.type) for f in edge_batch.schema],
                        "columns": [col.to_pylist() for col in edge_batch.columns],
                    }
                )
            else:
                edges.append(
                    refused(lambda: a.bind_arrow(edge, integer_widths=edge_requests))
                )
        r0, r1 = (a.IntegerWidthRequest(f.field, 64) for f in producer.fields)
        adaptation[target] = {
            "edges": edges,
            "types": [str(f.type) for f in selected_batch.schema],
            "default_types": [str(f.type) for f in original_batch.schema],
            "columns": [col.to_pylist() for col in selected_batch.columns],
            "default_columns": [col.to_pylist() for col in original_batch.columns],
            "refusals": [
                refused(lambda req=req: a.bind_arrow(producer, integer_widths=req))
                for req in (
                    (r0, r0),
                    (r1, r0),
                    (object(), None),
                    invalid,
                    foreign,
                    (),
                    [],
                    (a.IntegerWidthRequest(producer.fields[0].field, True), None),
                    (a.IntegerWidthRequest(producer.fields[0].field, 8), None),
                )
            ],
            "empty_small_independent": [
                refused(
                    lambda rows=rows: a.build_owned_batch(
                        a.bind_arrow(producer, integer_widths=invalid), rows
                    )
                )
                for rows in ([], [[0, None]])
            ],
        }
        checked, artifact, contract, producer = scalar_fixture(
            root / f"mixed-{target}", target
        )
        arrow = a.bind_arrow(producer)
        rows = scalar_rows(target)
        owned = a.build_owned_batch(arrow, rows)
        snapshot = scalar_snapshot(owned)
        scalar_value_oracle(snapshot)
        rows[0][:] = [0] * 6
        rows.clear()
        assert _exact(scalar_snapshot(owned), snapshot)
        mixed[target] = snapshot
        integer_bad = (True, 1.0, Decimal(1), "1", CoercibleScalar())
        bool_bad = (
            (0, 1, 2, -1, 0.0, "1", object())
            if target == "postgres"
            else (False, True, 2, -1, 0.0, "1", object())
        )
        bool_bad = (*bool_bad, CoercibleScalar())
        float_bad = (
            0,
            True,
            Decimal("0.125"),
            "0.125",
            float("nan"),
            float("inf"),
            float("-inf"),
            CoercibleScalar(),
        )
        negatives[target] = {}
        for kind, position, bad in (
            ("Int", 0, integer_bad),
            ("Bool", 2, bool_bad),
            ("Float", 4, float_bad),
        ):
            outcomes = []
            for value in bad:
                row = scalar_rows(target)[0]
                row[position] = value
                outcomes.append(
                    refused(lambda row=row: a.build_owned_batch(arrow, [row]))
                )
            row = scalar_rows(target)[0]
            row[position] = None
            outcomes.append(refused(lambda row=row: a.build_owned_batch(arrow, [row])))
            negatives[target][kind] = outcomes
        empty = a.build_owned_batch(arrow, [])
        _, _, _, nullable_producer = scalar_fixture(
            root / f"nulls-{target}", target, all_nullable=True
        )
        nulls = a.build_owned_batch(
            a.bind_arrow(nullable_producer), [[None] * 6, [None] * 6]
        )
        corrupt = []
        for index in (0, 2, 4):
            arrays = list(owned.columns)
            arrays[index] = pa.array([None] * 7, type=arrow.schema[index].type)
            bad = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
            corrupt.append(
                refused(lambda bad=bad: a.verify_batch(bad, arrow, producer))
            )
        for value in (float("nan"), float("inf"), float("-inf")):
            arrays = list(owned.columns)
            arrays[4] = pa.array([value] * 7, type=pa.float64(), from_pandas=False)
            bad = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
            corrupt.append(
                refused(lambda bad=bad: a.verify_batch(bad, arrow, producer))
            )
        wrong_schema = pa.RecordBatch.from_arrays(
            [pa.array([0], type=pa.int64())] * 6, names=list(SCALAR_LABELS)
        )
        corrupt.append(refused(lambda: a.verify_batch(wrong_schema, arrow, producer)))
        retained = owned.slice(0, 1)
        corrupt.append(
            refused(
                lambda: a.verify_batch(
                    retained, arrow, producer, limits=a.BatchLimits(bytes=60)
                )
            )
        )
        arrays = list(owned.columns)
        floats = arrays[4].to_pylist()
        floats[1] = 0.0
        arrays[4] = pa.array(floats, type=pa.float64())
        sign_flip = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
        a.verify_batch(sign_flip, arrow, producer)
        try:
            scalar_value_oracle(scalar_snapshot(sign_flip))
        except ValueError:
            sign_sensitive = "VALUE_CORRESPONDENCE"
        else:
            raise AssertionError("sign-flip value oracle did not discriminate")
        batches[target] = {
            "empty": scalar_snapshot(empty),
            "all_null": scalar_snapshot(nulls),
            "corruption": corrupt,
            "sign_flip": {"domain": "PASS", "value": sign_sensitive},
            "limits": [
                refused(
                    lambda limit=limit: a.build_owned_batch(
                        arrow, [scalar_rows(target)[0]], limits=limit
                    )
                )
                for limit in (
                    a.BatchLimits(fields=5),
                    a.BatchLimits(rows=0),
                    a.BatchLimits(bytes=53),
                )
            ],
        }
        bad_obs = replace(
            producer.fields[0].observation, storage=width_storage(target, 16)
        )
        damaged = replace(
            producer,
            fields=(
                replace(producer.fields[0], observation=bad_obs),
                *producer.fields[1:],
            ),
        )
        matching_schema = pa.schema(
            [
                pa.field(f.name, pa.int16() if i == 0 else f.type, nullable=f.nullable)
                for i, f in enumerate(arrow.schema)
            ]
        )
        coordinated = a.ArrowResultBinding(damaged, matching_schema)
        malformed = [
            refused(lambda fs=fs: a.bind_arrow(replace(producer, fields=fs)))
            for fs in (
                producer.fields[:-1],
                producer.fields[::-1],
                (producer.fields[0],) * 6,
            )
        ]
        malformed.append(refused(lambda: a.verify_arrow_binding(coordinated, damaged)))
        for index, updates in (
            (2, {"domain": "int_range"}),
            (2, {"carrier": "int"}),
            (4, {"domain": "bool01"}),
            (4, {"lower": 0}),
        ):
            observations_ = [f.observation for f in producer.fields]
            observations_[index] = replace(observations_[index], **updates)
            malformed.append(
                refused(
                    lambda obs=tuple(observations_): p.bind_producer(
                        contract, artifact, obs
                    )
                )
            )
        malformed.append(
            refused(
                lambda: a.bind_arrow(
                    producer,
                    integer_widths=(
                        None,
                        None,
                        a.IntegerWidthRequest(producer.fields[2].field, 16),
                        None,
                        None,
                        None,
                    ),
                )
            )
        )
        identities[target] = malformed
        exported = export_result_contract(contract, checked)
        verify_bound_export(exported, checked)
        assert (
            pure.encode_document(
                pure.decode_contract(exported.canonical_bytes).document
            )
            == exported.canonical_bytes
        )
        documents[target] = exported.canonical_bytes.decode()
    assert pure_child(documents) == {
        target: list(SCALAR_LABELS) for target in documents
    }
    return dict(
        integer_widths=widths,
        integer_adaptation=adaptation,
        scalar_mixed=mixed,
        scalar_refusals=negatives,
        scalar_batches=batches,
        scalar_identity=identities,
        scalar_codec=documents,
    )


def verify_scalar_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        for key in (
            "integer_adaptation",
            "scalar_mixed",
            "scalar_refusals",
            "scalar_batches",
            "scalar_identity",
            "scalar_codec",
        ):
            if set(cases[key]) != {"postgres", "mysql"}:
                raise ValueError("scalar target denominator")
        if set(cases["integer_widths"]) != {
            f"{t}/{w}" for t in ("postgres", "mysql") for w in (16, 32, 64)
        }:
            raise ValueError("integer width denominator")
        for target in ("postgres", "mysql"):
            for bits in (16, 32, 64):
                low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
                columns = [[low, high, 0, -1, low], [None, low, high, 0, None]]
                expected = {
                    "types": [f"int{bits}"] * 2,
                    "wide_types": ["int64"] * 2,
                    "columns": columns,
                    "wide_columns": columns,
                    "outside": "VALUE_DOMAIN",
                }
                if not _exact(cases["integer_widths"][f"{target}/{bits}"], expected):
                    raise ValueError("integer width/value evidence")
            columns = [[-100, 100, 0], [None, -100, 100]]
            expected = {
                "types": ["int16"] * 2,
                "default_types": ["int64"] * 2,
                "columns": columns,
                "default_columns": columns,
                "refusals": ["ARROW_ADAPTATION"] * 9,
                "edges": [
                    {
                        "types": ["int16", "int16"],
                        "columns": [[-32768, 32767], [None, 0]],
                    },
                    "ARROW_ADAPTATION",
                    "ARROW_ADAPTATION",
                ],
                "empty_small_independent": ["ARROW_ADAPTATION"] * 2,
            }
            if not _exact(cases["integer_adaptation"][target], expected):
                raise ValueError("domain-total adaptation evidence")
            scalar_value_oracle(cases["scalar_mixed"][target])
            if not _exact(
                cases["scalar_refusals"][target],
                {
                    "Int": ["VALUE_DOMAIN"] * 5 + ["NULL"],
                    "Bool": ["VALUE_DOMAIN"] * 8 + ["NULL"],
                    "Float": ["VALUE_DOMAIN"] * 8 + ["NULL"],
                },
            ):
                raise ValueError("exact scalar carrier evidence")
            empty = {
                "types": ["int64", "int64", "bool", "bool", "double", "double"],
                "labels": list(SCALAR_LABELS),
                "nullable": [False, True, False, True, False, True],
                "columns": [[] for _ in range(6)],
            }
            nulls = {
                **empty,
                "nullable": [True] * 6,
                "columns": [[None, None] for _ in range(6)],
            }
            expected = {
                "empty": empty,
                "all_null": nulls,
                "corruption": ["NULL"] * 3
                + ["VALUE_DOMAIN"] * 3
                + ["ARROW_SCHEMA", "LIMIT"],
                "sign_flip": {"domain": "PASS", "value": "VALUE_CORRESPONDENCE"},
                "limits": ["LIMIT"] * 3,
            }
            if not _exact(cases["scalar_batches"][target], expected):
                raise ValueError("scalar batch/ownership/resource evidence")
            if cases["scalar_identity"][target] != [
                "PRODUCER_ROOT",
                "PRODUCER_FIELDS",
                "PRODUCER_FIELDS",
            ] + ["PRODUCER_OBSERVATION"] * 5 + ["ARROW_ADAPTATION"]:
                raise ValueError("scalar binding identity evidence")
            view = pure.decode_contract(cases["scalar_codec"][target].encode())
            document = view.document
            if (
                [f["label"] for f in document["fields"]] != list(SCALAR_LABELS)
                or [f["canonical"] for f in document["fields"]]
                != [
                    {"kind": "builtin", "name": tag, "symbol": None}
                    for tag in ("Int", "Int", "Bool", "Bool", "Float", "Float")
                ]
                or [f["nullability"] for f in document["fields"]]
                != ["non_null", "nullable"] * 3
            ):
                raise ValueError("scalar neutral descriptor evidence")
    except (KeyError, TypeError, AttributeError, pure.ContractDocumentError) as exc:
        raise ValueError("scalar report evidence") from exc


# S05 fixtures and oracles remain inert when imported in the Arrow-free core.
TEXT_LABELS = ("renamed", "maybe_text", "number", "flag", "ratio")
TEXT_VALUES = (
    "",
    "a",
    "A",
    "中",
    "😀",
    "é",
    "e\u0301",
    "x",
    "x ",
    " \t",
    "repeat",
    "repeat",
    "abcdef中😀",
)
TEXT_HEX = (
    "",
    "61",
    "41",
    "e4b8ad",
    "f09f9880",
    "c3a9",
    "65cc81",
    "78",
    "7820",
    "2009",
    "726570656174",
    "726570656174",
    "616263646566e4b8adf09f9880",
)
TEXT_LENGTHS = (0, 1, 1, 1, 1, 1, 2, 1, 2, 2, 6, 6, 8)


def text_source(target, *, mixed=True, all_nullable=False):
    names = ("text", "maybe_text", "number", "flag", "ratio")[: 5 if mixed else 2]
    kinds = ("Text", "Text", "Int", "Bool", "Float")[: len(names)]
    source_ = "shape Row:\n" + "".join(
        f"    {name}: {kind} {'nullable' if all_nullable or i == 1 else 'not null'}\n"
        for i, (name, kind) in enumerate(zip(names, kinds, strict=True))
    )
    return (
        source_
        + f'source rows: Row is {target}.table("opaque.result.fixture")\ntable result:\n    from rows\n    select:\n'
        + "".join(
            f"        {label} = {name}\n"
            for label, name in zip(TEXT_LABELS[: len(names)], names, strict=True)
        )
    )


def text_input(target, *, mixed=True, all_nullable=False, maximum=8, length=8):
    doc = json.loads(emission_input(target, lower=-100, upper=100))
    storage = (
        {"kind": "pg_text"}
        if target == "postgres"
        else {"kind": "my_varchar", "length": length}
    )
    domain = dict(
        kind="text",
        max_characters=maximum,
        encoding="UTF8" if target == "postgres" else "utf8mb4",
        collation="C" if target == "postgres" else "utf8mb4_0900_bin",
        padding="NO PAD",
    )
    descriptions = [("text", storage, domain), ("maybe_text", storage, domain)]
    if mixed:
        descriptions += [
            (
                "number",
                {"kind": width_storage(target, 32)},
                {"kind": "int_range", "min": "-100", "max": "100"},
            ),
            (
                "flag",
                {"kind": "pg_bool" if target == "postgres" else "my_bool01"},
                {"kind": "bool01"},
            ),
            (
                "ratio",
                {"kind": "pg_float8" if target == "postgres" else "my_double"},
                {"kind": "finite_float", "format": "binary64"},
            ),
        ]
    doc["sources"][0]["fields"] = [
        dict(
            ordinal=i,
            name=name,
            column=name,
            representation=dict(
                storage=storage, nullable=bool(all_nullable or i == 1), domain=domain
            ),
        )
        for i, (name, storage, domain) in enumerate(descriptions)
    ]
    return json.dumps(doc).encode()


def text_observations(target, *, mixed=True, maximum=8, length=8):
    from pietto._project.project_result_binding import (
        ProducerObservation,
        TextObservation,
    )

    text = TextObservation(
        maximum,
        "UTF8" if target == "postgres" else "utf8mb4",
        "C" if target == "postgres" else "utf8mb4_0900_bin",
        "NO PAD",
        None if target == "postgres" else length,
    )
    observed = [
        ProducerObservation(
            i,
            label,
            target,
            "pg_text" if target == "postgres" else "my_varchar",
            domain="text",
            carrier="str",
            text=text,
        )
        for i, label in enumerate(TEXT_LABELS[:2])
    ]
    if mixed:
        observed += [
            ProducerObservation(
                2, "number", target, width_storage(target, 32), -100, 100
            ),
            ProducerObservation(
                3,
                "flag",
                target,
                "pg_bool" if target == "postgres" else "my_bool01",
                domain="bool01",
                carrier="bool" if target == "postgres" else "int01",
            ),
            ProducerObservation(
                4,
                "ratio",
                target,
                "pg_float8" if target == "postgres" else "my_double",
                domain="finite_float",
                carrier="float",
            ),
        ]
    return tuple(observed)


def text_fixture(
    directory, target, *, mixed=True, all_nullable=False, maximum=8, length=8
):
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import bind_producer

    checked = build_neutral(
        directory,
        {"main.pietto": text_source(target, mixed=mixed, all_nullable=all_nullable)},
    )
    result = emit_project_sql(
        checked,
        text_input(
            target,
            mixed=mixed,
            all_nullable=all_nullable,
            maximum=maximum,
            length=length,
        ),
    )
    assert result.status == "VERIFIED" and result.artifact is not None
    contract = build_result_contract(checked)
    producer = bind_producer(
        contract,
        result.artifact,
        text_observations(target, mixed=mixed, maximum=maximum, length=length),
    )
    return checked, result.artifact, contract, producer


def text_rows(target):
    return [
        [v, None if i % 2 == 0 else v, 7, True if target == "postgres" else 1, -0.0]
        for i, v in enumerate(TEXT_VALUES)
    ]


def text_arrow(producer, bits):
    from pietto._project import project_arrow_result as a

    count = len(producer.fields)
    requests = tuple(
        a.TextOffsetWidthRequest(f.field, bits) if i < 2 else None
        for i, f in enumerate(producer.fields)
    )
    integers = tuple(
        a.IntegerWidthRequest(f.field, 16) if i == 2 else None
        for i, f in enumerate(producer.fields)
    )
    return a.bind_arrow(
        producer,
        text_offset_widths=None if bits == 32 else requests,
        integer_widths=integers if count == 5 else None,
    )


def text_snapshot(batch):
    import struct

    columns = [col.to_pylist() for col in batch.columns]
    return dict(
        types=[str(f.type) for f in batch.schema],
        labels=batch.schema.names,
        nullable=[f.nullable for f in batch.schema],
        columns=[
            col
            if i != 4
            else [None if v is None else struct.pack(">d", v).hex() for v in col]
            for i, col in enumerate(columns)
        ],
        utf8=[
            [None if v is None else v.encode("utf-8").hex() for v in col]
            for col in columns[:2]
        ],
        codepoints=[
            [None if v is None else len(v) for v in col] for col in columns[:2]
        ],
    )


def text_expected(
    bits, *, mixed=True, state="values", all_nullable=False
) -> dict[str, Any]:
    # Literals are independent expectations, never derived from a product constructor.
    count = 5 if mixed else 2
    size = 13 if state == "values" else 0 if state == "empty" else 2
    columns = [
        list(TEXT_VALUES),
        [None if i % 2 == 0 else v for i, v in enumerate(TEXT_VALUES)],
        [7] * 13,
        [True] * 13,
        ["8000000000000000"] * 13,
    ][:count]
    utf8 = [list(TEXT_HEX), [None if i % 2 == 0 else v for i, v in enumerate(TEXT_HEX)]]
    lengths = [
        list(TEXT_LENGTHS),
        [None if i % 2 == 0 else v for i, v in enumerate(TEXT_LENGTHS)],
    ]
    if state != "values":
        columns = [[None] * size for _ in range(count)]
        utf8 = [[None] * size for _ in range(2)]
        lengths = [[None] * size for _ in range(2)]
    return dict(
        types=["string" if bits == 32 else "large_string"] * 2
        + (["int16", "bool", "double"] if mixed else []),
        labels=list(TEXT_LABELS[:count]),
        nullable=[bool(all_nullable or i == 1) for i in range(count)],
        columns=columns,
        utf8=utf8,
        codepoints=lengths,
    )


def text_value_oracle(snapshot, bits):
    if not _exact(snapshot, text_expected(bits)):
        raise ValueError("Text exact sequence/NULL/UTF8 correspondence")


class TextSubclass(str):
    pass


class CoercibleText:
    def __str__(self):
        raise AssertionError("implicit string conversion")


def run_text_cases(root):
    from pietto._project import project_arrow_result as a, project_result_binding as p
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
    )
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project.project_sql_emission import emit_project_sql
    import struct
    import unicodedata

    pa = importlib.import_module("pyarrow")

    class TextExtension(pa.ExtensionType):
        def __init__(self):
            super().__init__(pa.string(), "pietto.test.text")

        def __arrow_ext_serialize__(self):
            return b""

    results = {name: {} for name in CASES if name.startswith("text_")}
    for target in ("postgres", "mysql"):
        checked, artifact, contract, producer = text_fixture(
            root / f"text-{target}", target
        )
        initial = export_result_contract(contract, checked)
        verify_bound_export(initial, checked)
        results["text_codec"][target + "/mixed"] = initial.canonical_bytes.decode()
        observations_ = text_observations(target)
        observed_text = observations_[0].text
        assert observed_text is not None
        binding_negatives = {}
        for key, changes in {
            "max_characters": {"max_characters": 7},
            "encoding": {"encoding": "ASCII"},
            "collation": {"collation": "other"},
            "padding": {"padding": "PAD SPACE"},
            "storage_length": {"storage_length": 7},
            "bool_max": {"max_characters": True},
            "bool_length": {"storage_length": True},
        }.items():
            bad = replace(observations_[0], text=replace(observed_text, **changes))
            binding_negatives[key] = refused(
                lambda bad=bad: p.bind_producer(
                    contract, artifact, (bad, *observations_[1:])
                )
            )
        for key, changes in {
            "ordinal": {"ordinal": 1},
            "label": {"label": "text"},
            "family": {"family": "foreign"},
            "storage": {"storage": "binary"},
            "lower": {"lower": 0},
            "upper": {"upper": 1},
            "carrier": {"carrier": "int"},
            "domain": {"domain": "int_range"},
            "missing_text": {"text": None},
        }.items():
            binding_negatives[key] = refused(
                lambda changes=changes: p.bind_producer(
                    contract,
                    artifact,
                    (replace(observations_[0], **changes), *observations_[1:]),
                )
            )
        for key, fields in {
            "tail": producer.fields[:-1],
            "reordered": producer.fields[::-1],
            "duplicated": (producer.fields[0],) * 5,
        }.items():
            binding_negatives[key] = refused(
                lambda fields=fields: a.bind_arrow(replace(producer, fields=fields))
            )
        foreign_checked, foreign_artifact, _, foreign_producer = text_fixture(
            root / f"text-foreign-{target}", target
        )
        binding_negatives["foreign_root"] = refused(
            lambda: p.bind_producer(contract, foreign_artifact, observations_)
        )
        binding_negatives["foreign_field"] = refused(
            lambda: a.bind_arrow(
                replace(
                    producer,
                    fields=(
                        replace(
                            producer.fields[0], field=foreign_producer.fields[0].field
                        ),
                        *producer.fields[1:],
                    ),
                )
            )
        )
        coordinated = replace(
            producer,
            fields=(
                replace(
                    producer.fields[0],
                    observation=replace(
                        observations_[0],
                        text=replace(observed_text, max_characters=7),
                    ),
                ),
                *producer.fields[1:],
            ),
        )
        binding_negatives["coordinated"] = refused(
            lambda: a.verify_arrow_binding(
                a.ArrowResultBinding(coordinated, text_arrow(producer, 32).schema),
                coordinated,
            )
        )
        bad_input = json.loads(text_input(target))
        bad_input["sources"][0]["fields"][0]["representation"]["domain"][
            "collation"
        ] = "unsupported"
        blocked = emit_project_sql(checked, json.dumps(bad_input).encode())
        assert blocked.status == "BLOCKED" and blocked.artifact is None
        altered = emit_project_sql(checked, text_input(target, maximum=7, length=9))
        assert altered.status == "VERIFIED" and altered.artifact is not None
        alternate = p.bind_producer(
            contract, altered.artifact, text_observations(target, maximum=7, length=9)
        )
        assert (
            alternate.contract is contract
            and export_result_contract(contract, checked).canonical_bytes
            == initial.canonical_bytes
        )
        results["text_binding"][target] = dict(
            refusals=binding_negatives,
            upstream=blocked.status,
            same_contract=True,
            descriptors=[
                dict(
                    storage=f.observation.storage,
                    maximum=cast(p.TextObservation, f.observation.text).max_characters,
                    encoding=cast(p.TextObservation, f.observation.text).encoding,
                    collation=cast(p.TextObservation, f.observation.text).collation,
                    padding=cast(p.TextObservation, f.observation.text).padding,
                    length=cast(p.TextObservation, f.observation.text).storage_length,
                )
                for f in producer.fields[:2]
            ],
        )
        r0, r1 = (a.TextOffsetWidthRequest(f.field, 64) for f in producer.fields[:2])
        requests = [
            (),
            [],
            (r0,),
            (r0, r1, None, None, None, None),
            (r0, r0, None, None, None),
            (r1, r0, None, None, None),
            (
                a.TextOffsetWidthRequest(foreign_producer.fields[0].field, 64),
                r1,
                None,
                None,
                None,
            ),
            (
                r0,
                r1,
                a.TextOffsetWidthRequest(producer.fields[2].field, 64),
                None,
                None,
            ),
            (a.TextOffsetWidthRequest(r0.field, True), r1, None, None, None),
            (a.TextOffsetWidthRequest(r0.field, 16), r1, None, None, None),
            (a.IntegerWidthRequest(r0.field, 32), r1, None, None, None),
        ]
        results["text_requests"][target] = [
            refused(lambda req=req: a.bind_arrow(producer, text_offset_widths=req))
            for req in requests
        ]
        two_checked, _, two_contract, two = text_fixture(
            root / f"text-only-{target}", target, mixed=False
        )
        exported = export_result_contract(two_contract, two_checked)
        verify_bound_export(exported, two_checked)
        results["text_codec"][target + "/text"] = exported.canonical_bytes.decode()
        _, _, _, nullable = text_fixture(
            root / f"text-null-{target}", target, mixed=False, all_nullable=True
        )
        _, _, _, zero = text_fixture(
            root / f"text-zero-{target}", target, mixed=False, maximum=0
        )
        _, _, _, single = text_fixture(
            root / f"text-single-{target}", target, mixed=False, maximum=1
        )
        _, _, _, declared = text_fixture(
            root / f"text-declared-{target}",
            target,
            mixed=False,
            maximum=10**12 if target == "postgres" else 16383,
            length=16383,
        )
        for bits in (32, 64):
            key = f"{target}/{bits}"
            arrow = text_arrow(producer, bits)
            rows = text_rows(target)
            owned = a.build_owned_batch(arrow, rows)
            actual = text_snapshot(owned)
            text_value_oracle(actual, bits)
            rows[0][:] = [None] * 5
            rows.clear()
            assert _exact(text_snapshot(owned), actual)
            assert (
                export_result_contract(contract, checked).canonical_bytes
                == initial.canonical_bytes
            )
            explicit32 = tuple(
                a.TextOffsetWidthRequest(f.field, bits) if i < 2 else None
                for i, f in enumerate(producer.fields)
            )
            explicit = a.bind_arrow(
                producer,
                text_offset_widths=explicit32,
                integer_widths=arrow.integer_widths,
            )
            assert explicit.schema.equals(arrow.schema)
            results["text_values"][key] = actual
            small = text_arrow(two, bits)
            bad_values = (
                b"a",
                bytearray(b"a"),
                memoryview(b"a"),
                1,
                True,
                1.0,
                TextSubclass("a"),
                CoercibleText(),
                "\ud800",
                "\udfff",
                "abcdef中😀x",
            )
            empties: dict[str, Any] = dict(
                empty=text_snapshot(a.build_owned_batch(small, [])),
                all_null=text_snapshot(
                    a.build_owned_batch(
                        text_arrow(nullable, bits), [[None, None], [None, None]]
                    )
                ),
                zero=a.build_owned_batch(text_arrow(zero, bits), [["", None]])
                .column(0)
                .to_pylist(),
                refusals=[
                    refused(lambda v=v: a.build_owned_batch(small, [[v, None]]))
                    for v in bad_values
                ]
                + [
                    refused(lambda: a.build_owned_batch(small, [[None, None]])),
                    refused(
                        lambda: a.build_owned_batch(
                            text_arrow(zero, bits), [["a", None]]
                        )
                    ),
                ],
            )
            if target == "postgres":
                empties["nul"] = refused(
                    lambda: a.build_owned_batch(small, [["a\0b", None]])
                )
            else:
                empties["nul"] = (
                    a.build_owned_batch(small, [["a\0b", None]]).column(0).to_pylist()
                )
            one = text_arrow(single, bits)
            empties["domain_edges"] = {
                "single": a.build_owned_batch(
                    one, [["é", None], ["中", None], ["😀", None]]
                )
                .column(0)
                .to_pylist(),
                "combining": refused(
                    lambda: a.build_owned_batch(one, [["e\u0301", None]])
                ),
                "declared": a.build_owned_batch(
                    text_arrow(declared, bits),
                    [["a", None]],
                    limits=a.BatchLimits(bytes=19 if bits == 32 else 35),
                )
                .column(0)
                .to_pylist(),
            }
            empties["mixed_impersonation"] = [
                refused(
                    lambda: a.build_owned_batch(
                        arrow, [[1, None, 7, True if target == "postgres" else 1, -0.0]]
                    )
                ),
                refused(
                    lambda: a.build_owned_batch(
                        arrow,
                        [["a", None, "7", True if target == "postgres" else 1, -0.0]],
                    )
                ),
            ]
            results["text_empty_null"][key] = empties
            allowance = 21 if bits == 32 else 37
            exact = a.build_owned_batch(
                small, [["中", None]], limits=a.BatchLimits(bytes=allowance)
            )
            a.verify_batch(exact, small, two, limits=a.BatchLimits(bytes=allowance))
            mixed = a.build_owned_batch(
                arrow,
                [["中", None, 7, True if target == "postgres" else 1, -0.0]],
                limits=a.BatchLimits(bytes=allowance + 27),
            )
            retained_array = pa.array(
                ["a" * 64, "中", ""], type=small.schema[0].type
            ).slice(1, 1)
            retained = pa.RecordBatch.from_arrays(
                [retained_array, pa.array([None], type=small.schema[1].type)],
                schema=small.schema,
            )
            results["text_resources"][key] = dict(
                allowance=allowance,
                columns=[c.to_pylist() for c in exact.columns],
                mixed_allowance=allowance + 27,
                mixed_rows=mixed.num_rows,
                refusals=[
                    refused(
                        lambda: a.build_owned_batch(
                            small,
                            [["中", None]],
                            limits=a.BatchLimits(bytes=allowance - 1),
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(
                            small,
                            [["中a", None]],
                            limits=a.BatchLimits(bytes=allowance),
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(
                            small, [], limits=a.BatchLimits(bytes=bits // 4 - 1)
                        )
                    ),
                    refused(
                        lambda: a.verify_batch(
                            retained, small, two, limits=a.BatchLimits(bytes=allowance)
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(
                            arrow,
                            [
                                [
                                    "中",
                                    None,
                                    7,
                                    True if target == "postgres" else 1,
                                    -0.0,
                                ]
                            ],
                            limits=a.BatchLimits(bytes=allowance + 26),
                        )
                    ),
                ],
            )
            # Full allocated buffers only. NULL payload may contain unspecified non-UTF8 bytes.
            ty = small.schema[0].type
            fmt = "i" if bits == 32 else "q"
            invalid_retained = pa.Array.from_buffers(
                ty,
                1,
                [
                    None,
                    pa.py_buffer(struct.pack("<2" + fmt, 0, 1)),
                    pa.py_buffer(b"\xff" + b"a" * 64),
                ],
            )
            invalid_batch = pa.RecordBatch.from_arrays(
                [invalid_retained, pa.array([None], type=ty)], schema=small.schema
            )
            results["text_resources"][key]["before_validation"] = refused(
                lambda: a.verify_batch(
                    invalid_batch, small, two, limits=a.BatchLimits(bytes=allowance)
                )
            )
            array = pa.Array.from_buffers(
                ty,
                3,
                [
                    pa.py_buffer(b"\x05"),
                    pa.py_buffer(struct.pack("<4" + fmt, 0, 1, 2, 5)),
                    pa.py_buffer(b"a\xff\xe4\xb8\xad"),
                ],
            )
            nullslice = array.slice(1, 2)
            supplied = pa.RecordBatch.from_arrays(
                [pa.array(["skip", "", "中"], type=ty).slice(1, 2), nullslice],
                schema=small.schema,
            )
            a.verify_batch(supplied, small, two)
            malformed = []
            for offsets, payload in [
                ((0, 2, 1), b"ab"),
                ((0, 1), b"\xff"),
                ((-1, 1), b"ab"),
                ((0, 3), b"a"),
            ]:
                try:
                    badarray = pa.Array.from_buffers(
                        ty,
                        len(offsets) - 1,
                        [
                            None,
                            pa.py_buffer(
                                struct.pack("<" + str(len(offsets)) + fmt, *offsets)
                            ),
                            pa.py_buffer(payload),
                        ],
                    )
                except (ValueError, pa.ArrowException):
                    malformed.append("CONSTRUCTOR")
                    continue
                badbatch = pa.RecordBatch.from_arrays(
                    [badarray, pa.array([None] * len(badarray), type=ty)],
                    schema=small.schema,
                )
                malformed.append(refused(lambda: a.verify_batch(badbatch, small, two)))
            schema_bad = []
            for wrong in (
                pa.large_string() if bits == 32 else pa.string(),
                pa.binary(),
                pa.large_binary(),
                pa.dictionary(pa.int8(), pa.string()),
                pa.string_view(),
                pa.list_(pa.string()),
                TextExtension(),
            ):
                schema = pa.schema(
                    [pa.field("renamed", wrong, nullable=False), small.schema[1]]
                )
                schema_bad.append(
                    refused(
                        lambda schema=schema: a.verify_arrow_binding(
                            replace(small, schema=schema), two
                        )
                    )
                )
            schema_bad += [
                refused(
                    lambda: a.verify_batch(
                        supplied.replace_schema_metadata({b"collation": b"authority"}),
                        small,
                        two,
                    )
                ),
                refused(
                    lambda: a.verify_arrow_binding(
                        replace(
                            small,
                            schema=pa.schema(
                                [
                                    small.schema[0].with_metadata({b"collation": b"C"}),
                                    small.schema[1],
                                ]
                            ),
                        ),
                        two,
                    )
                ),
            ]
            supplied_domain = []
            for value in ("abcdef中😀x", None) + (
                ("a\0b",) if target == "postgres" else ()
            ):
                bad = pa.RecordBatch.from_arrays(
                    [pa.array([value], type=ty), pa.array([None], type=ty)],
                    schema=small.schema,
                )
                supplied_domain.append(refused(lambda: a.verify_batch(bad, small, two)))
            results["text_supplied"][key] = dict(
                domain_refusals=supplied_domain,
                offsets=[col.offset for col in supplied.columns],
                columns=[col.to_pylist() for col in supplied.columns],
                malformed=malformed,
                schema_refusals=schema_bad,
            )
            substitutions = []
            for index, value in [
                (1, "b"),
                (2, "a"),
                (6, unicodedata.normalize("NFC", TEXT_VALUES[6])),
                (8, "x"),
            ]:
                arrays = list(owned.columns)
                values = arrays[0].to_pylist()
                values[index] = value
                arrays[0] = pa.array(values, type=arrow.schema[0].type)
                changed = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
                a.verify_batch(changed, arrow, producer)
                try:
                    text_value_oracle(text_snapshot(changed), bits)
                except ValueError:
                    substitutions.append("VALUE_CORRESPONDENCE")
                else:
                    raise AssertionError("domain-valid substitution escaped oracle")
            for change in ("null", "order", "multiplicity"):
                arrays = list(owned.columns)
                if change == "null":
                    values = arrays[1].to_pylist()
                    values[0] = ""
                    arrays[1] = pa.array(values, type=arrow.schema[1].type)
                else:
                    indices = list(range(13))
                    indices[1:3] = [2, 1] if change == "order" else [1, 1]
                    arrays = [col.take(indices) for col in arrays]
                changed = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
                a.verify_batch(changed, arrow, producer)
                try:
                    text_value_oracle(text_snapshot(changed), bits)
                except ValueError:
                    substitutions.append("VALUE_CORRESPONDENCE")
                else:
                    raise AssertionError("sequence mutation escaped oracle")
            original_builder = a.build_owned_batch

            def injected(binding, rows, **kwargs):
                damaged_rows = [list(row) for row in rows]
                damaged_rows[1][0] = "b"
                return original_builder(binding, damaged_rows, **kwargs)

            try:
                a.build_owned_batch = injected
                try:
                    text_value_oracle(
                        text_snapshot(a.build_owned_batch(arrow, text_rows(target))),
                        bits,
                    )
                except ValueError:
                    substitutions.append("VALUE_CORRESPONDENCE")
                else:
                    raise AssertionError("injected builder escaped external oracle")
            finally:
                a.build_owned_batch = original_builder
            shortened = owned.slice(0, 12)
            a.verify_batch(shortened, arrow, producer)
            try:
                text_value_oracle(text_snapshot(shortened), bits)
            except ValueError:
                substitutions.append("VALUE_CORRESPONDENCE")
            else:
                raise AssertionError("valid prefix escaped exact value oracle")
            per_field = a.bind_arrow(
                two,
                text_offset_widths=(
                    a.TextOffsetWidthRequest(two.fields[0].field, 64),
                    None,
                ),
            )
            per_field_batch = a.build_owned_batch(per_field, [["中", "é"]])
            results["text_supplied"][key]["per_field"] = {
                "types": [str(f.type) for f in per_field_batch.schema],
                "columns": [col.to_pylist() for col in per_field_batch.columns],
            }
            results["text_value_substitution"][key] = substitutions
    for data in results["text_codec"].values():
        assert (
            pure.encode_document(pure.decode_contract(data.encode()).document)
            == data.encode()
        )
    return results


def verify_text_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        keys = {
            f"{target}/{bits}" for target in ("postgres", "mysql") for bits in (32, 64)
        }
        for name in (
            "text_values",
            "text_empty_null",
            "text_resources",
            "text_supplied",
            "text_value_substitution",
        ):
            if set(cases[name]) != keys:
                raise ValueError("Text width/target denominator")
        for name in ("text_binding", "text_requests"):
            if set(cases[name]) != {"postgres", "mysql"}:
                raise ValueError("Text target denominator")
        if set(cases["text_codec"]) != {
            f"{t}/{k}" for t in ("postgres", "mysql") for k in ("text", "mixed")
        }:
            raise ValueError("Text canonical denominator")
        for target in ("postgres", "mysql"):
            observation_keys = (
                "max_characters",
                "encoding",
                "collation",
                "padding",
                "storage_length",
                "bool_max",
                "bool_length",
                "ordinal",
                "label",
                "family",
                "storage",
                "lower",
                "upper",
                "carrier",
                "domain",
                "missing_text",
                "coordinated",
            )
            expected_binding = dict(
                refusals={
                    **dict.fromkeys(observation_keys, "PRODUCER_OBSERVATION"),
                    "tail": "PRODUCER_ROOT",
                    "reordered": "PRODUCER_FIELDS",
                    "duplicated": "PRODUCER_FIELDS",
                    "foreign_root": "ROOT",
                    "foreign_field": "PRODUCER_FIELDS",
                },
                upstream="BLOCKED",
                same_contract=True,
                descriptors=[
                    dict(
                        storage="pg_text" if target == "postgres" else "my_varchar",
                        maximum=8,
                        encoding="UTF8" if target == "postgres" else "utf8mb4",
                        collation="C" if target == "postgres" else "utf8mb4_0900_bin",
                        padding="NO PAD",
                        length=None if target == "postgres" else 8,
                    )
                ]
                * 2,
            )
            if not _exact(cases["text_binding"][target], expected_binding):
                raise ValueError("Text producer authority evidence")
            if cases["text_requests"][target] != ["ARROW_ADAPTATION"] * 11:
                raise ValueError("Text positional request evidence")
            for bits in (32, 64):
                key = f"{target}/{bits}"
                text_value_oracle(cases["text_values"][key], bits)
                expected_empty: dict[str, Any] = dict(
                    empty=text_expected(bits, mixed=False, state="empty"),
                    all_null=text_expected(
                        bits, mixed=False, state="null", all_nullable=True
                    ),
                    zero=[""],
                    refusals=["VALUE_DOMAIN"] * 11 + ["NULL", "VALUE_DOMAIN"],
                    nul="VALUE_DOMAIN" if target == "postgres" else ["a\0b"],
                )
                expected_empty["domain_edges"] = {
                    "single": ["é", "中", "😀"],
                    "combining": "VALUE_DOMAIN",
                    "declared": ["a"],
                }
                expected_empty["mixed_impersonation"] = ["VALUE_DOMAIN"] * 2
                allowance = 21 if bits == 32 else 37
                expected_resources = dict(
                    before_validation="LIMIT",
                    allowance=allowance,
                    columns=[["中"], [None]],
                    mixed_allowance=allowance + 27,
                    mixed_rows=1,
                    refusals=["LIMIT"] * 5,
                )
                expected_supplied = dict(
                    domain_refusals=["VALUE_DOMAIN", "NULL"]
                    + (["VALUE_DOMAIN"] if target == "postgres" else []),
                    per_field={
                        "types": ["large_string", "string"],
                        "columns": [["中"], ["é"]],
                    },
                    offsets=[1, 1],
                    columns=[["", "中"], [None, "中"]],
                    malformed=[
                        "ARROW_BATCH",
                        "ARROW_BATCH",
                        "CONSTRUCTOR",
                        "CONSTRUCTOR",
                    ],
                    schema_refusals=["ARROW_BINDING"] * 7
                    + ["ARROW_SCHEMA", "ARROW_BINDING"],
                )
                for name, expected in (
                    ("text_empty_null", expected_empty),
                    ("text_resources", expected_resources),
                    ("text_supplied", expected_supplied),
                    ("text_value_substitution", ["VALUE_CORRESPONDENCE"] * 9),
                ):
                    if not _exact(cases[name][key], expected):
                        raise ValueError("Text " + name + " evidence")
            for kind in ("text", "mixed"):
                data = cases["text_codec"][target + "/" + kind]
                view = pure.decode_contract(data.encode())
                count = 2 if kind == "text" else 5
                if (
                    [f["label"] for f in view.document["fields"]]
                    != list(TEXT_LABELS[:count])
                    or [f["canonical"] for f in view.document["fields"]]
                    != [
                        dict(kind="builtin", name=tag, symbol=None)
                        for tag in ("Text", "Text", "Int", "Bool", "Float")[:count]
                    ]
                    or [f["nullability"] for f in view.document["fields"]]
                    != ["nullable" if i == 1 else "non_null" for i in range(count)]
                ):
                    raise ValueError("Text neutral descriptor evidence")
    except (KeyError, TypeError, AttributeError, pure.ContractDocumentError) as exc:
        raise ValueError("Text report evidence") from exc


# S06 fixture coefficients and expectations do not use the product conversion helper.
DECIMAL_PAIRS = ((1, 0), (3, 3), (9, 2), (38, 0), (39, 4), (65, 30))
DECIMAL_LABELS = ("renamed", "optional", "number", "flag", "ratio", "label")


def decimal_source(target, precision, scale, *, mixed=False, all_nullable=False):
    kinds = [
        f"Decimal({precision}, {scale})",
        "Decimal(65, 30)" if mixed else f"Decimal({precision}, {scale})",
    ]
    if mixed:
        kinds += ["Int", "Bool", "Float", "Text"]
    names = ("amount", *DECIMAL_LABELS[1 : len(kinds)])
    text = "shape Row:\n" + "".join(
        f"    {name}: {kind} {'nullable' if all_nullable or i in (1, 5) else 'not null'}\n"
        for i, (name, kind) in enumerate(zip(names, kinds, strict=True))
    )
    return (
        text
        + f'source rows: Row is {target}.table("opaque.result.fixture")\ntable result:\n    from rows\n    select:\n'
        + "".join(
            f"        {label} = {name}\n"
            for label, name in zip(DECIMAL_LABELS[: len(kinds)], names, strict=True)
        )
    )


def decimal_input(target, precision, scale, *, mixed=False, all_nullable=False):
    doc = json.loads(emission_input(target))
    pairs = [(precision, scale), (65, 30) if mixed else (precision, scale)]
    descriptions = [
        (
            "amount" if i == 0 else "optional",
            dict(
                kind="pg_numeric" if target == "postgres" else "my_decimal",
                precision=p,
                scale=s,
            ),
            dict(kind="decimal", precision=p, scale=s),
        )
        for i, (p, s) in enumerate(pairs)
    ]
    if mixed:
        descriptions += [
            (
                "number",
                dict(kind=width_storage(target, 32)),
                dict(kind="int_range", min="-100", max="100"),
            ),
            (
                "flag",
                dict(kind="pg_bool" if target == "postgres" else "my_bool01"),
                dict(kind="bool01"),
            ),
            (
                "ratio",
                dict(kind="pg_float8" if target == "postgres" else "my_double"),
                dict(kind="finite_float", format="binary64"),
            ),
            (
                "label",
                dict(kind="pg_text")
                if target == "postgres"
                else dict(kind="my_varchar", length=8),
                dict(
                    kind="text",
                    max_characters=8,
                    encoding="UTF8" if target == "postgres" else "utf8mb4",
                    collation="C" if target == "postgres" else "utf8mb4_0900_bin",
                    padding="NO PAD",
                ),
            ),
        ]
    doc["sources"][0]["fields"] = [
        dict(
            ordinal=i,
            name=name,
            column=name,
            representation=dict(
                storage=storage,
                nullable=bool(all_nullable or i in (1, 5)),
                domain=domain,
            ),
        )
        for i, (name, storage, domain) in enumerate(descriptions)
    ]
    return json.dumps(doc).encode()


def decimal_observations(target, precision, scale, *, mixed=False):
    from pietto._project.project_result_binding import (
        DecimalObservation,
        ProducerObservation,
        TextObservation,
    )

    observed = [
        ProducerObservation(
            i,
            DECIMAL_LABELS[i],
            target,
            "pg_numeric" if target == "postgres" else "my_decimal",
            domain="decimal",
            carrier="decimal",
            decimal=DecimalObservation(p, s),
        )
        for i, (p, s) in enumerate(
            ((precision, scale), (65, 30) if mixed else (precision, scale))
        )
    ]
    if mixed:
        observed += [
            ProducerObservation(
                2, "number", target, width_storage(target, 32), -100, 100
            ),
            ProducerObservation(
                3,
                "flag",
                target,
                "pg_bool" if target == "postgres" else "my_bool01",
                domain="bool01",
                carrier="bool" if target == "postgres" else "int01",
            ),
            ProducerObservation(
                4,
                "ratio",
                target,
                "pg_float8" if target == "postgres" else "my_double",
                domain="finite_float",
                carrier="float",
            ),
            ProducerObservation(
                5,
                "label",
                target,
                "pg_text" if target == "postgres" else "my_varchar",
                domain="text",
                carrier="str",
                text=TextObservation(
                    8,
                    "UTF8" if target == "postgres" else "utf8mb4",
                    "C" if target == "postgres" else "utf8mb4_0900_bin",
                    "NO PAD",
                    None if target == "postgres" else 8,
                ),
            ),
        ]
    return tuple(observed)


def decimal_fixture(
    directory, target, precision, scale, *, mixed=False, all_nullable=False
):
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import bind_producer

    checked = build_neutral(
        directory,
        {
            "main.pietto": decimal_source(
                target, precision, scale, mixed=mixed, all_nullable=all_nullable
            )
        },
    )
    result = emit_project_sql(
        checked,
        decimal_input(target, precision, scale, mixed=mixed, all_nullable=all_nullable),
    )
    assert result.status == "VERIFIED" and result.artifact is not None
    neutral = build_result_contract(checked)
    producer = bind_producer(
        neutral,
        result.artifact,
        decimal_observations(target, precision, scale, mixed=mixed),
    )
    return checked, result.artifact, neutral, producer


def decimal_literal(coefficient, scale, *, trailing=0, negative_zero=False):
    from decimal import Decimal

    digits = tuple(int(c) for c in str(abs(coefficient))) + (0,) * trailing
    return Decimal((int(coefficient < 0 or negative_zero), digits, -scale - trailing))


def decimal_rows(target, precision, scale, *, mixed=False):
    maximum = 10**precision - 1
    other_max = 10**65 - 1 if mixed else maximum
    other_scale = 30 if mixed else scale
    coefficients = (maximum, -maximum, 0, 1, 1, -1)
    others = (None, other_max, 0, None, 1, -1)
    return [
        [
            decimal_literal(
                k, scale, trailing=2 if i == 4 else 0, negative_zero=i == 2
            ),
            None if other is None else decimal_literal(other, other_scale),
        ]
        + (
            [7, True if target == "postgres" else 1, -0.0, "é" if i % 2 else None]
            if mixed
            else []
        )
        for i, (k, other) in enumerate(zip(coefficients, others, strict=True))
    ]


def decimal_arrow(producer, *, bits=None, mixed=False):
    from pietto._project import project_arrow_result as a

    decimal_widths = (
        None
        if bits is None
        else tuple(
            a.DecimalWidthRequest(f.field, bits) if i < 2 else None
            for i, f in enumerate(producer.fields)
        )
    )
    return a.bind_arrow(
        producer,
        decimal_widths=decimal_widths,
        integer_widths=tuple(
            a.IntegerWidthRequest(f.field, 16) if i == 2 else None
            for i, f in enumerate(producer.fields)
        )
        if mixed
        else None,
        text_offset_widths=tuple(
            a.TextOffsetWidthRequest(f.field, 64) if i == 5 else None
            for i, f in enumerate(producer.fields)
        )
        if mixed
        else None,
    )


def decimal_snapshot(batch):
    import struct

    pa = importlib.import_module("pyarrow")
    columns, descriptors = [], []
    for i, column in enumerate(batch.columns):
        if pa.types.is_decimal(column.type):
            width = column.type.bit_width // 8
            data = memoryview(column.buffers()[1])
            # Independent reading of signed scaled coefficients and validity, including offsets.
            columns.append(
                [
                    str(
                        int.from_bytes(
                            data[
                                (column.offset + j) * width : (column.offset + j + 1)
                                * width
                            ],
                            "little",
                            signed=True,
                        )
                    )
                    if column[j].is_valid
                    else None
                    for j in range(len(column))
                ]
            )
            descriptors.append(
                dict(
                    ordinal=i,
                    precision=column.type.precision,
                    scale=column.type.scale,
                    bits=column.type.bit_width,
                )
            )
        else:
            values = column.to_pylist()
            columns.append(
                [None if v is None else struct.pack(">d", v).hex() for v in values]
                if i == 4
                else values
            )
    return dict(
        types=[str(f.type) for f in batch.schema],
        labels=batch.schema.names,
        nullable=[f.nullable for f in batch.schema],
        decimal=descriptors,
        columns=columns,
    )


def decimal_expected(
    precision, scale, *, bits=None, mixed=False, state="values", all_nullable=False
) -> dict[str, Any]:
    pairs = [(precision, scale), (65, 30) if mixed else (precision, scale)]
    descriptors = [
        dict(ordinal=i, precision=p, scale=s, bits=bits or (128 if p <= 38 else 256))
        for i, (p, s) in enumerate(pairs)
    ]
    maximum, other_max = 10**precision - 1, 10 ** pairs[1][0] - 1
    columns: list[list[Any]] = [
        [str(k) for k in (maximum, -maximum, 0, 1, 1, -1)],
        [None, str(other_max), "0", None, "1", "-1"],
    ]
    if mixed:
        columns += [
            [7] * 6,
            [True] * 6,
            ["8000000000000000"] * 6,
            [None, "é", None, "é", None, "é"],
        ]
    if state != "values":
        columns = [[None] * (0 if state == "empty" else 2) for _ in columns]
    return dict(
        types=[
            f"decimal{d['bits']}({d['precision']}, {d['scale']})" for d in descriptors
        ]
        + (["int16", "bool", "double", "large_string"] if mixed else []),
        labels=list(DECIMAL_LABELS[: len(columns)]),
        nullable=[bool(all_nullable or i in (1, 5)) for i in range(len(columns))],
        decimal=descriptors,
        columns=columns,
    )


def decimal_value_oracle(snapshot, precision, scale, **kwargs):
    if not _exact(snapshot, decimal_expected(precision, scale, **kwargs)):
        raise ValueError("Decimal exact scaled coefficient/scale/NULL correspondence")


def decimal_context_snapshot(context):
    return dict(
        precision=context.prec,
        rounding=context.rounding,
        emin=context.Emin,
        emax=context.Emax,
        capitals=context.capitals,
        clamp=context.clamp,
        flags={k.__name__: v for k, v in context.flags.items()},
        traps={k.__name__: v for k, v in context.traps.items()},
    )


def run_decimal_cases(root):
    from decimal import Decimal, localcontext, getcontext, ROUND_DOWN, ROUND_UP, Rounded
    from pietto._project import project_arrow_result as a, project_result_binding as p
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
    )
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project.project_sql_emission import emit_project_sql

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {
        name: {} for name in CASES if name.startswith("decimal_")
    }

    class DecimalSubclass(Decimal):
        pass

    class CoercibleDecimal:
        def __str__(self):
            raise AssertionError("Decimal coercion")

        def __float__(self):
            raise AssertionError("Decimal float coercion")

    class DecimalExtension(pa.ExtensionType):
        def __init__(self):
            super().__init__(pa.decimal128(9, 2), "pietto.test.decimal")

        def __arrow_ext_serialize__(self):
            return b""

    for target in ("postgres", "mysql"):
        built = {}
        for precision, scale in DECIMAL_PAIRS:
            key = f"{target}/{precision}/{scale}"
            checked, artifact, neutral, producer = decimal_fixture(
                root / f"decimal-{target}-{precision}-{scale}", target, precision, scale
            )
            built[precision, scale] = checked, artifact, neutral, producer
            arrow = decimal_arrow(producer)
            rows = decimal_rows(target, precision, scale)
            batch = a.build_owned_batch(arrow, rows)
            snapshot = decimal_snapshot(batch)
            decimal_value_oracle(snapshot, precision, scale)
            rows[0][:] = [None, None]
            rows.clear()
            assert _exact(decimal_snapshot(batch), snapshot)
            wide = decimal_arrow(producer, bits=256)
            widened = a.build_owned_batch(wide, decimal_rows(target, precision, scale))
            before = export_result_contract(neutral, checked)
            verify_bound_export(before, checked)
            assert (
                export_result_contract(neutral, checked).canonical_bytes
                == before.canonical_bytes
            )
            results["decimal_values"][key] = dict(
                default=snapshot,
                wide=decimal_snapshot(widened),
                overflow=[
                    refused(
                        lambda k=k: a.build_owned_batch(
                            arrow, [[decimal_literal(k, scale), None]]
                        )
                    )
                    for k in (10**precision, -(10**precision))
                ],
            )
        checked, artifact, neutral, producer = built[9, 2]
        observed = decimal_observations(target, 9, 2)
        fact = observed[0].decimal
        assert fact is not None
        refusals = {}
        for key, update in {
            "precision": {"precision": 8},
            "scale": {"scale": 1},
            "bool_precision": {"precision": True},
            "float_precision": {"precision": 9.0},
            "bool_scale": {"scale": False},
            "text_scale": {"scale": "2"},
        }.items():
            obs = (replace(observed[0], decimal=replace(fact, **update)), observed[1])
            refusals[key] = refused(
                lambda obs=obs: p.bind_producer(neutral, artifact, obs)
            )
        for key, update in {
            "storage": {
                "storage": "my_decimal" if target == "postgres" else "pg_numeric"
            },
            "carrier": {"carrier": "str"},
            "domain": {"domain": "int_range"},
            "lower": {"lower": 0},
            "upper": {"upper": 1},
            "text": {"text": p.TextObservation(8, "UTF8", "C", "NO PAD")},
            "missing": {"decimal": None},
            "label": {"label": "amount"},
            "ordinal": {"ordinal": 1},
            "family": {"family": "foreign"},
        }.items():
            refusals[key] = refused(
                lambda update=update: p.bind_producer(
                    neutral, artifact, (replace(observed[0], **update), observed[1])
                )
            )
        _, foreign_artifact, _, foreign = decimal_fixture(
            root / f"decimal-foreign-{target}", target, 9, 2
        )
        refusals["foreign_root"] = refused(
            lambda: p.bind_producer(neutral, foreign_artifact, observed)
        )
        refusals["foreign_field"] = refused(
            lambda: a.bind_arrow(
                replace(
                    producer,
                    fields=(
                        replace(producer.fields[0], field=foreign.fields[0].field),
                        producer.fields[1],
                    ),
                )
            )
        )
        refusals["nullable"] = refused(
            lambda: a.bind_arrow(
                replace(
                    producer,
                    fields=(
                        replace(producer.fields[0], nullable=True),
                        producer.fields[1],
                    ),
                )
            )
        )
        for key, fields in {
            "tail": producer.fields[:-1],
            "reordered": producer.fields[::-1],
            "duplicate": (producer.fields[0],) * 2,
        }.items():
            refusals[key] = refused(
                lambda fields=fields: a.bind_arrow(replace(producer, fields=fields))
            )
        bad = replace(
            producer,
            fields=(
                replace(
                    producer.fields[0],
                    observation=replace(
                        observed[0], decimal=p.DecimalObservation(8, 2)
                    ),
                ),
                producer.fields[1],
            ),
        )
        schema = pa.schema(
            [
                pa.field("renamed", pa.decimal256(8, 2), nullable=False),
                pa.field("optional", pa.decimal256(9, 2), nullable=True),
            ]
        )
        coordinated = a.ArrowResultBinding(
            bad,
            schema,
            decimal_widths=tuple(
                a.DecimalWidthRequest(f.field, 256) for f in bad.fields
            ),
        )
        refusals["coordinated"] = refused(
            lambda: a.verify_arrow_binding(coordinated, bad)
        )
        upstream = []
        for precision, scale in ((8, 2), (9, 1)):
            outcome = emit_project_sql(checked, decimal_input(target, precision, scale))
            assert outcome.status == "BLOCKED"
            upstream.append([b.code for b in outcome.blockers])
        results["decimal_bindings"][target] = dict(
            refusals=refusals,
            upstream=upstream,
            observed=[
                dict(
                    ordinal=o.ordinal,
                    label=o.label,
                    storage=o.storage,
                    carrier=o.carrier,
                    precision=cast(p.DecimalObservation, o.decimal).precision,
                    scale=cast(p.DecimalObservation, o.decimal).scale,
                )
                for o in observed
            ],
        )
        r0, r1 = (a.DecimalWidthRequest(f.field, 256) for f in producer.fields)
        invalid_requests = (
            (),
            [],
            (r0,),
            (r0, r1, None),
            (r0, r0),
            (r1, r0),
            (a.DecimalWidthRequest(foreign.fields[0].field, 256), r1),
            (a.DecimalWidthRequest(r0.field, True), r1),
            (a.DecimalWidthRequest(r0.field, 64), r1),
            (a.IntegerWidthRequest(r0.field, 64), r1),
        )
        request_negatives = [
            refused(lambda req=req: a.bind_arrow(producer, decimal_widths=req))
            for req in invalid_requests
        ]
        high = built[39, 4][3]
        _, _, _, high_null = decimal_fixture(
            root / f"decimal-high-null-{target}", target, 39, 4, all_nullable=True
        )
        for candidate, rows in (
            (high, []),
            (high, [[decimal_literal(1, 4), None]]),
            (high_null, [[None, None]]),
        ):
            req = tuple(a.DecimalWidthRequest(f.field, 128) for f in candidate.fields)
            request_negatives.append(
                refused(
                    lambda candidate=candidate, rows=rows, req=req: a.build_owned_batch(
                        a.bind_arrow(candidate, decimal_widths=req), rows
                    )
                )
            )
        selected = decimal_arrow(producer)
        schema_bad = []
        for wrong in (
            pa.decimal128(8, 2),
            pa.decimal128(9, 1),
            pa.decimal256(9, 2),
            pa.decimal32(9, 2),
            pa.decimal64(9, 2),
            pa.float64(),
            pa.string(),
            pa.binary(16),
            DecimalExtension(),
        ):
            schema = pa.schema(
                [pa.field("renamed", wrong, nullable=False), selected.schema[1]]
            )
            schema_bad.append(
                refused(
                    lambda schema=schema: a.verify_arrow_binding(
                        replace(selected, schema=schema), producer
                    )
                )
            )
        schema_bad += [
            refused(
                lambda: a.verify_arrow_binding(
                    replace(
                        selected,
                        schema=selected.schema.with_metadata({b"precision": b"65"}),
                    ),
                    producer,
                )
            ),
            refused(
                lambda: a.verify_arrow_binding(
                    replace(
                        selected,
                        schema=pa.schema(
                            [
                                selected.schema[0].with_metadata({b"scale": b"0"}),
                                selected.schema[1],
                            ]
                        ),
                    ),
                    producer,
                )
            ),
        ]
        results["decimal_requests"][target] = dict(
            refusals=request_negatives, schema=schema_bad
        )
        mixed_checked, mixed_artifact, mixed_neutral, mixed = decimal_fixture(
            root / f"decimal-mixed-{target}", target, 9, 2, mixed=True
        )
        mixed_arrow = decimal_arrow(mixed, mixed=True)
        mixed_rows = decimal_rows(target, 9, 2, mixed=True)
        mixed_batch = a.build_owned_batch(mixed_arrow, mixed_rows)
        mixed_snapshot = decimal_snapshot(mixed_batch)
        decimal_value_oracle(mixed_snapshot, 9, 2, mixed=True)
        mixed_rows[0][:] = [None] * 6
        mixed_rows.clear()
        assert _exact(decimal_snapshot(mixed_batch), mixed_snapshot)
        widened = a.build_owned_batch(
            decimal_arrow(mixed, bits=256, mixed=True),
            decimal_rows(target, 9, 2, mixed=True),
        )
        results["decimal_values"][target + "/mixed"] = dict(
            default=mixed_snapshot, wide=decimal_snapshot(widened), overflow=[]
        )
        bad_req = (
            None,
            None,
            a.DecimalWidthRequest(mixed.fields[2].field, 256),
            None,
            None,
            None,
        )
        results["decimal_requests"][target]["wrong_kind"] = refused(
            lambda: a.bind_arrow(mixed, decimal_widths=bad_req)
        )
        results["decimal_bindings"][target]["foreign_metadata"] = refused(
            lambda: p.bind_producer(
                mixed_neutral,
                mixed_artifact,
                tuple(
                    replace(f.observation, decimal=p.DecimalObservation(9, 2))
                    if i == 2
                    else f.observation
                    for i, f in enumerate(mixed.fields)
                ),
            )
        )
        for bits in (128, 256):
            key = f"{target}/{bits}"
            arrow = decimal_arrow(producer, bits=bits)
            _, _, _, nullable = decimal_fixture(
                root / f"decimal-null-{target}-{bits}", target, 9, 2, all_nullable=True
            )
            nonfinite = (
                Decimal("NaN"),
                Decimal("sNaN"),
                Decimal("Infinity"),
                Decimal("-Infinity"),
            )
            invalid = (
                1,
                True,
                1.0,
                "1",
                b"1",
                DecimalSubclass("1"),
                CoercibleDecimal(),
                *nonfinite,
                Decimal("1E+1000000"),
                Decimal("1E-1000000"),
                Decimal("1.234"),
            )
            zeros = a.build_owned_batch(
                arrow,
                [
                    [Decimal("0E+1000000"), Decimal("-0E-1000000")],
                    [Decimal("-0.00"), Decimal("0.0000")],
                ],
            )
            exact = a.build_owned_batch(
                arrow, [[Decimal("1.23"), None], [Decimal("1.2300"), Decimal("123E-2")]]
            )
            results["decimal_empty_null"][key] = dict(
                empty=decimal_snapshot(a.build_owned_batch(arrow, [])),
                all_null=decimal_snapshot(
                    a.build_owned_batch(
                        decimal_arrow(nullable, bits=bits), [[None, None], [None, None]]
                    )
                ),
                zeros=decimal_snapshot(zeros)["columns"],
                exact_rescale=decimal_snapshot(exact)["columns"],
                refusals=[
                    refused(lambda v=v: a.build_owned_batch(arrow, [[v, None]]))
                    for v in invalid
                ]
                + [refused(lambda: a.build_owned_batch(arrow, [[None, None]]))],
            )
            results["decimal_empty_null"][key]["high_default"] = (
                None
                if bits == 128
                else dict(
                    empty=decimal_snapshot(
                        a.build_owned_batch(decimal_arrow(high), [])
                    ),
                    all_null=decimal_snapshot(
                        a.build_owned_batch(
                            decimal_arrow(high_null), [[None, None], [None, None]]
                        )
                    ),
                )
            )
            impostors = []
            for position, value in (
                (0, 1),
                (2, Decimal("1")),
                (3, Decimal("1")),
                (4, Decimal("1")),
                (5, Decimal("1")),
            ):
                row = [
                    Decimal("1.23"),
                    None,
                    7,
                    True if target == "postgres" else 1,
                    -0.0,
                    "é",
                ]
                row[position] = value
                impostors.append(
                    refused(lambda row=row: a.build_owned_batch(mixed_arrow, [row]))
                )
            results["decimal_empty_null"][key]["mixed_impostors"] = impostors
            allowance = 2 * (bits // 8 + 1)
            allowed = a.build_owned_batch(
                arrow, [[Decimal("1.23"), None]], limits=a.BatchLimits(bytes=allowance)
            )
            width = bits // 8
            ty = arrow.schema[0].type
            # Safe allocated buffers: two's-complement coefficient with exact declared scale.
            data = pa.py_buffer(
                b"".join(
                    k.to_bytes(width, "little", signed=True)
                    for k in (1, 10**9, -(10**9), 123)
                )
            )
            invalid_array = pa.Array.from_buffers(ty, 4, [None, data]).slice(1, 1)
            invalid_batch = pa.RecordBatch.from_arrays(
                [invalid_array, pa.array([None], type=ty)], schema=arrow.schema
            )
            outcomes = [
                refused(
                    lambda: a.build_owned_batch(
                        arrow,
                        [[Decimal("1.23"), None]],
                        limits=a.BatchLimits(bytes=allowance - 1),
                    )
                ),
                refused(
                    lambda: a.verify_batch(
                        invalid_batch,
                        arrow,
                        producer,
                        limits=a.BatchLimits(bytes=allowance),
                    )
                ),
            ]
            # Decimal(9,2), Decimal(65,30), 3 fixed scalars and a large_string 'é'.
            mixed_allowance = 17 + 33 + 3 * 9 + 1 + 16 + 2
            mixed_allowed = a.build_owned_batch(
                mixed_arrow,
                [
                    [
                        Decimal("1.23"),
                        decimal_literal(1, 30),
                        7,
                        True if target == "postgres" else 1,
                        -0.0,
                        "é",
                    ]
                ],
                limits=a.BatchLimits(bytes=mixed_allowance),
            )
            outcomes.append(
                refused(
                    lambda: a.build_owned_batch(
                        mixed_arrow,
                        [
                            [
                                Decimal("1.23"),
                                decimal_literal(1, 30),
                                7,
                                True if target == "postgres" else 1,
                                -0.0,
                                "é",
                            ]
                        ],
                        limits=a.BatchLimits(bytes=mixed_allowance - 1),
                    )
                )
            )
            results["decimal_resources"][key] = dict(
                allowance=allowance,
                columns=decimal_snapshot(allowed)["columns"],
                mixed_allowance=mixed_allowance,
                mixed_rows=mixed_allowed.num_rows,
                refusals=outcomes,
            )
            original_array = pa.array

            def forbidden_array(*args, **kwargs):
                raise AssertionError("Arrow allocation preceded input preflight")

            try:
                setattr(pa, "array", forbidden_array)
                results["decimal_resources"][key]["preflight"] = [
                    refused(
                        lambda: a.build_owned_batch(
                            arrow,
                            [[Decimal("1.23"), None]],
                            limits=a.BatchLimits(bytes=allowance - 1),
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(
                            arrow,
                            [[Decimal("1.23"), None]],
                            limits=a.BatchLimits(rows=0),
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(arrow, [[Decimal("1.234"), None]])
                    ),
                ]
            finally:
                setattr(pa, "array", original_array)
            _, _, _, nullable_bound = decimal_fixture(
                root / f"decimal-buffer-null-{target}-{bits}",
                target,
                9,
                2,
                all_nullable=True,
            )
            nullable_arrow = decimal_arrow(nullable_bound, bits=bits)
            # Offset 1 includes a null slot with arbitrary out-of-precision bytes, then valid -123.
            payload = pa.py_buffer(
                b"".join(
                    k.to_bytes(width, "little", signed=True)
                    for k in (1, 10**12, -123, 123)
                )
            )
            array = pa.Array.from_buffers(
                ty, 4, [pa.py_buffer(b"\x0d"), payload]
            ).slice(1, 2)
            supplied = pa.RecordBatch.from_arrays(
                [array, array], schema=nullable_arrow.schema
            )
            a.verify_batch(supplied, nullable_arrow, nullable_bound)
            overflows = []
            for k in (10**9, -(10**9)):
                over = pa.Array.from_buffers(
                    ty,
                    1,
                    [None, pa.py_buffer(k.to_bytes(width, "little", signed=True))],
                )
                candidate = pa.RecordBatch.from_arrays(
                    [over, pa.array([None], type=ty)], schema=arrow.schema
                )
                overflows.append(
                    refused(lambda: a.verify_batch(candidate, arrow, producer))
                )
            try:
                pa.Array.from_buffers(ty, 1, [None, pa.py_buffer(b"\0" * (width - 1))])
            except (ValueError, pa.ArrowException):
                short = "CONSTRUCTOR"
            else:
                raise AssertionError("short Decimal buffer accepted by constructor")
            null_batch = pa.RecordBatch.from_arrays(
                [pa.array([None], type=ty), pa.array([None], type=ty)],
                schema=arrow.schema,
            )
            results["decimal_supplied"][key] = dict(
                offsets=[c.offset for c in supplied.columns],
                columns=decimal_snapshot(supplied)["columns"],
                overflow=overflows,
                short_buffer=short,
                null=refused(lambda: a.verify_batch(null_batch, arrow, producer)),
                metadata=refused(
                    lambda: a.verify_batch(
                        supplied.replace_schema_metadata({b"precision": b"65"}),
                        nullable_arrow,
                        nullable_bound,
                    )
                ),
            )
        high_producer = built[65, 30][3]
        high_arrow = decimal_arrow(high_producer)
        context_results = []
        for precision, rounding, trap in ((2, ROUND_DOWN, True), (7, ROUND_UP, False)):
            rows = decimal_rows(target, 65, 30)
            with localcontext() as context:
                context.prec = precision
                context.rounding = rounding
                context.Emin = -2
                context.Emax = 2
                context.capitals = 1
                context.clamp = 0
                for signal in context.traps:
                    context.traps[signal] = trap
                context.clear_flags()
                context.flags[Rounded] = True
                before = decimal_context_snapshot(context)
                values = decimal_snapshot(a.build_owned_batch(high_arrow, rows))
                negatives = [
                    refused(lambda v=v: a.build_owned_batch(high_arrow, [[v, None]]))
                    for v in (
                        Decimal("1E+1000000"),
                        Decimal("1E-1000000"),
                        Decimal("sNaN"),
                        Decimal("NaN"),
                        Decimal("Infinity"),
                        Decimal("-Infinity"),
                        Decimal("1E-31"),
                    )
                ]
                after = decimal_context_snapshot(context)
                assert getcontext() is context and before == after
                context_results.append(
                    dict(before=before, after=after, values=values, refusals=negatives)
                )
        results["decimal_context"][target] = context_results
        original = a.build_owned_batch(
            mixed_arrow, decimal_rows(target, 9, 2, mixed=True)
        )
        changed_batches = []
        for replacement in (Decimal("1.24"), Decimal("-9999999.99")):
            arrays = list(original.columns)
            values = arrays[0].to_pylist()
            values[0] = replacement
            arrays[0] = pa.array(values, type=mixed_arrow.schema[0].type)
            changed_batches.append(
                pa.RecordBatch.from_arrays(arrays, schema=mixed_arrow.schema)
            )
        for indices in ([1, 0, 2, 3, 4, 5], [0, 1, 2, 3, 5], [0, 1, 2, 3, 4]):
            changed_batches.append(original.take(indices))
        arrays = list(original.columns)
        values = arrays[1].to_pylist()
        values[0] = decimal_literal(0, 30)
        arrays[1] = pa.array(values, type=mixed_arrow.schema[1].type)
        changed_batches.append(
            pa.RecordBatch.from_arrays(arrays, schema=mixed_arrow.schema)
        )
        detected = []
        for changed in changed_batches:
            a.verify_batch(changed, mixed_arrow, mixed)
            try:
                decimal_value_oracle(decimal_snapshot(changed), 9, 2, mixed=True)
            except ValueError:
                detected.append("VALUE_CORRESPONDENCE")
            else:
                raise AssertionError("domain-valid Decimal substitution escaped oracle")
        builder = a.build_owned_batch

        def injected(binding, rows, **kwargs):
            altered = [list(r) for r in rows]
            altered[0][0] = Decimal("1.24")
            return builder(binding, altered, **kwargs)

        try:
            a.build_owned_batch = injected
            try:
                decimal_value_oracle(
                    decimal_snapshot(
                        a.build_owned_batch(
                            mixed_arrow, decimal_rows(target, 9, 2, mixed=True)
                        )
                    ),
                    9,
                    2,
                    mixed=True,
                )
            except ValueError:
                detected.append("VALUE_CORRESPONDENCE")
            else:
                raise AssertionError("injected Decimal builder escaped oracle")
        finally:
            a.build_owned_batch = builder
        results["decimal_substitution"][target] = detected
        for kind, checked_, neutral_ in [
            ("decimal", built[39, 4][0], built[39, 4][2]),
            ("mixed", mixed_checked, mixed_neutral),
        ]:
            exported = export_result_contract(neutral_, checked_)
            verify_bound_export(exported, checked_)
            assert (
                pure.encode_document(
                    pure.decode_contract(exported.canonical_bytes).document
                )
                == exported.canonical_bytes
            )
            results["decimal_codec"][target + "/" + kind] = (
                exported.canonical_bytes.decode()
            )
    return results


def verify_decimal_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        targets = {"postgres", "mysql"}
        width_keys = {f"{t}/{bits}" for t in targets for bits in (128, 256)}
        for name in (
            "decimal_bindings",
            "decimal_requests",
            "decimal_context",
            "decimal_substitution",
        ):
            if set(cases[name]) != targets:
                raise ValueError("Decimal target denominator")
        for name in ("decimal_empty_null", "decimal_resources", "decimal_supplied"):
            if set(cases[name]) != width_keys:
                raise ValueError("Decimal width denominator")
        if set(cases["decimal_values"]) != {
            f"{t}/{p}/{s}" for t in targets for p, s in DECIMAL_PAIRS
        } | {t + "/mixed" for t in targets}:
            raise ValueError("Decimal precision matrix denominator")
        if set(cases["decimal_codec"]) != {
            t + "/" + k for t in targets for k in ("decimal", "mixed")
        }:
            raise ValueError("Decimal codec denominator")
        for target in ("postgres", "mysql"):
            for precision, scale in DECIMAL_PAIRS:
                value = cases["decimal_values"][f"{target}/{precision}/{scale}"]
                expected = dict(
                    default=decimal_expected(precision, scale),
                    wide=decimal_expected(precision, scale, bits=256),
                    overflow=["VALUE_DOMAIN"] * 2,
                )
                if not _exact(value, expected):
                    raise ValueError("Decimal exact boundary values")
            if not _exact(
                cases["decimal_values"][target + "/mixed"],
                dict(
                    default=decimal_expected(9, 2, mixed=True),
                    wide=decimal_expected(9, 2, mixed=True, bits=256),
                    overflow=[],
                ),
            ):
                raise ValueError("Decimal mixed values")
            keys = (
                "precision",
                "scale",
                "bool_precision",
                "float_precision",
                "bool_scale",
                "text_scale",
                "storage",
                "carrier",
                "domain",
                "lower",
                "upper",
                "text",
                "missing",
                "label",
                "ordinal",
                "family",
                "nullable",
                "coordinated",
            )
            expected = dict(
                refusals={
                    **dict.fromkeys(keys, "PRODUCER_OBSERVATION"),
                    "foreign_root": "ROOT",
                    "foreign_field": "PRODUCER_FIELDS",
                    "tail": "PRODUCER_ROOT",
                    "reordered": "PRODUCER_FIELDS",
                    "duplicate": "PRODUCER_FIELDS",
                },
                upstream=[["PIE-B1002"] * 2] * 2,
                observed=[
                    dict(
                        ordinal=i,
                        label=DECIMAL_LABELS[i],
                        storage="pg_numeric" if target == "postgres" else "my_decimal",
                        carrier="decimal",
                        precision=9,
                        scale=2,
                    )
                    for i in range(2)
                ],
                foreign_metadata="PRODUCER_OBSERVATION",
            )
            if not _exact(cases["decimal_bindings"][target], expected):
                raise ValueError("Decimal producer authority")
            if not _exact(
                cases["decimal_requests"][target],
                dict(
                    refusals=["ARROW_ADAPTATION"] * 13,
                    schema=["ARROW_BINDING"] * 11,
                    wrong_kind="ARROW_ADAPTATION",
                ),
            ):
                raise ValueError("Decimal width/schema authority")
            for bits in (128, 256):
                key = f"{target}/{bits}"
                expected_empty: dict[str, Any] = dict(
                    empty=decimal_expected(9, 2, bits=bits, state="empty"),
                    all_null=decimal_expected(
                        9, 2, bits=bits, state="null", all_nullable=True
                    ),
                    zeros=[["0", "0"], ["0", "0"]],
                    exact_rescale=[["123", "123"], [None, "123"]],
                    refusals=["VALUE_DOMAIN"] * 14 + ["NULL"],
                )
                expected_empty["high_default"] = (
                    None
                    if bits == 128
                    else dict(
                        empty=decimal_expected(39, 4, state="empty"),
                        all_null=decimal_expected(
                            39, 4, state="null", all_nullable=True
                        ),
                    )
                )
                expected_empty["mixed_impostors"] = ["VALUE_DOMAIN"] * 5
                expected_resource = dict(
                    preflight=["LIMIT", "LIMIT", "VALUE_DOMAIN"],
                    allowance=34 if bits == 128 else 66,
                    columns=[["123"], [None]],
                    mixed_allowance=96,
                    mixed_rows=1,
                    refusals=["LIMIT"] * 3,
                )
                expected_supplied = dict(
                    offsets=[1, 1],
                    columns=[[None, "-123"], [None, "-123"]],
                    overflow=["ARROW_BATCH"] * 2,
                    short_buffer="CONSTRUCTOR",
                    null="NULL",
                    metadata="ARROW_SCHEMA",
                )
                for name, expected in [
                    ("decimal_empty_null", expected_empty),
                    ("decimal_resources", expected_resource),
                    ("decimal_supplied", expected_supplied),
                ]:
                    if not _exact(cases[name][key], expected):
                        raise ValueError(name + " evidence")
            contexts = cases["decimal_context"][target]
            if type(contexts) is not list or len(contexts) != 2:
                raise ValueError("Decimal context denominator")
            signals = (
                "InvalidOperation",
                "FloatOperation",
                "DivisionByZero",
                "Overflow",
                "Underflow",
                "Subnormal",
                "Inexact",
                "Rounded",
                "Clamped",
            )
            for actual, (precision, rounding, trap) in zip(
                contexts, ((2, "ROUND_DOWN", True), (7, "ROUND_UP", False)), strict=True
            ):
                settings = dict(
                    precision=precision,
                    rounding=rounding,
                    emin=-2,
                    emax=2,
                    capitals=1,
                    clamp=0,
                    flags={k: k == "Rounded" for k in signals},
                    traps=dict.fromkeys(signals, trap),
                )
                if not _exact(
                    actual,
                    dict(
                        before=settings,
                        after=settings,
                        values=decimal_expected(65, 30),
                        refusals=["VALUE_DOMAIN"] * 7,
                    ),
                ):
                    raise ValueError("Decimal context isolation")
            if cases["decimal_substitution"][target] != ["VALUE_CORRESPONDENCE"] * 7:
                raise ValueError("Decimal independent value oracle")
            for kind in ("decimal", "mixed"):
                document = pure.decode_contract(
                    cases["decimal_codec"][target + "/" + kind].encode()
                ).document
                count = 2 if kind == "decimal" else 6
                pairs = (
                    [["39", "4"]] * 2
                    if kind == "decimal"
                    else [["9", "2"], ["65", "30"]]
                )
                fields = document["fields"]
                if (
                    [f["label"] for f in fields] != list(DECIMAL_LABELS[:count])
                    or [f["canonical"] for f in fields]
                    != [
                        dict(kind="builtin", name=k, symbol=None)
                        for k in (
                            ["Decimal", "Decimal"]
                            + (
                                ["Int", "Bool", "Float", "Text"]
                                if kind == "mixed"
                                else []
                            )
                        )
                    ]
                    or [
                        [a["value"]["value"] for a in f["declared"]["arguments"]]
                        for f in fields[:2]
                    ]
                    != pairs
                    or [f["nullability"] for f in fields]
                    != ["nullable" if i in (1, 5) else "non_null" for i in range(count)]
                ):
                    raise ValueError("Decimal complete neutral parameters")
    except (KeyError, TypeError, AttributeError, pure.ContractDocumentError) as exc:
        raise ValueError("Decimal report evidence") from exc


TEMPORAL_NAMES = (
    "stamp",
    "optional_stamp",
    "identifier",
    "optional_identifier",
    "number",
    "flag",
    "ratio",
    "label",
    "amount",
)
TEMPORAL_LABELS = (
    "occurred_at",
    "maybe_time",
    "key_value",
    "maybe_key",
    "number",
    "flag",
    "ratio",
    "label",
    "amount",
)


def temporal_source(target, *, mixed=False, all_nullable=False, projection=None):
    kinds = (
        "Timestamp",
        "Timestamp",
        "UUID",
        "UUID",
        "Int",
        "Bool",
        "Float",
        "Text",
        "Decimal(39, 4)",
    )[: 9 if mixed else 4]
    text = "shape Row:\n" + "".join(
        f"    {name}: {kind} {'nullable' if all_nullable or i in (1, 3, 7) else 'not null'}\n"
        for i, (name, kind) in enumerate(
            zip(TEMPORAL_NAMES[: len(kinds)], kinds, strict=True)
        )
    )
    projection = tuple(range(len(kinds))) if projection is None else projection
    labels = (
        TEMPORAL_LABELS
        if projection == tuple(range(len(kinds)))
        else tuple(f"selected_{i}" for i in range(len(projection)))
    )
    return (
        text
        + f'source rows: Row is {target}.table("opaque.result.fixture")\ntable result:\n    from rows\n    select:\n'
        + "".join(
            f"        {labels[i]} = {TEMPORAL_NAMES[position]}\n"
            for i, position in enumerate(projection)
        )
    )


def temporal_input(target, *, mixed=False, all_nullable=False):
    doc = json.loads(emission_input(target))
    descriptions = [
        (
            dict(
                kind="pg_timestamp" if target == "postgres" else "my_datetime",
                fractional_seconds=6,
            ),
            dict(kind="timestamp"),
        ),
        (
            dict(
                kind="pg_timestamp" if target == "postgres" else "my_datetime",
                fractional_seconds=6,
            ),
            dict(kind="timestamp"),
        ),
        (
            dict(kind="pg_uuid" if target == "postgres" else "my_uuid_bytes"),
            dict(kind="uuid", encoding="standard_bytes"),
        ),
        (
            dict(kind="pg_uuid" if target == "postgres" else "my_uuid_bytes"),
            dict(kind="uuid", encoding="standard_bytes"),
        ),
    ]
    if mixed:
        descriptions += [
            (
                dict(kind=width_storage(target, 32)),
                dict(kind="int_range", min="-100", max="100"),
            ),
            (
                dict(kind="pg_bool" if target == "postgres" else "my_bool01"),
                dict(kind="bool01"),
            ),
            (
                dict(kind="pg_float8" if target == "postgres" else "my_double"),
                dict(kind="finite_float", format="binary64"),
            ),
            (
                dict(kind="pg_text")
                if target == "postgres"
                else dict(kind="my_varchar", length=8),
                dict(
                    kind="text",
                    max_characters=8,
                    encoding="UTF8" if target == "postgres" else "utf8mb4",
                    collation="C" if target == "postgres" else "utf8mb4_0900_bin",
                    padding="NO PAD",
                ),
            ),
            (
                dict(
                    kind="pg_numeric" if target == "postgres" else "my_decimal",
                    precision=39,
                    scale=4,
                ),
                dict(kind="decimal", precision=39, scale=4),
            ),
        ]
    doc["sources"][0]["fields"] = [
        dict(
            ordinal=i,
            name=TEMPORAL_NAMES[i],
            column=TEMPORAL_NAMES[i],
            representation=dict(
                storage=storage,
                domain=domain,
                nullable=bool(all_nullable or i in (1, 3, 7)),
            ),
        )
        for i, (storage, domain) in enumerate(descriptions)
    ]
    return json.dumps(doc).encode()


def temporal_premise(
    directory, target, *, mixed=False, all_nullable=False, projection=None
):
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_result_contract import build_result_contract

    checked = build_neutral(
        directory,
        {
            "main.pietto": temporal_source(
                target, mixed=mixed, all_nullable=all_nullable, projection=projection
            )
        },
    )
    meaning = acquire_scalar_meaning(checked)
    outcome = emit_project_sql(
        checked,
        temporal_input(target, mixed=mixed, all_nullable=all_nullable),
        scalar_meaning=meaning,
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    neutral = build_result_contract(checked, scalar_meaning=meaning)
    return checked, meaning, outcome.artifact, neutral


# Independent calendar/byte corpus; coefficients/ticks are literal expectations.
TIME_COMPONENTS = (
    (1000, 1, 1, 0, 0, 0, 0),
    (1969, 12, 31, 23, 59, 59, 999999),
    (1970, 1, 1, 0, 0, 0, 0),
    (1970, 1, 1, 0, 0, 0, 1),
    (2000, 2, 29, 12, 34, 56, 123456),
    (2024, 2, 29, 23, 59, 59, 999999),
    (9000, 1, 1, 0, 0, 0, 1),
    (9999, 12, 31, 23, 59, 59, 499999),
    (1970, 1, 1, 0, 0, 0, 0),
    (1970, 1, 1, 0, 0, 0, 0),
)
TIME_TICKS = (
    -30610224000000000,
    -1,
    0,
    1,
    951827696123456,
    1709251199999999,
    221845392000000001,
    253402300799499999,
    0,
    0,
)
UUID_HEX = (
    "00112233445566778899aabbccddeeff",
    "00000000000000000000000000000000",
    "ffffffffffffffffffffffffffffffff",
    "0123456789abcdeffedcba9876543210",
    "00110022003300440055006600770088",
    "00112233445566778899aabbccddeeff",
    "ffffffffffffffffffffffffffffffff",
    "00000000000000000000000000000000",
    "00112233445566778899aabbccddeeff",
    "00112233445566778899aabbccddeeff",
)
TEMPORAL_NULLS = (0, 3, 5, 8, 9)
TEMPORAL_DECIMAL = 123456789012345678901234567890123456789


def temporal_observations(target, *, mixed=False):
    from pietto._project.project_result_binding import (
        ProducerObservation,
        TextObservation,
        DecimalObservation,
    )
    from pietto._project.project_scalar_meaning import TimestampMeaning, UUIDMeaning

    observed = [
        ProducerObservation(
            i,
            TEMPORAL_LABELS[i],
            target,
            "pg_timestamp" if target == "postgres" else "my_datetime",
            domain="timestamp",
            carrier="datetime",
            meaning=TimestampMeaning(),
            fractional_seconds=6,
        )
        for i in range(2)
    ]
    observed += [
        ProducerObservation(
            i,
            TEMPORAL_LABELS[i],
            target,
            "pg_uuid" if target == "postgres" else "my_uuid_bytes",
            domain="uuid",
            carrier="uuid" if target == "postgres" else "bytes16",
            meaning=UUIDMeaning(),
        )
        for i in range(2, 4)
    ]
    if mixed:
        observed += [
            ProducerObservation(
                4, "number", target, width_storage(target, 32), -100, 100
            ),
            ProducerObservation(
                5,
                "flag",
                target,
                "pg_bool" if target == "postgres" else "my_bool01",
                domain="bool01",
                carrier="bool" if target == "postgres" else "int01",
            ),
            ProducerObservation(
                6,
                "ratio",
                target,
                "pg_float8" if target == "postgres" else "my_double",
                domain="finite_float",
                carrier="float",
            ),
            ProducerObservation(
                7,
                "label",
                target,
                "pg_text" if target == "postgres" else "my_varchar",
                domain="text",
                carrier="str",
                text=TextObservation(
                    8,
                    "UTF8" if target == "postgres" else "utf8mb4",
                    "C" if target == "postgres" else "utf8mb4_0900_bin",
                    "NO PAD",
                    None if target == "postgres" else 8,
                ),
            ),
            ProducerObservation(
                8,
                "amount",
                target,
                "pg_numeric" if target == "postgres" else "my_decimal",
                domain="decimal",
                carrier="decimal",
                decimal=DecimalObservation(39, 4),
            ),
        ]
    return tuple(observed)


def temporal_fixture(directory, target, *, mixed=False, all_nullable=False):
    from pietto._project.project_result_binding import bind_producer

    checked, meaning, artifact, neutral = temporal_premise(
        directory, target, mixed=mixed, all_nullable=all_nullable
    )
    producer = bind_producer(
        neutral, artifact, temporal_observations(target, mixed=mixed)
    )
    return checked, meaning, artifact, neutral, producer


def temporal_arrow(producer, *, representation=None, mixed=False):
    from pietto._project import project_arrow_result as a

    fields = producer.fields
    return a.bind_arrow(
        producer,
        uuid_representations=None
        if representation is None
        else tuple(
            a.UUIDRepresentationRequest(f.field, representation)
            if i in (2, 3)
            else None
            for i, f in enumerate(fields)
        ),
        integer_widths=tuple(
            a.IntegerWidthRequest(f.field, 16) if i == 4 else None
            for i, f in enumerate(fields)
        )
        if mixed
        else None,
        text_offset_widths=tuple(
            a.TextOffsetWidthRequest(f.field, 64) if i == 7 else None
            for i, f in enumerate(fields)
        )
        if mixed
        else None,
        decimal_widths=tuple(
            a.DecimalWidthRequest(f.field, 256) if i == 8 else None
            for i, f in enumerate(fields)
        )
        if mixed
        else None,
    )


def temporal_rows(target, *, mixed=False):
    from datetime import datetime
    from uuid import UUID

    result = []
    for i, (components, identifier) in enumerate(
        zip(TIME_COMPONENTS, UUID_HEX, strict=True)
    ):
        stamp = datetime(*components)
        data = bytes.fromhex(identifier)
        value = UUID(bytes=data) if target == "postgres" else data
        row = [
            stamp,
            None if i in TEMPORAL_NULLS else stamp,
            value,
            None if i in TEMPORAL_NULLS else value,
        ]
        if mixed:
            row += [
                7,
                True if target == "postgres" else 1,
                -0.0,
                None if i in TEMPORAL_NULLS else "é",
                decimal_literal(TEMPORAL_DECIMAL, 4),
            ]
        result.append(row)
    return result


def temporal_snapshot(batch):
    from datetime import datetime, timedelta
    import struct

    pa = importlib.import_module("pyarrow")
    columns = []
    components = []
    for i, column in enumerate(batch.columns):
        if i < 4:
            storage = column.storage if type(column.type) is type(pa.uuid()) else column
            width = 8 if i < 2 else 16
            data = memoryview(storage.buffers()[1])
            values = []
            parts = []
            for j in range(len(storage)):
                if not storage[j].is_valid:
                    values.append(None)
                    parts.append(None)
                    continue
                offset = (storage.offset + j) * width
                raw = bytes(data[offset : offset + width])
                if i < 2:
                    tick = int.from_bytes(raw, "little", signed=True)
                    values.append(tick)
                    value = datetime(1970, 1, 1) + timedelta(microseconds=tick)
                    parts.append(
                        [
                            value.year,
                            value.month,
                            value.day,
                            value.hour,
                            value.minute,
                            value.second,
                            value.microsecond,
                        ]
                    )
                else:
                    values.append(raw.hex())
            columns.append(values)
            if i < 2:
                components.append(parts)
        elif i == 8:
            width = column.type.bit_width // 8
            data = memoryview(column.buffers()[1])
            columns.append(
                [
                    str(
                        int.from_bytes(
                            data[
                                (column.offset + j) * width : (column.offset + j + 1)
                                * width
                            ],
                            "little",
                            signed=True,
                        )
                    )
                    if column[j].is_valid
                    else None
                    for j in range(len(column))
                ]
            )
        else:
            values = column.to_pylist()
            columns.append(
                [None if v is None else struct.pack(">d", v).hex() for v in values]
                if i == 6
                else values
            )
    return dict(
        types=[str(f.type) for f in batch.schema],
        labels=batch.schema.names,
        nullable=[f.nullable for f in batch.schema],
        columns=columns,
        components=components,
    )


def temporal_expected(
    *, representation="uuid", mixed=False, state="values", all_nullable=False
) -> dict[str, Any]:
    uuid_type = (
        "extension<arrow.uuid>" if representation == "uuid" else "fixed_size_binary[16]"
    )
    columns: list[list[Any]] = [
        list(TIME_TICKS),
        [None if i in TEMPORAL_NULLS else v for i, v in enumerate(TIME_TICKS)],
        list(UUID_HEX),
        [None if i in TEMPORAL_NULLS else v for i, v in enumerate(UUID_HEX)],
    ]
    components = [
        list(map(list, TIME_COMPONENTS)),
        [
            None if i in TEMPORAL_NULLS else list(v)
            for i, v in enumerate(TIME_COMPONENTS)
        ],
    ]
    if mixed:
        columns += [
            [7] * 10,
            [True] * 10,
            ["8000000000000000"] * 10,
            [None if i in TEMPORAL_NULLS else "é" for i in range(10)],
            [str(TEMPORAL_DECIMAL)] * 10,
        ]
    if state != "values":
        columns = [[None] * (0 if state == "empty" else 2) for _ in columns]
        components = [[None] * (0 if state == "empty" else 2) for _ in range(2)]
    return dict(
        types=["timestamp[us]"] * 2
        + [uuid_type] * 2
        + (
            ["int16", "bool", "double", "large_string", "decimal256(39, 4)"]
            if mixed
            else []
        ),
        labels=list(TEMPORAL_LABELS[: len(columns)]),
        nullable=[bool(all_nullable or i in (1, 3, 7)) for i in range(len(columns))],
        columns=columns,
        components=components,
    )


def temporal_value_oracle(snapshot, **kwargs):
    if not _exact(snapshot, temporal_expected(**kwargs)):
        raise ValueError("Timestamp/UUID exact value/NULL/sequence correspondence")


def meaning_refused(action):
    from pietto._project.project_scalar_meaning import ScalarMeaningError

    try:
        action()
    except ScalarMeaningError as exc:
        return exc.category
    raise AssertionError("invalid meaning accepted")


def meaning_snapshot(bundle):
    from dataclasses import asdict

    return [
        dict(
            ordinal=e.ordinal,
            source_position=e.source_port.ref.position,
            canonical=e.canonical.name,
            law=asdict(e.law),
        )
        for e in bundle.entries
    ]


def run_temporal_cases(root):
    from datetime import datetime, date, timezone, timedelta
    from uuid import UUID
    from pietto._project import (
        project_scalar_meaning as m,
        project_arrow_result as a,
        project_result_binding as p,
        project_result_contract as c,
    )
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
        verify_contract_correspondence,
    )
    from pietto._project import project_result_contract_pure_boundary as pure
    import struct

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {
        name: {}
        for name in (
            "meaning_premise",
            "timestamp_values",
            "timestamp_policy",
            "uuid_values",
            "uuid_policy",
            "temporal_empty_mixed",
            "temporal_resources",
            "temporal_correspondence",
            "temporal_codec",
        )
    }

    class DatetimeSubclass(datetime):
        pass

    class UUIDSubclass(UUID):
        pass

    class BytesSubclass(bytes):
        pass

    class PolicySubclass(str):
        pass

    class CoercibleTemporal:
        def __str__(self):
            raise AssertionError("temporal string coercion")

        def __int__(self):
            raise AssertionError("temporal integer coercion")

        def __bytes__(self):
            raise AssertionError("UUID bytes coercion")

    class FakeUUID(pa.ExtensionType):
        def __init__(self):
            super().__init__(pa.binary(16), "arrow.uuid")

        def __arrow_ext_serialize__(self):
            return b""

    for target in ("postgres", "mysql"):
        checked, bundle, artifact, neutral, producer = temporal_fixture(
            root / f"temporal-{target}", target
        )
        arrow = temporal_arrow(producer)
        absent = emit_project_sql(checked, temporal_input(target))
        other_checked, other_bundle, _, _, other = temporal_fixture(
            root / f"temporal-foreign-{target}", target
        )
        original_entries = bundle.entries
        bad_meanings = {
            "foreign_root": replace(bundle, verification=other_checked),
            "missing": replace(bundle, entries=bundle.entries[:-1]),
            "extra": replace(bundle, entries=(*bundle.entries, bundle.entries[0])),
            "reordered": replace(bundle, entries=bundle.entries[::-1]),
            "field": replace(
                bundle,
                entries=(
                    replace(
                        bundle.entries[0],
                        source_port=other_bundle.entries[0].source_port,
                    ),
                    *bundle.entries[1:],
                ),
            ),
            "type": replace(
                bundle,
                entries=(
                    replace(bundle.entries[0], canonical=bundle.entries[2].canonical),
                    *bundle.entries[1:],
                ),
            ),
            "calendar": replace(
                bundle,
                entries=(
                    replace(
                        bundle.entries[0],
                        law=replace(m.TimestampMeaning(), calendar="julian"),
                    ),
                    *bundle.entries[1:],
                ),
            ),
            "endpoint": replace(
                bundle,
                entries=(
                    replace(
                        bundle.entries[0],
                        law=replace(
                            m.TimestampMeaning(),
                            upper=(9999, 12, 31, 23, 59, 59, 999999),
                        ),
                    ),
                    *bundle.entries[1:],
                ),
            ),
            "byte_order": replace(
                bundle,
                entries=(
                    *bundle.entries[:2],
                    replace(
                        bundle.entries[2],
                        law=replace(m.UUIDMeaning(), byte_order="little_endian"),
                    ),
                    bundle.entries[3],
                ),
            ),
        }
        negatives = {
            name: meaning_refused(lambda bad=bad: m.verify_scalar_meaning(bad, checked))
            for name, bad in bad_meanings.items()
        }
        preparations = [
            emit_project_sql(checked, temporal_input(target), scalar_meaning=bad).status
            for bad in bad_meanings.values()
        ]
        try:
            object.__setattr__(bundle, "entries", bundle.entries[:-1])
            invalidated = not verify_project_sql_emission(
                artifact, artifact.request
            ).verified
            contract_invalidated = refused(
                lambda: c.verify_result_contract(neutral, checked)
            )
        finally:
            object.__setattr__(bundle, "entries", original_entries)
        rechecked, reused, reused_artifact, reused_contract = temporal_premise(
            root / f"temporal-reuse-{target}", target, projection=(2, 0, 2, 1, 3)
        )
        assert verify_project_sql_emission(
            reused_artifact, reused_artifact.request
        ).verified
        from pietto._project.project_sql_emission import realize_project_sql

        slot_refusals = []
        for meaning_slot in (artifact.request, artifact.request.sources[0].fields[0]):
            retained = meaning_slot.scalar_meaning
            try:
                object.__delattr__(meaning_slot, "scalar_meaning")
                outcome = realize_project_sql(artifact.request)
                slot_refusals.append(
                    [outcome.status, [(b.code, b.detail) for b in outcome.blockers]]
                )
            finally:
                object.__setattr__(meaning_slot, "scalar_meaning", retained)
        filtered_source = temporal_source(target, mixed=True).replace(
            "    select:\n", "    where number > 0\n    select:\n"
        )
        filtered = build_neutral(
            root / f"meaning-filter-{target}", {"main.pietto": filtered_source}
        )
        outside = emit_project_sql(
            filtered,
            temporal_input(target, mixed=True),
            scalar_meaning=m.acquire_scalar_meaning(filtered),
        )
        observations = temporal_observations(target)
        producer_negatives = {}
        for name, position, changes in (
            ("precision", 0, {"fractional_seconds": 3}),
            ("float_precision", 0, {"fractional_seconds": 6.0}),
            ("timezone", 0, {"meaning": replace(m.TimestampMeaning(), timezone="UTC")}),
            (
                "range",
                0,
                {"meaning": replace(m.TimestampMeaning(), lower=(1, 1, 1, 0, 0, 0, 0))},
            ),
            (
                "byte_order",
                2,
                {"meaning": replace(m.UUIDMeaning(), byte_order="little_endian")},
            ),
            ("carrier", 2, {"carrier": "str"}),
            ("storage", 0, {"storage": "pg_int8"}),
            ("lower", 2, {"lower": 0}),
            ("label", 0, {"label": "stamp"}),
        ):
            observed = list(observations)
            observed[position] = replace(observed[position], **changes)
            producer_negatives[name] = refused(
                lambda observed=tuple(observed): p.bind_producer(
                    neutral, artifact, observed
                )
            )
        coordinated = replace(
            producer,
            fields=(
                replace(
                    producer.fields[0],
                    observation=replace(
                        observations[0],
                        meaning=replace(m.TimestampMeaning(), timezone="UTC"),
                    ),
                ),
                *producer.fields[1:],
            ),
        )
        wrong = pa.schema(
            [
                pa.field("occurred_at", pa.timestamp("us", "UTC"), nullable=False),
                *list(arrow.schema)[1:],
            ]
        )
        producer_negatives["coordinated"] = refused(
            lambda: a.verify_arrow_binding(
                a.ArrowResultBinding(coordinated, wrong), coordinated
            )
        )
        producer_negatives["absent_contract"] = refused(
            lambda: p.bind_producer(
                c.build_result_contract(checked), artifact, observations
            )
        )
        nominal_source = "type Stamp = Timestamp\n" + temporal_source(target).replace(
            "stamp: Timestamp", "stamp: Stamp"
        )
        nominal = build_neutral(
            root / f"temporal-nominal-{target}", {"main.pietto": nominal_source}
        )
        results["meaning_premise"][target] = dict(
            slot_refusals=slot_refusals,
            outside_projection=[
                outside.status,
                [(b.code, b.detail) for b in outside.blockers],
            ],
            entries=meaning_snapshot(bundle),
            default=[(b.code, b.detail) for b in absent.blockers],
            refusals=negatives,
            preparations=preparations,
            invalidated=invalidated,
            contract_invalidated=contract_invalidated,
            producer=producer_negatives,
            projection=dict(
                labels=[f.label for f in reused_contract.shape.fields],
                source_positions=[
                    f.meaning.source_port.ref.position
                    for f in reused_contract.shape.fields
                ],
                distinct_outputs=reused_contract.shape.fields[0].port
                is not reused_contract.shape.fields[2].port,
            ),
            nominal=meaning_refused(lambda: m.acquire_scalar_meaning(nominal)),
        )
        owned = a.build_owned_batch(arrow, temporal_rows(target))
        snapshot = temporal_snapshot(owned)
        temporal_value_oracle(snapshot)
        results["timestamp_values"][target] = dict(
            types=snapshot["types"][:2],
            ticks=snapshot["columns"][:2],
            components=snapshot["components"],
        )
        bad_times = (
            datetime(1970, 1, 1, tzinfo=timezone.utc),
            datetime(1970, 1, 1, tzinfo=timezone(timedelta(hours=2))),
            datetime(1970, 1, 1, fold=1),
            DatetimeSubclass(1970, 1, 1),
            date(1970, 1, 1),
            0,
            0.0,
            True,
            "1970-01-01",
            b"1970-01-01",
            CoercibleTemporal(),
            datetime(999, 12, 31, 23, 59, 59, 999999),
            datetime(9999, 12, 31, 23, 59, 59, 500000),
            float("nan"),
        )
        time_refusals = []
        for value in bad_times:
            row = temporal_rows(target)[0]
            row[0] = value
            time_refusals.append(
                refused(lambda row=row: a.build_owned_batch(arrow, [row]))
            )
        nullrow = temporal_rows(target)[0]
        nullrow[0] = None
        time_refusals.append(refused(lambda: a.build_owned_batch(arrow, [nullrow])))
        constructors = []
        for components in ((1900, 2, 29), (2000, 2, 30), (2000, 1, 1, 0, 0, 60)):
            try:
                datetime(
                    year=components[0],
                    month=components[1],
                    day=components[2],
                    second=60 if len(components) == 6 else 0,
                )
            except ValueError:
                constructors.append("PYTHON_CONSTRUCTOR")
            else:
                raise AssertionError("invalid calendar constructor accepted")
        schema_refusals = []
        for wrong_type in (
            pa.timestamp("s"),
            pa.timestamp("ms"),
            pa.timestamp("ns"),
            pa.timestamp("us", "UTC"),
            pa.int64(),
            pa.date32(),
            pa.date64(),
        ):
            schema = pa.schema(
                [
                    pa.field("occurred_at", wrong_type, nullable=False),
                    *list(arrow.schema)[1:],
                ]
            )
            schema_refusals.append(
                refused(
                    lambda schema=schema: a.verify_arrow_binding(
                        replace(arrow, schema=schema), producer
                    )
                )
            )
        schema_refusals += [
            refused(
                lambda: a.verify_arrow_binding(
                    replace(
                        arrow, schema=arrow.schema.with_metadata({b"timezone": b"none"})
                    ),
                    producer,
                )
            ),
            refused(
                lambda: a.verify_arrow_binding(
                    replace(
                        arrow,
                        schema=pa.schema(
                            [
                                arrow.schema[0].with_metadata({b"unit": b"us"}),
                                *list(arrow.schema)[1:],
                            ]
                        ),
                    ),
                    producer,
                )
            ),
        ]
        raw_refusals = []
        for tick in (-30610224000000001, 253402300799500000, -(2**63), 2**63 - 1):
            arrays = list(owned.slice(0, 1).columns)
            arrays[0] = pa.Array.from_buffers(
                pa.timestamp("us"), 1, [None, pa.py_buffer(struct.pack("<q", tick))]
            )
            bad = pa.RecordBatch.from_arrays(arrays, schema=arrow.schema)
            raw_refusals.append(refused(lambda: a.verify_batch(bad, arrow, producer)))
        results["timestamp_policy"][target] = dict(
            rows=time_refusals,
            constructors=constructors,
            schema=schema_refusals,
            raw_ticks=raw_refusals,
        )
        req0, req1 = (
            a.UUIDRepresentationRequest(producer.fields[i].field, "binary16")
            for i in (2, 3)
        )
        requests = (
            (),
            [],
            (None, None, req0),
            (None, None, req0, req1, None),
            (None, None, req0, req0),
            (None, None, req1, req0),
            (
                None,
                None,
                a.UUIDRepresentationRequest(other.fields[2].field, "binary16"),
                req1,
            ),
            (
                a.UUIDRepresentationRequest(producer.fields[0].field, "binary16"),
                None,
                req0,
                req1,
            ),
            (
                None,
                None,
                a.UUIDRepresentationRequest(req0.field, cast(Any, True)),
                req1,
            ),
            (None, None, a.UUIDRepresentationRequest(req0.field, "binary"), req1),
            (
                None,
                None,
                a.UUIDRepresentationRequest(req0.field, PolicySubclass("binary16")),
                req1,
            ),
            (None, None, a.IntegerWidthRequest(req0.field, 16), req1),
        )
        uuid_requests = [
            refused(lambda req=req: a.bind_arrow(producer, uuid_representations=req))
            for req in requests
        ]
        identifier = UUID(bytes=bytes.fromhex(UUID_HEX[0]))
        invalid_uuid = (
            (identifier.bytes, UUIDSubclass(int=1))
            if target == "postgres"
            else (identifier, BytesSubclass(identifier.bytes))
        )
        invalid_uuid = (
            *invalid_uuid,
            b"",
            b"x" * 15,
            b"x" * 17,
            bytearray(identifier.bytes),
            memoryview(identifier.bytes),
            str(identifier),
            1,
            True,
            CoercibleTemporal(),
        )
        uuid_rows = []
        for value in invalid_uuid:
            row = temporal_rows(target)[0]
            row[2] = value
            uuid_rows.append(refused(lambda row=row: a.build_owned_batch(arrow, [row])))
        nullrow = temporal_rows(target)[0]
        nullrow[2] = None
        uuid_rows.append(refused(lambda: a.build_owned_batch(arrow, [nullrow])))
        _, _, _, _, nullable = temporal_fixture(
            root / f"temporal-null-{target}", target, all_nullable=True
        )
        mixed_checked, mixed_bundle, mixed_artifact, mixed_contract, mixed = (
            temporal_fixture(root / f"temporal-mixed-{target}", target, mixed=True)
        )
        for representation in ("uuid", "binary16"):
            key = f"{target}/{representation}"
            selected = temporal_arrow(producer, representation=representation)
            rows = temporal_rows(target)
            batch = a.build_owned_batch(selected, rows)
            actual = temporal_snapshot(batch)
            temporal_value_oracle(actual, representation=representation)
            rows[0][:] = [None] * 4
            rows.clear()
            assert _exact(temporal_snapshot(batch), actual)
            results["uuid_values"][key] = dict(
                types=actual["types"][2:], bytes=actual["columns"][2:]
            )
            schema = []
            for wrong_type in (
                pa.binary(16) if representation == "uuid" else pa.uuid(),
                pa.binary(15),
                pa.binary(17),
                pa.binary(),
                pa.large_binary(),
                pa.string(),
                FakeUUID(),
            ):
                wrong = pa.schema(
                    [
                        *list(selected.schema)[:2],
                        pa.field("key_value", wrong_type, nullable=False),
                        selected.schema[3],
                    ]
                )
                schema.append(
                    refused(
                        lambda wrong=wrong: a.verify_arrow_binding(
                            replace(selected, schema=wrong), producer
                        )
                    )
                )
            forged = pa.schema(
                [
                    *list(selected.schema)[:2],
                    pa.field(
                        "key_value",
                        pa.binary(16),
                        nullable=False,
                        metadata={b"ARROW:extension:name": b"arrow.uuid"},
                    ),
                    selected.schema[3],
                ]
            )
            schema.append(
                refused(
                    lambda: a.verify_arrow_binding(
                        replace(selected, schema=forged), producer
                    )
                )
            )
            fake_array = pa.ExtensionArray.from_storage(
                FakeUUID(),
                pa.array([bytes.fromhex(v) for v in UUID_HEX], type=pa.binary(16)),
            )
            arrays = list(batch.columns)
            arrays[2] = fake_array
            bad = pa.RecordBatch.from_arrays(
                arrays,
                schema=pa.schema(
                    [
                        *list(selected.schema)[:2],
                        pa.field("key_value", fake_array.type, nullable=False),
                        selected.schema[3],
                    ]
                ),
            )
            schema.append(refused(lambda: a.verify_batch(bad, selected, producer)))
            results["uuid_policy"][key] = dict(
                requests=uuid_requests, rows=uuid_rows, schema=schema
            )
            mixed_arrow = temporal_arrow(
                mixed, representation=representation, mixed=True
            )
            before = export_result_contract(
                mixed_contract, mixed_checked
            ).canonical_bytes
            mixed_batch = a.build_owned_batch(
                mixed_arrow, temporal_rows(target, mixed=True)
            )
            mixed_snapshot = temporal_snapshot(mixed_batch)
            temporal_value_oracle(
                mixed_snapshot, representation=representation, mixed=True
            )
            assert (
                export_result_contract(mixed_contract, mixed_checked).canonical_bytes
                == before
            )
            results["temporal_empty_mixed"][key] = dict(
                empty=temporal_snapshot(
                    a.build_owned_batch(selected, [], limits=a.BatchLimits(bytes=0))
                ),
                all_null=temporal_snapshot(
                    a.build_owned_batch(
                        temporal_arrow(nullable, representation=representation),
                        [[None] * 4, [None] * 4],
                    )
                ),
                mixed=mixed_snapshot,
            )
            one = temporal_rows(target)[0]
            exact = a.build_owned_batch(selected, [one], limits=a.BatchLimits(bytes=52))
            mixed_one = [
                datetime(1970, 1, 1),
                None,
                identifier if target == "postgres" else identifier.bytes,
                None,
                7,
                True if target == "postgres" else 1,
                -0.0,
                "é",
                decimal_literal(TEMPORAL_DECIMAL, 4),
            ]
            mixed_exact = a.build_owned_batch(
                mixed_arrow, [mixed_one], limits=a.BatchLimits(bytes=131)
            )
            retained_data = pa.py_buffer(struct.pack("<4q", 0, 2**63 - 1, 0, 0))
            arrays = [
                pa.Array.from_buffers(
                    pa.timestamp("us"), 4, [None, retained_data]
                ).slice(1, 1),
                pa.array([None], type=pa.timestamp("us")),
            ]
            for index in (2, 3):
                arrays.append(a.build_owned_batch(selected, [one]).column(index))
            # Both Timestamp columns retain large backing storage, and the first has an invalid tick.
            arrays[1] = pa.Array.from_buffers(
                pa.timestamp("us"), 4, [None, retained_data]
            ).slice(2, 1)
            invalid_retained = pa.RecordBatch.from_arrays(
                arrays, schema=selected.schema
            )
            limits = [
                refused(
                    lambda: a.build_owned_batch(
                        selected, [one], limits=a.BatchLimits(bytes=51)
                    )
                ),
                refused(
                    lambda: a.build_owned_batch(
                        mixed_arrow, [mixed_one], limits=a.BatchLimits(bytes=130)
                    )
                ),
                refused(
                    lambda: a.verify_batch(
                        invalid_retained,
                        selected,
                        producer,
                        limits=a.BatchLimits(bytes=52),
                    )
                ),
            ]
            original_array = pa.array

            def forbidden_array(*args, **kwargs):
                raise AssertionError("Arrow allocation preceded row preflight")

            try:
                setattr(pa, "array", forbidden_array)
                preflight = [
                    refused(
                        lambda: a.build_owned_batch(
                            selected, [one], limits=a.BatchLimits(bytes=51)
                        )
                    ),
                    refused(
                        lambda: a.build_owned_batch(
                            selected, [one], limits=a.BatchLimits(rows=0)
                        )
                    ),
                ]
            finally:
                setattr(pa, "array", original_array)
            nullable_arrow = temporal_arrow(nullable, representation=representation)
            times = pa.Array.from_buffers(
                pa.timestamp("us"),
                4,
                [
                    pa.py_buffer(b"\x0d"),
                    pa.py_buffer(struct.pack("<4q", 0, 2**63 - 1, -1, 1)),
                ],
            ).slice(1, 2)
            raw = pa.Array.from_buffers(
                pa.binary(16),
                4,
                [
                    pa.py_buffer(b"\x0d"),
                    pa.py_buffer(
                        bytes.fromhex(UUID_HEX[0])
                        + b"\xff" * 16
                        + bytes.fromhex(UUID_HEX[0])
                        + bytes(16)
                    ),
                ],
            ).slice(1, 2)
            identifiers = (
                pa.ExtensionArray.from_storage(pa.uuid(), raw)
                if representation == "uuid"
                else raw
            )
            supplied = pa.RecordBatch.from_arrays(
                [times, times, identifiers, identifiers], schema=nullable_arrow.schema
            )
            a.verify_batch(supplied, nullable_arrow, nullable)
            short = []
            for typ, width in ((pa.timestamp("us"), 8), (pa.binary(16), 16)):
                try:
                    pa.Array.from_buffers(
                        typ, 1, [None, pa.py_buffer(bytes(width - 1))]
                    )
                except (ValueError, pa.ArrowException):
                    short.append("ARROW_CONSTRUCTOR")
                else:
                    raise AssertionError("short buffer accepted")
            metadata = refused(
                lambda: a.verify_batch(
                    supplied.replace_schema_metadata({b"meaning": b"approved"}),
                    nullable_arrow,
                    nullable,
                )
            )
            null_refusals = []
            for index in (0, 2):
                arrays = list(batch.slice(0, 1).columns)
                arrays[index] = pa.array([None], type=selected.schema[index].type)
                actual_null = pa.RecordBatch.from_arrays(arrays, schema=selected.schema)
                null_refusals.append(
                    refused(lambda: a.verify_batch(actual_null, selected, producer))
                )
            results["temporal_resources"][key] = dict(
                nonnullable_nulls=null_refusals,
                allowance=52,
                rows=exact.num_rows,
                mixed_allowance=131,
                mixed_rows=mixed_exact.num_rows,
                limits=limits,
                preflight=preflight,
                sliced=temporal_snapshot(supplied),
                offsets=[col.offset for col in supplied.columns],
                short=short,
                metadata=metadata,
            )
            mutations = []
            # In-domain time shift and a valid but different UUID byte order.
            changed_rows = temporal_rows(target)
            changed_rows[2][0] = datetime(1970, 1, 1, 0, 0, 0, 1)
            mutations.append(a.build_owned_batch(selected, changed_rows))
            changed_rows = temporal_rows(target)
            changed_rows[0][2] = (
                UUID(bytes=identifier.bytes_le)
                if target == "postgres"
                else identifier.bytes_le
            )
            mutations.append(a.build_owned_batch(selected, changed_rows))
            for indices in (
                [1, 0, *range(2, 10)],
                list(range(9)),
                [0, 1, 2, 3, 4, 5, 6, 7, 9],
            ):
                mutations.append(batch.take(indices))
            changed_rows = temporal_rows(target)
            changed_rows[0][1] = datetime(*TIME_COMPONENTS[0])
            mutations.append(a.build_owned_batch(selected, changed_rows))
            detected = []
            for changed in mutations:
                a.verify_batch(changed, selected, producer)
                try:
                    temporal_value_oracle(
                        temporal_snapshot(changed), representation=representation
                    )
                except ValueError:
                    detected.append("VALUE_CORRESPONDENCE")
                else:
                    raise AssertionError(
                        "domain-valid temporal substitution escaped oracle"
                    )
            builder = a.build_owned_batch

            def injected(binding, rows, **kwargs):
                changed = [list(r) for r in rows]
                changed[2][0] = datetime(1970, 1, 1, 0, 0, 0, 1)
                return builder(binding, changed, **kwargs)

            try:
                a.build_owned_batch = injected
                try:
                    temporal_value_oracle(
                        temporal_snapshot(
                            a.build_owned_batch(selected, temporal_rows(target))
                        ),
                        representation=representation,
                    )
                except ValueError:
                    detected.append("VALUE_CORRESPONDENCE")
                else:
                    raise AssertionError("injected temporal builder escaped oracle")
            finally:
                a.build_owned_batch = builder
            results["temporal_correspondence"][key] = detected
        for kind, checked_, neutral_ in (
            ("temporal", checked, neutral),
            ("mixed", mixed_checked, mixed_contract),
        ):
            exported = export_result_contract(neutral_, checked_)
            verify_bound_export(exported, checked_)
            assert (
                pure.encode_document(
                    pure.decode_contract(exported.canonical_bytes).document
                )
                == exported.canonical_bytes
            )
            results["temporal_codec"][target + "/" + kind] = (
                exported.canonical_bytes.decode()
            )
        original = export_result_contract(neutral, checked)
        swapped = original.view.document
        source = swapped["scalar_meaning"]["sources"]
        source[2]["port"], source[3]["port"] = source[3]["port"], source[2]["port"]
        pure_view = pure.decode_contract(pure.encode_document(swapped))
        results["meaning_premise"][target]["portable_graft"] = refused(
            lambda: verify_contract_correspondence(pure_view, neutral, checked)
        )
    return results


def verify_temporal_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        targets = {"postgres", "mysql"}
        keys = {f"{t}/{r}" for t in targets for r in ("uuid", "binary16")}
        for name in ("meaning_premise", "timestamp_values", "timestamp_policy"):
            if set(cases[name]) != targets:
                raise ValueError("meaning/timestamp target denominator")
        for name in (
            "uuid_values",
            "uuid_policy",
            "temporal_empty_mixed",
            "temporal_resources",
            "temporal_correspondence",
        ):
            if set(cases[name]) != keys:
                raise ValueError("UUID representation denominator")
        if set(cases["temporal_codec"]) != {
            f"{t}/{k}" for t in targets for k in ("temporal", "mixed")
        }:
            raise ValueError("temporal canonical denominator")
        time_law = dict(
            calendar="proleptic_gregorian",
            resolution="microsecond",
            timezone="absent",
            lower=[1000, 1, 1, 0, 0, 0, 0],
            upper=[9999, 12, 31, 23, 59, 59, 499999],
        )
        uuid_law = dict(byte_order="big_endian", byte_width=16)
        entries = [
            dict(
                ordinal=i,
                source_position=i,
                canonical="Timestamp" if i < 2 else "UUID",
                law=time_law if i < 2 else uuid_law,
            )
            for i in range(4)
        ]
        for target in ("postgres", "mysql"):
            expected = dict(
                slot_refusals=[
                    ["BLOCKED", [["PIE-B1008", "scalar_meaning_correspondence"]]]
                ]
                * 2,
                outside_projection=[
                    "BLOCKED",
                    [["PIE-B1003", "scalar_meaning_requires_field_projection"]],
                ],
                entries=entries,
                default=[["PIE-B1004", "logical_temporal_or_uuid_meaning_missing"]] * 4,
                refusals={
                    "foreign_root": "MEANING_ROOT",
                    **dict.fromkeys(
                        ("missing", "extra", "reordered", "field", "type"),
                        "MEANING_FIELDS",
                    ),
                    **dict.fromkeys(
                        ("calendar", "endpoint", "byte_order"), "MEANING_LAW"
                    ),
                },
                preparations=["INPUT_REJECTED"] * 9,
                invalidated=True,
                contract_invalidated="MEANING_FIELDS",
                producer={
                    **dict.fromkeys(
                        (
                            "precision",
                            "float_precision",
                            "timezone",
                            "range",
                            "byte_order",
                            "carrier",
                            "storage",
                            "lower",
                            "label",
                            "coordinated",
                        ),
                        "PRODUCER_OBSERVATION",
                    ),
                    "absent_contract": "PRODUCER_ROOT",
                },
                projection=dict(
                    labels=[f"selected_{i}" for i in range(5)],
                    source_positions=[2, 0, 2, 1, 3],
                    distinct_outputs=True,
                ),
                nominal="MEANING_FIELDS",
                portable_graft="CORRESPONDENCE",
            )
            if not _exact(cases["meaning_premise"][target], expected):
                raise ValueError("upstream meaning authority evidence")
            values = temporal_expected()
            if not _exact(
                cases["timestamp_values"][target],
                dict(
                    types=["timestamp[us]"] * 2,
                    ticks=values["columns"][:2],
                    components=values["components"],
                ),
            ):
                raise ValueError("exact timestamp tick/component evidence")
            if not _exact(
                cases["timestamp_policy"][target],
                dict(
                    rows=["VALUE_DOMAIN"] * 14 + ["NULL"],
                    constructors=["PYTHON_CONSTRUCTOR"] * 3,
                    schema=["ARROW_BINDING"] * 9,
                    raw_ticks=["VALUE_DOMAIN"] * 4,
                ),
            ):
                raise ValueError("timestamp policy/invalid tick evidence")
            for representation in ("uuid", "binary16"):
                key = f"{target}/{representation}"
                expected = temporal_expected(representation=representation)
                if not _exact(
                    cases["uuid_values"][key],
                    dict(types=expected["types"][2:], bytes=expected["columns"][2:]),
                ):
                    raise ValueError("UUID standard bytes/type evidence")
                if not _exact(
                    cases["uuid_policy"][key],
                    dict(
                        requests=["ARROW_ADAPTATION"] * 12,
                        rows=["VALUE_DOMAIN"] * 11 + ["NULL"],
                        schema=["ARROW_BINDING"] * 8 + ["ARROW_SCHEMA"],
                    ),
                ):
                    raise ValueError("UUID identity/carrier/extension evidence")
                if not _exact(
                    cases["temporal_empty_mixed"][key],
                    dict(
                        empty=temporal_expected(
                            representation=representation, state="empty"
                        ),
                        all_null=temporal_expected(
                            representation=representation,
                            state="null",
                            all_nullable=True,
                        ),
                        mixed=temporal_expected(
                            representation=representation, mixed=True
                        ),
                    ),
                ):
                    raise ValueError("temporal typed empty/null/mixed evidence")
                sliced = temporal_expected(
                    representation=representation, state="null", all_nullable=True
                )
                sliced["columns"] = [
                    [None, -1],
                    [None, -1],
                    [None, UUID_HEX[0]],
                    [None, UUID_HEX[0]],
                ]
                sliced["components"] = [[None, [1969, 12, 31, 23, 59, 59, 999999]]] * 2
                resource = dict(
                    nonnullable_nulls=["NULL", "NULL"],
                    allowance=52,
                    rows=1,
                    mixed_allowance=131,
                    mixed_rows=1,
                    limits=["LIMIT"] * 3,
                    preflight=["LIMIT"] * 2,
                    sliced=sliced,
                    offsets=[1] * 4,
                    short=["ARROW_CONSTRUCTOR"] * 2,
                    metadata="ARROW_SCHEMA",
                )
                if not _exact(cases["temporal_resources"][key], resource):
                    raise ValueError("temporal retained-buffer/resource evidence")
                if (
                    cases["temporal_correspondence"][key]
                    != ["VALUE_CORRESPONDENCE"] * 7
                ):
                    raise ValueError("temporal independent value correspondence")
            for kind in ("temporal", "mixed"):
                doc = pure.decode_contract(
                    cases["temporal_codec"][target + "/" + kind].encode()
                ).document
                kinds = ["Timestamp", "Timestamp", "UUID", "UUID"] + (
                    ["Int", "Bool", "Float", "Text", "Decimal"]
                    if kind == "mixed"
                    else []
                )
                fields = doc["fields"]
                sources = doc["scalar_meaning"]["sources"]
                if (
                    [f["label"] for f in fields] != list(TEMPORAL_LABELS[: len(kinds)])
                    or [f["canonical"] for f in fields]
                    != [dict(kind="builtin", name=k, symbol=None) for k in kinds]
                    or [f.get("meaning") for f in fields]
                    != [0, 1, 2, 3] + ([None] * 5 if kind == "mixed" else [])
                    or [f["nullability"] for f in fields]
                    != [
                        "nullable" if i in (1, 3, 7) else "non_null"
                        for i in range(len(kinds))
                    ]
                    or [s["port"] for s in sources]
                    != [dict(kind="source_port", position=i) for i in range(4)]
                ):
                    raise ValueError("complete temporal neutral descriptor evidence")
    except (KeyError, TypeError, AttributeError, pure.ContractDocumentError) as exc:
        raise ValueError("temporal report evidence") from exc


# S08 fixtures use legal sources; these constants are independent of the mapper.
FINITE_NAMES = (
    "small",
    "medium",
    "large",
    "flag",
    "ratio",
    "text",
    "wide_text",
    "amount",
    "wide_amount",
    "stamp",
    "identifier",
    "binary_identifier",
    "other",
)
FINITE_KINDS = (
    "Int",
    "Int",
    "Int",
    "Bool",
    "Float",
    "Text",
    "Text",
    "Decimal(9, 2)",
    "Decimal(65, 30)",
    "Timestamp",
    "UUID",
    "UUID",
    "Int",
)
FINITE_LABELS = tuple("selected_" + name for name in FINITE_NAMES)
FINITE_TYPES = (
    "int16",
    "int32",
    "int64",
    "bool",
    "double",
    "string",
    "large_string",
    "decimal128(9, 2)",
    "decimal256(65, 30)",
    "timestamp[us]",
    "extension<arrow.uuid>",
    "fixed_size_binary[16]",
    "int16",
)
FINITE_GROUPS = (
    "finite_mixed_values",
    "finite_empty",
    "finite_all_null",
    "carrier_labels",
    "carrier_label_refusals",
    "finite_resources",
    "finite_correspondence",
    "finite_codec",
    "reader_values",
    "reader_empty_null",
    "reader_extent",
    "reader_terminal",
    "reader_lifecycle",
    "reader_limits",
    "reader_rechunk",
    "reader_identity",
    "reader_correspondence",
    "reader_incremental",
)


def finite_fixture(directory, target, *, all_nullable=False):
    from pietto._project.project_result_binding import bind_producer
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_sql_emission import emit_project_sql

    text = "shape Row:\n" + "".join(
        f"    {name}: {kind} {'nullable' if all_nullable or i % 2 else 'not null'}\n"
        for i, (name, kind) in enumerate(zip(FINITE_NAMES, FINITE_KINDS, strict=True))
    )
    text += f'source rows: Row is {target}.table("opaque.result.fixture")\ntable result:\n    from rows\n    select:\n'
    text += "".join(
        f"        {label} = {name}\n"
        for label, name in zip(FINITE_LABELS, FINITE_NAMES, strict=True)
    )
    checked = build_neutral(directory, {"main.pietto": text})
    meaning = acquire_scalar_meaning(checked)
    # Reuse authored physical declarations, not product-derived descriptions.
    base = json.loads(temporal_input(target, mixed=True))
    old_fields = base["sources"][0]["fields"]
    old_observed = temporal_observations(target, mixed=True)
    positions = (4, 4, 4, 5, 6, 7, 7, 8, 8, 0, 2, 3, 4)
    descriptions, observed = [], []
    from pietto._project.project_result_binding import DecimalObservation

    for i, position in enumerate(positions):
        description = json.loads(json.dumps(old_fields[position]))
        description.update(ordinal=i, name=FINITE_NAMES[i], column=FINITE_NAMES[i])
        rep = description["representation"]
        rep["nullable"] = bool(all_nullable or i % 2)
        observation = replace(old_observed[position], ordinal=i, label=FINITE_LABELS[i])
        if i in (0, 1, 2, 12):
            bits = {0: 32, 1: 32, 2: 64, 12: 16}[i]
            lower, upper = (
                (-100, 100)
                if i in (0, 12)
                else (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1)
            )
            rep["storage"] = dict(kind=width_storage(target, bits))
            rep["domain"] = dict(kind="int_range", min=str(lower), max=str(upper))
            observation = replace(
                observation,
                storage=width_storage(target, bits),
                lower=lower,
                upper=upper,
            )
        elif i in (7, 8):
            precision, scale = (9, 2) if i == 7 else (65, 30)
            rep["storage"].update(precision=precision, scale=scale)
            rep["domain"].update(precision=precision, scale=scale)
            observation = replace(
                observation, decimal=DecimalObservation(precision, scale)
            )
        descriptions.append(description)
        observed.append(observation)
    base["sources"][0]["fields"] = descriptions
    encoded = json.dumps(base).encode()
    outcome = emit_project_sql(checked, encoded, scalar_meaning=meaning)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    neutral = build_result_contract(checked, scalar_meaning=meaning)
    producer = bind_producer(neutral, outcome.artifact, tuple(observed))
    return checked, meaning, outcome.artifact, neutral, producer, encoded


def finite_policy(producer, *, labels=True, wide=False) -> dict[str, Any]:
    from pietto._project import project_arrow_result as a

    fields = producer.fields
    return dict(
        integer_widths=tuple(
            a.IntegerWidthRequest(b.field, 16) if i == 0 else None
            for i, b in enumerate(fields)
        ),
        text_offset_widths=tuple(
            a.TextOffsetWidthRequest(b.field, 64)
            if i == 6 or (wide and i == 5)
            else None
            for i, b in enumerate(fields)
        ),
        decimal_widths=tuple(
            a.DecimalWidthRequest(b.field, 256) if wide and i == 7 else None
            for i, b in enumerate(fields)
        ),
        uuid_representations=tuple(
            a.UUIDRepresentationRequest(b.field, "binary16") if i == 11 else None
            for i, b in enumerate(fields)
        ),
        field_labels=tuple(
            a.ArrowFieldLabelRequest(b.field, "repeated") if i in (0, 5, 12) else None
            for i, b in enumerate(fields)
        )
        if labels
        else None,
    )


def finite_rows(target, *, state="values") -> list[list[Any]]:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    first = [
        1,
        222,
        BIG,
        False if target == "postgres" else 0,
        -0.0,
        "",
        "é",
        Decimal("12.34"),
        Decimal("9876543210.987654321098765432109876543210"),
        datetime(1969, 12, 31, 23, 59, 59, 999999),
        UUID(hex="00112233445566778899aabbccddeeff"),
        UUID(hex="ffeeddccbbaa99887766554433221100"),
        -7,
    ]
    second = [
        0,
        0,
        -BIG,
        True if target == "postgres" else 1,
        0.0,
        "e\u0301",
        "😀",
        Decimal("0.00"),
        Decimal("0E-30"),
        datetime(2000, 2, 29, 12, 34, 56, 123456),
        UUID(int=0),
        UUID(int=(1 << 128) - 1),
        9,
    ]
    if target == "mysql":
        for row in (first, second):
            for i in (10, 11):
                row[i] = row[i].bytes
    third = [None if i % 2 else v for i, v in enumerate(first)]
    rows = [first, second, third, list(first)]
    if state == "empty":
        return []
    if state == "null":
        return [[None] * 13 for _ in range(2)]
    if state == "one":
        return rows[:1]
    if state == "first_null":
        return [[None] * 13, *rows]
    return rows


def finite_expected(
    *, state="values", labels=True, all_nullable=False, wide=False
) -> dict[str, Any]:
    first = [
        1,
        222,
        BIG,
        False,
        "8000000000000000",
        "",
        "c3a9",
        "1234",
        "9876543210987654321098765432109876543210",
        -1,
        "00112233445566778899aabbccddeeff",
        "ffeeddccbbaa99887766554433221100",
        -7,
    ]
    second = [
        0,
        0,
        -BIG,
        True,
        "0000000000000000",
        "65cc81",
        "f09f9880",
        "0",
        "0",
        951827696123456,
        "00000000000000000000000000000000",
        "ffffffffffffffffffffffffffffffff",
        9,
    ]
    rows = [
        first,
        second,
        [None if i % 2 else v for i, v in enumerate(first)],
        list(first),
    ]
    if state == "empty":
        rows = []
    elif state == "null":
        rows = [[None] * 13 for _ in range(2)]
    elif state == "one":
        rows = rows[:1]
    elif state == "first_null":
        rows = [[None] * 13, *rows]
    types: list[str] = list(FINITE_TYPES)
    if wide:
        types[5], types[7] = "large_string", "decimal256(9, 2)"
    return dict(
        fields=[
            dict(
                ordinal=i,
                label="repeated" if labels and i in (0, 5, 12) else label,
                type=types[i],
                nullable=bool(all_nullable or i % 2),
                metadata=None,
            )
            for i, label in enumerate(FINITE_LABELS)
        ],
        rows=rows,
        valid=[[v is not None for v in row] for row in rows],
        schema_metadata=None,
    )


def finite_snapshot(batch) -> dict[str, Any]:
    import struct

    pa = importlib.import_module("pyarrow")
    columns = []
    for column in batch.columns:
        storage = column.storage if type(column.type) is type(pa.uuid()) else column
        values = []
        for j, scalar in enumerate(storage):
            if not scalar.is_valid:
                values.append(None)
            elif (
                pa.types.is_decimal(storage.type)
                or pa.types.is_timestamp(storage.type)
                or pa.types.is_fixed_size_binary(storage.type)
            ):
                width = (
                    storage.type.byte_width
                    if pa.types.is_fixed_size_binary(storage.type)
                    else storage.type.bit_width // 8
                )
                data = memoryview(storage.buffers()[1])
                raw = data[
                    (storage.offset + j) * width : (storage.offset + j + 1) * width
                ]
                value = (
                    bytes(raw).hex()
                    if pa.types.is_fixed_size_binary(storage.type)
                    else int.from_bytes(raw, "little", signed=True)
                )
                values.append(
                    str(value) if pa.types.is_decimal(storage.type) else value
                )
            elif pa.types.is_floating(storage.type):
                values.append(struct.pack(">d", scalar.as_py()).hex())
            elif pa.types.is_string(storage.type) or pa.types.is_large_string(
                storage.type
            ):
                values.append(scalar.as_py().encode("utf-8").hex())
            else:
                values.append(scalar.as_py())
        columns.append(values)
    return dict(
        fields=[
            dict(
                ordinal=i,
                label=f.name,
                type=str(f.type),
                nullable=f.nullable,
                metadata=f.metadata,
            )
            for i, f in enumerate(batch.schema)
        ],
        rows=[list(row) for row in zip(*columns, strict=True)],
        valid=[
            [column[j].is_valid for column in batch.columns]
            for j in range(batch.num_rows)
        ],
        schema_metadata=batch.schema.metadata,
    )


def finite_oracle(snapshot, **kwargs):
    if not _exact(snapshot, finite_expected(**kwargs)):
        raise ValueError("finite positional source/value correspondence")


def finite_charge(*, state="values", wide=False):
    # Literal physical byte widths, independent of product admission/mapping.
    rows = finite_expected(state=state)["rows"]
    r = len(rows)
    fixed = 6 * 8 + 16 + 32 + 2 * 16 + 8  # four Int, Bool, Float, Timestamp
    if wide:
        fixed += 16
    offsets = 16 if wide else 12
    text_bytes = sum(
        len(bytes.fromhex(row[i])) for row in rows for i in (5, 6) if row[i] is not None
    )
    return 13 * ((r + 7) // 8) + fixed * r + offsets * (r + 1) + text_bytes


def finite_label_fixture(directory, count):
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import bind_producer
    from pietto._project.project_sql_emission import emit_project_sql

    text = (
        source("postgres").split("    select:\n")[0]
        + "    select:\n"
        + "".join(f"        output_{i} = id\n" for i in range(count))
    )
    checked = build_neutral(directory, {"main.pietto": text})
    emitted = emit_project_sql(checked, emission_input("postgres"))
    assert emitted.status == "VERIFIED" and emitted.artifact is not None
    neutral = build_result_contract(checked)
    return bind_producer(
        neutral,
        emitted.artifact,
        tuple(
            replace(observations("postgres")[0], ordinal=i, label=f"output_{i}")
            for i in range(count)
        ),
    )


def finite_observe(binding, rows, **kwargs):
    from pietto._project.project_arrow_result import build_owned_batch

    snapshot = finite_snapshot(build_owned_batch(binding, rows))
    finite_oracle(snapshot, **kwargs)
    return snapshot


def run_finite_cases(root):
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_binding as p
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
        verify_contract_correspondence,
    )
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto.parser_api import parse_source
    from pietto.semantic import analyze

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {key: {} for key in FINITE_GROUPS}
    for target in ("postgres", "mysql"):
        checked, meaning, artifact, neutral, producer, encoded = finite_fixture(
            root / ("finite-" + target), target
        )
        nchecked, _, _, nneutral, nproducer, _ = finite_fixture(
            root / ("finite-null-" + target), target, all_nullable=True
        )
        selected = a.bind_arrow(producer, **finite_policy(producer))
        default = a.bind_arrow(producer, **finite_policy(producer, labels=False))
        nullable = a.bind_arrow(nproducer, **finite_policy(nproducer))
        wide = a.bind_arrow(producer, **finite_policy(producer, wide=True))
        rows = finite_rows(target)
        actual = a.build_owned_batch(selected, rows)
        measured = finite_snapshot(actual)
        finite_oracle(measured)
        results["finite_mixed_values"][target] = dict(
            values=measured,
            wide=finite_observe(wide, rows, wide=True),
            semantic_labels=[b.field.label for b in producer.fields],
            producer_labels=[b.observation.label for b in producer.fields],
            distinct_sources=len(
                {id(b.column.source_field.field) for b in producer.fields}
            ),
        )
        empty = a.build_owned_batch(selected, [])
        no_meaning = emit_project_sql(checked, encoded)
        foreign_meaning = emit_project_sql(
            checked, encoded, scalar_meaning=nneutral.scalar_meaning
        )
        wrong_policy = finite_policy(producer)
        wrong_policy["integer_widths"] = (
            None,
            a.IntegerWidthRequest(producer.fields[1].field, 16),
            *(None,) * 11,
        )
        untyped = pa.RecordBatch.from_arrays(
            [pa.nulls(0) for _ in range(13)], names=selected.schema.names
        )
        wrong_unit = pa.RecordBatch.from_arrays(
            [
                pa.array([], type=pa.timestamp("ms")) if i == 9 else empty.column(i)
                for i in range(13)
            ],
            schema=pa.schema(
                [
                    pa.field(
                        f.name,
                        pa.timestamp("ms") if i == 9 else f.type,
                        nullable=f.nullable,
                    )
                    for i, f in enumerate(selected.schema)
                ]
            ),
        )
        missing_decimal = pa.RecordBatch.from_arrays(
            [
                pa.array([], type=pa.decimal128(8, 2)) if i == 7 else empty.column(i)
                for i in range(13)
            ],
            schema=pa.schema(
                [
                    pa.field(
                        f.name,
                        pa.decimal128(8, 2) if i == 7 else f.type,
                        nullable=f.nullable,
                    )
                    for i, f in enumerate(selected.schema)
                ]
            ),
        )
        results["finite_empty"][target] = dict(
            snapshot=finite_snapshot(empty),
            zero_fields=refused(
                lambda: a.verify_batch(
                    pa.RecordBatch.from_arrays([], names=[]), selected, producer
                )
            ),
            untyped=refused(lambda: a.verify_batch(untyped, selected, producer)),
            wrong_unit=refused(lambda: a.verify_batch(wrong_unit, selected, producer)),
            precision=refused(
                lambda: a.verify_batch(missing_decimal, selected, producer)
            ),
            request=refused(lambda: a.bind_arrow(producer, **wrong_policy)),
            meaning=[no_meaning.status, foreign_meaning.status],
        )
        nulls = a.build_owned_batch(nullable, finite_rows(target, state="null"))
        invalid_null = pa.RecordBatch.from_arrays(nulls.columns, schema=selected.schema)
        bad_row = list(rows[0])
        bad_row[4] = 0
        results["finite_all_null"][target] = dict(
            all_null=finite_snapshot(nulls),
            first_null=finite_observe(
                nullable,
                finite_rows(target, state="first_null"),
                all_nullable=True,
                state="first_null",
            ),
            one=finite_observe(selected, rows[:1], state="one"),
            actual_nonnullable=refused(
                lambda: a.verify_batch(invalid_null, selected, producer)
            ),
            row_nonnullable=refused(
                lambda: a.build_owned_batch(selected, [[None] * 13])
            ),
            coercion=refused(lambda: a.build_owned_batch(selected, [bad_row])),
        )
        results["carrier_labels"][target] = dict(
            populated=measured,
            empty=finite_snapshot(empty),
            all_null=finite_snapshot(nulls),
            default=finite_observe(default, rows, labels=False),
        )

        requests = finite_policy(producer)["field_labels"]
        assert requests is not None
        request = requests[0]
        assert request is not None
        label_bad: dict[str, Any] = dict(
            short=requests[:-1],
            extra=(*requests, None),
            list=list(requests),
            wrong_kind=(a.IntegerWidthRequest(request.field, 16), *requests[1:]),
            foreign=(
                a.ArrowFieldLabelRequest(nproducer.fields[0].field, "repeated"),
                *requests[1:],
            ),
            reorder=requests[::-1],
            reuse=(request, request, *requests[2:]),
        )
        for name, label in (
            ("empty", ""),
            ("nul", "a\0b"),
            ("surrogate", "\ud800"),
            ("codepoints", "x" * 1025),
            ("utf8", "😀" * 257),
            ("type", b"x"),
            ("subclass", TextSubclass("x")),
        ):
            label_bad[name] = (
                a.ArrowFieldLabelRequest(request.field, cast(Any, label)),
                *requests[1:],
            )
        refusals: dict[str, Any] = {
            name: refused(
                lambda policy=policy: a.bind_arrow(producer, field_labels=policy)
            )
            for name, policy in label_bad.items()
        }
        for slot in ("field", "label"):
            broken = copy(request)
            object.__delattr__(broken, slot)
            refusals["deleted_" + slot] = refused(
                lambda: a.bind_arrow(producer, field_labels=(broken, *requests[1:]))
            )
        absent = copy(selected)
        object.__delattr__(absent, "field_labels")
        refusals["deleted_policy"] = refused(
            lambda: a.verify_batch(empty, absent, producer)
        )
        refusals["cleared_policy"] = refused(
            lambda: a.verify_arrow_binding(
                replace(selected, field_labels=None), producer
            )
        )
        refusals["no_policy"] = refused(
            lambda: a.verify_batch(actual, default, producer)
        )
        renamed_schema = pa.schema(
            [
                pa.field("changed" if i == 12 else f.name, f.type, nullable=f.nullable)
                for i, f in enumerate(selected.schema)
            ]
        )
        renamed = pa.RecordBatch.from_arrays(actual.columns, schema=renamed_schema)
        refusals["changed_name"] = refused(
            lambda: a.verify_batch(renamed, selected, producer)
        )
        forged_obs = [b.observation for b in producer.fields]
        forged_obs[0] = replace(forged_obs[0], label="repeated")
        refusals["producer_label"] = refused(
            lambda: p.bind_producer(neutral, artifact, tuple(forged_obs))
        )
        meta = actual.replace_schema_metadata({b"field_labels": b"repeated"})
        refusals["metadata"] = refused(lambda: a.verify_batch(meta, selected, producer))
        field_meta = pa.schema(
            [
                f.with_metadata({b"label": b"repeated"}) if i == 5 else f
                for i, f in enumerate(selected.schema)
            ]
        )
        refusals["field_metadata"] = refused(
            lambda: a.verify_batch(
                pa.RecordBatch.from_arrays(actual.columns, schema=field_meta),
                selected,
                producer,
            )
        )
        # A coherently supplied new policy remains another legal representation.
        renamed_requests = (
            *requests[:12],
            a.ArrowFieldLabelRequest(producer.fields[12].field, "changed"),
        )
        coherent = a.bind_arrow(
            producer, **{**finite_policy(producer), "field_labels": renamed_requests}
        )
        a.verify_batch(renamed, coherent, producer)
        refusals["coherent_policy"] = finite_snapshot(renamed)["fields"][12]["label"]
        parsed = parse_source(
            source(target).replace("        other\n", "        renamed = other\n")
        )
        assert parsed.ast is not None and not parsed.diagnostics
        refusals["language"] = [d.code for d in analyze(parsed.ast).diagnostics]
        results["carrier_label_refusals"][target] = refusals

        resource: dict[str, Any] = {}
        for width in (False, True):
            binding = a.bind_arrow(nproducer, **finite_policy(nproducer, wide=width))
            for state in ("values", "empty", "null"):
                cost = finite_charge(state=state, wide=width)
                values = finite_rows(target, state=state)
                built = a.build_owned_batch(
                    binding, values, limits=a.BatchLimits(bytes=cost)
                )
                a.verify_batch(
                    built, binding, nproducer, limits=a.BatchLimits(bytes=cost)
                )
                resource[f"{state}/{'wide' if width else 'default'}"] = dict(
                    charge=cost,
                    rows=built.num_rows,
                    owned_under=refused(
                        lambda: a.build_owned_batch(
                            binding, values, limits=a.BatchLimits(bytes=cost - 1)
                        )
                    ),
                    supplied_under=refused(
                        lambda: a.verify_batch(
                            built,
                            binding,
                            nproducer,
                            limits=a.BatchLimits(bytes=cost - 1),
                        )
                    ),
                )
        offset_rows = [[None] * 13] * 10 + rows
        sliced = a.build_owned_batch(nullable, offset_rows).slice(9, 5)
        a.verify_batch(sliced, nullable, nproducer)
        resource["offset"] = dict(
            offsets=[c.offset for c in sliced.columns], snapshot=finite_snapshot(sliced)
        )
        retained_rows = [list(rows[0]) for _ in range(32)]
        retained = a.build_owned_batch(selected, retained_rows)
        bad_time = pa.array(
            [0] * 8 + [253402300800000000] + [0] * 23, type=pa.int64()
        ).view(pa.timestamp("us"))
        columns = list(retained.columns)
        columns[9] = bad_time
        bad_slice = pa.RecordBatch.from_arrays(columns, schema=selected.schema).slice(
            8, 1
        )
        resource["retained_first"] = [
            refused(
                lambda: a.verify_batch(
                    bad_slice,
                    selected,
                    producer,
                    limits=a.BatchLimits(bytes=finite_charge(state="one")),
                )
            ),
            refused(lambda: a.verify_batch(bad_slice, selected, producer)),
        ]
        array = pa.array

        def forbidden(*args, **kwargs):
            raise AssertionError("array construction preceded preflight")

        try:
            setattr(pa, "array", forbidden)
            over = list(rows[0])
            over[6] = "é" * 8
            resource["preflight"] = [
                refused(
                    lambda: a.build_owned_batch(
                        selected, rows, limits=a.BatchLimits(rows=3)
                    )
                ),
                refused(
                    lambda: a.build_owned_batch(
                        selected, rows, limits=a.BatchLimits(bytes=1)
                    )
                ),
                refused(
                    lambda: a.build_owned_batch(
                        selected,
                        [over],
                        limits=a.BatchLimits(bytes=finite_charge(state="one")),
                    )
                ),
            ]
        finally:
            setattr(pa, "array", array)
        layouts = []
        for i in (9, 10, 11):
            kind = pa.binary(16) if i == 10 else selected.schema[i].type
            try:
                column = pa.Array.from_buffers(kind, 0, [None, None])
                if i == 10:
                    column = pa.ExtensionArray.from_storage(pa.uuid(), column)
                columns = list(empty.columns)
                columns[i] = column
                candidate = pa.RecordBatch.from_arrays(columns, schema=selected.schema)
                candidate.validate(full=True)
            except (ValueError, pa.ArrowException):
                layouts.append("ARROW_CONSTRUCTOR")
            else:
                a.verify_batch(candidate, selected, producer)
                layouts.append("CHECKED_EMPTY")
        resource["empty_absent_buffers"] = layouts
        results["finite_resources"][target] = resource

        candidates = []
        columns = list(actual.columns)
        columns[0], columns[12] = columns[12], columns[0]
        candidates.append(pa.RecordBatch.from_arrays(columns, schema=selected.schema))
        for position, replacement in ((12, 11), (5, None)):
            changed = [list(r) for r in rows]
            changed[0][position] = replacement
            candidates.append(a.build_owned_batch(selected, changed))
        candidates += [actual.slice(0, 3), actual.slice(0, 1)]
        detected = []
        for candidate in candidates:
            a.verify_batch(candidate, selected, producer)
            snapshot = finite_snapshot(candidate)
            try:
                finite_oracle(snapshot)
            except ValueError:
                detected.append(
                    dict(
                        batch="PASS",
                        correspondence="VALUE_CORRESPONDENCE",
                        rows=snapshot["rows"],
                    )
                )
            else:
                raise AssertionError(
                    "finite substitution escaped original-input oracle"
                )
        builder = a.build_owned_batch

        def injected(binding, values, **kwargs):
            damaged = [list(row) for row in values]
            damaged[0][12] = 11
            return builder(binding, damaged, **kwargs)

        try:
            a.build_owned_batch = injected
            try:
                finite_observe(selected, rows)
            except ValueError:
                injection = "VALUE_CORRESPONDENCE"
            else:
                raise AssertionError("injected builder manufactured finite success")
        finally:
            a.build_owned_batch = builder
        results["finite_correspondence"][target] = dict(
            substitutions=detected,
            injected=injection,
            missing_column=refused(
                lambda: a.verify_batch(
                    actual.select(list(range(12))), selected, producer
                )
            ),
        )
        for kind, context, contract in (
            ("mixed", checked, neutral),
            ("nullable", nchecked, nneutral),
        ):
            exported = export_result_contract(contract, context)
            verify_bound_export(exported, context)
            assert (
                pure.reencode_contract(pure.decode_contract(exported.canonical_bytes))
                == exported.canonical_bytes
            )
            results["finite_codec"][target + "/" + kind] = (
                exported.canonical_bytes.decode()
            )
        before = export_result_contract(neutral, checked).canonical_bytes
        for chosen in (selected, default, wide, coherent):
            a.build_owned_batch(chosen, [])
            assert export_result_contract(neutral, checked).canonical_bytes == before
        damaged = pure.decode_contract(before).document
        damaged["fields"][12]["label"] = "repeated"
        damaged["fields"][12]["identity"]["name"] = "repeated"
        view = pure.decode_contract(pure.encode_document(damaged))
        results["finite_correspondence"][target]["codec_label"] = refused(
            lambda: verify_contract_correspondence(view, neutral, checked)
        )
        assert producer.contract.scalar_meaning is meaning

    small = finite_label_fixture(root / "labels-64", 64)
    large = finite_label_fixture(root / "labels-65", 65)
    for producer in (small, large):
        requests = tuple(
            a.ArrowFieldLabelRequest(b.field, "😀" * 256) for b in producer.fields
        )
        if producer is small:
            selected = a.bind_arrow(producer, field_labels=requests)
            results["carrier_label_refusals"]["aggregate"] = dict(
                accepted_bytes=sum(
                    len(name.encode()) for name in selected.schema.names
                ),
                fields=len(selected.schema),
            )
        else:
            results["carrier_label_refusals"]["aggregate"]["overflow"] = refused(
                lambda: a.bind_arrow(producer, field_labels=requests)
            )
    return results


def verify_finite_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        for key in FINITE_GROUPS:
            expected_keys = {"postgres", "mysql"}
            if key == "carrier_label_refusals":
                expected_keys.add("aggregate")
            elif key == "finite_codec":
                expected_keys = {
                    f"{t}/{k}"
                    for t in ("postgres", "mysql")
                    for k in ("mixed", "nullable")
                }
            if set(cases[key]) != expected_keys:
                raise ValueError("finite observation denominator")
        for target in ("postgres", "mysql"):

            def require(key, expected):
                if not _exact(cases[key][target], expected):
                    raise ValueError("finite observed " + key)

            require(
                "finite_mixed_values",
                dict(
                    values=finite_expected(),
                    wide=finite_expected(wide=True),
                    semantic_labels=list(FINITE_LABELS),
                    producer_labels=list(FINITE_LABELS),
                    distinct_sources=13,
                ),
            )
            require(
                "finite_empty",
                dict(
                    snapshot=finite_expected(state="empty"),
                    zero_fields="LIMIT",
                    untyped="ARROW_SCHEMA",
                    wrong_unit="ARROW_SCHEMA",
                    precision="ARROW_SCHEMA",
                    request="ARROW_ADAPTATION",
                    meaning=["BLOCKED", "INPUT_REJECTED"],
                ),
            )
            require(
                "finite_all_null",
                dict(
                    all_null=finite_expected(state="null", all_nullable=True),
                    first_null=finite_expected(state="first_null", all_nullable=True),
                    one=finite_expected(state="one"),
                    actual_nonnullable="NULL",
                    row_nonnullable="NULL",
                    coercion="VALUE_DOMAIN",
                ),
            )
            require(
                "carrier_labels",
                dict(
                    populated=finite_expected(),
                    empty=finite_expected(state="empty"),
                    all_null=finite_expected(state="null", all_nullable=True),
                    default=finite_expected(labels=False),
                ),
            )
            label_errors: dict[str, Any] = dict.fromkeys(
                (
                    "short",
                    "extra",
                    "list",
                    "wrong_kind",
                    "foreign",
                    "reorder",
                    "reuse",
                    "empty",
                    "nul",
                    "surrogate",
                    "codepoints",
                    "utf8",
                    "type",
                    "subclass",
                    "deleted_field",
                    "deleted_label",
                    "deleted_policy",
                ),
                "ARROW_LABELS",
            )
            label_errors.update(
                cleared_policy="ARROW_BINDING",
                no_policy="ARROW_SCHEMA",
                changed_name="ARROW_SCHEMA",
                producer_label="PRODUCER_OBSERVATION",
                metadata="ARROW_SCHEMA",
                field_metadata="ARROW_SCHEMA",
                coherent_policy="changed",
                language=["PIE-S2305"],
            )
            require("carrier_label_refusals", label_errors)
            resource: dict[str, Any] = {
                f"{state}/{'wide' if wide else 'default'}": dict(
                    charge=finite_charge(state=state, wide=wide),
                    rows=len(finite_expected(state=state)["rows"]),
                    owned_under="LIMIT",
                    supplied_under="LIMIT",
                )
                for wide in (False, True)
                for state in ("values", "empty", "null")
            }
            resource.update(
                offset=dict(
                    offsets=[9] * 13,
                    snapshot=finite_expected(state="first_null", all_nullable=True),
                ),
                retained_first=["LIMIT", "VALUE_DOMAIN"],
                preflight=["LIMIT"] * 3,
                empty_absent_buffers=["CHECKED_EMPTY"] * 3,
            )
            require("finite_resources", resource)
            rows = finite_expected()["rows"]
            variants = json.loads(json.dumps([rows] * 3))
            for row in variants[0]:
                row[0], row[12] = row[12], row[0]
            variants[1][0][12] = 11
            variants[2][0][5] = None
            variants += [rows[:3], rows[:1]]
            require(
                "finite_correspondence",
                dict(
                    substitutions=[
                        dict(
                            batch="PASS", correspondence="VALUE_CORRESPONDENCE", rows=v
                        )
                        for v in variants
                    ],
                    injected="VALUE_CORRESPONDENCE",
                    missing_column="ARROW_SCHEMA",
                    codec_label="CORRESPONDENCE",
                ),
            )
            for kind in ("mixed", "nullable"):
                raw = cases["finite_codec"][target + "/" + kind].encode()
                view = pure.decode_contract(raw)
                document = view.document
                fields = document["fields"]
                expected_names = [k.split("(")[0] for k in FINITE_KINDS]
                expected_laws = [
                    dict(
                        kind="timestamp",
                        calendar="proleptic_gregorian",
                        resolution="microsecond",
                        timezone="absent",
                        lower=[1000, 1, 1, 0, 0, 0, 0],
                        upper=[9999, 12, 31, 23, 59, 59, 499999],
                    ),
                    dict(kind="uuid", byte_order="big_endian", byte_width=16),
                    dict(kind="uuid", byte_order="big_endian", byte_width=16),
                ]
                if (
                    document["owner"]["identity"]
                    != dict(
                        module="main.pietto",
                        namespace="relation",
                        kind="table",
                        name="result",
                    )
                    or [f["declared"]["name"] for f in fields] != expected_names
                    or [
                        [a["value"]["value"] for a in f["declared"]["arguments"]]
                        for f in fields
                    ]
                    != [
                        [],
                        [],
                        [],
                        [],
                        [],
                        [],
                        [],
                        ["9", "2"],
                        ["65", "30"],
                        [],
                        [],
                        [],
                        [],
                    ]
                    or [f["provenance"]["symbol"]["identity"]["name"] for f in fields]
                    != ["rows"] * 13
                    or [entry["law"] for entry in document["scalar_meaning"]["sources"]]
                    != expected_laws
                    or pure.reencode_contract(view) != raw
                    or document["field_count"] != 13
                    or document["multiplicity"] != "bag"
                    or document["ordering"] is not None
                    or [f["ordinal"] for f in fields] != list(range(13))
                    or [f["label"] for f in fields] != list(FINITE_LABELS)
                    or [f["canonical"] for f in fields]
                    != [
                        dict(kind="builtin", name=k.split("(")[0], symbol=None)
                        for k in FINITE_KINDS
                    ]
                    or [f["nullability"] for f in fields]
                    != [
                        "nullable" if kind == "nullable" or i % 2 else "non_null"
                        for i in range(13)
                    ]
                    or [f.get("meaning") for f in fields]
                    != [None] * 9 + [0, 1, 2, None]
                    or [s["port"] for s in document["scalar_meaning"]["sources"]]
                    != [dict(kind="source_port", position=i) for i in (9, 10, 11)]
                    or any(
                        f["provenance"]["kind"] != "direct_projection" for f in fields
                    )
                ):
                    raise ValueError("finite complete neutral document")
        if cases["carrier_label_refusals"]["aggregate"] != dict(
            accepted_bytes=65536, fields=64, overflow="ARROW_LABELS"
        ):
            raise ValueError("label aggregate metadata bounds")
    except (KeyError, TypeError, AttributeError, pure.ContractDocumentError) as exc:
        raise ValueError("finite scalar report evidence") from exc


READER_GROUPS = (
    "reader_values",
    "reader_empty_null",
    "reader_extent",
    "reader_terminal",
    "reader_lifecycle",
    "reader_limits",
    "reader_rechunk",
    "reader_identity",
    "reader_correspondence",
    "reader_incremental",
)


def reader_receipt(reader) -> dict[str, Any]:
    completion = reader.completion
    return dict(
        state=reader.state,
        rows=reader.rows,
        batches=reader.batch_count,
        charge=reader.charge,
        pulls=reader.pulls,
        descriptors=[]
        if completion is None
        else [
            [d.ordinal, d.row_start, d.rows, d.logical_bytes, d.retained_bytes]
            for d in completion.descriptors
        ],
        complete=completion is not None,
    )


def reader_expected(usages, *, state="COMPLETE", pulls=None) -> dict[str, Any]:
    rows = charge = 0
    descriptors = []
    for i, (count, logical, retained) in enumerate(usages):
        descriptors.append([i, rows, count, logical, retained])
        rows += count
        charge += max(logical, retained)
    return dict(
        state=state,
        rows=rows,
        batches=len(usages),
        charge=charge,
        pulls=len(usages) + 1 if pulls is None else pulls,
        descriptors=descriptors if state == "COMPLETE" else [],
        complete=state == "COMPLETE",
    )


# Independent physical allowances: S08 original four-row mixed has A=630/R=528;
# its slices retain R=528. These are fixture arithmetic, not product receipts.
READER_LAYOUTS = {
    "whole": ((4, 630, 528),),
    "uneven": ((1, 175, 528), (2, 330, 528), (1, 175, 528)),
    "empty_interleaved": (
        (0, 12, 12),
        (1, 175, 528),
        (0, 12, 12),
        (2, 330, 528),
        (1, 175, 528),
        (0, 12, 12),
    ),
}


class ReaderTrace:
    """Test-only observation around real SDK operations, with named fault controls."""

    def __init__(self, schema, batches, *, late=False, close_error=None):
        self.schema = schema
        self.batches = batches
        self.late = late
        self.close_error = close_error
        self.events: list[Any] = []
        self.reads = self.closes = self.close_success = 0
        self.last = None

    def __enter__(self):
        from pietto._project import project_result_reader as r

        pa = importlib.import_module("pyarrow")

        def values():
            for batch in self.batches:
                self.events.append(["data", batch.num_rows])
                yield batch
            self.events.append(["error" if self.late else "eof"])
            if self.late:
                raise RuntimeError("late cooperative source failure")

        self.source = pa.RecordBatchReader.from_batches(self.schema, values())
        self.read_original, self.close_original = r._read_source, r._close_source

        def read(source):
            self.reads += 1
            batch = self.read_original(source)
            self.last = id(batch)
            return batch

        def close(source):
            self.closes += 1
            self.close_original(source)
            if self.close_error is not None:
                raise self.close_error
            self.close_success += 1

        r._read_source, r._close_source = read, close
        return self

    def __exit__(self, *args):
        from pietto._project import project_result_reader as r

        r._read_source, r._close_source = self.read_original, self.close_original
        return False

    def snapshot(self):
        return dict(
            events=self.events,
            reads=self.reads,
            closes=self.closes,
            close_success=self.close_success,
        )


def reader_trace_expected(
    counts, *, late=False, closes=1, close_success=1
) -> dict[str, Any]:
    return dict(
        events=[["data", n] for n in counts] + [["error" if late else "eof"]],
        reads=len(counts) + 1,
        closes=closes,
        close_success=close_success,
    )


def reader_consume(
    binding, batches, expected_rows, *, limits=None, late=False, close_error=None
) -> dict[str, Any]:
    from pietto._project import project_result_reader as r

    snapshots = []
    with ReaderTrace(
        binding.schema, batches, late=late, close_error=close_error
    ) as trace:
        reader = r.open_finite_reader(
            binding,
            trace.source,
            expected_rows=expected_rows,
            limits=r.FiniteReaderLimits() if limits is None else limits,
        )
        assert (
            trace.reads == 0
            and reader.schema is binding.schema
            and reader.completion is None
        )
        error = None
        try:
            for batch in reader:
                assert id(batch) == trace.last
                snapshots.append(finite_snapshot(batch))
        except r.ResultError as exc:
            error = exc.category
        result = dict(
            receipt=reader_receipt(reader),
            trace=trace.snapshot(),
            error=error,
            rows=[row for snapshot in snapshots for row in snapshot["rows"]],
            primary=reader.primary_error.category
            if isinstance(reader.primary_error, r.ResultError)
            else None
            if reader.primary_error is None
            else type(reader.primary_error).__name__,
            cleanup=None
            if reader.cleanup_error is None
            else type(reader.cleanup_error).__name__,
        )
        if error is not None:
            assert reader.completion is None
            assert refused(reader.read_next_batch) == "READER_FAILED"
        else:
            receipt = reader.completion
            r.verify_finite_completion(reader, reader.expectation, receipt)
            assert reader.completion is receipt
            try:
                reader.read_next_batch()
            except StopIteration:
                pass
            else:
                raise AssertionError("completed session read again")
        reader.close()
        reader.close()
        assert trace.closes == 1
        return result


def reader_expected_result(
    usages,
    rows,
    *,
    state="COMPLETE",
    error=None,
    counts=None,
    late=False,
    pulls=None,
    eof=True,
    close_success=1,
) -> dict[str, Any]:
    counts = [u[0] for u in usages] if counts is None else counts
    trace = reader_trace_expected(counts, late=late, close_success=close_success)
    if not eof:
        trace["events"] = trace["events"][:-1]
        trace["reads"] -= 1
    return dict(
        receipt=reader_expected(usages, state=state, pulls=pulls),
        trace=trace,
        error=error,
        rows=rows,
        primary="RuntimeError" if error == "READER_SOURCE" else error,
        cleanup="RuntimeError" if close_success == 0 else None,
    )


def run_reader_cases(root):
    import gc
    import itertools
    import weakref
    from pietto._project import project_result_reader as r
    from pietto._project import project_arrow_result as a
    from pietto._project.project_result_contract_portable import export_result_contract

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {name: {} for name in READER_GROUPS}
    for target in ("postgres", "mysql"):
        checked, _, _, neutral, producer, _ = finite_fixture(
            root / ("reader-" + target), target
        )
        _, _, _, _, nproducer, _ = finite_fixture(
            root / ("reader-null-" + target), target, all_nullable=True
        )
        binding = a.bind_arrow(producer, **finite_policy(producer))
        nullable = a.bind_arrow(nproducer, **finite_policy(nproducer))
        expected_rows = (
            4  # Declared from the independent original sequence, before reads.
        )
        batch = a.build_owned_batch(binding, finite_rows(target))
        empty = a.build_owned_batch(binding, [])
        before = export_result_contract(neutral, checked).canonical_bytes
        values = reader_consume(binding, [batch], expected_rows)
        finite_oracle(dict(finite_expected(), rows=values["rows"]))
        results["reader_values"][target] = dict(
            result=values,
            schema=finite_snapshot(batch)["fields"],
            declared_rows=expected_rows,
            borrowed_claim=False,
        )
        absent = list(empty.columns)
        for i in (9, 10, 11):
            kind = pa.binary(16) if i == 10 else binding.schema[i].type
            column = pa.Array.from_buffers(kind, 0, [None, None])
            absent[i] = (
                pa.ExtensionArray.from_storage(pa.uuid(), column) if i == 10 else column
            )
        absent_batch = pa.RecordBatch.from_arrays(absent, schema=binding.schema)
        nulls = a.build_owned_batch(nullable, finite_rows(target, state="null"))
        first_null = a.build_owned_batch(
            nullable, finite_rows(target, state="first_null")
        )
        wrong_schema = pa.schema(
            [
                pa.field("wrong" if i == 12 else f.name, f.type, nullable=f.nullable)
                for i, f in enumerate(binding.schema)
            ]
        )
        with ReaderTrace(wrong_schema, []) as trace:
            wrong = refused(
                lambda: r.open_finite_reader(binding, trace.source, expected_rows=0)
            )
            assert trace.reads == trace.closes == 0
            trace.source.close()
        invalid_null = pa.RecordBatch.from_arrays(nulls.columns, schema=binding.schema)
        from pietto._project.project_result_contract import build_result_contract

        no_meaning = replace(producer, contract=build_result_contract(checked))
        with ReaderTrace(binding.schema, []) as trace:
            missing = refused(
                lambda: r.open_finite_reader(
                    replace(binding, producer=no_meaning), trace.source, expected_rows=0
                )
            )
            assert trace.reads == trace.closes == 0
            trace.source.close()
        results["reader_empty_null"][target] = dict(
            zero=reader_consume(binding, [], 0),
            empty=reader_consume(binding, [empty, absent_batch, empty], 0),
            all_null=reader_consume(nullable, [nulls], 2),
            first_null=reader_consume(nullable, [first_null], 5),
            wrong_schema=wrong,
            missing_meaning=missing,
            nonnullable=reader_consume(binding, [invalid_null], 2),
        )

        invalid = []
        with ReaderTrace(binding.schema, [batch]) as trace:
            for total in (None, True, 4.0, -1, "4", CoercibleScalar(), 1048577):
                invalid.append(
                    refused(
                        lambda total=total: r.open_finite_reader(
                            binding, trace.source, expected_rows=total
                        )
                    )
                )
            invalid.append(
                refused(
                    lambda: r.open_finite_reader(
                        binding,
                        trace.source,
                        expected_rows=4,
                        limits=r.FiniteReaderLimits(max_total_rows=3),
                    )
                )
            )
            assert trace.reads == trace.closes == 0
            invalid_trace = trace.snapshot()
            trace.source.close()
        results["reader_extent"][target] = dict(
            source_types=[
                refused(
                    lambda source=source: r.open_finite_reader(
                        binding, source, expected_rows=0
                    )
                )
                for source in (None, object(), iter(()))
            ],
            invalid=invalid,
            invalid_trace=invalid_trace,
            short=reader_consume(binding, [batch.slice(0, 3)], 4),
            extra=reader_consume(binding, [batch, batch.slice(0, 1)], 4),
            zero_extra=reader_consume(binding, [batch], 0),
        )
        late = reader_consume(binding, [batch], 4, late=True)
        trailing = reader_consume(binding, [batch, empty, empty], 4)
        early = []
        for batches, total, pulls in (([batch], 4, 1), ([], 0, 0)):
            with ReaderTrace(binding.schema, batches) as trace:
                reader = r.open_finite_reader(
                    binding, trace.source, expected_rows=total
                )
                for _ in range(pulls):
                    reader.read_next_batch()
                assert reader.completion is None
                reader.close()
                reader.close()
                early.append(
                    dict(
                        receipt=reader_receipt(reader),
                        trace=trace.snapshot(),
                        subsequent=refused(reader.read_next_batch),
                    )
                )
        results["reader_terminal"][target] = dict(
            late=late, trailing=trailing, early=early
        )

        cleanup = reader_consume(
            binding, [batch], 4, close_error=RuntimeError("injected cleanup failure")
        )
        combined = reader_consume(
            binding,
            [batch],
            4,
            late=True,
            close_error=RuntimeError("injected cleanup failure"),
        )
        controls: dict[str, Any] = {}
        for operation in (
            "validation_stop",
            "finalization_stop",
            "close_stop",
            "read_interrupt",
            "read_exit",
        ):
            with ReaderTrace(binding.schema, [batch]) as trace:
                reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
                if operation == "finalization_stop":
                    reader.read_next_batch()
                owner, attribute = (
                    (a, "_checked_batch_usage")
                    if operation == "validation_stop"
                    else (r, "_make_completion")
                    if operation == "finalization_stop"
                    else (r, "_close_source")
                    if operation == "close_stop"
                    else (r, "_read_source")
                )
                original = getattr(owner, attribute)
                error = (
                    KeyboardInterrupt()
                    if operation == "read_interrupt"
                    else SystemExit(9)
                    if operation == "read_exit"
                    else StopIteration("injected non-source stop")
                )

                def injected(*args, **kwargs):
                    raise error

                try:
                    setattr(owner, attribute, injected)
                    try:
                        if operation == "close_stop":
                            reader.close()
                        else:
                            reader.read_next_batch()
                    except BaseException as exc:
                        controls[operation] = dict(
                            error=exc.category
                            if isinstance(exc, r.ResultError)
                            else type(exc).__name__,
                            state=reader.state,
                            complete=reader.completion is not None,
                        )
                    else:
                        raise AssertionError("injected reader failure accepted")
                finally:
                    setattr(owner, attribute, original)
                    # The close sentinel did not call the real SDK; caller releases this test handle.
                    if operation == "close_stop":
                        trace.source.close()
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            returned = None
            try:
                with reader:
                    returned = reader.read_next_batch()
                    raise ValueError("body failure")
            except ValueError:
                pass
            assert returned is not None
            body = dict(
                state=reader.state,
                closes=trace.closes,
                complete=reader.completion is not None,
                retained=finite_snapshot(returned),
            )
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            returned = reader.read_next_batch()
            try:
                reader.read_next_batch()
            except StopIteration:
                pass
            source_ref = weakref.ref(trace.source)
            del trace.source
            gc.collect()
            release = dict(
                source_released=source_ref() is None,
                active_source_released=reader._source is None,
                retained=finite_snapshot(returned),
            )
        for name, cleanup_error in (
            ("eof_cleanup_interrupt", KeyboardInterrupt()),
            ("eof_cleanup_exit", SystemExit(10)),
        ):
            with ReaderTrace(binding.schema, [], close_error=cleanup_error) as trace:
                reader = r.open_finite_reader(binding, trace.source, expected_rows=0)
                try:
                    reader.read_next_batch()
                except BaseException as exc:
                    controls[name] = dict(
                        error=type(exc).__name__,
                        state=reader.state,
                        complete=reader.completion is not None,
                    )
                    assert exc is cleanup_error and trace.closes == 1
                else:
                    raise AssertionError("cleanup control exception was swallowed")
        with ReaderTrace(binding.schema, [], close_error=KeyboardInterrupt()) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=0)
            try:
                with reader:
                    raise ValueError("body and cleanup")
            except BaseExceptionGroup as exc:
                controls["context_cleanup_interrupt"] = dict(
                    errors=[type(e).__name__ for e in exc.exceptions],
                    state=reader.state,
                    closes=trace.closes,
                    complete=reader.completion is not None,
                )
            else:
                raise AssertionError("combined context failure was swallowed")
        results["reader_lifecycle"][target] = dict(
            cleanup=cleanup,
            combined=combined,
            controls=controls,
            body=body,
            release=release,
            cleanup_controls="test-injected around real SDK close",
        )

        limits: dict[str, Any] = {}
        for name, batches, total, policy in (
            (
                "exact_bytes",
                [batch, batch],
                8,
                r.FiniteReaderLimits(max_total_bytes=1260),
            ),
            (
                "under_bytes",
                [batch, batch],
                8,
                r.FiniteReaderLimits(max_total_bytes=1259),
            ),
            ("exact_batches", [batch], 4, r.FiniteReaderLimits(max_batches=1)),
            (
                "zero_batches",
                [],
                0,
                r.FiniteReaderLimits(
                    max_batches=0, max_total_rows=0, max_total_bytes=0
                ),
            ),
            (
                "endless_empty",
                itertools.repeat(empty),
                0,
                r.FiniteReaderLimits(max_batches=2),
            ),
            ("empty_under", [empty], 0, r.FiniteReaderLimits(max_total_bytes=11)),
            (
                "batch_rows",
                [batch],
                4,
                r.FiniteReaderLimits(batch=a.BatchLimits(rows=3)),
            ),
        ):
            limits[name] = reader_consume(binding, batches, total, limits=policy)
        arrays = list(batch.columns)
        arrays[4] = pa.array([float("nan")] * 4, type=pa.float64())
        tiny = pa.RecordBatch.from_arrays(arrays, schema=binding.schema).slice(0, 1)
        original_value = a._value

        def forbidden(*args, **kwargs):
            raise AssertionError("retained buffers not checked first")

        try:
            a._value = forbidden
            limits["retained_first"] = reader_consume(
                binding, [tiny], 1, limits=r.FiniteReaderLimits(max_total_bytes=527)
            )
        finally:
            a._value = original_value
        limits["invalid_after_retained"] = reader_consume(
            binding, [tiny], 1, limits=r.FiniteReaderLimits(max_total_bytes=528)
        )
        with ReaderTrace(binding.schema, []) as trace:
            invalid_limits = [
                r.FiniteReaderLimits(max_batches=True),
                r.FiniteReaderLimits(max_batches=1025),
                r.FiniteReaderLimits(max_total_rows=1048577),
                r.FiniteReaderLimits(max_total_bytes=64 * 1024 * 1024 + 1),
                r.FiniteReaderLimits(max_total_bytes=-1),
                r.FiniteReaderLimits(batch=a.BatchLimits(rows=4097)),
                r.FiniteReaderLimits(batch=a.BatchLimits(fields=12)),
            ]
            limits["invalid"] = [
                refused(
                    lambda policy=policy: r.open_finite_reader(
                        binding, trace.source, expected_rows=0, limits=policy
                    )
                )
                for policy in invalid_limits
            ]
            assert trace.reads == trace.closes == 0
            trace.source.close()
        limits["exact_rows"] = reader_consume(
            binding, [batch], 4, limits=r.FiniteReaderLimits(max_total_rows=4)
        )
        results["reader_extent"][target]["new_declaration"] = reader_consume(
            binding, [batch.slice(0, 3)], 3
        )
        results["reader_limits"][target] = limits
        layouts = dict(
            whole=[batch],
            uneven=[batch.slice(0, 1), batch.slice(1, 2), batch.slice(3, 1)],
            empty_interleaved=[
                empty,
                batch.slice(0, 1),
                empty,
                batch.slice(1, 2),
                batch.slice(3, 1),
                empty,
            ],
        )
        rechunk = {
            name: reader_consume(binding, chunks, 4) for name, chunks in layouts.items()
        }
        assert all(
            value["rows"] == finite_expected()["rows"] for value in rechunk.values()
        )
        assert export_result_contract(neutral, checked).canonical_bytes == before
        results["reader_rechunk"][target] = dict(
            layouts=rechunk, neutral_unchanged=True
        )

        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            list(reader)
            expected = reader.expectation
            receipt = reader.completion
            assert receipt is not None
            copied_receipt = replace(receipt)

            def verify():
                r.verify_finite_completion(reader, expected, receipt)

            identities: dict[str, Any] = dict(
                copy=refused(
                    lambda: r.verify_finite_completion(copy(reader), expected, receipt)
                ),
                expectation_copy=refused(
                    lambda: r.verify_finite_completion(
                        reader, replace(expected), receipt
                    )
                ),
                receipt_copy=refused(
                    lambda: r.verify_finite_completion(reader, expected, copied_receipt)
                ),
            )
            for name, value in (
                ("rows", 3),
                ("batches", 0),
                ("charge", 0),
                ("pulls", 1),
                ("descriptors", ()),
                ("_session", object()),
                ("binding", a.bind_arrow(producer, **finite_policy(producer))),
                ("_terminal", object()),
            ):
                previous = getattr(receipt, name)
                try:
                    object.__setattr__(receipt, name, value)
                    identities[name] = refused(verify)
                finally:
                    object.__setattr__(receipt, name, previous)
            for record, name, key in (
                (receipt, "rows", "deleted_receipt"),
                (expected, "expected_rows", "deleted_expectation"),
                (receipt.descriptors[0], "retained_bytes", "deleted_descriptor"),
            ):
                previous = getattr(record, name)
                try:
                    object.__delattr__(record, name)
                    identities[key] = refused(verify)
                finally:
                    object.__setattr__(record, name, previous)
            previous = reader._rows
            try:
                reader._rows = 3
                object.__setattr__(receipt, "rows", 3)
                identities["coordinated_counts"] = refused(verify)
                object.__setattr__(expected, "expected_rows", 3)
                identities["coordinated_declaration"] = refused(verify)
            finally:
                reader._rows = previous
                object.__setattr__(receipt, "rows", 4)
                object.__setattr__(expected, "expected_rows", 4)
            with ReaderTrace(binding.schema, [batch]) as other_trace:
                other = r.open_finite_reader(
                    binding, other_trace.source, expected_rows=4
                )
                list(other)
                identities["foreign_session"] = refused(
                    lambda: r.verify_finite_completion(other, expected, receipt)
                )
                previous_ref = expected._source_ref
                try:
                    object.__setattr__(
                        expected, "_source_ref", other.expectation._source_ref
                    )
                    identities["foreign_source"] = refused(verify)
                finally:
                    object.__setattr__(expected, "_source_ref", previous_ref)
            verify()
        for mutation in (
            "source",
            "binding",
            "policy",
            "limit",
            "deleted_policy",
            "protocol",
        ):
            with ReaderTrace(binding.schema, [batch]) as trace:
                session_binding = a.bind_arrow(producer, **finite_policy(producer))
                reader = r.open_finite_reader(
                    session_binding, trace.source, expected_rows=4
                )
                if mutation == "source":
                    reader._source = pa.RecordBatchReader.from_batches(
                        binding.schema, []
                    )
                elif mutation == "binding":
                    object.__setattr__(reader.expectation, "binding", binding)
                elif mutation == "limit":
                    object.__setattr__(reader.expectation.limits, "max_total_bytes", 1)
                elif mutation == "protocol":
                    object.__setattr__(
                        session_binding.producer.fields[0].observation,
                        "protocol_nullable",
                        True,
                    )
                elif mutation == "deleted_policy":
                    object.__delattr__(session_binding, "field_labels")
                else:
                    requests = session_binding.field_labels
                    assert requests is not None and requests[0] is not None
                    object.__setattr__(requests[0], "label", "changed")
                try:
                    identities["live_" + mutation] = refused(reader.read_next_batch)
                    assert trace.reads == 0 and trace.closes == 1
                finally:
                    # Restore the shared frozen default limit, not a failed session.
                    if mutation == "protocol":
                        object.__setattr__(
                            session_binding.producer.fields[0].observation,
                            "protocol_nullable",
                            None,
                        )
                    if mutation == "limit":
                        object.__setattr__(
                            reader.expectation.limits,
                            "max_total_bytes",
                            64 * 1024 * 1024,
                        )
        results["reader_identity"][target] = identities

        altered = []
        columns = list(batch.columns)
        columns[0], columns[12] = columns[12], columns[0]
        altered.append(pa.RecordBatch.from_arrays(columns, schema=binding.schema))
        rows = finite_rows(target)
        changed = [list(row) for row in rows]
        changed[0][12] = 11
        altered.append(a.build_owned_batch(binding, changed))
        altered.append(a.build_owned_batch(binding, [rows[1], rows[0], *rows[2:]]))
        altered.append(a.build_owned_batch(binding, [*rows[:3], rows[1]]))
        correspondence = []
        for candidate in altered:
            observed = reader_consume(binding, [candidate], 4)
            try:
                finite_oracle(dict(finite_expected(), rows=observed["rows"]))
            except ValueError:
                correspondence.append(
                    dict(
                        complete=observed["receipt"]["complete"],
                        original_values="VALUE_CORRESPONDENCE",
                        rows=observed["rows"],
                    )
                )
            else:
                raise AssertionError(
                    "same-count corruption escaped original-input oracle"
                )
        original_builder = a.build_owned_batch

        def injected_builder(binding, values, **kwargs):
            copied = [list(row) for row in values]
            copied[0][12] = 11
            return original_builder(binding, copied, **kwargs)

        try:
            a.build_owned_batch = injected_builder
            candidate = a.build_owned_batch(binding, finite_rows(target))
            measured = reader_consume(binding, [candidate], 4)
            try:
                finite_oracle(dict(finite_expected(), rows=measured["rows"]))
            except ValueError:
                injection = "VALUE_CORRESPONDENCE"
            else:
                raise AssertionError(
                    "injected builder manufactured reader value evidence"
                )
        finally:
            a.build_owned_batch = original_builder
        results["reader_correspondence"][target] = dict(
            cases=correspondence,
            injected=injection,
            conditional_claim="declared extent, not original-value authentication",
        )
        with ReaderTrace(binding.schema, layouts["uneven"]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            opening = trace.reads
            for _ in range(3):
                assert reader.schema is binding.schema and reader.completion is None
            inspections = trace.reads
            first = reader.read_next_batch()
            first_pull = trace.reads
            assert id(first) == trace.last
            assert all(
                type(item) is tuple and all(type(n) is int for n in item)
                for item in reader._observations
            )
            reader.close()
            results["reader_incremental"][target] = dict(
                opening_pulls=opening,
                inspection_pulls=inspections,
                first_pulls=first_pull,
                first=finite_snapshot(first),
                descriptors_retained=len(reader._observations),
                state=reader.state,
                trace=trace.snapshot(),
                forbidden_api=any(
                    hasattr(reader, name)
                    for name in (
                        "read_all",
                        "to_pandas",
                        "combine_chunks",
                        "source",
                        "__arrow_c_stream__",
                    )
                ),
            )
    return results


def verify_reader_report(cases):
    try:
        if any(set(cases[name]) != {"postgres", "mysql"} for name in READER_GROUPS):
            raise ValueError("reader exact target/group denominator")
        rows = finite_expected()["rows"]
        whole = READER_LAYOUTS["whole"]
        complete = reader_expected_result(whole, rows)
        for target in ("postgres", "mysql"):

            def require(name, expected):
                if not _exact(cases[name][target], expected):
                    raise ValueError("reader observed " + name)

            require(
                "reader_values",
                dict(
                    result=complete,
                    schema=finite_expected()["fields"],
                    declared_rows=4,
                    borrowed_claim=False,
                ),
            )
            require(
                "reader_empty_null",
                dict(
                    zero=reader_expected_result((), []),
                    empty=reader_expected_result(((0, 12, 12),) * 3, []),
                    all_null=reader_expected_result(
                        ((2, 321, 274),), [[None] * 13] * 2
                    ),
                    first_null=reader_expected_result(
                        ((5, 778, 659),), [[None] * 13, *rows]
                    ),
                    wrong_schema="ARROW_SCHEMA",
                    missing_meaning="PRODUCER_ROOT",
                    nonnullable=reader_expected_result(
                        (),
                        [],
                        state="FAILED",
                        error="NULL",
                        counts=[2],
                        pulls=1,
                        eof=False,
                    ),
                ),
            )
            require(
                "reader_extent",
                dict(
                    source_types=["READER_SOURCE"] * 3,
                    invalid=["READER_DECLARATION"] * 8,
                    invalid_trace=dict(events=[], reads=0, closes=0, close_success=0),
                    new_declaration=reader_expected_result(((3, 480, 528),), rows[:3]),
                    short=reader_expected_result(
                        ((3, 480, 528),),
                        rows[:3],
                        state="FAILED",
                        error="READER_EXTENT",
                    ),
                    extra=reader_expected_result(
                        whole,
                        rows,
                        state="FAILED",
                        error="READER_EXTENT",
                        counts=[4, 1],
                        pulls=2,
                        eof=False,
                    ),
                    zero_extra=reader_expected_result(
                        (),
                        [],
                        state="FAILED",
                        error="READER_EXTENT",
                        counts=[4],
                        pulls=1,
                        eof=False,
                    ),
                ),
            )
            early = [
                dict(
                    receipt=reader_expected(whole, state="CLOSED_INCOMPLETE", pulls=1),
                    trace=dict(
                        events=[["data", 4]], reads=1, closes=1, close_success=1
                    ),
                    subsequent="READER_CLOSED",
                ),
                dict(
                    receipt=reader_expected((), state="CLOSED_INCOMPLETE", pulls=0),
                    trace=dict(events=[], reads=0, closes=1, close_success=1),
                    subsequent="READER_CLOSED",
                ),
            ]
            require(
                "reader_terminal",
                dict(
                    late=reader_expected_result(
                        whole, rows, state="FAILED", error="READER_SOURCE", late=True
                    ),
                    trailing=reader_expected_result(
                        (*whole, (0, 12, 12), (0, 12, 12)), rows
                    ),
                    early=early,
                ),
            )
            controls: dict[str, Any] = {
                name: dict(error=error, state="FAILED", complete=False)
                for name, error in (
                    ("validation_stop", "READER_VALIDATION"),
                    ("finalization_stop", "READER_VALIDATION"),
                    ("close_stop", "READER_CLEANUP"),
                    ("read_interrupt", "KeyboardInterrupt"),
                    ("read_exit", "SystemExit"),
                )
            }
            controls.update(
                eof_cleanup_interrupt=dict(
                    error="KeyboardInterrupt", state="FAILED", complete=False
                ),
                eof_cleanup_exit=dict(
                    error="SystemExit", state="FAILED", complete=False
                ),
                context_cleanup_interrupt=dict(
                    errors=["ValueError", "KeyboardInterrupt"],
                    state="FAILED",
                    closes=1,
                    complete=False,
                ),
            )
            require(
                "reader_lifecycle",
                dict(
                    cleanup=reader_expected_result(
                        whole,
                        rows,
                        state="FAILED",
                        error="READER_CLEANUP",
                        close_success=0,
                    ),
                    combined=reader_expected_result(
                        whole,
                        rows,
                        state="FAILED",
                        error="READER_SOURCE",
                        late=True,
                        close_success=0,
                    ),
                    controls=controls,
                    body=dict(
                        state="FAILED",
                        closes=1,
                        complete=False,
                        retained=finite_expected(),
                    ),
                    release=dict(
                        source_released=True,
                        active_source_released=True,
                        retained=finite_expected(),
                    ),
                    cleanup_controls="test-injected around real SDK close",
                ),
            )
            limits = dict(
                exact_bytes=reader_expected_result(whole * 2, rows * 2),
                under_bytes=reader_expected_result(
                    whole,
                    rows,
                    state="FAILED",
                    error="LIMIT",
                    counts=[4, 4],
                    pulls=2,
                    eof=False,
                ),
                exact_batches=complete,
                zero_batches=reader_expected_result((), []),
                endless_empty=reader_expected_result(
                    ((0, 12, 12),) * 2,
                    [],
                    state="FAILED",
                    error="LIMIT",
                    counts=[0, 0, 0],
                    pulls=3,
                    eof=False,
                ),
                empty_under=reader_expected_result(
                    (),
                    [],
                    state="FAILED",
                    error="LIMIT",
                    counts=[0],
                    pulls=1,
                    eof=False,
                ),
                batch_rows=reader_expected_result(
                    (),
                    [],
                    state="FAILED",
                    error="LIMIT",
                    counts=[4],
                    pulls=1,
                    eof=False,
                ),
                retained_first=reader_expected_result(
                    (),
                    [],
                    state="FAILED",
                    error="LIMIT",
                    counts=[1],
                    pulls=1,
                    eof=False,
                ),
                invalid_after_retained=reader_expected_result(
                    (),
                    [],
                    state="FAILED",
                    error="VALUE_DOMAIN",
                    counts=[1],
                    pulls=1,
                    eof=False,
                ),
                invalid=["LIMIT"] * 7,
                exact_rows=complete,
            )
            require("reader_limits", limits)
            require(
                "reader_rechunk",
                dict(
                    layouts={
                        name: reader_expected_result(usage, rows)
                        for name, usage in READER_LAYOUTS.items()
                    },
                    neutral_unchanged=True,
                ),
            )
            identities = dict.fromkeys(
                (
                    "copy",
                    "expectation_copy",
                    "receipt_copy",
                    "rows",
                    "batches",
                    "charge",
                    "pulls",
                    "descriptors",
                    "_session",
                    "binding",
                    "_terminal",
                    "deleted_receipt",
                    "deleted_expectation",
                    "deleted_descriptor",
                    "coordinated_counts",
                    "coordinated_declaration",
                    "foreign_session",
                    "foreign_source",
                    "live_source",
                    "live_binding",
                    "live_policy",
                    "live_limit",
                    "live_deleted_policy",
                    "live_protocol",
                ),
                "READER_IDENTITY",
            )
            require("reader_identity", identities)
            variants = json.loads(json.dumps([rows] * 4))
            for row in variants[0]:
                row[0], row[12] = row[12], row[0]
            variants[1][0][12] = 11
            variants[2][0], variants[2][1] = variants[2][1], variants[2][0]
            variants[3][-1] = rows[1]
            require(
                "reader_correspondence",
                dict(
                    cases=[
                        dict(
                            complete=True,
                            original_values="VALUE_CORRESPONDENCE",
                            rows=variant,
                        )
                        for variant in variants
                    ],
                    injected="VALUE_CORRESPONDENCE",
                    conditional_claim="declared extent, not original-value authentication",
                ),
            )
            require(
                "reader_incremental",
                dict(
                    opening_pulls=0,
                    inspection_pulls=0,
                    first_pulls=1,
                    first=finite_expected(state="one"),
                    descriptors_retained=1,
                    state="CLOSED_INCOMPLETE",
                    trace=dict(
                        events=[["data", 1]], reads=1, closes=1, close_success=1
                    ),
                    forbidden_api=False,
                ),
            )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("reader observed report evidence") from exc


INTEROP_GROUPS = (
    "ownership_copy",
    "ownership_borrow",
    "ownership_transfer",
    "c_schema_array",
    "c_schema_requests",
    "c_stream_values",
    "c_stream_terminal",
    "c_protocol_lifetime",
    "cpu_protocol_resources",
    "interop_correspondence",
)


class InteropOwner:
    def __init__(self):
        self.buffers: dict[tuple[int, int], bytearray] = {}


def mutable_finite(batch):
    pa = importlib.import_module("pyarrow")
    owner = InteropOwner()
    columns = []
    for i, column in enumerate(batch.columns):
        extension = type(column.type) is type(pa.uuid())
        storage = column.storage if extension else column
        buffers = []
        for j, buffer in enumerate(storage.buffers()):
            if buffer is None:
                buffers.append(None)
            else:
                backing = bytearray(memoryview(buffer))
                owner.buffers[i, j] = backing
                buffers.append(pa.py_buffer(backing))
        array_ = pa.Array.from_buffers(
            storage.type, len(storage), buffers, offset=storage.offset, null_count=-1
        )
        columns.append(
            pa.ExtensionArray.from_storage(column.type, array_) if extension else array_
        )
    return pa.RecordBatch.from_arrays(columns, schema=batch.schema), owner


def mutate_finite(owner):
    for i, value, width in (
        (0, 17, 2),
        (1, 333, 4),
        (2, BIG + 2, 8),
        (7, 4321, 16),
        (8, 17, 32),
        (9, 1, 8),
        (12, -9, 2),
    ):
        owner.buffers[i, 1][:width] = value.to_bytes(width, "little", signed=True)
    owner.buffers[1, 0][0] &= ~2
    owner.buffers[3, 1][0] |= 1
    owner.buffers[4, 1][:8] = bytes(8)
    owner.buffers[5, 1][4:8] = (1).to_bytes(4, "little")
    owner.buffers[6, 2][:2] = bytes.fromhex("c3a8")
    owner.buffers[10, 1][:16] = bytes.fromhex("102132435465768798a9bacbdcedfe0f")
    owner.buffers[11, 1][:16] = b"\xff" * 16


def protocol_expected(**kwargs) -> dict[str, Any]:
    expected = finite_expected(**kwargs)
    expected["fields"][10]["metadata"] = {}
    return expected


def protocol_oracle(snapshot):
    if not _exact(snapshot, protocol_expected()):
        raise ValueError("protocol positional source/value correspondence")


def mutated_finite_expected() -> dict[str, Any]:
    expected = finite_expected()
    expected["rows"][0] = [
        17,
        333,
        BIG + 2,
        True,
        "0000000000000000",
        "65",
        "c3a8",
        "4321",
        "17",
        1,
        "102132435465768798a9bacbdcedfe0f",
        "ffffffffffffffffffffffffffffffff",
        -9,
    ]
    expected["rows"][1][5] = "cc81"
    expected["rows"][1][1] = None
    expected["valid"][1][1] = False
    return expected


def interop_snapshot_slice(start, stop) -> dict[str, Any]:
    expected = protocol_expected()
    expected["rows"] = expected["rows"][start:stop]
    expected["valid"] = expected["valid"][start:stop]
    return expected


def protocol_error(action):
    from pietto._project.project_result_contract import ResultError

    try:
        action()
    except ResultError as exc:
        return exc.category
    except Exception as exc:
        return type(exc).__name__
    raise AssertionError("protocol negative unexpectedly accepted")


class ProtocolBatch:
    def __init__(self, batch):
        self.batch = batch
        self.calls = 0

    def __arrow_c_array__(self, requested_schema=None):
        self.calls += 1
        return self.batch.__arrow_c_array__(requested_schema)


class ProtocolStream:
    def __init__(self, source):
        self.source = source
        self.calls = 0

    def __arrow_c_stream__(self, requested_schema=None):
        self.calls += 1
        return self.source.__arrow_c_stream__(requested_schema)


def interop_stream(
    binding,
    batches,
    total,
    *,
    limits=None,
    late=False,
    early=False,
    close_error=None,
    borrow=False,
    route="checked",
) -> dict[str, Any]:
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_result_reader as reader_api

    pa = importlib.import_module("pyarrow")
    with ReaderTrace(
        binding.schema, batches, late=late, close_error=close_error
    ) as trace:
        from pietto._project import project_result_ingress as ingress

        owner = InteropOwner()
        policy = reader_api.FiniteReaderLimits() if limits is None else limits
        provider = None
        if route == "checked":
            reader = reader_api.open_finite_reader(
                binding, trace.source, expected_rows=total, limits=policy
            )
            lease = (
                interop.BorrowLease(reader, binding, owner, True) if borrow else None
            )
            session = interop.manage_stream(reader, lease=lease)
        elif route == "raw":
            lease = (
                interop.BorrowLease(trace.source, binding, owner, True)
                if borrow
                else None
            )
            session = ingress.ingest_reader(
                binding, trace.source, expected_rows=total, limits=policy, lease=lease
            )
            reader = session._reader
        else:
            assert route == "protocol"
            provider = ProtocolStream(trace.source)
            lease = (
                interop.BorrowLease(provider, binding, owner, True) if borrow else None
            )
            session = interop.import_stream(
                binding, provider, expected_rows=total, limits=policy, lease=lease
            )
            reader = session._reader
        pre_read = trace.reads
        consumer = pa.RecordBatchReader.from_stream(session)
        assert reader.pulls == 0 and trace.reads == 0
        competing = refused(reader.read_next_batch)
        snapshots = []
        error = None
        foreign_error = None
        try:
            if early:
                snapshots.append(finite_snapshot(consumer.read_next_batch()))
            else:
                for batch in consumer:
                    snapshots.append(finite_snapshot(batch))
        except Exception as exc:
            foreign_error = type(exc).__name__
            primary = session.primary_error
            error = (
                primary.category
                if isinstance(primary, reader_api.ResultError)
                else type(primary).__name__
                if primary is not None
                else foreign_error
            )
        before = [session.state, reader.state]
        consumer.close()
        after_foreign = reader.state
        try:
            session.close()
        except Exception as exc:
            if error is None:
                error = (
                    exc.category
                    if isinstance(exc, reader_api.ResultError)
                    else type(exc).__name__
                )
        session.close()
        result: dict[str, Any] = dict(
            before=before,
            after=[session.state, reader.state],
            after_foreign=after_foreign,
            source_complete=session.input_completion is not None,
            charge=session.charge,
            descriptors=[list(d) for d in session.descriptors],
            chunks=[len(s["rows"]) for s in snapshots],
            rows=[r for s in snapshots for r in s["rows"]],
            error=error,
            foreign_error=foreign_error,
            source_rows=reader.rows,
            competing=competing,
            closes=trace.closes,
            reads=trace.reads,
        )
        if route != "checked":
            result.update(
                route=route,
                pre_read=pre_read,
                provider_calls=0 if provider is None else provider.calls,
                snapshots=snapshots,
            )
        return result


def interop_stream_expected(
    usages,
    rows,
    *,
    failure=None,
    early=False,
    counts=None,
    input_state=None,
    borrow=False,
) -> dict[str, Any]:
    sizes = [u[0] for u in usages]
    counts = sizes if counts is None else counts
    state = input_state or (
        "FAILED" if failure else "CLOSED_INCOMPLETE" if early else "COMPLETE"
    )
    before_input = "OPEN" if early else state
    return dict(
        before=[
            "FAILED" if failure else "EXPORTED" if early else "EXHAUSTED",
            before_input,
        ],
        after=[
            "FAILED" if failure else "CLOSED_INCOMPLETE" if early else "CLOSED",
            state,
        ],
        after_foreign=before_input,
        source_complete=state == "COMPLETE",
        charge=sum(max(logical, retained) for _, logical, retained in usages),
        descriptors=[
            [n, logical, retained, logical, retained, 0 if borrow else retained * 2]
            for n, logical, retained in usages
        ],
        chunks=sizes,
        rows=rows,
        error=failure,
        foreign_error="ArrowInvalid" if failure else None,
        source_rows=sum(u[0] for u in usages),
        competing="READER_CLAIMED",
        closes=1,
        reads=len(counts)
        if early
        or failure == "LIMIT"
        or (failure == "READER_EXTENT" and len(counts) > len(usages))
        else len(counts) + 1,
    )


def run_interop_cases(root):
    import gc
    import itertools
    import weakref
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_reader as r

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {name: {} for name in INTEROP_GROUPS}
    for target in ("postgres", "mysql"):
        *_, producer, _ = finite_fixture(root / ("interop-" + target), target)
        *_, nullable_producer, _ = finite_fixture(
            root / ("interop-null-" + target), target, all_nullable=True
        )
        binding = a.bind_arrow(producer, **finite_policy(producer))
        nullable = a.bind_arrow(nullable_producer, **finite_policy(nullable_producer))
        rows = finite_rows(target)
        batch = a.build_owned_batch(binding, rows)
        empty = a.build_owned_batch(binding, [])
        nulls = a.build_owned_batch(nullable, finite_rows(target, state="null"))
        source, owner = mutable_finite(batch)
        managed = interop.manage_batch(binding, source)
        owned = pa.record_batch(managed)
        independent = all(
            x.address != y.address
            for c, d in zip(source.columns, owned.columns, strict=True)
            for x, y in zip(c.buffers(), d.buffers(), strict=True)
            if x is not None and y is not None and x.size
        )
        mutate_finite(owner)
        protocol_oracle(finite_snapshot(owned))
        managed.close()
        managed.close()
        copy_cases = dict(
            values=finite_snapshot(owned),
            source_after=finite_snapshot(source),
            independent=independent,
            closed=refused(lambda: pa.record_batch(managed)),
            empty=finite_snapshot(
                pa.record_batch(interop.manage_batch(binding, empty))
            ),
            sliced=finite_snapshot(
                pa.record_batch(interop.manage_batch(binding, batch.slice(1, 2)))
            ),
            all_null=finite_snapshot(
                pa.record_batch(interop.manage_batch(nullable, nulls))
            ),
        )
        original_copy = interop._copy_batch

        def forbidden(*args, **kwargs):
            raise AssertionError("copy before source validation")

        invalid = pa.RecordBatch.from_arrays(
            [
                pa.array([float("nan")] * 4, type=pa.float64()) if j == 4 else column
                for j, column in enumerate(batch.columns)
            ],
            schema=binding.schema,
        )
        try:
            interop._copy_batch = forbidden
            copy_cases["invalid_before_copy"] = refused(
                lambda: interop.manage_batch(binding, invalid)
            )
            fresh = interop.build_managed_batch(binding, rows)
            copy_cases["fresh_owned"] = finite_snapshot(pa.record_batch(fresh))
            fresh.close()
        finally:
            interop._copy_batch = original_copy
        fresh = interop.build_managed_batch(binding, rows)
        import struct

        assert fresh._batch is not None
        memoryview(fresh._batch.column(4).buffers()[1]).cast("B")[:8] = struct.pack(
            "<d", float("nan")
        )
        copy_cases["fresh_mutable_guard"] = refused(lambda: pa.record_batch(fresh))
        fresh.close()
        results["ownership_copy"][target] = copy_cases

        source, owner = mutable_finite(batch)
        owner_ref = weakref.ref(owner)
        lease = interop.BorrowLease(source, binding, owner, True)
        borrowed = interop.manage_batch(binding, source, lease=lease)
        imported = pa.record_batch(borrowed)
        shared = all(
            x.address == y.address
            for c, d in zip(source.columns, imported.columns, strict=True)
            for x, y in zip(c.buffers(), d.buffers(), strict=True)
            if x is not None and y is not None
        )
        mutate_finite(owner)
        after_alias = finite_snapshot(imported)
        refusals = []
        for broken in (
            interop.BorrowLease(source, binding, owner, False),
            interop.BorrowLease(batch, binding, owner, True),
            interop.BorrowLease(source, binding, None, True),
            interop.BorrowLease(source, nullable, owner, True),
        ):
            refusals.append(
                refused(
                    lambda lease=broken, source=source: interop.manage_batch(
                        binding, source, lease=lease
                    )
                )
            )
        del broken
        object.__delattr__(lease, "non_mutation")
        deleted = refused(lambda borrowed=borrowed: pa.record_batch(borrowed))
        object.__setattr__(lease, "non_mutation", True)
        borrowed.close()
        del borrowed, lease, source, owner
        gc.collect()
        pinned = owner_ref() is not None
        del imported
        gc.collect()
        results["ownership_borrow"][target] = dict(
            shared=shared,
            alias_values=after_alias,
            refusals=refusals,
            deleted_commitment=deleted,
            pinned_after_exporter_close=pinned,
            released_after_consumer=owner_ref() is None,
            obligation="stable backing through every derived consumer",
        )

        managed = interop.manage_batch(binding, batch)
        grant = managed.transfer()
        copied_transfer = refused(lambda: pa.record_batch(copy(grant)))
        transferred = pa.record_batch(grant)
        replay = refused(lambda: pa.record_batch(grant))
        pending = managed.transfer()
        pending.close()
        disposed = refused(lambda: pa.record_batch(pending))
        original_export = interop._export_array

        def broken_export(batch):
            raise RuntimeError("injected export failure")

        try:
            interop._export_array = broken_export
            failed = managed.transfer()
            failure = protocol_error(lambda: pa.record_batch(failed))
        finally:
            interop._export_array = original_export
        failed_replay = refused(lambda: pa.record_batch(failed))
        capsules = managed.__arrow_c_array__()
        capsule_value = pa.RecordBatch._import_from_c_capsule(*capsules)
        native_replay = protocol_error(
            lambda: pa.RecordBatch._import_from_c_capsule(*capsules)
        )
        unused = managed.__arrow_c_array__()
        del unused
        gc.collect()
        managed.close()
        results["ownership_transfer"][target] = dict(
            values=finite_snapshot(transferred),
            capsule_values=finite_snapshot(capsule_value),
            replay=replay,
            disposed=disposed,
            failure=failure,
            failed_replay=failed_replay,
            native_replay=native_replay,
            buffer_policy=managed.buffer_policy,
            copied_transfer=copied_transfer,
        )
        exported = interop.manage_batch(binding, batch)
        schema = pa.schema(exported)
        provider = ProtocolBatch(batch)
        adopted = interop.import_batch(binding, provider)
        results["c_schema_array"][target] = dict(
            schema_equal=schema.equals(binding.schema, check_metadata=True),
            values=finite_snapshot(pa.record_batch(exported)),
            imported=finite_snapshot(pa.record_batch(adopted)),
            provider_calls=provider.calls,
            consumer="pyarrow",
            independent_c_implementation=False,
        )
        exported.close()
        adopted.close()

        managed = interop.manage_batch(binding, batch)
        changes = {
            "int": (0, pa.int32(), None, None),
            "text": (5, pa.large_string(), None, None),
            "precision": (7, pa.decimal128(8, 2), None, None),
            "scale": (7, pa.decimal128(9, 1), None, None),
            "unit": (9, pa.timestamp("ms"), None, None),
            "timezone": (9, pa.timestamp("us", tz="UTC"), None, None),
            "uuid": (10, pa.binary(16), None, None),
            "label": (12, None, "other", None),
            "nullable": (0, None, None, True),
            "metadata": (0, None, None, None),
        }
        request_errors = {}
        for name, (position, kind, label, optional) in changes.items():
            fields = [
                pa.field(
                    label if label is not None and j == position else f.name,
                    kind if kind is not None and j == position else f.type,
                    nullable=optional
                    if optional is not None and j == position
                    else f.nullable,
                    metadata={b"fake": b"authority"}
                    if name == "metadata" and j == position
                    else None,
                )
                for j, f in enumerate(binding.schema)
            ]
            request = pa.schema(fields)
            grant = managed.transfer()
            request_errors[name] = refused(
                lambda: grant.__arrow_c_array__(request.__arrow_c_schema__())
            )
            assert finite_snapshot(pa.record_batch(grant)) == protocol_expected()
        request_errors["schema_metadata"] = refused(
            lambda: managed.__arrow_c_array__(
                binding.schema.with_metadata(
                    {b"fake": b"authority"}
                ).__arrow_c_schema__()
            )
        )
        equivalent = pa.RecordBatch._import_from_c_capsule(
            *managed.__arrow_c_array__(binding.schema.__arrow_c_schema__())
        )
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            bad_request = binding.schema.set(
                0, pa.field("wrong", pa.int16(), nullable=False)
            )
            stream_error = refused(
                lambda: stream.__arrow_c_stream__(bad_request.__arrow_c_schema__())
            )
            no_pulls = trace.reads
            capsule = stream.__arrow_c_stream__(binding.schema.__arrow_c_schema__())
            foreign = pa.RecordBatchReader._import_from_c_capsule(capsule)
            stream_rows = [
                row for part in foreign for row in finite_snapshot(part)["rows"]
            ]
            foreign.close()
            stream.close()
        results["c_schema_requests"][target] = dict(
            refusals=request_errors,
            equivalent=finite_snapshot(equivalent),
            stream_refusal=stream_error,
            request_pulls=no_pulls,
            stream_rows=stream_rows,
        )
        managed.close()

        layouts = [
            empty,
            batch.slice(0, 1),
            empty,
            batch.slice(1, 2),
            batch.slice(3, 1),
            empty,
        ]
        values = interop_stream(binding, layouts, 4)
        borrowed_stream = interop_stream(binding, [batch], 4, borrow=True)
        raw = pa.RecordBatchReader.from_batches(binding.schema, [batch])
        provider = ProtocolStream(raw)
        imported_session = interop.import_stream(binding, provider, expected_rows=4)
        with imported_session:
            foreign = pa.RecordBatchReader.from_stream(imported_session)
            imported_rows = [
                row for part in foreign for row in finite_snapshot(part)["rows"]
            ]
            foreign.close()
        results["c_stream_values"][target] = dict(
            mixed=values,
            borrowed=borrowed_stream,
            all_null=interop_stream(nullable, [nulls], 2),
            zero=interop_stream(binding, [], 0),
            imported_rows=imported_rows,
            imported_complete=imported_session.input_completion is not None,
            provider_calls=provider.calls,
        )
        terminal: dict[str, Any] = dict(
            short=interop_stream(binding, [batch.slice(0, 3)], 4),
            extra=interop_stream(binding, [batch, batch], 4),
            late=interop_stream(binding, [batch], 4, late=True),
            early=interop_stream(binding, [batch], 4, early=True),
            normal=interop_stream(binding, [batch, empty], 4),
            cleanup=interop_stream(
                binding, [batch], 4, close_error=RuntimeError("injected source close")
            ),
        )
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            foreign = pa.RecordBatchReader.from_stream(stream)
            original_copy = interop._copy_batch

            def invalid_copy(*args, **kwargs):
                raise StopIteration("injected bridge stop")

            try:
                interop._copy_batch = invalid_copy
                bridge_error = protocol_error(foreign.read_next_batch)
            finally:
                interop._copy_batch = original_copy
            foreign.close()
            stream.close()
            terminal["bridge_failure"] = dict(
                error=bridge_error,
                primary=type(stream.primary_error).__name__,
                states=[reader.state, stream.state],
                rows=reader.rows,
                delivered=len(stream.descriptors),
                input_complete=stream.input_completion is not None,
            )
        original_close = interop._close_bridge
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            foreign = pa.RecordBatchReader.from_stream(stream)
            list(foreign)
            foreign.close()

            def close_failure(bridge):
                original_close(bridge)
                raise RuntimeError("injected downstream close")

            try:
                interop._close_bridge = close_failure
                close_error = refused(stream.close)
            finally:
                interop._close_bridge = original_close
            terminal["completed_input_failed_delivery_cleanup"] = dict(
                error=close_error,
                states=[reader.state, stream.state],
                input_complete=stream.input_completion is not None,
            )
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            foreign = pa.RecordBatchReader.from_stream(stream)
            old_copy = interop._copy_batch

            def interrupted_copy(*args, **kwargs):
                raise KeyboardInterrupt("injected bridge control")

            try:
                interop._copy_batch = interrupted_copy
                try:
                    with stream:
                        foreign.read_next_batch()
                except KeyboardInterrupt:
                    terminal["context_control"] = [
                        stream.state,
                        reader.state,
                        type(stream.primary_error).__name__,
                        trace.closes,
                    ]
                else:
                    raise AssertionError("context lost original control exception")
            finally:
                interop._copy_batch = old_copy
                foreign.close()
        results["c_stream_terminal"][target] = terminal

        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            foreign = pa.RecordBatchReader.from_stream(stream)
            retained = foreign.read_next_batch()
            foreign.close()
            native_close_did_not_finish = reader.state
            stream.close()
            stream.close()
            closed_states = [stream.state, reader.state]
            del foreign, stream
            gc.collect()
            lifetime_values = finite_snapshot(retained)
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            capsule = stream.__arrow_c_stream__()
            del capsule
            gc.collect()
            unread = [reader.pulls, reader.state]
            stream.close()
            unconsumed = [reader.pulls, reader.state, trace.closes]
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream_owner = InteropOwner()
            stream_owner_ref = weakref.ref(stream_owner)
            stream_lease = interop.BorrowLease(reader, binding, stream_owner, True)
            stream = interop.manage_stream(reader, lease=stream_lease)
            foreign = pa.RecordBatchReader.from_stream(stream)
            retained_borrow = foreign.read_next_batch()
            foreign.close()
            stream.close()
            del stream, stream_lease, stream_owner, foreign
            gc.collect()
            stream_pinned = stream_owner_ref() is not None
            assert finite_snapshot(retained_borrow)["rows"] == finite_expected()["rows"]
            del retained_borrow
            gc.collect()
            stream_released = stream_owner_ref() is None
        results["c_protocol_lifetime"][target] = dict(
            retained=lifetime_values,
            foreign_close_state=native_close_did_not_finish,
            explicit_close_states=closed_states,
            unconsumed_before=unread,
            unconsumed_after=unconsumed,
            callback_count_claim=False,
            borrowed_stream_owner=[stream_pinned, stream_released],
        )

        class DeviceOnly:
            calls = 0

            def __arrow_c_device_array__(self, *args, **kwargs):
                self.calls += 1
                raise AssertionError("device route invoked")

            def __arrow_c_device_stream__(self, *args, **kwargs):
                self.calls += 1
                raise AssertionError("device stream invoked")

        device = DeviceOnly()

        class BadArray:
            def __arrow_c_array__(self, requested_schema=None):
                return (None, None)

        class BadStream:
            def __arrow_c_stream__(self, requested_schema=None):
                return None

        exact = interop.manage_batch(binding, batch, limits=a.BatchLimits(bytes=630))
        exact_value = finite_snapshot(pa.record_batch(exact))
        exact.close()
        tiny = invalid.slice(0, 1)
        original_copy = interop._copy_batch
        try:
            interop._copy_batch = forbidden
            retained_first = refused(
                lambda: interop.manage_batch(
                    binding, tiny, limits=a.BatchLimits(bytes=527)
                )
            )
        finally:
            interop._copy_batch = original_copy

        def padded_copy(value, lease):
            copied = original_copy(value, lease)
            columns = list(copied.columns)
            column = columns[0]
            validity, data = column.buffers()
            buffer = pa.py_buffer(bytes(memoryview(data)) + bytes(1024))
            columns[0] = pa.Array.from_buffers(
                column.type,
                len(column),
                [validity, buffer],
                offset=column.offset,
                null_count=-1,
            )
            return pa.RecordBatch.from_arrays(columns, schema=copied.schema)

        try:
            interop._copy_batch = padded_copy
            delivery_limit = refused(
                lambda: interop.manage_batch(
                    binding, batch, limits=a.BatchLimits(bytes=630)
                )
            )
        finally:
            interop._copy_batch = original_copy

        def slightly_padded_copy(value, lease):
            copied = original_copy(value, lease)
            columns = list(copied.columns)
            column = columns[0]
            validity, data = column.buffers()
            columns[0] = pa.Array.from_buffers(
                column.type,
                len(column),
                [validity, pa.py_buffer(bytes(memoryview(data)) + bytes(128))],
                offset=column.offset,
                null_count=-1,
            )
            return pa.RecordBatch.from_arrays(columns, schema=copied.schema)

        try:
            interop._copy_batch = slightly_padded_copy
            delivery_total = interop_stream(
                binding,
                [batch, batch],
                8,
                limits=r.FiniteReaderLimits(max_total_bytes=1311),
            )
        finally:
            interop._copy_batch = original_copy
        results["cpu_protocol_resources"][target] = dict(
            cpu=batch.is_cpu,
            device=[
                refused(lambda: interop.import_batch(binding, device)),
                refused(
                    lambda: interop.import_stream(binding, device, expected_rows=0)
                ),
            ],
            device_calls=device.calls,
            malformed=[
                protocol_error(lambda: interop.import_batch(binding, BadArray())),
                protocol_error(
                    lambda: interop.import_stream(binding, BadStream(), expected_rows=0)
                ),
            ],
            exact=exact_value,
            under=refused(
                lambda: interop.manage_batch(
                    binding, batch, limits=a.BatchLimits(bytes=629)
                )
            ),
            retained_first=retained_first,
            delivery_limit=delivery_limit,
            stream_under=interop_stream(
                binding,
                [batch, batch],
                8,
                limits=r.FiniteReaderLimits(max_total_bytes=1259),
            ),
            empty_cap=interop_stream(
                binding,
                itertools.repeat(empty),
                0,
                limits=r.FiniteReaderLimits(max_batches=2),
            ),
            gpu_executed=False,
            delivery_total=delivery_total,
        )

        managed = interop.manage_batch(binding, batch)
        original = managed._captured
        foreign_binding = a.bind_arrow(
            nullable_producer, **finite_policy(nullable_producer)
        )
        try:
            managed._captured = (foreign_binding, *original[1:])
            graft = refused(lambda: pa.record_batch(managed))
        finally:
            managed._captured = original
        old_policy = managed._policy
        try:
            managed._policy = "borrowed"
            policy_error = refused(lambda: pa.record_batch(managed))
        finally:
            managed._policy = old_policy
        managed.close()
        with ReaderTrace(binding.schema, [batch]) as trace:
            reader = r.open_finite_reader(binding, trace.source, expected_rows=4)
            stream = interop.manage_stream(reader)
            reuse = refused(lambda: interop.manage_stream(reader))
            copied_stream = copy(stream)
            copied_refusal = refused(
                lambda copied_stream=copied_stream: pa.RecordBatchReader.from_stream(
                    copied_stream
                )
            )
            del copied_stream
            gc.collect()
            copy_disposal_state = reader.state
            foreign = pa.RecordBatchReader.from_stream(stream)
            duplicate_grant = refused(lambda: pa.RecordBatchReader.from_stream(stream))
            foreign.close()
            stream.close()
        swaps = []
        columns = list(batch.columns)
        columns[0], columns[12] = columns[12], columns[0]
        swapped = pa.RecordBatch.from_arrays(columns, schema=binding.schema)
        for candidate in (swapped,):
            observed = interop_stream(binding, [candidate], 4)
            try:
                finite_oracle(dict(finite_expected(), rows=observed["rows"]))
            except ValueError:
                swaps.append(
                    dict(
                        rows=observed["rows"],
                        source_complete=observed["source_complete"],
                        oracle="VALUE_CORRESPONDENCE",
                    )
                )
            else:
                raise AssertionError("protocol swap escaped original values")

        def changed_copy(value, lease):
            copied = original_copy(value, lease)
            cols = list(copied.columns)
            cols[0], cols[12] = cols[12], cols[0]
            return pa.RecordBatch.from_arrays(cols, schema=copied.schema)

        try:
            interop._copy_batch = changed_copy
            observed = interop_stream(binding, [batch], 4)
            try:
                finite_oracle(dict(finite_expected(), rows=observed["rows"]))
            except ValueError:
                injected = "VALUE_CORRESPONDENCE"
            else:
                raise AssertionError("value-changing bridge manufactured success")
        finally:
            interop._copy_batch = original_copy
        results["interop_correspondence"][target] = dict(
            binding=graft,
            policy=policy_error,
            reuse=reuse,
            duplicate_grant=duplicate_grant,
            copied_stream=copied_refusal,
            copy_disposal_state=copy_disposal_state,
            swaps=swaps,
            injected=injected,
        )
    return results


def verify_interop_report(cases):
    try:
        if any(set(cases[name]) != {"postgres", "mysql"} for name in INTEROP_GROUPS):
            raise ValueError("interop denominator")
        rows = protocol_expected()["rows"]
        whole = READER_LAYOUTS["whole"]
        for target in ("postgres", "mysql"):

            def require(name, expected):
                if not _exact(cases[name][target], expected):
                    raise ValueError(
                        "interop observed "
                        + name
                        + ": "
                        + json.dumps(
                            {"actual": cases[name][target], "expected": expected},
                            sort_keys=True,
                        )
                    )

            require(
                "ownership_copy",
                dict(
                    values=protocol_expected(),
                    source_after=mutated_finite_expected(),
                    independent=True,
                    closed="INTEROP_CLOSED",
                    empty=protocol_expected(state="empty"),
                    sliced=interop_snapshot_slice(1, 3),
                    all_null=protocol_expected(state="null", all_nullable=True),
                    invalid_before_copy="VALUE_DOMAIN",
                    fresh_owned=protocol_expected(),
                    fresh_mutable_guard="VALUE_DOMAIN",
                ),
            )
            require(
                "ownership_borrow",
                dict(
                    shared=True,
                    alias_values={
                        **mutated_finite_expected(),
                        "fields": protocol_expected()["fields"],
                    },
                    refusals=["INTEROP_LEASE"] * 4,
                    deleted_commitment="INTEROP_LEASE",
                    pinned_after_exporter_close=True,
                    released_after_consumer=True,
                    obligation="stable backing through every derived consumer",
                ),
            )
            require(
                "ownership_transfer",
                dict(
                    values=protocol_expected(),
                    capsule_values=protocol_expected(),
                    replay="INTEROP_SPENT",
                    disposed="INTEROP_SPENT",
                    failure="RuntimeError",
                    failed_replay="INTEROP_SPENT",
                    native_replay="ArrowInvalid",
                    buffer_policy="owned_copy",
                    copied_transfer="INTEROP_BINDING",
                ),
            )
            require(
                "c_schema_array",
                dict(
                    schema_equal=True,
                    values=protocol_expected(),
                    imported=protocol_expected(),
                    provider_calls=1,
                    consumer="pyarrow",
                    independent_c_implementation=False,
                ),
            )
            require(
                "c_schema_requests",
                dict(
                    refusals=dict.fromkeys(
                        (
                            "int",
                            "text",
                            "precision",
                            "scale",
                            "unit",
                            "timezone",
                            "uuid",
                            "label",
                            "nullable",
                            "metadata",
                            "schema_metadata",
                        ),
                        "INTEROP_REQUEST",
                    ),
                    equivalent=protocol_expected(),
                    stream_refusal="INTEROP_REQUEST",
                    request_pulls=0,
                    stream_rows=rows,
                ),
            )
            require(
                "c_stream_values",
                dict(
                    mixed=interop_stream_expected(
                        READER_LAYOUTS["empty_interleaved"], rows
                    ),
                    borrowed=interop_stream_expected(whole, rows, borrow=True),
                    all_null=interop_stream_expected(
                        ((2, 321, 274),), [[None] * 13] * 2
                    ),
                    zero=interop_stream_expected((), []),
                    imported_rows=rows,
                    imported_complete=True,
                    provider_calls=1,
                ),
            )
            require(
                "c_stream_terminal",
                dict(
                    short=interop_stream_expected(
                        ((3, 480, 528),), rows[:3], failure="READER_EXTENT"
                    ),
                    extra=interop_stream_expected(
                        whole, rows, failure="READER_EXTENT", counts=[4, 4]
                    ),
                    late=interop_stream_expected(whole, rows, failure="READER_SOURCE"),
                    early=interop_stream_expected(whole, rows, early=True),
                    normal=interop_stream_expected((*whole, (0, 12, 12)), rows),
                    cleanup=interop_stream_expected(
                        whole, rows, failure="READER_CLEANUP"
                    ),
                    bridge_failure=dict(
                        error="ArrowInvalid",
                        primary="StopIteration",
                        states=["CLOSED_INCOMPLETE", "FAILED"],
                        rows=4,
                        delivered=0,
                        input_complete=False,
                    ),
                    context_control=[
                        "FAILED",
                        "CLOSED_INCOMPLETE",
                        "KeyboardInterrupt",
                        1,
                    ],
                    completed_input_failed_delivery_cleanup=dict(
                        error="INTEROP_CLEANUP",
                        states=["COMPLETE", "FAILED"],
                        input_complete=True,
                    ),
                ),
            )
            require(
                "c_protocol_lifetime",
                dict(
                    retained=protocol_expected(),
                    foreign_close_state="OPEN",
                    explicit_close_states=["CLOSED_INCOMPLETE", "CLOSED_INCOMPLETE"],
                    unconsumed_before=[0, "OPEN"],
                    unconsumed_after=[0, "CLOSED_INCOMPLETE", 1],
                    callback_count_claim=False,
                    borrowed_stream_owner=[True, True],
                ),
            )
            delivery_total = interop_stream_expected(
                whole,
                rows,
                failure="LIMIT",
                counts=[4, 4],
                input_state="CLOSED_INCOMPLETE",
            )
            delivery_total.update(
                charge=656, descriptors=[[4, 630, 528, 630, 656, 1184]], source_rows=8
            )
            require(
                "cpu_protocol_resources",
                dict(
                    cpu=True,
                    device=["INTEROP_DEVICE"] * 2,
                    device_calls=0,
                    malformed=["INTEROP_PROTOCOL"] * 2,
                    exact=protocol_expected(),
                    under="LIMIT",
                    retained_first="LIMIT",
                    delivery_limit="LIMIT",
                    stream_under=interop_stream_expected(
                        whole, rows, failure="LIMIT", counts=[4, 4]
                    ),
                    empty_cap=interop_stream_expected(
                        ((0, 12, 12),) * 2, [], failure="LIMIT", counts=[0, 0, 0]
                    ),
                    gpu_executed=False,
                    delivery_total=delivery_total,
                ),
            )
            swapped = json.loads(json.dumps(rows))
            for row in swapped:
                row[0], row[12] = row[12], row[0]
            require(
                "interop_correspondence",
                dict(
                    binding="READER_IDENTITY",
                    policy="INTEROP_BINDING",
                    reuse="READER_CLAIMED",
                    duplicate_grant="INTEROP_SPENT",
                    copied_stream="INTEROP_BINDING",
                    copy_disposal_state="OPEN",
                    swaps=[
                        dict(
                            rows=swapped,
                            source_complete=True,
                            oracle="VALUE_CORRESPONDENCE",
                        )
                    ],
                    injected="VALUE_CORRESPONDENCE",
                ),
            )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("interop report evidence") from exc


CONTRACT_CORPUS = ("postgres", "mysql", "descriptors", "imported")
CONTRACT_SEEDS = (7, 19)


INGRESS_GROUPS = (
    "ingress_rows",
    "ingress_batch",
    "ingress_reader",
    "ingress_parity",
    "ingress_refusals",
    "ingress_ownership",
    "ingress_resources",
    "ingress_independence",
)
INGRESS_STATES = ("values", "empty", "null", "first_null")
INGRESS_USAGES = {
    "values": (630, 528),
    "empty": (12, 12),
    "null": (321, 274),
    "first_null": (778, 659),
}


def native_finite(*, state="values"):
    """SDK fixture from authored logical literals, never the producer row mapper."""
    import struct
    from decimal import Decimal

    pa = importlib.import_module("pyarrow")
    nullable = state in ("null", "first_null")
    literals = finite_expected(state=state, all_nullable=nullable)
    types = [
        pa.int16(),
        pa.int32(),
        pa.int64(),
        pa.bool_(),
        pa.float64(),
        pa.string(),
        pa.large_string(),
        pa.decimal128(9, 2),
        pa.decimal256(65, 30),
        pa.timestamp("us"),
        pa.uuid(),
        pa.binary(16),
        pa.int16(),
    ]
    columns = []
    for i, type_ in enumerate(types):
        values = []
        for row in literals["rows"]:
            value = row[i]
            if value is not None:
                if i == 4:
                    value = struct.unpack(">d", bytes.fromhex(value))[0]
                elif i in (5, 6):
                    value = bytes.fromhex(value).decode("utf-8")
                elif i in (7, 8):
                    coefficient = int(value)
                    value = Decimal(
                        (
                            int(coefficient < 0),
                            tuple(map(int, str(abs(coefficient)))),
                            -type_.scale,
                        )
                    )
                elif i in (10, 11):
                    value = bytes.fromhex(value)
            values.append(value)
        columns.append(pa.array(values, type=type_))
    schema = pa.schema(
        [
            pa.field(f["label"], type_, nullable=f["nullable"])
            for f, type_ in zip(literals["fields"], types, strict=True)
        ]
    )
    return pa.RecordBatch.from_arrays(columns, schema=schema)


def ingress_batch_snapshot(managed) -> dict[str, Any]:
    pa = importlib.import_module("pyarrow")
    try:
        output = pa.record_batch(managed)
        return dict(
            snapshot=finite_snapshot(output),
            policy=managed.buffer_policy,
            source_usage=list(managed.source_usage),
            usage=list(managed.usage),
            completion=hasattr(managed, "input_completion"),
        )
    finally:
        managed.close()


def ingress_batch_expected(state="values") -> dict[str, Any]:
    return dict(
        snapshot=protocol_expected(
            state=state, all_nullable=state in ("null", "first_null")
        ),
        policy="owned_copy",
        source_usage=list(INGRESS_USAGES[state]),
        usage=list(INGRESS_USAGES[state]),
        completion=False,
    )


def ingress_stream_expected(usages, rows, *, route="raw", nullable=False, **kwargs):
    expected = interop_stream_expected(usages, rows, **kwargs)
    snapshots = []
    start = 0
    for count in expected["chunks"]:
        value = protocol_expected(all_nullable=nullable)
        value["rows"] = rows[start : start + count]
        value["valid"] = [[v is not None for v in row] for row in value["rows"]]
        snapshots.append(value)
        start += count
    expected.update(
        route=route,
        pre_read=0,
        provider_calls=int(route == "protocol"),
        snapshots=snapshots,
    )
    return expected


def ingress_value_oracle(rows):
    if not _exact(rows, finite_expected()["rows"]):
        raise ValueError("ingress original-value correspondence")


def run_ingress_cases(root):
    import gc
    import itertools
    import weakref
    from decimal import Decimal
    from pietto._project import project_arrow_result as a
    from pietto._project import project_arrow_interop as i
    from pietto._project import project_result_reader as r
    from pietto._project import project_result_ingress as ingress
    from pietto._project.project_result_contract_portable import export_result_contract

    pa = importlib.import_module("pyarrow")
    results: dict[str, Any] = {name: {} for name in INGRESS_GROUPS}
    for target in ("postgres", "mysql"):
        checked, _, _, neutral, producer, _ = finite_fixture(
            root / ("ingress-" + target), target
        )
        *_, np, _ = finite_fixture(
            root / ("ingress-null-" + target), target, all_nullable=True
        )
        binding = a.bind_arrow(producer, **finite_policy(producer))
        nullable = a.bind_arrow(np, **finite_policy(np))
        rows = finite_rows(target)
        native = native_finite()
        empty = native_finite(state="empty")
        before = export_result_contract(neutral, checked).canonical_bytes
        row_cases = {}
        old_copy = i._copy_batch

        def forbidden(*args, **kwargs):
            raise AssertionError("unexpected conversion or copy")

        try:
            i._copy_batch = forbidden
            for state in INGRESS_STATES:
                chosen = nullable if state in ("null", "first_null") else binding
                supplied = finite_rows(target, state=state)
                managed = ingress.ingest_rows(chosen, supplied)
                # Mutating caller containers cannot modify the already built buffers.
                if supplied:
                    supplied[0][12] = 42
                row_cases[state] = ingress_batch_snapshot(managed)
        finally:
            i._copy_batch = old_copy
        bad_rows = [
            dict(value=1),
            iter(rows),
            [rows[0][:-1]],
            [dict(enumerate(rows[0]))],
        ]
        row_errors = [
            refused(lambda value=value: ingress.ingest_rows(binding, value))
            for value in bad_rows
        ]
        for ordinal, value in (
            (3, 0 if target == "postgres" else False),
            (9, -1),
            (10, bytes(16) if target == "postgres" else __import__("uuid").UUID(int=0)),
            (7, 12.34),
        ):
            wrong = list(rows[0])
            wrong[ordinal] = value
            row_errors.append(
                refused(lambda wrong=wrong: ingress.ingest_rows(binding, [wrong]))
            )
        redundant = [list(row) for row in rows]
        redundant[0][7] = Decimal("12.3400")
        row_cases.update(
            refusals=row_errors,
            redundant=ingress_batch_snapshot(ingress.ingest_rows(binding, redundant)),
        )
        results["ingress_rows"][target] = row_cases

        batch_cases: dict[str, Any] = {
            state: ingress_batch_snapshot(
                ingress.ingest_batch(
                    nullable if state in ("null", "first_null") else binding,
                    native_finite(state=state),
                )
            )
            for state in INGRESS_STATES
        }
        sliced = native.slice(1, 2)
        batch_cases["sliced"] = ingress_batch_snapshot(
            ingress.ingest_batch(binding, sliced)
        )
        batch_cases["offsets"] = [c.offset for c in sliced.columns]
        # Legal absent zero-length fixed-width buffers: no reconstruction is needed.
        cols = list(empty.columns)
        for position in (9, 10, 11):
            col = cols[position]
            extension = position == 10
            storage_type = pa.binary(16) if extension else col.type
            storage = pa.Array.from_buffers(storage_type, 0, [None, None])
            cols[position] = (
                pa.ExtensionArray.from_storage(pa.uuid(), storage)
                if extension
                else storage
            )
        absent = pa.RecordBatch.from_arrays(cols, schema=empty.schema)
        batch_cases["absent"] = ingress_batch_snapshot(
            ingress.ingest_batch(binding, absent)
        )
        invalid = {}
        for name, position, col in (
            ("float", 4, pa.array([float("nan")] * 4, type=pa.float64())),
            (
                "utf8",
                5,
                pa.Array.from_buffers(
                    pa.string(),
                    4,
                    [
                        None,
                        pa.py_buffer(b"\0\0\0\0" + (1).to_bytes(4, "little") * 4),
                        pa.py_buffer(b"\xff"),
                    ],
                ),
            ),
            (
                "precision",
                7,
                pa.Array.from_buffers(
                    pa.decimal128(9, 2),
                    4,
                    [None, pa.py_buffer((10**9).to_bytes(16, "little") * 4)],
                ),
            ),
            (
                "timestamp",
                9,
                pa.Array.from_buffers(
                    pa.timestamp("us"),
                    4,
                    [None, pa.py_buffer((2**63 - 1).to_bytes(8, "little") * 4)],
                ),
            ),
            ("null", 12, pa.array([None] * 4, type=pa.int16())),
        ):
            columns = list(native.columns)
            columns[position] = col
            invalid[name] = pa.RecordBatch.from_arrays(columns, schema=native.schema)
        try:
            i._copy_batch = forbidden
            batch_cases["original_refusals"] = {
                name: refused(lambda batch=batch: ingress.ingest_batch(binding, batch))
                for name, batch in invalid.items()
            }
        finally:
            i._copy_batch = old_copy
        results["ingress_batch"][target] = batch_cases

        layouts = {
            "whole": [native],
            "uneven": [native.slice(0, 1), native.slice(1, 2), native.slice(3, 1)],
            "empty_interleaved": [
                empty,
                native.slice(0, 1),
                empty,
                native.slice(1, 2),
                native.slice(3, 1),
                empty,
            ],
            "zero": [],
            "empty": [empty],
            "trailing_empty": [native, empty],
        }
        reader_cases = {
            name: interop_stream(
                binding, batches, 0 if name in ("zero", "empty") else 4, route="raw"
            )
            for name, batches in layouts.items()
        }
        reader_cases["short"] = interop_stream(
            binding, [native.slice(0, 3)], 4, route="raw"
        )
        reader_cases["extra"] = interop_stream(binding, [native], 3, route="raw")
        for state in ("null", "first_null"):
            reader_cases[state] = interop_stream(
                nullable,
                [native_finite(state=state)],
                2 if state == "null" else 5,
                route="raw",
            )
        results["ingress_reader"][target] = reader_cases
        provider = ProtocolBatch(native_finite())
        parity = dict(
            rows=ingress_batch_snapshot(
                ingress.ingest_rows(binding, finite_rows(target))
            ),
            batch=ingress_batch_snapshot(
                ingress.ingest_batch(binding, native_finite())
            ),
            reader=interop_stream(binding, [native_finite()], 4, route="raw"),
            array=ingress_batch_snapshot(i.import_batch(binding, provider)),
            stream=interop_stream(binding, [native_finite()], 4, route="protocol"),
            array_calls=provider.calls,
            row_carriers=[type(rows[0][j]).__name__ for j in (3, 9, 10, 7)],
            logical_bool=type(native.column(3)[0].as_py()).__name__,
        )
        results["ingress_parity"][target] = parity

        class Fake:
            def __init__(self):
                self.calls = 0

            def hook(self, *args, **kwargs):
                self.calls += 1
                raise AssertionError("implicit conversion invoked")

            to_arrow = __dataframe__ = to_batches = __arrow_c_array__ = (
                __arrow_c_stream__
            ) = hook
            __arrow_c_device_array__ = __arrow_c_device_stream__ = hook

        fake = Fake()
        wrong_routes = [
            refused(lambda: ingress.ingest_rows(binding, fake)),
            refused(lambda: ingress.ingest_batch(binding, fake)),
            refused(lambda: ingress.ingest_reader(binding, fake, expected_rows=0)),
            refused(
                lambda: ingress.ingest_batch(binding, pa.Table.from_batches([native]))
            ),
            refused(
                lambda: ingress.ingest_batch(
                    binding, pa.chunked_array([native.column(0)])
                )
            ),
            refused(lambda: ingress.ingest_batch(binding, b"IPC")),
            refused(lambda: ingress.ingest_batch(binding, 0)),
            refused(lambda: ingress.ingest_rows(binding, native)),
            refused(lambda: ingress.ingest_reader(binding, native, expected_rows=4)),
        ]
        schemas = []
        for position, field_ in (
            (12, native.schema[12].with_name("changed")),
            (12, native.schema[12].with_nullable(True)),
            (12, native.schema[12].with_metadata({b"wrong": b"metadata"})),
            (0, pa.field("repeated", pa.int32(), nullable=False)),
        ):
            fields = list(native.schema)
            fields[position] = field_
            columns = list(native.columns)
            if position == 0:
                columns[0] = pa.array([1, 0, 1, 1], type=pa.int32())
            schemas.append(
                pa.RecordBatch.from_arrays(columns, schema=pa.schema(fields))
            )
        schemas.append(native.replace_schema_metadata({b"wrong": b"metadata"}))
        schema_refusals = [
            refused(lambda batch=batch: ingress.ingest_batch(binding, batch))
            for batch in schemas
        ]
        foreign = replace(binding, integer_widths=finite_policy(np)["integer_widths"])
        corrupted = replace(
            binding,
            producer=replace(
                producer,
                contract=replace(neutral, scalar_meaning=np.contract.scalar_meaning),
            ),
        )
        authority = [
            refused(lambda b=b: ingress.ingest_rows(b, fake))
            for b in (None, foreign, corrupted)
        ]
        preaccept = []
        for mode in ("binding", "schema", "extent", "lease", "policy", "meaning"):
            with ReaderTrace(
                schemas[0].schema if mode == "schema" else binding.schema,
                [schemas[0] if mode == "schema" else native],
            ) as trace:
                b = (
                    None
                    if mode == "binding"
                    else foreign
                    if mode == "policy"
                    else corrupted
                    if mode == "meaning"
                    else binding
                )
                lease = (
                    i.BorrowLease(object(), binding, object(), True)
                    if mode == "lease"
                    else None
                )
                error = refused(
                    lambda lease=lease: ingress.ingest_reader(
                        b,
                        trace.source,
                        expected_rows=True if mode == "extent" else 4,
                        lease=lease,
                    )
                )
                before_counts = [trace.reads, trace.closes]
                caller_batch = trace.source.read_next_batch()
                trace.source.close()
                preaccept.append(
                    dict(
                        mode=mode,
                        error=error,
                        before=before_counts,
                        caller_rows=caller_batch.num_rows,
                    )
                )
        signature_errors = [
            protocol_error(lambda: cast(Any, ingress.ingest_reader)(binding, fake)),
            protocol_error(
                lambda: cast(Any, ingress.ingest_rows)(binding, rows, lease=None)
            ),
        ]
        results["ingress_refusals"][target] = dict(
            wrong_routes=wrong_routes,
            hook_calls=fake.calls,
            schema=schema_refusals,
            authority=authority,
            preaccept=preaccept,
            signatures=signature_errors,
        )

        source, owner = mutable_finite(native)
        managed = ingress.ingest_batch(binding, source)
        copied = pa.record_batch(managed)
        independent = all(
            x.address != y.address
            for c, d in zip(source.columns, copied.columns, strict=True)
            for x, y in zip(c.buffers(), d.buffers(), strict=True)
            if x is not None and y is not None and x.size
        )
        mutate_finite(owner)
        isolated = finite_snapshot(copied)
        managed.close()
        source, owner = mutable_finite(native)
        reference = weakref.ref(owner)
        lease = i.BorrowLease(source, binding, owner, True)
        borrowed = ingress.ingest_batch(binding, source, lease=lease)
        output = pa.record_batch(borrowed)
        shared = all(
            x.address == y.address
            for c, d in zip(source.columns, output.columns, strict=True)
            for x, y in zip(c.buffers(), d.buffers(), strict=True)
            if x is not None and y is not None
        )
        batch_lease = refused(
            lambda lease=lease: ingress.ingest_batch(binding, native, lease=lease)
        )
        borrowed.close()
        del borrowed, source, lease, owner
        gc.collect()
        batch_pinned = reference() is not None
        del output
        gc.collect()
        batch_released = reference() is None
        borrowed_source, owner = mutable_finite(native)
        with ReaderTrace(binding.schema, [borrowed_source]) as trace:
            owner_ref = weakref.ref(owner)
            lease = i.BorrowLease(trace.source, binding, owner, True)
            session = ingress.ingest_reader(
                binding, trace.source, expected_rows=4, lease=lease
            )
            assert session._lease is not None
            raw_identity = (
                session._lease[1] is trace.source and session._lease[0] is lease
            )
            foreign_reader = pa.RecordBatchReader.from_stream(session)
            output = foreign_reader.read_next_batch()
            sharing = all(
                x.address == y.address
                for c, d in zip(borrowed_source.columns, output.columns, strict=True)
                for x, y in zip(c.buffers(), d.buffers(), strict=True)
                if x is not None and y is not None
            )
            copied_session = copy(session)
            copy_error = refused(
                lambda copied_session=copied_session: pa.RecordBatchReader.from_stream(
                    copied_session
                )
            )
            copied_close = refused(copied_session.close)
            del copied_session
            competing = refused(session._reader.read_next_batch)
            second = refused(
                lambda session=session: pa.RecordBatchReader.from_stream(session)
            )
            foreign_reader.close()
            session.close()
            session.close()
            after = [session.state, session._reader.state, trace.reads, trace.closes]
            del foreign_reader, session, lease, owner
            gc.collect()
            reader_pinned = owner_ref() is not None
            del output
            gc.collect()
            reader_released = owner_ref() is None
        wrapping = []
        original_initialize = i.ManagedStream._initialize

        def fail_initialize(*args):
            raise RuntimeError("injected post-acceptance initialization")

        for cleanup in (None, RuntimeError("injected accepted close")):
            with ReaderTrace(binding.schema, [native], close_error=cleanup) as trace:
                try:
                    setattr(i.ManagedStream, "_initialize", fail_initialize)
                    try:
                        ingress.ingest_reader(binding, trace.source, expected_rows=4)
                    except BaseException as exc:
                        wrapping.append(
                            dict(
                                error=type(exc).__name__,
                                errors=[type(e).__name__ for e in exc.exceptions]
                                if isinstance(exc, BaseExceptionGroup)
                                else [],
                                reads=trace.reads,
                                closes=trace.closes,
                            )
                        )
                    else:
                        raise AssertionError("composition injection ignored")
                finally:
                    i.ManagedStream._initialize = original_initialize
        late = interop_stream(binding, [native], 4, route="raw", late=True)
        early = interop_stream(binding, [native], 4, route="raw", early=True)
        cleanup = interop_stream(
            binding,
            [native],
            4,
            route="raw",
            close_error=RuntimeError("injected source cleanup"),
        )
        old_close = i._close_bridge

        def fail_close(bridge):
            old_close(bridge)
            raise RuntimeError("injected delivery cleanup")

        try:
            i._close_bridge = fail_close
            downstream = interop_stream(binding, [native], 4, route="raw")
        finally:
            i._close_bridge = old_close

        def fail_copy(*args):
            raise StopIteration("not source EOF")

        try:
            i._copy_batch = fail_copy
            not_eof = interop_stream(binding, [native], 4, route="raw")
        finally:
            i._copy_batch = old_copy
        results["ingress_ownership"][target] = dict(
            independent=independent,
            isolated=isolated,
            batch_shared=shared,
            batch_lease=batch_lease,
            batch_pinned=batch_pinned,
            batch_released=batch_released,
            raw_lease_identity=raw_identity,
            reader_shared=sharing,
            reader_pinned=reader_pinned,
            reader_released=reader_released,
            copy=copy_error,
            copied_close=copied_close,
            competing=competing,
            second=second,
            early_state=after,
            wrapping=wrapping,
            early=early,
            late=late,
            cleanup=cleanup,
            downstream=downstream,
            not_eof=not_eof,
        )

        # Direct-reader ownership must be observed at this new acceptance seam.
        source, owner = mutable_finite(native)
        with ReaderTrace(binding.schema, [source]) as trace:
            session = ingress.ingest_reader(binding, trace.source, expected_rows=4)
            consumer = pa.RecordBatchReader.from_stream(session)
            output = consumer.read_next_batch()
            mutate_finite(owner)
            raw_isolated = finite_snapshot(output)
            consumer.close()
            session.close()
            raw_isolation_counts = [trace.reads, trace.closes]
        with ReaderTrace(binding.schema, [native]) as trace:
            lease = i.BorrowLease(trace.source, binding, InteropOwner(), True)
            session = ingress.ingest_reader(
                binding, trace.source, expected_rows=4, lease=lease
            )
            consumer = pa.RecordBatchReader.from_stream(session)
            object.__setattr__(lease, "non_mutation", False)
            lease_abi = protocol_error(consumer.read_next_batch)
            lease_primary = session.primary_error
            assert isinstance(lease_primary, a.ResultError)
            consumer.close()
            session.close()
            raw_lease_change = dict(
                error=lease_primary.category,
                foreign=lease_abi,
                reads=trace.reads,
                closes=trace.closes,
            )
        original_claim = r.CheckedFiniteReader._claim

        def claim_failure(self):
            raise RuntimeError("injected accepted claim failure")

        with ReaderTrace(binding.schema, [native]) as trace:
            try:
                setattr(r.CheckedFiniteReader, "_claim", claim_failure)
                claim_error = protocol_error(
                    lambda: ingress.ingest_reader(
                        binding, trace.source, expected_rows=4
                    )
                )
            finally:
                setattr(r.CheckedFiniteReader, "_claim", original_claim)
            claim_counts = [trace.reads, trace.closes]
        control = KeyboardInterrupt("injected source close control")
        with ReaderTrace(binding.schema, [native], close_error=control) as trace:
            session = ingress.ingest_reader(binding, trace.source, expected_rows=4)
            consumer = pa.RecordBatchReader.from_stream(session)
            foreign_control = None
            try:
                with session:
                    try:
                        list(consumer)
                    except Exception as exc:
                        foreign_control = type(exc).__name__
                        raise
            except KeyboardInterrupt as exc:
                original_control = exc is control
            else:
                raise AssertionError("original control lost across ABI")
            consumer.close()
            control_result = dict(
                original=original_control,
                foreign=foreign_control,
                state=session.state,
                complete=session.input_completion is not None,
                closes=trace.closes,
            )
        results["ingress_ownership"][target].update(
            raw_isolated=raw_isolated,
            raw_isolation_counts=raw_isolation_counts,
            raw_lease_change=raw_lease_change,
            claim_error=claim_error,
            claim_counts=claim_counts,
            control=control_result,
        )

        class DeviceOnly:
            def __init__(self):
                self.calls = 0

            def hook(self, *args, **kwargs):
                self.calls += 1
                raise AssertionError("device fallback invoked")

            __arrow_c_device_array__ = __arrow_c_device_stream__ = hook

        device = DeviceOnly()
        results["ingress_refusals"][target]["device"] = dict(
            errors=[
                refused(lambda: ingress.ingest_rows(binding, device)),
                refused(lambda: ingress.ingest_batch(binding, device)),
                refused(
                    lambda: ingress.ingest_reader(binding, device, expected_rows=0)
                ),
            ],
            calls=device.calls,
        )

        resource = {}
        for state in INGRESS_STATES:
            chosen = nullable if state in ("null", "first_null") else binding
            cap = max(INGRESS_USAGES[state])
            resource[state] = dict(
                rows=ingress_batch_snapshot(
                    ingress.ingest_rows(
                        chosen,
                        finite_rows(target, state=state),
                        limits=a.BatchLimits(bytes=cap),
                    )
                ),
                batch=ingress_batch_snapshot(
                    ingress.ingest_batch(
                        chosen,
                        native_finite(state=state),
                        limits=a.BatchLimits(bytes=cap),
                    )
                ),
                under=[
                    refused(
                        lambda: ingress.ingest_rows(
                            chosen,
                            finite_rows(target, state=state),
                            limits=a.BatchLimits(bytes=cap - 1),
                        )
                    ),
                    refused(
                        lambda: ingress.ingest_batch(
                            chosen,
                            native_finite(state=state),
                            limits=a.BatchLimits(bytes=cap - 1),
                        )
                    ),
                ],
            )
        resource["slice"] = ingress_batch_snapshot(
            ingress.ingest_batch(
                binding, native.slice(0, 1), limits=a.BatchLimits(bytes=528)
            )
        )
        resource["one_row"] = ingress_batch_snapshot(
            ingress.ingest_rows(binding, rows[:1], limits=a.BatchLimits(bytes=175))
        )
        resource["slice_under"] = refused(
            lambda: ingress.ingest_batch(
                binding, native.slice(0, 1), limits=a.BatchLimits(bytes=527)
            )
        )
        try:
            i._copy_batch = forbidden
            resource["retained_first"] = refused(
                lambda: ingress.ingest_batch(
                    binding,
                    invalid["float"].slice(0, 1),
                    limits=a.BatchLimits(bytes=527),
                )
            )
        finally:
            i._copy_batch = old_copy

        def padded(value, lease):
            copied = old_copy(value, lease)
            columns = list(copied.columns)
            col = columns[0]
            validity, data = col.buffers()
            columns[0] = pa.Array.from_buffers(
                col.type,
                len(col),
                [validity, pa.py_buffer(bytes(memoryview(data)) + bytes(128))],
                offset=col.offset,
                null_count=-1,
            )
            return pa.RecordBatch.from_arrays(columns, schema=copied.schema)

        try:
            i._copy_batch = padded
            resource["delivery_under"] = interop_stream(
                binding,
                [native, native],
                8,
                route="raw",
                limits=r.FiniteReaderLimits(max_total_bytes=1311),
            )
            resource["delivery_exact"] = interop_stream(
                binding,
                [native, native],
                8,
                route="raw",
                limits=r.FiniteReaderLimits(max_total_bytes=1312),
            )
        finally:
            i._copy_batch = old_copy
        resource["empty_cap"] = interop_stream(
            binding,
            itertools.repeat(empty),
            0,
            route="raw",
            limits=r.FiniteReaderLimits(max_batches=2),
        )
        results["ingress_resources"][target] = resource

        try:
            i._copy_batch = forbidden
            resource["raw_retained_first"] = interop_stream(
                binding,
                [invalid["float"].slice(0, 1)],
                1,
                route="raw",
                limits=r.FiniteReaderLimits(max_total_bytes=527),
            )
        finally:
            i._copy_batch = old_copy

        # All five paths really call the shared checker; no unchecked route or fabricated usage.
        original_checker = a._checked_batch_usage
        reached = []
        for route in ("rows", "batch", "raw", "array", "protocol"):
            calls = []

            def reject_checked(*args, **kwargs):
                calls.append("actual batch checker")
                raise a.ResultError("VALUE_DOMAIN")

            try:
                a._checked_batch_usage = reject_checked
                if route == "rows":
                    error = refused(lambda: ingress.ingest_rows(binding, rows))
                elif route == "batch":
                    error = refused(lambda: ingress.ingest_batch(binding, native))
                elif route == "array":
                    error = refused(
                        lambda: i.import_batch(binding, ProtocolBatch(native))
                    )
                else:
                    error = interop_stream(binding, [native], 4, route=route)["error"]
                reached.append(dict(route=route, error=error, calls=len(calls)))
            finally:
                a._checked_batch_usage = original_checker
        altered = {}
        wrong = [list(row) for row in rows]
        wrong[0][4] = float("nan")
        altered["rows"] = refused(lambda: ingress.ingest_rows(binding, wrong))
        altered["batch"] = refused(
            lambda: ingress.ingest_batch(binding, invalid["float"])
        )
        altered["array"] = refused(
            lambda: i.import_batch(binding, ProtocolBatch(invalid["float"]))
        )
        for route in ("raw", "protocol"):
            observed = interop_stream(binding, [invalid["float"]], 4, route=route)
            altered[route] = dict(
                error=observed["error"],
                complete=observed["source_complete"],
                delivered=observed["chunks"],
            )
        columns = list(native.columns)
        columns[0], columns[12] = columns[12], columns[0]
        swapped = pa.RecordBatch.from_arrays(columns, schema=native.schema)
        columns = list(native.columns)
        columns[12] = pa.array([-8, 9, -7, -7], type=pa.int16())
        substituted = pa.RecordBatch.from_arrays(columns, schema=native.schema)
        substitutions = []
        for name, batch in (
            ("swap", swapped),
            ("non_first", substituted),
            ("lost_duplicate", native.slice(0, 3)),
        ):
            observed = interop_stream(binding, [batch], batch.num_rows, route="raw")
            error = protocol_error(lambda: ingress_value_oracle(observed["rows"]))
            substitutions.append(
                dict(
                    kind=name,
                    rows=observed["rows"],
                    source_complete=observed["source_complete"],
                    oracle=error,
                )
            )

        def changed_copy(value, lease):
            copied = old_copy(value, lease)
            columns = list(copied.columns)
            columns[0], columns[12] = columns[12], columns[0]
            return pa.RecordBatch.from_arrays(columns, schema=copied.schema)

        try:
            i._copy_batch = changed_copy
            changed = interop_stream(binding, [native], 4, route="raw")
        finally:
            i._copy_batch = old_copy
        results["ingress_independence"][target] = dict(
            altered=altered,
            checker=reached,
            substitutions=substitutions,
            injected=dict(
                rows=changed["rows"],
                source_complete=changed["source_complete"],
                oracle=protocol_error(lambda: ingress_value_oracle(changed["rows"])),
            ),
            neutral_unchanged=export_result_contract(neutral, checked).canonical_bytes
            == before,
        )
    return results


def verify_ingress_report(cases):
    try:
        if any(set(cases[name]) != {"postgres", "mysql"} for name in INGRESS_GROUPS):
            raise ValueError("ingress denominator")
        rows = finite_expected()["rows"]
        whole = READER_LAYOUTS["whole"]
        failures = []
        for target in ("postgres", "mysql"):

            def require(name, expected):
                if not _exact(cases[name][target], expected):
                    failures.append(
                        "ingress observed "
                        + name
                        + ": "
                        + json.dumps(
                            {"actual": cases[name][target], "expected": expected},
                            sort_keys=True,
                        )
                    )

            row_cases: dict[str, Any] = {
                state: ingress_batch_expected(state) for state in INGRESS_STATES
            }
            row_cases.update(
                refusals=["ROWS", "ROWS", "ROW_ARITY", "ROW_ARITY"]
                + ["VALUE_DOMAIN"] * 4,
                redundant=ingress_batch_expected(),
            )
            require("ingress_rows", row_cases)
            batch_cases: dict[str, Any] = {
                state: ingress_batch_expected(state) for state in INGRESS_STATES
            }
            sliced = ingress_batch_expected()
            sliced.update(
                snapshot=interop_snapshot_slice(1, 3),
                source_usage=[330, 528],
                usage=[330, 528],
            )
            batch_cases.update(
                sliced=sliced,
                offsets=[1] * 13,
                absent=ingress_batch_expected("empty"),
                original_refusals=dict(
                    float="VALUE_DOMAIN",
                    utf8="ARROW_BATCH",
                    precision="ARROW_BATCH",
                    timestamp="VALUE_DOMAIN",
                    null="NULL",
                ),
            )
            require("ingress_batch", batch_cases)
            reader_cases = {
                name: ingress_stream_expected(usages, rows)
                for name, usages in READER_LAYOUTS.items()
            }
            reader_cases.update(
                zero=ingress_stream_expected((), []),
                empty=ingress_stream_expected(((0, 12, 12),), []),
                trailing_empty=ingress_stream_expected((*whole, (0, 12, 12)), rows),
                short=ingress_stream_expected(
                    ((3, 480, 528),), rows[:3], failure="READER_EXTENT"
                ),
                extra=ingress_stream_expected(
                    (), [], failure="READER_EXTENT", counts=[4]
                ),
            )
            for state in ("null", "first_null"):
                count = 2 if state == "null" else 5
                reader_cases[state] = ingress_stream_expected(
                    ((count, *INGRESS_USAGES[state]),),
                    finite_expected(state=state)["rows"],
                    nullable=True,
                )
            require("ingress_reader", reader_cases)
            require(
                "ingress_parity",
                dict(
                    rows=ingress_batch_expected(),
                    batch=ingress_batch_expected(),
                    reader=ingress_stream_expected(whole, rows),
                    array=ingress_batch_expected(),
                    stream=ingress_stream_expected(whole, rows, route="protocol"),
                    array_calls=1,
                    row_carriers=[
                        "bool" if target == "postgres" else "int",
                        "datetime",
                        "UUID" if target == "postgres" else "bytes",
                        "Decimal",
                    ],
                    logical_bool="bool",
                ),
            )
            require(
                "ingress_refusals",
                dict(
                    wrong_routes=[
                        "ROWS",
                        "ARROW_BATCH",
                        "READER_SOURCE",
                        "ARROW_BATCH",
                        "ARROW_BATCH",
                        "ARROW_BATCH",
                        "ARROW_BATCH",
                        "ROWS",
                        "READER_SOURCE",
                    ],
                    hook_calls=0,
                    schema=["ARROW_SCHEMA"] * 5,
                    authority=["ARROW_BINDING", "ARROW_ADAPTATION", "MEANING_ROOT"],
                    preaccept=[
                        dict(mode=mode, error=error, before=[0, 0], caller_rows=4)
                        for mode, error in zip(
                            (
                                "binding",
                                "schema",
                                "extent",
                                "lease",
                                "policy",
                                "meaning",
                            ),
                            (
                                "ARROW_BINDING",
                                "ARROW_SCHEMA",
                                "READER_DECLARATION",
                                "INTEROP_LEASE",
                                "ARROW_ADAPTATION",
                                "MEANING_ROOT",
                            ),
                            strict=True,
                        )
                    ],
                    signatures=["TypeError"] * 2,
                    device=dict(
                        errors=["ROWS", "ARROW_BATCH", "READER_SOURCE"], calls=0
                    ),
                ),
            )
            downstream = ingress_stream_expected(whole, rows)
            downstream.update(after=["FAILED", "COMPLETE"], error="INTEROP_CLEANUP")
            not_eof = ingress_stream_expected(
                (),
                [],
                failure="StopIteration",
                counts=[4],
                input_state="CLOSED_INCOMPLETE",
            )
            not_eof.update(source_rows=4, reads=1)
            require(
                "ingress_ownership",
                dict(
                    raw_isolated=protocol_expected(),
                    raw_isolation_counts=[1, 1],
                    raw_lease_change=dict(
                        error="INTEROP_LEASE", foreign="ArrowInvalid", reads=0, closes=1
                    ),
                    claim_error="RuntimeError",
                    claim_counts=[0, 1],
                    control=dict(
                        original=True,
                        foreign="ArrowInvalid",
                        state="FAILED",
                        complete=False,
                        closes=1,
                    ),
                    independent=True,
                    isolated=protocol_expected(),
                    batch_shared=True,
                    batch_lease="INTEROP_LEASE",
                    batch_pinned=True,
                    batch_released=True,
                    raw_lease_identity=True,
                    reader_shared=True,
                    reader_pinned=True,
                    reader_released=True,
                    copy="INTEROP_BINDING",
                    copied_close="INTEROP_BINDING",
                    competing="READER_CLAIMED",
                    second="INTEROP_SPENT",
                    early_state=["CLOSED_INCOMPLETE", "CLOSED_INCOMPLETE", 1, 1],
                    wrapping=[
                        dict(error="RuntimeError", errors=[], reads=0, closes=1),
                        dict(
                            error="ExceptionGroup",
                            errors=["RuntimeError", "ResultError"],
                            reads=0,
                            closes=1,
                        ),
                    ],
                    early=ingress_stream_expected(whole, rows, early=True),
                    late=ingress_stream_expected(whole, rows, failure="READER_SOURCE"),
                    cleanup=ingress_stream_expected(
                        whole, rows, failure="READER_CLEANUP"
                    ),
                    downstream=downstream,
                    not_eof=not_eof,
                ),
            )
            resource: dict[str, Any] = {
                state: dict(
                    rows=ingress_batch_expected(state),
                    batch=ingress_batch_expected(state),
                    under=["LIMIT"] * 2,
                )
                for state in INGRESS_STATES
            }
            sliced = ingress_batch_expected()
            sliced.update(
                snapshot=interop_snapshot_slice(0, 1),
                source_usage=[175, 528],
                usage=[175, 528],
            )
            one = ingress_batch_expected()
            one.update(
                snapshot=protocol_expected(state="one"),
                source_usage=[175, 139],
                usage=[175, 139],
            )
            under = ingress_stream_expected(
                whole,
                rows,
                failure="LIMIT",
                counts=[4, 4],
                input_state="CLOSED_INCOMPLETE",
            )
            under.update(
                charge=656, descriptors=[[4, 630, 528, 630, 656, 1184]], source_rows=8
            )
            exact = ingress_stream_expected((*whole, *whole), rows + rows)
            exact.update(charge=1312, descriptors=[[4, 630, 528, 630, 656, 1184]] * 2)
            resource.update(
                slice=sliced,
                one_row=one,
                slice_under="LIMIT",
                retained_first="LIMIT",
                raw_retained_first=ingress_stream_expected(
                    (), [], failure="LIMIT", counts=[1]
                ),
                delivery_under=under,
                delivery_exact=exact,
                empty_cap=ingress_stream_expected(
                    ((0, 12, 12), (0, 12, 12)), [], failure="LIMIT", counts=[0, 0, 0]
                ),
            )
            require("ingress_resources", resource)
            swapped = json.loads(json.dumps(rows))
            for row in swapped:
                row[0], row[12] = row[12], row[0]
            substitute = json.loads(json.dumps(rows))
            substitute[0][12] = -8
            require(
                "ingress_independence",
                dict(
                    altered=dict(
                        rows="VALUE_DOMAIN",
                        batch="VALUE_DOMAIN",
                        array="VALUE_DOMAIN",
                        raw=dict(error="VALUE_DOMAIN", complete=False, delivered=[]),
                        protocol=dict(
                            error="VALUE_DOMAIN", complete=False, delivered=[]
                        ),
                    ),
                    checker=[
                        dict(route=route, error="VALUE_DOMAIN", calls=1)
                        for route in ("rows", "batch", "raw", "array", "protocol")
                    ],
                    substitutions=[
                        dict(
                            kind=name,
                            rows=value,
                            source_complete=True,
                            oracle="ValueError",
                        )
                        for name, value in (
                            ("swap", swapped),
                            ("non_first", substitute),
                            ("lost_duplicate", rows[:3]),
                        )
                    ],
                    injected=dict(
                        rows=swapped, source_complete=True, oracle="ValueError"
                    ),
                    neutral_unchanged=True,
                ),
            )
        if failures:
            raise ValueError("\n".join(failures))
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("ingress observations") from exc


def descriptor_sources(imported=False):
    types = """type Money = Decimal(12, 2)
type Label = Text:
    ensure self != "café é"
"""
    body = """shape Row:
    id: Int not null
    label: Label nullable
    amount: Money nullable
    second: Money not null
source rows: Row is postgres.table("rows")
table result:
    from rows
    select:
        id
        label
        amount
        second
    order by:
        id desc
"""
    if imported:
        body = body.replace("        id desc\n", "        id + 0 desc\n")
        return {
            "types.pietto": types + "export:\n    type Money\n    type Label\n",
            "main.pietto": 'import "types.pietto":\n    type Money\n    type Label\n'
            + body,
        }
    return {"main.pietto": types + body}


def contract_fixture(root, name):
    from pietto._project.project_result_contract import build_result_contract

    sources = (
        {"main.pietto": source(name)}
        if name in ("postgres", "mysql")
        else descriptor_sources(name == "imported")
    )
    checked = build_neutral(root / name, sources)
    return checked, build_result_contract(checked)


def contract_documents(root):
    from pietto._project.project_result_contract_portable import export_result_contract
    from pietto._project.project_result_contract_correspondence import (
        verify_bound_export,
    )

    result = {}
    for name in CONTRACT_CORPUS:
        checked, contract = contract_fixture(root, name)
        exported = export_result_contract(contract, checked)
        verify_bound_export(exported, checked)
        result[name] = exported.canonical_bytes.decode("utf-8")
    return result


def check_document_oracle(name, data):
    """Independent expected-field enumeration, not an exporter round-trip oracle."""
    from pietto._project import project_result_contract_pure_boundary as pure

    view = pure.decode_contract(data.encode("utf-8"))
    doc = view.document
    assert doc["owner"]["identity"] == {
        "module": "main.pietto",
        "namespace": "relation",
        "kind": "table",
        "name": "result",
    }
    assert doc["multiplicity"] == "bag"
    fields = doc["fields"]
    simple = name in ("postgres", "mysql")
    assert doc["field_count"] == (2 if simple else 4)
    assert [f["label"] for f in fields] == (
        ["renamed", "other"] if simple else ["id", "label", "amount", "second"]
    )
    assert [f["ordinal"] for f in fields] == list(range(len(fields)))
    assert [f["canonical"]["name"] for f in fields] == (
        ["Int", "Int"] if simple else ["Int", "Text", "Decimal", "Decimal"]
    )
    assert [f["nullability"] for f in fields] == (
        ["non_null", "nullable"]
        if simple
        else ["non_null", "nullable", "nullable", "non_null"]
    )
    assert all(f["provenance"]["kind"] == "direct_projection" for f in fields)
    assert all(f["provenance"]["symbol"]["identity"]["name"] == "rows" for f in fields)
    if simple:
        assert doc["ordering"] is None and doc["types"] == []
        assert [f["declared"]["name"] for f in fields] == ["Int", "Int"]
    else:
        assert doc["ordering"]["keys"][0]["direction"] == "desc"
        key = doc["ordering"]["keys"][0]
        assert key["expression"]["tag"] == ("binary" if name == "imported" else "name")
        assert key["prepared"]["value_type"]["name"] == "Int"
        assert len(key["prepared"]["uses"]) == 1
        assert key["prepared"]["uses"][0]["expression"]["name"] == "id"
        assert key["prepared"]["uses"][0]["value_type"]["nullability"] == "non_null"
        assert [t["owner"]["identity"]["name"] for t in doc["types"]] == [
            "Label",
            "Money",
        ]
        assert [a["value"]["value"] for a in doc["types"][1]["base"]["arguments"]] == [
            "12",
            "2",
        ]
        assert doc["types"][0]["ensures"][0]["right"]["value"] == "café é"
        assert (
            fields[2]["type_resolution"]["aliases"]
            == fields[3]["type_resolution"]["aliases"]
        )
        if name == "imported":
            assert all(
                t["owner"]["identity"]["module"] == "types.pietto" for t in doc["types"]
            )
            assert (
                fields[2]["type_resolution"]["origins"][0]["paths"][0]["hops"][0][
                    "origin"
                ]["import"]["target_module"]
                == "types.pietto"
            )
    assert pure.reencode_contract(view) == data.encode("utf-8")
    return view


def coherent_tail(view):
    from pietto._project import project_result_contract_pure_boundary as pure

    doc = view.document
    doc["fields"].pop()
    doc["field_count"] -= 1
    doc["output"]["field_count"] -= 1
    for field in doc["fields"]:
        field["output"]["field_count"] -= 1
    return pure.decode_contract(pure.encode_document(doc))


def pure_child(documents):
    child = r"""
import importlib.abc, json, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        allowed = {"pietto", "pietto._project", "pietto._project.project_result_contract_pure_boundary"}
        if fullname == "pyarrow" or fullname.startswith("pyarrow.") or (fullname.startswith("pietto.") and fullname not in allowed):
            raise AssertionError("runtime dependency: " + fullname)
sys.meta_path.insert(0, Block())
from pietto._project.project_result_contract_pure_boundary import decode_contract, reencode_contract
values=json.loads(sys.stdin.read())
result={}
for name, text in values.items():
    view=decode_contract(text.encode("utf-8"))
    assert reencode_contract(view)==text.encode("utf-8")
    owned=view.fields
    owned[0]["label"]="changed"
    assert view.fields[0]["label"]!="changed"
    result[name]=[f["label"] for f in view.fields]
print(json.dumps(result,sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", child],
        input=json.dumps(documents),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


MALFORMED_EXPECTED = {
    "utf8": "UTF8",
    "escape": "TEXT",
    "duplicate_key": "DUPLICATE_KEY",
    "float_number": "NUMBER",
    "nonfinite": "NUMBER",
    "negative_zero": "NUMBER",
    "truncation": "JSON",
    "trailing": "JSON",
    "noncanonical": "CANONICAL",
    "unknown_version": "VERSION",
    "extra_key": "DOCUMENT",
    "missing_key": "DOCUMENT",
    "unknown_kind": "TAG",
    "container_tag": "DOCUMENT",
    "bool_ordinal": "INDEX",
    "field_omission": "DOCUMENT",
    "field_duplicate": "INDEX",
    "field_reorder": "INDEX",
    "dangling_ref": "REFERENCE",
    "wrong_kind_ref": "REFERENCE",
    "alias_cycle": "REFERENCE",
    "provenance_cycle": "REFERENCE",
    "foreign_output": "REFERENCE",
    "invalid_int_tag": "NUMBER",
    "depth_limit": "LIMIT",
    "record_limit": "LIMIT",
    "value_limit": "LIMIT",
}


def malformed_contract_cases(documents):
    from pietto._project import project_result_contract_pure_boundary as pure

    base = documents["postgres"].encode("utf-8")
    raw = {
        "utf8": b"\xff",
        "escape": b'{"x":"\\ud800"}',
        "duplicate_key": b'{"x":1,"x":2}',
        "float_number": b'{"x":1.0}',
        "nonfinite": b'{"x":Infinity}',
        "negative_zero": b'{"x":-0}',
        "truncation": base[:-2],
        "trailing": base + b"{}",
        "noncanonical": b" " + base,
    }
    mutations = {
        "unknown_version": lambda d: d.update(format="foreign.v1"),
        "extra_key": lambda d: d.update(extra=None),
        "missing_key": lambda d: d.pop("multiplicity"),
        "unknown_kind": lambda d: d["fields"][0]["canonical"].update(kind="nested"),
        "container_tag": lambda d: d["fields"][0]["canonical"].update(kind=[]),
        "bool_ordinal": lambda d: d["fields"][0].update(ordinal=False),
        "field_omission": lambda d: d["fields"].pop(),
        "field_duplicate": lambda d: d["fields"].__setitem__(1, d["fields"][0]),
        "field_reorder": lambda d: d["fields"].reverse(),
        "dangling_ref": lambda d: d["fields"][2]["type_resolution"]["aliases"][
            0
        ].update(index=99),
        "wrong_kind_ref": lambda d: d["fields"][2]["type_resolution"]["aliases"][
            0
        ].update(kind="field"),
        "alias_cycle": lambda d: d["fields"][2]["type_resolution"]["aliases"].append(
            d["fields"][2]["type_resolution"]["aliases"][0]
        ),
        "provenance_cycle": lambda d: d["fields"][2]["type_resolution"]["origins"][0][
            "paths"
        ][0]["hops"].append(
            d["fields"][2]["type_resolution"]["origins"][0]["paths"][0]["hops"][0]
        ),
        "foreign_output": lambda d: d["fields"][0]["output"].update(position=99),
        "invalid_int_tag": lambda d: d["types"][1]["base"]["arguments"][0][
            "value"
        ].update(value="01"),
    }
    for name, mutate in mutations.items():
        doc = json.loads(documents["descriptors"])
        mutate(doc)
        raw[name] = (
            json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
    cases = {name: (data, pure.DocumentLimits()) for name, data in raw.items()}
    cases.update(
        depth_limit=(b"[" * 49 + b"]" * 49, pure.DocumentLimits()),
        record_limit=(base, pure.DocumentLimits(records=1)),
        value_limit=(base, pure.DocumentLimits(values=1)),
    )
    outcomes = {}
    for name, (data, limits) in cases.items():
        try:
            pure.decode_contract(data, limits=limits)
        except pure.ContractDocumentError as exc:
            outcomes[name] = exc.category
        else:
            raise AssertionError("malformed document accepted: " + name)
    assert outcomes == MALFORMED_EXPECTED
    return outcomes


def run_contract_cases(root, built):
    from unittest.mock import patch
    from pietto._project import project_result_contract as c
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_correspondence as runtime
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project import project_result_binding as binding
    from pietto._project import project_arrow_result as arrow

    documents = {}
    contracts = {}
    for name in CONTRACT_CORPUS:
        if name in built:
            checked, _, contract, _, _ = built[name]
        else:
            checked, contract = contract_fixture(root, name)
        contracts[name] = checked, contract
        exported = writer.export_result_contract(contract, checked)
        runtime.verify_bound_export(exported, checked)
        documents[name] = exported.canonical_bytes.decode("utf-8")
        check_document_oracle(name, documents[name])
        assert (
            writer.export_result_contract(contract, checked).canonical_bytes
            == exported.canonical_bytes
        )
    checked, artifact, contract, producer, original_arrow = built["postgres"]
    exported = writer.export_result_contract(contract, checked)
    smaller = coherent_tail(exported.view)
    changed = exported.view.document
    changed["fields"][0]["nullability"] = "unknown"
    changed = pure.decode_contract(pure.encode_document(changed))
    substitutions = [
        refused(
            lambda v=v: runtime.verify_contract_correspondence(v, contract, checked)
        )
        for v in (smaller, changed)
    ]
    (root / "relocation").mkdir()
    foreign_checked, foreign_contract = contract_fixture(
        root / "relocation", "postgres"
    )
    assert (
        writer.export_result_contract(foreign_contract, foreign_checked).canonical_bytes
        == exported.canonical_bytes
    )
    runtime.verify_contract_correspondence(
        exported.view, foreign_contract, foreign_checked
    )
    identity = [
        refused(lambda: runtime.verify_bound_export(exported, foreign_checked)),
        refused(
            lambda: runtime.verify_contract_correspondence(
                exported.view, contract, foreign_checked
            )
        ),
    ]
    for impostor in (exported.view, exported.view.document, exported.canonical_bytes):
        identity.extend(
            (
                refused(
                    lambda v=impostor: binding.bind_producer(
                        v, artifact, observations("postgres")
                    )
                ),
                refused(lambda v=impostor: arrow.bind_arrow(cast(Any, v))),
                refused(lambda v=impostor: arrow.build_owned_batch(cast(Any, v), [])),
            )
        )
    damaged = replace(
        contract,
        shape=c.ResultShape(
            (
                replace(contract.shape.fields[0], label="changed"),
                contract.shape.fields[1],
            )
        ),
    )
    coordinated = exported.view.document
    coordinated["fields"][0]["label"] = coordinated["fields"][0]["identity"]["name"] = (
        "changed"
    )
    coordinated = pure.decode_contract(pure.encode_document(coordinated))
    identity.append(
        refused(
            lambda: runtime.verify_contract_correspondence(
                coordinated, damaged, checked
            )
        )
    )
    with (
        patch.object(
            writer,
            "export_result_contract",
            side_effect=AssertionError("exporter called"),
        ),
        patch.object(
            writer._Projection,
            "document",
            side_effect=AssertionError("projection called"),
        ),
    ):
        runtime.verify_contract_correspondence(exported.view, contract, checked)
        independent = refused(
            lambda: runtime.verify_contract_correspondence(smaller, contract, checked)
        )
    with patch.object(writer._Projection, "document", return_value=smaller.document):
        defective = writer.export_result_contract(contract, checked)
    injected = refused(lambda: runtime.verify_bound_export(defective, checked))
    # Only new reads are blocked; legitimate retained upstream verification stays real.
    with (
        patch(
            "pietto._project.check.check_project_parse_only",
            side_effect=AssertionError("parse"),
        ),
        patch(
            "pietto._project.project_sql_plan.build_project_sql_plan",
            side_effect=AssertionError("build"),
        ),
        patch(
            "pietto._project.project_sql_emission.emit_project_sql",
            side_effect=AssertionError("emit"),
        ),
    ):
        runtime.verify_bound_export(
            writer.export_result_contract(contract, checked), checked
        )
        arrow.verify_batch(
            arrow.build_owned_batch(original_arrow, [[BIG, None]]),
            original_arrow,
            producer,
        )
    order_checked, order_contract = contracts["imported"]
    order_doc = json.loads(documents["imported"])
    order_doc["ordering"]["keys"][0].update(authored_direction="asc", direction="asc")
    order_view = pure.decode_contract(pure.encode_document(order_doc))
    order_substitution = {
        "document": order_view.canonical_bytes.decode("utf-8"),
        "refusal": refused(
            lambda: runtime.verify_contract_correspondence(
                order_view, order_contract, order_checked
            )
        ),
    }
    original_leaf = contract.shape.fields[0]
    grafts = {}
    for part in ("owner", "output", "port", "canonical", "declared", "provenance"):
        if part in ("owner", "output"):
            bad = replace(contract, **{part: copy(getattr(contract, part))})
        else:
            if part in ("canonical", "declared"):
                leaf = replace(
                    original_leaf,
                    shape=replace(
                        original_leaf.shape,
                        **{part: copy(getattr(original_leaf.shape, part))},
                    ),
                )
            else:
                leaf = replace(
                    original_leaf, **{part: copy(getattr(original_leaf, part))}
                )
            bad = replace(
                contract, shape=c.ResultShape((leaf, *contract.shape.fields[1:]))
            )
        grafts[part] = [
            refused(lambda bad=bad: writer.export_result_contract(bad, checked)),
            refused(
                lambda bad=bad: runtime.verify_contract_correspondence(
                    exported.view, bad, checked
                )
            ),
        ]
    saved_label = original_leaf.label
    try:
        object.__setattr__(original_leaf, "label", "changed")
        pure.decode_contract(exported.canonical_bytes)
        grafts["damaged_live"] = [
            refused(lambda: runtime.verify_bound_export(exported, checked)),
            refused(lambda: arrow.build_owned_batch(original_arrow, [[0, None]])),
        ]
    finally:
        object.__setattr__(original_leaf, "label", saved_label)
    runtime.verify_bound_export(exported, checked)
    malformed = malformed_contract_cases(documents)
    limits = [
        refused(
            lambda lim=lim: writer.export_result_contract(contract, checked, limits=lim)
        )
        for lim in (
            pure.DocumentLimits(bytes=1),
            pure.DocumentLimits(fields=1),
            pure.DocumentLimits(depth=2),
            pure.DocumentLimits(values=1),
            pure.DocumentLimits(records=1),
            pure.DocumentLimits(text=1),
            pure.DocumentLimits(total_text=1),
            pure.DocumentLimits(references=0),
        )
    ]
    labels = pure_child(documents)
    for seed in CONTRACT_SEEDS:
        command = [
            sys.executable,
            "-I",
            str(Path(__file__).resolve()),
            "--contract-child",
        ]
        child = subprocess.run(
            command,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
            capture_output=True,
            check=True,
        )
        assert json.loads(child.stdout) == documents
    return {
        "contract_documents": documents,
        "contract_substitutions": {
            "tail": smaller.canonical_bytes.decode("utf-8"),
            "nullability": changed.canonical_bytes.decode("utf-8"),
            "refusals": substitutions,
        },
        "contract_identity": identity,
        "contract_independence": [independent, injected],
        "contract_pure": {
            "labels": labels,
            "seeds": list(CONTRACT_SEEDS),
            "isolation": "stdlib-only",
        },
        "contract_limits": limits,
        "contract_malformed": malformed,
        "contract_order_substitution": order_substitution,
        "contract_live_grafts": grafts,
    }


def input_closure(repository):
    paths = sorted((repository / "src/pietto").rglob("*.py"))
    paths += [
        repository / p
        for p in (
            "tests/_pietto_phase67_result_product_probe.py",
            "ci/phase67-arrow-compatibility-requirements.txt",
            "pyproject.toml",
            "uv.lock",
        )
    ]
    return {
        p.relative_to(repository).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }


def _exact(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False
    )


def verify_report(value, context, inputs):
    """Data-only checks require actual measured types/values, not an exit-zero flag."""
    if (
        type(value) is not dict
        or set(value)
        != {
            "format",
            "context",
            "pin",
            "inputs",
            "origins",
            "prefix",
            "dependencies",
            "cases",
        }
        or value["format"] != FORMAT
        or not _exact(value["context"], context)
        or value["pin"] != PIN
        or value["inputs"] != inputs
    ):
        raise ValueError("product evidence identity")
    cases = value["cases"]
    if type(cases) is not dict or set(cases) != set(CASES):
        raise ValueError("product witness denominator")
    for target, storage in (("postgres", "pg_int8"), ("mysql", "my_bigint")):
        if not _exact(
            cases[target],
            {
                "rows": [
                    [BIG, None],
                    [BIG, -BIG],
                    [0, 0],
                    [-1, 1],
                    [LOW, HIGH],
                    [HIGH, LOW],
                ],
                "types": ["int64", "int64"],
                "nullable": [False, True],
                "labels": ["renamed", "other"],
                "storage": [storage, storage],
            },
        ):
            raise ValueError("product measured Int correspondence")
    expected = {
        "neutral_reuse": {
            "same_contract": True,
            "outside_narrow_domain": "VALUE_DOMAIN",
        },
        "foreign_root": ["ROOT", "ROOT"],
        "ordered_fields": ["FIELD"] * 3,
        "empty": [0, ["int64", "int64"]],
        "all_null": [2, "int64"],
        "null_bool_arity": [
            "NULL",
            "VALUE_DOMAIN",
            "ROW_ARITY",
            "ROW_ARITY",
            "VALUE_DOMAIN",
            "VALUE_DOMAIN",
            "VALUE_DOMAIN",
        ],
        "producer_mismatch": ["PRODUCER_OBSERVATION"] * 2,
        "coordinated_mutation": "PRODUCER_OBSERVATION/PRODUCER_ROOT",
        "owned": [[BIG, 0], [None, 1]],
        "limits": ["LIMIT"] * 3,
        "batch_corruption": ["ARROW_SCHEMA", "NULL", "LIMIT"],
        "no_reconstruction": True,
    }
    if any(not _exact(cases[k], v) for k, v in expected.items()):
        raise ValueError("product negative/ownership evidence")
    verify_contract_report(cases)
    verify_scalar_report(cases)
    verify_text_report(cases)
    verify_decimal_report(cases)
    verify_temporal_report(cases)
    verify_finite_report(cases)
    verify_reader_report(cases)
    verify_interop_report(cases)
    verify_ingress_report(cases)
    origins = value["origins"]
    prefix = Path(value["prefix"])
    required = {"pietto._project." + name for name in PRODUCTS} | {
        "pietto._project.check",
        "pietto._project.project_sql_emission",
        "pietto._project.project_sql_plan_verification",
    }
    if (
        not isinstance(origins, dict)
        or not required <= set(origins)
        or not prefix.is_absolute()
        or ".." in prefix.parts
    ):
        raise ValueError("installed product origins")
    for name, origin in origins.items():
        if (
            (name != "pietto" and not name.startswith("pietto."))
            or set(origin) != {"path", "member", "sha256"}
            or not Path(origin["path"]).is_relative_to(prefix)
            or "site-packages" not in Path(origin["path"]).parts
            or ".." in Path(origin["path"]).parts
            or origin["member"]
            not in (
                name.replace(".", "/") + ".py",
                name.replace(".", "/") + "/__init__.py",
            )
            or not origin["path"].endswith("/site-packages/" + origin["member"])
            or inputs.get("src/" + origin["member"]) != origin["sha256"]
        ):
            raise ValueError("foreign installed origin")
    dependencies = value["dependencies"]
    if type(dependencies) is not dict or set(dependencies) != {
        "pyarrow",
        "antlr4-python3-runtime",
    }:
        raise ValueError("installed dependency denominator")
    for name, version, module in (
        ("pyarrow", PIN, "pyarrow"),
        ("antlr4-python3-runtime", "4.13.2", "antlr4"),
    ):
        actual = dependencies[name]
        if (
            type(actual) is not dict
            or set(actual) != {"version", "path"}
            or actual["version"] != version
            or not Path(actual["path"]).is_relative_to(prefix)
            or ".." in Path(actual["path"]).parts
            or not actual["path"].endswith("/site-packages/" + module + "/__init__.py")
        ):
            raise ValueError("installed dependency origin/pin")
    return value


def verify_contract_report(cases):
    from pietto._project import project_result_contract_pure_boundary as pure

    try:
        documents = cases["contract_documents"]
        if type(documents) is not dict or set(documents) != set(CONTRACT_CORPUS):
            raise ValueError("contract document denominator")
        for name, data in documents.items():
            check_document_oracle(name, data)
        substitutions = cases["contract_substitutions"]
        if set(substitutions) != {"tail", "nullability", "refusals"}:
            raise ValueError("contract substitution denominator")
        original = pure.decode_contract(documents["postgres"].encode("utf-8"))
        if substitutions["tail"] != coherent_tail(original).canonical_bytes.decode(
            "utf-8"
        ):
            raise ValueError("coherent tail observation")
        changed = original.document
        changed["fields"][0]["nullability"] = "unknown"
        if substitutions["nullability"] != pure.encode_document(changed).decode(
            "utf-8"
        ):
            raise ValueError("coherent nullability observation")
        order_doc = json.loads(documents["imported"])
        order_doc["ordering"]["keys"][0].update(
            authored_direction="asc", direction="asc"
        )
        if cases["contract_order_substitution"] != {
            "document": pure.encode_document(order_doc).decode("utf-8"),
            "refusal": "CORRESPONDENCE",
        }:
            raise ValueError("contract legal ordering substitution")
        expected = {
            "contract_identity": ["ROOT", "ROOT"]
            + ["ROOT", "PRODUCER_ROOT", "ARROW_BINDING"] * 3
            + ["FIELD"],
            "contract_independence": ["CORRESPONDENCE"] * 2,
            "contract_limits": ["DOCUMENT_LIMIT"] * 8,
            "contract_malformed": MALFORMED_EXPECTED,
            "contract_live_grafts": {
                name: ["ROOT" if name in ("owner", "output") else "FIELD"] * 2
                for name in (
                    "owner",
                    "output",
                    "port",
                    "canonical",
                    "declared",
                    "provenance",
                    "damaged_live",
                )
            },
            "contract_pure": {
                "labels": {
                    name: ["renamed", "other"]
                    if name in ("postgres", "mysql")
                    else ["id", "label", "amount", "second"]
                    for name in CONTRACT_CORPUS
                },
                "seeds": [7, 19],
                "isolation": "stdlib-only",
            },
        }
        if substitutions["refusals"] != ["CORRESPONDENCE"] * 2 or any(
            not _exact(cases[k], v) for k, v in expected.items()
        ):
            raise ValueError("contract runtime refusal/isolation observations")
    except (AssertionError, KeyError, TypeError, pure.ContractDocumentError) as exc:
        raise ValueError("contract document evidence") from exc


def compare_product_reports(paths, repository, contexts):
    if len(paths) != 2:
        raise ValueError("two product reports required")
    checkout = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    documents = []
    for py, path in zip(("3.12", "3.13"), paths, strict=True):
        data = path.read_bytes()
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("product report limit")
        value = json.loads(data)
        context = contexts[py]
        if context != {
            **context,
            "checkout": checkout,
            "run_id": os.environ["GITHUB_RUN_ID"],
            "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
            "python": py,
        }:
            raise ValueError("product comparison context")
        verify_report(value, context, input_closure(repository))
        reject_report_damage(value, context, input_closure(repository))
        documents.append(
            (
                value["cases"]["contract_documents"],
                value["cases"]["scalar_codec"],
                value["cases"]["text_codec"],
                value["cases"]["decimal_codec"],
                value["cases"]["temporal_codec"],
                value["cases"]["finite_codec"],
            )
        )
    if documents[0] != documents[1]:
        raise ValueError("cross-runtime complete canonical bytes differ")
    print("verified complete canonical document bytes across Python 3.12/3.13")


def reject_report_damage(value, context, inputs):
    """Mutate actual saved-data observations, never fake an Arrow success."""
    mutations = (
        lambda v: v["cases"]["ingress_rows"]["postgres"]["values"]["snapshot"]["rows"][
            0
        ].__setitem__(12, 1),
        lambda v: v["cases"]["ingress_batch"]["mysql"]["sliced"]["snapshot"]["valid"][
            1
        ].__setitem__(1, True),
        lambda v: v["cases"]["ingress_reader"]["postgres"]["trailing_empty"].update(
            source_complete=False
        ),
        lambda v: v["cases"]["ingress_parity"]["mysql"]["batch"]["snapshot"]["rows"][
            0
        ].__setitem__(4, "0000000000000000"),
        lambda v: v["cases"]["ingress_refusals"]["postgres"]["preaccept"][0][
            "before"
        ].__setitem__(1, 1),
        lambda v: v["cases"]["ingress_ownership"]["mysql"]["downstream"][
            "after"
        ].__setitem__(0, "CLOSED"),
        lambda v: v["cases"]["ingress_resources"]["postgres"]["delivery_under"].update(
            charge=630
        ),
        lambda v: v["cases"]["ingress_independence"]["mysql"]["substitutions"][1][
            "rows"
        ][0].__setitem__(12, -7),
        lambda v: v["cases"]["ownership_copy"]["postgres"]["values"]["rows"][
            0
        ].__setitem__(4, "0000000000000000"),
        lambda v: v["cases"]["ownership_borrow"]["mysql"].update(
            pinned_after_exporter_close=False
        ),
        lambda v: v["cases"]["ownership_transfer"]["postgres"].update(
            failed_replay="PASS"
        ),
        lambda v: v["cases"]["c_schema_array"]["mysql"]["imported"]["fields"][
            12
        ].update(label="lost"),
        lambda v: v["cases"]["c_schema_requests"]["postgres"].update(request_pulls=1),
        lambda v: v["cases"]["c_stream_values"]["mysql"]["mixed"]["rows"][
            0
        ].__setitem__(12, 1),
        lambda v: v["cases"]["c_stream_terminal"]["postgres"]["late"].update(
            source_complete=True
        ),
        lambda v: v["cases"]["c_protocol_lifetime"]["mysql"].update(
            foreign_close_state="COMPLETE"
        ),
        lambda v: v["cases"]["cpu_protocol_resources"]["postgres"]["empty_cap"].update(
            reads=99
        ),
        lambda v: v["cases"]["interop_correspondence"]["mysql"]["swaps"][0]["rows"][
            0
        ].__setitem__(12, -7),
        lambda v: v["cases"]["reader_values"]["postgres"]["result"]["rows"][
            0
        ].__setitem__(12, 1),
        lambda v: v["cases"]["reader_empty_null"]["mysql"]["empty"]["receipt"].update(
            batches=0
        ),
        lambda v: v["cases"]["reader_extent"]["postgres"]["short"]["receipt"].update(
            state="COMPLETE"
        ),
        lambda v: v["cases"]["reader_terminal"]["mysql"]["late"]["trace"][
            "events"
        ].__setitem__(-1, ["eof"]),
        lambda v: v["cases"]["reader_lifecycle"]["postgres"]["cleanup"]["trace"].update(
            close_success=1
        ),
        lambda v: v["cases"]["reader_limits"]["mysql"]["under_bytes"]["receipt"].update(
            charge=0
        ),
        lambda v: v["cases"]["reader_rechunk"]["postgres"]["layouts"]["uneven"][
            "receipt"
        ]["descriptors"][1].__setitem__(1, 0),
        lambda v: v["cases"]["reader_identity"]["mysql"].update(
            coordinated_counts="PASS"
        ),
        lambda v: v["cases"]["reader_correspondence"]["postgres"]["cases"][0]["rows"][
            0
        ].__setitem__(12, -7),
        lambda v: v["cases"]["reader_incremental"]["mysql"].update(first_pulls=3),
        lambda v: v["cases"]["finite_mixed_values"]["postgres"]["values"]["rows"][
            0
        ].__setitem__(12, 1),
        lambda v: v["cases"]["finite_empty"]["mysql"]["snapshot"]["fields"][7].update(
            type="null"
        ),
        lambda v: v["cases"]["finite_all_null"]["postgres"]["first_null"]["valid"][
            0
        ].__setitem__(12, True),
        lambda v: v["cases"]["carrier_labels"]["mysql"]["populated"]["fields"][
            12
        ].update(label="lost_duplicate"),
        lambda v: v["cases"]["carrier_label_refusals"]["aggregate"].update(
            accepted_bytes=65537
        ),
        lambda v: v["cases"]["finite_resources"]["postgres"]["null/wide"].update(
            charge=321
        ),
        lambda v: v["cases"]["finite_correspondence"]["mysql"]["substitutions"][0][
            "rows"
        ][0].__setitem__(12, -7),
        lambda v: v["cases"]["finite_codec"].__setitem__(
            "postgres/mixed",
            v["cases"]["finite_codec"]["postgres/mixed"].replace(
                '"ordinal":12', '"ordinal":11'
            ),
        ),
        lambda v: v["cases"].pop("meaning_premise"),
        lambda v: v["cases"]["meaning_premise"]["postgres"]["entries"][0].update(
            source_position=99
        ),
        lambda v: v["cases"]["timestamp_values"]["postgres"]["ticks"][0].__setitem__(
            0, 0
        ),
        lambda v: v["cases"]["timestamp_values"]["mysql"]["types"].__setitem__(
            0, "timestamp[ms, tz=UTC]"
        ),
        lambda v: v["cases"]["uuid_values"]["postgres/uuid"]["bytes"][0].__setitem__(
            0, "33221100554477668899aabbccddeeff"
        ),
        lambda v: v["cases"]["uuid_values"]["mysql/binary16"]["types"].__setitem__(
            0, "extension<arrow.uuid>"
        ),
        lambda v: v["cases"]["timestamp_policy"]["postgres"].pop("raw_ticks"),
        lambda v: v["cases"]["meaning_premise"]["mysql"]["entries"][0]["law"].update(
            timezone="UTC"
        ),
        lambda v: v["cases"]["temporal_codec"].pop("mysql/mixed"),
        lambda v: v["cases"].pop("decimal_values"),
        lambda v: v["cases"]["decimal_values"]["postgres/65/30"]["default"]["columns"][
            0
        ].__setitem__(0, "1"),
        lambda v: v["cases"]["decimal_values"]["postgres/39/4"]["default"]["decimal"][
            0
        ].update(scale=3),
        lambda v: v["cases"]["decimal_values"]["mysql/9/2"]["wide"]["decimal"][
            0
        ].update(bits=128),
        lambda v: v["cases"]["decimal_values"]["postgres/9/2"]["overflow"].__setitem__(
            0, "PASS"
        ),
        lambda v: v["cases"]["decimal_context"]["mysql"][0]["after"]["flags"].update(
            Rounded=False
        ),
        lambda v: v["cases"]["decimal_resources"]["postgres/256"].update(allowance=34),
        lambda v: v["cases"]["decimal_supplied"]["mysql/128"]["overflow"].__setitem__(
            0, "PASS"
        ),
        lambda v: v["cases"]["decimal_codec"].pop("mysql/mixed"),
        lambda v: v["cases"].pop("text_values"),
        lambda v: v["cases"]["text_values"]["postgres/32"]["columns"][0].__setitem__(
            6, "é"
        ),
        lambda v: v["cases"]["text_values"]["mysql/64"]["utf8"][0].__setitem__(3, "61"),
        lambda v: v["cases"]["text_binding"]["mysql"]["descriptors"][0].update(
            length=9
        ),
        lambda v: v["cases"]["text_requests"]["postgres"].__setitem__(0, "PASS"),
        lambda v: v["cases"]["text_resources"]["mysql/64"].update(allowance=36),
        lambda v: v["cases"]["text_supplied"]["postgres/32"]["malformed"].__setitem__(
            1, "PASS"
        ),
        lambda v: v["cases"]["text_codec"].pop("postgres/text"),
        lambda v: v["cases"].pop("integer_widths"),
        lambda v: v["cases"]["integer_widths"].pop("mysql/16"),
        lambda v: v["cases"]["integer_adaptation"]["postgres"]["refusals"].__setitem__(
            0, "PASS"
        ),
        lambda v: v["cases"]["scalar_mixed"]["mysql"]["columns"][2].__setitem__(0, 0),
        lambda v: v["cases"]["scalar_mixed"]["postgres"]["columns"][4].__setitem__(
            1, "0000000000000000"
        ),
        lambda v: v["cases"]["scalar_batches"]["mysql"]["sign_flip"].update(
            value="PASS"
        ),
        lambda v: v["cases"]["scalar_codec"].pop("postgres"),
        lambda v: v["context"].update(checkout="0" * 40),
        lambda v: v["context"].update(run_attempt=True),
        lambda v: v["context"].update(python="0.0"),
        lambda v: v["context"].update(python_version="0.0.0"),
        lambda v: v["cases"]["contract_malformed"].update(dangling_ref="PASS"),
        lambda v: v.update(pin="0.0"),
        lambda v: v["inputs"].pop(next(iter(v["inputs"]))),
        lambda v: v["cases"].pop("owned"),
        lambda v: v["cases"]["contract_documents"].pop("imported"),
        lambda v: v["cases"]["contract_documents"].update(
            postgres=v["cases"]["contract_documents"]["postgres"].replace(
                '"label":"renamed"', '"label":"wrong"'
            )
        ),
        lambda v: v["cases"]["contract_substitutions"].update(
            refusals=["PASS", "PASS"]
        ),
        lambda v: v["origins"].pop(
            "pietto._project.project_result_contract_pure_boundary"
        ),
        lambda v: v["cases"]["contract_documents"].update(
            postgres=v["cases"]["contract_documents"]["postgres"].replace(
                "pietto.result-contract.v1", "pietto.result-contract.v2"
            )
        ),
        lambda v: v["cases"]["contract_independence"].__setitem__(0, "PASS"),
        lambda v: v["cases"]["postgres"]["rows"][2].__setitem__(0, False),
        lambda v: v["cases"]["postgres"]["rows"][3].__setitem__(0, -1.0),
        lambda v: v["cases"]["mysql"]["types"].__setitem__(0, "int32"),
        lambda v: v["cases"].__setitem__("coordinated_mutation", "PASS"),
        lambda v: v["origins"].pop("pietto._project.project_result_contract"),
        lambda v: v["origins"]["pietto._project.project_result_contract"].update(
            member="pietto/__init__.py"
        ),
        lambda v: v["dependencies"]["pyarrow"].update(
            path="/checkout/pyarrow/__init__.py"
        ),
    )
    for mutate in mutations:
        bad = json.loads(json.dumps(value))
        mutate(bad)
        try:
            verify_report(bad, context, inputs)
        except ValueError:
            continue
        raise AssertionError("damaged product report accepted")
    return len(mutations)


def _module_path(name):
    filename = importlib.import_module(name).__file__
    assert filename is not None
    return str(Path(filename).resolve())


def main():
    if sys.argv[1:] == ["--contract-child"]:
        with TemporaryDirectory(prefix="pietto-contract-") as scratch:
            print(
                json.dumps(
                    contract_documents(Path(scratch)),
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
        return
    if len(sys.argv) == 6 and sys.argv[1] == "--compare-contract-reports":
        compare_product_reports(
            [Path(p) for p in sys.argv[2:4]],
            Path(sys.argv[4]),
            json.loads(Path(sys.argv[5]).read_text()),
        )
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    pa = importlib.import_module("pyarrow")

    assert pa.__version__ == PIN
    repository = args.repository.resolve()
    context = {
        "checkout": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository, text=True
        ).strip(),
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "python_version": platform.python_version(),
    }
    with TemporaryDirectory(prefix="pietto-int-") as scratch:
        cases = run_cases(Path(scratch))
    prefix = Path(sys.prefix).resolve()
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "pietto" or name.startswith("pietto."):
            assert module.__file__ is not None
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(prefix) and "site-packages" in path.parts
            member = "/".join(path.parts[path.parts.index("site-packages") + 1 :])
            origins[name] = {
                "path": str(path),
                "member": member,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    value = {
        "format": FORMAT,
        "context": context,
        "pin": PIN,
        "inputs": input_closure(repository),
        "origins": origins,
        "prefix": str(prefix),
        "dependencies": {
            name: {
                "version": importlib.metadata.version(name),
                "path": _module_path(module),
            }
            for name, module in (
                ("pyarrow", "pyarrow"),
                ("antlr4-python3-runtime", "antlr4"),
            )
        },
        "cases": cases,
    }
    verify_report(value, context, input_closure(repository))
    rejected = reject_report_damage(value, context, input_closure(repository))
    assert len(cases) == 92
    assert rejected == 90
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
    print(
        f"installed product: {len(cases)} cases, {len(origins)} verified origins, PyArrow {PIN}"
    )


if __name__ == "__main__":
    main()
