"""Public local publication of a checked ordinary saved generation."""

from __future__ import annotations

import os

import pytest

import _pietto_jobs_public_cases as public_cases
import pietto.execution as execution
from pietto._project import project_job_publication as publication
from pietto._project import project_job_replay as replay
from pietto._project import project_job_store as store
from pietto._project import project_job_collection as collection


def _closing(workspace, job):
    attempts = store.job_record(workspace, job).attempts
    assert len(attempts) == 1 and attempts[0].terminal == "OUTCOME"
    return attempts[0].identity


def _publish(saved, *, operation=None, **overrides):
    pin, producer, compatibility = saved.trust
    arguments = {
        "job": saved.job,
        "generation": saved.generation,
        "checkpoint": saved.snapshot.checkpoint,
        "closing": _closing(saved.workspace, saved.job),
        "purpose": "public-local-publication",
        "route": "postgres_rows",
        "isolation": "stable",
        "values": saved.user_values,
        "expected_pin": pin,
        "accepted_producer": producer,
        "accepted_compatibility": compatibility[-1],
        "seconds": 600,
        "operation": operation or execution.new_operation(),
    }
    arguments.update(overrides)
    return execution.publish_saved_generation(saved.reference, **arguments)


def test_publication_preserves_real_members_and_source_free_saved_read(
    tmp_path, monkeypatch
):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        reply = _publish(saved)
        assert (
            reply.terminal,
            reply.checkpoint,
            reply.extent,
            reply.operation is not None,
        ) == ("PUBLISHED", saved.snapshot.checkpoint, 3, True)
        found = publication.publication(saved.workspace, saved.job, saved.generation)
        assert found is not None
        assert (found.checkpoint, found.closing, found.extent, found.members) == (
            saved.snapshot.checkpoint,
            _closing(saved.workspace, saved.job),
            3,
            2,
        )

        acceptance = replay.accept_saved_read(
            saved.workspace,
            saved.job,
            saved.generation,
            checkpoint=found.checkpoint,
            consumer=replay.new_consumer(),
            scope="complete_capture",
            extent=found.extent,
            purpose="publication-source-free-read",
            route="postgres_rows",
            values=saved.user_values,
            expected_pin=saved.trust[0],
            accepted_producer=saved.trust[1],
            accepted_compatibility=saved.trust[2],
            seconds=600,
            batch_rows=2,
        )
        publisher = store.claim_publisher(
            saved.workspace, saved.job, operation=store.new_operation()
        )
        try:
            replay.register_consumer(
                publisher, acceptance, operation=store.new_operation()
            )
            session = replay.open_replay(
                publisher, acceptance, operation=store.new_operation()
            )
            try:
                rows = []
                while True:
                    item = session.next(2, operation=store.new_operation())
                    if isinstance(item, replay.SavedScopeEnd):
                        break
                    pyarrow = pytest.importorskip("pyarrow")

                    rows.extend(pyarrow.record_batch(item.batch).to_pylist())
                    item.batch.close()
                    session.acknowledge(item, operation=store.new_operation())
                assert [tuple(row.values()) for row in rows] == list(
                    saved.expected_rows
                )
            finally:
                session.close()
        finally:
            publisher.close()
    finally:
        saved.close()


def test_publication_acceptance_defers_arrow_binding_until_member_verify(
    tmp_path, monkeypatch
):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        from pietto._project import project_arrow_result as arrow

        def forbidden(*arguments, **keywords):
            raise AssertionError("publication acceptance bound Arrow")

        monkeypatch.setattr(arrow, "bind_arrow", forbidden)
        pin, producer, compatibility = saved.trust
        acceptance = publication.accept_publication(
            saved.workspace,
            saved.job,
            saved.generation,
            checkpoint=saved.snapshot.checkpoint,
            closing=_closing(saved.workspace, saved.job),
            purpose="publication-arrow-deferral",
            route="postgres_rows",
            isolation="stable",
            values=saved.user_values,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
            seconds=600,
        )
        assert acceptance._stored_output.binding is not None
    finally:
        saved.close()


def test_publication_replay_reports_partial_without_claiming_again(
    tmp_path, monkeypatch
):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        operation = execution.new_operation()
        first = _publish(saved, operation=operation)
        assert first.terminal == "PUBLISHED"

        def forbidden(*arguments, **keywords):
            raise AssertionError("replayed publication claimed a publisher")

        monkeypatch.setattr(store, "claim_publisher", forbidden)
        replayed = _publish(saved, operation=operation)
        assert replayed.terminal == "REPLY_LOST_OR_PARTIAL"
        assert replayed.operation == first.operation
        with pytest.raises(execution.RequestRejected) as conflict:
            _publish(saved, operation=operation, purpose="different-publication")
        assert conflict.value.code == "PIE-R1010"
    finally:
        saved.close()


def test_publication_refuses_bad_trust_and_missing_member_before_publication(
    tmp_path, monkeypatch
):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        with pytest.raises(execution.RequestRejected) as bad_trust:
            _publish(saved, expected_pin="0" * 64)
        assert bad_trust.value.code == "PIE-R1009"
        assert (
            publication.publication(saved.workspace, saved.job, saved.generation)
            is None
        )

        member = saved.snapshot.members[0]
        os.unlink(os.path.join(saved.workspace.root, "chunks", member.file))
        with pytest.raises(execution.RequestRejected) as missing:
            _publish(saved)
        assert missing.value.code == "PIE-R1009"
        assert (
            publication.publication(saved.workspace, saved.job, saved.generation)
            is None
        )
    finally:
        saved.close()


def test_publication_refuses_a_retired_unpublished_generation(tmp_path, monkeypatch):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        publisher = store.claim_publisher(
            saved.workspace, saved.job, operation=store.new_operation()
        )
        try:
            collection.retire_generation(
                publisher, saved.generation, operation=store.new_operation()
            )
        finally:
            publisher.close()
        with pytest.raises(execution.RequestRejected) as retired:
            _publish(saved)
        assert retired.value.code == "PIE-R1009"
        assert (
            publication.publication(saved.workspace, saved.job, saved.generation)
            is None
        )
    finally:
        saved.close()
