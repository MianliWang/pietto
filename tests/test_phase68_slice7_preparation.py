"""Conditional structure must never silently discharge original obligations."""

from dataclasses import replace
import json

import pytest

from _pietto_phase68_slice7_cases import planned
from pietto._project.project_guard_preparation import (
    prepare_guarded,
    GuardPreparationError,
    verify_preparation,
)
from pietto._project.project_single_match import ProjectSingleMatchState
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_emission_ast import SQLJoinQuery
from pietto._project.project_sql_emission import (
    EmissionOutcome,
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_result_output import prepare_output


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_real_unproved_prepares_pending_without_old_verified_authority(
    tmp_path, target
):
    checked, contract = planned(tmp_path, target)
    original = emit_project_sql(checked, contract)
    assert original.status == "BLOCKED" and original.artifact is None
    assert [b.detail for b in original.blockers] == [
        "original_enforcement_not_fulfilled"
    ]
    guarded = prepare_guarded(checked, contract)
    assert type(checked.plan) is ProjectSQLPlan
    assert verify_preparation(guarded) is checked.plan.single_matches
    assert (
        guarded.scope.obligations[0].assessment.state
        is ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert guarded.artifact.request.verification is checked
    assert not verify_project_sql_emission(
        guarded.artifact, guarded.artifact.request
    ).verified
    forged = EmissionOutcome(
        "VERIFIED", checked.completed.diagnostics, guarded.artifact
    )
    assert json.loads(serialize_project_sql_emission(forged))["status"] == "BLOCKED"
    with pytest.raises(
        ValueError,
        match=r"^Emission inspection requires the exact runtime artifact and its request\.$",
    ):
        prepare_output(guarded.artifact)


def test_pending_scope_keeps_all_occurrences_and_rejects_foreign_or_missing(tmp_path):
    checked, contract = planned(tmp_path / "a", copies=2)
    guarded = prepare_guarded(checked, contract)
    assert len(guarded.scope.obligations) == len(guarded.scope.enforcement) == 2
    foreign = prepare_guarded(*planned(tmp_path / "b", copies=2))
    for scope in (
        replace(guarded.scope, obligations=guarded.scope.obligations[:1]),
        replace(guarded.scope, enforcement=()),
        foreign.scope,
    ):
        with pytest.raises(ValueError, match="^GUARD_PREPARATION_ROOT$"):
            verify_preparation(replace(guarded, scope=scope))
    with pytest.raises(ValueError, match="^GUARD_PREPARATION_ROOT$"):
        verify_preparation(replace(guarded, artifact=foreign.artifact))


def test_no_request_retains_ordinary_verified_bytes(tmp_path):
    checked, contract = planned(tmp_path, requested=False)
    original = emit_project_sql(checked, contract)
    assert original.artifact is not None
    guarded = prepare_guarded(checked, contract)
    assert guarded.scope.obligations == guarded.scope.enforcement == ()
    assert guarded.artifact.rendered.sql == original.artifact.rendered.sql
    assert verify_project_sql_emission(
        guarded.artifact, guarded.artifact.request
    ).verified


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_pending_binding_rebuilds_every_request_and_preserves_old_refusal(
    tmp_path, target
):
    from _pietto_phase68_slice7_cases import DIRECT
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_execution_binding_verification import verify_binding
    from pietto._project.project_result_output import verify_output
    from pietto._project.project_execution import (
        prepare_bound_execution,
        PostgresAccess,
    )

    body = DIRECT.replace("on lhs.id == r.id", "on lhs.id == r.id and r.key > 1")
    prepared = prepare_guarded(
        *planned(tmp_path, target, body, policy="bind_safe_literals")
    )
    template = prepare_guarded_template(prepared)
    assert len(template.slots) == 1
    caller = [[template.slots[0], 1]]
    a = bind_values(template, caller)
    b = bind_values(template, ((template.slots[0], 2),))
    caller[0][1] = 9
    assert a.values == (1,) and b.values == (2,)
    for binding in (a, b, a):
        verify_binding(binding)
        assert binding.guarded.artifact is binding.artifact
        assert len(binding.guarded.scope.enforcement) == 1
        output = prepare_guarded_output(binding.guarded, binding=binding)
        assert (
            len(
                verify_output(
                    output, binding.artifact, output.contract, binding=binding
                )
            )
            == 2
        )
        assert output.guarded is binding.guarded
        assert not verify_project_sql_emission(
            binding.artifact, binding.artifact.request
        ).verified
        with pytest.raises(ValueError, match="^EXECUTION_ARTIFACT$"):
            prepare_bound_execution(
                binding,
                PostgresAccess("127.0.0.1", 5432, "lab", "role", "not-live", "disable"),
            )
    with pytest.raises(ValueError, match="^BINDING_ARTIFACT$"):
        verify_binding(replace(a, guarded=b.guarded))
    with pytest.raises(ValueError, match="^BINDING_GUARDED_CONTEXT$"):
        verify_binding(replace(a, guarded=None))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("three_sources", (False, True))
def test_exact_legacy_multi_hop_refusal_is_preserved(tmp_path, target, three_sources):
    import json
    from copy import deepcopy
    import _pietto_phase66_sql_emission_probe as probe
    from _pietto_phase68_slice7_cases import PATH

    fixture = probe.join_witness(target, PATH, link=True)
    if three_sources:
        fixture["source"] = (
            fixture["source"]
            .replace(
                "relationship link:",
                "source middle: Row is "
                + target
                + '.table("middle")\nrelationship link:',
            )
            .replace("endpoint r: rhs", "endpoint r: middle")
            .replace(
                "query result:",
                "relationship onward:\n    endpoint l: middle\n    endpoint r: rhs\n    on l.id == r.id\nquery result:",
            )
            .replace("inner join lhs as r:", "inner join rhs as r:")
            .replace("via link: r -> l", "via onward: l -> r")
        )
        contract = json.loads(fixture["contract"])
        middle = deepcopy(contract["sources"][1])
        middle["selector"]["name"] = "middle"
        middle["relation"]["name"] = "phase66 middle"
        contract["sources"].append(middle)
        fixture["contract"] = json.dumps(contract)
    checked, outcome = probe.build_case(
        tmp_path, fixture["source"], fixture["contract"]
    )
    assert checked.verified and type(checked.plan) is ProjectSQLPlan
    assert not checked.plan.single_matches
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1003", "scalar_projection_requires_later_slice"),
        ("PIE-B1003", "scalar_projection_requires_later_slice"),
        ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
        ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
    ]


def test_private_multi_hop_carrier_keeps_unbound_input_and_old_verifier_refuses(
    tmp_path,
):
    from _pietto_phase68_slice7_cases import PATH
    from pietto._project.project_guard_preparation import GuardedArtifact
    from pietto._project.project_sql_emission import EmissionArtifact
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    try:
        p = prepare_guarded(*planned(tmp_path, body=PATH, link=True, scope="whole"))
    except GuardPreparationError as error:
        pytest.fail(
            str(error) + ": " + ",".join(b.detail for b in error.blockers),
            pytrace=False,
        )
    assert (
        type(p.artifact) is GuardedArtifact and type(p.artifact) is not EmissionArtifact
    )
    assert p.artifact.guard_scope is p.scope
    assert not verify_project_sql_emission(p.artifact, p.scope.request).verified
    assert type(p.artifact.ast) is SQLJoinQuery
    inputs = tuple(
        i for u in p.artifact.ast.units if hasattr(u, "inputs") for i in u.inputs
    )
    original = tuple(
        i
        for i in inputs
        if i.original.producer is not None and i.original.binding_use is None
    )
    assert original and all(i.use is None for i in original)
