"""Actual ADBC context and retained-source/guard binding after qualification."""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_execution import ExecutionError
from pietto._project.project_execution_postgres_adbc_native import (
    CONTEXT_SQL,
    read_control,
)
from pietto._project.project_execution_source import (
    SourceAdmissions,
    ObservedSource,
    identifier,
    requirement_state,
    _observation_state,
    verify_requirement,
    verify_source_observations,
)
from pietto._project.project_guard_context import (
    guard_source_schema_sql,
    verify_guard_source_columns,
)
from pietto._project.project_result_output import source_read_columns

__all__: tuple[str, ...] = ()


def native_context(owner):
    _, rows, reply = read_control(owner, CONTEXT_SQL, maximum=1)
    a = owner.request.access
    isolation = (
        "repeatable read" if owner.request.isolation == "stable" else "serializable"
    )
    version = owner.request.artifact.request.release
    major, minor = map(int, version.split("."))
    if (
        len(rows) != 1
        or len(rows[0]) != 17
        or rows[0][0] != major * 10000 + minor
        or rows[0][1:4] != (a.database, a.user, a.user)
        or any(type(v) is not int or v <= 0 for v in rows[0][4:7])
        or type(rows[0][7]) is not str
        or not rows[0][7].isascii()
        or not rows[0][7].isdigit()
        or rows[0][8:14] != (isolation, "on", "UTF8", "pg_catalog", "UTC", "on")
        or type(rows[0][14]) is not str
        or type(rows[0][15]) is not int
        or not rows[0][16]
    ):
        raise ExecutionError("POSTGRES_ADBC_NATIVE_CONTEXT")
    return rows[0], reply


@dataclass(frozen=True, slots=True, eq=False)
class ADBCSourceAdmission:
    owner: Any = field(repr=False)
    connection: Any = field(repr=False)
    requirement: Any = field(repr=False)
    session_id: int
    state: tuple = field(repr=False)

    def verify(self, connection, requirement):
        if (
            self.connection is not connection
            or self.requirement is not requirement
            or self.state != requirement_state(requirement)
            or self.owner._connection is not connection
            or self.owner.session_id != self.session_id
        ):
            raise ExecutionError("SOURCE_ADMISSION_IDENTITY")
        self.owner._qualification.verify(self.owner)


def admit_sources(owner, requirements):
    owner._qualification.verify(owner)
    all_reads = source_read_columns(owner.request.output)
    read_columns = tuple(all_reads[r.source.position] for r in requirements)
    observations = []
    admissions = []
    for req, names in zip(requirements, read_columns, strict=True):
        verify_requirement(req, owner.request.artifact.request.sources)
        if req.role != owner.context[2]:
            raise ExecutionError("SOURCE_ROLE")
        source = req.source
        relation = identifier(source.namespace) + "." + identifier(source.name)
        registry = (
            identifier(req.registry_namespace) + "." + identifier(req.registry_name)
        )
        _, registry_rows, _ = read_control(
            owner,
            "SELECT provider,version_tag,active,revision FROM " + registry + " LIMIT 2",
            maximum=2,
        )
        _, definition, _ = read_control(
            owner,
            "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
            (relation,),
            ("Text",),
            maximum=1,
        )
        if len(definition) != 1 or len(definition[0]) != 1:
            raise ExecutionError("SOURCE_DOMAIN")
        columns = ",".join(identifier(n) for n in req.token_columns)
        token_meta, _, _ = read_control(
            owner, "SELECT " + columns + " FROM " + relation + " LIMIT 0", maximum=0
        )
        nulls = " OR ".join(identifier(n) + " IS NULL" for n in req.token_columns)
        _, collision, _ = read_control(
            owner,
            "SELECT "
            + columns
            + " FROM "
            + relation
            + " GROUP BY "
            + columns
            + " HAVING "
            + nulls
            + " OR COUNT(*)<>1 LIMIT 1",
            maximum=1,
        )
        metadata, collations = source_schema(owner, source, names)
        observations.append(
            ObservedSource(
                req,
                "postgres_adbc",
                owner.session_id,
                owner.context[2],
                registry_rows,
                definition[0][0],
                tuple(m["type"] for m in token_meta),
                collision,
                metadata,
                collations,
                ("NORMAL",) * 4 + (("NORMAL" if names else "NOT_REQUIRED"), "NORMAL"),
            )
        )
        state = requirement_state(req)
        if state is None:
            raise ExecutionError("SOURCE_REQUIREMENT")
        admissions.append(
            ADBCSourceAdmission(owner, owner._connection, req, owner.session_id, state)
        )
    observations = tuple(observations)
    verify_source_observations(
        requirements,
        read_columns,
        observations,
        route="postgres_adbc",
        session_id=owner.session_id,
        role=owner.context[2],
    )
    return SourceAdmissions(
        requirements,
        read_columns,
        observations,
        "postgres_adbc",
        owner.session_id,
        owner.context[2],
        owner.environment,
        owner._connection,
        tuple(admissions),
        (tuple(requirement_state(r) for r in requirements), owner.environment),
        tuple(_observation_state(v) for v in observations),
    )


def source_schema(owner, source, names):
    owner._qualification.verify(owner)
    sql = guard_source_schema_sql(source, names, family="postgres")
    metadata = ()
    if sql is not None:
        metadata, rows, _ = read_control(owner, sql, maximum=0)
        if rows:
            raise ExecutionError("SOURCE_SCHEMA_ROWS")
    relation = identifier(source.namespace) + "." + identifier(source.name)
    _, collations, _ = read_control(
        owner,
        "SELECT a.attname::text,c.collname::text FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_collation c ON c.oid=a.attcollation WHERE a.attrelid=$1::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
        (relation,),
        ("Text",),
    )
    verify_guard_source_columns(
        source, names, metadata, collations, route="postgres_adbc"
    )
    return metadata, collations


@dataclass(frozen=True, slots=True, eq=False)
class ADBCGuardContext:
    program: Any = field(repr=False)
    owner: Any = field(repr=False)
    connection: Any = field(repr=False)
    transaction: Any = field(repr=False)
    native_transaction: str
    session_id: int
    role: str
    environment: tuple
    sources: tuple = field(repr=False)
    route: str = "postgres_adbc"

    @property
    def separate_allowed(self):
        return self.program.refinement is not None

    def verify_owned(self, owner):
        from pietto._project.project_execution_postgres_adbc import (
            PostgresADBCExecution,
        )

        if (
            type(owner) is not PostgresADBCExecution
            or self.owner is not owner
            or owner._closed
            or self.connection is not owner._owned_connection
            or owner._connection is not self.connection
            or self is not owner._guard_context
            or self.transaction is not owner._guard_transaction
            or owner._transaction != "OPEN"
            or owner.guarded_request is None
            or self.program is not owner.guarded_request.program
            or self.native_transaction != owner.context[7]
            or self.session_id != owner.session_id
            or self.role != owner.context[2]
            or self.environment != owner.environment
            or self.route != "postgres_adbc"
            or self.sources is not owner._guard_sources
        ):
            raise ExecutionError("GUARD_CONTEXT_LIFETIME")
        owner._qualification.verify(owner)
        if self.program.refinement is not None:
            owner.source_admissions.verify(
                self.connection,
                self.program.refinement.sources,
                source_read_columns(self.program.refinement.output),
            )


def guard_context(owner):
    program = owner.guarded_request.program
    observations = []
    for source in program.preparation.artifact.request.sources:
        source_schema(owner, source, program.source_reads[source.position])
        observations.append((source, owner._qualification))
    owner._guard_sources = tuple(observations)
    owner._guard_transaction = object()
    result = ADBCGuardContext(
        program,
        owner,
        owner._connection,
        owner._guard_transaction,
        owner.context[7],
        owner.session_id,
        owner.context[2],
        owner.environment,
        owner._guard_sources,
    )
    owner._guard_context = result
    return result
