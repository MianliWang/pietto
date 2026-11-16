"""Installed pietto.interop consumer; importing its report checker needs no Arrow.

Run it with ``-I`` in one environment per cell: ``arrow`` (the arrow-ready
environment, ``pietto[arrow,execute-duckdb]``, no target library) or a target
(``pietto[arrow,interop-<target>]``). It fails when the cell's target is missing
or another target is present. Before it exits it checks its own report with
``verify_report``: the versions equal the pins and every case is exact. That
check belongs to this witness; the adapters check no target version at run time
(D80.05).
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime
from decimal import Context, Decimal, localcontext
import gc
import hashlib
import importlib
import importlib.metadata
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast
from unittest import mock
from uuid import UUID

from pietto._project.project_arrow_result import PYARROW as ARROW_PIN

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.interop-consumer.v1"
PYARROW = ARROW_PIN[1]
# A literal reader of the five interop extras' pins: it changes with them.
PINS = {
    "pandas": "3.1.1",
    "polars": "2.1.0",
    "numpy": "2.5.4",
    "scipy": "1.18.1",
    "matplotlib": "3.11.2",
}
TARGET = {
    "to_pandas": "pandas",
    "to_polars": "polars",
    "to_numpy": "numpy",
    "to_scipy_csr": "scipy",
    "plot_line": "matplotlib",
    "plot_scatter": "matplotlib",
}
EXTRA = {
    "pandas": "interop-pandas",
    "polars": "interop-polars",
    "numpy": "interop-numpy",
    "scipy": "interop-scipy",
    "matplotlib": "interop-matplotlib",
}
# The target libraries each cell's environment holds (its extra's closure).
CELLS = {
    "arrow": (),
    "pandas": ("pandas", "numpy"),
    "polars": ("polars",),
    "numpy": ("numpy",),
    "scipy": ("scipy", "numpy"),
    "matplotlib": ("matplotlib", "numpy"),
}
COMMON = (
    "type_errors",
    "closed",
    "ordinals",
    "admission",
    "shape_coordinates",
    "envelope",
    "missing_extra",
    "inert",
    "unwrapped_failure",
    "kinds",
    "envelope_nulls",
)
FRAME = (
    "matrix",
    "empty",
    "order",
    "reads",
    "labels",
    "refusals",
    "drift",
    "after_close",
    "relief",
)
# No environment holds it: a target that imports it fails on its own import.
ABSENT_DEPENDENCY = "pietto_interop_absent_dependency"
DRIVERS = ("psycopg", "mysql", "adbc_driver_manager", "adbc_driver_postgresql")
B53 = 2**53
NUMERIC = (
    ("i64", "Int", 64, False),
    ("f64", "Float", None, False),
    ("flag", "Bool", None, False),
    ("maybe", "Int", 64, True),
    ("i16", "Int", 16, False),
    ("i32", "Int", 32, False),
)
NUMERIC_ROWS = {
    "values": [
        [0, 0.5, True, None, 0, 1],
        [B53, -0.0, False, 7, 1, 0],
        [-B53, 1.25, True, None, 2, 3],
        [0, 0.5, True, None, 0, 1],
    ],
    "negative": [[0, 0.0, True, None, 0, 1], [1, 0.0, True, None, -1, 0]],
    "outside": [[0, 0.0, True, None, 0, 1], [1, 0.0, True, None, 2, 4]],
    "duplicate": [
        [0, 0.0, True, None, 0, 1],
        [1, 0.0, True, None, 1, 1],
        [2, 0.0, True, None, 0, 1],
    ],
    "above": [[0, 0.0, True, None, 0, 0], [B53 + 1, 0.0, True, None, 0, 0]],
    "below": [[-B53 - 1, 0.0, True, None, 0, 0]],
}
DATE_ROWS = [[date(1000, 1, 1)], [None], [date(9999, 12, 31)], [date(1000, 1, 1)]]
MATRIX = {
    "numeric": ["int64", "double", "bool", "int64", "int16", "int32"],
    "scalar": ["int64", "int64", "bool", "bool", "double", "double"],
    "text32": ["string", "string", "int16", "bool", "double"],
    "text64": ["large_string", "large_string", "int16", "bool", "double"],
    "decimal": ["decimal128(38, 2)", "decimal128(38, 2)"],
    "date": ["date32[day]"],
    "timestamp": ["timestamp[us]", "timestamp[us]"],
}
POLARS = {
    "int16": "Int16",
    "int32": "Int32",
    "int64": "Int64",
    "bool": "Boolean",
    "double": "Float64",
    "string": "String",
    "large_string": "String",
    "decimal128(38, 2)": "Decimal(precision=38, scale=2)",
    "date32[day]": "Date",
    "timestamp[us]": "Datetime(time_unit='us', time_zone=None)",
}
# The frame functions' rules (PL.47): only to_pandas admits decimal256.
PANDAS_ADMITS = (
    "admits only Int, Bool, Float, Text, Decimal, Date, Timestamp, UUID or nested"
    " fields (a nested field is a list of non-null structs of the other types)"
)
POLARS_ADMITS = (
    "admits only Int, Bool, Float, Text, Decimal, Date, Timestamp, UUID or"
    " nested fields (Decimal up to precision 38; a nested field is a list of"
    " non-null structs of the other types)"
)
COALESCE = (
    "is nullable in the schema; make it non-nullable in Pietto first,"
    " for example with coalesce"
)
# The fix each column refusal names after the rule, by the refused field's kind.
TO_FRAME = "; to_pandas and to_polars admit it"
TO_PANDAS = "; to_pandas admits it"
LEAVE = "; leave it out of the query"
# The finite batch's first refused field: to_pandas still refuses a UUID
# requested as binary16, and to_polars the decimal256 field that to_pandas admits.
FINITE_REFUSED = {
    "pandas": "to_pandas: field 11 ('selected_binary_identifier') has Arrow type"
    f" fixed_size_binary[16]; to_pandas {PANDAS_ADMITS}{LEAVE}",
    "polars": "to_polars: field 8 ('selected_wide_amount') has Arrow type"
    f" decimal256(65, 30); to_polars {POLARS_ADMITS}{TO_PANDAS}",
}
AS_INT = "; make it an Int in the query, for example 1 if flag else 0"
DISTINCT_LABELS = (
    "admits only distinct labels, so give each field its own label in the query"
)
COORDINATES = "row field 4 ('i16') and column field 5 ('i32')"
NESTED = "list<item: struct<i: int64 not null, b: bool, t: string> not null>"
UUID16 = "fixed_size_binary[16]"
NESTED_WIDE = "list<item: struct<d: decimal256(40, 2) not null> not null>"
# PL.47's batches, each from a real producer, and each field's Arrow type as
# to_pandas holds it: a UUID, nested too, as its 16 bytes. nested_kinds has a
# child of each other admitted kind, and outer is an outer JOIN's, whose
# missing container is null, not [].
RELIEF = {
    "temporal": ["timestamp[us]", "timestamp[us]", UUID16, UUID16],
    "wide": ["decimal256(65, 30)", "decimal256(65, 30)"],
    "nested": ["int64", NESTED],
    "nested_uuid": [
        "int64",
        f"list<item: struct<i: int64 not null, u: {UUID16}> not null>",
    ],
    "nested_kinds": [
        "int64",
        "list<item: struct<i: int64 not null, r: double, a: decimal128(9, 2),"
        f" s: timestamp[us], d: date32[day], u: {UUID16}> not null>",
    ],
    "nested_wide": ["int64", NESTED_WIDE],
    "outer": ["int64", "list<item: struct<id: int64 not null> not null>"],
}
# The Polars dtypes of the batches to_polars admits; it refuses the others at
# the field given, since only to_pandas admits decimal256, alone or nested.
POLARS_HELD = {
    "temporal": ["Datetime(time_unit='us', time_zone=None)"] * 2 + ["Binary"] * 2,
    "nested": ["Int64", "List(Struct({'i': Int64, 'b': Boolean, 't': String}))"],
    "nested_uuid": ["Int64", "List(Struct({'i': Int64, 'u': Binary}))"],
    "nested_kinds": [
        "Int64",
        "List(Struct({'i': Int64, 'r': Float64, 'a': Decimal(precision=9,"
        " scale=2), 's': Datetime(time_unit='us', time_zone=None), 'd': Date,"
        " 'u': Binary}))",
    ],
    "outer": ["Int64", "List(Struct({'id': Int64}))"],
}
POLARS_REFUSED = {
    "wide": "field 0 ('renamed') has Arrow type decimal256(65, 30)",
    "nested_wide": f"field 1 ('c') has Arrow type {NESTED_WIDE}",
}
# Containers of (i, u) children: UUIDs with 0x00 and 0xff bytes, a null u, an
# empty container and a repeated row.
NESTED_UUID_ROWS = [
    (1, ((1, B53), (UUID(int=1), None))),
    (2, ((), ())),
    (1, ((1, B53), (UUID(int=1), None))),
    (3, ((-1,), (UUID(int=2**128 - 1),))),
]
KIDS = (
    ("i", "Int8", False),
    ("r", "Float", True),
    ("a", "Decimal", True),
    ("s", "Timestamp", True),
    ("d", "Date", True),
    ("u", "UUID", True),
)
TOKEN = UUID("00112233-4455-6677-8899-aabbccddeeff")
KIDS_ROW = (
    7,
    (
        (1, 2),
        (-0.0, None),
        (Decimal("-12.50"), None),
        (datetime(2000, 2, 29, 12, 0, 0, 1), None),
        (date(1000, 1, 1), None),
        (TOKEN, None),
    ),
)
NESTED_KINDS_ROWS = [
    KIDS_ROW,
    (0, ((), (), (), (), (), ())),
    KIDS_ROW,
    (
        9,
        (
            (3,),
            (1.5,),
            (Decimal("0.01"),),
            (datetime(9999, 12, 31, 23, 59, 59, 499999),),
            (date(9999, 12, 31),),
            (UUID(int=2**128 - 1),),
        ),
    ),
]
NESTED_WIDE_ROWS = [(7, ((Decimal("1.00"),),))]
# Outer-JOIN rows: a missing container (None), distinct from an empty one.
OUTER_ROWS = [(1, None), (2, ((5, 6),)), (3, ((),)), (1, None), (2, ((5, 6),))]
# Arrow types and the admission row kind() gives each: PL.47 adds UUID,
# decimal256 and one level of nesting, and every other shape stays refused.
KINDS = [
    ["int16", "Int"],
    ["int8", None],
    ["uint64", None],
    ["float", None],
    ["decimal128(38, 2)", "Decimal"],
    ["decimal256(10, 2)", "Decimal256"],
    ["date64[ms]", None],
    ["timestamp[us, tz=UTC]", None],
    ["timestamp[ns]", None],
    ["extension<arrow.uuid>", "UUID"],
    ["fixed_size_binary[16]", None],
    ["binary", None],
    [NESTED, "nested"],
    [
        "list<item: struct<u: extension<arrow.uuid>, d: decimal256(40, 2)> not null>",
        "nested",
    ],
    ["list<item: struct<i: int64>>", None],
    ["list<element: struct<i: int64> not null>", None],
    ["large_list<item: struct<i: int64> not null>", None],
    ["list<item: int64 not null>", None],
    ["list<item: struct<> not null>", None],
    ["list<item: struct<f: float> not null>", None],
    ["list<item: struct<x: list<item: struct<i: int64> not null>> not null>", None],
    ["struct<i: int64>", None],
    ["null", None],
]
FILTER = "filter the record out with a where"
FLOAT = (
    "outside the float64-exact range of ±2**53; convert the field with"
    f" Float(...) in the query to accept its rounding, or {FILTER}"
)


def pinned(top):
    return f'install the versions that "pietto[arrow,{EXTRA[top]}]" pins'


def _helper(name):
    path = Path(__file__).with_name(name + ".py").resolve()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    filename = sys.modules[name].__file__
    if filename is None or Path(filename).resolve() != path:
        raise ValueError("foreign result helper")
    return cast(Any, sys.modules[name])


def _product():
    return _helper("_pietto_results_product")


def cases_of(cell):
    if cell == "numpy":
        return COMMON + tuple(f"numpy_{case}" for case in NUMPY)
    if cell == "scipy":
        return COMMON + tuple(f"scipy_{case}" for case in SCIPY)
    if cell == "matplotlib":
        return COMMON + tuple(f"matplotlib_{case}" for case in PLOT)
    if cell == "pandas":
        return COMMON + tuple(f"pandas_{case}" for case in (*FRAME, "ops"))
    return COMMON + (
        tuple(f"{cell}_{case}" for case in FRAME) if cell != "arrow" else ()
    )


# ---------------------------------------------------------------- fixtures


def numeric_fixture(directory, target="postgres"):
    """One real query over six numeric fields (NUMERIC): name, kind, width, nullable."""
    from pietto._project.project_result_binding import (
        ProducerObservation,
        bind_producer,
    )
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_sql_emission import emit_project_sql

    p = _product()
    text = "shape Row:\n" + "".join(
        f"    {name}: {kind}{' | None' if nullable else ''}\n"
        for name, kind, _bits, nullable in NUMERIC
    )
    text += f'source rows: Row = {target}.table("opaque.result.fixture")\n'
    text += "table result:\n    from rows\n    select:\n"
    text += "".join(f"        {name}\n" for name, *_ in NUMERIC)
    checked = p.build_neutral(directory, {"main.pietto": text})
    document = json.loads(p.emission_input(target))
    fields, observed = [], []
    for i, (name, kind, bits, nullable) in enumerate(NUMERIC):
        if kind == "Int":
            bits = cast(int, bits)
            lower, upper = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            storage = p.width_storage(target, bits)
            domain = {"kind": "int_range", "min": str(lower), "max": str(upper)}
            carrier = "int"
        elif kind == "Bool":
            storage, domain, carrier = "pg_bool", {"kind": "bool01"}, "bool"
            lower = upper = None
        else:
            storage = "pg_float8"
            domain = {"kind": "finite_float", "format": "binary64"}
            carrier, lower = "float", None
            upper = None
        fields.append(
            {
                "ordinal": i,
                "name": name,
                "column": name,
                "representation": {
                    "storage": {"kind": storage},
                    "nullable": nullable,
                    "domain": domain,
                },
            }
        )
        observed.append(
            ProducerObservation(
                i,
                name,
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
    contract = build_result_contract(checked)
    return bind_producer(contract, result.artifact, tuple(observed))


def date_fixture(directory, target="postgres"):
    from pietto._project.project_result_binding import (
        ProducerObservation,
        bind_producer,
    )
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_sql_emission import emit_project_sql

    p = _product()
    source = (
        "shape Row:\n    day: Date | None\n"
        f'source rows: Row = {target}.table("opaque.result.fixture")\n'
        "table result:\n    from rows\n    select:\n        event_date = day\n"
    )
    document = json.loads(p.temporal_input(target))
    (item,) = document["sources"][0]["fields"][:1]
    item.update(name="day", column="day")
    item["representation"] = {
        "storage": {"kind": "pg_date"},
        "nullable": True,
        "domain": {"kind": "date"},
    }
    document["sources"][0]["fields"] = [item]
    checked = p.build_neutral(directory, {"main.pietto": source})
    outcome = emit_project_sql(checked, json.dumps(document).encode())
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    return bind_producer(
        output.contract,
        outcome.artifact,
        (
            ProducerObservation(
                0, "event_date", target, "pg_date", domain="date", carrier="date"
            ),
        ),
        output=output,
    )


def timestamp_fixture(directory, target="postgres"):
    from pietto._project.project_result_binding import bind_producer

    p = _product()
    _checked, _meaning, artifact, neutral = p.temporal_premise(
        directory, target, projection=(0, 1)
    )
    observed = tuple(
        replace(o, ordinal=i, label=f"selected_{i}")
        for i, o in enumerate(p.temporal_observations(target)[:2])
    )
    return bind_producer(neutral, artifact, observed)


def outer_fixture(directory):
    """The real binding of an outer JOIN that keeps a nullable collection."""
    from pietto._project.project_execution_reader import bind_postgres_output
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_sql_emission import emit_project_sql

    plan = _helper("_pietto_plan_nested")
    verified = plan.nested_plan(directory, plan.retained_outer_sources())
    contract = json.dumps(plan.retained_unnest_contract()).encode()
    outcome = emit_project_sql(verified, contract)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    return bind_postgres_output(
        output, _helper("_pietto_results_nested").metadata(output)
    )


def fixtures(root):
    """Arrow bindings of real queries and the producer rows each batch takes."""
    from pietto._project import project_arrow_result as a

    p = _product()
    nested = _helper("_pietto_results_nested")
    root.mkdir(parents=True, exist_ok=True)
    numeric = numeric_fixture(root / "numeric")
    scalar = p.scalar_fixture(root / "scalar", "postgres")[3]
    text = p.text_fixture(root / "text", "postgres")[3]
    decimal = p.decimal_fixture(root / "decimal", "postgres", 38, 2)[3]
    finite = p.finite_fixture(root / "finite", "postgres")[4]
    temporal = p.temporal_fixture(root / "temporal", "postgres")[4]

    def labels(*ordinals):
        return tuple(
            a.ArrowFieldLabelRequest(f.field, "same") if i in ordinals else None
            for i, f in enumerate(numeric.fields)
        )

    return {
        "numeric": (a.bind_arrow(numeric), NUMERIC_ROWS["values"]),
        "scalar": (a.bind_arrow(scalar), p.scalar_rows("postgres")),
        "text32": (p.text_arrow(text, 32), p.text_rows("postgres")),
        "text64": (p.text_arrow(text, 64), p.text_rows("postgres")),
        "decimal": (p.decimal_arrow(decimal), p.decimal_rows("postgres", 38, 2)),
        "date": (a.bind_arrow(date_fixture(root / "date")), DATE_ROWS),
        "timestamp": (
            a.bind_arrow(timestamp_fixture(root / "timestamp")),
            [row[:2] for row in p.temporal_rows("postgres")],
        ),
        "finite": (
            a.bind_arrow(finite, **p.finite_policy(finite)),
            p.finite_rows("postgres"),
        ),
        "temporal": (a.bind_arrow(temporal), p.temporal_rows("postgres")),
        "nested": (
            a.bind_arrow(nested.real(p, root / "nested", nested.IBT)),
            list(nested.ROWS),
        ),
        "wide": (
            p.decimal_arrow(p.decimal_fixture(root / "wide", "postgres", 65, 30)[3]),
            p.decimal_rows("postgres", 65, 30),
        ),
        "nested_uuid": (
            a.bind_arrow(
                nested.real(
                    p, root / "nested-uuid", (("i", "Int8", False), ("u", "UUID", True))
                )
            ),
            NESTED_UUID_ROWS,
        ),
        "nested_kinds": (
            a.bind_arrow(nested.real(p, root / "nested_kinds", KIDS)),
            NESTED_KINDS_ROWS,
        ),
        "nested_wide": (
            a.bind_arrow(
                nested.real(p, root / "nested_wide", (("d", "Decimal(40, 2)", False),))
            ),
            NESTED_WIDE_ROWS,
        ),
        "outer": (a.bind_arrow(outer_fixture(root / "outer")), OUTER_ROWS),
        # Fields 0 and 1 differ in type; fields 0 and 3 are both int64.
        "labels": (
            a.bind_arrow(numeric, field_labels=labels(0, 1)),
            NUMERIC_ROWS["values"],
        ),
        "same_type_labels": (
            a.bind_arrow(numeric, field_labels=labels(0, 3)),
            NUMERIC_ROWS["values"],
        ),
    }


def batch(binding, rows):
    """A real ResultBatch: the owner's managed batch through the private _batch."""
    from pietto._project.project_arrow_interop import build_managed_batch
    from pietto.execution._handle import _batch

    return _batch(build_managed_batch(binding, rows))


# ---------------------------------------------------------------- observation


def refusal(action, result):
    """The class, message (or PIE code and detail) and batch state of a refusal."""
    from pietto.execution import HandleMisuse

    try:
        action()
    except HandleMisuse as exc:
        return [type(exc).__name__, exc.code, exc.detail, result.closed]
    except (TypeError, ValueError, ModuleNotFoundError) as exc:
        name = getattr(exc, "name", None) if type(exc) is ModuleNotFoundError else None
        return [type(exc).__name__, str(exc), name, result.closed]
    raise AssertionError("interop refusal unexpectedly accepted")


def exports(item, call):
    """The call's outcome, the batch's Arrow exports during it, the batch after."""
    from pietto.execution import ResultBatch

    calls = {"array": 0, "schema": 0}
    array, schema = ResultBatch.__arrow_c_array__, ResultBatch.__arrow_c_schema__

    def counted_array(self, requested_schema=None):
        calls["array"] += 1
        return array(self, requested_schema)

    def counted_schema(self):
        calls["schema"] += 1
        return schema(self)

    with (
        mock.patch.object(ResultBatch, "__arrow_c_array__", counted_array),
        mock.patch.object(ResultBatch, "__arrow_c_schema__", counted_schema),
    ):
        outcome = call()
    return [
        outcome,
        calls,
        item.closed,
        item.num_rows,
        sorted(m for m in sys.modules if m.partition(".")[0] in DRIVERS),
    ]


def token(value):
    """A tag that keeps bool/int/float/text/decimal/temporal values distinct."""
    if value is None:
        return None
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        return ["float", struct.pack(">d", value).hex()]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        return ["timestamp", value.isoformat(timespec="microseconds")]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, list):
        return ["list", [token(v) for v in value]]
    if isinstance(value, dict):
        return ["struct", [[k, token(v)] for k, v in value.items()]]
    raise TypeError(type(value).__name__)


def scaled(value, kind):
    """A producer value as a frame holds it: a decimal at its field scale (no
    negative zero)."""
    if value is not None and kind.startswith("decimal"):
        scale = int(kind.rstrip(")").split(", ")[1])
        with localcontext(Context(prec=100)):
            return Decimal(int(value.scaleb(scale))).scaleb(-scale)
    return value


def oracle(rows, types):
    """Producer input rows as the columns a frame must hold: decimals at their
    field scale and timestamps at microseconds."""
    return [
        [token(scaled(row[i], kind)) for row in rows] for i, kind in enumerate(types)
    ]


def frame_columns(cell, frame):
    if cell == "pandas":
        return [
            [
                None if missing else token(value)
                for value, missing in zip(
                    frame.iloc[:, i].tolist(),
                    frame.iloc[:, i].isna().tolist(),
                    strict=True,
                )
            ]
            for i in range(frame.shape[1])
        ]
    return [
        [token(v) for v in frame.to_series(i).to_list()] for i in range(frame.width)
    ]


def frame_types(cell, frame):
    if cell == "pandas":
        return [str(d) for d in frame.dtypes]
    return [repr(d) for d in frame.dtypes]


def frame_index(cell, frame):
    if cell == "pandas":
        index = frame.index
        return [type(index).__name__, index.start, index.stop, index.step]
    return None


# ---------------------------------------------------------------- cases


def common_cases(cell, fx):
    interop: Any = importlib.import_module("pietto.interop")

    numeric = batch(*fx["numeric"])
    closed = batch(*fx["numeric"])
    closed.close()
    observations: dict[str, Any] = {}
    targets = tuple(PINS)
    before = {m for m in sys.modules if m.partition(".")[0] in targets}
    ax = object()
    observations["type_errors"] = [
        refusal(lambda: interop.to_pandas(None), numeric),
        refusal(lambda: interop.to_polars({"batch": numeric}), numeric),
        refusal(lambda: interop.to_numpy(numeric, True), numeric),
        refusal(lambda: interop.to_numpy(numeric, 1.0), numeric),
        refusal(lambda: interop.to_numpy(numeric, "0"), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 5, 0, [3, 4]), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 5, 0, (3, 4.0)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 5, 0, (3,)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, False, 0, (3, 4)), numeric),
        refusal(lambda: interop.plot_line(numeric, 0, None, ax=ax), numeric),
        refusal(lambda: interop.plot_scatter(numeric, 0.0, 1, ax=ax), numeric),
        # Argument types come in parameter order and before the one read of
        # the batch, so a closed batch still reports the type error.
        refusal(lambda: interop.to_numpy(closed, True), closed),
        refusal(lambda: interop.to_scipy_csr(closed, 0, 1.0, 2, (3, 4)), closed),
        refusal(lambda: interop.to_scipy_csr(closed, 0, 1, 2, [3, 4]), closed),
        refusal(lambda: interop.plot_line(closed, "0", 1, ax=ax), closed),
        refusal(lambda: interop.plot_scatter(closed, 0, None, ax=ax), closed),
        refusal(lambda: interop.to_scipy_csr(numeric, False, 1, 2.0, None), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 0, 1, 2.0, None), numeric),
        refusal(lambda: interop.plot_line(numeric, "0", None, ax=ax), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 1.0, False, 0, (3, 4)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 0, False, 1.0, (3, 4)), numeric),
        # A type error comes before an out-of-range ordinal.
        refusal(lambda: interop.to_scipy_csr(numeric, 99, 5, 0, None), numeric),
    ]
    after = {m for m in sys.modules if m.partition(".")[0] in targets}
    observations["type_errors"].append(sorted(after - before))
    if "matplotlib" in CELLS[cell]:
        # With Matplotlib installed, the plot refusals below get a real Axes.
        ax = axes()

    observations["closed"] = [
        refusal(lambda: interop.to_pandas(closed), closed),
        refusal(lambda: interop.to_polars(closed), closed),
        refusal(lambda: interop.to_numpy(closed, 99), closed),
        refusal(lambda: interop.to_scipy_csr(closed, 1, 1, 1, (9999, 0)), closed),
        refusal(lambda: interop.plot_line(closed, 0, 1, ax=ax), closed),
        refusal(lambda: interop.plot_scatter(closed, 0, 1, ax=ax), closed),
    ]

    observations["ordinals"] = [
        refusal(lambda: interop.to_numpy(numeric, -1), numeric),
        refusal(lambda: interop.to_numpy(numeric, 6), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 3, 99, 1, (3, 4)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 4, 0, (3, 4)), numeric),
        refusal(lambda: interop.plot_line(numeric, 0, 6, ax=ax), numeric),
        refusal(lambda: interop.plot_scatter(numeric, -6, 1, ax=ax), numeric),
    ]

    finite = batch(*fx["finite"])
    text = batch(*fx["text32"])
    dated = batch(*fx["date"])
    labelled = batch(*fx["labels"])
    observations["admission"] = [
        refusal(lambda: interop.to_pandas(finite), finite),
        refusal(lambda: interop.to_polars(finite), finite),
        # A repeated label is refused before the target import in every cell.
        refusal(lambda: interop.to_pandas(labelled), labelled),
        refusal(lambda: interop.to_polars(labelled), labelled),
        refusal(lambda: interop.to_numpy(numeric, 3), numeric),
        refusal(lambda: interop.to_numpy(text, 0), text),
        refusal(lambda: interop.to_numpy(dated, 0), dated),
        refusal(lambda: interop.to_numpy(finite, 1), finite),
        refusal(lambda: interop.to_scipy_csr(numeric, 1, 5, 0, (9999, 4)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 2, 5, 0, (3, 4)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 3, 0, (3, 4)), numeric),
        refusal(lambda: interop.plot_line(numeric, 2, 1, ax=ax), numeric),
        refusal(lambda: interop.plot_scatter(dated, 0, 0, ax=ax), dated),
        refusal(lambda: interop.plot_line(text, 0, 2, ax=ax), text),
    ]

    shaped = {
        name: batch(fx["numeric"][0], rows) for name, rows in NUMERIC_ROWS.items()
    }
    observations["shape_coordinates"] = [
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 5, 0, (4097, 4)), numeric),
        refusal(lambda: interop.to_scipy_csr(numeric, 4, 5, 0, (3, -1)), numeric),
        refusal(
            lambda: interop.to_scipy_csr(shaped["negative"], 4, 5, 0, (0, 0)),
            shaped["negative"],
        ),
        refusal(
            lambda: interop.to_scipy_csr(shaped["negative"], 4, 5, 0, (3, 4)),
            shaped["negative"],
        ),
        refusal(
            lambda: interop.to_scipy_csr(shaped["outside"], 4, 5, 0, (3, 4)),
            shaped["outside"],
        ),
        refusal(
            lambda: interop.to_scipy_csr(shaped["duplicate"], 4, 5, 0, (3, 4)),
            shaped["duplicate"],
        ),
    ]
    observations["envelope"] = [
        refusal(
            lambda: interop.plot_line(shaped["above"], 1, 0, ax=ax), shaped["above"]
        ),
        refusal(
            lambda: interop.plot_scatter(shaped["below"], 0, 1, ax=ax),
            shaped["below"],
        ),
    ]
    if "matplotlib" not in CELLS[cell]:
        # The ±2**53 values themselves pass every check before the target import.
        observations["envelope"].append(
            refusal(lambda: interop.plot_line(numeric, 0, 1, ax=ax), numeric)
        )

    sparse = shaped["outside"]
    admitted = {
        "to_pandas": (lambda: interop.to_pandas(numeric), numeric),
        "to_polars": (lambda: interop.to_polars(numeric), numeric),
        "to_numpy": (lambda: interop.to_numpy(numeric, 0), numeric),
        "to_scipy_csr": (lambda: interop.to_scipy_csr(sparse, 4, 5, 0, (3, 5)), sparse),
        "plot_line": (lambda: interop.plot_line(numeric, 0, 1, ax=ax), numeric),
        "plot_scatter": (lambda: interop.plot_scatter(numeric, 5, 1, ax=ax), numeric),
    }
    absent = [name for name in admitted if TARGET[name] not in CELLS[cell]]
    observations["missing_extra"] = [
        [name, *refusal(*admitted[name])] for name in absent
    ]

    observations["inert"] = []
    for name in absent:
        action, item = admitted[name]
        outcome = exports(item, lambda: refusal(action, item)[0])
        observations["inert"].append([name, *outcome])

    # A target that is installed but whose own import misses a dependency:
    # that failure is the target's, raised as it is, never as the extra hint.
    top = TARGET[absent[0]]
    with TemporaryDirectory(prefix="pietto-interop-shadow-") as shadow:
        Path(shadow, top).mkdir()
        Path(shadow, top, "__init__.py").write_text(
            f"import {ABSENT_DEPENDENCY}\n", encoding="utf-8"
        )
        sys.path.insert(0, shadow)
        importlib.invalidate_caches()
        try:
            outcome = refusal(*admitted[absent[0]])
        finally:
            sys.path.remove(shadow)
            importlib.invalidate_caches()
    observations["unwrapped_failure"] = [
        absent[0],
        *outcome,
        sorted(m for m in sys.modules if m.partition(".")[0] == top),
    ]

    pa: Any = importlib.import_module("pyarrow")
    common: Any = importlib.import_module("pietto.interop._common")
    observations["kinds"] = [[str(t), common.kind(pa, t)] for t in kind_types(pa)]

    # A null is skipped and keeps its record's number: field 3 is nullable.
    def envelope(values):
        item = batch(fx["numeric"][0], [[0, 0.0, True, v, 0, 1] for v in values])
        data = pa.record_batch(item)
        return lambda: common.check_envelope("plot_line", data, "y", 3, "Int"), item

    held, outside = envelope([None, B53, None, -B53]), envelope([None, -B53 - 1])
    observations["envelope_nulls"] = [held[0](), refusal(*outside)]
    return observations


def kind_types(pa):
    """The Arrow types of KINDS, in its order."""

    def listed(*fields, name="item", nullable=False, large=False):
        item = pa.field(name, pa.struct(list(fields)), nullable=nullable)
        return (pa.large_list if large else pa.list_)(item)

    one = pa.field("i", pa.int64())
    return [
        pa.int16(),
        pa.int8(),
        pa.uint64(),
        pa.float32(),
        pa.decimal128(38, 2),
        pa.decimal256(10, 2),
        pa.date64(),
        pa.timestamp("us", "UTC"),
        pa.timestamp("ns"),
        pa.uuid(),
        pa.binary(16),
        pa.binary(),
        listed(
            pa.field("i", pa.int64(), nullable=False),
            pa.field("b", pa.bool_()),
            pa.field("t", pa.string()),
        ),
        listed(pa.field("u", pa.uuid()), pa.field("d", pa.decimal256(40, 2))),
        listed(one, nullable=True),
        listed(one, name="element"),
        listed(one, large=True),
        pa.list_(pa.field("item", pa.int64(), nullable=False)),
        listed(),
        listed(pa.field("f", pa.float32())),
        listed(pa.field("x", listed(one))),
        pa.struct([one]),
        pa.null(),
    ]


def frame_cases(cell, fx):
    interop: Any = importlib.import_module("pietto.interop")

    convert = interop.to_pandas if cell == "pandas" else interop.to_polars
    observations: dict[str, Any] = {}
    matrix, empty = {}, {}
    for name in MATRIX:
        binding, rows = fx[name]
        item = batch(binding, rows)
        frame = convert(item)
        matrix[name] = {
            "types": frame_types(cell, frame),
            "labels": [str(c) for c in frame.columns],
            "index": frame_index(cell, frame),
            "columns": frame_columns(cell, frame),
            "open": not item.closed,
        }
        hollow = batch(binding, [])
        frame = convert(hollow)
        empty[name] = {
            "types": frame_types(cell, frame),
            "index": frame_index(cell, frame),
            "rows": len(frame),
        }
    observations["matrix"], observations["empty"] = matrix, empty

    rows = NUMERIC_ROWS["values"] + [NUMERIC_ROWS["values"][1]]
    frame = convert(batch(fx["numeric"][0], rows))
    observations["order"] = frame_columns(cell, frame)

    # An admitted conversion reads the batch once too and leaves it open.
    counted = batch(*fx["numeric"])
    observations["reads"] = exports(counted, lambda: len(convert(counted)))

    observations["labels"] = []
    for key in ("labels", "same_type_labels"):
        labelled = batch(*fx[key])
        try:
            frame = convert(labelled)
        except Exception as exc:  # a refused label, or the target's own failure
            observations["labels"].append(
                [
                    "raised",
                    type(exc).__module__,
                    type(exc).__name__,
                    str(exc) if type(exc) is ValueError else None,
                    labelled.closed,
                ]
            )
        else:
            observations["labels"].append(["frame", [str(c) for c in frame.columns]])

    finite = batch(*fx["finite"])
    observations["refusals"] = [
        refusal(lambda: convert(finite), finite),
        len(convert(batch(*fx["scalar"]))),
    ]

    # Pin drift: the target hands back another index or dtype than the
    # mapping's; the adapter refuses it and leaves the batch open. The pandas
    # index drifts in its type and, as a RangeIndex one row short, in its
    # length, so a check of the type alone fails.
    pa: Any = importlib.import_module("pyarrow")
    drifted = batch(*fx["numeric"])
    if cell == "pandas":
        compat: Any = importlib.import_module("pyarrow.pandas_compat")
        pandas: Any = importlib.import_module("pandas")
        built = compat.table_to_dataframe

        def reindexed(*args, **kwargs):
            frame = built(*args, **kwargs)
            frame.index = pandas.Index(list(range(len(frame))), dtype="int64")
            return frame

        def shortened(*args, **kwargs):
            return built(*args, **kwargs).iloc[:-1]

        def recast(*args, **kwargs):
            wider = pandas.ArrowDtype(pa.float64())
            return built(*args, **kwargs).astype({"i64": wider})

        drifts = [
            (mock.patch.object(compat, "table_to_dataframe", changed), drifted)
            for changed in (reindexed, shortened, recast)
        ]
    else:
        polars: Any = importlib.import_module("polars")
        built = polars.from_arrow

        def recast(*args, **kwargs):
            wider = polars.col("i64").cast(polars.Float64)
            return built(*args, **kwargs).with_columns(wider)

        # A child of a nested field drifts while the field stays a list.
        def inner(*args, **kwargs):
            child = {"i": polars.Float64, "b": polars.Boolean, "t": polars.String}
            wider = polars.col("c").cast(polars.List(polars.Struct(child)))
            return built(*args, **kwargs).with_columns(wider)

        drifts = [
            (mock.patch.object(polars, "from_arrow", recast), drifted),
            (mock.patch.object(polars, "from_arrow", inner), batch(*fx["nested"])),
        ]
    observations["drift"] = []
    for drift, item in drifts:
        with drift:
            observations["drift"].append(refusal(lambda i=item: convert(i), item))

    item = batch(*fx["text64"])
    frame = convert(item)
    item.close()
    del item
    gc.collect()
    observations["after_close"] = frame_columns(cell, frame)

    # PL.47's UUID, decimal256 and nested cells.
    observations["relief"] = {
        name: relieved(cell, convert, *fx[name]) for name in RELIEF
    }
    if cell == "pandas":
        observations["ops"] = {
            label: pandas_ops(convert(batch(*fx[name])), label)
            for name, label in (("temporal", "maybe_key"), ("wide", "optional"))
        }
    return {f"{cell}_{key}": value for key, value in observations.items()}


def relieved(cell, convert, binding, rows):
    """A batch's frame, read after the batch is closed, and its typed empty
    frame; or the conversion's refusal."""
    item = batch(binding, rows)
    try:
        frame, empty = convert(item), convert(batch(binding, []))
    except ValueError as exc:
        return ["ValueError", str(exc), None, item.closed]
    held = {
        "types": frame_types(cell, frame),
        "labels": [str(c) for c in frame.columns],
        "index": frame_index(cell, frame),
        "open": not item.closed,
        "empty": [frame_types(cell, empty), frame_index(cell, empty), len(empty)],
    }
    item.close()
    del item
    gc.collect()
    return held | {"columns": frame_columns(cell, frame)}


def pandas_ops(frame, label):
    """pandas' own operations on one nullable column: comparison with a value,
    membership in a Series, grouping, unique values, stable sorting and a merge
    with itself, nulls included."""
    pandas: Any = importlib.import_module("pandas")
    column = frame[label]
    first = column.dropna().iloc[:1]
    equal = column == first.iloc[0]
    groups = frame.groupby(label, dropna=False, sort=True).size()
    return {
        "equal": [
            None if missing else bool(value)
            for value, missing in zip(
                equal.tolist(), equal.isna().tolist(), strict=True
            )
        ],
        "member": column.isin(first).tolist(),
        "groups": [
            [token(None if pandas.isna(k) else k), int(n)] for k, n in groups.items()
        ],
        "unique": [token(None if pandas.isna(v) else v) for v in column.unique()],
        "sorted": frame.sort_values(
            label, kind="stable", na_position="last"
        ).index.tolist(),
        "merged": len(frame[[label]].merge(frame[[label]], on=label)),
        "null": column.isna().tolist(),
    }


def run_cases(cell, root):
    if "matplotlib" in CELLS[cell]:
        # Matplotlib's configuration and font cache stay in this run's scratch.
        os.environ["MPLCONFIGDIR"] = str(root / "matplotlib")
    fx = fixtures(root)
    result = common_cases(cell, fx)
    if cell == "numpy":
        return result | numpy_cases(fx)
    if cell == "scipy":
        return result | scipy_cases(fx)
    if cell == "matplotlib":
        return result | plot_cases(fx)
    if cell != "arrow":
        result.update(frame_cases(cell, fx))
    return result


# ---------------------------------------------------------------- checker


def _type_error(text, closed=False):
    return ["TypeError", text, None, closed]


def _value_error(text, closed=False):
    return ["ValueError", text, None, closed]


def _missing(name):
    top = TARGET[name]
    return [
        name,
        "ModuleNotFoundError",
        f'{name} needs {top}: install "pietto[arrow,{EXTRA[top]}]"',
        top,
        False,
    ]


def expected_common(cell):
    closed = ["HandleMisuse", "PIE-R4002", "PUBLIC_BATCH_CLOSED", True]
    nullable = f"field 3 ('maybe') {COALESCE}"
    scipy_ints = "to_scipy_csr admits only Int fields"
    plot = "admits only Int or Float fields"
    envelope = [
        _value_error(
            f"plot_line: y field 0 ('i64') has {B53 + 1} in record 1, {FLOAT}"
        ),
        _value_error(
            f"plot_scatter: x field 0 ('i64') has {-B53 - 1} in record 0, {FLOAT}"
        ),
    ]
    if "matplotlib" not in CELLS[cell]:
        envelope.append(_missing("plot_line")[1:])
    absent = [name for name in TARGET if TARGET[name] not in CELLS[cell]]
    return {
        "type_errors": [
            _type_error(
                "to_pandas: batch must be a pietto.execution.ResultBatch, not NoneType"
            ),
            _type_error(
                "to_polars: batch must be a pietto.execution.ResultBatch, not dict"
            ),
            _type_error("to_numpy: column must be an int field ordinal, not bool"),
            _type_error("to_numpy: column must be an int field ordinal, not float"),
            _type_error("to_numpy: column must be an int field ordinal, not str"),
            _type_error("to_scipy_csr: shape must be a tuple of two ints"),
            _type_error("to_scipy_csr: shape must be a tuple of two ints"),
            _type_error("to_scipy_csr: shape must be a tuple of two ints"),
            _type_error("to_scipy_csr: column must be an int field ordinal, not bool"),
            _type_error("plot_line: y must be an int field ordinal, not NoneType"),
            _type_error("plot_scatter: x must be an int field ordinal, not float"),
            _type_error(
                "to_numpy: column must be an int field ordinal, not bool", True
            ),
            _type_error(
                "to_scipy_csr: column must be an int field ordinal, not float", True
            ),
            _type_error("to_scipy_csr: shape must be a tuple of two ints", True),
            _type_error("plot_line: x must be an int field ordinal, not str", True),
            _type_error(
                "plot_scatter: y must be an int field ordinal, not NoneType", True
            ),
            _type_error("to_scipy_csr: row must be an int field ordinal, not bool"),
            _type_error("to_scipy_csr: value must be an int field ordinal, not float"),
            _type_error("plot_line: x must be an int field ordinal, not str"),
            _type_error("to_scipy_csr: row must be an int field ordinal, not float"),
            _type_error("to_scipy_csr: column must be an int field ordinal, not bool"),
            _type_error("to_scipy_csr: shape must be a tuple of two ints"),
            [],
        ],
        "closed": [closed] * 6,
        "ordinals": [
            _value_error(
                "to_numpy: column -1 is not a field ordinal of this batch (0 <= ordinal < 6)"
            ),
            _value_error(
                "to_numpy: column 6 is not a field ordinal of this batch (0 <= ordinal < 6)"
            ),
            _value_error(
                "to_scipy_csr: column 99 is not a field ordinal of this batch"
                " (0 <= ordinal < 6)"
            ),
            _value_error(
                "to_scipy_csr: row, column and value must name distinct fields,"
                " not fields 4, 4 and 0"
            ),
            _value_error(
                "plot_line: y 6 is not a field ordinal of this batch (0 <= ordinal < 6)"
            ),
            _value_error(
                "plot_scatter: x -6 is not a field ordinal of this batch (0 <= ordinal < 6)"
            ),
        ],
        "admission": [
            _value_error(FINITE_REFUSED["pandas"]),
            _value_error(FINITE_REFUSED["polars"]),
            _value_error(
                "to_pandas: field 1 ('same') repeats the label of field 0;"
                f" to_pandas {DISTINCT_LABELS}"
            ),
            _value_error(
                "to_polars: field 1 ('same') repeats the label of field 0;"
                f" to_polars {DISTINCT_LABELS}"
            ),
            _value_error(f"to_numpy: column {nullable}"),
            _value_error(
                "to_numpy: column field 0 ('renamed') has Arrow type string;"
                f" {NUMPY_ADMITS}{TO_FRAME}"
            ),
            _value_error(
                "to_numpy: column field 0 ('event_date') has Arrow type date32[day];"
                f" {NUMPY_ADMITS}{TO_FRAME}"
            ),
            _value_error(f"to_numpy: column field 1 ('selected_medium') {COALESCE}"),
            _value_error(
                "to_scipy_csr: row field 1 ('f64') has Arrow type double;"
                f" {scipy_ints}{TO_FRAME}"
            ),
            _value_error(
                "to_scipy_csr: row field 2 ('flag') has Arrow type bool;"
                f" {scipy_ints}{AS_INT}"
            ),
            _value_error(f"to_scipy_csr: column {nullable}"),
            _value_error(
                "plot_line: x field 2 ('flag') has Arrow type bool;"
                f" plot_line {plot}{AS_INT}"
            ),
            _value_error(
                "plot_scatter: x field 0 ('event_date') has Arrow type date32[day];"
                f" plot_scatter {plot}{TO_FRAME}"
            ),
            _value_error(
                "plot_line: x field 0 ('renamed') has Arrow type string;"
                f" plot_line {plot}{TO_FRAME}"
            ),
        ],
        "shape_coordinates": [
            _value_error(
                "to_scipy_csr: shape[0] is 4097; each dimension must lie between 0 and 4096"
            ),
            _value_error(
                "to_scipy_csr: shape[1] is -1; each dimension must lie between 0 and 4096"
            ),
            _value_error(
                f"to_scipy_csr: record 0 has the coordinate (0, 1) in {COORDINATES},"
                " outside the shape (0, 0); pass a shape that holds it, at most 4096"
                f" in each dimension, or {FILTER} in the query"
            ),
            _value_error(
                "to_scipy_csr: record 1 has the negative coordinate (-1, 0) in"
                f" {COORDINATES}; coordinates start at 0, so filter such records"
                " out with a where in the query"
            ),
            _value_error(
                f"to_scipy_csr: record 1 has the coordinate (2, 4) in {COORDINATES},"
                " outside the shape (3, 4); pass a shape that holds it, at most 4096"
                f" in each dimension, or {FILTER} in the query"
            ),
            _value_error(
                "to_scipy_csr: records 0 and 2 have the same coordinate (0, 1) in"
                f" {COORDINATES}; to_scipy_csr stores each coordinate once and never"
                " sums, so give each coordinate one record in the query, for example"
                " by grouping it by both fields"
            ),
        ],
        "envelope": envelope,
        "missing_extra": [_missing(name) for name in absent],
        "inert": [
            [
                name,
                "ModuleNotFoundError",
                {"array": 1, "schema": 0},
                False,
                len(NUMERIC_ROWS["outside" if name == "to_scipy_csr" else "values"]),
                [],
            ]
            for name in absent
        ],
        "unwrapped_failure": [
            absent[0],
            "ModuleNotFoundError",
            f"No module named '{ABSENT_DEPENDENCY}'",
            ABSENT_DEPENDENCY,
            False,
            [],
        ],
        "kinds": KINDS,
        "envelope_nulls": [
            None,
            _value_error(
                f"plot_line: y field 3 ('maybe') has {-B53 - 1} in record 1, {FLOAT}"
            ),
        ],
    }


def expected_frames(cell, inputs):
    """Frame oracles from the producer input rows, never from the target output."""
    expected: dict[str, Any] = {}
    matrix, empty = {}, {}
    for name, types in MATRIX.items():
        labels, rows = inputs[name]
        if cell == "pandas":
            shown = [f"{t}[pyarrow]" for t in types]
            index = ["RangeIndex", 0, len(rows), 1]
            hollow = ["RangeIndex", 0, 0, 1]
        else:
            shown = [POLARS[t] for t in types]
            index = hollow = None
        matrix[name] = {
            "types": shown,
            "labels": labels,
            "index": index,
            "columns": oracle(rows, types),
            "open": True,
        }
        empty[name] = {"types": shown, "index": hollow, "rows": 0}
    expected["matrix"], expected["empty"] = matrix, empty
    rows = NUMERIC_ROWS["values"] + [NUMERIC_ROWS["values"][1]]
    expected["order"] = oracle(rows, MATRIX["numeric"])
    count = len(inputs["numeric"][1])
    expected["reads"] = [count, {"array": 1, "schema": 0}, False, count, []]
    convert = "to_pandas" if cell == "pandas" else "to_polars"
    # Repeated labels, of two types and of one type: both are refused before
    # the target converts them.
    expected["labels"] = [
        [
            "raised",
            "builtins",
            "ValueError",
            f"{convert}: field {ordinal} ('same') repeats the label of"
            f" field 0; {convert} {DISTINCT_LABELS}",
            False,
        ]
        for ordinal in (1, 3)
    ]
    expected["refusals"] = [
        _value_error(FINITE_REFUSED[cell]),
        len(inputs["scalar"][1]),
    ]
    changed = (
        f"{convert}: field 0 ('i64') became %s instead of %s;"
        f" {convert} never returns a changed type; {pinned(cell)}"
    )
    another = _value_error(
        f"to_pandas: pandas built another index than a RangeIndex; {pinned(cell)}"
    )
    expected["drift"] = (
        [
            another,
            another,
            _value_error(changed % ("double[pyarrow]", "int64[pyarrow]")),
        ]
        if cell == "pandas"
        else [
            _value_error(changed % ("Float64", "Int64")),
            _value_error(
                f"to_polars: field 1 ('c') became List(Struct({{'i': Float64, 'b':"
                " Boolean, 't': String})) instead of List(Struct({'i': Int64, 'b':"
                " Boolean, 't': String})); to_polars never returns a changed type;"
                f" {pinned(cell)}"
            ),
        ]
    )
    expected["after_close"] = oracle(inputs["text64"][1], MATRIX["text64"])
    expected["relief"] = {}
    for name, types in RELIEF.items():
        if cell == "polars" and name in POLARS_REFUSED:
            expected["relief"][name] = _value_error(
                f"to_polars: {POLARS_REFUSED[name]}; to_polars {POLARS_ADMITS}"
                f"{TO_PANDAS}"
            )
            continue
        labels, rows = inputs[name]
        if cell == "pandas":
            shown = [f"{t}[pyarrow]" for t in types]
            index, empty = ["RangeIndex", 0, len(rows), 1], ["RangeIndex", 0, 0, 1]
        else:
            shown, index, empty = POLARS_HELD[name], None, None
        expected["relief"][name] = {
            "types": shown,
            "labels": labels,
            "index": index,
            "open": True,
            "empty": [shown, empty, 0],
            "columns": oracle(rows, types),
        }
    if cell == "polars":
        return {f"{cell}_{key}": value for key, value in expected.items()}
    expected["ops"] = {
        label: ops_oracle([scaled(row[i], RELIEF[name][i]) for row in inputs[name][1]])
        for name, label, i in (("temporal", "maybe_key", 3), ("wide", "optional", 1))
    }
    return {f"{cell}_{key}": value for key, value in expected.items()}


def ops_oracle(values):
    """pandas_ops of a column that holds these values: pandas groups nulls
    last, sorts bytes unsigned and matches null keys in a merge."""
    present = [v for v in values if v is not None]
    counts, nulls = Counter(present), len(values) - len(present)
    return {
        "equal": [None if v is None else v == present[0] for v in values],
        "member": [v is not None and v == present[0] for v in values],
        "groups": [[token(k), counts[k]] for k in sorted(counts)]
        + ([[None, nulls]] if nulls else []),
        "unique": [token(v) for v in dict.fromkeys(values)],
        "sorted": sorted(
            range(len(values)),
            key=lambda i: (
                values[i] is None,
                present[0] if values[i] is None else values[i],
            ),
        ),
        "merged": sum(n * n for n in counts.values()) + nulls * nulls,
        "null": [v is None for v in values],
    }


def frame_inputs():
    """The labels and producer rows of each matrix batch, without PyArrow."""
    p = _product()
    return {
        "numeric": ([n for n, *_ in NUMERIC], NUMERIC_ROWS["values"]),
        "scalar": (list(p.SCALAR_LABELS), p.scalar_rows("postgres")),
        "text32": (list(p.TEXT_LABELS), p.text_rows("postgres")),
        "text64": (list(p.TEXT_LABELS), p.text_rows("postgres")),
        "decimal": (
            list(p.DECIMAL_LABELS[:2]),
            p.decimal_rows("postgres", 38, 2),
        ),
        "date": (["event_date"], DATE_ROWS),
        "timestamp": (
            ["selected_0", "selected_1"],
            [row[:2] for row in p.temporal_rows("postgres")],
        ),
        **relief_inputs(p),
    }


def relief_inputs(p):
    """The labels and producer rows of RELIEF's batches as to_pandas holds them:
    a UUID as its 16 bytes and a container as the records of its children."""
    n = _helper("_pietto_results_nested")

    def held(value):
        return value.bytes if isinstance(value, UUID) else value

    def records(rows, labels):
        return [
            [
                key,
                None
                if box is None
                else [dict(zip(labels, map(held, r), strict=True)) for r in zip(*box)],
            ]
            for key, box in rows
        ]

    temporal = [[held(v) for v in row] for row in p.temporal_rows("postgres")]
    return {
        "temporal": (list(p.TEMPORAL_LABELS[:4]), temporal),
        "wide": (list(p.DECIMAL_LABELS[:2]), p.decimal_rows("postgres", 65, 30)),
        "nested": (["renamed", "c"], records(n.ROWS, ("i", "b", "t"))),
        "nested_uuid": (["renamed", "c"], records(NESTED_UUID_ROWS, ("i", "u"))),
        "nested_kinds": (
            ["renamed", "c"],
            records(NESTED_KINDS_ROWS, tuple(label for label, *_ in KIDS)),
        ),
        "nested_wide": (["renamed", "c"], records(NESTED_WIDE_ROWS, ("d",))),
        "outer": (["id", "retained"], records(OUTER_ROWS, ("id",))),
    }


def _exact(actual, expected):
    return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(
        expected, sort_keys=True, allow_nan=False
    )


def verify_report(report, *, cell, python, checkout):
    """Refuse every report that is not this cell's complete, exact witness."""
    if cell not in CELLS or python not in ("3.12", "3.13"):
        raise ValueError("interop cell")
    if (
        type(report) is not dict
        or set(report) != {"format", "context", "cell", "versions", "origins", "cases"}
        or report["format"] != FORMAT
        or report["cell"] != cell
        or type(report["context"]) is not dict
        or report["context"].get("python") != python
        or report["context"].get("checkout") != checkout
    ):
        raise ValueError("interop report identity")
    versions = {"pyarrow": PYARROW} | {t: PINS[t] for t in CELLS[cell] if t in PINS}
    if report["versions"] != versions:
        raise ValueError("interop target versions")
    origins = report["origins"]
    if (
        type(origins) is not dict
        or "pietto.interop" not in origins
        or any(
            type(path) is not str or "/site-packages/pietto/" not in path
            for path in origins.values()
        )
    ):
        raise ValueError("interop installed origins")
    cases = report["cases"]
    if type(cases) is not dict or list(cases) != list(cases_of(cell)):
        raise ValueError("interop case denominator")
    expected = expected_common(cell)
    if cell == "numpy":
        expected |= expected_numpy()
    elif cell == "scipy":
        expected |= expected_scipy()
    elif cell == "matplotlib":
        expected |= expected_plots()
    elif cell != "arrow":
        expected |= expected_frames(cell, frame_inputs())
    for name in cases_of(cell):
        if not _exact(cases[name], expected[name]):
            raise ValueError(f"interop case {name}")


# ---------------------------------------------------------------- NumPy

NUMPY = (
    "matrix",
    "signed_zero",
    "empty",
    "copy",
    "labels",
    "refusals",
    "drift",
    "inert",
    "after_close",
    "nullable",
)
# The numeric batch's non-nullable fields and the dtype to_numpy keeps.
NUMPY_FIELDS = ((0, "int64"), (1, "float64"), (2, "bool"), (4, "int16"), (5, "int32"))
# Each width's bounds, ±0 and a repeated row; nullable field 3 holds no null.
NUMPY_ROWS = [
    [-(2**63), 0.0, True, 1, -(2**15), -(2**31)],
    [2**63 - 1, -0.0, False, 2, 2**15 - 1, 2**31 - 1],
    [0, 0.5, True, 3, 0, 0],
    [2**63 - 1, -0.0, False, 2, 2**15 - 1, 2**31 - 1],
]
NUMPY_ADMITS = "to_numpy admits only Int, Bool or Float fields"
# Nullable Float field 5 of the scalar batch: signed zeros on both sides of a
# null, a repeated -0.0, the least subnormal and the largest finite value.
MAYBE_RATIO = [
    -0.0,
    None,
    0.0,
    float.fromhex("0x0.0000000000001p-1022"),
    None,
    -0.0,
    float.fromhex("0x1.fffffffffffffp+1023"),
]


def numpy_cases(fx):
    interop: Any = importlib.import_module("pietto.interop")
    numpy: Any = importlib.import_module("numpy")
    pa: Any = importlib.import_module("pyarrow")

    def values(array):
        return [token(value) for value in array.tolist()]

    binding = fx["numeric"][0]
    item = batch(binding, NUMPY_ROWS)
    observations: dict[str, Any] = {}
    converted = [(o, interop.to_numpy(item, o)) for o, _ in NUMPY_FIELDS]
    observations["matrix"] = {
        "fields": [[o, str(a.dtype), list(a.shape), values(a)] for o, a in converted],
        "open": not item.closed,
    }
    observations["signed_zero"] = numpy.signbit(interop.to_numpy(item, 1)).tolist()
    hollow = batch(binding, [])
    observations["empty"] = [
        [o, str(a.dtype), list(a.shape)]
        for o, a in ((o, interop.to_numpy(hollow, o)) for o, _ in NUMPY_FIELDS)
    ]

    # The copy owns its memory: no buffer of the batch, and a write to it
    # leaves the next conversion of the batch unchanged.
    observations["copy"] = []
    for ordinal, _dtype in NUMPY_FIELDS:
        array = interop.to_numpy(item, ordinal)
        stored = pa.record_batch(item).column(ordinal).buffers()[1]
        flags = [
            array.flags.writeable,
            array.flags.owndata,
            array.base is None,
            numpy.shares_memory(array, numpy.frombuffer(stored, dtype=numpy.uint8)),
        ]
        array[0] = array[1]
        fresh = values(interop.to_numpy(item, ordinal))
        observations["copy"].append([ordinal, *flags, values(array), fresh])

    # Fields 0 and 1 share one label; the ordinal alone picks the field.
    labelled = batch(*fx["labels"])
    observations["labels"] = [values(interop.to_numpy(labelled, o)) for o in (0, 1)]

    text, decimal, timestamp = (
        batch(*fx[n]) for n in ("text64", "decimal", "timestamp")
    )
    finite, temporal, nested = (batch(*fx[n]) for n in ("finite", "temporal", "nested"))
    observations["refusals"] = [
        # Nullable in the schema, though this batch holds no null.
        refusal(lambda: interop.to_numpy(item, 3), item),
        refusal(lambda: interop.to_numpy(text, 0), text),
        refusal(lambda: interop.to_numpy(decimal, 0), decimal),
        refusal(lambda: interop.to_numpy(timestamp, 0), timestamp),
        refusal(lambda: interop.to_numpy(finite, 8), finite),
        refusal(lambda: interop.to_numpy(temporal, 2), temporal),
        refusal(lambda: interop.to_numpy(nested, 1), nested),
    ]

    # Pin drift: PyArrow hands over another dtype than the field's, of another
    # kind as for an Int that holds a null, or of the same kind and another
    # width; it is refused, never cast back. The witness widens the input of
    # numpy.array, so it needs the copy to go through numpy.array: a copy made
    # another way fails here, not in the adapter.
    built = numpy.array

    def widened(dtype):
        def build(source, *args, **kwargs):
            return built(numpy.asarray(source).astype(dtype), *args, **kwargs)

        return build

    observations["drift"] = []
    for ordinal, dtype in ((0, numpy.float64), (4, numpy.int64)):
        with mock.patch.object(numpy, "array", widened(dtype)):
            observations["drift"].append(
                refusal(lambda: interop.to_numpy(item, ordinal), item)
            )

    observations["inert"] = exports(item, lambda: values(interop.to_numpy(item, 0)))

    kept = batch(binding, NUMPY_ROWS)
    array = interop.to_numpy(kept, 1)
    kept.close()
    del kept
    gc.collect()
    observations["after_close"] = values(array)

    # PL.47's nullable Float: each null becomes NaN, here reported as None,
    # and each value keeps its bits, whether or not the batch holds a null.
    # Nullable Int and Bool fields stay refused.
    def nulls(array):
        return [None if math.isnan(v) else token(v) for v in array.tolist()]

    scalar, rows = fx["scalar"]
    held = batch(scalar, [r[:5] + [v] for r, v in zip(rows, MAYBE_RATIO, strict=True)])
    full = batch(scalar, [r[:5] + [r[4]] for r in rows])
    observations["nullable"] = [
        [str(a.dtype), list(a.shape), nulls(a)]
        for a in (interop.to_numpy(held, 5), interop.to_numpy(full, 5))
    ]
    array = interop.to_numpy(batch(scalar, []), 5)
    observations["nullable"].append([str(array.dtype), list(array.shape)])
    array = interop.to_numpy(held, 5)
    stored = pa.record_batch(held).column(5).buffers()[1]
    flags = [
        array.flags.writeable,
        array.flags.owndata,
        array.base is None,
        numpy.shares_memory(array, numpy.frombuffer(stored, dtype=numpy.uint8)),
    ]
    array[1] = array[0]
    fresh = nulls(interop.to_numpy(held, 5))
    observations["nullable"].append([*flags, nulls(array), fresh, held.closed])
    array = interop.to_numpy(held, 5)
    held.close()
    del held
    gc.collect()
    observations["nullable"] += [
        nulls(array),
        refusal(lambda: interop.to_numpy(full, 1), full),
        refusal(lambda: interop.to_numpy(full, 3), full),
    ]
    return {f"numpy_{key}": value for key, value in observations.items()}


def expected_numpy():
    """NumPy oracles from the producer input rows, never from the target output."""

    def column(rows, ordinal):
        return [token(row[ordinal]) for row in rows]

    rows = NUMPY_ROWS
    written = [rows[1], *rows[1:]]
    refused = "to_numpy: column field %s has Arrow type %s; " + NUMPY_ADMITS + "%s"
    ratio = [row[4] for row in _product().scalar_rows("postgres")]
    expected = {
        "matrix": {
            "fields": [
                [o, dtype, [len(rows)], column(rows, o)] for o, dtype in NUMPY_FIELDS
            ],
            "open": True,
        },
        "signed_zero": [math.copysign(1.0, row[1]) < 0 for row in rows],
        "empty": [[o, dtype, [0]] for o, dtype in NUMPY_FIELDS],
        "copy": [
            [o, True, True, True, False, column(written, o), column(rows, o)]
            for o, _ in NUMPY_FIELDS
        ],
        "labels": [column(NUMERIC_ROWS["values"], o) for o in (0, 1)],
        "refusals": [
            _value_error(f"to_numpy: column field 3 ('maybe') {COALESCE}"),
            _value_error(refused % ("0 ('renamed')", "large_string", TO_FRAME)),
            _value_error(
                refused
                % (
                    f"0 ({_product().DECIMAL_LABELS[0]!r})",
                    "decimal128(38, 2)",
                    TO_FRAME,
                )
            ),
            _value_error(refused % ("0 ('selected_0')", "timestamp[us]", TO_FRAME)),
            _value_error(
                refused
                % ("8 ('selected_wide_amount')", "decimal256(65, 30)", TO_PANDAS)
            ),
            _value_error(
                refused % ("2 ('key_value')", "extension<arrow.uuid>", TO_FRAME)
            ),
            _value_error(refused % ("1 ('c')", NESTED, TO_FRAME)),
        ],
        "drift": [
            _value_error(
                f"to_numpy: field {changed}; to_numpy never returns a changed type;"
                f" {pinned('numpy')}"
            )
            for changed in (
                "0 ('i64') became float64 instead of int64",
                "4 ('i16') became int64 instead of int16",
            )
        ],
        "inert": [column(rows, 0), {"array": 1, "schema": 0}, False, len(rows), []],
        "after_close": column(rows, 1),
        "nullable": [
            ["float64", [len(MAYBE_RATIO)], [token(v) for v in MAYBE_RATIO]],
            ["float64", [len(ratio)], [token(v) for v in ratio]],
            ["float64", [0]],
            [
                True,
                True,
                True,
                False,
                [token(v) for v in MAYBE_RATIO[:1] * 2 + MAYBE_RATIO[2:]],
                [token(v) for v in MAYBE_RATIO],
                False,
            ],
            [token(v) for v in MAYBE_RATIO],
            _value_error(f"to_numpy: column field 1 ('maybe_integer') {COALESCE}"),
            _value_error(f"to_numpy: column field 3 ('maybe_flag') {COALESCE}"),
        ],
    }
    return {f"numpy_{key}": value for key, value in expected.items()}


# ---------------------------------------------------------------- SciPy

SCIPY = (
    "matrix",
    "permutations",
    "empty",
    "bound",
    "drift",
    "inert",
    "after_close",
    "float_values",
)
I64 = 1 << 63
# Numeric-fixture rows (i64, f64, flag, maybe, i16, i32), out of canonical
# order, with explicit zeros and the extremes of each value width.
SCIPY_ROWS = {
    "int64": [
        [0, 0.0, True, None, 2, 1],
        [I64 - 1, 0.5, False, 7, 0, 3],
        [0, 0.0, True, None, 1, 0],
        [-I64, 1.0, True, None, 0, 0],
        [5, 0.0, False, None, 2, 0],
    ],
    "int16": [
        [1, 0.0, True, None, -(1 << 15), 2],
        [0, 0.0, True, None, (1 << 15) - 1, 2],
        [1, 0.0, True, None, 0, 0],
    ],
    "int32": [
        [2, 0.0, True, None, 1, -(1 << 31)],
        [0, 0.0, True, None, 0, (1 << 31) - 1],
        [2, 0.0, True, None, 0, 0],
    ],
}
# The row, column and value ordinals and the shape of each width's call.
SCIPY_CALLS = {
    "int64": (4, 5, 0, (4, 5)),
    "int16": (0, 5, 4, (2, 3)),
    "int32": (0, 4, 5, (3, 2)),
}


def csr(sparse, matrix):
    return {
        "type": [type(matrix).__name__, type(matrix) is sparse.csr_array],
        "shape": list(matrix.shape),
        "nnz": int(matrix.nnz),
        "dtypes": [str(a.dtype) for a in (matrix.indices, matrix.indptr, matrix.data)],
        "canonical": bool(matrix.has_canonical_format),
        "indptr": matrix.indptr.tolist(),
        "indices": matrix.indices.tolist(),
        "data": matrix.data.tolist(),
    }


def scipy_cases(fx):
    interop: Any = importlib.import_module("pietto.interop")
    sparse: Any = importlib.import_module("scipy.sparse")

    binding = fx["numeric"][0]
    observations: dict[str, Any] = {"matrix": {}}
    for width, rows in SCIPY_ROWS.items():
        item = batch(binding, rows)
        matrix = interop.to_scipy_csr(item, *SCIPY_CALLS[width])
        observations["matrix"][width] = [csr(sparse, matrix), item.closed]

    seen: dict[str, int] = {}
    for order in itertools.permutations(SCIPY_ROWS["int64"]):
        matrix = interop.to_scipy_csr(
            batch(binding, list(order)), *SCIPY_CALLS["int64"]
        )
        key = json.dumps(csr(sparse, matrix), sort_keys=True)
        seen[key] = seen.get(key, 0) + 1
    observations["permutations"] = [[json.loads(k), n] for k, n in seen.items()]

    observations["empty"] = [
        csr(sparse, interop.to_scipy_csr(batch(binding, []), *call[:3], shape))
        for call in SCIPY_CALLS.values()
        for shape in ((0, 0), call[3])
    ]
    item = batch(binding, SCIPY_ROWS["int16"])
    observations["bound"] = csr(
        sparse, interop.to_scipy_csr(item, *SCIPY_CALLS["int16"][:3], (4096, 4096))
    )

    # Pin drift: SciPy hands back another type, shape, index, index-pointer or
    # data dtype, entry count or order than the canonical csr_array; the
    # adapter refuses it. The shape drifts one dimension at a time and the
    # dtypes one array at a time, so a check of any one of them alone fails.
    base = sparse.csr_array

    def matrix_type(arg, shape):
        return sparse.csr_matrix(arg, shape=shape)

    def reshaped(rows, columns):
        class Reshaped(base):
            def __init__(self, arg, shape):
                super().__init__(arg, shape=(shape[0] + rows, shape[1] + columns))

        return Reshaped

    def retyped(part, dtype):
        class Retyped(base):
            def __init__(self, arg, shape):
                super().__init__(arg, shape=shape)
                setattr(self, part, getattr(self, part).astype(dtype))

        return Retyped

    class Pruned(base):
        def __init__(self, arg, shape):
            super().__init__(arg, shape=shape)
            self.eliminate_zeros()

    class Unsorted(base):
        def __init__(self, arg, shape):
            built = base(arg, shape=shape)
            indices, values = built.indices.copy(), built.data.copy()
            indices[:2], values[:2] = indices[1::-1].copy(), values[1::-1].copy()
            super().__init__((values, indices, built.indptr), shape=shape)

    drifted = batch(binding, SCIPY_ROWS["int64"])
    observations["drift"] = []
    for drift in (
        matrix_type,
        reshaped(1, 0),
        reshaped(0, 1),
        retyped("indices", "int64"),
        retyped("indptr", "int64"),
        retyped("data", "int32"),
        Pruned,
        Unsorted,
    ):
        with mock.patch.object(sparse, "csr_array", drift):
            observations["drift"].append(
                refusal(
                    lambda: interop.to_scipy_csr(drifted, *SCIPY_CALLS["int64"]),
                    drifted,
                )
            )

    counted = batch(binding, SCIPY_ROWS["int64"])
    observations["inert"] = exports(
        counted,
        lambda: type(interop.to_scipy_csr(counted, *SCIPY_CALLS["int64"])).__name__,
    )

    item = batch(binding, SCIPY_ROWS["int64"])
    matrix = interop.to_scipy_csr(item, *SCIPY_CALLS["int64"])
    item.close()
    del item
    gc.collect()
    observations["after_close"] = [csr(sparse, matrix), matrix.toarray().tolist()]

    # PL.47's Float value cell, refused while to_scipy_csr admits only Int values.
    floats = batch(binding, SCIPY_ROWS["int64"])
    observations["float_values"] = [
        refusal(lambda: interop.to_scipy_csr(floats, 4, 5, 1, (4, 5)), floats)
    ]
    return {f"scipy_{key}": value for key, value in observations.items()}


def csr_oracle(width, rows=None, shape=None):
    """The canonical CSR of a width's records: entries sorted by coordinate."""
    row, column, value, called = SCIPY_CALLS[width]
    rows = SCIPY_ROWS[width] if rows is None else rows
    shape = called if shape is None else shape
    entries = sorted((r[row], r[column], r[value]) for r in rows)
    indptr = [0] * (shape[0] + 1)
    for i, _c, _v in entries:
        indptr[i + 1] += 1
    for i in range(shape[0]):
        indptr[i + 1] += indptr[i]
    return {
        "type": ["csr_array", True],
        "shape": list(shape),
        "nnz": len(entries),
        "dtypes": ["int32", "int32", width],
        "canonical": True,
        "indptr": indptr,
        "indices": [c for _r, c, _v in entries],
        "data": [v for _r, _c, v in entries],
    }


def expected_scipy():
    """CSR oracles from the producer input rows, never from the target output."""
    row, column, value, shape = SCIPY_CALLS["int64"]
    dense = [[0] * shape[1] for _ in range(shape[0])]
    for r in SCIPY_ROWS["int64"]:
        dense[r[row]][r[column]] = r[value]
    unstored = _value_error(
        f"to_scipy_csr: scipy did not store the {len(SCIPY_ROWS['int64'])} records"
        f" once each in canonical order; {pinned('scipy')}"
    )

    def retyped(indices, pointers, data):
        return _value_error(
            f"to_scipy_csr: scipy built {indices} indices, {pointers} index pointers"
            f" and {data} data instead of int32, int32 and int64; to_scipy_csr never"
            f" returns a changed type; {pinned('scipy')}"
        )

    return {
        "scipy_matrix": {width: [csr_oracle(width), False] for width in SCIPY_ROWS},
        "scipy_permutations": [
            [csr_oracle("int64"), math.factorial(len(SCIPY_ROWS["int64"]))]
        ],
        "scipy_empty": [
            csr_oracle(width, [], hollow)
            for width, call in SCIPY_CALLS.items()
            for hollow in ((0, 0), call[3])
        ],
        "scipy_bound": csr_oracle("int16", shape=(4096, 4096)),
        "scipy_drift": [
            _value_error(
                "to_scipy_csr: scipy built a csr_matrix instead of a csr_array;"
                f" {pinned('scipy')}"
            ),
            _value_error(
                f"to_scipy_csr: scipy built the shape ({shape[0] + 1}, {shape[1]})"
                f" instead of {shape}; {pinned('scipy')}"
            ),
            _value_error(
                f"to_scipy_csr: scipy built the shape ({shape[0]}, {shape[1] + 1})"
                f" instead of {shape}; {pinned('scipy')}"
            ),
            retyped("int64", "int32", "int64"),
            retyped("int32", "int64", "int64"),
            retyped("int32", "int32", "int32"),
            unstored,
            unstored,
        ],
        "scipy_inert": [
            "csr_array",
            {"array": 1, "schema": 0},
            False,
            len(SCIPY_ROWS["int64"]),
            [],
        ],
        "scipy_after_close": [csr_oracle("int64"), dense],
        "scipy_float_values": [
            _value_error(
                "to_scipy_csr: value field 1 ('f64') has Arrow type double;"
                f" to_scipy_csr admits only Int fields{TO_FRAME}"
            )
        ],
    }


# ---------------------------------------------------------------- Matplotlib

PLOT = ("draw", "empty", "order", "refusals", "inert", "after_close", "nullable")
# NUMERIC rows with the ±2**53 bound, values that float32 would round (2**53 - 1,
# 0.1, the least subnormal), -0.0, the Int16 and Int32 bounds and a repeat.
PLOT_ROWS = [
    [B53 - 1, 0.1, True, None, -(2**15), 2**31 - 1],
    [B53, -0.0, False, 7, 2**15 - 1, -(2**31)],
    [-B53, 5e-324, True, None, 0, 0],
    [B53 - 1, 0.1, True, None, -(2**15), 2**31 - 1],
]
# Point order follows input order: these rows are reversed, with a repeat.
PLOT_ORDER = PLOT_ROWS[::-1] + [PLOT_ROWS[1]]
# Nullable field 3 with a null before a value beyond 2**53: the null is
# skipped, and the value keeps its record's number.
PLOT_GAP = [[0, 0.0, True, None, 0, 0], [0, 0.0, True, B53 + 1, 0, 0]]
# Numeric rows whose nullable field 3 holds no null, or only a null, and scalar
# rows whose nullable Float field 5 holds nulls, -0.0 and the least subnormal.
PLOT_NULLS = {
    "full": [[0, 0.5, True, 7, 0, 1]],
    "lone": [[0, 0.5, True, None, 0, 1]],
    "ratio": [
        [0, None, False, None, 0.1, None],
        [1, 2, True, True, -0.0, 5e-324],
        [2, None, False, None, 2.5, -0.0],
        [0, None, False, None, 0.1, None],
    ],
}
# Matplotlib 3.11.2's font cache, which docs/interop.md names.
FONT_CACHE = "fontlist-v3.11.0.json"
# Any of these modules would mean that pyplot or a backend was selected.
SELECTED = ("matplotlib.pyplot", "matplotlib.backends.backend_")


def axes():
    """A new Axes on a new Figure, without pyplot."""
    return importlib.import_module("matplotlib.figure").Figure().add_subplot()


def drawn(artist, ax):
    """The artist's type, its Axes and Axes list, and its points' dtype, shape
    and values in point order."""
    numpy: Any = importlib.import_module("numpy")
    line = type(artist).__name__ == "Line2D"
    data = artist.get_xydata() if line else artist.get_offsets()
    return [
        type(artist).__name__,
        artist.axes is ax,
        artist in (ax.lines if line else ax.collections),
        str(numpy.asarray(data).dtype),
        list(numpy.shape(data)),
        [[token(x), token(y)] for x, y in data.tolist()],
    ]


def plot_cases(fx):
    interop: Any = importlib.import_module("pietto.interop")
    matplotlib: Any = importlib.import_module("matplotlib")
    figure_type = importlib.import_module("matplotlib.figure").Figure
    config = Path(matplotlib.get_configdir())
    cached = sorted(path.name for path in config.iterdir())
    backend = dict.__getitem__(matplotlib.rcParams, "backend")
    observations: dict[str, Any] = {}

    # What each call hands Matplotlib: its positional arguments and keywords.
    axes_type = importlib.import_module("matplotlib.axes").Axes
    passed = []

    def recorded(method):
        original = getattr(axes_type, method)

        def record(self, *args, **kwargs):
            shown = [[type(a).__name__, str(getattr(a, "dtype", None))] for a in args]
            passed.append([method, shown, sorted(kwargs)])
            return original(self, *args, **kwargs)

        return mock.patch.object(axes_type, method, record)

    # The Figure's current Axes is the other one: only the Axes passed is drawn on.
    figure = figure_type()
    first, current = figure.add_subplot(1, 2, 1), figure.add_subplot(1, 2, 2)
    item = batch(fx["numeric"][0], PLOT_ROWS)
    with recorded("plot"), recorded("scatter"):
        artists = (
            interop.plot_line(item, 0, 1, ax=first),
            interop.plot_scatter(item, 4, 5, ax=first),
            interop.plot_line(item, 1, 0, ax=first),
        )
    observations["draw"] = [
        *(drawn(artist, first) for artist in artists),
        [[len(a.lines), len(a.collections)] for a in (first, current)],
        figure.gca() is current,
        item.closed,
        passed,
    ]

    hollow, ax = batch(fx["numeric"][0], []), axes()
    observations["empty"] = [
        drawn(interop.plot_line(hollow, 0, 1, ax=ax), ax),
        drawn(interop.plot_scatter(hollow, 5, 4, ax=ax), ax),
        drawn(interop.plot_scatter(hollow, 3, 1, ax=ax), ax),
    ]

    ordered, ax = batch(fx["numeric"][0], PLOT_ORDER), axes()
    observations["order"] = [
        drawn(interop.plot_line(ordered, 0, 1, ax=ax), ax),
        drawn(interop.plot_scatter(ordered, 0, 1, ax=ax), ax),
    ]

    figure = figure_type()
    ax = figure.add_subplot()
    children = len(ax.get_children())
    numeric, closed = batch(*fx["numeric"]), batch(*fx["numeric"])
    closed.close()
    above = batch(fx["numeric"][0], NUMERIC_ROWS["above"])
    gap = batch(fx["numeric"][0], PLOT_GAP)
    observations["refusals"] = [
        refusal(lambda: interop.plot_line(numeric, 0, 1, ax=object()), numeric),
        refusal(lambda: interop.plot_scatter(numeric, 0, 1, ax=figure), numeric),
        refusal(lambda: interop.plot_line(numeric, True, 1, ax=ax), numeric),
        # The Axes is checked before the one read of the batch.
        refusal(lambda: interop.plot_line(closed, 0, 1, ax=None), closed),
        refusal(lambda: interop.plot_scatter(closed, 0, 1, ax=ax), closed),
        refusal(lambda: interop.plot_line(numeric, 0, 6, ax=ax), numeric),
        refusal(lambda: interop.plot_scatter(numeric, 2, 1, ax=ax), numeric),
        refusal(lambda: interop.plot_scatter(above, 1, 0, ax=ax), above),
        refusal(lambda: interop.plot_line(gap, 3, 1, ax=ax), gap),
        [len(ax.lines), len(ax.collections), len(ax.get_children()) - children],
    ]

    # PL.47's nullable Int and Float cells, on the line and the scatter.
    ax = axes()
    full = batch(fx["numeric"][0], PLOT_NULLS["full"])
    lone = batch(fx["numeric"][0], PLOT_NULLS["lone"])
    ratio = batch(fx["scalar"][0], PLOT_NULLS["ratio"])
    observations["nullable"] = [
        drawn(interop.plot_line(numeric, 3, 1, ax=ax), ax),
        drawn(interop.plot_scatter(numeric, 1, 3, ax=ax), ax),
        drawn(interop.plot_line(ratio, 5, 4, ax=ax), ax),
        drawn(interop.plot_scatter(ratio, 4, 5, ax=ax), ax),
        drawn(interop.plot_scatter(full, 0, 3, ax=ax), ax),
        drawn(interop.plot_line(lone, 3, 1, ax=ax), ax),
    ]

    counted, ax = batch(*fx["numeric"]), axes()
    observations["inert"] = []
    for name, x, y in (("plot_line", 0, 1), ("plot_scatter", 5, 4)):
        plot = getattr(interop, name)
        outcome = exports(counted, lambda: type(plot(counted, x, y, ax=ax)).__name__)
        observations["inert"].append([name, *outcome])
    observations["inert"] += [
        sorted(m for m in sys.modules if m.startswith(SELECTED)),
        dict.__getitem__(matplotlib.rcParams, "backend") is backend,
        config == Path(os.environ["MPLCONFIGDIR"]).resolve(),
        [cached, sorted(path.name for path in config.iterdir())],
    ]

    item, ax = batch(fx["numeric"][0], PLOT_ROWS), axes()
    artists = (
        interop.plot_line(item, 0, 1, ax=ax),
        interop.plot_scatter(item, 5, 0, ax=ax),
        interop.plot_line(item, 3, 0, ax=ax),
    )
    item.close()
    del item
    gc.collect()
    observations["after_close"] = [drawn(artist, ax) for artist in artists]
    return {f"matplotlib_{key}": value for key, value in observations.items()}


def plotted(kind, rows, x, y):
    """What drawn() gives for an artist of the producer rows' fields x and y: a
    null is NaN on the line, and the scatter masks the whole record."""

    def point(row):
        if kind == "PathCollection" and None in (row[x], row[y]):
            return [None, None]
        return [token(float("nan" if v is None else v)) for v in (row[x], row[y])]

    return [kind, True, True, "float64", [len(rows), 2], [point(r) for r in rows]]


def expected_plots():
    """Plot oracles from the producer input rows, never from Matplotlib's output."""
    values = NUMERIC_ROWS["values"]
    plot = "admits only Int or Float fields"
    not_axes = "ax must be a matplotlib.axes.Axes, not"
    arrays = [["ndarray", "float64"], ["ndarray", "float64"]]
    return {
        "matplotlib_draw": [
            plotted("Line2D", PLOT_ROWS, 0, 1),
            plotted("PathCollection", PLOT_ROWS, 4, 5),
            plotted("Line2D", PLOT_ROWS, 1, 0),
            [[2, 1], [0, 0]],
            True,
            False,
            [[method, arrays, []] for method in ("plot", "scatter", "plot")],
        ],
        "matplotlib_empty": [
            plotted("Line2D", [], 0, 1),
            plotted("PathCollection", [], 5, 4),
            plotted("PathCollection", [], 3, 1),
        ],
        "matplotlib_order": [
            plotted("Line2D", PLOT_ORDER, 0, 1),
            plotted("PathCollection", PLOT_ORDER, 0, 1),
        ],
        "matplotlib_refusals": [
            _type_error(f"plot_line: {not_axes} object"),
            _type_error(f"plot_scatter: {not_axes} Figure"),
            _type_error("plot_line: x must be an int field ordinal, not bool"),
            _type_error(f"plot_line: {not_axes} NoneType", True),
            ["HandleMisuse", "PIE-R4002", "PUBLIC_BATCH_CLOSED", True],
            _value_error(
                "plot_line: y 6 is not a field ordinal of this batch (0 <= ordinal < 6)"
            ),
            _value_error(
                "plot_scatter: x field 2 ('flag') has Arrow type bool;"
                f" plot_scatter {plot}{AS_INT}"
            ),
            _value_error(
                f"plot_scatter: y field 0 ('i64') has {B53 + 1} in record 1, {FLOAT}"
            ),
            _value_error(
                f"plot_line: x field 3 ('maybe') has {B53 + 1} in record 1, {FLOAT}"
            ),
            [0, 0, 0],
        ],
        "matplotlib_inert": [
            [name, kind, {"array": 1, "schema": 0}, False, len(values), []]
            for name, kind in (
                ("plot_line", "Line2D"),
                ("plot_scatter", "PathCollection"),
            )
        ]
        + [
            [],
            True,
            True,
            [[FONT_CACHE], [FONT_CACHE]],
        ],
        "matplotlib_after_close": [
            plotted("Line2D", PLOT_ROWS, 0, 1),
            plotted("PathCollection", PLOT_ROWS, 5, 0),
            plotted("Line2D", PLOT_ROWS, 3, 0),
        ],
        "matplotlib_nullable": [
            plotted("Line2D", values, 3, 1),
            plotted("PathCollection", values, 1, 3),
            plotted("Line2D", PLOT_NULLS["ratio"], 5, 4),
            plotted("PathCollection", PLOT_NULLS["ratio"], 4, 5),
            plotted("PathCollection", PLOT_NULLS["full"], 0, 3),
            plotted("Line2D", PLOT_NULLS["lone"], 3, 1),
        ],
    }


# ---------------------------------------------------------------- main


def _environment(cell):
    present = tuple(t for t in PINS if importlib.util.find_spec(t) is not None)
    wanted = tuple(t for t in PINS if t in CELLS[cell])
    if present != wanted:
        raise SystemExit(f"cell {cell} holds targets {present}, not {wanted}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", choices=tuple(CELLS), required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    assert not args.report.exists()
    _environment(args.cell)
    pa = importlib.import_module("pyarrow")
    if pa.__version__ != PYARROW:
        raise SystemExit(f"pyarrow {pa.__version__}, not {PYARROW}")
    context = {
        "checkout": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=args.repository, text=True
        ).strip(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "interop-local"),
        "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "python_version": platform.python_version(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with TemporaryDirectory(prefix="pietto-interop-") as scratch:
        cases = run_cases(args.cell, Path(scratch))
    cases = json.loads(json.dumps(cases, allow_nan=False))
    report = {
        "format": FORMAT,
        "context": context,
        "cell": args.cell,
        "versions": {"pyarrow": pa.__version__}
        | {t: importlib.metadata.version(t) for t in PINS if t in CELLS[args.cell]},
        "origins": {
            name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in sorted(sys.modules.items())
            if name == "pietto.interop" or name.startswith("pietto.interop.")
        },
        "cases": {name: cases[name] for name in cases_of(args.cell)},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=False, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    verify_report(
        deepcopy(report),
        cell=args.cell,
        python=context["python"],
        checkout=context["checkout"],
    )
    print(json.dumps({"cell": args.cell, "cases": len(report["cases"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
