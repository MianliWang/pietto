"""Explicit finite scalar meanings over exact verified source occurrences.

Acquisition applies an approved closed law to actual builtin source evidence.
Verification reads the retained authorities independently; no constructor history
or producer/Arrow description can supply an absent meaning. `now()` reads the
statement clock, the one meaning that comes from no source field.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_plan import ProjectSQLPlan, ProjectSQLPlanRef
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


@dataclass(frozen=True, slots=True, eq=False)
class StatementClockMeaning:
    """The statement clock that every now() of one statement reads. Its
    identity is the holding contract's authority plus this clock, so the same
    object in two contracts never means one value."""

    law: TimestampMeaning = TimestampMeaning()


STATEMENT_CLOCK = StatementClockMeaning()


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


# Plan records that only carry a port's value to a later port, list a row's
# ports or name them. Every other record reads each port it references.
_CARRIERS = frozenset(
    {
        "aggregations",
        "blocks",
        "demands",
        "join_inputs",
        "join_ports",
        "join_tails",
        "joins",
        "origins",
        "stage_ports",
        "symbols",
        "windows",
    }
)


def _read_refs(plan) -> set:
    """The ports some plan record reads, with every port that carries them."""
    carried = {port.ref: port.source for port in (*plan.stage_ports, *plan.join_ports)}
    pending = []
    for item in fields(plan):
        records = getattr(plan, item.name)
        if item.name in _CARRIERS or type(records) is not tuple:
            continue
        for record in records:
            for slot in fields(record):
                value = getattr(record, slot.name)
                values = value if type(value) is tuple else (value,)
                pending.extend(v for v in values if type(v) is ProjectSQLPlanRef)
    read = set()
    while pending:
        ref = pending.pop()
        if ref not in read:
            read.add(ref)
            if ref in carried:
                pending.append(carried[ref])
    return read


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
        # D76.02 E1: a port the relation never reads does not close a FULL or
        # CROSS JOIN.
        read = _read_refs(plan)
        temporal_join_ports = any(
            port.ref in read
            and port.field.evidence.resolved_type.name in {"Timestamp", "Date", "UUID"}
            for port in plan.join_ports
        )
        if temporal_join_ports and any(
            join.kind
            not in {
                AuthoredJoinKind.INNER,
                AuthoredJoinKind.LEFT,
                AuthoredJoinKind.RIGHT,
            }
            and not (
                join.kind is AuthoredJoinKind.CROSS
                and any(unnest.join is join.ref for unnest in plan.unnests)
            )
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


def _resolved(found, complete, kind, strict):
    """The one meaning a traced output reaches. Under a bundle (strict) anything
    else is refused; without one, only a complete trace to the clock counts."""
    found = tuple(dict.fromkeys(found))  # eq=False ends: one per identity
    if not strict:
        clock = complete and len(found) == 1 and found[0] is STATEMENT_CLOCK
        return STATEMENT_CLOCK if clock and kind == "Timestamp" else None
    if not complete or len(found) != 1:
        raise ScalarMeaningError("MEANING_OUTPUT")
    entry = found[0]
    reached = "Timestamp" if entry is STATEMENT_CLOCK else entry.canonical.name
    if reached != kind:
        raise ScalarMeaningError("MEANING_OUTPUT")
    verify_law(entry.law, kind)
    return entry


def _output_entry(checked, bundle, port):
    if type(checked) is CompiledSQLPlanVerification:
        return _compiled_output_entry(checked, bundle, port)
    from pietto._project.project_sql_plan_expressions import ProjectSQLScalarCall
    from pietto.ir.model import SymbolNamespace

    plan = checked.plan
    kind = port.field.evidence.resolved_type
    if kind.kind is not ProjectResolvedTypeKind.BUILTIN or kind.name not in (
        "Timestamp",
        "UUID",
    ):
        return None
    strict = bundle is not None
    ends: dict[Any, Any] = {STATEMENT_CLOCK: STATEMENT_CLOCK}
    if strict:
        ends.update((e.source_port.ref, e) for e in bundle.entries)
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
    for unnest in plan.unnests:
        matches = tuple(
            collect for collect in plan.collects if collect.ref is unnest.collect
        )
        definitions = tuple(
            definition
            for definition in plan.bindings.definitions
            if definition.ref is unnest.definition
        )
        # A verified plan never fails these unnest checks; without a bundle the
        # guard of _prepare_output owns the refusal, so a generic leaf stays None.
        if len(matches) != 1 or len(definitions) != 1:
            return _resolved((), False, kind.name, strict)
        children = tuple(
            port
            for child in matches[0].children
            for port in plan.all_exports
            if port.ref is child
        )
        outputs = tuple(
            port
            for output in unnest.outputs
            for port in plan.join_ports
            if port.ref is output
        )
        if (
            not unnest.outputs
            or not definitions[0].exports
            or not len(unnest.outputs)
            == len(definitions[0].exports)
            == len(matches[0].children)
            == len(children)
            == len(outputs)
            or any(
                output.field.evidence is not export.field.evidence
                or export.field.evidence is not child.field.evidence
                for output, export, child in zip(
                    outputs, definitions[0].exports, children, strict=True
                )
            )
        ):
            return _resolved((), False, kind.name, strict)
        for export, child in zip(
            definitions[0].exports, matches[0].children, strict=True
        ):
            add(export.ref, child)
    for key in plan.group_keys:
        add(key.ref, key.input)
    for projection in plan.projections:
        source = projection.source_port or projection.input_port
        if source is None:
            expression = plan.expressions[projection.expression.position]
            source = getattr(expression, "port", None)
            if (
                type(expression) is ProjectSQLScalarCall
                and expression.callee_symbol.namespace is SymbolNamespace.CALLABLE
                and expression.callee_symbol.name == "now"
                and not expression.arguments
            ):
                source = STATEMENT_CLOCK
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
        entry = ends.get(current)
        if entry is not None:
            found.append(entry)
            continue
        next_values = edges.get(current)
        if not next_values:
            return _resolved(found, False, kind.name, strict)
        pending.extend(next_values)
    return _resolved(found, True, kind.name, strict)


def _compiled_output_entry(checked, bundle, port):
    """Resolve meaning through exact compiled value edges, preserving source identity."""
    from pietto._project.project_compiled_schema import Address, NOW_OPERATOR

    records = checked.plan.ir.completed.root.records
    kind = port.field.evidence.resolved_type.name
    if kind not in ("Timestamp", "UUID"):
        return None
    strict = bundle is not None
    sources = {
        Address(e.source_port.ref.kind, e.source_port.ref.position): e
        for e in (bundle.entries if strict else ())
    }
    pending = [Address(port.ref.kind, port.ref.position)]
    seen, found = set(), []
    while pending:
        address = pending.pop()
        if address in seen:
            continue
        seen.add(address)
        if address in sources:
            found.append(sources[address])
            continue
        record = records[address]
        if address.kind == "operation" and record.get("operator") == NOW_OPERATOR:
            found.append(STATEMENT_CLOCK)
        elif address.kind == "port":
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
        elif address.kind == "field":
            from pietto._project.project_compiled_schema import (
                CompiledError,
                unnest_field_source,
            )

            try:
                source = unnest_field_source(records, record)
            except (CompiledError, KeyError, TypeError) as exc:
                if strict:
                    raise ScalarMeaningError("MEANING_OUTPUT") from exc
                source = None
            if source is None:
                return _resolved(found, False, kind, strict)
            pending.append(source)
        else:
            return _resolved(found, False, kind, strict)
    return _resolved(found, True, kind, strict)
