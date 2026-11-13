"""Data-only laws for the unexported S12 carrier preparation."""

from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fcntl", reason="the live witness needs the POSIX job runtime")

import _pietto_execution_jobs_probe as workspace_probe
from pietto._project import project_public_r2_proposal as proposal


def _live_request(tmp_path):
    import _pietto_execution_api as api
    from pietto._project.project_execution import (
        ExecutionLimits,
        PostgresAccess,
        verify_compiled_owner,
    )
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_job_runtime import NativeSource, _owner
    from pietto.execution import R2SourceInput, compile_query

    query = compile_query(
        api.write_example(Path(tmp_path) / "r2-live"),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    inputs = tuple(
        R2SourceInput(
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
        for source in binding.artifact.request.sources
    )
    prepared = proposal.prepare_live_refinement(query, binding, inputs)
    source = NativeSource(
        "postgres_rows",
        PostgresAccess("127.0.0.1", 5432, "db", "pietto_query", "pw", "disable"),
        ("fixture", "pg_catalog"),
        ExecutionLimits(),
        refinement=prepared.refinement,
        live_r2=prepared.witness,
    )
    owner = _owner(binding, source)
    verify_compiled_owner(owner)
    return query, binding, inputs, prepared, owner


def artifact():
    left = SimpleNamespace(namespace="public", name="left")
    right = SimpleNamespace(namespace="public", name="right")
    return SimpleNamespace(
        request=SimpleNamespace(sources=(left, right), family="postgres")
    )


def input(namespace, name):
    return proposal.R2SourceInput(
        namespace,
        name,
        "provider",
        "v1",
        "r1",
        "public",
        "registry",
        "SELECT 1",
        ("token",),
        "reader",
        "retained",
    )


def test_retained_requirements_preserve_compiled_source_order(monkeypatch):
    value = artifact()
    monkeypatch.setattr(proposal, "verify_requirement", lambda *args, **kwargs: None)
    requirements = proposal.retained_requirements(
        value, (input("public", "left"), input("public", "right"))
    )
    assert tuple(item.source for item in requirements) == value.request.sources
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_ORDER"):
        proposal.retained_requirements(
            value, (input("public", "right"), input("public", "left"))
        )


def test_live_refinement_refuses_bundle_and_fixes_tie_policy(monkeypatch):
    value = artifact()
    template = object()
    binding = SimpleNamespace(artifact=value, template=template)
    captured = {}
    monkeypatch.setattr(
        proposal,
        "retained_requirements",
        lambda artifact, inputs: ("requirements",),
    )

    def prepare(template, binding, requirements, *, reanchor=False):
        captured.update(
            template=template,
            binding=binding,
            requirements=requirements,
            reanchor=reanchor,
        )
        return "refinement", "witness"

    monkeypatch.setattr(proposal, "prepare_live_r2_refinement", prepare)
    with pytest.raises(ValueError, match="PUBLIC_R2_LIVE_QUERY"):
        proposal.prepare_live_refinement(
            SimpleNamespace(origin="bundle", _template=template), binding, ()
        )
    prepared = proposal.prepare_live_refinement(
        SimpleNamespace(origin="live", _template=template), binding, ()
    )
    assert (prepared.refinement, prepared.witness, prepared.template) == (
        "refinement",
        "witness",
        template,
    )
    assert captured == {
        "template": template,
        "binding": binding,
        "requirements": ("requirements",),
        "reanchor": False,
    }


def test_live_witness_refuses_plain_copied_and_mismatched_requests(tmp_path):
    from pietto._project.project_execution import ExecutionError, verify_compiled_owner
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_refinement import LiveR2Witness
    from pietto._project.project_refinement_enumeration import RefinedExecutionRequest
    from pietto._project.project_execution_postgres import PostgresExecution

    _query, binding, inputs, prepared, owner = _live_request(tmp_path)
    plain = PostgresExecution(
        RefinedExecutionRequest(owner.request, prepared.refinement)
    )
    with pytest.raises(ExecutionError, match="COMPILED_REFINEMENT_MODE_REQUIRED"):
        verify_compiled_owner(plain)
    copied = LiveR2Witness(
        prepared.witness.template,
        binding,
        prepared.refinement,
        prepared.witness.requirements,
        False,
    )
    forged = PostgresExecution(
        RefinedExecutionRequest(owner.request, prepared.refinement, copied)
    )
    with pytest.raises(ValueError, match="PUBLIC_R2_WITNESS"):
        verify_compiled_owner(forged)
    rebound = bind_values(
        binding.template,
        tuple(zip(binding.template.slots, binding.values, strict=True)),
    )
    other = LiveR2Witness(
        prepared.witness.template,
        rebound,
        prepared.refinement,
        prepared.witness.requirements,
        False,
    )
    mismatched = PostgresExecution(
        RefinedExecutionRequest(owner.request, prepared.refinement, other)
    )
    with pytest.raises(ValueError, match="PUBLIC_R2_WITNESS"):
        verify_compiled_owner(mismatched)
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(_query, binding, inputs[:-1])
    wrong = proposal.R2SourceInput(
        inputs[0].namespace,
        "wrong",
        inputs[0].provider,
        inputs[0].version,
        inputs[0].revision,
        inputs[0].registry_namespace,
        inputs[0].registry_name,
        inputs[0].definition,
        inputs[0].token_columns,
        inputs[0].role,
        inputs[0].provider_guarantee,
    )
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_ORDER"):
        proposal.prepare_live_refinement(_query, binding, (wrong,))


def test_live_refinement_requires_a_source_read_only_inside_a_let(tmp_path):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-let")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table tagged_items:\n    let tagged:\n        from tags\n"
        "        select:\n            tag_id = id\n    from items\n"
        "    let t = tagged\n"
        "    inner join t on items.id == t.tag_id\n"
        "    select:\n        id = items.id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="tagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    sources = binding.artifact.request.sources
    assert [(s.namespace, s.name) for s in sources] == [
        ("fixture", "items"),
        ("fixture", "tags"),
    ]
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in sources
    )
    assert proposal.prepare_live_refinement(query, binding, inputs) is not None
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])


def test_r2_refuses_a_computed_group_key_before_any_workspace(tmp_path, monkeypatch):
    """A query that groups by its own `let` value is not an R2 shape yet."""
    import sys

    import _pietto_execution_api as api
    import pietto.execution as execution
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_execution_template import bind_values

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused R2 request opened workspace state")

    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    before = {n for n in sys.modules if n.split(".")[0] in {"psycopg", "pyarrow"}}
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)
    access = execution.PostgresAccess("127.0.0.1", 9, "db", "pietto_query", "pw")
    premise = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
    computed = "    group by:\n        big\n    select:\n        flag = big\n"
    for name, body, refused in (
        ("computed", "    let big = id > 5\n" + computed, True),
        # A later stage carries the key on by a read; it is still computed.
        (
            "let_where",
            "    let big = id > 5\n    where id > 0\n" + computed,
            True,
        ),
        (
            "two_lets",
            "    let big = id > 5\n    let other = id + 0\n" + computed,
            True,
        ),
        # S05j: the JOIN key's own LET unit comes before the one for `level`.
        (
            "joined",
            "    let r = items\n    inner join r on items.id == r.id\n"
            "    let later = items.id > r.id or r.id > 12\n"
            "    let level = r.id + items.id * 0\n    group by:\n        later\n"
            "    select:\n        b = later\n        top = max(level)\n",
            True,
        ),
        (
            "field",
            "    group by:\n        label\n    select:\n        label\n",
            False,
        ),
        # A WHERE stage between the let and the grouping only carries the key.
        (
            "computed_where",
            "    let big = id > 5\n    where id > 1\n" + computed,
            True,
        ),
        (
            "field_where",
            "    where id > 1\n    group by:\n        label\n    select:\n"
            "        label\n",
            False,
        ),
    ):
        project = api.write_example(Path(tmp_path) / name)
        main = project / "main.pietto"
        main.write_text(
            main.read_text(encoding="utf-8")
            + "table grouped:\n    from items\n"
            + body
            + "        total = count()\n",
            encoding="utf-8",
        )
        query = execution.compile_query(
            project,
            module="main.pietto",
            kind="table",
            name="grouped",
            dialect="postgres",
            emission_contract="contract.json",
        )
        values = tuple(
            slot.original.site.position.literal.value for slot in query._template.slots
        )
        binding = bind_values(
            query._template, tuple(zip(query._template.slots, values))
        )
        inputs = tuple(
            execution.R2SourceInput(
                s.namespace,
                s.name,
                "provider",
                "v1",
                "r1",
                s.namespace,
                "registry",
                "SELECT 1",
                ("id",),
                "pietto_query",
                "retained",
            )
            for s in binding.artifact.request.sources
        )
        if not refused:
            # A field key is unchanged.
            assert proposal.prepare_live_refinement(query, binding, inputs)
            continue
        with pytest.raises(ValueError, match="^PUBLIC_R2_COMPUTED_GROUP_KEY$"):
            proposal.prepare_live_refinement(query, binding, inputs)
        common: dict[str, Any] = dict(
            query=query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=access,
            premise=premise,
            limits=execution.ExecutionLimits(),
            values=values,
        )
        for call in (
            lambda: execution.save_recoverable(workspace, **common),
            lambda: execution.recover(
                workspace,
                job="job-" + "0" * 32,
                generation="gen-" + "0" * 32,
                checkpoint=None,
                expected_pin="0" * 64,
                accepted_producer="0" * 64,
                accepted_compatibility="0",
                purpose="r2-computed-key",
                seconds=60,
                **common,
            ),
        ):
            with pytest.raises(execution.RequestRejected) as rejected:
                call()
            assert (rejected.value.code, rejected.value.detail) == (
                "PIE-R1004",
                "PUBLIC_R2_COMPUTED_GROUP_KEY",
            )
    assert before == {
        n for n in sys.modules if n.split(".")[0] in {"psycopg", "pyarrow"}
    }


# The body of `table snap: from items`, whether the program has Timestamp
# source fields, and the PIE-R1004 detail of both R2 calls (None: they reach
# the workspace).
NOW_FORMS = {
    # On PostgreSQL R2 reads these `now()` reads.
    "seen": ("    select:\n        id\n        seen = now()\n", False, None),
    "seen_beside_source": (
        "    select:\n        id\n        seen = now()\n",
        True,
        None,
    ),
    "where": ("    where stamp <= now()\n    select:\n        id\n", True, None),
    "comparison_item": (
        "    select:\n        id\n        late = stamp <= now()\n",
        True,
        None,
    ),
    "or": (
        "    where stamp == now() or opt == now()\n    select:\n        id\n",
        True,
        None,
    ),
    # Their SQL is SQL R2 does not read, as in 0.1.11.
    "date_of": (
        "    select:\n        id\n        day = date_of(now())\n",
        True,
        "PUBLIC_R2_STATEMENT_SNAPSHOT",
    ),
    "coalesce": (
        "    where coalesce(opt, now()) <= stamp\n    select:\n        id\n",
        True,
        "PUBLIC_R2_STATEMENT_SNAPSHOT",
    ),
    "lower_beside": (
        "    select:\n        id\n        l = lower(label)\n        seen = now()\n",
        True,
        "PUBLIC_R2_STATEMENT_SNAPSHOT",
    ),
    # A `now()` read in a conditional sum's test.
    "conditional_sum": (
        "    group by:\n        label\n    select:\n        label\n"
        "        n = sum(o.id for o in group if o.stamp <= now())\n",
        True,
        "PUBLIC_R2_STATEMENT_SNAPSHOT",
    ),
    # Without `now()` that check is not made: its first page fails later.
    "lower_alone": ("    select:\n        id\n        l = lower(label)\n", True, None),
    # The check is the last of preparation: another refusal comes first.
    "computed_key": (
        "    let big = id > 5\n    where date_of(now()) <= date_of(stamp)\n"
        "    group by:\n        big\n    select:\n        flag = big\n"
        "        total = count()\n",
        True,
        "PUBLIC_R2_COMPUTED_GROUP_KEY",
    ),
    "computed_output": (
        "    select:\n        id\n        c = coalesce(now(), now())\n",
        True,
        "MEANING_OUTPUT",
    ),
}


def _now_query(directory, body, temporal, header="table snap:"):
    import _pietto_execution_api as api
    import pietto.execution as execution

    writer = api.write_temporal_example if temporal else api.write_example
    project = writer(Path(directory) / "now")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8") + header + "\n    from items\n" + body,
        encoding="utf-8",
    )
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind=header.split()[0],
        name="snap",
        dialect="postgres",
        emission_contract="contract.json",
    )
    inputs = tuple(
        execution.R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in query._template.artifact.request.sources
    )
    return query, inputs


def _r2_calls(query, inputs, **restated):
    """`save_recoverable` and `recover` of ``query`` over an unopenable
    workspace, with its own trust records."""
    import pietto.execution as execution

    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)
    root = query._template.artifact.request.verification.completed.root
    common: dict[str, Any] = dict(
        query=query,
        source_requirements=inputs,
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 9, "db", "pietto_query", "pw"),
        premise=execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")),
        limits=execution.ExecutionLimits(),
        values=tuple(
            slot.original.site.position.literal.value for slot in query._template.slots
        ),
        **restated,
    )
    return (
        lambda: execution.save_recoverable(
            workspace, operation=execution.new_operation(), **common
        ),
        lambda: execution.recover(
            workspace,
            job="job-" + "0" * 32,
            generation="gen-" + "0" * 32,
            checkpoint=None,
            operation=execution.new_operation(),
            expected_pin=root.expected_pin,
            accepted_producer=root.accepted_producer,
            accepted_compatibility=root.accepted_compatibility[-1],
            purpose="r2-now",
            seconds=60,
            **common,
        ),
    )


@pytest.mark.parametrize("form", NOW_FORMS)
def test_r2_reads_now_on_postgres(tmp_path, form):
    """R2 runs a `now()` read that it reads in its SQL; it refuses one whose
    SQL it does not read before any workspace, after its other refusals."""
    import pietto.execution as execution
    from pietto._project.project_execution_template import bind_values

    body, temporal, detail = NOW_FORMS[form]
    query, inputs = _now_query(tmp_path, body, temporal)
    if detail != "MEANING_OUTPUT":
        template = query._template
        binding = bind_values(
            template,
            tuple((s, s.original.site.position.literal.value) for s in template.slots),
        )
        if detail is None:
            assert proposal.prepare_live_refinement(query, binding, inputs)
        else:
            with pytest.raises(ValueError, match="^" + detail + "$"):
                proposal.prepare_live_refinement(query, binding, inputs)
    for call in _r2_calls(query, inputs):
        with pytest.raises(execution.RequestRejected) as rejected:
            call()
        if detail is None:
            assert rejected.value.code == "PIE-R1009"
        else:
            assert (rejected.value.code, rejected.value.detail) == (
                "PIE-R1004",
                detail,
            )


def test_r2_checks_now_sql_only_when_restated_values_bind(tmp_path):
    """`recover` renders the first page with the restated values, so with
    values that do not bind it goes on to the workspace, which refuses it
    (here the unopenable one, by its parent), never connecting."""
    import pietto.execution as execution

    query, inputs = _now_query(
        tmp_path,
        "    where id > low\n    select:\n        id\n        day = date_of(now())\n",
        True,
        header="query snap(low: Int):",
    )
    for parameters, refusal in (
        ({"low": 1}, ("PIE-R1004", "PUBLIC_R2_STATEMENT_SNAPSHOT")),
        ({"low": "x"}, ("PIE-R1009", "WORKSPACE_PARENT")),
    ):
        _save, recover = _r2_calls(query, inputs, parameters=parameters)
        with pytest.raises(execution.RequestRejected) as rejected:
            recover()
        assert (rejected.value.code, rejected.value.detail) == refusal


def test_mysql_r2_refuses_now_in_its_place(tmp_path):
    """MySQL R2 has no statement time yet: it refuses a query that reads
    `now()` where 0.1.11 did, before the computed-key refusal, while
    PostgreSQL makes its check last."""
    from pietto._project.project_refinement import _live_shape

    query, inputs = _now_query(tmp_path, NOW_FORMS["computed_key"][0], True)
    artifact = query._template.artifact
    requirements = proposal.retained_requirements(artifact, inputs)
    for family, detail in (
        ("mysql", "PUBLIC_R2_STATEMENT_SNAPSHOT"),
        ("postgres", "PUBLIC_R2_COMPUTED_GROUP_KEY"),
    ):
        relabelled = SimpleNamespace(
            request=SimpleNamespace(
                family=family,
                verification=artifact.request.verification,
                sources=artifact.request.sources,
            )
        )
        with pytest.raises(ValueError, match="^" + detail + "$"):
            _live_shape(relabelled, requirements)


def test_a_reused_let_refines_like_its_module_level_equivalent(tmp_path):
    """R2 coordinates of a diamond of lets are those of the module-level diamond."""
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    module_level = """query base:
    from items
    select:
        id
query low:
    from base
    where id < 50
    select:
        id
query high:
    from base
    where id > 10
    select:
        id
table result:
    union all:
        from low
        from high
"""
    lets = """table result:
    let low:
        from base
        where id < 50
        select:
            id
    let high:
        from base
        where id > 10
        select:
            id
    let base:
        from items
        select:
            id
    union all:
        from low
        from high
"""
    refined = []
    for name, text in (("module", module_level), ("lets", lets)):
        project = api.write_example(Path(tmp_path) / name)
        main = project / "main.pietto"
        main.write_text(main.read_text(encoding="utf-8") + text, encoding="utf-8")
        query = compile_query(
            project,
            module="main.pietto",
            kind="table",
            name="result",
            dialect="postgres",
            emission_contract="contract.json",
        )
        values = tuple(
            slot.original.site.position.literal.value for slot in query._template.slots
        )
        binding = bind_values(
            query._template, tuple(zip(query._template.slots, values))
        )
        inputs = tuple(
            R2SourceInput(
                s.namespace,
                s.name,
                "provider",
                "v1",
                "r1",
                s.namespace,
                "registry",
                "SELECT 1",
                ("id",),
                "pietto_query",
                "retained",
            )
            for s in binding.artifact.request.sources
        )
        refinement = proposal.prepare_live_refinement(query, binding, inputs).refinement
        refined.append(
            (
                binding.artifact.rendered.sql,
                refinement.prefix,
                [
                    (u.rule, u.dependencies, u.key_names, len(u.coordinates))
                    for u in refinement.units
                ],
            )
        )
    assert refined[0] == refined[1]
    # `base` is one unit read by both branches.
    assert [unit[1] for unit in refined[1][2]] == [
        (-1,),
        (0,),
        (1,),
        (0,),
        (3,),
        (2, 4),
    ]


# A capture-free let and (Phase70 S10) a let with a capture line, inline at its
# read; both are read by EXISTS and (Phase70 S14) the captured let by a
# correlated scalar or NOT IN read, also when it ends in ORDER BY and LIMIT.
EXISTS_LETS = {
    "let": "        from tags\n",
    "captured": "        capture items\n        from tags\n"
    "        where tags.label == items.label\n",
    "ordered": "        capture items\n        from tags\n"
    "        where tags.label == items.label\n",
}
ORDER_TAILS = {"ordered": "        order by:\n            id desc\n        limit 1\n"}
BLOCK_READS = {
    ("let", "exists"): "exists tagged",
    ("captured", "exists"): "exists tagged",
    ("captured", "not_in"): "id not in tagged",
    ("captured", "scalar"): "id <= scalar tagged.tag_id",
    ("ordered", "not_in"): "id not in tagged",
    ("ordered", "scalar"): "id <= scalar tagged.tag_id",
}


@pytest.mark.parametrize(("let", "read"), sorted(BLOCK_READS))
def test_live_refinement_refuses_a_let_read_after_its_source_closure(
    tmp_path, monkeypatch, let, read
):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-exists")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table flagged_items:\n    let tagged:\n"
        + EXISTS_LETS[let]
        + "        select:\n            tag_id = id\n"
        + ORDER_TAILS.get(let, "")
        + "    from items\n"
        f"    where {BLOCK_READS[let, read]}\n    select:\n        id = items.id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="flagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    sources = binding.artifact.request.sources
    assert [(s.namespace, s.name) for s in sources] == [
        ("fixture", "items"),
        ("fixture", "tags"),
    ]
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in sources
    )
    # The source read only through the let read is a required input,
    # then the read itself is refused before any connection.
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    with pytest.raises(ValueError, match="REFINEMENT_EXPRESSION_BLOCK_READ"):
        proposal.prepare_live_refinement(query, binding, inputs)
    # The public call refuses it as the query's own refusal, before any
    # workspace or connection is opened.
    from pietto import execution
    from pietto._project import project_job_workspace as private_workspace

    import socket

    from pietto._project import project_execution_postgres as pg

    if not workspace_probe.qualified(tmp_path):
        return
    workspace = execution.create_workspace(
        Path(tmp_path) / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    before = sorted(
        (p.relative_to(workspace.root), p.stat().st_size)
        for p in Path(workspace.root).rglob("*")
    )

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the driver")

    for owner, name in ((pg, "_connect"), (pg, "drivers"), (socket.socket, "connect")):
        monkeypatch.setattr(owner, name, forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.save_recoverable(
            workspace,
            query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess(
                "127.0.0.1", 5432, "app", "reader", "x" * 24, "disable"
            ),
            premise=execution.PostgresDeploymentPremise(
                schemas=("fixture", "pg_catalog")
            ),
            limits=execution.ExecutionLimits(),
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "REFINEMENT_EXPRESSION_BLOCK_READ",
    )
    assert refused.value.attempt is None and refused.value.outcome is None
    assert (
        sorted(
            (p.relative_to(workspace.root), p.stat().st_size)
            for p in Path(workspace.root).rglob("*")
        )
        == before
    )


def test_live_refinement_refuses_a_scalar_read_after_its_source_closure(tmp_path):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-scalar")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table priced_items:\n    let top:\n        from tags\n"
        "        select:\n            n = count()\n    from items\n"
        "    where id <= scalar top.n\n    select:\n        id = items.id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="priced_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    sources = binding.artifact.request.sources
    assert [(s.namespace, s.name) for s in sources] == [
        ("fixture", "items"),
        ("fixture", "tags"),
    ]
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in sources
    )
    # The source read only through the scalar read is a required input, then
    # the read itself is refused before any connection.
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    with pytest.raises(ValueError, match="REFINEMENT_EXPRESSION_BLOCK_READ"):
        proposal.prepare_live_refinement(query, binding, inputs)


def test_a_membership_read_is_refused_after_its_source_closure_before_any_workspace(
    tmp_path, monkeypatch
):
    import socket

    import _pietto_execution_api as api
    from pietto import execution
    from pietto._project import project_execution_postgres as pg
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-membership")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table flagged_items:\n    let tagged:\n        from tags\n"
        "        select:\n            tag_id = id\n    from items\n"
        "    where id not in tagged\n    select:\n        id = items.id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="flagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    sources = binding.artifact.request.sources
    assert [(s.namespace, s.name) for s in sources] == [
        ("fixture", "items"),
        ("fixture", "tags"),
    ]
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in sources
    )
    # The source read only through the membership read is a required input,
    # then the read itself is refused.
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    with pytest.raises(ValueError, match="REFINEMENT_EXPRESSION_BLOCK_READ"):
        proposal.prepare_live_refinement(query, binding, inputs)
    if not workspace_probe.qualified(tmp_path):
        return
    workspace = execution.create_workspace(
        Path(tmp_path) / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    before = sorted(
        (p.relative_to(workspace.root), p.stat().st_size)
        for p in Path(workspace.root).rglob("*")
    )

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the driver")

    for owner, name in ((pg, "_connect"), (pg, "drivers"), (socket.socket, "connect")):
        monkeypatch.setattr(owner, name, forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.save_recoverable(
            workspace,
            query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess(
                "127.0.0.1", 5432, "app", "reader", "x" * 24, "disable"
            ),
            premise=execution.PostgresDeploymentPremise(
                schemas=("fixture", "pg_catalog")
            ),
            limits=execution.ExecutionLimits(),
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "REFINEMENT_EXPRESSION_BLOCK_READ",
    )
    assert refused.value.attempt is None and refused.value.outcome is None
    assert (
        sorted(
            (p.relative_to(workspace.root), p.stat().st_size)
            for p in Path(workspace.root).rglob("*")
        )
        == before
    )


# A `[not] any(...)` conjunct of a WHERE, what a last `semi join` or `anti join`
# migrates to, refines as that JOIN did: one EXISTS over the read source's own
# refined input, which projects the columns the test reads. The same read under
# `or` or around another block read still fails closed.
TAIL_ANY = {
    "any": "any(t.label == items.label for t in tags)",
    "not_any": "not any(t.label == items.label for t in tags)",
    "and": "id > 1 and any(t.id < items.id for t in tags)",
    "or": "id > 1 or any(t.label == items.label for t in tags)",
    "nested": "any(any(u.id == t.id for u in tags) for t in tags)",
}


@pytest.mark.parametrize("name", sorted(TAIL_ANY))
def test_live_refinement_refines_a_tail_any_as_its_semi_or_anti_join(tmp_path, name):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import verify_native
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-tail-any")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table tagged_items:\n    from items\n"
        f"    where {TAIL_ANY[name]}\n    select:\n        id = items.id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="tagged_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in binding.artifact.request.sources
    )
    assert [i.name for i in inputs] == ["items", "tags"]
    with pytest.raises(ValueError, match="^PUBLIC_R2_SOURCE_CLOSURE$"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    if name in ("or", "nested"):
        with pytest.raises(ValueError, match="^REFINEMENT_EXPRESSION_BLOCK_READ$"):
            proposal.check_live_refinement(query, inputs)
        with pytest.raises(ValueError, match="^REFINEMENT_EXPRESSION_BLOCK_READ$"):
            proposal.prepare_live_refinement(query, binding, inputs)
        return
    # recover's template checks and save_recoverable's preparation accept it.
    proposal.check_live_refinement(query, inputs)
    refinement = proposal.prepare_live_refinement(query, binding, inputs).refinement
    prefix = refinement.prefix
    (tags_input,) = (
        c for c in refinement.statement.ctes if c.name == prefix + "source1"
    )
    read = "item_id" if name == "and" else "item_label"
    assert tags_input.columns == (read, prefix + "k0", prefix + "k1")
    native = render(refinement.statement, refinement.original)
    assert verify_native(native, refinement) == ()
    sql = native.sql.decode("utf-8")
    # `tags` is read once, by its refined input; the test reads that input.
    assert sql.count('"fixture"."tags"') == 1
    test = 'EXISTS (SELECT 1 AS "' + prefix + 'one" FROM "' + prefix + 'source1" AS '
    assert sql.count(test) == 1
    assert sql.count("(NOT " + test) == (name == "not_any")


@pytest.mark.parametrize(
    "text",
    (
        # The statement groups by its own computed key and reads a block.
        "table refused:\n    from items\n    let big = id > 2\n"
        "    where exists tags\n    group by:\n        big\n    select:\n"
        "        big\n        n = count()\n",
        # The block it reads groups by that block's own computed key.
        "table grouped_tags:\n    from tags\n    let big = id > 2\n"
        "    group by:\n        big\n    select:\n        flag = big\n"
        "        n = count()\n"
        "table refused:\n    from items\n    where exists grouped_tags\n"
        "    select:\n        id = items.id\n",
    ),
    ids=("own_key", "read_key"),
)
def test_r2_refusals_keep_their_order_closure_group_key_then_block_read(tmp_path, text):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-order")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        + text,
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="refused",
        dialect="postgres",
        emission_contract="contract.json",
    )
    values = tuple(
        slot.original.site.position.literal.value for slot in query._template.slots
    )
    binding = bind_values(query._template, tuple(zip(query._template.slots, values)))
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in binding.artifact.request.sources
    )
    assert [i.name for i in inputs] == ["items", "tags"]
    # The source closure first, then the computed group key before the read.
    with pytest.raises(ValueError, match="^PUBLIC_R2_SOURCE_CLOSURE$"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    with pytest.raises(ValueError, match="^PUBLIC_R2_COMPUTED_GROUP_KEY$"):
        proposal.prepare_live_refinement(query, binding, inputs)


@pytest.mark.parametrize("top_k", (False, True))
def test_live_refinement_refuses_a_lateral_join_after_its_source_closure(
    tmp_path, monkeypatch, top_k
):
    # Phase70 S12: a JOIN that reads a let with capture lines LATERAL has no
    # proven row coordinates; R2 refuses it once the complete source closure,
    # including the source read only inside the let, has been checked. A let
    # ending in ORDER BY and LIMIT (a top-k per left row) is refused alike.
    import socket

    import _pietto_execution_api as api
    from pietto import execution
    from pietto._project import project_execution_postgres as pg
    from pietto._project import project_job_workspace as private_workspace
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-lateral")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item = postgres.table("fixture.tags")\n'
        "table lateral_items:\n    let later:\n        capture items\n"
        "        from tags\n        where tags.id > items.id\n"
        "        select:\n            tag_id = id\n"
        + ("        order by:\n            id desc\n        limit 2\n" if top_k else "")
        + "    from items\n"
        "    let t = later\n"
        "    cross join t\n"
        "    select:\n        id = items.id\n        tag_id = t.tag_id\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    tags = json.loads(json.dumps(contract["sources"][0]))
    tags["selector"]["name"] = tags["relation"]["name"] = "tags"
    contract["sources"].append(tags)
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="lateral_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    binding = bind_values(query._template, ())
    inputs = tuple(
        R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in binding.artifact.request.sources
    )
    assert [i.name for i in inputs] == ["items", "tags"]
    with pytest.raises(ValueError, match="PUBLIC_R2_SOURCE_CLOSURE"):
        proposal.prepare_live_refinement(query, binding, inputs[:1])
    with pytest.raises(ValueError, match="REFINEMENT_LATERAL_JOIN"):
        proposal.prepare_live_refinement(query, binding, inputs)
    if not workspace_probe.qualified(tmp_path):
        return
    workspace = execution.create_workspace(
        Path(tmp_path) / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    before = sorted(
        (p.relative_to(workspace.root), p.stat().st_size)
        for p in Path(workspace.root).rglob("*")
    )

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the driver")

    for owner, name in ((pg, "_connect"), (pg, "drivers"), (socket.socket, "connect")):
        monkeypatch.setattr(owner, name, forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.save_recoverable(
            workspace,
            query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess(
                "127.0.0.1", 5432, "app", "reader", "x" * 24, "disable"
            ),
            premise=execution.PostgresDeploymentPremise(
                schemas=("fixture", "pg_catalog")
            ),
            limits=execution.ExecutionLimits(),
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "REFINEMENT_LATERAL_JOIN",
    )
    assert refused.value.attempt is None and refused.value.outcome is None
    assert (
        sorted(
            (p.relative_to(workspace.root), p.stat().st_size)
            for p in Path(workspace.root).rglob("*")
        )
        == before
    )


def test_r2_refuses_a_paired_mysql_form_before_any_workspace(tmp_path):
    """A MySQL statement opened as a qualification-pack form is that form
    only, so R2 refuses to refine it (Phase77 S16, S10, S08, S11)."""
    import _pietto_sql_paired as paired_forms
    import pietto.execution as execution
    from pietto._project.project_execution_template import bind_values

    def compiled(directory, kind="query"):
        return execution.compile_query(
            directory,
            module="main.pietto",
            kind=kind,
            name="q16",
            dialect="mysql",
            emission_contract="contract.json",
        )

    def inputs_of(binding):
        return tuple(
            execution.R2SourceInput(
                s.namespace,
                s.name,
                "provider",
                "v1",
                "r1",
                s.namespace,
                "registry",
                "SELECT 1",
                ("c_id",),
                "pietto_query",
                "retained",
            )
            for s in binding.artifact.request.sources
        )

    directory = paired_forms.project(tmp_path / "paired", 1)
    query = compiled(directory)
    binding = bind_values(query._template, ())
    inputs = inputs_of(binding)
    with pytest.raises(ValueError, match="^PUBLIC_R2_PAIRED_FORM$"):
        proposal.prepare_live_refinement(query, binding, inputs)
    with pytest.raises(ValueError, match="^PUBLIC_R2_PAIRED_FORM$"):
        proposal.check_live_refinement(query, inputs)
    for form in (3, *paired_forms.S08, 17, 25):
        kind = paired_forms.FORMS[form][1].split(" ", 1)[0]
        paired = compiled(paired_forms.project(tmp_path / f"f{form}", form), kind)
        paired_binding = bind_values(paired._template, ())
        paired_inputs = inputs_of(paired_binding)
        with pytest.raises(ValueError, match="^PUBLIC_R2_PAIRED_FORM$"):
            proposal.prepare_live_refinement(paired, paired_binding, paired_inputs)
        with pytest.raises(ValueError, match="^PUBLIC_R2_PAIRED_FORM$"):
            proposal.check_live_refinement(paired, paired_inputs)
    # The same query without its Text defaults is no form and R2 checks it.
    main = directory / "main.pietto"
    text = main.read_text(encoding="utf-8")
    for default in (', "雪")', ', "a\'b")'):
        assert text.count(default) == 1
        text = text.replace(default, ")")
    main.write_text(text, encoding="utf-8", newline="\n")
    proposal.check_live_refinement(compiled(directory), inputs)
