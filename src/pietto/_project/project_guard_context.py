"""Attempt-local guard context; data observations cannot create a PG owner."""

from dataclasses import dataclass, field
from typing import Any

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class GuardContext:
    program: Any = field(repr=False)
    route: str
    session_id: int
    role: str
    isolation: str
    environment: tuple
    sources: tuple = field(repr=False)
    owner: Any = field(repr=False)
    connection: Any = field(repr=False)
    transaction: object = field(repr=False)
    native_transaction: str = field(default="", repr=False, kw_only=True)

    @property
    def separate_allowed(self):
        return self.program.refinement is not None

    def verify_owned(self, owner):
        from pietto._project.project_execution_postgres import PostgresExecution

        if (
            type(owner) is not PostgresExecution
            or owner.guarded_request is None
            or owner.context is None
            or owner.guarded_request is not owner._owned_guarded_request
            or owner.guarded_request.program is not self.program
            or self.route != "postgres_rows"
            or self.owner is not owner
            or owner._guard_context is not self
            or owner._guard_transaction is not self.transaction
            or owner._connection is not self.connection
            or self.connection is not owner._owned_connection
            or self.connection.closed
            or owner._closed
            or owner._transaction != "OPEN"
            or int(self.connection.info.transaction_status) != 2
            or self.session_id != self.connection.info.backend_pid
            or self.session_id != owner.session_id
            or self.role != owner.request.access.user
            or owner.context[:4] != (self.role, self.isolation, "on", "UTF8")
        ):
            raise ValueError("GUARD_CONTEXT_LIFETIME")
        query = self.program.refinement
        if query is not None:
            from pietto._project.project_result_output import source_read_columns

            if (
                owner.source_admissions is None
                or owner.source_admissions is not owner._owned_admissions
            ):
                raise ValueError("GUARD_SOURCE_VECTOR")
            owner.source_admissions.verify(
                self.connection, query.sources, source_read_columns(query.output)
            )


def admit_postgres_guard_context(owner, program):
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_guard_verification import verify_program

    verify_program(program)
    if (
        type(owner) is not PostgresExecution
        or owner._connection is None
        or owner._transaction != "OPEN"
        or owner.context is None
        or type(owner.session_id) is not int
    ):
        raise ValueError("GUARD_CONTEXT_OWNER")
    connection = owner._connection
    observations = []
    for source in program.preparation.artifact.request.sources:
        owner._remaining()
        if owner._cancel.is_set():
            raise ValueError("EXECUTION_CANCELED")
        cursor = connection.cursor()
        owner._cursor = owner._owned_cursor = cursor
        owner.guard_events.append(("context_statement_open", source.position))
        primary = None
        try:
            sql = (
                "SELECT c.oid::bigint,c.relkind::text,c.relrowsecurity,"
                "pg_catalog.pg_get_userbyid(c.relowner),"
                "COALESCE('security_invoker=true'=ANY(c.reloptions),false) "
                "FROM pg_catalog.pg_class AS c JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace "
                "WHERE n.nspname=$1 AND c.relname=$2"
            )
            charge_guard(
                owner,
                len(sql.encode())
                + len(source.namespace.encode())
                + len(source.name.encode()),
            )
            cursor.execute(sql, (source.namespace, source.name))
            rows = cursor.fetchall()
            if len(rows) != 1 or len(rows[0]) != 5 or type(rows[0][0]) is not int:
                raise ValueError("GUARD_SOURCE_CONTEXT")
            descriptor = tuple(rows[0])
            charge_guard(
                owner, sum(len(str(v).encode("utf-8")) + 8 for v in descriptor)
            )
            names = program.source_reads[source.position]
            sql = guard_source_schema_sql(source, names, family="postgres")
            metadata = ()
            if sql is not None:
                owner._remaining()
                if owner._cancel.is_set():
                    raise ValueError("EXECUTION_CANCELED")
                charge_guard(owner, len(sql.encode("utf-8")))
                cursor.execute(sql)
                metadata = tuple(cursor.description)
                if cursor.fetchall():
                    raise ValueError("GUARD_SOURCE_SCHEMA_ROWS")
            sql = "SELECT a.attname,c.collname FROM pg_catalog.pg_attribute AS a JOIN pg_catalog.pg_collation AS c ON c.oid=a.attcollation WHERE a.attrelid=$1::oid AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum"
            charge_guard(owner, len(sql.encode()) + 8)
            owner._remaining()
            if owner._cancel.is_set():
                raise ValueError("EXECUTION_CANCELED")
            cursor.execute(sql, (descriptor[0],))
            collations = tuple(cursor.fetchall())
            charge_guard(
                owner,
                sum(
                    len(str(v).encode("utf-8")) + 8
                    for meta in metadata
                    for v in (meta.name, meta.type_code, meta.null_ok)
                )
                + sum(
                    len(str(v).encode("utf-8")) + 8 for row in collations for v in row
                ),
            )
            verify_guard_source_columns(
                source, names, metadata, collations, route="postgres_rows"
            )
            observations.append((source, descriptor))
            owner._remaining()
            if owner._cancel.is_set():
                raise ValueError("EXECUTION_CANCELED")
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                cursor.close()
            except BaseException as error:
                from pietto._project.project_execution_postgres import failure

                owner._cleanup_errors.append(failure(error, "guard_context_close"))
                if primary is None:
                    raise
            else:
                owner._cursor = owner._owned_cursor = None
                owner.guard_events.append(("context_statement_closed", source.position))
    native = _postgres_context(owner)
    owner._guard_transaction = object()
    context = GuardContext(
        program,
        "postgres_rows",
        owner.session_id,
        owner.context[0],
        owner.context[1],
        (owner.request.artifact.request.release, "UTF8", "pg_catalog"),
        tuple(observations),
        owner,
        connection,
        owner._guard_transaction,
        native_transaction=native[2],
    )
    owner._guard_context = context
    context.verify_owned(owner)
    return context


@dataclass(frozen=True, slots=True, eq=False)
class ObservedGuardContext:
    """Test-transport observation lifetime; never a PG execution capability."""

    program: Any = field(repr=False)
    route: str
    session_id: int
    role: str
    environment: tuple
    sources: tuple = field(repr=False)
    admissions: Any = field(repr=False)
    owner: Any = field(repr=False)
    transaction: object = field(repr=False)

    @property
    def separate_allowed(self):
        return self.program.refinement is not None

    def verify_owned(self, owner):
        from pietto._project.project_result_output import source_read_columns

        if (
            type(owner) is not ObservedGuardOwner
            or owner.context is not self
            or owner.closed
            or owner.transaction is not self.transaction
            or owner.request.program is not self.program
        ):
            raise ValueError("GUARD_OBSERVED_LIFETIME")
        family = self.program.preparation.artifact.request.family
        if self.route not in (
            "postgres_rows",
            "mysql_rows",
            "postgres_adbc",
        ) or family != ("mysql" if self.route == "mysql_rows" else "postgres"):
            raise ValueError("GUARD_OBSERVED_ROUTE")
        if (
            type(self.session_id) is not int
            or self.session_id <= 0
            or not self.role
            or self.environment[:4]
            != (
                self.program.preparation.artifact.request.release,
                owner.request.isolation,
                True,
                "utf8mb4" if family == "mysql" else "UTF8",
            )
        ):
            raise ValueError("GUARD_OBSERVED_ENVIRONMENT")
        expected = self.program.preparation.artifact.request.sources
        if (
            type(self.sources) is not tuple
            or len(self.sources) != len(expected)
            or any(
                type(item) is not tuple
                or len(item) != 2
                or item[0] is not source
                or not item[1]
                for item, source in zip(self.sources, expected, strict=True)
            )
        ):
            raise ValueError("GUARD_OBSERVED_SOURCES")
        if self.program.refinement is not None:
            q = self.program.refinement
            from pietto._project.project_execution_source import SourceAdmissions

            if (
                type(self.admissions) is not SourceAdmissions
                or self.admissions.route != self.route
                or self.admissions.session_id != self.session_id
                or self.admissions.role != self.role
                or self.admissions.environment != self.environment
            ):
                raise ValueError("GUARD_OBSERVED_SOURCE_VECTOR")
            self.admissions.verify(None, q.sources, source_read_columns(q.output))


class ObservedGuardOwner:
    """Closed consumer of explicit test observations, with no native submit API."""

    def __init__(
        self, request, *, route, session_id, role, environment, sources, admissions=None
    ):
        import threading
        import time
        from pietto._project.project_guard_runtime import ObservedGuardRequest, GuardRun

        if type(request) is not ObservedGuardRequest:
            raise ValueError("GUARD_OBSERVED_REQUEST")
        self.request = request
        self.transaction = object()
        self.closed = False
        self._cancel = threading.Event()
        self._guard_bytes = 0
        self.deadline = time.monotonic() + request.limits.seconds
        self.context = ObservedGuardContext(
            request.program,
            route,
            session_id,
            role,
            environment,
            sources,
            admissions,
            self,
            self.transaction,
        )
        self._context_state = (
            self.context,
            route,
            session_id,
            role,
            environment,
            sources,
            admissions,
            self.transaction,
        )
        self.guards = GuardRun(request, self.context)

    def _remaining(self):
        import time

        c = self.context
        if self.closed or self._context_state != (
            c,
            c.route,
            c.session_id,
            c.role,
            c.environment,
            c.sources,
            c.admissions,
            self.transaction,
        ):
            raise ValueError("GUARD_OBSERVED_LIFETIME")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("EXECUTION_DEADLINE")
        return remaining

    def close(self):
        self.guards.close()
        self.closed = True


def verify_guard_source_columns(source, names, metadata, collations, *, route):
    """Check each original read through the existing native field checker."""
    from pietto._project.project_execution_reader import check_native_column
    from pietto._project.project_sql_emission_rows import field_realization

    if len(names) != len(metadata):
        raise ValueError("GUARD_SOURCE_METADATA")
    for i, (name, meta) in enumerate(zip(names, metadata, strict=True)):
        fields = tuple(f for f in source.fields if f.column == name)
        if not fields:
            raise ValueError("GUARD_SOURCE_FIELD")
        for source_field in fields:
            real = field_realization(source_field)
            if real is None:
                raise ValueError("GUARD_SOURCE_REALIZATION")
            check_native_column(
                real,
                route,
                meta,
                label="__pietto_source_" + str(i),
                ordinal=i,
                source_field=source_field,
            )
            if (
                real.tag == "Text"
                and route != "mysql_rows"
                and tuple(c for c in collations if c[0] == name)
                != ((name, real.domain["collation"]),)
            ):
                raise ValueError("GUARD_SOURCE_COLLATION")


def guard_source_schema_sql(source, names, *, family):
    from pietto._project.project_execution_source import identifier

    selected = ",".join(
        identifier(name, family=family)
        + " AS "
        + identifier("__pietto_source_" + str(i), family=family)
        for i, name in enumerate(names)
    )
    if not selected:
        return None
    return (
        "SELECT "
        + selected
        + " FROM "
        + identifier(source.namespace, family=family)
        + "."
        + identifier(source.name, family=family)
        + " LIMIT 0"
    )


def _postgres_context(owner):
    """Fresh server context and transaction identity, not an equal snapshot label."""
    from pietto._project.project_execution_postgres import failure

    owner._remaining()
    if owner._cancel.is_set():
        raise ValueError("EXECUTION_CANCELED")
    cursor = owner._connection.cursor()
    owner._guard_control = cursor
    owner.guard_events.append(("live_context_open", owner.session_id))
    primary = None
    try:
        sql = "SELECT current_user,pg_catalog.pg_backend_pid(),pg_catalog.pg_current_xact_id()::text,current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_setting('search_path')"
        charge_guard(owner, len(sql.encode()))
        cursor.execute(sql)
        rows = cursor.fetchall()
        if len(rows) != 1 or len(rows[0]) != 7:
            raise ValueError("GUARD_LIVE_CONTEXT")
        row = rows[0]
        charge_guard(owner, sum(len(str(v).encode("utf-8")) + 8 for v in row))
        if (
            row[0] != owner.request.access.user
            or row[1] != owner.session_id
            or type(row[2]) is not str
            or not row[2].isascii()
            or not row[2].isdigit()
            or row[3:]
            != (
                "repeatable read"
                if owner.request.isolation == "stable"
                else "serializable",
                "on",
                "UTF8",
                "pg_catalog",
            )
        ):
            raise ValueError("GUARD_LIVE_CONTEXT")
        owner._remaining()
        if owner._cancel.is_set():
            raise ValueError("EXECUTION_CANCELED")
        return row
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            cursor.close()
        except BaseException as error:
            owner._cleanup_errors.append(failure(error, "guard_live_context_close"))
            if primary is None:
                raise
        else:
            owner._guard_control = None
            owner.guard_events.append(("live_context_closed", owner.session_id))


def refresh_postgres_guard_context(owner):
    context = owner._guard_context
    if type(context) is not GuardContext:
        raise ValueError("GUARD_CONTEXT_OWNER")
    context.verify_owned(owner)
    native = _postgres_context(owner)
    if native[2] != context.native_transaction:
        raise ValueError("GUARD_TRANSACTION_CHANGED")


def charge_guard(owner, amount):
    if type(amount) is not int or amount < 0:
        raise ValueError("GUARD_RESOURCE_ACCOUNTING")
    charged = owner._guard_bytes + amount
    if charged > owner.request.limits.max_bytes:
        raise ValueError("GUARD_RESOURCE_LIMIT")
    owner._guard_bytes = charged
