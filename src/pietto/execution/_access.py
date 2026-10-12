"""Caller-supplied inputs of one execute() call; constructing them does no I/O
and reads no environment. execute() checks them, never a constructor."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ExecutionLimits",
    "MySQLAccess",
    "MySQLDeploymentPremise",
    "PostgresAccess",
    "PostgresDeploymentPremise",
]


@dataclass(frozen=True, slots=True, eq=False)
class PostgresAccess:
    """Explicit connection input for one PostgreSQL 18.6 server.

    ``host`` is one TCP host name or IP address: a Unix-socket directory
    (leading ``/``), an abstract socket (leading ``@``) or a host list (a
    comma) is refused. ``sslmode`` is ``require`` (TLS that encrypts but does
    not verify the server's certificate; SCRAM is bound to the TLS channel)
    or ``disable`` (only for the loopback addresses ``127.0.0.1`` and
    ``::1``). The role must authenticate with SCRAM-SHA-256. Pietto reads no
    environment variable, service file, password file or certificate in
    place of these fields. The password is never shown by repr() or str(),
    and the object refuses pickle and copy.
    """

    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str = "require"

    def __repr__(self) -> str:
        return (
            f"PostgresAccess(host={self.host!r}, port={self.port!r},"
            f" database={self.database!r}, user={self.user!r},"
            f" password=<redacted>, sslmode={self.sslmode!r})"
        )

    def __reduce_ex__(self, protocol):
        raise TypeError(
            "PostgresAccess holds a credential; it cannot be pickled or copied"
        )


@dataclass(frozen=True, slots=True, eq=False)
class PostgresDeploymentPremise:
    """The operator's explicit commitment for one execute() call.

    From before source discovery until the last possible remote use of the
    sources, every administrative path keeps the definitions and security of
    the relations in ``schemas`` stable; row data may change. ``schemas`` is a
    tuple of 1 to 128 distinct schema names that covers the schema of every
    source of the compiled query and includes ``pg_catalog``, where
    qualification checks built-in definitions; other ``pg_*`` schemas and
    ``information_schema`` are refused. Pietto binds the premise to the
    compiled query's own sources and requalifies them on every attempt; it
    does not verify the commitment.

    Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED
    """

    schemas: tuple[str, ...]

    def __reduce_ex__(self, protocol):
        raise TypeError(
            "PostgresDeploymentPremise is a per-call commitment;"
            " it cannot be pickled or copied"
        )


@dataclass(frozen=True, slots=True, eq=False)
class MySQLAccess:
    """Explicit connection input for one MySQL 8.4.12 server.

    ``host`` is one TCP host name or IP address. Unix-socket and host-list
    forms are refused. ``ca_file`` is the explicit trust anchor; Pietto always
    verifies the certificate and its identity. The account and roles are the
    values the freshly qualified context must observe. The password is never
    shown by repr() or str(), and the object refuses pickle and copy.
    """

    host: str
    port: int
    database: str
    user: str
    password: str
    ca_file: str
    account: str
    roles: str = "NONE"

    def __repr__(self) -> str:
        return (
            f"MySQLAccess(host={self.host!r}, port={self.port!r},"
            f" database={self.database!r}, user={self.user!r},"
            f" password=<redacted>, ca_file={self.ca_file!r},"
            f" account={self.account!r}, roles={self.roles!r})"
        )

    def __reduce_ex__(self, protocol):
        raise TypeError(
            "MySQLAccess holds a credential; it cannot be pickled or copied"
        )


@dataclass(frozen=True, slots=True, eq=False)
class MySQLDeploymentPremise:
    """The operator's explicit commitment for one execute() call.

    From before source discovery until the last possible remote use of the
    sources, every administrative path keeps definitions and security in
    ``schemas`` stable; row data may change. Pietto binds the premise to the
    compiled query's own sources and requalifies them on every attempt; it
    does not verify the commitment.

    Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED
    """

    schemas: tuple[str, ...]

    def __reduce_ex__(self, protocol):
        raise TypeError(
            "MySQLDeploymentPremise is a per-call commitment;"
            " it cannot be pickled or copied"
        )


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    """Bounds of one attempt. ``batch_rows`` (at most 4096) and ``batch_bytes``
    (at most 8 MiB) bound each batch; ``max_rows`` and ``max_bytes`` bound what
    is delivered; ``max_bytes`` also counts the route's qualifying profile and
    catalog reads. ``seconds`` is the attempt's deadline. Each PostgreSQL
    statement is also limited to 10 seconds by the server."""

    batch_rows: int = 256
    batch_bytes: int = 1024 * 1024
    max_rows: int = 1048576
    max_bytes: int = 64 * 1024 * 1024
    seconds: float = 20.0
