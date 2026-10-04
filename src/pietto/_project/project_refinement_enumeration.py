"""Bounded native pages over a complete refined query, with owned live progress.

A syntax-checked cursor is not checkpoint authority. Every enumerator starts at
zero, owns its pending page, and advances only after a checked normal terminal.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
import re
import math
import threading
import time
from typing import Any
from uuid import UUID

from pietto._project.project_execution import (
    ExecutionLimits,
    ExecutionRequest,
    prepare_execution,
    verify_execution_request,
    verify_execution_limits,
)
from pietto._project.project_execution_source import SourceAdmissions, requirement_state
from pietto._project.project_execution_reader import (
    check_native_column,
    decode_native_rows,
)
from pietto._project.project_refinement import RefinedQuery
from pietto._project.project_refinement_order import before, check_coordinates, compare
from pietto._project.project_refinement_rendering import Expr, render
from pietto._project.project_refinement_verification import (
    verify_refinement,
    verify_native,
)
from pietto._project.project_result_output import source_read_columns
from pietto._project.project_sql_emission_rows import Realization

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class RefinedExecutionRequest:
    execution: ExecutionRequest = field(repr=False)
    refinement: RefinedQuery = field(repr=False)


def prepare_refined_execution(
    refinement,
    access,
    *,
    limits=ExecutionLimits(),
    isolation="stable",
    mysql_deployment=None,
    route="",
    postgres_adbc_deployment=None,
):
    verify_refinement(refinement)
    execution = prepare_execution(
        refinement.original,
        access,
        limits=limits,
        isolation=isolation,
        binding=refinement.output.binding,
        output=refinement.output,
        mysql_deployment=mysql_deployment,
        route=route,
        postgres_adbc_deployment=postgres_adbc_deployment,
    )
    request = RefinedExecutionRequest(execution, refinement)
    verify_refined_execution(request)
    return request


def verify_refined_execution(request, *, _guarded=None):
    if type(request) is not RefinedExecutionRequest:
        raise ValueError("REFINEMENT_EXECUTION_ROOT")
    if _guarded is None:
        verify_execution_request(request.execution)
    else:
        from pietto._project.project_guard_runtime import verify_guarded_execution

        verify_guarded_execution(_guarded)
        if (
            _guarded.execution is not request.execution
            or _guarded.program.refinement is not request.refinement
        ):
            raise ValueError("GUARD_REFINEMENT_EXECUTION_ROOT")
    verify_refinement(request.refinement)
    e, q = request.execution, request.refinement
    if (
        e.artifact is not q.original
        or e.output is not q.output
        or e.binding is not q.output.binding
        or e.source_requirement is not None
    ):
        raise ValueError("REFINEMENT_EXECUTION_CORRESPONDENCE")


def atom(value):
    if type(value) is float:
        return ("float", value.hex())
    if type(value) is Decimal:
        return ("decimal", value.as_tuple())
    if type(value) is datetime:
        return ("datetime", value.isoformat(), value.fold)
    if type(value) is UUID:
        return ("uuid", value.bytes)
    if type(value) in (int, bool, str, bytes, type(None)):
        return (type(value).__name__, value)
    raise ValueError("REFINEMENT_CARRIER")


def refinement_state(query):
    from pietto._project.project_execution_binding_verification import binding_state

    return (
        query.original,
        query.output,
        query.policy,
        query.policy.choice,
        query.statement,
        query.prefix,
        query.original.request.accepted_bytes,
        query.original.request.normalized_bytes,
        query.original.rendered.sql,
        tuple(
            atom(s.site.position.literal.value)
            for s in query.original.request.plan.literal_slots
        ),
        None if query.output.binding is None else binding_state(query.output.binding),
        query.sources,
        tuple(requirement_state(r) for r in query.sources),
    )


def limits_state(limits):
    return (
        limits.batch_rows,
        limits.batch_bytes,
        limits.max_rows,
        limits.max_bytes,
        limits.seconds,
    )


def _size(value, limit):
    if value is None:
        return 1
    if type(value) in (bool, int, float):
        return 8
    if type(value) is str:
        if len(value) > limit:
            raise ValueError("REFINEMENT_RESOURCE_LIMIT")
        return len(value.encode("utf-8"))
    if type(value) is bytes:
        return len(value)
    if type(value) is Decimal:
        return len(value.as_tuple().digits) + 32
    if type(value) in (datetime, UUID):
        return 16
    raise ValueError("REFINEMENT_CARRIER")


@dataclass(frozen=True, slots=True, eq=False)
class PageRequest:
    owner: Any = field(repr=False)
    ordinal: int
    frontier: tuple | None = field(repr=False)
    size: int
    native: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CheckedPage:
    request: PageRequest = field(repr=False)
    producer: Any = field(repr=False)
    rows: tuple = field(repr=False)
    coordinates: tuple = field(repr=False)
    raw_bytes: int
    complete: bool


class Enumeration:
    def __init__(self, query, admissions, *, limits=ExecutionLimits(), _guards=None):
        verify_refinement(query)
        verify_execution_limits(limits)
        if type(admissions) is not SourceAdmissions:
            raise ValueError("REFINEMENT_SOURCE_ADMISSION")
        reads = source_read_columns(query.output)
        admissions.verify(admissions._connection, query.sources, reads)
        family = "mysql" if admissions.route == "mysql_rows" else "postgres"
        if family != query.original.request.family:
            raise ValueError("REFINEMENT_TARGET")
        environment = admissions.environment
        if (
            type(environment) is not tuple
            or len(environment) != (6 if family == "mysql" else 4)
            or environment[0] != query.original.request.release
            or environment[1] not in ("repeatable read", "serializable")
            or environment[2] is not True
            or environment[3] != ("utf8mb4" if family == "mysql" else "UTF8")
        ):
            raise ValueError("REFINEMENT_ENVIRONMENT")
        if family == "mysql" and (
            type(environment[4]) is not int
            or environment[4] < 0
            or type(environment[5]) is not str
            or not environment[5]
        ):
            raise ValueError("REFINEMENT_NATIVE_SELECTION_CAPACITY")
        if _guards is None and any(
            x.downstream_enforcement_required
            for x in query.original.request.plan.single_matches
        ):
            raise ValueError("UNFULFILLED_RUNTIME_OBLIGATION")
        self.guards = self._owned_guards = _guards
        if _guards is not None:
            from pietto._project.project_guard_runtime import GuardRun

            if type(_guards) is not GuardRun:
                raise ValueError("GUARD_REFINEMENT_OWNER")
            _guards.require_fulfilled(_guards.context.owner, refinement=query)
        self.query, self.admissions, self.limits = query, admissions, limits
        self._roots = (query, admissions, limits)
        self._captured = (refinement_state(query), limits_state(limits))
        self._reads = reads
        self._pending = self._checked = None
        self._pending_state = self._checked_state = None
        # The last committed checked page, kept for S12 capture lineage only.
        self.last_committed = None
        self._frontier = None
        self._rows = self._bytes = self._pages = 0
        self._complete = self._failed = False
        self._progress_state = self._progress_snapshot()

    @property
    def progress(self):
        return (self._rows, self._pages, self._complete, self._failed)

    def _progress_snapshot(self):
        frontier = (
            None if self._frontier is None else tuple(atom(v) for v in self._frontier)
        )
        return (
            frontier,
            atom(self._rows),
            atom(self._bytes),
            atom(self._pages),
            atom(self._complete),
            atom(self._failed),
        )

    def verify(self):
        if self.guards is not self._owned_guards:
            raise ValueError("GUARD_REFINEMENT_OWNER")
        if self.guards is not None:
            self.guards.require_fulfilled(
                self.guards.context.owner, refinement=self.query
            )
        if self._progress_snapshot() != self._progress_state:
            raise ValueError("REFINEMENT_PROGRESS_CHANGED")
        if self._roots != (
            self.query,
            self.admissions,
            self.limits,
        ) or self._captured != (
            refinement_state(self.query),
            limits_state(self.limits),
        ):
            raise ValueError("REFINEMENT_ATTEMPT_CHANGED")
        verify_refinement(self.query)
        verify_execution_limits(self.limits)
        self.admissions.verify(
            self.admissions._connection, self.query.sources, self._reads
        )
        if self._failed:
            raise ValueError("REFINEMENT_ATTEMPT_FAILED")

    def request_page(self):
        self.verify()
        if self._pending is not None or self._complete:
            raise ValueError("REFINEMENT_PAGE_LIFETIME")
        unit = self.query.units[-1]
        offset = len(unit.order_coordinates)
        coordinates = unit.order_coordinates + tuple(
            replace(c, active=tuple((i + offset, v) for i, v in c.active))
            for c in unit.coordinates
        )
        controls = (
            ()
            if self._frontier is None
            else check_coordinates(self._frontier, coordinates)
        )
        predicate = None
        if self._frontier is not None:
            parameters = []
            for index, c in enumerate(coordinates):
                domain = dict(c.domain)
                parameters.append(
                    Expr(
                        "page",
                        (index, c.tag, domain.get("precision"), domain.get("scale")),
                    )
                )
            order = self.query.statement.query.orders
            predicate = before(
                tuple(parameters),
                tuple(o.value for o in order),
                tuple(o.direction for o in order),
                self.query.original.request.family,
            )
        controls += (self.limits.batch_rows,)
        terminal = replace(
            self.query.statement.query,
            where=predicate,
            limit=Expr("page_limit", (len(controls) - 1, "Int", None, None)),
        )
        statement = replace(self.query.statement, query=terminal)
        native = render(statement, self.query.original, controls)
        if (
            len(native.sql)
            + sum(_size(v, self.limits.max_bytes) for v in native.arguments)
            > self.limits.max_bytes
        ):
            raise ValueError("REFINEMENT_RESOURCE_LIMIT")
        verify_native(
            native, self.query, frontier=self._frontier, size=self.limits.batch_rows
        )
        page = PageRequest(
            self, self._pages, self._frontier, self.limits.batch_rows, native
        )
        self._pending = page
        self._pending_state = self._page_state(page)
        return page

    @staticmethod
    def _page_state(page):
        return (
            page.owner,
            page.ordinal,
            None if page.frontier is None else tuple(atom(v) for v in page.frontier),
            page.size,
            page.native,
            page.native.statement,
            page.native.sql,
            tuple(atom(v) for v in page.native.arguments),
            tuple(
                (u, u.domain, u.owner, u.index, atom(u.value), u.original)
                for u in page.native.uses
            ),
        )

    def _verify_page(self, page):
        self.verify()
        if (
            type(page) is not PageRequest
            or type(page.ordinal) is not int
            or page.ordinal != self._pages
            or type(page.size) is not int
            or page.size != self.limits.batch_rows
            or page is not self._pending
            or page.owner is not self
            or self._page_state(page) != self._pending_state
        ):
            raise ValueError("REFINEMENT_PAGE_IDENTITY")
        verify_native(
            page.native,
            self.query,
            frontier=self._frontier,
            size=self.limits.batch_rows,
        )

    def check_page(self, page, metadata, rows, *, terminal):
        try:
            self._verify_page(page)
            if (
                self._checked is not None
                or terminal != "NORMAL"
                or type(rows) is not tuple
                or len(rows) > page.size
            ):
                raise ValueError("REFINEMENT_PAGE_TERMINAL")
            unit = self.query.units[-1]
            public_count = len(self.query.erasure)
            coordinates = unit.order_coordinates + tuple(
                replace(
                    c,
                    active=tuple(
                        (i + len(unit.order_coordinates), v) for i, v in c.active
                    ),
                )
                for c in unit.coordinates
            )
            names = unit.order_names + unit.key_names
            count = public_count + len(names)
            if type(metadata) is not tuple or len(metadata) != count:
                raise ValueError("REFINEMENT_METADATA")
            route = self.admissions.route
            for i, (coordinate, name, meta) in enumerate(
                zip(coordinates, names, metadata[public_count:], strict=True),
                start=public_count,
            ):
                storage = dict(coordinate.storage)
                if storage["kind"] == "signed64":
                    storage = {
                        "kind": "my_signed_int" if route == "mysql_rows" else "pg_int8"
                    }
                realization = Realization(
                    coordinate.tag,
                    storage,
                    coordinate.nullable,
                    dict(coordinate.domain),
                )
                check_native_column(
                    realization, route, meta, label=name, ordinal=i, source_field=None
                )
            charged = 0
            public_rows, keys = [], []
            previous = self._frontier
            directions = unit.directions + ("asc",) * len(unit.key_names)
            page_keys = set()
            for row in rows:
                if type(row) is not tuple or len(row) != count:
                    raise ValueError("REFINEMENT_ROW_ARITY")
                charged += sum(
                    _size(value, self.limits.batch_bytes) + 8 for value in row
                )
                if (
                    charged > self.limits.batch_bytes
                    or self._bytes + charged > self.limits.max_bytes
                ):
                    raise ValueError("REFINEMENT_RESOURCE_LIMIT")
                internal = []
                for raw, coordinate in zip(
                    row[public_count:], coordinates, strict=True
                ):
                    if raw is not None:
                        if coordinate.tag == "Bool":
                            if route == "mysql_rows":
                                if type(raw) is not int or raw not in (0, 1):
                                    raise ValueError("REFINEMENT_CARRIER")
                                raw = bool(raw)
                            elif type(raw) is not bool:
                                raise ValueError("REFINEMENT_CARRIER")
                        elif coordinate.tag == "Decimal" and route == "postgres_adbc":
                            if (
                                type(raw) is not str
                                or len(raw) > 256
                                or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", raw)
                                is None
                            ):
                                raise ValueError("REFINEMENT_CARRIER")
                            raw = Decimal(raw)
                        elif (
                            coordinate.tag == "Text"
                            and route == "mysql_rows"
                            and type(raw) is bytes
                        ):
                            raw = raw.decode("utf-8")
                    internal.append(raw)
                key = check_coordinates(tuple(internal), coordinates)
                occurrence = tuple(atom(v) for v in key[len(unit.order_coordinates) :])
                if (
                    occurrence in page_keys
                    or previous is not None
                    and compare(
                        previous,
                        key,
                        coordinates,
                        directions,
                        self.query.original.request.family,
                    )
                    >= 0
                ):
                    raise ValueError("REFINEMENT_PAGE_ORDER_OR_OVERLAP")
                # This set is bounded by one requested page. Global uniqueness
                # follows from the verified transfer, not a growing identity map.
                page_keys.add(occurrence)
                previous = key
                keys.append(key)
                public_rows.append(
                    tuple(row[position] for position, _ in self.query.erasure)
                )
            if self._rows + len(rows) > self.limits.max_rows:
                raise ValueError("REFINEMENT_RESOURCE_LIMIT")
            public_metadata = tuple(
                metadata[position] for position, _ in self.query.erasure
            )
            producer, decoded = decode_native_rows(
                self.query.output, route, public_metadata, tuple(public_rows)
            )
            checked = CheckedPage(
                page, producer, decoded, tuple(keys), charged, len(rows) < page.size
            )
            self._checked = checked
            self._checked_state = self._result_state(checked)
            return checked
        except BaseException:
            self.fail()
            raise

    @staticmethod
    def _result_state(checked):
        if type(checked.raw_bytes) is not int or type(checked.complete) is not bool:
            raise ValueError("REFINEMENT_CHECKED_PAGE_STATE")
        return (
            checked.request,
            checked.producer,
            tuple(tuple(atom(v) for v in row) for row in checked.rows),
            tuple(tuple(atom(v) for v in row) for row in checked.coordinates),
            checked.raw_bytes,
            checked.complete,
        )

    def commit_page(self, checked, *, cancel_event=None, deadline=None):
        try:
            self._verify_page(checked.request)
            if (
                checked is not self._checked
                or self._result_state(checked) != self._checked_state
            ):
                raise ValueError("REFINEMENT_CHECKED_PAGE_IDENTITY")
            # The closed PG control seam checks after all expensive proof and
            # scalar work. It accepts no callback or SQL/connection authority.
            if cancel_event is not None:
                if type(cancel_event) is not threading.Event:
                    raise ValueError("REFINEMENT_CONTROL")
                if cancel_event.is_set():
                    raise ValueError("EXECUTION_CANCELED")
            if deadline is not None:
                if type(deadline) not in (int, float) or not math.isfinite(deadline):
                    raise ValueError("REFINEMENT_CONTROL")
                if time.monotonic() >= deadline:
                    raise TimeoutError("EXECUTION_DEADLINE")
            self._rows += len(checked.rows)
            self._bytes += checked.raw_bytes
            self._pages += 1
            if checked.coordinates:
                self._frontier = checked.coordinates[-1]
            self._complete = checked.complete
            self.last_committed = checked
            self._pending = self._checked = None
            self._pending_state = self._checked_state = None
            self._progress_state = self._progress_snapshot()
        except BaseException:
            self.fail()
            raise

    def fail(self):
        self._failed = True
        self._progress_state = self._progress_snapshot()
