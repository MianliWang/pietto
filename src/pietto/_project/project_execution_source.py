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


def identifier(value: str) -> str:
    if type(value) is not str or not value or "\0" in value or len(value.encode()) > 63:
        raise SourceAdmissionError("SOURCE_IDENTIFIER")
    return '"' + value.replace('"', '""') + '"'


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


def verify_requirement(value, sources) -> None:
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
        identifier(name)
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
    )
