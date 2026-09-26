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
            (value["cases"]["contract_documents"], value["cases"]["scalar_codec"])
        )
    if documents[0] != documents[1]:
        raise ValueError("cross-runtime complete canonical bytes differ")
    print("verified complete canonical document bytes across Python 3.12/3.13")


def reject_report_damage(value, context, inputs):
    """Mutate actual saved-data observations, never fake an Arrow success."""
    mutations = (
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
    assert rejected == 28
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
    print(
        f"installed product: {len(cases)} cases, {len(origins)} verified origins, PyArrow {PIN}"
    )


if __name__ == "__main__":
    main()
