"""Two-database differential of the generated opened forms.

For a seed of the narrow profile of tests/_pietto_harness_generated_forms.py,
whose forms PostgreSQL and MySQL projects both open, ``rows`` draws the rows of
the sources ``t`` and ``u`` within the emission contract's domains. The
campaign loads them into one owned PostgreSQL 18.6 and one owned MySQL 8.4.12
container, compiles the case with ``compile_query`` for each target and runs
it through the public ``execute()`` on ``postgres_rows`` and ``mysql_rows``.
``compare`` then holds the two public results to each other: the same Arrow
schema, a complete outcome, and the same rows as far as the language promises
them. The place of NULL in an order is the target's (docs/language.md), and
tied rows have no promised order, so the row sequence is compared only under a
total ORDER BY of keys that cannot be NULL; otherwise the rows are compared as
multisets, and a LIMIT that cuts an unpromised order is checked against the
same query without it: each engine's rows must be a sub-multiset of its own
complete result, and the complete results must be equal.

Importing this module opens nothing; only ``campaign`` starts containers, and
pytest checks the pure parts (tests/test_harness_generated_forms_differential.py).
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import random
import time
from typing import Any

import _pietto_harness_generated_forms as forms

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "narrow"  # MySQL projects open only the narrow profile's forms
TARGETS = ("postgres", "mysql")
ROUTES = {"postgres": "postgres_rows", "mysql": "mysql_rows"}
# The registered campaign: these narrow seeds and the digest of their cases
# and rows. A generator or row change registers a new campaign.
SEEDS = range(1000)
CORPUS_SHA256 = "e60e26559667321fbc2c47740b5720555d24f2e61c5a9464a80c24434328569e"
# Values within the contract's domains (Int -1000..1000, Text of at most 16
# characters with no padding), few enough that joins, groups and ties occur.
POOL: dict[str, tuple] = {
    "Int": (-1000, -2, 0, 1, 2, 7, 1000),
    "Float": (-2.5, 0.0, 0.1, 0.5, 2.0, 1e15),
    "Text": ("", "a", "a ", "A", "Zz", "zz", "é", "abcdefghijklmnop"),
    "Bool": (False, True),
    "Date": (
        date(1999, 12, 31),
        date(2000, 1, 1),
        date(2024, 2, 29),
        date(2031, 6, 15),
    ),
}
# Column definitions of the contract's storage per target
# (tests/_pietto_harness_generated_forms.py, _REPRESENTATION).
COLUMN = {
    "postgres": {
        "Int": "BIGINT",
        "Float": "DOUBLE PRECISION",
        "Text": 'TEXT COLLATE "C"',
        "Bool": "BOOLEAN",
        "Date": "DATE",
    },
    "mysql": {
        "Int": "BIGINT",
        "Float": "DOUBLE",
        "Text": "VARCHAR(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
        "Bool": "TINYINT",
        "Date": "DATE",
    },
}


def rows(case: forms.Case, source: str) -> list[tuple]:
    """The rows of ``source`` (``t`` or ``u``) for ``case``: unique ids, NULL
    only in optional fields, every value in the contract's domain."""
    rng = random.Random(f"rows:{case.profile}:{case.seed}:{source}")
    ids = rng.sample(range(-3, 9), rng.randint(0, 6))
    return [
        (key,)
        + tuple(
            None if nullable and rng.random() < 0.3 else rng.choice(POOL[kind])
            for _, kind, nullable in case.fields[1:]
        )
        for key in ids
    ]


def corpus_digest(seeds) -> str:
    digest = hashlib.sha256()
    for seed in seeds:
        case = forms.generate(seed, PROFILE)
        digest.update(repr((case, rows(case, "t"), rows(case, "u"))).encode() + b"\n")
    return digest.hexdigest()


def _literal(value: Any, target: str) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return (
            ("TRUE" if value else "FALSE") if target == "postgres" else str(int(value))
        )
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".17e")  # a binary64 literal that both parse exactly
    if isinstance(value, date):
        return f"DATE '{value.isoformat()}'"
    return "'" + value + "'"  # the Text pool holds no quote or backslash


def table_sql(case: forms.Case, target: str) -> list[str]:
    """Statements that replace ``app.t`` and ``app.u`` with the case's rows."""
    statements = ["DROP TABLE IF EXISTS app.t, app.u"]
    columns = ", ".join(
        f"{name} {COLUMN[target][kind]}{'' if nullable else ' NOT NULL'}"
        for name, kind, nullable in case.fields
    )
    for source in ("t", "u"):
        statements.append(f"CREATE TABLE app.{source} ({columns})")
        values = rows(case, source)
        if values:
            statements.append(
                f"INSERT INTO app.{source} VALUES "
                + ", ".join(
                    "(" + ", ".join(_literal(v, target) for v in row) + ")"
                    for row in values
                )
            )
    if target == "postgres":
        statements.append("GRANT SELECT ON app.t, app.u TO pietto_query")
    return statements


def promised(case: forms.Case) -> bool:
    """Whether the language promises the row sequence: a total ORDER BY whose
    keys cannot be NULL. Row forms end on ``t``'s unique ``id``; an aggregate
    is total over its groups when it orders every key; JOIN rows repeat
    ``t.id``."""
    keys = [key for key, _ in case.order]
    if any(forms.typed(case, ("field", key))[1] != forms.NON_NULL for key in keys):
        return False
    if case.form == "aggregate":
        return set(keys) == set(case.keys)
    return case.form == "row"


def encode(value: Any) -> Any:
    """A JSON value that keeps each public value exactly."""
    if isinstance(value, float):
        return {"float": value.hex()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    return value


def _bag(result: dict) -> Counter:
    return Counter(json.dumps(row, sort_keys=True) for row in result["rows"])


def compare(case: forms.Case, limited: dict, full: dict | None = None) -> list[str]:
    """Every disagreement of the two engines' public results for ``case``.

    ``limited`` and ``full`` map each target to its observation (``schema``,
    ``rows``, ``end``, ``count``) or to ``{"error": ...}``; ``full`` is the
    same query without its LIMIT, needed when the LIMIT cuts an order that
    the language does not promise."""
    problems = []
    runs = {"": limited, " without limit": full or {}}
    for label, observed in runs.items():
        for target in observed:
            result = observed[target]
            if "error" in result:
                problems.append(f"{target}{label}: {result['error']}")
            elif result["end"] != "COMPLETE" or result["count"] != len(result["rows"]):
                problems.append(
                    f"{target}{label}: {result['end']}, {result['count']} rows"
                )
    if problems:
        return problems
    pg, my = (limited[target] for target in TARGETS)
    if pg["schema"] != my["schema"]:
        problems.append(f"schema: {pg['schema']} != {my['schema']}")
    if promised(case):
        if pg["rows"] != my["rows"]:
            problems.append(f"rows in order: {pg['rows']} != {my['rows']}")
    elif case.limit is None:
        if _bag(pg) != _bag(my):
            problems.append(f"rows: {pg['rows']} != {my['rows']}")
    elif full is None:
        problems.append("an unpromised order under LIMIT needs the complete result")
    else:
        if _bag(full["postgres"]) != _bag(full["mysql"]):
            problems.append(
                f"rows without limit: {full['postgres']['rows']}"
                f" != {full['mysql']['rows']}"
            )
        for target in TARGETS:
            whole, part = _bag(full[target]), _bag(limited[target])
            if part - whole or part.total() != min(case.limit, whole.total()):
                problems.append(
                    f"{target}: {limited[target]['rows']} is not {case.limit}"
                    f" rows of {full[target]['rows']}"
                )
    return problems


# ---- the campaign: containers, compile_query and execute() ----


def _execute(query: Any, target: str, endpoint: tuple) -> dict:
    import importlib

    # PyArrow is optional: only the explicit campaign, with an execute extra,
    # reaches this, and the core environment never imports it.
    pa: Any = importlib.import_module("pyarrow")

    from pietto.execution import ExecutionError, ExecutionLimits, execute

    access, premise = endpoint
    try:
        batches = []
        with execute(
            query,
            route=ROUTES[target],
            access=access,
            premise=premise,
            limits=ExecutionLimits(seconds=60),
        ) as result:
            schema = pa.schema(result)
            for batch in result:
                with batch:
                    batches.append(pa.record_batch(batch))
    except ExecutionError as error:
        return {"error": [error.code, error.detail]}
    table = pa.Table.from_batches(batches, schema=schema)
    columns = [column.to_pylist() for column in table.columns]
    return {
        "schema": [[f.name, str(f.type), f.nullable] for f in schema],
        "rows": [[encode(value) for value in row] for row in zip(*columns)],
        "end": result.outcome.end,
        "count": result.outcome.rows,
    }


def _observe(case: forms.Case, root: Path, endpoints: dict) -> dict:
    from pietto.execution import CompileRejected, ExecutionError, compile_query

    observed = {}
    for target in TARGETS:
        project = root / target
        project.mkdir(parents=True)
        for name, text in forms.project_files(case, target).items():
            (project / name).write_text(text, encoding="utf-8")
        try:
            query = compile_query(
                project,
                module="main.pietto",
                kind="query",
                name="q",
                dialect=target,
                emission_contract="contract.json",
            )
        except (CompileRejected, ExecutionError) as error:
            observed[target] = {"error": ["compile_query", type(error).__name__]}
            continue
        observed[target] = _execute(query, target, endpoints[target])
    return observed


def _resource(target: str, directory: Path) -> Any:
    from _pietto_target_conformance_resources import Resources

    # engine-slot exports the held slot's suffix; containers carry it.
    suffix = os.environ.get(f"PIETTO_ENGINE_SLOT_{target.upper()}_SUFFIX")
    if not suffix:
        raise ValueError(f"run under engine-slot {target}")
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    directory.mkdir(mode=0o700)
    resource = Resources(target, pins["targets"][target], directory)
    resource.name += suffix
    resource.network_name = resource.name + "-network"
    return resource


def _prepare(resource: Any) -> tuple:
    """Acquire the container, the reader role and the ``app`` namespace, and
    return the public access and deployment premise of its route."""
    from _pietto_execution_api_mysql_native import _configure_tls
    from _pietto_execution_source_assurance_probe import manager

    from pietto.execution import (
        MySQLAccess,
        MySQLDeploymentPremise,
        PostgresAccess,
        PostgresDeploymentPremise,
    )

    resource.acquire()
    password = resource._passwords[1]
    if resource.target == "postgres":
        manager(resource, "CREATE SCHEMA app")
        for sql, _ in resource.role_statements():
            manager(resource, sql)
        manager(resource, "GRANT USAGE ON SCHEMA app TO pietto_query")
        return (
            PostgresAccess(
                "127.0.0.1",
                resource.port,
                "phase66",
                "pietto_query",
                password,
                "disable",
            ),
            PostgresDeploymentPremise(schemas=("app", "pg_catalog")),
        )
    _configure_tls(resource)
    manager(
        resource,
        "CREATE DATABASE app CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
    )
    for sql, _ in resource.role_statements():
        manager(resource, sql)
    for grant in (
        "app.*",
        "performance_schema.threads",
        "performance_schema.events_transactions_current",
    ):
        manager(resource, f"GRANT SELECT ON {grant} TO 'pietto_query'@'%'")
    return (
        MySQLAccess(
            "localhost",
            resource.port,
            "app",
            "pietto_query",
            password,
            str(resource.ca_path),
            "pietto_query@%",
        ),
        MySQLDeploymentPremise(schemas=("app",)),
    )


def campaign(directory: Path, seeds: range) -> dict:
    """Run ``seeds`` on both engines and write ``report.json`` in ``directory``."""
    from _pietto_execution_source_assurance_probe import manager

    directory.mkdir(mode=0o700)
    report: dict[str, Any] = {
        "profile": PROFILE,
        "seeds": [seeds.start, seeds.stop],
        "corpus_sha256": corpus_digest(seeds),
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": "STARTED",
        "cases": [],
    }
    resources = {}
    try:
        endpoints = {}
        for target in TARGETS:  # PostgreSQL first, as the slot locks are taken
            resources[target] = _resource(target, directory / target)
            endpoints[target] = _prepare(resources[target])
        for seed in seeds:
            case = forms.generate(seed, PROFILE)
            started = time.monotonic()
            for target in TARGETS:
                for sql in table_sql(case, target):
                    manager(resources[target], sql)
            work = directory / "work" / str(seed)
            limited = _observe(case, work / "limited", endpoints)
            full = None
            if case.limit is not None and not promised(case):
                full = _observe(replace(case, limit=None), work / "full", endpoints)
            report["cases"].append(
                {
                    "seed": seed,
                    "form": case.form,
                    "promised": promised(case),
                    "limited": limited,
                    "full": full,
                    "problems": compare(case, limited, full),
                    "seconds": round(time.monotonic() - started, 3),
                }
            )
        report["disagreements"] = [c["seed"] for c in report["cases"] if c["problems"]]
        report["status"] = "COMPLETE"
    except BaseException as error:
        report["status"] = "FAILED"
        report["failure"] = [type(error).__name__, str(error)[:500]]
        raise
    finally:
        report["cleanup"] = {t: r.cleanup()["status"] for t, r in resources.items()}
        if set(report["cleanup"].values()) - {"success"}:
            report["status"] = "FAILED"
        (directory / "report.json").write_text(
            json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--first", type=int, default=SEEDS.start)
    parser.add_argument("--stop", type=int, default=SEEDS.stop)
    args = parser.parse_args(argv)
    report = campaign(args.directory, range(args.first, args.stop))
    print(report["status"], len(report["cases"]), report.get("disagreements"))
    return 0 if report["status"] == "COMPLETE" and not report["disagreements"] else 1


if __name__ == "__main__":  # explicit native entry point
    raise SystemExit(main())
