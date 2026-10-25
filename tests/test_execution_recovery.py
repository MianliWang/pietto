"""Offline checks for the public ordinary R2 entry."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from typing import Any, cast

from pietto._project import project_job_extraction as extraction
from pietto._project import project_job_store as store
from pietto._project import project_public_jobs as jobs
from pietto._project.project_job_workspace import JobStoreError, Workspace
from pietto.execution import RequestRejected, WorkspaceRef
from pietto.execution import _r2 as public_r2


def test_saved_output_rebuilds_recorded_r2_shape_over_guarded_output(monkeypatch):
    from pietto._project import project_execution as private_execution
    from pietto._project import project_job_capture as capture

    binding, output, program, refinement = object(), object(), object(), object()
    observed = []
    monkeypatch.setattr(capture, "supports", lambda workspace, feature: True)
    monkeypatch.setattr(
        private_execution, "compiled_output", lambda actual: (output, None, program)
    )
    monkeypatch.setattr(capture, "read", lambda *args: ("recorded", "stable"))
    monkeypatch.setattr(
        capture,
        "_recorded_refinement",
        lambda actual_binding, actual_output, route, isolation, text: (
            observed.append((actual_binding, actual_output, route, isolation, text))
            or refinement
        ),
    )
    monkeypatch.setattr(
        capture,
        "arrow_output",
        lambda job, generation, actual_output, actual_refinement, route: (
            job,
            generation,
            actual_output,
            actual_refinement,
            route,
        ),
    )

    assert capture.verified_stored_output(
        cast(Workspace, object()), "job", "generation", binding, "postgres_rows"
    ) == ("job", "generation", output, refinement, "postgres_rows")
    assert observed == [(binding, output, "postgres_rows", "stable", "recorded")]


def test_r2_entry_refuses_an_ordinary_owner_before_capture_progress():
    class Owner:
        refined_request = None
        enumeration = None
        _payloads = None
        _closed = False

    with pytest.raises(JobStoreError, match="EXTRACTION_OWNER_STATE"):
        extraction._fresh(Owner())


@pytest.mark.parametrize(
    ("purpose", "seconds", "reason"),
    (
        ("", 60, "ACCEPTANCE_PURPOSE"),
        ("recovery", 0, "ACCEPTANCE_BOUND"),
    ),
)
def test_recovery_acceptance_refuses_invalid_caller_declaration_before_source(
    monkeypatch, purpose, seconds, reason
):
    monkeypatch.setattr(extraction, "_extracting", lambda workspace: None)
    monkeypatch.setattr(
        extraction,
        "stored_binding",
        lambda *args, **kwargs: pytest.fail("invalid acceptance opened a saved source"),
    )
    with pytest.raises(JobStoreError, match=reason):
        extraction.accept_recovery(
            cast(Any, object()),
            "job-" + "0" * 32,
            "gen-" + "0" * 32,
            checkpoint=None,
            purpose=purpose,
            values=(),
            expected_pin="0" * 64,
            accepted_producer="0" * 64,
            accepted_compatibility=(),
            seconds=seconds,
        )


@pytest.mark.parametrize(
    ("purpose", "seconds", "detail"),
    (
        ("", 60, "ACCEPTANCE_PURPOSE"),
        ("unprintable\n", 60, "ACCEPTANCE_PURPOSE"),
        ("x" * 257, 60, "ACCEPTANCE_PURPOSE"),
        ("recovery", 0, "ACCEPTANCE_BOUND"),
        ("recovery", True, "ACCEPTANCE_BOUND"),
        ("recovery", 86401, "ACCEPTANCE_BOUND"),
    ),
)
def test_public_recovery_rejects_invalid_bounds_before_workspace(
    monkeypatch, purpose, seconds, detail
):
    monkeypatch.setattr(
        public_r2.private_workspace,
        "open_workspace",
        lambda *args, **kwargs: pytest.fail("invalid input opened a workspace"),
    )
    with pytest.raises(RequestRejected) as refused:
        public_r2.recover(
            WorkspaceRef("/not-opened", "ws-" + "0" * 32),
            job="job-" + "1" * 32,
            generation="gen-" + "2" * 32,
            checkpoint=None,
            query=None,
            source_requirements=(),
            operation="op-" + "3" * 32,
            route="postgres_rows",
            access=None,
            premise=None,
            limits=None,
            expected_pin="0" * 64,
            accepted_producer="0" * 64,
            accepted_compatibility="0" * 64,
            purpose=purpose,
            seconds=seconds,
        )
    assert refused.value.code == "PIE-R1002"
    assert refused.value.detail == detail
    assert refused.value.__cause__ is None
    assert refused.value.__context__ is None


def test_public_recovery_refuses_preflight_before_runtime(monkeypatch):
    workspace = WorkspaceRef("/not-opened", "ws-" + "0" * 32)
    opened = SimpleNamespace(close=lambda: None)
    called = []
    monkeypatch.setattr(
        public_r2,
        "_checked_request",
        lambda *args, **kwargs: (object(), None, None, None, None, None),
    )
    monkeypatch.setattr(
        public_r2.proposal, "prepare_live_refinement", lambda *args: None
    )
    monkeypatch.setattr(
        public_r2, "_recovery_trust", lambda *args: ("pin", "producer", ())
    )
    monkeypatch.setattr(
        public_r2.private_workspace, "open_workspace", lambda *args, **kwargs: opened
    )
    monkeypatch.setattr(
        public_r2.extraction,
        "continuation_replay_request",
        lambda *args, **kwargs: {"job": args[1]},
    )
    monkeypatch.setattr(
        public_r2.store, "query_operation", lambda *args, **kwargs: None
    )

    def refuse(*args, **kwargs):
        called.append((args, kwargs))
        raise JobStoreError("JOB_UNKNOWN")

    monkeypatch.setattr(public_r2.extraction, "accept_recovery", refuse)
    monkeypatch.setattr(
        public_r2.jobs,
        "recover_recoverable",
        lambda *args, **kwargs: pytest.fail("preflight failure opened runtime"),
    )
    with pytest.raises(RequestRejected) as refused:
        public_r2.recover(
            workspace,
            job="job-" + "1" * 32,
            generation="gen-" + "2" * 32,
            checkpoint=None,
            query=object(),
            source_requirements=(),
            operation="op-" + "3" * 32,
            route="postgres_rows",
            access=object(),
            premise=object(),
            limits=object(),
            expected_pin="pin",
            accepted_producer="producer",
            accepted_compatibility="compatibility",
            purpose="recovery",
            seconds=60,
        )
    assert (
        refused.value.code == "PIE-R1009"
        and refused.value.__cause__ is None
        and refused.value.__context__ is None
        and len(called) == 1
    )


def test_public_recovery_replays_before_current_predecessor_acceptance(monkeypatch):
    workspace = WorkspaceRef("/not-opened", "ws-" + "0" * 32)
    opened = SimpleNamespace(close=lambda: None)
    operation = "op-" + "3" * 32
    expected = {
        "job": "job-" + "1" * 32,
        "generation": "gen-" + "2" * 32,
        "predecessor": "ckp-" + "4" * 32,
        "frontier": 2,
        "reach": 2,
        "members": 1,
        "rows": 2,
        "qualification": "qualified",
    }
    previous = store.OperationResult(
        operation, "begin_continuation", expected["job"], 7, (), "QUERIED"
    )
    monkeypatch.setattr(
        public_r2,
        "_checked_request",
        lambda *args, **kwargs: (object(), (), None, None, (), None),
    )
    monkeypatch.setattr(
        public_r2.proposal, "prepare_live_refinement", lambda *args: object()
    )
    monkeypatch.setattr(
        public_r2, "_recovery_trust", lambda *args: ("pin", "producer", ())
    )
    monkeypatch.setattr(
        public_r2.private_workspace, "open_workspace", lambda *args, **kwargs: opened
    )
    monkeypatch.setattr(
        public_r2.extraction,
        "continuation_replay_request",
        lambda *args, **kwargs: expected,
    )

    def query(_workspace, actual_operation, *, expected_kind, expected_request):
        assert (actual_operation, expected_kind, expected_request) == (
            operation,
            "begin_continuation",
            expected,
        )
        return previous

    monkeypatch.setattr(public_r2.store, "query_operation", query)
    monkeypatch.setattr(
        public_r2.extraction,
        "accept_recovery",
        lambda *args, **kwargs: pytest.fail("replay accepted a current predecessor"),
    )
    monkeypatch.setattr(
        public_r2.jobs,
        "recover_recoverable",
        lambda *args, **kwargs: pytest.fail("replay opened a recovery runtime"),
    )
    reply = public_r2.recover(
        workspace,
        job=expected["job"],
        generation=expected["generation"],
        checkpoint=expected["predecessor"],
        query=object(),
        source_requirements=(),
        operation=operation,
        route="postgres_rows",
        access=object(),
        premise=object(),
        limits=object(),
        expected_pin="pin",
        accepted_producer="producer",
        accepted_compatibility="compatibility",
        purpose="recovery",
        seconds=60,
    )
    assert reply.terminal == "REPLY_LOST_OR_PARTIAL"
    assert reply.operation is not None and reply.operation.sequence == 7


@pytest.mark.parametrize(
    "function", (jobs.capture_recoverable, jobs.recover_recoverable)
)
def test_recoverable_pending_close_reuses_the_s08_single_retry(monkeypatch, function):
    class Opened:
        def __init__(self):
            self.resumes = self.closes = 0

        def reconcile(self):
            return ()

        def submit(self, unit):
            return "admission"

        def wait(self, handle, timeout):
            return SimpleNamespace(
                terminal="COMPLETED" if self.resumes else None,
                activity=None if self.resumes else "WAITING_FOR_CLEANUP",
            )

        def resume(self, handle):
            self.resumes += 1

        def close(self):
            self.closes += 1
            return {"unjoined": False}

    opened = Opened()
    monkeypatch.setattr(
        jobs,
        "runtime_capacity",
        lambda workspace: (jobs.workspace.CONTROL_RESERVE + 2, 1),
    )
    monkeypatch.setattr(jobs.runtime, "open_runtime", lambda *args, **kwargs: opened)
    values = dict(
        job="job-" + "0" * 32,
        generation="gen-" + "0" * 32,
        template=object(),
        route="postgres_rows",
        access=object(),
        schemas=(),
        limits=SimpleNamespace(seconds=1),
        isolation="stable",
        values=(),
    )
    if function is jobs.capture_recoverable:
        values["source_requirements"] = ()
    else:
        values.update(
            checkpoint=None,
            trust=("pin", "producer", ()),
            purpose="recovery",
            seconds=1,
            source_requirements=(),
            operation="op-" + "0" * 32,
        )
    state, pending = function(
        SimpleNamespace(root="/root", identity="ws-" + "0" * 32), **values
    )
    assert state.activity == "WAITING_FOR_CLEANUP" and pending is not None
    pending.close()
    pending.close()
    assert (opened.resumes, opened.closes) == (1, 1)


def test_pending_close_refuses_an_unresolved_single_retry():
    class Opened:
        def __init__(self):
            self.resumes = self.closes = 0

        def resume(self, handle):
            self.resumes += 1

        def wait(self, handle, timeout):
            return SimpleNamespace(terminal=None)

        def close(self):
            self.closes += 1
            return {"unjoined": False}

    opened = Opened()
    with pytest.raises(JobStoreError, match="RUNTIME_CLOSE_UNJOINED"):
        jobs.PendingClose(opened, "admission").close()
    assert (opened.resumes, opened.closes) == (1, 0)


SINCE = (
    "\nquery since(low: Int, note: Text | None):\n    from items\n"
    "    where id > low and (note is None or label != note)\n    select:\n"
    "        id\n        next = low + 1\n"
)
# An R2 shape that is refused (D70.05): it groups by a key its let computes.
GROUPED = (
    "\nquery grouped(low: Int):\n    from items\n"
    "    let big = id > 5\n    group by:\n        big\n"
    "    select:\n        flag = big\n        total = count()\n"
)
SAVED = {"low": 5, "note": None}


def _queries(directory):
    """The `since` and `grouped` queries of one example project."""
    import _pietto_execution_api as api
    import pietto.execution as execution

    project = api.write_example(directory)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8") + SINCE + GROUPED, encoding="utf-8"
    )
    return tuple(
        execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name=name,
            dialect="postgres",
            emission_contract="contract.json",
        )
        for name in ("since", "grouped")
    )


# R2 shapes that are refused (D70.05) whose lets with capture lines read the
# header: an EXISTS read and a LATERAL join.
CAPTURING = """
source tags: Item = postgres.table("fixture.tags")

query exists_since(low: Int, note: Text | None):
    let same:
        capture items
        from tags
        where tags.label == items.label and tags.id > low
        select:
            id
    from items
    where exists same and (note is None or label != note)
    select:
        id

query lateral_since(low: Int, note: Text | None):
    let later:
        capture items
        from tags
        where tags.id > items.id and tags.id > low
        select:
            tag_id = id
    from items
    let t = later
    cross join t
    where note is None or items.label != note
    select:
        id = items.id
        tag_id = t.tag_id
"""


def _capturing(directory):
    """`exists_since` and `lateral_since` of one example project with `tags`."""
    import json

    import _pietto_execution_api as api
    import pietto.execution as execution

    project = api.write_example(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + CAPTURING, encoding="utf-8")
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return tuple(
        execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name=name,
            dialect="postgres",
            emission_contract="contract.json",
        )
        for name in ("exists_since", "lateral_since")
    )


def _recover(workspace, query, parameters, **overrides):
    """recover's refusal (code, detail) for one restatement of `parameters`,
    with the R2 declarations and trust records of `query` itself."""
    import pietto.execution as execution

    root = query._template.artifact.request.verification.completed.root
    sources = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in query._template.artifact.request.sources
    )
    arguments: dict[str, Any] = dict(
        job="job-" + "0" * 32,
        generation="gen-" + "0" * 32,
        checkpoint=None,
        query=query,
        source_requirements=sources,
        operation=execution.new_operation(),
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        limits=execution.ExecutionLimits(),
        expected_pin=root.expected_pin,
        accepted_producer=root.accepted_producer,
        accepted_compatibility=root.accepted_compatibility[-1],
        purpose="restatement",
        seconds=60,
        parameters=parameters,
    )
    with pytest.raises(RequestRejected) as refused:
        public_r2.recover(workspace, **(arguments | overrides))
    return refused.value.code, refused.value.detail


def test_recover_judges_restated_parameters_by_the_saved_binding(tmp_path, monkeypatch):
    """D70.02: recover restates the saved parameters. A missing, extra,
    mistyped, illegal NULL, out-of-range or other value is BINDING_VECTOR
    from the saved binding, after the workspace's own checks and before any
    source; only the type of ``parameters`` is refused before the workspace."""
    from _pietto_execution_jobs_probe import qualified
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_execution_template import bind_values, named_values

    if not qualified(tmp_path):
        return
    query, _ = _queries(tmp_path / "project")
    template = query._template
    opened = private_workspace.create_workspace(
        str(tmp_path / "workspace"), format=private_workspace.FORMAT_V7
    )
    try:
        job = store.register_job(opened, template, operation=store.new_operation()).get(
            "job"
        )
        publisher = store.claim_publisher(opened, job, operation=store.new_operation())
        binding = bind_values(
            template,
            tuple((s, s.original.site.position.literal.value) for s in template.slots),
            named_values(template, SAVED),
        )
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
        publisher.close()
        workspace = WorkspaceRef(opened.root, opened.identity)
    finally:
        opened.close()
    monkeypatch.setattr(
        jobs,
        "recover_recoverable",
        lambda *args, **kwargs: pytest.fail("a refused restatement reached a source"),
    )

    def recover(parameters, **overrides):
        return _recover(
            workspace,
            query,
            parameters,
            **({"job": job, "generation": generation} | overrides),
        )

    for parameters in (
        None,
        {"low": 5},
        {**SAVED, "extra": 1},
        {**SAVED, "low": True},
        {**SAVED, "low": None},
        {**SAVED, "note": 5},
        {**SAVED, "low": 2**63 - 1},
        {**SAVED, "low": 6},
        {**SAVED, "note": ""},
    ):
        assert recover(parameters) == ("PIE-R1009", "BINDING_VECTOR")
    # The saved values pass the restatement and meet the next stored fact.
    assert recover(dict(SAVED)) == ("PIE-R1009", "EXTRACTION_UNKNOWN")
    # The workspace's own checks come first: no saved binding, no comparison.
    unknown = "gen-" + "0" * 32
    assert recover({**SAVED, "low": True}, generation=unknown) == (
        "PIE-R1009",
        "GENERATION_UNKNOWN",
    )
    monkeypatch.setattr(
        private_workspace,
        "open_workspace",
        lambda *args, **kwargs: pytest.fail("opened the workspace"),
    )
    assert recover([("low", 5)]) == ("PIE-R1002", "PUBLIC_PARAMETERS_TYPE")


def test_recover_refuses_its_other_inputs_first_whatever_the_restatement(
    tmp_path, monkeypatch
):
    """Every other refusal of recover precedes the workspace in the same order
    whether the restated parameters bind, differ or cannot bind at all: the
    access, premise, limits, isolation and R2 checks read no value."""
    from dataclasses import replace

    import pietto.execution as execution
    from pietto._project import project_job_workspace as private_workspace

    since, grouped = _queries(tmp_path)
    exists, lateral = _capturing(tmp_path / "capturing")
    bundle = execution.export_bundle(since)
    loaded = execution.load_bundle(
        bundle.payload,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
    )
    workspace = object.__new__(WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "3" * 32)
    monkeypatch.setattr(
        private_workspace,
        "open_workspace",
        lambda *args, **kwargs: pytest.fail("opened the workspace"),
    )
    (source,) = since._template.artifact.request.sources
    declared = execution.R2SourceInput(
        source.namespace,
        "other",
        "provider",
        "v1",
        "r1",
        source.namespace,
        "registry",
        "SELECT 1",
        ("id",),
        "pietto_query",
        "retained",
    )
    host = "db.example.test"
    for query, overrides, refusal in (
        (
            since,
            {"premise": execution.PostgresDeploymentPremise(("pg_catalog",))},
            ("PIE-R1002", "POSTGRES_DEPLOYMENT_PREMISE_SCOPE"),
        ),
        (
            since,
            {"access": execution.PostgresAccess("127.0.0.1", 0, "db", "u", "pw")},
            ("PIE-R1002", "EXECUTION_ACCESS"),
        ),
        (
            since,
            {
                "access": execution.PostgresAccess(
                    host, 5432, "db", "u", "pw", "disable"
                )
            },
            ("PIE-R1002", "EXECUTION_ACCESS_PROFILE"),
        ),
        (since, {"isolation": "dirty"}, ("PIE-R1002", "EXECUTION_ISOLATION")),
        (
            since,
            {"limits": execution.ExecutionLimits(batch_rows=4097)},
            ("PIE-R1002", "EXECUTION_LIMITS"),
        ),
        (loaded, {}, ("PIE-R1004", "PUBLIC_R2_LIVE_QUERY")),
        (since, {"source_requirements": ()}, ("PIE-R1004", "PUBLIC_R2_SOURCE_CLOSURE")),
        (
            since,
            {"source_requirements": (replace(declared),)},
            ("PIE-R1004", "PUBLIC_R2_SOURCE_ORDER"),
        ),
        (grouped, {}, ("PIE-R1004", "PUBLIC_R2_COMPUTED_GROUP_KEY")),
        (exists, {}, ("PIE-R1004", "REFINEMENT_EXPRESSION_BLOCK_READ")),
        (lateral, {}, ("PIE-R1004", "REFINEMENT_LATERAL_JOIN")),
    ):
        # Equal for one query, different or unbindable for the other.
        for parameters in (SAVED, {"low": 5}, {"low": 6}, {"low": True}, None):
            assert _recover(workspace, query, parameters, **overrides) == refusal
