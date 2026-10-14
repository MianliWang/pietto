from __future__ import annotations

from collections import Counter
import inspect
import sys
from typing import cast

import _pietto_differential_process_acquisition as acquisition
import _pietto_differential_probe_batch as batch
from _pietto_plan_process_acquisition import expected_request_manifest


def test_process_cell_plan_preserves_current_requests() -> None:
    two_interpreters = {(3, 13): "python3.13", (3, 12): "python3.12"}
    plan = acquisition.cell_plan(two_interpreters)
    expected = expected_request_manifest()
    historical = ("phase58", "phase59", "phase60", "phase61", "phase62", "phase63")
    previous = (*historical, "phase64")
    actual = tuple(
        (
            request.family,
            request.key,
            request.cell.version,
            request.cell.seed,
            request.cell.mode,
            request.ambient,
        )
        for request in acquisition.all_requests(two_interpreters)
    )
    assert actual == expected
    assert len(plan) == len({row[2:5] for row in expected})
    assert sum(len(requests) for requests in plan.values()) == len(expected)
    assert sum(row[0] in previous for row in actual) == 74
    assert sum(row[0] in historical for row in actual) == 62
    assert acquisition.FAMILY_ORDER == tuple(batch.FAMILY_MODULES)

    modes = Counter(cell.mode for cell in plan)
    assert modes == Counter({"checkout": 8, "relocated": 5, "installed": 3})
    assert sum(modes.values()) == len(plan) == 16
    current = cast(tuple[int, int], sys.version_info[:2])
    other = next(
        version for version in acquisition.SUPPORTED_INTERPRETERS if version != current
    )
    assert Counter(cell.version for cell in plan) == Counter({current: 9, other: 7})


def test_guarded_publication_rechecks_and_cleans() -> None:
    guard = inspect.getsource(acquisition.DifferentialAcquisition._guarded)
    marker_index = guard.index('_atomic_write(marker, "ok")')
    unlink_index = guard.index("lock.unlink(missing_ok=True)", marker_index)
    assert marker_index < unlink_index
    assert guard.count("if marker.exists():") == 2
    cell = inspect.getsource(acquisition.DifferentialAcquisition._cell_payload)
    assert cell.count("if output.exists():") == 2
