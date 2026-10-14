"""Qualified real-runtime saved-result fixture for public-job consumers."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import _pietto_execution_jobs_probe as workspace_probe


@dataclass(slots=True)
class SavedResultCase:
    """One completed v7 capture; callers close it after their saved-read work."""

    workspace: Any
    reference: Any
    template: Any
    built: Any
    binding: Any
    job: str
    generation: str
    state: Any
    snapshot: Any
    expected_rows: tuple[tuple[int, int | None], ...]
    expected_schema: Any
    user_values: tuple[int, ...]
    trust: tuple[str, str, tuple]

    def close(self) -> None:
        self.workspace.close()


@dataclass(slots=True)
class UnstartedSavedGeneration:
    """One qualified v7 generation before any native capture or Arrow result."""

    workspace: Any
    reference: Any
    job: str
    generation: str

    def close(self) -> None:
        self.workspace.close()


def _controlled_postgres_source(monkeypatch, rows) -> None:
    """Keep the real compiled owner and replace only its native service read."""
    from pietto._project import project_job_runtime as runtime
    from pietto._project import project_execution_reader as reader
    from pietto._project.project_execution_postgres import PostgresExecution

    original = runtime._owner

    def owner(binding, source):
        result = original(binding, source)
        if type(result) is not PostgresExecution:
            raise AssertionError("PUBLIC_SAVED_SOURCE_OWNER")
        return result

    def open(self):
        if self._closed or self._started is not None:
            raise AssertionError("PUBLIC_SAVED_SOURCE_REUSE")
        from pietto._project.project_execution_reader import bind_stored_output

        self._payloads = reader.ExecutionPayloads(
            self.request,
            (),
            producer=bind_stored_output(self.request.output, self.request.route),
        )
        self._fixture_rows = iter(rows)
        self._started = time.monotonic()
        self._source, self._transaction, self._delivery = "READING", "OPEN", "OPEN"
        self._qualification, self.context = "QUALIFIED", ("CONTROLLED",)
        return self

    def next_(self):
        if self._closed:
            raise StopIteration
        if self._started is None:
            self.open()
        try:
            return self._payloads.accept(next(self._fixture_rows))
        except StopIteration:
            self._terminal = "COMPLETE"
            self._source, self._transaction, self._delivery = (
                "EOF",
                "COMMIT_ACK",
                "COMPLETE",
            )
            self._cleanup, self._closed = "CLOSED", True
            raise

    monkeypatch.setattr(runtime, "_owner", owner)
    monkeypatch.setattr(PostgresExecution, "open", open)
    monkeypatch.setattr(PostgresExecution, "__next__", next_)


def _store(root, template, values, *, format):
    """Create the minimal registered v7 fixture without a phase-test import."""
    from pietto._project import project_job_store as store
    from pietto._project import project_job_workspace as workspace
    from pietto._project.project_execution_template import bind_values

    saved = workspace.create_workspace(str(root), format=format)
    job = store.register_job(saved, template, operation=store.new_operation()).get(
        "job"
    )
    publisher = store.claim_publisher(saved, job, operation=store.new_operation())
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    record = store.register_binding(
        publisher, binding, operation=store.new_operation()
    ).get("binding")
    generation = store.register_generation(
        publisher,
        record,
        binding,
        route="postgres_rows",
        isolation="stable",
        operation=store.new_operation(),
    ).get("generation")
    return saved, job, publisher, binding, record, generation


def unstarted_saved_generation(directory) -> UnstartedSavedGeneration | None:
    """Build the real v7 metadata needed by control-only public consumers."""
    if not workspace_probe.qualified(directory):
        return None
    from _pietto_execution_capture_probe import store
    from pietto._project import project_job_workspace as private_workspace
    from pietto.execution import WorkspaceRef

    template, _built = workspace_probe.compiled_template(directory / "compiled")
    workspace, job, publisher, _binding, _record, generation = store(
        directory / "workspace", template, (1,), format=private_workspace.FORMAT_V7
    )
    publisher.close()
    return UnstartedSavedGeneration(
        workspace, WorkspaceRef(workspace.root, workspace.identity), job, generation
    )


def completed_saved_result(directory, monkeypatch) -> SavedResultCase | None:
    """Save checked Arrow rows through the real runtime, chunk and reader path."""
    if not workspace_probe.qualified(directory):
        return None
    from pietto._project import project_job_capture as capture
    from pietto._project import project_public_jobs as jobs
    from pietto._project import project_execution as private_execution
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project import project_arrow_result as arrow
    from pietto.execution import WorkspaceRef

    try:
        arrow.pinned()
    except private_execution.ExecutionError:
        import pytest

        pytest.skip("R1 delivery consumes pinned PyArrow")

    expected_rows = ((2, 3), (2, 3), (3, 4))
    _controlled_postgres_source(monkeypatch, (expected_rows[:2], expected_rows[2:]))
    template, built = workspace_probe.compiled_template(directory / "compiled")
    workspace, job, publisher, binding, _record, generation = _store(
        directory / "workspace", template, (1,), format=private_workspace.FORMAT_V7
    )
    publisher.close()
    reference = WorkspaceRef(workspace.root, workspace.identity)
    try:
        state, pending = jobs.capture(
            reference,
            job=job,
            generation=generation,
            template=template,
            route="postgres_rows",
            access=private_execution.PostgresAccess(
                "127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable"
            ),
            schemas=("public", "pg_catalog"),
            limits=private_execution.ExecutionLimits(batch_rows=2, seconds=600),
            isolation="stable",
            values=(1,),
        )
        if pending is not None or (state.terminal, state.settlement) != (
            "COMPLETED",
            "RELEASED",
        ):
            raise AssertionError("PUBLIC_SAVED_CAPTURE")
        snapshot = capture.checkpoint_snapshot(workspace, job, generation)
        if (snapshot.frontier, snapshot.committed, snapshot.holes) != (
            3,
            ((0, 2), (2, 3)),
            (),
        ):
            raise AssertionError("PUBLIC_SAVED_SNAPSHOT")
        output = capture.stored_output(
            workspace,
            job,
            generation,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
        with capture.SnapshotReader(workspace, snapshot, output) as reader:
            chunks = tuple(reader.read(index) for index in range(len(snapshot.members)))
            verified = reader.verify()
        rows = tuple(
            tuple(row[name] for name in chunk.table.column_names)
            for chunk in chunks
            for row in chunk.table.to_pylist()
        )
        if rows != expected_rows or verified != {
            "integrity": "VERIFIED",
            "checkpoint": snapshot.checkpoint,
            "members": 2,
            "rows": 3,
            "frontier": 3,
        }:
            raise AssertionError("PUBLIC_SAVED_TRUST")
        return SavedResultCase(
            workspace,
            reference,
            template,
            built,
            output.binding,
            job,
            generation,
            state,
            snapshot,
            expected_rows,
            chunks[0].table.schema,
            (1,),
            (built.pin, built.producer, built.compatibility),
        )
    except BaseException:
        workspace.close()
        raise
