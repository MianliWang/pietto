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


def _output_entry(bundle, port):
    if bundle is None:
        return None
    if type(bundle.verification) is CompiledSQLPlanVerification:
        return _compiled_output_entry(bundle, port)
    plan = bundle.verification.plan
    origins = {p.ref: p for p in plan.source_ports}
    for projection in plan.projections:
        if projection.source_port in origins:
            origins[projection.export] = origins[projection.source_port]
    source = origins.get(port.ref)
    entry = None if source is None else _source_entry(bundle, source.field)
    kind = port.field.evidence.resolved_type
    if (
        kind.kind is ProjectResolvedTypeKind.BUILTIN
        and kind.name in ("Timestamp", "UUID")
        and entry is None
    ):
        raise ScalarMeaningError("MEANING_OUTPUT")
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
        elif address.kind == "window_value":
            pending.extend(a for role, a in record.get("arguments") if role == "value")
        else:
            raise ScalarMeaningError("MEANING_OUTPUT")
    if len(found) != 1:
        raise ScalarMeaningError("MEANING_OUTPUT")
    verify_law(found[0].law, port.field.evidence.resolved_type.name)
    return found[0]
