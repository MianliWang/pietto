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
    assert set(results) == set(CASES)
    return results


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
        documents.append(value["cases"]["contract_documents"])
    if documents[0] != documents[1]:
        raise ValueError("cross-runtime complete canonical bytes differ")
    print("verified complete canonical document bytes across Python 3.12/3.13")


def reject_report_damage(value, context, inputs):
    """Mutate actual saved-data observations, never fake an Arrow success."""
    mutations = (
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
    assert rejected == 21
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
    print(
        f"installed product: {len(cases)} cases, {len(origins)} verified origins, PyArrow {PIN}"
    )


if __name__ == "__main__":
    main()
