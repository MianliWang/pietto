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

FORMAT = "pietto.result-product.v1"
PIN = "25.0.1"
BIG = 9007199254740993
LOW, HIGH = -(2**63), 2**63 - 1
PRODUCTS = ("project_result_contract", "project_result_binding", "project_arrow_result")
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


def build_source(directory, target):
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
    from pietto._project.project_sql_emission import emit_project_sql

    directory.mkdir()
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (directory / "main.pietto").write_text(source(target))
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
    assert set(results) == set(CASES)
    return results


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


def reject_report_damage(value, context, inputs):
    """Mutate actual saved-data observations, never fake an Arrow success."""
    mutations = (
        lambda v: v["context"].update(checkout="0" * 40),
        lambda v: v["context"].update(run_attempt=True),
        lambda v: v["context"].update(python="0.0"),
        lambda v: v.update(pin="0.0"),
        lambda v: v["inputs"].pop(next(iter(v["inputs"]))),
        lambda v: v["cases"].pop("owned"),
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
    assert rejected == 13
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
    print(
        f"installed product: {len(cases)} cases, {len(origins)} verified origins, PyArrow {PIN}"
    )


if __name__ == "__main__":
    main()
