"""Bounded native witnesses for the admitted project AVG(Int) realization.

Run explicitly; importing this module creates no database or Docker resource.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from _pietto_target_conformance_resources import Resources, error_fact


ROOT = Path(__file__).resolve().parents[1]
TABLE = "pietto_q2_avg_int"
CASES = (
    ("one_two_two", (1, 2, 2), float(5 / 3)),
    ("empty", (), None),
    ("all_null", (None, None), None),
    ("near_2_53", ((1 << 53), (1 << 53) + 1), float(1 << 53)),
)


def sql(target: str) -> tuple[str, str, str, str]:
    """The native DDL, clear, insert and exact emitted AVG expression."""
    if target == "postgres":
        return (
            f'CREATE TABLE "{TABLE}" ("value" BIGINT NULL)',
            f'TRUNCATE TABLE "{TABLE}"',
            f'INSERT INTO "{TABLE}" ("value") VALUES ($1)',
            f'SELECT AVG(CAST("value" AS pg_catalog.float8)) AS "average" '
            f'FROM "{TABLE}"',
        )
    if target == "mysql":
        return (
            f"CREATE TABLE `{TABLE}` (`value` BIGINT NULL)",
            f"TRUNCATE TABLE `{TABLE}`",
            f"INSERT INTO `{TABLE}` (`value`) VALUES (%s)",
            f"SELECT AVG(CAST(`value` AS DOUBLE)) AS `average` FROM `{TABLE}`",
        )
    raise ValueError("unknown target")


def _run(connection, target: str, statement: str, parameters=(), *, fetch=False):
    cursor = connection.cursor()
    try:
        if target == "postgres":
            cursor.execute(statement, parameters, prepare=True)
        else:
            cursor.execute(statement, parameters)
        return (cursor.fetchall(), cursor.description) if fetch else ((), None)
    finally:
        cursor.close()


def _carrier(target: str, description) -> int:
    if target == "postgres":
        return description[0].type_code
    return description[0][1]


def validate_case(
    target: str, name: str, expected, rows, description
) -> dict[str, Any]:
    """Validate one bounded query observation without comparing targets to each other."""
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError("AVG witness cardinality")
    carrier = _carrier(target, description)
    expected_carrier = 701 if target == "postgres" else 5
    if carrier != expected_carrier:
        raise ValueError("AVG witness carrier")
    observed = rows[0][0]
    if expected is None:
        if observed is not None:
            raise ValueError("AVG witness null result")
        encoded = None
    else:
        if type(observed) is not float or not math.isfinite(observed):
            raise ValueError("AVG witness finite float")
        if observed.hex() != expected.hex():
            raise ValueError("AVG witness binary64 result")
        encoded = observed.hex()
    return {"case": name, "carrier": carrier, "value_hex": encoded}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(target: str, directory: Path) -> dict[str, Any]:
    """Acquire one owned fixture, observe four cases, then clean it up."""
    if directory.exists():
        raise ValueError("witness directory already exists")
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    directory.mkdir(mode=0o700, parents=True)
    resource = Resources(target, pins["targets"][target], directory)
    report: dict[str, Any] = {"target": target, "status": "STARTED", "cases": []}
    try:
        resource.acquire()
        create, clear, insert, select = sql(target)
        _run(resource.manager, target, create)
        for statement, sensitive in resource.role_statements():
            _run(resource.manager, target, statement)
            resource.event("role_statement", sensitive=sensitive)
        resource.query = resource.connect(query=True)
        for name, values, expected in CASES:
            _run(resource.manager, target, clear)
            for value in values:
                _run(resource.manager, target, insert, (value,))
            rows, description = _run(resource.query, target, select, fetch=True)
            report["cases"].append(
                validate_case(target, name, expected, rows, description)
            )
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["failure"] = error_fact(error, "avg_int_witness")
        raise
    finally:
        report["cleanup"] = resource.cleanup()
        if report["cleanup"]["status"] != "success":
            report["status"] = "FAILED"
        _write(directory / "report.json", report)
    if report["cleanup"]["status"] != "success":
        raise RuntimeError("AVG witness resource cleanup failed")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("postgres", "mysql"), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    run(args.target, args.directory)
    return 0


if __name__ == "__main__":  # pragma: no cover - explicit native entry point
    raise SystemExit(main())
