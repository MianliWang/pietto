"""D69.10 verified export over a real v7 saved snapshot."""

from __future__ import annotations

import os
from typing import Any, cast

import pytest

import _pietto_jobs_public_cases as cases
import pietto.execution as execution


def _tree(root):
    """Names, kinds and sizes under a workspace without reading contents."""
    result = {}
    for directory, names, files in os.walk(root):
        for name in names + files:
            path = os.path.join(directory, name)
            state = os.lstat(path)
            result[os.path.relpath(path, root)] = (state.st_mode >> 12, state.st_size)
    return result


def _facts(case):
    """The public read leaves both the durable rows and the workspace tree alone."""
    from pietto._project import project_job_workspace as workspace

    tables = (
        "operation",
        "consumer",
        "acknowledgement",
        "replay_session",
        "runtime_owner",
        "admission",
        "admission_settlement",
    )
    counts = workspace.read(
        case.workspace,
        lambda connection: {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in tables
        },
    )
    return _tree(case.workspace.root), counts


def _retire(case):
    from pietto._project import project_job_collection as collection
    from pietto._project import project_job_store as store

    publisher = store.claim_publisher(
        case.workspace, case.job, operation=store.new_operation()
    )
    try:
        collection.retire_generation(
            publisher, case.generation, operation=store.new_operation()
        )
    finally:
        publisher.close()


def _export(case, **changes):
    pin, producer, compatibility = case.trust
    arguments: dict[str, Any] = dict(
        job=case.job,
        generation=case.generation,
        checkpoint=case.snapshot.checkpoint,
        scope="committed_prefix",
        extent=case.snapshot.frontier,
        purpose="verified-export",
        route="postgres_rows",
        values=case.user_values,
        expected_pin=pin,
        accepted_producer=producer,
        accepted_compatibility=compatibility[-1],
        seconds=60,
        batch_rows=2,
    )
    arguments.update(changes)
    return execution.verified_export(case.reference, **cast(Any, arguments))


def test_verified_export_checks_the_parameters_type_before_workspace_open(
    monkeypatch,
):
    from pietto._project import project_job_workspace as workspace

    monkeypatch.setattr(
        workspace,
        "open_workspace",
        lambda *arguments, **keywords: pytest.fail("opened private workspace"),
    )
    reference = object.__new__(execution.WorkspaceRef)
    object.__setattr__(reference, "root", "/not-opened")
    object.__setattr__(reference, "identity", "ws-" + "0" * 32)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.verified_export(
            reference,
            job="job-" + "0" * 32,
            generation="gen-" + "0" * 32,
            checkpoint="ckp-" + "0" * 32,
            scope="committed_prefix",
            extent=0,
            purpose="verified-export",
            route="postgres_rows",
            values=(),
            expected_pin="0" * 64,
            accepted_producer="0" * 64,
            accepted_compatibility="0" * 64,
            seconds=60,
            batch_rows=2,
            parameters=cast(Any, {1: 5}),
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1002",
        "PUBLIC_PARAMETERS_TYPE",
    )


def test_verified_export_reads_one_fixed_real_snapshot_without_writes(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        pa = pytest.importorskip("pyarrow")

        before = _tree(case.workspace.root)
        with _export(case) as exported:
            rows = []
            schema = None
            for batch in exported:
                with batch:
                    value = pa.record_batch(batch)
                    schema = value.schema
                    rows.extend(
                        tuple(row[name] for name in value.schema.names)
                        for row in value.to_pylist()
                    )
        assert rows == list(case.expected_rows)
        assert schema == case.expected_schema
        assert _tree(case.workspace.root) == before
    finally:
        case.close()


@pytest.mark.parametrize(
    "field,value",
    (("expected_pin", "0" * 64), ("accepted_producer", "0" * 64), ("extent", 2)),
)
def test_verified_export_refuses_wrong_trust_or_fixed_extent_before_delivery(
    tmp_path, monkeypatch, field, value
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        before = _tree(case.workspace.root)
        with pytest.raises(execution.RequestRejected):
            _export(case, **{field: value})
        assert _tree(case.workspace.root) == before
    finally:
        case.close()


def test_verified_export_accepts_only_the_public_scalar_compatibility_record(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        before = _facts(case)
        with pytest.raises(execution.RequestRejected) as refused:
            _export(case, accepted_compatibility=case.trust[2])
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1002",
            "PUBLIC_COMPATIBILITY",
        )
        assert _facts(case) == before
    finally:
        case.close()


@pytest.mark.parametrize("damage", ("missing", "corrupt"))
def test_verified_export_refuses_a_missing_or_corrupt_committed_member(
    tmp_path, monkeypatch, damage
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        member = case.snapshot.members[0]
        path = os.path.join(case.workspace.root, "chunks", member.file)
        original = open(path, "rb").read()
        directory = case.workspace.directory("chunks")
        try:
            if damage == "missing":
                os.unlink(path)
            else:
                with open(path, "wb") as stream:
                    stream.write(b"not a Pietto chunk")
            with _export(case) as exported:
                with pytest.raises(execution.RequestRejected) as refused:
                    next(exported)
            assert refused.value.__cause__ is None and refused.value.__context__ is None
        finally:
            os.close(directory)
            if damage == "missing":
                with open(path, "wb") as stream:
                    stream.write(original)
            elif os.path.exists(path):
                with open(path, "wb") as stream:
                    stream.write(original)
    finally:
        case.close()


def test_verified_export_ignores_an_uncommitted_staging_file(tmp_path, monkeypatch):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        path = os.path.join(case.workspace.root, "staging", "uncommitted")
        with open(path, "wb") as stream:
            stream.write(b"not a committed chunk")
        with _export(case) as exported:
            rows = []
            for batch in exported:
                rows.append(batch.num_rows)
                batch.close()
            assert rows == [2, 1]
        assert os.path.exists(path)
    finally:
        case.close()


def test_verified_export_early_close_releases_its_reader_lease_without_writes(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        from pietto._project import project_job_chunks as chunks

        before = _facts(case)
        exported = _export(case)
        batch = next(exported)
        batch.close()
        exported.close()
        with chunks.Lease(case.workspace, case.generation, exclusive=True, wait=0):
            pass
        assert _facts(case) == before
    finally:
        case.close()


def test_verified_export_reads_a_retired_generation_without_new_state(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        pa = pytest.importorskip("pyarrow")

        _retire(case)
        before = _facts(case)
        with _export(case) as exported:
            rows = []
            for batch in exported:
                with batch:
                    rows.extend(pa.record_batch(batch).to_pylist())
        assert [tuple(row.values()) for row in rows] == list(case.expected_rows)
        assert _facts(case) == before
    finally:
        case.close()


def test_verified_export_refuses_a_collected_member_without_writes(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        from pietto._project import project_job_runtime as runtime

        _retire(case)
        opened = runtime.open_runtime(
            case.reference.root, expected_identity=case.reference.identity
        )
        try:
            assert opened.collect().decided
        finally:
            opened.close()
        before = _facts(case)
        with pytest.raises(execution.RequestRejected) as refused:
            _export(case)
        assert refused.value.code == "PIE-R1009"
        assert refused.value.__cause__ is None and refused.value.__context__ is None
        assert _facts(case) == before
    finally:
        case.close()


def test_verified_export_survives_an_exhausted_operation_quota_without_writes(
    tmp_path, monkeypatch
):
    case = cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    try:
        from pietto._project import project_job_store as store
        from pietto._project import project_job_workspace as workspace
        from pietto._project import project_public_jobs as jobs
        from pietto._project import project_job_runtime as runtime
        from pietto._project import project_execution as private_execution

        before = _facts(case)
        operations = before[1]["operation"]
        monkeypatch.setitem(
            store.LIMITS, "operation", operations + store.CONTROL_OPERATIONS
        )
        monkeypatch.setattr(jobs, "_DATA_OPERATIONS", operations)

        def forbidden(*args, **kwargs):
            raise AssertionError("VERIFIED_EXPORT_RUNTIME_OR_SOURCE")

        monkeypatch.setattr(runtime, "open_runtime", forbidden)
        monkeypatch.setattr(runtime, "_owner", forbidden)
        with pytest.raises(workspace.JobStoreError, match="RUNTIME_UNIT_BOUND"):
            jobs.capture(
                case.reference,
                job=case.job,
                generation=case.generation,
                template=case.template,
                route="postgres_rows",
                access=private_execution.PostgresAccess(
                    "127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable"
                ),
                schemas=("public", "pg_catalog"),
                limits=private_execution.ExecutionLimits(batch_rows=2, seconds=600),
                isolation="stable",
                values=case.user_values,
            )
        with _export(case) as exported:
            assert [batch.num_rows for batch in exported] == [2, 1]
        assert _facts(case) == before
    finally:
        case.close()
