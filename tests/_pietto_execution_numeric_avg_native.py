"""Bounded native witnesses for the admitted project AVG(Int) realization.

Run explicitly; importing this module creates no database or Docker resource.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import statistics
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


# Lane F campaign 3 cells for `stddev`: (id, tag, values). Their statements
# come from the emitter at run time; only these values and `tolerance` live here.
_BASICS = (
    ("E0", ()),
    ("E1", (7,)),
    ("E1N", (7, None, None)),
    ("EN", (None, None)),
    ("N2", (1, 2)),
    ("M8", (2, 4, 4, 4, 5, 5, 7, 9)),
    ("R3", (5, 5, 5)),
    ("WN", (1, None, 3)),
)
_SEEDED = random.Random(72)
STDDEV_CASES = (
    *((name, "Int", values) for name, values in _BASICS),
    ("I53", "Int", tuple((1 << 53) + offset for offset in (1, 3, 5))),
    ("I64", "Int", (-(1 << 63), (1 << 63) - 1)),
    ("IS", "Int", (0, 100000000)),
    ("IN", "Int", tuple(_SEEDED.randint(-(10**6), 10**6) for _ in range(10000))),
    *(
        (name, "Float", tuple(None if v is None else float(v) for v in values))
        for name, values in _BASICS
    ),
    ("F1", "Float", (0.1, 0.2, 0.3)),
    ("F2", "Float", (0.1, 0.1, 0.1)),
    ("FO", "Float", (1e9 + 0.1, 1e9 + 0.1, 1e9 + 0.1, 1e9 + 0.2)),
    ("FL", "Float", (1e150, 3e150, 5e150)),
    ("FT", "Float", (1e-300, 3e-300, 5e-300)),
    ("FZ", "Float", (-0.0, 0.0)),
    ("FN", "Float", tuple(1e6 + i * 0.001 for i in range(100000))),
    ("O1", "Float", (1e200, -1e200)),
    ("O2", "Float", (1.7e308, -1.7e308)),
)
EPSILON = 2.0**-52


def stddev_oracle(values) -> float | None:
    """`statistics.stdev` of the non-None values; None below two of them.
    Raises OverflowError when the deviation exceeds binary64 (cell O2)."""
    present = [value for value in values if value is not None]
    return statistics.stdev(present) if len(present) >= 2 else None


def stddev_bound(tag: str, values, oracle: float) -> float:
    """The accuracy tier: Int 2*eps*s; Float B = 4*eps*s +
    8*n*eps*sqrt(S2/(n-1)) + 2*sqrt(n*2^-1074), with S2 = exact sum of squares."""
    if tag == "Int":
        return 2 * EPSILON * oracle
    present = [value for value in values if value is not None]
    n = len(present)
    squares = sum((Fraction(value) ** 2 for value in present), Fraction(0))
    mean_square = squares / (n - 1)
    # Logarithms keep sqrt(S2/(n-1)) finite where S2 itself is not (O1).
    root = (
        0.0
        if mean_square == 0
        else math.exp(
            (math.log(mean_square.numerator) - math.log(mean_square.denominator)) / 2
        )
    )
    return 4 * EPSILON * oracle + 8 * n * EPSILON * root + 2 * math.sqrt(n * 2.0**-1074)


def tolerance(tag: str, values, observed) -> float:
    """|t - s| over the cell's tier (at most 1 passes). A NULL mismatch, a
    negative or non-finite value, or any value for an unrepresentable oracle
    raises ValueError; the hex compare is never used for `stddev`."""
    if tag not in {"Int", "Float"}:
        raise ValueError("stddev tier")
    try:
        oracle = stddev_oracle(values)
    except OverflowError:
        raise ValueError("stddev oracle unrepresentable; only an error passes")
    if oracle is None or observed is None:
        if oracle is not observed:
            raise ValueError("stddev NULL mismatch")
        return 0.0
    if type(observed) is not float or not math.isfinite(observed) or observed < 0:
        raise ValueError("stddev result is not a finite non-negative float")
    bound = stddev_bound(tag, values, oracle)
    difference = abs(observed - oracle)
    if bound == 0:
        return 0.0 if difference == 0 else math.inf
    return difference / bound


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
