"""Private explicit retained-source admission; provider guarantees are not data hashes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_sql_emission_contract import BoundSource

__all__: tuple[str, ...] = ()


class SourceAdmissionError(ValueError):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class RetainedSourceRequirement:
    source: BoundSource = field(repr=False)
    provider: str
    version: str
    revision: str
    registry_namespace: str
    registry_name: str
    definition: str = field(repr=False)
    token_columns: tuple[str, ...]
    role: str
    provider_guarantee: str


def identifier(value: str, *, family="postgres") -> str:
    if (
        family not in ("postgres", "mysql")
        or type(value) is not str
        or not value
        or "\0" in value
        or len(value.encode()) > (63 if family == "postgres" else 64)
    ):
        raise SourceAdmissionError("SOURCE_IDENTIFIER")
    quote = '"' if family == "postgres" else "`"
    return quote + value.replace(quote, quote * 2) + quote


def requirement_state(value):
    if value is None:
        return None
    if type(value) is not RetainedSourceRequirement:
        raise SourceAdmissionError("SOURCE_REQUIREMENT")
    return (
        value.source,
        value.provider,
        value.version,
        value.revision,
        value.registry_namespace,
        value.registry_name,
        value.definition,
        value.token_columns,
        value.role,
        value.provider_guarantee,
    )


def verify_requirement(value, sources, *, family="postgres") -> None:
    if value is None:
        return
    requirement_state(value)
    if not any(value.source is source for source in sources):
        raise SourceAdmissionError("SOURCE_ROOT")
    if (
        type(value.token_columns) is not tuple
        or not 0 < len(value.token_columns) <= 16
        or len(set(value.token_columns)) != len(value.token_columns)
    ):
        raise SourceAdmissionError("SOURCE_TOKENS")
    for name in (
        *value.token_columns,
        value.registry_namespace,
        value.registry_name,
        value.source.namespace,
        value.source.name,
    ):
        identifier(name, family=family)
    if any(
        type(item) is not str or not item or "\0" in item
        for item in (
            value.provider,
            value.version,
            value.revision,
            value.definition,
            value.role,
            value.provider_guarantee,
        )
    ):
        raise SourceAdmissionError("SOURCE_DECLARATION")


@dataclass(frozen=True, slots=True, eq=False)
class SourceAdmission:
    requirement: RetainedSourceRequirement = field(repr=False)
    source: BoundSource = field(repr=False)
    session_id: int
    definition: str = field(repr=False)
    token_type_oids: tuple[int, ...]
    _connection: Any = field(repr=False)
    _state: tuple = field(repr=False)
    registry: tuple = field(default=(), repr=False)

    def verify(self, connection, requirement) -> None:
        if (
            self._connection is not connection
            or self.requirement is not requirement
            or self.source is not requirement.source
            or self._state != requirement_state(requirement)
        ):
            raise SourceAdmissionError("SOURCE_ADMISSION_IDENTITY")


def admit_postgres_source(connection, requirement, *, role, session_id):
    """Check actual full-domain key/metadata evidence in the owned read-only view.

    The definition is supplied in the explicit pg_catalog deparse context.
    The provider separately guarantees immutable token/value correspondence and
    retention. This check neither authenticates a malicious provider nor proves
    a new R2 execution mode. Other lawful token representations are future owners.
    """
    if type(requirement) is not RetainedSourceRequirement:
        raise SourceAdmissionError("SOURCE_REQUIREMENT")
    source = requirement.source
    verify_requirement(requirement, (source,))
    if role != requirement.role:
        raise SourceAdmissionError("SOURCE_ROLE")
    relation = identifier(source.namespace) + "." + identifier(source.name)
    registry = (
        identifier(requirement.registry_namespace)
        + "."
        + identifier(requirement.registry_name)
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT provider,version_tag,active,revision FROM " + registry + " LIMIT 2"
        )
        rows = cursor.fetchall()
        if (
            rows
            != [(requirement.provider, requirement.version, 1, requirement.revision)]
            or len(rows) != 1
            or tuple(type(v) for v in rows[0]) != (str, str, int, str)
        ):
            raise SourceAdmissionError("SOURCE_VERSION_OR_RETENTION")
        cursor.execute(
            "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)", (relation,)
        )
        actual = cursor.fetchone()
        if actual != (requirement.definition,):
            raise SourceAdmissionError("SOURCE_DOMAIN")
        columns = ",".join(identifier(n) for n in requirement.token_columns)
        cursor.execute("SELECT " + columns + " FROM " + relation + " LIMIT 0")
        oids = tuple(c.type_code for c in cursor.description)
        # S03's qualified provider profile is a composite native signed integer
        # key. This is one admission method, not a universal R2 token restriction.
        if any(oid not in (20, 21, 23) for oid in oids):
            raise SourceAdmissionError("SOURCE_TOKEN_PROFILE_NOT_DELIVERED")
        nulls = " OR ".join(
            identifier(n) + " IS NULL" for n in requirement.token_columns
        )
        cursor.execute(
            "SELECT "
            + columns
            + " FROM "
            + relation
            + " GROUP BY "
            + columns
            + " HAVING "
            + nulls
            + " OR COUNT(*)<>1 LIMIT 1"
        )
        if cursor.fetchone() is not None:
            raise SourceAdmissionError("SOURCE_TOKEN_NOT_INJECTIVE")
    state = requirement_state(requirement)
    assert state is not None
    return SourceAdmission(
        requirement,
        source,
        session_id,
        actual[0],
        oids,
        connection,
        state,
        tuple(rows),
    )


@dataclass(frozen=True, slots=True, eq=False)
class ObservedSource:
    """Data supplied by an explicitly owned native observer, not authentication."""

    requirement: RetainedSourceRequirement = field(repr=False)
    route: str
    session_id: int
    role: str
    registry: tuple = field(repr=False)
    definition: str = field(repr=False)
    token_types: tuple
    collision_rows: tuple = field(repr=False)
    schema: tuple = field(repr=False)
    collations: tuple = field(repr=False)
    terminals: tuple[str, ...]


def _observation_state(observation):
    import json

    return (
        observation.requirement,
        observation.route,
        observation.session_id,
        observation.role,
        observation.registry,
        observation.definition,
        observation.token_types,
        observation.collision_rows,
        json.dumps(observation.schema, sort_keys=True, separators=(",", ":")),
        observation.collations,
        observation.terminals,
    )


def verify_source_observations(
    requirements, read_columns, observations, *, route, session_id, role
):
    """Complete per-source checks; declarations and native observations stay separate."""
    from types import SimpleNamespace
    from pietto._project.project_execution_reader import check_native_column
    from pietto._project.project_sql_emission_rows import field_realization

    if (
        route not in ("postgres_rows", "postgres_adbc", "mysql_rows")
        or type(session_id) is not int
        or session_id <= 0
    ):
        raise SourceAdmissionError("SOURCE_CONTEXT")
    if (
        type(requirements) is not tuple
        or type(observations) is not tuple
        or len(requirements) != len(observations)
        or len(read_columns) != len(requirements)
    ):
        raise SourceAdmissionError("SOURCE_VECTOR")
    for req, names, observed in zip(
        requirements, read_columns, observations, strict=True
    ):
        if (
            type(observed) is not ObservedSource
            or observed.requirement is not req
            or observed.route != route
            or observed.session_id != session_id
            or observed.role != role
            or req.role != role
        ):
            raise SourceAdmissionError("SOURCE_OBSERVATION_IDENTITY")
        if observed.registry != (
            (req.provider, req.version, 1, req.revision),
        ) or tuple(type(v) for v in observed.registry[0]) != (str, str, int, str):
            raise SourceAdmissionError("SOURCE_VERSION_OR_RETENTION")
        if observed.definition != req.definition or observed.collision_rows != ():
            raise SourceAdmissionError("SOURCE_DOMAIN_OR_TOKEN")
        if type(observed.token_types) is not tuple or len(observed.token_types) != len(
            req.token_columns
        ):
            raise SourceAdmissionError("SOURCE_TOKEN_TYPES")
        for native in observed.token_types:
            if route == "postgres_rows":
                valid = type(native) is int and native in (20, 21, 23)
            elif route == "postgres_adbc":
                valid = type(native) is str and native in ("int16", "int32", "int64")
            else:
                valid = (
                    type(native) is tuple
                    and len(native) == 2
                    and type(native[0]) is int
                    and native[0] in (2, 3, 8)
                    and type(native[1]) is int
                    and not native[1] & 32
                )
            if not valid:
                raise SourceAdmissionError("SOURCE_TOKEN_PROFILE_NOT_DELIVERED")
        expected_terminals = ("NORMAL",) * 4 + (
            ("NORMAL" if names else "NOT_REQUIRED"),
            "NORMAL",
        )
        if (
            len(observed.schema) != len(names)
            or observed.terminals != expected_terminals
        ):
            raise SourceAdmissionError("SOURCE_OBSERVATION_TERMINAL")
        for i, (name, metadata) in enumerate(zip(names, observed.schema, strict=True)):
            matches = tuple(f for f in req.source.fields if f.column == name)
            if not matches:
                raise SourceAdmissionError("SOURCE_SCHEMA_FIELD")
            if route == "postgres_rows":
                if type(metadata) is not tuple or len(metadata) != 7:
                    raise SourceAdmissionError("SOURCE_SCHEMA")
                meta = SimpleNamespace(
                    name=metadata[0],
                    type_code=metadata[1],
                    precision=metadata[4],
                    scale=metadata[5],
                    null_ok=metadata[6],
                )
            else:
                meta = metadata
            for source_field in matches:
                real = field_realization(source_field)
                if real is None:
                    raise SourceAdmissionError("SOURCE_SCHEMA")
                check_native_column(
                    real,
                    route,
                    meta,
                    label="__pietto_source_" + str(i),
                    ordinal=i,
                    source_field=source_field,
                )
                if real.tag == "Text" and route != "mysql_rows":
                    selected = tuple(c for c in observed.collations if c[0] == name)
                    if selected != ((name, real.domain["collation"]),):
                        raise SourceAdmissionError("SOURCE_COLLATION")
        if route == "mysql_rows" and observed.collations != ():
            raise SourceAdmissionError("SOURCE_COLLATION_OBSERVATION")


@dataclass(frozen=True, slots=True, eq=False)
class SourceAdmissions:
    requirements: tuple = field(repr=False)
    read_columns: tuple = field(repr=False)
    observations: tuple = field(repr=False)
    route: str
    session_id: int
    role: str
    environment: tuple
    _connection: Any = field(repr=False)
    _admissions: tuple = field(repr=False)
    _states: tuple = field(repr=False)
    _observed_states: tuple = field(repr=False)

    def verify(self, connection, requirements, read_columns):
        if (
            self._connection is not connection
            or self.requirements is not requirements
            or self.read_columns != read_columns
            or self._states
            != (tuple(requirement_state(r) for r in requirements), self.environment)
        ):
            raise SourceAdmissionError("SOURCE_VECTOR_IDENTITY")
        if self._observed_states != tuple(
            _observation_state(o) for o in self.observations
        ):
            raise SourceAdmissionError("SOURCE_OBSERVATION_CHANGED")
        if connection is not None:
            if getattr(connection, "closed", False):
                raise SourceAdmissionError("SOURCE_VECTOR_CLOSED")
            if self.route != "postgres_rows" or len(self._admissions) != len(
                requirements
            ):
                raise SourceAdmissionError("SOURCE_VECTOR_CONNECTION")
            for admission, requirement in zip(
                self._admissions, requirements, strict=True
            ):
                if (
                    type(admission) is not SourceAdmission
                    or admission.session_id != self.session_id
                ):
                    raise SourceAdmissionError("SOURCE_VECTOR_CONNECTION")
                admission.verify(connection, requirement)
        elif self._admissions:
            raise SourceAdmissionError("SOURCE_VECTOR_CONNECTION")
        verify_source_observations(
            requirements,
            read_columns,
            self.observations,
            route=self.route,
            session_id=self.session_id,
            role=self.role,
        )


def admit_observed_sources(
    requirements, read_columns, observations, *, route, session_id, role, environment
):
    """Explicit test-transport observations; not a MySQL/ADBC product executor."""
    verify_source_observations(
        requirements,
        read_columns,
        observations,
        route=route,
        session_id=session_id,
        role=role,
    )
    return SourceAdmissions(
        requirements,
        read_columns,
        observations,
        route,
        session_id,
        role,
        environment,
        None,
        (),
        (tuple(requirement_state(r) for r in requirements), environment),
        tuple(_observation_state(o) for o in observations),
    )


def admit_postgres_sources(connection, requirements, read_columns, *, role, session_id):
    """One exact source vector in the same owned stable read-only transaction."""
    admissions, observations = [], []
    with connection.cursor() as context:
        context.execute(
            "SELECT current_setting('server_version_num'),current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding')"
        )
        version, isolation, readonly, encoding = context.fetchone()
    version_number = int(version)
    environment = (
        f"{version_number // 10000}.{version_number % 10000}",
        isolation,
        readonly == "on",
        encoding,
    )
    for req, names in zip(requirements, read_columns, strict=True):
        admission = admit_postgres_source(
            connection, req, role=role, session_id=session_id
        )
        admissions.append(admission)
        relation = identifier(req.source.namespace) + "." + identifier(req.source.name)
        metadata = ()
        with connection.cursor() as cursor:
            if names:
                selected = ",".join(
                    identifier(n) + " AS " + identifier("__pietto_source_" + str(i))
                    for i, n in enumerate(names)
                )
                cursor.execute("SELECT " + selected + " FROM " + relation + " LIMIT 0")
                metadata = tuple(
                    (
                        c.name,
                        c.type_code,
                        getattr(c, "display_size", None),
                        getattr(c, "internal_size", None),
                        getattr(c, "precision", None),
                        getattr(c, "scale", None),
                        c.null_ok,
                    )
                    for c in cursor.description
                )
                if cursor.fetchall() != []:
                    raise SourceAdmissionError("SOURCE_SCHEMA_ROWS")
            cursor.execute(
                "SELECT a.attname,c.collname FROM pg_catalog.pg_attribute AS a JOIN pg_catalog.pg_collation AS c ON c.oid=a.attcollation WHERE a.attrelid=$1::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
                (relation,),
            )
            collations = tuple(cursor.fetchall())
        observations.append(
            ObservedSource(
                req,
                "postgres_rows",
                session_id,
                role,
                admission.registry,
                admission.definition,
                admission.token_type_oids,
                (),
                metadata,
                collations,
                ("NORMAL",) * 4 + (("NORMAL" if names else "NOT_REQUIRED"), "NORMAL"),
            )
        )
    observations = tuple(observations)
    verify_source_observations(
        requirements,
        read_columns,
        observations,
        route="postgres_rows",
        session_id=session_id,
        role=role,
    )
    return SourceAdmissions(
        requirements,
        read_columns,
        observations,
        "postgres_rows",
        session_id,
        role,
        environment,
        connection,
        tuple(admissions),
        (tuple(requirement_state(r) for r in requirements), environment),
        tuple(_observation_state(o) for o in observations),
    )
