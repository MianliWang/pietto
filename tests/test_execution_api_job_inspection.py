"""Public, read-only observations of saved-job metadata."""

from __future__ import annotations

import dataclasses

import pytest

import _pietto_jobs_public_cases as public_cases
import _pietto_phase68_slice11_probe as workspace_probe
import pietto.execution as execution
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace


def _saved(tmp_path, monkeypatch):
    if not workspace_probe.qualified(tmp_path):
        return None
    from pietto._project import project_arrow_result as arrow
    from pietto._project import project_execution as private_execution
    from pietto.execution._query import _query

    try:
        arrow.pinned()
    except private_execution.ExecutionError:
        pytest.skip("inspection requires pinned PyArrow")
    public_cases._controlled_postgres_source(monkeypatch, (((2, 3), (2, 3)), ((3, 4),)))
    template, built = workspace_probe.compiled_template(tmp_path / "compiled")
    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    operation = execution.new_operation()
    reply = execution.save(
        workspace,
        _query(template, "live", None),
        operation=operation,
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 9, "db", "u", "pw", "disable"),
        premise=execution.PostgresDeploymentPremise(("public", "pg_catalog")),
    )
    assert (reply.terminal, reply.settlement, reply.cleanup) == (
        "COMPLETED",
        "RELEASED",
        None,
    )
    assert reply.job is not None and reply.generation is not None
    return workspace, operation, reply, built


def _unstarted(tmp_path):
    if not workspace_probe.qualified(tmp_path):
        return None
    from pietto._project.project_execution_template import bind_values

    template, _built = workspace_probe.compiled_template(tmp_path / "compiled")
    workspace = private_workspace.create_workspace(
        str(tmp_path / "workspace"),
        budget_bytes=private_workspace.MIN_BUDGET,
        format=private_workspace.FORMAT_V7,
    )
    binding = bind_values(
        template,
        tuple(
            (slot, slot.original.site.position.literal.value) for slot in template.slots
        ),
    )
    try:
        registered = store.register_job(
            workspace, template, operation=store.new_operation()
        )
        publisher = store.claim_publisher(
            workspace, registered.job, operation=store.new_operation()
        )
        try:
            record = store.register_binding(
                publisher, binding, operation=store.new_operation()
            )
            first = store.register_generation(
                publisher,
                record.get("binding"),
                binding,
                route="postgres_rows",
                isolation="stable",
                operation=store.new_operation(),
            )
            first_attempt = store.open_attempt(
                publisher,
                first.get("generation"),
                binding,
                operation=store.new_operation(),
            )
            store.record_not_executed(
                publisher, first_attempt, operation=store.new_operation()
            )
            second_attempt = store.open_attempt(
                publisher,
                first.get("generation"),
                binding,
                operation=store.new_operation(),
            )
            store.record_not_executed(
                publisher, second_attempt, operation=store.new_operation()
            )
            second = store.register_generation(
                publisher,
                record.get("binding"),
                binding,
                route="postgres_rows",
                isolation="stable",
                operation=store.new_operation(),
            )
            return (
                execution.WorkspaceRef(workspace.root, workspace.identity),
                registered.job,
                first.get("generation"),
                second.get("generation"),
                (first_attempt.identity, second_attempt.identity),
            )
        finally:
            publisher.close()
    finally:
        workspace.close()


def test_inspection_refuses_invalid_public_arguments_before_opening(monkeypatch):
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)

    def forbidden(*arguments, **keywords):
        raise AssertionError("invalid inspection opened a workspace")

    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    for job, expected in (
        (None, ("PIE-R1001", "PUBLIC_JOB_REQUIRED")),
        (1, ("PIE-R1002", "PUBLIC_JOB_TYPE")),
    ):
        with pytest.raises(execution.RequestRejected) as refused:
            execution.inspect_job(workspace, job=job)  # type: ignore[arg-type]
        assert (refused.value.code, refused.value.detail) == expected


def test_public_save_then_inspect_recovers_lost_reply_and_never_controls_source(
    tmp_path, monkeypatch
):
    saved = _saved(tmp_path, monkeypatch)
    if saved is None:
        return
    workspace, operation, reply, _built = saved

    def forbidden(*arguments, **keywords):
        raise AssertionError("inspection changed saved-job state or opened a source")

    monkeypatch.setattr(store, "write", forbidden)
    monkeypatch.setattr(store, "claim_publisher", forbidden)
    from pietto._project import project_job_runtime as runtime

    monkeypatch.setattr(runtime, "_owner", forbidden)
    recorded = execution.operation_result(workspace, operation)
    assert recorded is not None and recorded.job == reply.job
    observed = execution.inspect_job(workspace, job=recorded.job)
    generation = observed.generations[0]
    assert (observed.job, observed.revision, len(observed.generations)) == (
        reply.job,
        observed.revision,
        1,
    )
    assert (
        generation.identity,
        generation.route,
        generation.isolation,
        generation.frontier,
        generation.committed,
        generation.holes,
        generation.observed_end,
    ) == (
        reply.generation,
        "postgres_rows",
        "stable",
        3,
        ((0, 2), (2, 3)),
        (),
        3,
    )
    assert generation.checkpoint is not None and len(generation.closings) == 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        generation.frontier = 0  # type: ignore[misc]


def test_inspection_preserves_ordered_closings_and_no_capture_state(tmp_path):
    unstarted = _unstarted(tmp_path)
    if unstarted is None:
        return
    workspace, job, first, second, closings = unstarted
    observed = execution.inspect_job(workspace, job=job)
    assert [item.identity for item in observed.generations] == [first, second]
    assert observed.generations[0].closings == closings
    for generation in observed.generations:
        assert (
            generation.checkpoint,
            generation.frontier,
            generation.committed,
            generation.holes,
            generation.observed_end,
        ) == (None, 0, (), (), None)


def test_inspection_refuses_wrong_workspace_identity_and_keeps_consumer_trust_fresh(
    tmp_path, monkeypatch
):
    saved = _saved(tmp_path, monkeypatch)
    if saved is None:
        return
    workspace, _operation, reply, built = saved
    assert reply.job is not None
    with pytest.raises(execution.RequestRejected) as identity:
        execution.inspect_job(
            execution.WorkspaceRef(workspace.root, "ws-" + "0" * 32), job=reply.job
        )
    assert identity.value.code == "PIE-R1009"

    observed = execution.inspect_job(workspace, job=reply.job)
    generation = observed.generations[0]
    assert generation.checkpoint is not None
    with pytest.raises(execution.RequestRejected) as trust:
        execution.open_saved_read(
            workspace,
            job=observed.job,
            generation=generation.identity,
            checkpoint=generation.checkpoint,
            consumer=execution.new_consumer_identity(),
            register_operation=execution.new_operation(),
            open_operation=execution.new_operation(),
            expected_pin="0" * 64,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility[-1],
            values=(1,),
            extent=generation.frontier,
            purpose="inspection-wrong-trust",
            route=generation.route,
            batch_rows=2,
            seconds=60,
        )
    assert trust.value.code == "PIE-R1009"


def test_inspection_refuses_a_job_revision_change_instead_of_merging_reads(
    tmp_path, monkeypatch
):
    unstarted = _unstarted(tmp_path)
    if unstarted is None:
        return
    workspace, job, _first, _second, _closings = unstarted
    from pietto._project import project_job_capture as capture

    original, changed = capture.checkpoint_snapshot, False

    def concurrent_change(opened, inspected_job, generation):
        nonlocal changed
        if not changed:
            changed = True
            writer = private_workspace.open_workspace(
                workspace.root, expected_identity=workspace.identity
            )
            publisher = store.claim_publisher(
                writer, job, operation=store.new_operation()
            )
            try:
                store.cancel_job(publisher, operation=store.new_operation())
            finally:
                publisher.close()
                writer.close()
        return original(opened, inspected_job, generation)

    monkeypatch.setattr(capture, "checkpoint_snapshot", concurrent_change)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.inspect_job(workspace, job=job)
    assert (refused.value.code, refused.value.detail) == ("PIE-R1009", "JOB_REVISION")
    assert refused.value.__cause__ is None and refused.value.__context__ is None
