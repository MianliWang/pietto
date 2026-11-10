"""Independent finite oracle for a future MySQL nested raw qualification.

This is test preparation only. It neither emits Pietto SQL nor opens a database.
The values are deliberately small, explicit witnesses for the transport claims.
"""

from __future__ import annotations

import struct

SCHEMA = "pietto.phase77.mysql-nested-raw-observation.v1"
RAW_CANDIDATE = "RAW_CANDIDATE_NOT_PIETTO_EMITTED"
ENVELOPE_VERSION = 1
MAX_CHILD_ROWS = 1 << 20


def float_bits(value: float) -> str:
    return struct.pack(">d", value).hex()


NEGATIVE_ZERO = -0.0
POSITIVE_ZERO = 0.0
ADJACENT_BINARY64 = float.fromhex("0x1.0000000000001p+0")


# pg_control documents the existing pg_column_arrays_v1 logical carrier:
# count plus aligned child arrays. It is an oracle control, not queried here.
CASES = (
    {
        "id": "float_bits",
        "leaf": "Float",
        "parent": "parent_float",
        "pg_control": {"count": 3, "arrays": [[NEGATIVE_ZERO, POSITIVE_ZERO, ADJACENT_BINARY64]]},
        "expected_rows": ((NEGATIVE_ZERO,), (POSITIVE_ZERO,), (ADJACENT_BINARY64,)),
    },
    {
        "id": "int64",
        "leaf": "Int",
        "parent": "parent_int",
        "pg_control": {"count": 3, "arrays": [[-(2**63), 0, 2**63 - 1]]},
        "expected_rows": (("-9223372036854775808",), ("0",), ("9223372036854775807",)),
    },
    {
        "id": "decimal_string",
        "leaf": "Decimal",
        "parent": "parent_decimal",
        "pg_control": {"count": 3, "arrays": [["-12.30", "0", "999.99"]]},
        "expected_rows": (("-12.30",), ("0",), ("999.99",)),
    },
    {
        "id": "date_string",
        "leaf": "Date",
        "parent": "parent_date",
        "pg_control": {"count": 3, "arrays": [["1000-01-01", "2026-11-08", "9999-12-31"]]},
        "expected_rows": (("1000-01-01",), ("2026-11-08",), ("9999-12-31",)),
    },
    {
        "id": "uuid_bytes",
        "leaf": "UUID",
        "parent": "parent_uuid",
        "pg_control": {"count": 3, "arrays": [["00000000000000000000000000000000", "80ff00112233445566778899aabbccdd", "ffffffffffffffffffffffffffffffff"]]},
        "expected_rows": (("00000000000000000000000000000000",), ("80ff00112233445566778899aabbccdd",), ("ffffffffffffffffffffffffffffffff",)),
    },
    {
        "id": "window_order_unique",
        "leaf": "Text",
        "parent": "parent_order_unique",
        "pg_control": {"count": 3, "arrays": [["first", "second", "third"]]},
        "expected_rows": (("first",), ("second",), ("third",)),
    },
    {
        "id": "window_order_tie",
        "leaf": "Text",
        "parent": "parent_order_tie",
        "pg_control": {"count": 3, "arrays": [["before_tie", "tie_a", "tie_b"]]},
        "allowed_rows": (
            (("before_tie",), ("tie_a",), ("tie_b",)),
            (("before_tie",), ("tie_b",), ("tie_a",)),
        ),
    },
    {
        "id": "empty",
        "leaf": "Text",
        "parent": "parent_empty",
        "pg_control": {"count": 0, "arrays": [[]]},
        "expected_rows": (),
    },
    {
        "id": "outer_absent",
        "leaf": "Text",
        "parent": "parent_absent",
        "pg_control": {"count": None, "arrays": [None]},
        "absent": True,
    },
)


def case_ids() -> tuple[str, ...]:
    return tuple(case["id"] for case in CASES)


def case_by_id(identifier: str) -> dict:
    for case in CASES:
        if case["id"] == identifier:
            return case
    raise KeyError(identifier)

