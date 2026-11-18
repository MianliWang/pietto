"""Shared process-family request fixture."""

import sys


SUPPORTED_INTERPRETERS = ((3, 12), (3, 13), (3, 14))


def _available_request_manifest(interpreters):
    from _pietto_plan_process_acquisition import (
        expected_request_manifest,
    )

    current = (sys.version_info.major, sys.version_info.minor)
    assert current in interpreters
    assert set(interpreters) <= set(SUPPORTED_INTERPRETERS)
    return tuple(
        row
        for row in expected_request_manifest(tuple(interpreters))
        if row[2] in interpreters
    )
