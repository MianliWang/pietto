"""Data-only laws for the unexported S12 carrier preparation."""

from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import pytest

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
        + 'source tags: Item is postgres.table("fixture.tags")\n'
        "table tagged_items:\n    let tagged:\n        from tags\n"
        "        select:\n            tag_id = id\n    from items\n"
        "    inner join tagged as t:\n        from items\n"
        "        on items.id == t.tag_id\n    select:\n        id = items.id\n",
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
    """A query that groups by its own `let:` value is not an R2 shape yet."""
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
        ("computed", "    let:\n        big = id > 5\n" + computed, True),
        # A later stage carries the key on by a read; it is still computed.
        (
            "let_where",
            "    let:\n        big = id > 5\n    where id > 0\n" + computed,
            True,
        ),
        (
            "two_lets",
            "    let:\n        big = id > 5\n        other = id + 0\n" + computed,
            True,
        ),
        # S05j: the JOIN key's own LET unit comes before the one for `level`.
        (
            "joined",
            "    inner join items as r:\n        from items\n"
            "        on items.id == r.id\n    let:\n"
            "        later = items.id > r.id or r.id > 12\n"
            "        level = r.id + items.id * 0\n    group by:\n        later\n"
            "    select:\n        b = later\n        top = max(level)\n",
            True,
        ),
        (
            "field",
            "    group by:\n        label\n    select:\n        label\n",
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


def test_live_refinement_refuses_an_existence_read_after_its_source_closure(
    tmp_path, monkeypatch
):
    import _pietto_execution_api as api
    from pietto._project.project_execution_template import bind_values
    from pietto.execution import R2SourceInput, compile_query

    project = api.write_example(Path(tmp_path) / "r2-exists")
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + 'source tags: Item is postgres.table("fixture.tags")\n'
        "table flagged_items:\n    let tagged:\n        from tags\n"
        "        select:\n            tag_id = id\n    from items\n"
        "    where exists tagged\n    select:\n        id = items.id\n",
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
    # The source read only through the existence read is a required input,
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
