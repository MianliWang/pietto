"""Public-only caller for one real S18 ordinary saved-result journey."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


class UnavailableJourney(AssertionError):
    """A candidate lacks a public prerequisite; it is not an accepted witness."""


class Rejected(ValueError):
    """The data-only campaign checker rejected an incomplete witness."""


@dataclass(frozen=True, slots=True)
class Inputs:
    workspace: Any
    query: Any
    route: str
    access: Any
    premise: Any
    limits: Any
    values: tuple
    expected_pin: str
    accepted_producer: str
    accepted_compatibility: str


@dataclass(frozen=True, slots=True)
class Generation:
    job: str
    identity: str
    checkpoint: str
    extent: int
    closings: tuple[str, ...]


def compile_inputs(
    execution: Any,
    workspace: Any,
    project: str,
    *,
    module: str,
    kind: str,
    name: str,
    dialect: str,
    emission_contract: str,
    route: str,
    access: Any,
    premise: Any,
    limits: Any,
    values: tuple,
    literal_policy: str = "bind-safe",
) -> Inputs:
    """Compile the candidate's ordinary query and keep its public trust records."""
    query = execution.compile_query(
        project,
        module=module,
        kind=kind,
        name=name,
        dialect=dialect,
        emission_contract=emission_contract,
        literal_policy=literal_policy,
    )
    bundle = execution.export_bundle(query)
    if type(bundle.compatibility) is not str:
        raise UnavailableJourney("BUNDLE_COMPATIBILITY_ABI")
    return Inputs(
        workspace,
        query,
        route,
        access,
        premise,
        limits,
        values,
        bundle.pin,
        bundle.producer,
        bundle.compatibility,
    )


def generation(
    execution: Any, workspace: Any, reply: Any, *, complete=True
) -> Generation:
    """Read the explicit durable names needed by later public calls."""
    if reply.job is None or reply.generation is None:
        raise UnavailableJourney("SAVE_REPLY_GENERATION")
    observed = execution.inspect_job(workspace, job=reply.job)
    matches = tuple(
        item for item in observed.generations if item.identity == reply.generation
    )
    if len(matches) != 1:
        raise UnavailableJourney("GENERATION_IDENTITY")
    item = matches[0]
    if item.checkpoint is None or item.frontier <= 0 or item.holes:
        raise UnavailableJourney("GENERATION_NOT_COMPLETE")
    if complete and item.observed_end != item.frontier:
        raise UnavailableJourney("GENERATION_NOT_COMPLETE")
    return Generation(
        reply.job, item.identity, item.checkpoint, item.frontier, item.closings
    )


def explicit_closing(generation: Generation, closing: str) -> str:
    """Require the caller to name its recorded terminal attempt."""
    if closing not in generation.closings:
        raise UnavailableJourney("GENERATION_CLOSING")
    return closing


def _refused(call: Any, detail: str | None = None) -> None:
    try:
        call()
    except Exception as refused:
        if detail is None or getattr(refused, "detail", None) == detail:
            return
        raise
    raise UnavailableJourney(detail or "PUBLIC_REFUSAL")


def preflight_refusals(execution: Any, inputs: Inputs) -> None:
    """Reject route, bundle, workspace identity and premise before a source run."""
    _refused(
        lambda: execution.save(
            inputs.workspace,
            inputs.query,
            operation=execution.new_operation(),
            route="mysql_rows"
            if inputs.route.startswith("postgres")
            else "postgres_rows",
            access=inputs.access,
            premise=inputs.premise,
            limits=inputs.limits,
            values=inputs.values,
        ),
        "PUBLIC_ROUTE_UNAVAILABLE",
    )
    bundle = execution.export_bundle(inputs.query)
    _refused(
        lambda: execution.load_bundle(
            bundle.payload,
            expected_pin="0" * 64,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        ),
        "COMPILED_CONTENT_PIN",
    )
    _refused(
        lambda: execution.open_workspace(
            inputs.workspace.root, expected_identity="ws-" + "0" * 32
        ),
        "WORKSPACE_IDENTITY",
    )
    _refused(
        lambda: execution.save(
            inputs.workspace,
            inputs.query,
            operation=execution.new_operation(),
            route=inputs.route,
            access=inputs.access,
            premise=None,
            limits=inputs.limits,
            values=inputs.values,
        ),
        "PUBLIC_PREMISE_REQUIRED",
    )


def _trust_refusals(
    execution: Any, inputs: Inputs, captured: Generation, closing: str
) -> tuple[str, ...]:
    common = dict(
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        expected_pin=inputs.expected_pin,
        accepted_producer=inputs.accepted_producer,
        accepted_compatibility=inputs.accepted_compatibility,
        values=inputs.values,
        scope="complete_capture",
        extent=captured.extent,
        purpose="s18-trust-refusal",
        route=inputs.route,
        batch_rows=inputs.limits.batch_rows,
        seconds=inputs.limits.seconds,
    )
    _refused(
        lambda: execution.open_saved_read(
            inputs.workspace,
            **(common | {"accepted_producer": "0" * 64}),
            consumer=execution.new_consumer_identity(),
            register_operation=execution.new_operation(),
            open_operation=execution.new_operation(),
        )
    )
    _refused(
        lambda: execution.verified_export(
            inputs.workspace,
            **(common | {"accepted_compatibility": "0" * 64}),
        )
    )
    _refused(
        lambda: execution.publish_saved_generation(
            inputs.workspace,
            job=captured.job,
            generation=captured.identity,
            checkpoint=captured.checkpoint,
            closing=explicit_closing(captured, closing),
            purpose="s18-trust-refusal",
            route=inputs.route,
            isolation="stable",
            values=inputs.values,
            expected_pin=inputs.expected_pin,
            accepted_producer="0" * 64,
            accepted_compatibility=inputs.accepted_compatibility,
            seconds=inputs.limits.seconds,
            operation=execution.new_operation(),
        )
    )
    return ("r1_producer", "export_compatibility", "publication_producer")


def _r1_export_publish(
    execution: Any, inputs: Inputs, captured: Generation, closing: str
) -> tuple[Any, Any, tuple[str, ...]]:
    """Exercise the public source-free reader, export and one named closing."""
    common = dict(
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        consumer=execution.new_consumer_identity(),
        expected_pin=inputs.expected_pin,
        accepted_producer=inputs.accepted_producer,
        accepted_compatibility=inputs.accepted_compatibility,
        values=inputs.values,
        scope="complete_capture",
        extent=captured.extent,
        purpose="s18-r1",
        route=inputs.route,
        batch_rows=inputs.limits.batch_rows,
        seconds=inputs.limits.seconds,
    )
    trust_refusals = _trust_refusals(execution, inputs, captured, closing)
    first = execution.open_saved_read(
        inputs.workspace,
        **common,
        register_operation=execution.new_operation(),
        open_operation=execution.new_operation(),
    )
    try:
        unacknowledged = first.next(
            inputs.limits.batch_rows, operation=execution.new_operation()
        )
        if type(unacknowledged) is not execution.SavedBatch:
            raise UnavailableJourney("R1_EMPTY")
        unacknowledged.batch.close()
    finally:
        first.close()
    reopened = execution.open_saved_read(
        inputs.workspace,
        **common,
        register_operation=None,
        open_operation=execution.new_operation(),
    )
    try:
        repeated = reopened.next(
            inputs.limits.batch_rows, operation=execution.new_operation()
        )
        if type(repeated) is not execution.SavedBatch or (
            repeated.start,
            repeated.stop,
        ) != (unacknowledged.start, unacknowledged.stop):
            raise UnavailableJourney("R1_UNACKNOWLEDGED_REOPEN")
        repeated.batch.close()
        reopened.ack(repeated, operation=execution.new_operation())
        while True:
            item = reopened.next(
                inputs.limits.batch_rows, operation=execution.new_operation()
            )
            if type(item) is execution.SavedReadEnd:
                end = item
                break
            item.batch.close()
            reopened.ack(item, operation=execution.new_operation())
    finally:
        reopened.close()
    if (end.checkpoint, end.extent, end.acknowledged) != (
        captured.checkpoint,
        captured.extent,
        captured.extent,
    ):
        raise UnavailableJourney("R1_ACK")
    rows = 0
    with execution.verified_export(
        inputs.workspace,
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        scope="complete_capture",
        extent=captured.extent,
        purpose="s18-verified-export",
        route=inputs.route,
        values=inputs.values,
        expected_pin=inputs.expected_pin,
        accepted_producer=inputs.accepted_producer,
        accepted_compatibility=inputs.accepted_compatibility,
        seconds=inputs.limits.seconds,
        batch_rows=inputs.limits.batch_rows,
    ) as exported:
        for batch in exported:
            rows += batch.num_rows
            batch.close()
    if rows != captured.extent:
        raise UnavailableJourney("VERIFIED_EXPORT_EXTENT")
    published = execution.publish_saved_generation(
        inputs.workspace,
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        closing=explicit_closing(captured, closing),
        purpose="s18-publication",
        route=inputs.route,
        isolation="stable",
        values=inputs.values,
        expected_pin=inputs.expected_pin,
        accepted_producer=inputs.accepted_producer,
        accepted_compatibility=inputs.accepted_compatibility,
        seconds=inputs.limits.seconds,
        operation=execution.new_operation(),
    )
    if (
        published.terminal,
        published.checkpoint,
        published.extent,
    ) != ("PUBLISHED", captured.checkpoint, captured.extent):
        raise UnavailableJourney("PUBLICATION")
    return end, published, trust_refusals


def ordinary(
    execution: Any, inputs: Inputs
) -> tuple[Any, Generation, Any, Any, tuple[str, ...]]:
    """Save and finish one ordinary generation with its only recorded closing."""
    saved = execution.save(
        inputs.workspace,
        inputs.query,
        operation=execution.new_operation(),
        route=inputs.route,
        access=inputs.access,
        premise=inputs.premise,
        limits=inputs.limits,
        values=inputs.values,
    )
    if (saved.terminal, saved.settlement, saved.cleanup) != (
        "COMPLETED",
        "RELEASED",
        None,
    ):
        raise UnavailableJourney("ORDINARY_CAPTURE")
    captured = generation(execution, inputs.workspace, saved)
    if len(captured.closings) != 1:
        raise UnavailableJourney("ORDINARY_CLOSING_CARDINALITY")
    end, published, trust_refusals = _r1_export_publish(
        execution, inputs, captured, captured.closings[0]
    )
    return saved, captured, end, published, trust_refusals


def recoverable(
    execution: Any,
    inputs: Inputs,
    *,
    source_requirements: tuple,
    prefix_limits: Any,
    recovery_limits: Any,
) -> tuple[Any, Generation, Any, Any, Any, tuple[str, ...]]:
    """Keep a failed prefix and recover it once under a named closing policy."""
    failed = execution.save_recoverable(
        inputs.workspace,
        inputs.query,
        source_requirements=source_requirements,
        operation=execution.new_operation(),
        route=inputs.route,
        access=inputs.access,
        premise=inputs.premise,
        limits=prefix_limits,
        values=inputs.values,
    )
    if failed.terminal != "FAILED" or failed.cleanup is not None:
        raise UnavailableJourney("R2_FAILED_PREFIX")
    prefix = generation(execution, inputs.workspace, failed, complete=False)
    if len(prefix.closings) != 1:
        raise UnavailableJourney("R2_PREFIX_CLOSING")
    _refused(
        lambda: execution.recover(
            inputs.workspace,
            job=prefix.job,
            generation=prefix.identity,
            checkpoint=prefix.checkpoint,
            query=inputs.query,
            source_requirements=source_requirements,
            operation=execution.new_operation(),
            route=inputs.route,
            access=inputs.access,
            premise=inputs.premise,
            limits=recovery_limits,
            expected_pin=inputs.expected_pin,
            accepted_producer="0" * 64,
            accepted_compatibility=inputs.accepted_compatibility,
            purpose="s18-r2-trust-refusal",
            seconds=int(recovery_limits.seconds),
            values=inputs.values,
        ),
        "PUBLIC_R2_TRUST",
    )
    operation = execution.new_operation()
    recovered = execution.recover(
        inputs.workspace,
        job=prefix.job,
        generation=prefix.identity,
        checkpoint=prefix.checkpoint,
        query=inputs.query,
        source_requirements=source_requirements,
        operation=operation,
        route=inputs.route,
        access=inputs.access,
        premise=inputs.premise,
        limits=recovery_limits,
        expected_pin=inputs.expected_pin,
        accepted_producer=inputs.accepted_producer,
        accepted_compatibility=inputs.accepted_compatibility,
        purpose="s18-r2-recovery",
        seconds=int(recovery_limits.seconds),
        values=inputs.values,
    )
    if (recovered.terminal, recovered.settlement, recovered.cleanup) != (
        "COMPLETED",
        "RELEASED",
        None,
    ):
        raise UnavailableJourney("R2_RECOVERY")
    current = execution.operation_result(inputs.workspace, operation)
    if current is None or current.operation != operation:
        raise UnavailableJourney("R2_RECOVERY_OPERATION")
    completed = generation(execution, inputs.workspace, recovered)
    if len(completed.closings) != 2 or completed.closings[:1] != prefix.closings:
        raise UnavailableJourney("R2_CLOSING_ORDER")
    # The caller owns this policy: only the newly appended recovery closing may publish.
    end, published, trust_refusals = _r1_export_publish(
        execution, inputs, completed, completed.closings[1]
    )
    return (
        failed,
        completed,
        recovered,
        end,
        published,
        ("recovery_producer", *trust_refusals),
    )


def relay(execution: Any, inputs: Inputs, sink_root: str) -> Any:
    """Create a local sink and send one fresh public relay to it."""
    sink = execution.create_reference_sink(
        sink_root, namespace="s18", epoch=1, retention_seconds=60
    )
    reply = execution.relay_live(
        inputs.workspace,
        inputs.query,
        operation=execution.new_operation(),
        route=inputs.route,
        access=inputs.access,
        premise=inputs.premise,
        sink_root=sink.root,
        expected_sink_identity=sink.identity,
        sink_namespace=sink.namespace,
        sink_epoch=sink.epoch,
        sink_retention=sink.retention,
        sink_budget_bytes=sink.budget_bytes,
        sink_busy_seconds=sink.busy_seconds,
        limits=inputs.limits,
        values=inputs.values,
    )
    if (reply.terminal, reply.settlement, reply.cleanup) != (
        "COMPLETED",
        "RELEASED",
        None,
    ):
        raise UnavailableJourney("LIVE_RELAY")
    return reply


def _need(value: bool, reason: str) -> None:
    if not value:
        raise Rejected(reason)


def check(report: Any) -> dict[str, str]:
    """Check raw campaign facts without importing Pietto or opening a service."""
    _need(type(report) is dict, "ENVELOPE")
    _need(report.get("format") == "pietto.s18-public-journey.v1", "FORMAT")
    _need(report.get("status") == "PASS", "STATUS")
    routes = report.get("routes")
    _need(
        type(routes) is dict
        and set(routes) == {"postgres_rows", "postgres_adbc", "mysql_rows"},
        "ROUTES",
    )
    for route, facts in routes.items():
        if type(route) is not str:
            raise Rejected("ROUTE_KEY")
        if type(facts) is not dict:
            raise Rejected("ROUTE_" + route)
        ordinary_facts = facts.get("ordinary")
        if type(ordinary_facts) is not dict:
            raise Rejected("ORDINARY_" + route)
        _need(
            ordinary_facts.get("save") == "COMPLETED"
            and ordinary_facts.get("trust_refusals")
            == ["r1_producer", "export_compatibility", "publication_producer"]
            and ordinary_facts.get("r1") == "SAVED_SCOPE_EXHAUSTED"
            and ordinary_facts.get("exported") == ordinary_facts.get("extent")
            and ordinary_facts.get("publication") == "PUBLISHED"
            and ordinary_facts.get("published_extent") == ordinary_facts.get("extent")
            and ordinary_facts.get("relay") == "COMPLETED"
            and type(ordinary_facts.get("checkpoint")) is str
            and type(ordinary_facts.get("extent")) is int
            and ordinary_facts["extent"] > 0,
            "ORDINARY_" + route,
        )
    r2 = report.get("r2")
    _need(type(r2) is dict and set(r2) == set(routes), "R2_ROUTES")
    for route, facts in r2.items():
        if type(route) is not str or type(facts) is not dict:
            raise Rejected("R2_ROUTE")
        order = facts.get("source_order")
        _need(
            type(facts.get("source")) is str
            and facts["source"].count("cross join rows as ") == 1
            and type(order) is list
            and len(order) == 1
            and facts.get("source_occurrences") == 2
            and facts.get("values") == [0, 1]
            and facts.get("expected_extent") == 12
            and facts.get("prefix") == "FAILED"
            and facts.get("trust_refusals")
            == [
                "recovery_producer",
                "r1_producer",
                "export_compatibility",
                "publication_producer",
            ]
            and facts.get("recovery") == "COMPLETED"
            and facts.get("closings") == 2
            and facts.get("closing_policy") == "recovery_after_failed_prefix"
            and facts.get("r1") == "SAVED_SCOPE_EXHAUSTED"
            and facts.get("extent") == 12
            and facts.get("exported") == 12
            and facts.get("publication") == "PUBLISHED"
            and facts.get("published_extent") == 12
            and type(facts.get("checkpoint")) is str
            and type(facts.get("extent")) is int,
            "R2_" + route,
        )
    cleanup = report.get("cleanup")
    _need(type(cleanup) is dict and set(cleanup) == {"postgres", "mysql"}, "CLEANUP")
    _need(all(value == "success" for value in cleanup.values()), "CLEANUP")
    return {"family": "public-journey", "verdict": "ACCEPTED"}


def main(path: str) -> int:
    print(json.dumps(check(json.loads(Path(path).read_text(encoding="utf-8")))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
