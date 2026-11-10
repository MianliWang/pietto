"""Offline request manifest for the Phase77 Float-equivalence raw campaign.

This script deliberately has no endpoint, DBAPI, subprocess, or network path.
The engine parent owns those capabilities and consumes the JSON request only
after its resource lease is active.
"""

from __future__ import annotations

import argparse
import json


WIDE = "w" * 1000
NARROW = "n" * 64


def encoded(value: object) -> object:
    if type(value) is float:
        return {"float_hex": value.hex()}
    return value


def rows(values: tuple[tuple[int, float, str], ...]) -> list[list[object]]:
    return [[encoded(cell) for cell in row] for row in values]


OUTER = ((1, -0.0, WIDE), (2, 0.0, WIDE), (3, 1.5, NARROW))
INNER = ((10, -0.0, WIDE), (11, 0.0, WIDE), (12, 1.5, NARROW))


def request() -> dict[str, object]:
    """Return a finite parent-bound request, never a claimed B10 replay."""

    return {
        "format": "pietto.phase77.float-raw-request.v1",
        "execution": "parent_bound_only",
        "historical_b10": {
            "status": "exact_statement_unrecovered",
            "known_conclusion": "wide-key materialized semijoin returned outer rows twice",
            "must_record_before_comparison": [
                "exact_statement",
                "seed_readback",
                "session_settings",
                "explain",
                "result_rows",
            ],
        },
        "source_evidence": {
            "matrix": "phase72/b72-0/DB-MATRIX.md section C",
            "m1_m2_design": "phase72/lane-e-float/design-contract.md Stage 0 M1/M2",
        },
        "schema": [
            "CREATE TABLE p77_outer (id BIGINT NOT NULL, v DOUBLE NOT NULL, wide VARCHAR(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL)",
            "CREATE TABLE p77_inner (id BIGINT NOT NULL, v DOUBLE NOT NULL, wide VARCHAR(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL)",
        ],
        "insert": "INSERT INTO {table} (id, v, wide) VALUES (%s, %s, %s)",
        "seed": {"outer": rows(OUTER), "inner": rows(INNER)},
        "readback": "SELECT id, v, wide FROM {table} ORDER BY id",
        "queries": {
            "wide_semijoin_candidate": (
                "SELECT o.id, o.v, o.wide FROM p77_outer AS o WHERE EXISTS "
                "(SELECT 1 FROM p77_inner AS i WHERE i.v = o.v AND i.wide = o.wide) "
                "ORDER BY o.id"
            ),
            "wide_antijoin_candidate": (
                "SELECT o.id, o.v, o.wide FROM p77_outer AS o WHERE NOT EXISTS "
                "(SELECT 1 FROM p77_inner AS i WHERE i.v = o.v AND i.wide = o.wide) "
                "ORDER BY o.id"
            ),
        },
        "explain_prefix": "EXPLAIN FORMAT=TREE ",
        "oracle": {
            "semijoin_outer_ids_once": [1, 2, 3],
            "antijoin_outer_ids_once": [],
            "float_equality": "finite binary64; -0.0 equals 0.0",
            "transport": "selected Float bits must equal the selected outer row bits",
            "failure": "any duplicate outer id, missing id, warning, non-finite readback, or absent materialization evidence",
        },
    }


def selfcheck() -> None:
    data = request()
    assert len(WIDE) == 1000 and len(NARROW) == 64
    assert (-0.0).hex() == "-0x0.0p+0" and (0.0).hex() == "0x0.0p+0"
    assert data["execution"] == "parent_bound_only"
    assert data["historical_b10"]["status"] == "exact_statement_unrecovered"
    assert {row[0] for row in OUTER} == {1, 2, 3}
    assert {row[0] for row in INNER} == {10, 11, 12}
    for query in data["queries"].values():
        assert "EXISTS" in query and "i.v = o.v" in query and "i.wide = o.wide" in query
        assert "-0.0" not in query


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selfcheck", action="store_true")
    mode.add_argument("--request", action="store_true")
    args = parser.parse_args()
    if args.selfcheck:
        selfcheck()
        return 0
    print(json.dumps(request(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
