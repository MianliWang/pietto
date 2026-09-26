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


CONTRACT_CORPUS = ("postgres", "mysql", "descriptors", "imported")
CONTRACT_SEEDS = (7, 19)


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
            )
        )
    if documents[0] != documents[1]:
        raise ValueError("cross-runtime complete canonical bytes differ")
    print("verified complete canonical document bytes across Python 3.12/3.13")


def reject_report_damage(value, context, inputs):
    """Mutate actual saved-data observations, never fake an Arrow success."""
    mutations = (
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
    assert rejected == 45
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
    print(
        f"installed product: {len(cases)} cases, {len(origins)} verified origins, PyArrow {PIN}"
    )


if __name__ == "__main__":
    main()
