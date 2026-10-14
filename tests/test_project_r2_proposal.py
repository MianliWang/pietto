"""Data-only laws for the unexported S12 carrier preparation."""

from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

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
