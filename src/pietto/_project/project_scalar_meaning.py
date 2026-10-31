"""Explicit finite scalar meanings over exact verified source occurrences.

Acquisition applies an approved closed law to actual builtin source evidence.
Verification reads the retained authorities independently; no constructor history
or producer/Arrow description can supply an absent meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    CompiledSQLPlanVerification,
)

__all__: tuple[str, ...] = ()


class ScalarMeaningError(ValueError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


@dataclass(frozen=True, slots=True)
class TimestampMeaning:
    calendar: str = "proleptic_gregorian"
    resolution: str = "microsecond"
    timezone: str = "absent"
    lower: tuple[int, ...] = (1000, 1, 1, 0, 0, 0, 0)
    upper: tuple[int, ...] = (9999, 12, 31, 23, 59, 59, 499999)


@dataclass(frozen=True, slots=True)
class UUIDMeaning:
    byte_order: str = "big_endian"
    byte_width: int = 16


@dataclass(frozen=True, slots=True, eq=False)
class ScalarMeaningEntry:
    ordinal: int
    source_port: Any = field(repr=False)
    declared: Any = field(repr=False)
    canonical: Any = field(repr=False)
    resolution: Any = field(repr=False)
    law: TimestampMeaning | UUIDMeaning


@dataclass(frozen=True, slots=True, eq=False)
class ScalarMeaningBundle:
    verification: ProjectSQLPlanVerification | CompiledSQLPlanVerification = field(
        repr=False
    )
    entries: tuple[ScalarMeaningEntry, ...] = field(repr=False)


TIMESTAMP_LOWER = datetime(1000, 1, 1)
TIMESTAMP_UPPER = datetime(9999, 12, 31, 23, 59, 59, 499999)
EPOCH = datetime(1970, 1, 1)


def civil_ticks(value: datetime) -> int:
    delta = value - EPOCH
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


MIN_TIMESTAMP_TICKS = civil_ticks(TIMESTAMP_LOWER)
MAX_TIMESTAMP_TICKS = civil_ticks(TIMESTAMP_UPPER)


def verify_law(law, kind):
    if kind == "Timestamp":
        valid = (
            type(law) is TimestampMeaning
            and all(
                type(v) is str for v in (law.calendar, law.resolution, law.timezone)
            )
            and all(
                type(v) is tuple and all(type(n) is int for n in v)
                for v in (law.lower, law.upper)
            )
            and law == TimestampMeaning()
        )
    elif kind == "UUID":
        valid = (
            type(law) is UUIDMeaning
            and type(law.byte_order) is str
            and type(law.byte_width) is int
            and law == UUIDMeaning()
        )
    else:
        valid = False
    if not valid:
        raise ScalarMeaningError("MEANING_LAW")


def _sources(verification):
    if type(verification) is CompiledSQLPlanVerification:
        from pietto._project.project_sql_plan_verification import (
            verify_compiled_sql_plan,
        )
        from pietto._project.project_compiled_schema import Address

        verify_compiled_sql_plan(verification.plan)
        plan = verification.plan
        records = plan.ir.completed.root.records
        result: list[tuple[Any, Any, Any, Any]] = []
        for source in plan.sources:
            source_record = records[Address(source.ref.kind, source.ref.position)]
            for port in plan.ports.values():
                if port.owner is not source.ref:
                    continue
                canonical = port.field.evidence.resolved_type
                if canonical.name not in ("Timestamp", "UUID"):
                    continue
                record = records[source_record.get("fields")[port.field.field_position]]
                if record.get("meaning") != canonical.name:
                    raise ScalarMeaningError("MEANING_FIELDS")
                result.append((port, record, canonical, port.field.fact))
        return tuple(result)
    if (
        type(verification) is not ProjectSQLPlanVerification
        or type(verification.plan) is not ProjectSQLPlan
    ):
        raise ScalarMeaningError("MEANING_ROOT")
    try:
        inspect_project_sql_plan(verification)
    except (ValueError, TypeError, AttributeError, IndexError, KeyError) as exc:
        raise ScalarMeaningError("MEANING_ROOT") from exc
    types = verification.completed.semantic_result.module_type_source_resolutions
    result = []
    for port in verification.plan.source_ports:
        evidence = port.field.evidence
        canonical = evidence.resolved_type
        if (
            canonical.kind is not ProjectResolvedTypeKind.BUILTIN
            or canonical.name not in ("Timestamp", "UUID")
        ):
            continue
        declared = None if evidence.field_def is None else evidence.field_def.type_expr
        matches = (
            tuple(r for env in types.environments for r in env.find_type_expr(declared))
            if declared is not None and types is not None
            else ()
        )
        if declared is None or len(matches) != 1:
            raise ScalarMeaningError("MEANING_FIELDS")
        resolution = matches[0]
        if (
            resolution.reference.type_expr is not declared
            or resolution.direct_kind is not ProjectResolvedTypeKind.BUILTIN
            or resolution.canonical_kind is not canonical.kind
            or resolution.canonical_name != canonical.name
            or resolution.alias_chain
            or declared.arguments
        ):
            raise ScalarMeaningError("MEANING_FIELDS")
        result.append((port, declared, canonical, resolution))
    return tuple(result)


def acquire_scalar_meaning(verification) -> ScalarMeaningBundle:
    sources = _sources(verification)
    bundle = ScalarMeaningBundle(
        verification,
        tuple(
            ScalarMeaningEntry(
                i,
                port,
                declared,
                canonical,
                resolution,
                TimestampMeaning() if canonical.name == "Timestamp" else UUIDMeaning(),
            )
            for i, (port, declared, canonical, resolution) in enumerate(sources)
        ),
    )
    verify_scalar_meaning(bundle, verification)
    return bundle


def intrinsic_scalar_meaning(verification) -> ScalarMeaningBundle | None:
    """Derive the closed builtin law without accepting caller authority."""

    try:
        bundle = acquire_scalar_meaning(verification)
    except ScalarMeaningError as exc:
        if exc.category != "MEANING_FIELDS":
            raise
        return None
    return bundle if bundle.entries else None


def verify_scalar_meaning(bundle, verification) -> None:
    if (
        type(bundle) is not ScalarMeaningBundle
        or bundle.verification is not verification
    ):
        raise ScalarMeaningError("MEANING_ROOT")
    sources = _sources(verification)
    if type(bundle.entries) is not tuple or len(bundle.entries) != len(sources):
        raise ScalarMeaningError("MEANING_FIELDS")
    for ordinal, (entry, (port, declared, canonical, resolution)) in enumerate(
        zip(bundle.entries, sources, strict=True)
    ):
        if (
            type(entry) is not ScalarMeaningEntry
            or type(entry.ordinal) is not int
            or entry.ordinal != ordinal
            or entry.source_port is not port
            or entry.declared is not declared
            or entry.canonical is not canonical
            or entry.resolution is not resolution
        ):
            raise ScalarMeaningError("MEANING_FIELDS")
        verify_law(entry.law, canonical.name)


def _source_entry(bundle, field):
    if bundle is None:
        return None
    matches = tuple(e for e in bundle.entries if e.source_port.field is field)
    if len(matches) > 1:
        raise ScalarMeaningError("MEANING_FIELDS")
    return matches[0] if matches else None


def operations_admitted(bundle) -> bool:
    """Accept only source-identified Q3 carriers through existing row operations."""
    if type(bundle) is not ScalarMeaningBundle:
        return False
    verification = bundle.verification
    if (
        type(verification) is not ProjectSQLPlanVerification
        or type(verification.plan) is not ProjectSQLPlan
    ):
        return False
    try:
        from pietto._project.project_sql_emission_scopes import reference_source_ports
        from pietto._project import project_sql_plan_expressions as expressions
        from pietto.ast_nodes import AuthoredJoinKind

        plan = verification.plan
        temporal_join_ports = any(
            port.field.evidence.resolved_type.name in {"Timestamp", "Date", "UUID"}
            for port in plan.join_ports
        )
        if temporal_join_ports and any(
            join.kind
            not in {
                AuthoredJoinKind.INNER,
                AuthoredJoinKind.LEFT,
                AuthoredJoinKind.RIGHT,
            }
            for join in plan.joins
        ):
            return False
        references = reference_source_ports(plan)
        direct = {
            expressions.ProjectSQLReference,
            expressions.ProjectSQLJoinedReference,
        }
        for expression in plan.expressions:
            kind = expression.value_type.resolved_type
            if kind.kind is not ProjectResolvedTypeKind.BUILTIN or kind.name not in {
                "Timestamp",
                "UUID",
            }:
                continue
            if type(expression) not in direct:
                return False
            source = references.get(expression.ref)
            if source is None:
                return False
            entry = _source_entry(bundle, source[1].field)
            if entry is None or entry.canonical is not kind:
                return False
        return True
    except (AttributeError, TypeError, ValueError, KeyError, ScalarMeaningError):
        return False


def _output_entry(bundle, port):
    if bundle is None:
        return None
    if type(bundle.verification) is CompiledSQLPlanVerification:
        return _compiled_output_entry(bundle, port)
    plan = bundle.verification.plan
    kind = port.field.evidence.resolved_type
    if kind.kind is not ProjectResolvedTypeKind.BUILTIN or kind.name not in (
        "Timestamp",
        "UUID",
    ):
        return None
    source_entries = {entry.source_port.ref: entry for entry in bundle.entries}
    edges: dict[Any, list[Any]] = {}

    def add(target, source):
        if target is None or source is None:
            return
        targets = edges.setdefault(target, [])
        if all(source is not item for item in targets):
            targets.append(source)

    for input_port in plan.input_ports:
        add(input_port.ref, input_port.producer_port)
    for stage_port in plan.stage_ports:
        add(stage_port.ref, stage_port.source)
    for join_port in plan.join_ports:
        add(join_port.ref, join_port.source)
    for key in plan.group_keys:
        add(key.ref, key.input)
    for projection in plan.projections:
        source = projection.source_port or projection.input_port
        if source is None:
            expression = plan.expressions[projection.expression.position]
            source = getattr(expression, "port", None)
        add(projection.ref, source)
        add(projection.export, source)
    for projection in plan.aggregate_projections:
        add(projection.ref, projection.input)
        add(projection.export, projection.input)
    from pietto._project.project_sql_emission_aggregation import function_name

    # MIN and MAX keep the exact value of their one direct argument.
    for aggregate in plan.aggregates:
        if function_name(aggregate.source) in ("min", "max") and (
            len(aggregate.arguments) == 1
        ):
            argument = plan.expressions[aggregate.arguments[0].position]
            add(aggregate.ref, getattr(argument, "port", None))
    for result_port in plan.result_ports:
        add(result_port.ref, result_port.source)
    for export in plan.result_exports:
        add(export.canonical.ref, export.port)
    pending = [port.ref]
    seen, found = set(), []
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        entry = source_entries.get(current)
        if entry is not None:
            if all(entry is not item for item in found):
                found.append(entry)
            continue
        next_values = edges.get(current)
        if not next_values:
            raise ScalarMeaningError("MEANING_OUTPUT")
        pending.extend(next_values)
    if len(found) != 1:
        raise ScalarMeaningError("MEANING_OUTPUT")
    entry = found[0]
    if entry.canonical.name != kind.name:
        raise ScalarMeaningError("MEANING_OUTPUT")
    verify_law(entry.law, kind.name)
    return entry


def _compiled_output_entry(bundle, port):
    """Resolve meaning through exact compiled value edges, preserving source identity."""
    from pietto._project.project_compiled_schema import Address

    plan = bundle.verification.plan
    records = plan.ir.completed.root.records
    if port.field.evidence.resolved_type.name not in ("Timestamp", "UUID"):
        return None
    sources = {
        Address(e.source_port.ref.kind, e.source_port.ref.position): e
        for e in bundle.entries
    }
    pending = [Address(port.ref.kind, port.ref.position)]
    seen, found = set(), []
    while pending:
        address = pending.pop()
        if address in seen:
            continue
        seen.add(address)
        if address in sources:
            entry = sources[address]
            if all(entry is not e for e in found):
                found.append(entry)
            continue
        record = records[address]
        if address.kind == "port":
            pending.append(record.get("source"))
        elif address.kind == "read":
            pending.append(record.get("port"))
        elif address.kind == "join_value":
            pending.append(record.get("input"))
        elif address.kind == "window_value":
            pending.extend(a for role, a in record.get("arguments") if role == "value")
        elif address.kind == "aggregate_value" and record.get("function") in (
            "min",
            "max",
        ):
            # MIN and MAX keep the exact value of their one direct argument.
            pending.extend(record.get("arguments")[:1])
        else:
            raise ScalarMeaningError("MEANING_OUTPUT")
    if len(found) != 1:
        raise ScalarMeaningError("MEANING_OUTPUT")
    verify_law(found[0].law, port.field.evidence.resolved_type.name)
    return found[0]
