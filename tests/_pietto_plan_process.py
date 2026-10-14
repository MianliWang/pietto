"""Shared process-family request fixture."""

import sys


SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


def _available_request_manifest(interpreters):
    from _pietto_plan_process_acquisition import (
        expected_request_manifest,
    )

    current = (sys.version_info.major, sys.version_info.minor)
    assert current in interpreters
    assert set(interpreters) <= set(SUPPORTED_INTERPRETERS)
    rows = [row for row in expected_request_manifest() if row[2] in interpreters]
    expected = []
    for family in dict.fromkeys(row[0] for row in rows):
        family_rows = [row for row in rows if row[0] == family]
        if family in ("phase62", "phase63", "phase64", "phase65", "phase66"):
            family_rows.sort(
                key=lambda row: (
                    ("checkout", "relocated", "installed").index(row[4]),
                    tuple(interpreters).index(row[2]),
                    SEEDS.index(row[3]),
                )
            )
        expected.extend(family_rows)
    return tuple(expected)
