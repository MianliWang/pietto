"""S18 public caller wiring; the native candidate campaign invokes the producer."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import copy
import json

import pytest

import _pietto_execution_public_journey_check as journey
import _pietto_execution_public_journey_runner as runner


def test_publication_report_uses_its_public_fields():
    assert runner._publication(
        SimpleNamespace(terminal="PUBLISHED", checkpoint="ckp-1", extent=3)
    ) == {"terminal": "PUBLISHED", "checkpoint": "ckp-1", "extent": 3}


def test_r2_bridge_observer_calls_each_original_once_and_redacts_failure():
    calls, observed = [], []

    class Jobs:
        @staticmethod
        def capture_recoverable():
            calls.append("capture")
            return SimpleNamespace(
                terminal="FAILED",
                settlement="RELEASED",
                failure="ExecutionError:GENERATION_NOT_COMPLETE",
            ), None

        @staticmethod
        def recover_recoverable():
            calls.append("recover")
            return SimpleNamespace(
                terminal="FAILED",
                settlement="UNKNOWN",
                failure="ValueError:unstructured detail",
            ), None

    originals = runner._observe_r2_bridges(Jobs, observed)
    Jobs.capture_recoverable()
    Jobs.recover_recoverable()
    runner._restore_r2_bridges(Jobs, originals)
    assert calls == ["capture", "recover"]
    assert observed == [
        {
            "bridge": "capture_recoverable",
            "terminal": "FAILED",
            "settlement": "RELEASED",
            "failure": "ExecutionError:GENERATION_NOT_COMPLETE",
        },
        {
            "bridge": "recover_recoverable",
            "terminal": "FAILED",
            "settlement": "UNKNOWN",
            "failure": "ValueError",
        },
    ]


def test_public_journey_reports_mysql_constructor_failure_without_acquire(
    tmp_path, monkeypatch
):
    import _pietto_phase68_slice11_probe as workspace_probe
    import _pietto_target_conformance_resources as resources

    calls = []

    class FakeResources:
        def __init__(self, target, pin, directory):
            calls.append(("init", target, directory))
            if target == "mysql":
                raise RuntimeError("MYSQL_INIT")

        def acquire(self):
            raise AssertionError("constructor failure acquired a resource")

        def cleanup(self):
            calls.append(("cleanup", "postgres"))
            return {"status": "success"}

    monkeypatch.setattr(workspace_probe, "qualified", lambda directory: True)
    monkeypatch.setattr(resources, "Resources", FakeResources)
    evidence = tmp_path / "evidence"
    assert runner.main(str(Path(__file__).resolve().parents[1]), str(evidence)) == 1
    report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert report["error"]["reason"] == "MYSQL_INIT"
    assert report["cleanup"] == {"postgres": "success", "mysql": "not_started"}
    assert [call[:2] for call in calls] == [
        ("init", "postgres"),
        ("init", "mysql"),
        ("cleanup", "postgres"),
    ]


def _report():
    ordinary = {
        "save": "COMPLETED",
        "trust_refusals": [
            "r1_producer",
            "export_compatibility",
            "publication_producer",
        ],
        "checkpoint": "ckp-1",
        "extent": 3,
        "r1": "SAVED_SCOPE_EXHAUSTED",
        "exported": 3,
        "publication": "PUBLISHED",
        "published_extent": 3,
        "relay": "COMPLETED",
    }
    return {
        "format": "pietto.s18-public-journey.v1",
        "status": "PASS",
        "routes": {
            route: {"ordinary": ordinary.copy()}
            for route in ("postgres_rows", "postgres_adbc", "mysql_rows")
        },
        "r2": {
            route: {
                "source": "cross join rows as second",
                "source_order": [["phase66", "rows"]],
                "source_occurrences": 2,
                "expected_extent": 12,
                "values": [0, 1],
                "trust_refusals": [
                    "recovery_producer",
                    "r1_producer",
                    "export_compatibility",
                    "publication_producer",
                ],
                "prefix": "FAILED",
                "recovery": "COMPLETED",
                "checkpoint": "ckp-2",
                "extent": 12,
                "closings": 2,
                "closing_policy": "recovery_after_failed_prefix",
                "r1": "SAVED_SCOPE_EXHAUSTED",
                "exported": 12,
                "publication": "PUBLISHED",
                "published_extent": 12,
            }
            for route in ("postgres_rows", "postgres_adbc", "mysql_rows")
        },
        "cleanup": {"postgres": "success", "mysql": "success"},
    }


def test_public_journey_checker_requires_every_route_and_history():
    assert journey.check(_report()) == {
        "family": "public-journey",
        "verdict": "ACCEPTED",
    }
    bad = copy.deepcopy(_report())
    bad["routes"]["postgres_adbc"]["ordinary"]["relay"] = "FAILED"
    with pytest.raises(journey.Rejected, match="ORDINARY_postgres_adbc"):
        journey.check(bad)
    bad = copy.deepcopy(_report())
    bad["r2"]["mysql_rows"]["closings"] = 1
    with pytest.raises(journey.Rejected, match="R2_mysql_rows"):
        journey.check(bad)


def test_r2_target_inputs_remain_explicit_route_callers():
    import _pietto_execution_recovery_cases as recovery
    import pietto.execution as execution

    postgres, pg_premise = recovery.target_inputs(
        SimpleNamespace(target="postgres", port=5432, _passwords=("root", "pg"))
    )
    mysql, mysql_premise = recovery.target_inputs(
        SimpleNamespace(
            target="mysql",
            port=3306,
            _passwords=("root", "mysql"),
            ca_path="/fixture/ca.pem",
        )
    )
    assert type(postgres) is execution.PostgresAccess
    assert pg_premise.schemas == ("public", "pg_catalog")
    assert type(mysql) is execution.MySQLAccess
    assert mysql_premise.schemas == ("phase66",)
    assert mysql.account == "pietto_query@%"
    assert recovery._source_role("mysql") == mysql.account


def test_mysql_r2_fixture_adds_its_two_context_grants(monkeypatch):
    import _pietto_execution_recovery_cases as recovery
    import _pietto_phase68_slice6_probe as fixture

    providers = ({"provider": "fixture"},)
    grants = []
    monkeypatch.setattr(fixture, "setup", lambda resource: providers)
    monkeypatch.setattr(fixture, "manager", lambda resource, sql: grants.append(sql))
    assert recovery.setup_target(SimpleNamespace(target="mysql")) == providers
    assert grants == [
        "GRANT SELECT ON performance_schema.threads TO 'pietto_query'@'%'",
        "GRANT SELECT ON performance_schema.events_transactions_current "
        "TO 'pietto_query'@'%'",
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_r2_cross_fixture_has_four_ordered_sources_and_two_slots(tmp_path, target):
    import _pietto_execution_recovery_cases as recovery
    from _pietto_phase68_slice6_cases import fixture as source_fixture

    source = source_fixture(target, "R2_bound", "values")
    providers = tuple(
        {
            "namespace": item["relation"]["namespace"],
            "name": item["relation"]["name"],
            "provider": "fixture-provider",
            "version": "v1",
            "revision": "r1",
            "registry": "fixture-registry",
            "definition": "fixture view",
            "tokens": ("p68_part", "p68_lid"),
        }
        for item in json.loads(source["contract"])["sources"]
    )
    witness = recovery.live_r2(tmp_path, providers, target=target)
    expected = ((providers[0]["namespace"], providers[0]["name"]),)
    assert (
        witness.values,
        witness.source_order,
        witness.source_occurrences,
        witness.expected_extent,
    ) == (
        (0, 1),
        expected,
        2,
        12,
    )
    assert witness.source.count("cross join rows as ") == 1
    assert tuple(item.role for item in witness.source_requirements) == (
        ("pietto_query@%",)
        if target == "mysql"
        else ("pietto_query",)
    )


def test_journey_trust_refusals_preserve_the_saved_public_revision(
    tmp_path, monkeypatch
):
    import _pietto_jobs_public_cases as public_cases
    import pietto.execution as execution

    case = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if case is None:
        pytest.skip("qualified local storage is unavailable")
    assert case is not None
    try:
        pin, producer, compatibility = case.trust
        captured = journey.generation(
            execution,
            case.reference,
            SimpleNamespace(job=case.job, generation=case.generation),
        )
        assert len(captured.closings) == 1
        inputs = journey.Inputs(
            case.reference,
            None,
            "postgres_rows",
            None,
            None,
            execution.ExecutionLimits(batch_rows=2, seconds=60),
            case.user_values,
            pin,
            producer,
            compatibility[-1],
        )
        before = execution.inspect_job(case.reference, job=case.job).revision
        assert journey._trust_refusals(
            execution, inputs, captured, captured.closings[0]
        ) == ("r1_producer", "export_compatibility", "publication_producer")
        assert execution.inspect_job(case.reference, job=case.job).revision == before
    finally:
        case.close()


def test_public_journey_refuses_route_bundle_identity_and_premise_before_source(
    tmp_path, monkeypatch
):
    import pietto.execution as execution

    if not {"save", "create_workspace"} <= set(execution.__all__):
        pytest.skip("S18 preflight waits for the integrated saved-result surface")
    import _pietto_execution_api as api
    import _pietto_phase68_slice11_probe as workspace_probe
    from pietto._project import project_job_runtime as runtime

    if not workspace_probe.qualified(tmp_path):
        pytest.skip("qualified local storage is unavailable")
    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=8 * 1024 * 1024
    )
    inputs = journey.compile_inputs(
        execution,
        workspace,
        str(api.write_example(tmp_path / "project")),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 9, "db", "u", "pw", "disable"),
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        limits=execution.ExecutionLimits(batch_rows=2, seconds=60),
        values=(1,),
    )
    assert type(inputs.accepted_compatibility) is str

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused public journey opened a source")

    monkeypatch.setattr(runtime, "_owner", forbidden)
    journey.preflight_refusals(execution, inputs)
