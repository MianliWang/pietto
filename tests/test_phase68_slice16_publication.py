"""S16 complete-generation publication: v6, truth table, atomic publish, query.

No database or Arrow: saved inputs and closing owners use the labelled
ARROW_FREE_STORAGE_STEP, SYNTHETIC_CLOSED_OWNER and ARROW_FREE_MEMBER_CHECK
replacements (see the probe); R2 histories reuse S14's labelled synthetic
steps. record_attempt, closing observations, retention, fences, the publication
transaction, lookups, S13/S15 neighbours and the independent verifier run for
real. Real checked Arrow members and native closing owners are
execution-profile evidence only.
"""

import json
import os
import pickle
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

import _pietto_phase68_slice13_probe as s13
import _pietto_phase68_slice14_probe as r2
import _pietto_phase68_slice15_probe as s15
import _pietto_phase68_slice16_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_delivery as d
from pietto._project import project_job_extraction as ext
from pietto._project import project_job_publication as p
from pietto._project import project_job_replay as r
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

op = probe.op


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(tmp_path_factory.mktemp("s16") / "small", entry="bundle")


@pytest.fixture
def setup(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    probe.arrow_free(monkeypatch)
    template, compiled = built
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template
    )
    x = SimpleNamespace(
        workspace=workspace,
        job=job,
        publisher=publisher,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
        root=tmp_path,
    )
    yield x
    for item in (x.publisher, x.workspace):
        if not item._closed:
            item.close()


def another(x):
    """A further generation of the same job and binding."""
    return s.register_generation(
        x.publisher,
        x.record,
        x.binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")


def released(x, retention):
    return bool(
        probe.rows(
            x.workspace,
            "SELECT 1 FROM retention_release WHERE retention = ?",
            (retention,),
        )
    )


def preparations(x):
    """Every preparation retention of the job (released or not)."""
    return [
        row[0]
        for row in probe.rows(x.workspace, "SELECT identity, scope FROM retention")
        if json.loads(row[1]).get("purpose") == "publication-preparation"
    ]


# --- pure laws ---------------------------------------------------------------


def eligible_facts(outcome=None, **changes):
    """A complete eligible fact set (CAPTURE basis, 3 rows in two members);
    `outcome` overrides fields of the raw terminal outcome only."""
    facts = {
        "route": "postgres_rows",
        "binding": "bind-" + "1" * 32,
        "kind": "ORDINARY",
        "checkpoint": "ckp-" + "2" * 32,
        "closing": "att-" + "3" * 32,
        "binding_reference": "ref",
        "terminal": "OUTCOME",
        "outcome": {
            "binding_reference": "ref",
            "cancel": [False, False, False],
            "cleanup": "CLOSED",
            "delivery": "COMPLETE",
            "deployment_acceptance": "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
            "guard_states": [],
            "local_durable_result": "NOT_IMPLEMENTED",
            "native_definition_lifetime_exclusion": "NOT_DEMONSTRATED",
            "premise_compliance": "NOT_INDEPENDENTLY_VERIFIED",
            "remote_source_use_end": "TRANSACTION_ACK",
            "route": "postgres_rows",
            "source": "EOF",
            "source_qualification": "QUALIFIED",
            "structure": "ACCEPTED",
            "transaction": "COMMIT_ACK",
            "transaction_opened": True,
        },
        "observation": {"closed": True, "rows": 3, "failure": None, "cleanup": []},
        "basis": "CAPTURE",
        "end": (3, "EOF"),
        "reconciled": False,
        "end_checkpoint": None,
        "predecessor": frozenset(),
        "members": (
            ("chk-a", 0, 2, "att-" + "3" * 32),
            ("chk-b", 2, 3, "att-" + "3" * 32),
        ),
        "ranges": ((0, 2), (2, 3)),
        "latest": "ckp-" + "2" * 32,
        "known": 3,
        "extent": 3,
        "open": 0,
        "published": False,
    }
    facts.update(changes)
    if outcome is not None:
        facts["outcome"] = {**facts["outcome"], **outcome}
    return facts


def test_completion_truth_table_refuses_each_missing_fact():
    assert p.eligibility(eligible_facts()) == ()
    cases = [
        ({"terminal": "INTERRUPTED", "outcome": None, "observation": None}, None),
        ({"terminal": "NOT_EXECUTED", "observation": None}, None),
        ({"outcome": {"source": "EARLY_CLOSE"}}, "PUBLICATION_SOURCE"),
        ({"outcome": {"source": "INCOMPLETE"}}, "PUBLICATION_SOURCE"),
        ({"outcome": {"transaction": "UNKNOWN"}}, "PUBLICATION_TRANSACTION"),
        ({"outcome": {"transaction": "ROLLBACK_ACK"}}, "PUBLICATION_TRANSACTION"),
        (
            {"outcome": {"remote_source_use_end": "REMOTE_QUIESCENCE_UNCONFIRMED"}},
            "PUBLICATION_TRANSACTION",
        ),
        ({"outcome": {"delivery": "FAILED"}}, "PUBLICATION_DELIVERY"),
        ({"outcome": {"delivery": "INCOMPLETE"}}, "PUBLICATION_DELIVERY"),
        ({"outcome": {"cleanup": "FAILED"}}, "PUBLICATION_CLEANUP"),
        (
            {
                "observation": {
                    "closed": True,
                    "rows": 3,
                    "failure": None,
                    "cleanup": [["connection_close", "OSError"]],
                }
            },
            "PUBLICATION_CLEANUP",
        ),
        (
            {
                "observation": {
                    "closed": True,
                    "rows": 3,
                    "failure": ["finalization", "ExecutionError"],
                    "cleanup": [],
                }
            },
            "PUBLICATION_PRIMARY",
        ),
        (
            {"outcome": {"source_qualification": "NOT_QUALIFIED"}},
            "PUBLICATION_QUALIFICATION",
        ),
        ({"outcome": {"transaction_opened": False}}, "PUBLICATION_QUALIFICATION"),
        ({"outcome": {"guard_states": ["VIOLATED"]}}, "PUBLICATION_GUARDS"),
        ({"outcome": {"guard_states": ["FULFILLED", "UNKNOWN"]}}, "PUBLICATION_GUARDS"),
        ({"outcome": {"guard_states": ["PENDING"]}}, "PUBLICATION_GUARDS"),
        ({"outcome": {"structure": "CHANGED"}}, "PUBLICATION_OUTCOME"),
        ({"outcome": {"route": "mysql_rows"}}, "PUBLICATION_OUTCOME"),
        ({"outcome": {"binding_reference": "other"}}, "PUBLICATION_OUTCOME"),
        ({"binding_reference": "other"}, "PUBLICATION_OUTCOME"),
        ({"basis": None}, "PUBLICATION_BASIS"),
        ({"end": (3, "EARLY_CLOSE"), "extent": None}, None),
        (
            {"members": (("chk-a", 0, 2, "att-x"), ("chk-b", 2, 3, "att-" + "3" * 32))},
            "PUBLICATION_BASIS",
        ),
        ({"known": None}, "PUBLICATION_EXTENT"),
        (
            {
                "observation": {
                    "closed": True,
                    "rows": 4,
                    "failure": None,
                    "cleanup": [],
                }
            },
            "PUBLICATION_EXTENT",
        ),
        ({"latest": "ckp-" + "9" * 32}, "PUBLICATION_COVERAGE"),
        ({"ranges": ((0, 2),)}, "PUBLICATION_COVERAGE"),
        ({"ranges": ((0, 1), (2, 3))}, "PUBLICATION_COVERAGE"),
        ({"open": 1}, "PUBLICATION_ATTEMPT_OPEN"),
        ({"published": True}, "GENERATION_PUBLISHED"),
    ]
    for change, code in cases:
        refused = p.eligibility(eligible_facts(**change))
        assert refused, change
        if code is not None:
            assert refused == (code,), (change, refused)
    # The continuation basis: barrier, its own end checkpoint, kept old members.
    old = ("chk-a", 0, 2, "att-old")
    new = ("chk-b", 2, 3, "att-" + "3" * 32)
    continuation = dict(
        basis="CONTINUATION",
        reconciled=True,
        end_checkpoint="ckp-" + "2" * 32,
        predecessor=frozenset({"chk-a"}),
        members=(old, new),
    )
    assert p.eligibility(eligible_facts(**continuation)) == ()
    for change in (
        {"reconciled": False},
        {"end_checkpoint": "ckp-" + "8" * 32},
        {"predecessor": frozenset({"chk-z"})},
        {"members": (old, ("chk-b", 2, 3, "att-foreign"))},
    ):
        assert p.eligibility(eligible_facts(**{**continuation, **change})) == (
            "PUBLICATION_BASIS",
        )


def test_route_cleanup_vocabulary_and_late_cancel_flags():
    actual = {
        "postgres_rows": ("CLOSED", ("FAILED", "NOT_STARTED")),
        "postgres_adbc": (
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            ("FAILED_REMOTE_UNOBSERVED", "CLOSED", "NOT_STARTED"),
        ),
        "mysql_rows": (
            "LOCAL_CLOSED_REMOTE_UNOBSERVED",
            ("FAILED", "CLOSED", "NOT_STARTED"),
        ),
    }
    for route, (clean, refused) in actual.items():
        assert (
            p.eligibility(
                eligible_facts({"route": route, "cleanup": clean}, route=route)
            )
            == ()
        )
        for term in refused:
            assert p.eligibility(
                eligible_facts({"route": route, "cleanup": term}, route=route)
            ) == ("PUBLICATION_CLEANUP",)
    # A late cancel request after completed native work is recorded, not a failure.
    for flags in ([True, False, False], [True, True, False], [True, True, True]):
        assert p.eligibility(eligible_facts({"cancel": flags})) == ()


def test_exact_coverage_model():
    from itertools import product

    assert p.covers([(0, 0)], 0) and not p.covers([], 0) and not p.covers([(0, 0)], 1)
    checked = 0
    for n in range(0, 6):
        for cuts in product((False, True), repeat=max(n - 1, 0)):
            bounds = [0] + [i + 1 for i, cut in enumerate(cuts) if cut] + [n]
            blocks = list(zip(bounds, bounds[1:]))
            for keep in product((False, True), repeat=len(blocks)):
                ranges = [b for b, k in zip(blocks, keep) if k]
                complete = all(keep)  # [0, 0) is the complete empty result
                assert p.covers(ranges, n) is complete
                assert not p.covers(ranges + [(n, n)], n) or n == 0
                checked += 1
    assert checked > 50
    assert not p.covers([(0, 2), (1, 3)], 3) and not p.covers([(0, 2), (2, 2)], 2)
    assert not p.covers([(0, 3)], -1) and not p.covers([(0, 3)], None)


# --- v6 boundary ----------------------------------------------------------------


def test_v6_is_an_explicit_closed_capability_set(tmp_path, built):
    if not qualified(tmp_path):
        return
    v5, v6 = w.expected_schema(w.FORMAT_V5), w.expected_schema(w.FORMAT_V6)
    added = {row[1] for row in v6} - {row[1] for row in v5}
    assert {
        "closing_observation",
        "publication",
        "attempt_subject",
        "retention_subject",
    } <= added
    assert {row for row in v5} <= {row for row in v6}
    workspace = w.create_workspace(str(tmp_path / "v6"), format=w.FORMAT_V6)
    try:
        assert w.supports(workspace, "complete-publication")
        envelope = json.loads((tmp_path / "v6" / "workspace.json").read_text())
        assert envelope["features"] == [
            "result-chunks",
            "saved-replay",
            "extraction-resume",
            "cooperative-delivery",
            "complete-publication",
        ]
        assert workspace.use().execute("PRAGMA user_version").fetchone() == (6,)
    finally:
        workspace.close()
    w.open_workspace(str(tmp_path / "v6"), expected_identity=workspace.identity).close()
    raw = (tmp_path / "v6" / "workspace.json").read_bytes()
    for bad in (
        raw.replace(b',"complete-publication"', b""),
        raw.replace(b"job-workspace.v6", b"job-workspace.v7"),
    ):
        with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
            w.read_envelope(bad)
    # Older formats: S16 refuses before any change; record_attempt is unchanged.
    template, compiled = built
    old, job, publisher, binding, record, generation = s15.store(
        tmp_path / "v5", template
    )
    try:
        before = probe.rows(old, "SELECT * FROM operation")
        with pytest.raises(JobStoreError, match="WORKSPACE_PUBLICATION_FORMAT"):
            p.publication(old, job, generation)
        with pytest.raises(JobStoreError, match="WORKSPACE_PUBLICATION_FORMAT"):
            p.accept_publication(
                old,
                job,
                generation,
                checkpoint="ckp-" + "0" * 32,
                closing="att-" + "0" * 32,
                purpose="s16",
                route="postgres_rows",
                isolation="stable",
                values=(1,),
                seconds=60,
                **s13.trust(compiled),
            )
        assert probe.rows(old, "SELECT * FROM operation") == before
        session = probe.ordinary(publisher, generation, binding, [2])
        terminal = [o for o in s.job_record(old, job).operations][-1]
        assert terminal.kind == "attempt_terminal"
        request = json.loads(
            probe.rows(
                old,
                "SELECT request FROM operation WHERE identity = ?",
                (terminal.operation,),
            )[0][0]
        )
        assert "observation" not in request and session.observed == 2
        assert not [
            row
            for row in probe.rows(old, "SELECT name FROM sqlite_schema")
            if row[0] in ("closing_observation", "publication")
        ]
        verify_store(old)
    finally:
        publisher.close()
        old.close()


# --- closing observation ----------------------------------------------------------


def test_closing_observation_is_written_with_its_terminal(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 1])
    attempt = session.attempt.identity
    assert probe.rows(x.workspace, "SELECT * FROM closing_observation") == [
        (attempt, x.generation, x.job, 1, 3, None, "[]", x.publisher.epoch)
    ]
    operation = [o for o in s.job_record(x.workspace, x.job).operations][-1]
    request = json.loads(
        probe.rows(
            x.workspace,
            "SELECT request FROM operation WHERE identity = ?",
            (operation.operation,),
        )[0][0]
    )
    assert request["observation"] == {
        "cleanup": [],
        "closed": True,
        "failure": None,
        "rows": 3,
    }
    # Categories only: phase and exception kind, never message text.
    failed = probe.ordinary(
        x.publisher,
        another(x),
        x.binding,
        [1],
        transaction="UNKNOWN",
        primary=("transaction", "OperationalError"),
        cleanup="FAILED",
        cleanup_errors=[("connection_close", "OSError")],
    )
    row = probe.rows(
        x.workspace,
        "SELECT failure, cleanup FROM closing_observation WHERE attempt = ?",
        (failed.attempt.identity,),
    )[0]
    assert row == (
        '["transaction","OperationalError"]',
        '[["connection_close","OSError"]]',
    )
    # NOT_EXECUTED and INTERRUPTED never have a closing observation.
    third = another(x)
    attempt3 = s.open_attempt(x.publisher, third, x.binding, operation=op())
    s.record_not_executed(x.publisher, attempt3, operation=op())
    fourth = another(x)
    s.open_attempt(x.publisher, fourth, x.binding, operation=op())
    fresh = r2.takeover(x.workspace, x.job, x.publisher)
    x.publisher = fresh
    assert len(probe.rows(x.workspace, "SELECT * FROM closing_observation")) == 2
    counts = verify_store(x.workspace)
    assert (counts["closing_observations"], counts["publications"]) == (2, 0)


# --- ordinary publication -----------------------------------------------------------


def test_ordinary_publication_commits_once_and_is_queryable(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2, 1])
    closing = session.attempt.identity
    assert p.publication(x.workspace, x.job, x.generation) is None
    prepared, operation, result = probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, closing
    )
    assert result.observation == "COMMITTED_THIS_CALL" and prepared.state == "PUBLISHED"
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    found = p.publication(x.workspace, x.job, x.generation)
    assert found is not None and found.integrity == "RECORDED"
    assert (found.checkpoint, found.extent, found.members, found.closing) == (
        snapshot.checkpoint,
        5,
        3,
        closing,
    )
    assert (found.operation, found.retention) == (operation, prepared.retention)
    assert json.loads(found.descriptor) == {
        "basis": "CAPTURE",
        "chunk": "pietto.result-chunk.v1",
        "coordinates": None,
        "format": "pietto.publication.v1",
        "kind": "ORDINARY",
        "workspace": "pietto.job-workspace.v6",
    }
    assert p.publications(x.workspace, x.job) == (found,)
    queried = s.query_operation(x.workspace, operation)
    assert queried is not None and queried.get("retention") == found.retention
    # Publication-owned protection: protected, never released by a generic release.
    assert {m.chunk for m in snapshot.members} <= c.protected_chunks(x.workspace, x.job)
    with pytest.raises(JobStoreError, match="RETENTION_PUBLISHED"):
        c.release_retention(x.publisher, found.retention, operation=op())
    # Same operation replays the historical fact; nothing new is published.
    again = p.publish_generation(x.publisher, prepared, operation=operation)
    assert again.observation == "PREVIOUSLY_COMMITTED"
    assert dict(again.result) == dict(result.result)
    with pytest.raises(JobStoreError, match="GENERATION_PUBLISHED"):
        p.publish_generation(x.publisher, prepared, operation=op())
    # A published generation takes no new attempt and no second publication.
    with pytest.raises(JobStoreError, match="GENERATION_PUBLISHED"):
        s.open_attempt(x.publisher, x.generation, x.binding, operation=op())
    with pytest.raises(JobStoreError, match="GENERATION_PUBLISHED"):
        probe.publish(x.workspace, x.job, x.publisher, x.generation, x.built, closing)
    assert len(probe.rows(x.workspace, "SELECT * FROM publication")) == 1
    counts = verify_store(x.workspace)
    assert (counts["publications"], counts["closing_observations"]) == (1, 1)


def test_empty_ordinary_result_publishes_its_schema_member(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [])
    _prepared, _operation, result = probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    found = p.publication(x.workspace, x.job, x.generation)
    assert result.get("extent") == 0 and found is not None
    assert (found.extent, found.members) == (0, 1)
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    assert [(m.start, m.stop, m.batches) for m in snapshot.members] == [(0, 0, 0)]
    verify_store(x.workspace)


INELIGIBLE = {
    "early_close": (
        dict(source="EARLY_CLOSE", delivery="INCOMPLETE"),
        "PUBLICATION_SOURCE",
    ),
    "transaction_unknown": (
        dict(transaction="UNKNOWN", primary=("transaction", "OperationalError")),
        "PUBLICATION_TRANSACTION",
    ),
    "rollback": (dict(transaction="ROLLBACK_ACK"), "PUBLICATION_TRANSACTION"),
    "delivery_failed": (
        dict(delivery="FAILED", primary=("consumer", "ValueError")),
        "PUBLICATION_DELIVERY",
    ),
    "cleanup_failed": (
        dict(cleanup="FAILED", cleanup_errors=[("connection_close", "OSError")]),
        "PUBLICATION_CLEANUP",
    ),
    "primary": (
        dict(primary=("finalization", "ExecutionError")),
        "PUBLICATION_PRIMARY",
    ),
    "not_qualified": (dict(qualified=False), "PUBLICATION_QUALIFICATION"),
    "no_transaction": (dict(opened=False), "PUBLICATION_QUALIFICATION"),
    "guard_violated": (dict(guards=["VIOLATED"]), "PUBLICATION_GUARDS"),
    "guard_unknown": (dict(guards=["FULFILLED", "UNKNOWN"]), "PUBLICATION_GUARDS"),
}


@pytest.mark.parametrize("case", sorted(INELIGIBLE))
def test_ineligible_closing_refuses_and_releases_its_preparation(setup, case):
    if setup is None:
        return
    x = setup
    close, code = INELIGIBLE[case]
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 1], **close)
    acceptance = probe.accept(
        x.workspace, x.job, x.generation, x.built, session.attempt.identity
    )
    with pytest.raises(JobStoreError, match=code):
        p.prepare_publication(x.publisher, acceptance, operation=op())
    (preparation,) = preparations(x)
    assert released(x, preparation)
    assert p.publication(x.workspace, x.job, x.generation) is None
    verify_store(x.workspace)


def test_missing_closing_observation_and_count_mismatch_refuse(setup):
    if setup is None:
        return
    x = setup
    # The publisher reports no native owner: NOT_EXECUTED is never a closing basis.
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2], end=False)
    probe.close_owner(session.owner, session.observed)
    session.end(operation=op())
    s.record_not_executed(x.publisher, session.attempt, operation=op())
    with pytest.raises(JobStoreError, match="PUBLICATION_CLOSING_UNOBSERVED"):
        probe.publish(
            x.workspace,
            x.job,
            x.publisher,
            x.generation,
            x.built,
            session.attempt.identity,
        )
    # Interrupted (a later epoch closed it): no observation can exist.
    g2 = another(x)
    session2 = probe.ordinary(x.publisher, g2, x.binding, [2], end=False)
    x.publisher = r2.takeover(x.workspace, x.job, x.publisher)
    with pytest.raises(JobStoreError, match="PUBLICATION_CLOSING_UNOBSERVED"):
        probe.publish(
            x.workspace, x.job, x.publisher, g2, x.built, session2.attempt.identity
        )
    # The owner's own checked count disagrees with the captured extent.
    g3 = another(x)
    session3 = probe.ordinary(x.publisher, g3, x.binding, [2], end=False)
    probe.close_owner(session3.owner, session3.observed + 1)
    session3.end(operation=op())
    s.record_attempt(x.publisher, session3.attempt, session3.owner, operation=op())
    with pytest.raises(JobStoreError, match="PUBLICATION_EXTENT"):
        probe.publish(
            x.workspace, x.job, x.publisher, g3, x.built, session3.attempt.identity
        )
    assert all(released(x, item) for item in preparations(x))
    assert p.publications(x.workspace, x.job) == ()
    verify_store(x.workspace)


def test_late_cancel_after_completed_work_is_not_a_failure(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(
        x.publisher, x.generation, x.binding, [2], cancel=(True, True, False)
    )
    recorded = s.job_record(x.workspace, x.job).attempts[0].outcome
    assert recorded is not None and dict(recorded)["cancel"] == (True, True, False)
    _prepared, _operation, result = probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    assert result.observation == "COMMITTED_THIS_CALL"
    verify_store(x.workspace)


def test_holes_staging_and_open_attempts_never_publish_complete(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    s15.arrow_free(monkeypatch)
    # [0, 2) and [4, 6) committed; the [2, 4) file is durable but unpublished.
    session = probe.ordinary(
        x.publisher, x.generation, x.binding, [2, 2, 2], order=[0, 2]
    )
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    assert snapshot.holes == ((2, 4),) and snapshot.observed_end == 6
    assert session.staged and c.classify_files(x.workspace)["orphans"]
    # A sink holding every effect of the committed prefix closes no hole.
    handle = s15.sink(x.root / "sink")
    _stream, delivery = s15.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, handle
    )
    s15.deliver(delivery, 2)
    delivery.close()
    effects = s15.effects(handle)
    assert [effect[0] for effect in effects] == [0, 1]
    with pytest.raises(JobStoreError, match="PUBLICATION_COVERAGE"):
        probe.publish(
            x.workspace,
            x.job,
            x.publisher,
            x.generation,
            x.built,
            session.attempt.identity,
        )
    assert s15.effects(handle) == effects
    handle.close()
    # A full last batch is not an end: without the owner's terminal, refuse.
    g2 = another(x)
    open_session = probe.ordinary(x.publisher, g2, x.binding, [2, 2], end=False)
    with pytest.raises(JobStoreError, match="PUBLICATION_CLOSING_UNOBSERVED"):
        probe.publish(
            x.workspace, x.job, x.publisher, g2, x.built, open_session.attempt.identity
        )
    probe.close_owner(open_session.owner, open_session.observed)
    open_session.end(operation=op())
    s.record_attempt(
        x.publisher, open_session.attempt, open_session.owner, operation=op()
    )
    probe.publish(
        x.workspace, x.job, x.publisher, g2, x.built, open_session.attempt.identity
    )
    assert [item.generation for item in p.publications(x.workspace, x.job)] == [g2]
    verify_store(x.workspace)


# --- R2 basis ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def refined(tmp_path_factory):
    return r2.refined_template(tmp_path_factory.mktemp("s16-r2") / "bound")


@pytest.fixture
def recovered(tmp_path, refined, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    r2.synthetic(monkeypatch)
    probe.arrow_free(monkeypatch)
    template, compiled, values = refined
    workspace, job, publisher, binding, record, generation = probe.store(
        tmp_path / "workspace", template, values
    )
    x = SimpleNamespace(
        workspace=workspace,
        job=job,
        publisher=publisher,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        values=values,
    )
    yield x
    for item in (x.publisher, x.workspace):
        if not item._closed:
            item.close()


def continue_from(x, sizes, *, page_rows=3, **close):
    """Takeover, fresh recovery acceptance, a new continuation driven over
    `sizes` pages and its normal end with a recorded closing observation."""
    fresh, acceptance, attempt = r2.recover(
        x.workspace, x.job, x.generation, x.built, x.values, previous=x.publisher
    )
    x.publisher = fresh
    session = ext.begin_continuation(
        fresh,
        acceptance,
        attempt,
        r2.owner(acceptance.binding, batch_rows=page_rows),
        operation=op(),
    )
    r2.drive(session, sizes)
    ended = probe.finish_continuation(session, **close)
    return session, ended


def publish_r2(x, closing):
    return probe.publish(
        x.workspace,
        x.job,
        x.publisher,
        x.generation,
        x.built,
        closing,
        values=x.values,
    )


def test_r2_publication_binds_the_reconciled_closing_attempt(recovered):
    if recovered is None:
        return
    x = recovered
    original, _ = r2.extract(
        x.publisher, x.generation, x.binding, [2, 2, 2], order=[0, 2]
    )
    # Before R2: the only attempt is open (crashed), then INTERRUPTED: refused.
    with pytest.raises(JobStoreError, match="PUBLICATION_CLOSING_UNOBSERVED"):
        publish_r2(x, original.attempt.identity)
    session, ended = continue_from(x, [3, 3, 3])
    history = probe.rows(x.workspace, "SELECT * FROM attempt_terminal")
    closing = session.attempt.identity
    old_terminal = probe.rows(
        x.workspace,
        "SELECT * FROM attempt_terminal WHERE attempt = ?",
        (original.attempt.identity,),
    )
    assert old_terminal and dict(json.loads(old_terminal[0][3]))["source"] == "UNKNOWN"
    with pytest.raises(JobStoreError, match="PUBLICATION_CLOSING_UNOBSERVED"):
        publish_r2(x, original.attempt.identity)
    _prepared, _operation, result = publish_r2(x, closing)
    found = p.publication(x.workspace, x.job, x.generation)
    assert found is not None and found.closing == closing
    assert found.checkpoint == ended.get("checkpoint") and found.extent == 9
    assert json.loads(found.descriptor)["basis"] == "CONTINUATION"
    assert json.loads(found.descriptor)["coordinates"] == "pietto.coordinate-atoms.v1"
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    producers = {m.stop: m.attempt for m in snapshot.members}
    assert producers[2] == producers[6] == original.attempt.identity
    assert {producers[3], producers[4], producers[9]} == {closing}
    # Old history is byte-identical: the INTERRUPTED UNKNOWN stays UNKNOWN.
    assert probe.rows(x.workspace, "SELECT * FROM attempt_terminal") == history
    assert result.get("extent") == 9
    verify_store(x.workspace)


def test_r2_without_continuation_uses_the_original_capture(recovered):
    if recovered is None:
        return
    x = recovered
    session, _ = r2.extract(x.publisher, x.generation, x.binding, [2, 1])
    probe.close_owner(session.owner, session.observed)
    session.end(operation=op())
    s.record_attempt(x.publisher, session.attempt, session.owner, operation=op())
    publish_r2(x, session.attempt.identity)
    found = p.publication(x.workspace, x.job, x.generation)
    assert found is not None and json.loads(found.descriptor)["basis"] == "CAPTURE"
    verify_store(x.workspace)


def test_r2_incomplete_unrelated_and_changed_basis_refuse(recovered, tmp_path):
    if recovered is None:
        return
    x = recovered
    r2.extract(x.publisher, x.generation, x.binding, [2, 2])
    # An incomplete re-enumeration: the continuation ended early.
    session, ended = continue_from(x, [3], source="EARLY_CLOSE", delivery="INCOMPLETE")
    assert ended.get("checkpoint") is None
    with pytest.raises(JobStoreError, match="PUBLICATION_SOURCE"):
        publish_r2(x, session.attempt.identity)
    # An unrelated later success (another generation's attempt) is no basis.
    other = s.register_generation(
        x.publisher,
        x.record,
        x.binding,
        route="postgres_rows",
        isolation="stable",
        operation=op(),
    ).get("generation")
    foreign, _ = r2.extract(x.publisher, other, x.binding, [1])
    probe.close_owner(foreign.owner, foreign.observed)
    foreign.end(operation=op())
    s.record_attempt(x.publisher, foreign.attempt, foreign.owner, operation=op())
    with pytest.raises(JobStoreError, match="PUBLICATION_BASIS"):
        publish_r2(x, foreign.attempt.identity)
    # A complete continuation now succeeds; a changed stored specification
    # (injected edit) refuses any new acceptance.
    complete, _ = continue_from(x, [3, 3])
    root = x.workspace.root
    connection = sqlite3.connect(os.path.join(root, "store.sqlite"))
    try:
        connection.execute(
            "UPDATE extraction SET specification = replace(specification,"
            " 'stable', 'serializable') WHERE generation = ?",
            (x.generation,),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(JobStoreError, match="EXTRACTION_SPECIFICATION"):
        publish_r2(x, complete.attempt.identity)
    assert p.publication(x.workspace, x.job, x.generation) is None


# --- member checks and races ----------------------------------------------------


def mutate(x, member, how):
    path = os.path.join(x.workspace.root, "chunks", member.file)
    data = open(path, "rb").read()
    if how == "missing":
        os.unlink(path)
    elif how == "size":
        with open(path, "ab") as stream:
            stream.write(b"\0")
    elif how == "digest":
        with open(path, "r+b") as stream:
            stream.seek(len(data) - 1)
            stream.write(bytes([data[-1] ^ 1]))
    elif how == "replaced":
        os.unlink(path)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, data)
        finally:
            os.close(descriptor)


@pytest.mark.parametrize(
    "how,code",
    [
        ("missing", "CHUNK_MISSING"),
        ("size", "CHUNK_SIZE"),
        ("digest", "CHUNK_DIGEST"),
    ],
)
def test_late_member_damage_is_refused_before_visibility(setup, how, code):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2, 1])
    last = c.checkpoint_snapshot(x.workspace, x.job, x.generation).members[-1]
    mutate(x, last, how)
    acceptance = probe.accept(
        x.workspace, x.job, x.generation, x.built, session.attempt.identity
    )
    with pytest.raises(JobStoreError, match=code):
        p.prepare_publication(x.publisher, acceptance, operation=op())
    assert all(released(x, item) for item in preparations(x))
    assert p.publication(x.workspace, x.job, x.generation) is None


def test_a_member_object_replaced_after_preparation_is_refused_at_commit(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2])
    acceptance = probe.accept(
        x.workspace, x.job, x.generation, x.built, session.attempt.identity
    )
    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())
    first = c.checkpoint_snapshot(x.workspace, x.job, x.generation).members[0]
    mutate(x, first, "replaced")  # identical bytes, a different file object
    with pytest.raises(JobStoreError, match="CHUNK_OBJECT"):
        p.publish_generation(x.publisher, prepared, operation=op())
    assert prepared.state == "REFUSED" and released(x, prepared.retention)
    with pytest.raises(JobStoreError, match="PREPARED_USED"):
        p.publish_generation(x.publisher, prepared, operation=op())
    assert p.publication(x.workspace, x.job, x.generation) is None
    verify_store(x.workspace)


def test_cancel_before_publish_refuses_and_publish_before_cancel_keeps(setup):
    if setup is None:
        return
    x = setup
    # Publication first: a later cancellation retracts nothing.
    first = probe.ordinary(x.publisher, x.generation, x.binding, [2])
    _prepared, operation, _ = probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, first.attempt.identity
    )
    g2 = another(x)
    second = probe.ordinary(x.publisher, g2, x.binding, [1])
    acceptance = probe.accept(x.workspace, x.job, g2, x.built, second.attempt.identity)
    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())
    s.cancel_job(x.publisher, operation=op())
    # Cancellation first (for g2): the publication transaction refuses.
    with pytest.raises(JobStoreError, match="JOB_STATE"):
        p.publish_generation(x.publisher, prepared, operation=op())
    assert released(x, prepared.retention)
    assert p.publication(x.workspace, x.job, g2) is None
    kept = p.publication(x.workspace, x.job, x.generation)
    assert kept is not None and kept.operation == operation
    assert not released(x, kept.retention)
    assert s.job_record(x.workspace, x.job).state == "CANCELLED"
    with pytest.raises(JobStoreError, match="RETENTION_PUBLISHED"):
        c.release_retention(x.publisher, kept.retention, operation=op())
    # New saved reads obey cancellation; the historical record does not change.
    with pytest.raises(JobStoreError, match="JOB_STATE"):
        r.register_consumer(
            x.publisher,
            s13.accept(x.workspace, x.job, x.generation, x.built),
            operation=op(),
        )
    assert p.publications(x.workspace, x.job) == (kept,)
    verify_store(x.workspace)


def test_stale_publisher_conflict_and_operation_replay(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2])
    closing = session.attempt.identity
    acceptance = probe.accept(x.workspace, x.job, x.generation, x.built, closing)
    one = p.prepare_publication(x.publisher, acceptance, operation=op())
    two = p.prepare_publication(x.publisher, acceptance, operation=op())
    x.publisher.revision -= 1
    with pytest.raises(JobStoreError, match="PUBLISHER_REVISION") as stale:
        p.publish_generation(x.publisher, one, operation=op())
    x.publisher.revision += 1
    # Not even the release can pass a wrong revision: kept, never guessed.
    assert any("PUBLISHER_REVISION" in n for n in stale.value.__notes__)
    assert not released(x, one.retention) and not released(x, two.retention)
    operation = op()
    assert (
        p.publish_generation(x.publisher, two, operation=operation).observation
        == "COMMITTED_THIS_CALL"
    )
    with pytest.raises(JobStoreError, match="PREPARED_USED"):
        p.publish_generation(x.publisher, one, operation=operation)
    # A different prepared subject under the same operation conflicts.
    g2 = another(x)
    other = probe.ordinary(x.publisher, g2, x.binding, [1])
    four = p.prepare_publication(
        x.publisher,
        probe.accept(x.workspace, x.job, g2, x.built, other.attempt.identity),
        operation=op(),
    )
    with pytest.raises(JobStoreError, match="OPERATION_CONFLICT"):
        p.publish_generation(x.publisher, four, operation=operation)
    assert released(x, four.retention)
    # A stale publisher (lock lost, a new claim) is not a cancellation.
    five = p.prepare_publication(
        x.publisher,
        probe.accept(x.workspace, x.job, g2, x.built, other.attempt.identity),
        operation=op(),
    )
    os.unlink(os.path.join(x.workspace.root, "locks", x.job + ".lock"))
    newer = s.claim_publisher(x.workspace, x.job, operation=op())
    with pytest.raises(JobStoreError, match="PUBLISHER_STALE") as stale:
        p.publish_generation(x.publisher, five, operation=op())
    assert any("preparation protection kept" in n for n in stale.value.__notes__)
    assert not released(x, five.retention)
    x.publisher.close()
    x.publisher = newer
    assert s.job_record(x.workspace, x.job).state == "ACTIVE"
    assert [i.generation for i in p.publications(x.workspace, x.job)] == [x.generation]
    verify_store(x.workspace)


def test_acceptance_and_prepared_bounds(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2])
    closing = session.attempt.identity
    for overrides, code in (
        ({"values": (2,)}, "BINDING_VECTOR"),
        ({"values": (True,)}, "BINDING_VECTOR"),
        ({"route": "mysql_rows"}, "ACCEPTANCE_ROUTE"),
        ({"isolation": "serializable"}, "ACCEPTANCE_ISOLATION"),
        ({"expected_pin": "0" * 64}, "JOB_TRUST_INPUT"),
        ({"checkpoint": "ckp-" + "0" * 32}, "CHECKPOINT_UNKNOWN"),
        ({"closing": "nope"}, "PUBLICATION_BASIS"),
        ({"purpose": ""}, "ACCEPTANCE_PURPOSE"),
        ({"seconds": 0}, "ACCEPTANCE_BOUND"),
    ):
        with pytest.raises(JobStoreError, match=code):
            probe.accept(
                x.workspace,
                x.job,
                x.generation,
                x.built,
                **{"closing": closing, **overrides},
            )
    acceptance = probe.accept(x.workspace, x.job, x.generation, x.built, closing)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_COPY"):
        pickle.dumps(acceptance)
    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())
    with pytest.raises(JobStoreError, match="PREPARED_COPY"):
        pickle.dumps(prepared)
    forged = p.PreparedPublication.__new__(p.PreparedPublication)
    with pytest.raises(JobStoreError, match="PREPARED_UNKNOWN"):
        p.publish_generation(x.publisher, forged, operation=op())
    # Expiry after slow validation: the commit transaction refuses.
    now = p._monotonic()
    monkeypatch.setattr(p, "_monotonic", lambda: now + 601)
    with pytest.raises(JobStoreError, match="ACCEPTANCE_EXPIRED"):
        p.publish_generation(x.publisher, prepared, operation=op())
    monkeypatch.setattr(p, "_monotonic", lambda: now)
    assert released(x, prepared.retention)
    # A released (or missing) preparation protection refuses.
    again = p.prepare_publication(x.publisher, acceptance, operation=op())
    c.release_retention(x.publisher, again.retention, operation=op())
    with pytest.raises(JobStoreError, match="RETENTION_RELEASED"):
        p.publish_generation(x.publisher, again, operation=op())
    missing = p.prepare_publication(x.publisher, acceptance, operation=op())
    own, missing.retention = missing.retention, "ret-" + "0" * 32
    with pytest.raises(JobStoreError, match="RETENTION_UNKNOWN") as unknown:
        p.publish_generation(x.publisher, missing, operation=op())
    assert any("preparation protection kept" in n for n in unknown.value.__notes__)
    c.release_retention(x.publisher, own, operation=op())
    # Membership that no longer matches the prepared subject refuses at commit.
    stale = p.prepare_publication(x.publisher, acceptance, operation=op())
    stale.members = stale.members[:-1]
    with pytest.raises(JobStoreError, match="PUBLICATION_MEMBERSHIP"):
        p.publish_generation(x.publisher, stale, operation=op())
    assert released(x, stale.retention)
    # A newly opened attempt of the generation blocks; its terminal unblocks.
    third = p.prepare_publication(x.publisher, acceptance, operation=op())
    extra = s.open_attempt(x.publisher, x.generation, x.binding, operation=op())
    with pytest.raises(JobStoreError, match="PUBLICATION_ATTEMPT_OPEN"):
        p.publish_generation(x.publisher, third, operation=op())
    s.record_not_executed(x.publisher, extra, operation=op())
    fourth = p.prepare_publication(x.publisher, acceptance, operation=op())
    p.publish_generation(x.publisher, fourth, operation=op())
    verify_store(x.workspace)


def test_injected_faults_keep_the_primary_and_the_ambiguity(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2])
    closing = session.attempt.identity
    acceptance = probe.accept(x.workspace, x.job, x.generation, x.built, closing)
    # Admission (ENOSPC-like budget) refuses before any transaction.
    original = s.admit

    def full(workspace, payload, *, control=False):
        if not control:
            raise JobStoreError("WORKSPACE_BUDGET")
        return original(workspace, payload, control=control)

    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())
    monkeypatch.setattr(s, "admit", full)
    with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
        p.publish_generation(x.publisher, prepared, operation=op())
    monkeypatch.setattr(s, "admit", original)
    assert released(x, prepared.retention)
    # A busy writer elsewhere: refused, and the release is also busy (kept).
    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())
    other = sqlite3.connect(os.path.join(x.workspace.root, "store.sqlite"), timeout=0)
    other.execute("BEGIN IMMEDIATE")
    try:
        x.workspace.use().execute("PRAGMA busy_timeout = 10")
        with pytest.raises(JobStoreError, match="STORE_BUSY") as busy:
            p.publish_generation(x.publisher, prepared, operation=op())
        assert any("STORE_BUSY" in n for n in busy.value.__notes__)
    finally:
        other.rollback()
        other.close()
        x.workspace.use().execute("PRAGMA busy_timeout = 5000")
    assert not released(x, prepared.retention)
    # An uncertain COMMIT: nothing is released, the handle retires, query later.
    prepared = p.prepare_publication(x.publisher, acceptance, operation=op())

    def lost(connection):
        connection.execute("COMMIT")
        raise OSError("reply lost")

    commit = w.commit
    monkeypatch.setattr(w, "commit", lost)
    operation = op()
    with pytest.raises(JobStoreError, match="STORE_COMMIT_UNKNOWN"):
        p.publish_generation(x.publisher, prepared, operation=operation)
    monkeypatch.setattr(w, "commit", commit)
    assert prepared.state == "UNKNOWN"
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        p.publication(x.workspace, x.job, x.generation)
    fresh = w.open_workspace(x.workspace.root, expected_identity=x.workspace.identity)
    try:
        found = p.publication(fresh, x.job, x.generation)
        queried = s.query_operation(fresh, operation)
        assert found is not None and found.operation == operation
        assert queried is not None and queried.kind == "publish_generation"
        assert found.retention == prepared.retention
        verify_store(fresh)
    finally:
        fresh.close()


def test_history_survives_cancel_corruption_and_current_read_refusal(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 1])
    probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    recorded = p.publication(x.workspace, x.job, x.generation)
    s.cancel_job(x.publisher, operation=op())
    snapshot = c.checkpoint_snapshot(x.workspace, x.job, x.generation)
    mutate(x, snapshot.members[0], "digest")
    # The historical publication stays; a current read refuses separately.
    assert p.publication(x.workspace, x.job, x.generation) == recorded
    with pytest.raises(JobStoreError, match="CHUNK_DIGEST"):
        probe.arrow_free_verify(x.workspace, None, snapshot)
    assert {m.chunk for m in snapshot.members} <= c.protected_chunks(x.workspace, x.job)
    verify_store(x.workspace)


def test_protection_survives_reader_release_retirement_and_publisher_change(
    setup, monkeypatch
):
    if setup is None:
        return
    x = setup
    s15.arrow_free(monkeypatch)
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2])
    # A reader and a stream protect the same checkpoint independently.
    acceptance = s13.accept(x.workspace, x.job, x.generation, x.built)
    consumer = r.register_consumer(x.publisher, acceptance, operation=op())
    handle = s15.sink(x.root / "sink")
    stream, delivery = s15.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, handle
    )
    s15.deliver(delivery, 4)
    delivery.close()
    probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    found = p.publication(x.workspace, x.job, x.generation)
    assert found is not None
    c.release_retention(x.publisher, consumer.get("retention"), operation=op())
    d.retire_stream(x.publisher, stream, operation=op())
    x.publisher = r2.takeover(x.workspace, x.job, x.publisher)
    members = {
        m.chunk for m in c.checkpoint_snapshot(x.workspace, x.job, x.generation).members
    }
    assert members <= c.protected_chunks(x.workspace, x.job)
    assert not released(x, found.retention)
    with pytest.raises(JobStoreError, match="RETENTION_PUBLISHED"):
        c.release_retention(x.publisher, found.retention, operation=op())
    handle.close()
    verify_store(x.workspace)


def test_s15_effects_and_sink_state_stay_separate_from_publication(setup, monkeypatch):
    if setup is None:
        return
    x = setup
    s15.arrow_free(monkeypatch)
    # Early provisional effects, then the source fails: publication refused.
    failed = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2], end=False)
    handle = s15.sink(x.root / "sink")
    stream, delivery = s15.registered(
        x.workspace, x.job, x.publisher, x.generation, x.built, handle
    )
    s15.deliver(delivery, 2)
    delivery.close()
    probe.close_owner(
        failed.owner,
        failed.observed,
        source="FAILED",
        delivery="FAILED",
        transaction="ROLLBACK_ACK",
        primary=("read", "OperationalError"),
    )
    failed.end(operation=op())
    s.record_attempt(x.publisher, failed.attempt, failed.owner, operation=op())
    effects = s15.effects(handle)
    with pytest.raises(JobStoreError, match="PUBLICATION_SOURCE"):
        probe.publish(
            x.workspace,
            x.job,
            x.publisher,
            x.generation,
            x.built,
            failed.attempt.identity,
        )
    assert s15.effects(handle) == effects and len(effects) == 4
    # A complete local publication beside an unresolved stream on another generation.
    g2 = another(x)
    done = probe.ordinary(x.publisher, g2, x.binding, [2, 2, 1])
    other = s15.sink(x.root / "sink2", namespace="s16.other")
    stream2, delivery2 = s15.registered(
        x.workspace, x.job, x.publisher, g2, x.built, other
    )
    issued = delivery2.next(2, operation=op())
    assert isinstance(issued, d.Issued)
    delivery2.send(issued)  # replies received, never confirmed locally
    before = (d.stream_state(x.workspace, stream2), s15.effects(other))
    acks = probe.rows(x.workspace, "SELECT count(*) FROM acknowledgement")
    probe.publish(x.workspace, x.job, x.publisher, g2, x.built, done.attempt.identity)
    assert (d.stream_state(x.workspace, stream2), s15.effects(other)) == before
    assert before[0].unresolved == ((0, 2),) and before[0].position == 0
    assert probe.rows(x.workspace, "SELECT count(*) FROM acknowledgement") == acks
    delivery2.close()
    for item in (handle, other):
        item.close()
    verify_store(x.workspace)


def test_r1_reads_a_publication_only_with_a_fresh_saved_read(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2, 1])
    early = s13.accept(x.workspace, x.job, x.generation, x.built)
    r.register_consumer(x.publisher, early, operation=op())
    probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    found = p.publication(x.workspace, x.job, x.generation)
    assert found is not None
    with pytest.raises(JobStoreError, match="ACCEPTANCE_UNKNOWN"):
        r.register_consumer(x.publisher, found, operation=op())  # type: ignore[arg-type]
    acceptance = s13.accept(
        x.workspace,
        x.job,
        x.generation,
        x.built,
        checkpoint=found.checkpoint,
        extent=found.extent,
        scope="complete_capture",
    )
    r.register_consumer(x.publisher, acceptance, operation=op())
    replay = r.open_replay(x.publisher, acceptance, operation=op())
    extents, end = s13.drain(replay, 2)
    assert extents == [(0, 2), (2, 4), (4, 5)] and end.extent == found.extent
    state = r.consumer_state(x.workspace, early.consumer)
    assert (state.checkpoint, state.extent) == (early.checkpoint, early.extent)
    verify_store(x.workspace)


def test_core_lookups_import_no_arrow_and_no_driver(setup):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [1])
    probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    program = (
        "import json, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from pietto._project import project_job_publication as p\n"
        "from pietto._project import project_job_workspace as w\n"
        "ws = w.open_workspace(sys.argv[2], expected_identity=sys.argv[3])\n"
        "found = p.publication(ws, sys.argv[4], sys.argv[5])\n"
        "listed = p.publications(ws, sys.argv[4])\n"
        "ws.close()\n"
        "loaded = sorted(n for n in sys.modules if n.split('.')[0] in\n"
        "    ('pyarrow', 'psycopg', 'mysql', 'adbc_driver_manager',\n"
        "     'adbc_driver_postgresql'))\n"
        "print(json.dumps([found is not None, len(listed), loaded]))\n"
    )
    out = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            program,
            str(probe.ROOT / "src"),
            x.workspace.root,
            x.workspace.identity,
            x.job,
            x.generation,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    assert json.loads(out.stdout) == [True, 1, []]


# --- independent verifier ----------------------------------------------------------


DAMAGES = {
    "publication_extent": (
        "UPDATE publication SET extent = extent + 1",
        "PUBLICATION_HISTORY",
    ),
    "publication_checkpoint": (
        "UPDATE publication SET checkpoint = (SELECT identity FROM checkpoint"
        " WHERE ordinal = 1)",
        "INTEGRITY",
    ),
    "publication_dropped": ("DELETE FROM publication", "PUBLICATION_HISTORY"),
    "closing_rows": (
        "UPDATE closing_observation SET rows = rows + 1",
        "CLOSING_HISTORY",
    ),
    "closing_failure": (
        'UPDATE closing_observation SET failure = \'["read","OSError"]\'',
        "CLOSING_HISTORY",
    ),
    "closing_dropped": ("DELETE FROM closing_observation", "INTEGRITY"),
    "outcome_relabel": (
        "UPDATE attempt_terminal SET outcome = replace(outcome, 'COMMIT_ACK',"
        " 'UNKNOWN')",
        "TERMINAL_HISTORY",
    ),
    "protection_released": (
        "INSERT INTO retention_release(retention, publisher_epoch, publisher_instance)"
        " SELECT retention, 1, 'pub-x' FROM publication",
        "CAPTURE_ROWS",
    ),
    "operation_result": (
        "UPDATE operation SET result = replace(result, '\"extent\":5',"
        " '\"extent\":4') WHERE kind = 'publish_generation'",
        "PUBLICATION_HISTORY",
    ),
}


@pytest.mark.parametrize("damage", sorted(DAMAGES))
def test_verifier_rejects_coordinated_publication_damage(setup, damage, monkeypatch):
    if setup is None:
        return
    x = setup
    session = probe.ordinary(x.publisher, x.generation, x.binding, [2, 2, 1])
    probe.publish(
        x.workspace, x.job, x.publisher, x.generation, x.built, session.attempt.identity
    )
    verify_store(x.workspace)
    copy = x.root / "copy"
    os.mkdir(copy, 0o700)
    target = copy / "store.sqlite"
    with sqlite3.connect(target) as backup:
        x.workspace.use().backup(backup)
    backup.close()
    statement, code = DAMAGES[damage]
    connection = sqlite3.connect(target)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()
    view = SimpleNamespace(
        **{name: getattr(x.workspace, name) for name in ("identity", "format")}
    )
    from pietto._project import project_job_store_verification as v

    def read_copy(_workspace, body):
        raw = sqlite3.connect(target)
        try:
            raw.execute("BEGIN")
            return body(raw)
        finally:
            raw.close()

    monkeypatch.setattr(v, "read", read_copy)
    with pytest.raises(JobStoreError, match="STORE_INVARIANT_" + code):
        v.verify_store(view)  # type: ignore[arg-type]
