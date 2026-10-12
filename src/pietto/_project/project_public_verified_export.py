"""Private composition for D69.10's read-only verified saved export."""

from __future__ import annotations


def open_verified_export(
    workspace,
    *,
    job,
    generation,
    checkpoint,
    scope,
    extent,
    purpose,
    route,
    values,
    expected_pin,
    accepted_producer,
    accepted_compatibility,
    seconds,
    batch_rows,
):
    from pietto._project import project_job_replay as replay
    from pietto._project.project_job_capture import (
        SnapshotReader,
        checkpoint_snapshot,
    )

    acceptance = replay.accept_saved_read(
        workspace,
        job,
        generation,
        checkpoint=checkpoint,
        consumer=replay.new_consumer(),
        scope=scope,
        extent=extent,
        purpose=purpose,
        route=route,
        values=values,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
        seconds=seconds,
        batch_rows=batch_rows,
    )
    snapshot = checkpoint_snapshot(workspace, job, generation, checkpoint=checkpoint)
    return acceptance, SnapshotReader(workspace, snapshot, acceptance._stored_output)
