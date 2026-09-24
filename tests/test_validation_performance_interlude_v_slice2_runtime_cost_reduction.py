"""Cell traversal changes work placement, never observation identity or reuse scope."""

from __future__ import annotations

import base64
import json
import sys

import pytest

import _pietto_differential_process_acquisition as process


def _synthetic_producer(monkeypatch):
    produced = []

    def produce(store, cell, root):
        produced.append((store.root, cell))
        requests = store.plan[cell]
        payload = {
            "results": {
                request.request_id: base64.b64encode(
                    (request.request_id + "\n").encode()
                ).decode()
                for request in requests
            },
            "import_origin": str(root / "pietto/__init__.py"),
        }
        (root / "cell.json").write_text(json.dumps(payload))
        return payload

    monkeypatch.setattr(process.DifferentialAcquisition, "_run_cell", produce)
    return produced


@pytest.mark.parametrize("family", ("phase58", "phase65"))
@pytest.mark.parametrize("both_interpreters", (False, True))
def test_workers_visit_distinct_needed_cells_but_return_original_requests(
    tmp_path, monkeypatch, family, both_interpreters
):
    versions = (
        process.SUPPORTED_INTERPRETERS
        if both_interpreters
        else ((sys.version_info.major, sys.version_info.minor),)
    )
    interpreters = {version: sys.executable for version in versions}
    monkeypatch.setattr(
        process, "available_supported_interpreters", lambda: interpreters
    )
    produced = _synthetic_producer(monkeypatch)
    first_cells = []
    requests = process.family_requests(family, interpreters)
    expected = {
        request.key: (request.request_id + "\n").encode() for request in requests
    }
    for worker in range(4):
        monkeypatch.setenv("PYTEST_XDIST_WORKER", f"gw{worker}")
        monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "4")
        store = process.DifferentialAcquisition(tmp_path / str(worker))
        before = len(produced)
        documents = store.documents(family)
        cells = [cell for _, cell in produced[before:]]
        assert set(cells) == {request.cell for request in requests}
        assert len(cells) == len(set(cells))
        first_cells.append(cells[0])
        assert documents == expected and tuple(documents) == tuple(expected)
        for cell in cells:
            assert (
                store.import_origin(cell)
                == store.root / f"cell-{cell.name}/pietto/__init__.py"
            )
        # The same worker and a different worker view reuse only this run's cells.
        after = len(produced)
        assert store.documents(family) == expected
        other = process.DifferentialAcquisition(store.root)
        assert other.documents(family) == expected
        assert len(produced) == after
        assert not tuple(store.root.glob("**/*.lock"))
    assert len(set(first_cells)) == 4
    # Four separate roots above each produced every required cell from scratch.
    assert len(produced) == 4 * len({request.cell for request in requests})


def test_serial_traversal_and_cross_family_completed_cell_reuse(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    produced = _synthetic_producer(monkeypatch)
    store = process.DifferentialAcquisition(tmp_path)
    first = process.family_requests("phase58", store.interpreters)
    second = process.family_requests("phase65", store.interpreters)
    expected = tuple(dict.fromkeys(request.cell for request in (*first, *second)))
    for family in ("phase58", "phase65"):
        assert store.documents(family)
    assert tuple(cell for _, cell in produced) == expected


def test_cell_failure_is_published_once_and_never_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw2")
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "4")
    calls = []

    def fail(store, cell, root):
        calls.append(cell)
        raise RuntimeError("deliberate cell failure")

    monkeypatch.setattr(process.DifferentialAcquisition, "_run_cell", fail)
    store = process.DifferentialAcquisition(tmp_path)
    with pytest.raises(RuntimeError, match="deliberate cell failure"):
        store.documents("phase65")
    with pytest.raises(process.AcquisitionFailure, match="deliberate cell failure"):
        process.DifferentialAcquisition(tmp_path).documents("phase65")
    assert len(calls) == 1
    assert len(tuple(tmp_path.glob("**/cell.failed"))) == 1
    assert not tuple(tmp_path.glob("**/cell.json"))
    assert not tuple(tmp_path.glob("**/*.lock"))
    assert not tuple(tmp_path.glob("**/*.pending"))
