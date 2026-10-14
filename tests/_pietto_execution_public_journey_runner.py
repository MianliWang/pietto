"""Run one explicit, bounded public S18 route campaign."""

from __future__ import annotations

import json
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any

import _pietto_execution_public_journey_check as journey


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _publication(value: Any) -> dict[str, Any]:
    return {
        "terminal": value.terminal,
        "checkpoint": value.checkpoint,
        "extent": value.extent,
    }


def _ordinary(
    execution: Any, journey: Any, inputs: Any, relay_inputs: Any, root: Path
) -> dict[str, Any]:
    saved, generation, end, published, trust_refusals = journey.ordinary(
        execution, inputs
    )
    relay = journey.relay(execution, relay_inputs, str(root / "sink"))
    return {
        "save": saved.terminal,
        "trust_refusals": list(trust_refusals),
        "checkpoint": generation.checkpoint,
        "extent": generation.extent,
        "r1": end.terminal,
        "exported": generation.extent,
        "publication": published.terminal,
        "published_extent": published.extent,
        "relay": relay.terminal,
    }


def _r2(
    execution: Any,
    journey: Any,
    workspace: Any,
    fixture: Any,
    route: str,
    access: Any,
    premise: Any,
    prefix_limits: Any,
    recovery_limits: Any,
) -> dict[str, Any]:
    inputs = journey.Inputs(
        workspace,
        fixture.query,
        route,
        access,
        premise,
        recovery_limits,
        fixture.values,
        *fixture.trust,
    )
    prefix, generation, recovery, end, published, trust_refusals = journey.recoverable(
        execution,
        inputs,
        source_requirements=fixture.source_requirements,
        prefix_limits=prefix_limits,
        recovery_limits=recovery_limits,
    )
    return {
        "source": fixture.source,
        "source_order": [list(item) for item in fixture.source_order],
        "source_occurrences": fixture.source_occurrences,
        "expected_extent": fixture.expected_extent,
        "values": list(fixture.values),
        "trust_refusals": list(trust_refusals),
        "prefix": prefix.terminal,
        "recovery": recovery.terminal,
        "checkpoint": generation.checkpoint,
        "extent": generation.extent,
        "closings": len(generation.closings),
        "closing_policy": "recovery_after_failed_prefix",
        "r1": end.terminal,
        "exported": generation.extent,
        "publication": published.terminal,
        "published_extent": published.extent,
    }


def _workspace(execution: Any, root: Path) -> Any:
    return execution.create_workspace(root, budget_bytes=8 * 1024 * 1024)


def _failure_label(value: Any) -> str | None:
    if type(value) is not str:
        return None
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):([A-Z][A-Z0-9_]*)", value)
    if match is not None:
        return match.group(0)
    name = value.partition(":")[0]
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else None


def _observe_r2_bridges(jobs: Any, observed: list[dict[str, Any]]) -> dict[str, Any]:
    originals = {}
    for name in ("capture_recoverable", "recover_recoverable"):
        original = getattr(jobs, name)
        originals[name] = original

        def wrapped(*arguments, _name=name, _original=original, **keywords):
            state, pending = _original(*arguments, **keywords)
            observed.append(
                {
                    "bridge": _name,
                    "terminal": state.terminal,
                    "settlement": state.settlement,
                    "failure": _failure_label(state.failure),
                }
            )
            return state, pending

        setattr(jobs, name, wrapped)
    return originals


def _restore_r2_bridges(jobs: Any, originals: dict[str, Any]) -> None:
    for name, original in originals.items():
        setattr(jobs, name, original)


def _postgres_inputs(
    execution: Any,
    journey: Any,
    workspace: Any,
    project: Path,
    access: Any,
    limits: Any,
    route: str,
) -> Any:
    return journey.compile_inputs(
        execution,
        workspace,
        str(project),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
        route=route,
        access=access,
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        limits=limits,
        values=(1,),
    )


def _mysql_inputs(
    execution: Any, journey: Any, workspace: Any, project: Path, resource: Any
) -> Any:
    return journey.compile_inputs(
        execution,
        workspace,
        str(project),
        module="main.pietto",
        kind="table",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
        route="mysql_rows",
        access=execution.MySQLAccess(
            "localhost",
            resource.port,
            "phase66",
            "pietto_query",
            resource._passwords[1],
            str(resource.ca_path),
            "pietto_query@%",
        ),
        premise=execution.MySQLDeploymentPremise(("phase66",)),
        limits=execution.ExecutionLimits(batch_rows=2, max_rows=64, seconds=60),
        values=(),
    )


def main(snapshot: str, evidence: str) -> int:
    snapshot_root, evidence_root = Path(snapshot), Path(evidence)
    evidence_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    sys.path.insert(0, str(snapshot_root / "tests"))
    import _pietto_execution_api as api
    import _pietto_execution_api_probe as probe
    import _pietto_execution_jobs_probe as workspace_probe
    import _pietto_target_conformance_resources as resources_module
    import pietto.execution as execution

    report: dict[str, Any] = {
        "format": "pietto.s18-public-journey.v1",
        "snapshot": str(snapshot_root),
        "status": "STARTED",
    }
    postgres = mysql = None
    try:
        if not workspace_probe.qualified(evidence_root):
            report["status"] = "UNQUALIFIED_STORAGE"
            return 2
        pins = json.loads(
            (snapshot_root / "tests/phase66_target_pins.json").read_text()
        )
        postgres_root, mysql_root = (
            evidence_root / "resources",
            evidence_root / "mysql-resources",
        )
        for root in (postgres_root, mysql_root):
            root.mkdir(mode=0o700, parents=True)
        postgres = resources_module.Resources(
            "postgres", pins["targets"]["postgres"], postgres_root
        )
        mysql = resources_module.Resources(
            "mysql", pins["targets"]["mysql"], mysql_root
        )
        passwords = {role: secrets.token_hex(16) for role in probe.ROLES}
        routes, r2 = {}, {}
        report.update(routes=routes, r2=r2)
        postgres.acquire()
        from _pietto_execution_recovery_cases import (
            live_r2,
            prefix_limits,
            recovery_limits,
            setup_target,
            target_inputs,
        )

        postgres_providers = setup_target(postgres)
        r2_access, r2_premise = target_inputs(postgres)
        for route in ("postgres_rows", "postgres_adbc"):
            r2[route] = _r2(
                execution,
                journey,
                _workspace(execution, evidence_root / (route + "-r2")),
                live_r2(
                    evidence_root / (route + "-r2-project"),
                    postgres_providers,
                    target="postgres",
                ),
                route,
                r2_access,
                r2_premise,
                prefix_limits(),
                recovery_limits(),
            )
        report["server"] = probe.prepare_server(postgres, passwords)
        project = api.write_example(evidence_root / "project")
        access = execution.PostgresAccess(
            "127.0.0.1",
            postgres.port,
            "phase66",
            "pietto_reader",
            passwords["pietto_reader"],
            "require",
        )
        limits = execution.ExecutionLimits(batch_rows=2, max_rows=64, seconds=60)
        for route in ("postgres_rows", "postgres_adbc"):
            inputs = _postgres_inputs(
                execution,
                journey,
                _workspace(execution, evidence_root / route),
                project,
                access,
                limits,
                route,
            )
            relay_inputs = _postgres_inputs(
                execution,
                journey,
                _workspace(execution, evidence_root / (route + "-relay")),
                project,
                access,
                limits,
                route,
            )
            journey.preflight_refusals(execution, inputs)
            routes[route] = {
                "ordinary": _ordinary(
                    execution, journey, inputs, relay_inputs, evidence_root / route
                )
            }

        mysql.acquire()
        from _pietto_execution_api_mysql_native import _configure_tls, _public_project
        from _pietto_execution_source_assurance_probe import manager

        _configure_tls(mysql)
        mysql_providers = setup_target(mysql)
        mysql_access, mysql_premise = target_inputs(mysql)
        r2["mysql_rows"] = _r2(
            execution,
            journey,
            _workspace(execution, evidence_root / "mysql-r2"),
            live_r2(
                evidence_root / "mysql-r2-project",
                mysql_providers,
                target="mysql",
            ),
            "mysql_rows",
            mysql_access,
            mysql_premise,
            prefix_limits(),
            recovery_limits(),
        )
        mysql_project_root = evidence_root / "mysql-project"
        mysql_project_root.mkdir(mode=0o700)
        mysql_project = _public_project(mysql_project_root)
        manager(
            mysql,
            "CREATE TABLE phase66.s06_public_rows "
            "(left_id BIGINT NOT NULL,right_key BIGINT NULL)",
        )
        manager(
            mysql,
            "INSERT INTO phase66.s06_public_rows (left_id,right_key) "
            "VALUES (1,NULL),(1,NULL)",
        )
        mysql_inputs = _mysql_inputs(
            execution,
            journey,
            _workspace(execution, evidence_root / "mysql-workspace"),
            mysql_project,
            mysql,
        )
        mysql_relay_inputs = _mysql_inputs(
            execution,
            journey,
            _workspace(execution, evidence_root / "mysql-relay-workspace"),
            mysql_project,
            mysql,
        )
        journey.preflight_refusals(execution, mysql_inputs)
        mysql_journey_root = evidence_root / "mysql-journey"
        mysql_journey_root.mkdir(mode=0o700)
        routes["mysql_rows"] = {
            "ordinary": _ordinary(
                execution,
                journey,
                mysql_inputs,
                mysql_relay_inputs,
                mysql_journey_root,
            )
        }
        report.update(
            status="PASS",
        )
        return 0
    except Exception as error:
        report.update(
            status="FAILED",
            error={
                "type": type(error).__name__,
                "code": getattr(error, "code", None),
                "detail": getattr(error, "detail", None),
                "reason": str(error),
            },
        )
        return 1
    finally:
        report["cleanup"] = {
            "postgres": "not_started"
            if postgres is None
            else postgres.cleanup()["status"],
            "mysql": "not_started" if mysql is None else mysql.cleanup()["status"],
        }
        if report.get("status") == "PASS":
            try:
                journey.check(report)
            except Exception as error:
                report.update(
                    status="FAILED",
                    error={"type": type(error).__name__, "reason": str(error)},
                )
        _write(evidence_root / "report.json", report)
        if report["status"] == "FAILED":
            return 1


def diagnostic_main(snapshot: str, evidence: str) -> int:
    """Observe one PostgreSQL R2 capture bridge without qualifying a candidate."""
    snapshot_root, evidence_root = Path(snapshot), Path(evidence)
    evidence_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    sys.path.insert(0, str(snapshot_root / "tests"))
    import _pietto_execution_jobs_probe as workspace_probe
    import _pietto_target_conformance_resources as resources_module
    import pietto.execution as execution
    from pietto._project import project_public_jobs as jobs

    report: dict[str, Any] = {
        "format": "pietto.s18-public-journey-diagnostic.v1",
        "snapshot": str(snapshot_root),
        "status": "STARTED",
        "bridges": [],
    }
    postgres = None
    originals = None
    try:
        if not workspace_probe.qualified(evidence_root):
            report["status"] = "UNQUALIFIED_STORAGE"
            return 2
        pins = json.loads(
            (snapshot_root / "tests/phase66_target_pins.json").read_text()
        )
        resource_root = evidence_root / "resources"
        resource_root.mkdir(mode=0o700)
        postgres = resources_module.Resources(
            "postgres", pins["targets"]["postgres"], resource_root
        )
        postgres.acquire()
        from _pietto_execution_recovery_cases import (
            live_r2,
            prefix_limits,
            setup_target,
            target_inputs,
        )

        fixture = live_r2(
            evidence_root / "r2-project", setup_target(postgres), target="postgres"
        )
        access, premise = target_inputs(postgres)
        workspace = _workspace(execution, evidence_root / "r2-workspace")
        originals = _observe_r2_bridges(jobs, report["bridges"])
        reply = execution.save_recoverable(
            workspace,
            fixture.query,
            source_requirements=fixture.source_requirements,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=access,
            premise=premise,
            limits=prefix_limits(),
            values=fixture.values,
        )
        report.update(
            status="OBSERVED",
            reply={
                "terminal": reply.terminal,
                "settlement": reply.settlement,
                "has_cleanup": reply.cleanup is not None,
            },
        )
        return 0
    except Exception as error:
        report.update(
            status="FAILED",
            error={"type": type(error).__name__, "reason": _failure_label(str(error))},
        )
        return 1
    finally:
        if originals is not None:
            _restore_r2_bridges(jobs, originals)
        report["cleanup"] = (
            "not_started" if postgres is None else postgres.cleanup()["status"]
        )
        _write(evidence_root / "report.json", report)


def _measurement_status(sample: dict[str, Any]) -> str:
    required = (
        "container_cpu_percent",
        "container_memory_used_bytes",
        "container_memory_limit_bytes",
        "database_clock",
        "database_client_realtime_offset_bounds_ns",
    )
    return (
        "OBSERVED"
        if all(sample.get(key) is not None for key in required)
        else "PARTIAL"
    )


def _measure_targets(
    pins: dict[str, Any],
    evidence_root: Path,
    resources_module: Any,
    observer: Any,
    *,
    clock: Any = time.monotonic,
) -> tuple[list[dict[str, Any]], BaseException | None]:
    """Acquire, sample, and close each target before the next target begins."""
    targets: list[dict[str, Any]] = []
    interrupted: BaseException | None = None
    for target in ("postgres", "mysql"):
        resource = None
        started = clock()
        row: dict[str, Any] = {"target": target, "status": "STARTED"}
        try:
            target_root = evidence_root / target
            target_root.mkdir(mode=0o700, parents=True)
            resource = resources_module.Resources(
                target, pins["targets"][target], target_root
            )
            with resources_module.deadline(20 * 60):
                resource.acquire()
                sample = observer.observe(resource)
            row.update(status=_measurement_status(sample), sample=sample)
        except BaseException as error:
            row.update(
                status="FAILED",
                error={
                    "type": type(error).__name__,
                    "reason": _failure_label(str(error)),
                },
            )
            interrupted = error if not isinstance(error, Exception) else None
        finally:
            row["elapsed_seconds"] = clock() - started
            try:
                row["cleanup"] = (
                    "not_started" if resource is None else resource.cleanup()["status"]
                )
            except BaseException as error:
                row["cleanup"] = "FAILED_EXCEPTION"
                row["cleanup_error"] = type(error).__name__
                interrupted = error if not isinstance(error, Exception) else interrupted
            if resource is not None and row["cleanup"] != "success":
                row["status"] = "CLEANUP_FAILED"
            if row["elapsed_seconds"] > 20 * 60:
                row["status"] = "TIME_CAP_EXCEEDED"
            targets.append(row)
        if row["status"] in {"FAILED", "CLEANUP_FAILED", "TIME_CAP_EXCEEDED"}:
            break
        if interrupted is not None:
            break
    return targets, interrupted


def measurement_main(snapshot: str, evidence: str) -> int:
    """Calibrate two current owned containers serially; it runs no query journey."""
    snapshot_root, evidence_root = Path(snapshot), Path(evidence)
    evidence_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    sys.path.insert(0, str(snapshot_root / "tests"))
    import _pietto_harness_resource_observer as observer
    import _pietto_target_conformance_resources as resources_module

    pins = json.loads((snapshot_root / "tests/phase66_target_pins.json").read_text())
    targets, interrupted = _measure_targets(
        pins, evidence_root, resources_module, observer
    )
    report: dict[str, Any] = {
        "format": "pietto.resource-calibration.v1",
        "snapshot": str(snapshot_root),
        "targets": targets,
        "sample_bound": 2,
        "status": "PASS"
        if len(targets) == 2 and all(row["status"] == "OBSERVED" for row in targets)
        else "PARTIAL_OR_FAILED",
    }
    _write(evidence_root / "report.json", report)
    if interrupted is not None:
        raise interrupted
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    if sys.argv[1] == "diagnostic":
        raise SystemExit(diagnostic_main(sys.argv[2], sys.argv[3]))
    if sys.argv[1] == "measure":
        raise SystemExit(measurement_main(sys.argv[2], sys.argv[3]))
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
