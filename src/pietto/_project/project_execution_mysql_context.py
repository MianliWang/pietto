"""Current MySQL query-role metadata and native transaction-epoch admission."""

from dataclasses import astuple, dataclass, field
from typing import Any, cast

from pietto._project.project_execution import (
    ExecutionError,
    MySQLAccess,
    MySQLDeploymentPremise,
    request_state,
    verify_deployment,
)
from pietto._project.project_execution_mysql_native import read_control
from pietto._project.project_execution_source import (
    ObservedSource,
    SourceAdmissions,
    _observation_state,
    identifier,
    requirement_state,
    verify_requirement,
    verify_source_observations,
)
from pietto._project.project_result_output import source_read_columns

__all__: tuple[str, ...] = ()

EPOCH_SQL = (
    "SELECT t.THREAD_ID,e.EVENT_ID,e.STATE,e.ACCESS_MODE,e.ISOLATION_LEVEL,e.AUTOCOMMIT,@@server_uuid,CURRENT_USER(),CURRENT_ROLE(),DATABASE() "
    "FROM performance_schema.threads t JOIN performance_schema.events_transactions_current e USING(THREAD_ID) "
    "WHERE t.PROCESSLIST_ID=%s AND t.PROCESSLIST_USER=%s"
)
CONTEXT_SQL = (
    "SELECT VERSION(),CURRENT_USER(),CURRENT_ROLE(),CONNECTION_ID(),DATABASE(),"
    "@@transaction_isolation,@@character_set_client,@@character_set_connection,"
    "@@character_set_results,@@collation_connection,@@sql_mode,@@time_zone,"
    "@@lower_case_table_names,@@cte_max_recursion_depth,@@server_uuid,"
    "@@max_allowed_packet"
)
SQL_MODE = "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION"


def native_epoch(owner, *, control=False):
    connection = owner._control_connection if control else owner._connection
    _, rows = read_control(
        owner,
        EPOCH_SQL,
        (owner.session_id, owner.request.access.user),
        connection=connection,
    )
    strength = (
        "REPEATABLE READ" if owner.request.isolation == "stable" else "SERIALIZABLE"
    )
    if (
        len(rows) != 1
        or len(rows[0]) != 10
        or any(type(v) is not int or v <= 0 for v in rows[0][:2])
        or rows[0][2:6] != ("ACTIVE", "READ ONLY", strength, "NO")
        or rows[0][6] != owner.context[14]
        or rows[0][7:]
        != (
            owner.request.access.account,
            owner.request.access.roles,
            owner.request.access.database,
        )
    ):
        raise ExecutionError("MYSQL_TRANSACTION_OBSERVATION_REQUIRED")
    return rows[0]


def native_context(owner):
    _, rows = read_control(owner, CONTEXT_SQL)
    a = owner.request.access
    strength = (
        "REPEATABLE-READ" if owner.request.isolation == "stable" else "SERIALIZABLE"
    )
    if (
        len(rows) != 1
        or len(rows[0]) != 16
        or rows[0][:10]
        != (
            owner.request.artifact.request.release,
            a.account,
            a.roles,
            owner.session_id,
            a.database,
            strength,
            "utf8mb4",
            "utf8mb4",
            "utf8mb4",
            "utf8mb4_0900_bin",
        )
        or set(rows[0][10].split(",")) != set(SQL_MODE.split(","))
        or rows[0][11:13] != ("+00:00", 0)
        or type(rows[0][13]) is not int
        or rows[0][13] < 0
        or type(rows[0][14]) is not str
        or not rows[0][14]
        or type(rows[0][15]) is not int
        or rows[0][15] <= 0
    ):
        raise ExecutionError("MYSQL_NATIVE_CONTEXT")
    capacity = rows[0][15]
    previous = getattr(owner, "_mysql_packet_capacity", None)
    if previous is not None and capacity != previous:
        raise ExecutionError("MYSQL_PACKET_CAPACITY_CHANGED")
    owner._mysql_packet_capacity = capacity
    return rows[0][:15]


def _same_packet_requirements(left, right) -> bool:
    return (
        type(left) is tuple
        and type(right) is tuple
        and len(left) == len(right)
        and all(
            type(actual) is tuple
            and type(expected) is tuple
            and len(actual) == len(expected) == 2
            and actual[0] is expected[0]
            and type(actual[1]) is int
            and actual[1] == expected[1]
            for actual, expected in zip(left, right, strict=True)
        )
    )


def mysql_text_packet_requirements(owner) -> tuple[tuple[object, int], ...]:
    """Derive every growing Text operation from the verified rendered AST."""
    from pietto._project.project_sql_emission_ast import (
        inline_body,
        inline_values,
        row_value_roots,
    )
    from pietto._project.project_sql_emission_rows import (
        SQLBlockRead,
        SQLOperation,
        value_nodes,
    )
    from pietto.ir.model import SymbolNamespace

    roots = row_value_roots(owner.request.artifact.ast)
    if type(roots) is not tuple:
        raise ExecutionError("MYSQL_TEXT_PACKET_ROOTS")

    def nodes(values):
        # An inline let's operations follow the EXISTS read that renders it.
        for value in values:
            for node in value_nodes(value):
                yield node
                if type(node) is SQLBlockRead and inline_body(node.target.producer):
                    yield from nodes(inline_values(node.target.producer))

    requirements = []
    for root in roots:
        for node in nodes((root,)):
            if type(node) is not SQLOperation:
                continue
            original = node.original
            symbol = getattr(original, "callee_symbol", None)
            if node.kind != "scalar_call":
                continue
            if getattr(symbol, "namespace", None) is not SymbolNamespace.CALLABLE:
                raise ExecutionError("MYSQL_TEXT_PACKET_IDENTITY")
            if getattr(symbol, "name", None) not in {
                "lower",
                "upper",
                "replace",
            }:
                continue
            maximum = node.realization.domain.get("max_characters")
            if (
                node.realization.tag != "Text"
                or type(maximum) is not int
                or not 0 <= maximum <= 16383
            ):
                raise ExecutionError("MYSQL_TEXT_PACKET_BOUND")
            required = maximum * 4
            requirements.append((original.ref, required))
    return tuple(requirements)


def verify_mysql_text_packet_capacity(owner) -> None:
    """Bind the live packet ceiling to the complete verified expression closure."""
    capacity = getattr(owner, "_mysql_packet_capacity", None)
    if type(capacity) is not int or capacity <= 0:
        raise ExecutionError("MYSQL_TEXT_PACKET_CONTEXT")
    requirements = mysql_text_packet_requirements(owner)
    previous = getattr(owner, "_mysql_text_packet_requirements", None)
    if previous is None:
        owner._mysql_text_packet_requirements = requirements
    elif not _same_packet_requirements(previous, requirements):
        raise ExecutionError("MYSQL_TEXT_PACKET_IDENTITY")
    if any(required > capacity for _, required in requirements):
        raise ExecutionError("MYSQL_TEXT_PACKET_CAPACITY")


@dataclass(frozen=True, slots=True, eq=False)
class MySQLSourceQualification:
    """Fresh owned structural authority, conditional on an external commitment."""

    owner: Any = field(repr=False)
    request: Any = field(repr=False)
    connection: Any = field(repr=False)
    context: tuple
    epoch: tuple
    objects: tuple = field(repr=False)
    edges: tuple
    security: tuple
    state: tuple = field(repr=False)
    definition_stability: str = "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
    native_lifetime_protection: str = "NOT_DEMONSTRATED"
    premise_compliance: str = "NOT_INDEPENDENTLY_VERIFIED"

    def verify(self, owner):
        from pietto._project.project_execution_mysql import MySQLExecution

        if (
            type(owner) is not MySQLExecution
            or owner._closed
            or owner._discarded
            or owner._transaction != "OPEN"
            or self.connection is None
            or not self.objects
            or self.owner is not owner
            or owner._qualification is not self
            or owner._owned_qualification is not self
            or self.request is not owner.request
            or request_state(owner.request) != owner._captured
            or self.connection is not owner._owned_connection
            or owner._connection is not self.connection
            or self.context != owner.context
            or self.epoch != owner._epoch
            or self.objects is not owner._sources
            or self.state
            != (tuple(astuple(obj) for obj in self.objects), self.edges, self.security)
            or self.definition_stability != "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
            or self.native_lifetime_protection != "NOT_DEMONSTRATED"
            or self.premise_compliance != "NOT_INDEPENDENTLY_VERIFIED"
        ):
            raise ExecutionError("MYSQL_SOURCE_QUALIFICATION_IDENTITY")


def qualify_sources(owner) -> tuple[tuple, tuple]:
    """Acquire effect-free definitions first, then independently check all reads.

    The operator's definition/security commitment precedes ALL acquisition.
    Catalog visibility is required for each structurally discovered object; an
    empty usage catalog cannot provide missing edges. No EXPLAIN is used.
    """
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_mysql_view_source import recognize_view, ViewLimits
    from pietto._project.project_mysql_view_source_verification import (
        SourceObject,
        verify_view,
        verify_closure,
        security_paths,
    )
    from pietto._project.project_guard_context import (
        guard_source_schema_sql,
        verify_guard_source_columns,
    )
    from pietto._project.project_execution_source import (
        requires_temporal_uuid_catalog,
        verify_temporal_uuid_catalog,
    )

    owner._checkpoint()
    verify_deployment(owner.request, required=True)
    if type(owner) is not MySQLExecution or owner._qualification is not None:
        raise ExecutionError("MYSQL_SOURCE_QUALIFICATION_OWNER")
    owner._refresh()
    premise = cast(MySQLDeploymentPremise, owner.request.mysql_deployment)
    limits = ViewLimits()
    sources = owner.request.artifact.request.sources
    roots = tuple((s.namespace, s.name) for s in sources)
    requirements = (
        owner.refined_request.refinement.sources
        if owner.refined_request is not None
        else ()
        if owner.request.source_requirement is None
        else (owner.request.source_requirement,)
    )
    roots += tuple((r.registry_namespace, r.registry_name) for r in requirements)
    _, quoted = read_control(owner, "SELECT @@sql_quote_show_create")
    if quoted != ((1,),):
        raise ExecutionError("MYSQL_VIEW_LEXICAL_CONTEXT")
    records, active, visited = [], set(), set()
    total_bytes = 0

    def acquire(key, depth=0):
        nonlocal total_bytes
        owner._checkpoint()
        if key[0] not in premise.schemas:
            raise ExecutionError("MYSQL_DEPLOYMENT_PREMISE_SCOPE")
        if key in active or depth > limits.depth:
            raise ExecutionError("MYSQL_VIEW_DEPENDENCY_CYCLE")
        if key in visited:
            return
        if len(records) >= limits.objects:
            raise ExecutionError("MYSQL_VIEW_OBJECT_LIMIT")
        active.add(key)
        position = len(records)
        records.append(None)
        relation = ".".join(identifier(v, family="mysql") for v in key)
        _, kind = read_control(
            owner,
            "SELECT TABLE_TYPE,ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            key,
        )
        if len(kind) != 1 or kind[0][0] not in ("BASE TABLE", "VIEW"):
            raise ExecutionError("MYSQL_SOURCE_METADATA_REQUIRED")
        _, definition = read_control(
            owner,
            "SHOW CREATE " + ("VIEW " if kind[0][0] == "VIEW" else "TABLE ") + relation,
        )
        if (
            len(definition) != 1
            or definition[0][0] != key[1]
            or type(definition[0][1]) is not str
        ):
            raise ExecutionError("MYSQL_SOURCE_DEFINITION_REQUIRED")
        total_bytes += len(definition[0][1].encode("utf-8"))
        if total_bytes > limits.bytes:
            raise ExecutionError("MYSQL_VIEW_DEFINITION_SIZE")
        view = None
        if kind[0][0] == "VIEW":
            if len(definition[0]) != 4:
                raise ExecutionError("MYSQL_SOURCE_DEFINITION_REQUIRED")
            view = recognize_view(
                key,
                definition[0][1],
                charset=definition[0][2],
                collation=definition[0][3],
            )
            refs = verify_view(view)
            for _, schema, name in refs:
                acquire((schema, name), depth + 1)
        elif kind[0][1] != "InnoDB":
            raise ExecutionError("MYSQL_SOURCE_ENGINE")
        elif not definition[0][1].startswith(
            "CREATE TABLE " + identifier(key[1], family="mysql") + " ("
        ):
            # SHOW CREATE resolves session shadows; Information Schema alone
            # describes the persistent object and cannot exclude a temporary one.
            raise ExecutionError("MYSQL_SOURCE_PERSISTENT_IDENTITY")
        # Calls in every nested view have been rejected before type resolution.
        _, columns = read_control(
            owner,
            "SELECT COLUMN_NAME,EXTRA,GENERATION_EXPRESSION FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
            key,
        )
        records[position] = SourceObject(
            key, kind[0][0], kind[0][1], columns, view, owner.context, definition[0][1]
        )
        active.remove(key)
        visited.add(key)

    for root in roots:
        acquire(root)
    objects = tuple(records)
    edges = verify_closure(roots, objects, owner.context)
    security = security_paths(
        roots,
        objects,
        cast(MySQLAccess, owner.request.access).account,
        cast(MySQLAccess, owner.request.access).roles,
    )
    owner._refresh()
    # This fresh object is never reconstructed from a caller/data-only receipt.
    owner._sources = objects
    owner._qualification = owner._owned_qualification = MySQLSourceQualification(
        owner,
        owner.request,
        owner._connection,
        owner.context,
        owner._epoch,
        objects,
        edges,
        security,
        (tuple(astuple(obj) for obj in objects), edges, security),
    )
    owner._qualification.verify(owner)
    reads = source_read_columns(owner.request.output)
    schemas = []
    by_key = {obj.key: obj for obj in objects}
    for source, names in zip(sources, reads, strict=True):
        columns = by_key[(source.namespace, source.name)].columns
        if any(name not in tuple(c[0] for c in columns) for name in names):
            raise ExecutionError("MYSQL_SOURCE_COLUMN_METADATA_REQUIRED")
        sql = guard_source_schema_sql(source, names, family="mysql")
        metadata, rows = ((), ()) if sql is None else read_control(owner, sql)
        if rows:
            raise ExecutionError("MYSQL_SOURCE_SCHEMA_ROWS")
        if requires_temporal_uuid_catalog(source):
            _, catalog = read_control(
                owner,
                "SELECT COLUMN_NAME,COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                (source.namespace, source.name),
            )
            try:
                verify_temporal_uuid_catalog(source, tuple(catalog), family="mysql")
            except ValueError as error:
                raise ExecutionError(
                    "MYSQL_SOURCE_TEMPORAL_UUID_QUALIFICATION"
                ) from error
        verify_guard_source_columns(source, names, metadata, (), route="mysql_rows")
        schemas.append(metadata)
    owner._refresh()
    owner._qualification.verify(owner)
    return objects, tuple(schemas)


@dataclass(frozen=True, slots=True, eq=False)
class MySQLSourceAdmission:
    owner: Any = field(repr=False)
    requirement: Any = field(repr=False)
    connection: Any = field(repr=False)
    session_id: int
    epoch: tuple
    state: tuple = field(repr=False)

    def verify(self, connection, requirement):
        self.owner._verify_lifetime()
        if (
            self.owner._owned_connection is not connection
            or self.connection is not connection
            or self.requirement is not requirement
            or self.state != requirement_state(requirement)
            or self.session_id != self.owner.session_id
            or self.epoch != self.owner._epoch
        ):
            raise ExecutionError("MYSQL_SOURCE_ADMISSION_IDENTITY")


def admit_sources(owner, requirements):
    reads = source_read_columns(owner.request.output)
    if len(requirements) != len(reads):
        raise ExecutionError("SOURCE_VECTOR")
    observations, admissions = [], []
    for req, names, schema in zip(
        requirements, reads, owner._source_schema, strict=True
    ):
        verify_requirement(req, owner.request.artifact.request.sources, family="mysql")
        if req.role != owner.request.access.account:
            raise ExecutionError("SOURCE_ROLE")
        relation = (
            identifier(req.source.namespace, family="mysql")
            + "."
            + identifier(req.source.name, family="mysql")
        )
        registry = (
            identifier(req.registry_namespace, family="mysql")
            + "."
            + identifier(req.registry_name, family="mysql")
        )
        _, registered = read_control(
            owner,
            "SELECT provider,version_tag,active,revision FROM " + registry + " LIMIT 2",
        )
        _, definition = read_control(owner, "SHOW CREATE VIEW " + relation)
        columns = ",".join(identifier(n, family="mysql") for n in req.token_columns)
        meta, rows = read_control(
            owner, "SELECT " + columns + " FROM " + relation + " LIMIT 0"
        )
        if rows or len(definition) != 1:
            raise ExecutionError("SOURCE_DOMAIN")
        nulls = " OR ".join(
            identifier(n, family="mysql") + " IS NULL" for n in req.token_columns
        )
        _, collisions = read_control(
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
        )
        observations.append(
            ObservedSource(
                req,
                "mysql_rows",
                owner.session_id,
                req.role,
                registered,
                definition[0][1],
                tuple((m[1], m[7]) for m in meta),
                collisions,
                schema,
                (),
                ("NORMAL",) * 4 + (("NORMAL" if names else "NOT_REQUIRED"), "NORMAL"),
            )
        )
        state = requirement_state(req)
        if state is None:
            raise ExecutionError("SOURCE_REQUIREMENT")
        admissions.append(
            MySQLSourceAdmission(
                owner,
                req,
                owner._connection,
                owner.session_id,
                owner._epoch,
                state,
            )
        )
    observations = tuple(observations)
    environment = owner.environment
    verify_source_observations(
        requirements,
        reads,
        observations,
        route="mysql_rows",
        session_id=owner.session_id,
        role=owner.request.access.account,
    )
    return SourceAdmissions(
        requirements,
        reads,
        observations,
        "mysql_rows",
        owner.session_id,
        owner.request.access.account,
        environment,
        owner._connection,
        tuple(admissions),
        (tuple(requirement_state(r) for r in requirements), environment),
        tuple(_observation_state(o) for o in observations),
    )


@dataclass(frozen=True, slots=True, eq=False)
class MySQLGuardContext:
    program: Any = field(repr=False)
    owner: Any = field(repr=False)
    connection: Any = field(repr=False)
    transaction: object = field(repr=False)
    native_transaction: tuple
    session_id: int
    role: str
    environment: tuple
    sources: tuple = field(repr=False)
    route: str = "mysql_rows"

    @property
    def separate_allowed(self):
        return self.program.refinement is not None

    def verify_owned(self, owner):
        from pietto._project.project_execution_mysql import MySQLExecution

        if (
            type(owner) is not MySQLExecution
            or self.owner is not owner
            or owner.guarded_request is None
            or owner.guarded_request is not owner._owned_guarded_request
            or owner.guarded_request.program is not self.program
            or owner._guard_context is not self
            or owner._guard_transaction is not self.transaction
            or self.connection is not owner._owned_connection
            or self.native_transaction != owner._epoch
            or self.session_id != owner.session_id
            or self.role != cast(MySQLAccess, owner.request.access).account
            or self.environment != owner.environment
            or self.sources != owner._sources
            or self.route != "mysql_rows"
        ):
            raise ExecutionError("GUARD_CONTEXT_LIFETIME")
        owner._verify_lifetime()
        if self.program.refinement is not None:
            admissions = owner.source_admissions
            if admissions is None or admissions is not owner._owned_admissions:
                raise ExecutionError("GUARD_SOURCE_VECTOR")
            admissions.verify(
                self.connection,
                self.program.refinement.sources,
                source_read_columns(self.program.output),
            )
