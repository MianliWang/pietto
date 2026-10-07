"""Pinned pure MySQL connection and single-use binary statement ownership."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import ssl
from typing import Any

from pietto._project.project_execution import (
    ExecutionError,
    ExecutionFailure,
    pinned_modules,
)

__all__: tuple[str, ...] = ()
# The pinned driver closure of `pietto[execute-mysql]`.
DRIVERS = (("mysql-connector-python", "26.7.0", "mysql.connector.connection"),)


def drivers():
    return pinned_modules(DRIVERS, "EXECUTION_DRIVER_VERSION")


@dataclass(frozen=True, slots=True)
class MySQLFailure(ExecutionFailure):
    vendor_code: int | None = None


def failure(error, phase):
    code, state = getattr(error, "errno", None), getattr(error, "sqlstate", None)
    return MySQLFailure(
        phase,
        type(error).__name__,
        state if type(state) is str else None,
        code if type(code) is int else None,
    )


def transport_state(connection):
    socket = connection._socket
    return (
        socket,
        None if socket is None else socket.sock,
        connection._protocol,
        connection.connection_id,
    )


def connect(owner, *, control=False):
    if "SSLKEYLOGFILE" in os.environ:
        raise ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")
    (module,) = drivers()
    connection = module.MySQLConnection()
    # Register the unconnected handle, including failed handshakes.
    owner._connections.append(connection)
    if control:
        owner._control_connection = owner._owned_control_connection = connection
    else:
        owner._connection = owner._owned_connection = connection
    owner.control_events.append(
        ("connection_registered", "control" if control else "data")
    )
    owner._checkpoint()
    a = owner.request.access
    switch = connection._authenticator._switch_auth_strategy

    def selected_auth(
        new_strategy_name, strategy_class=None, username=None, password_factor=1
    ):
        if (
            new_strategy_name != "caching_sha2_password"
            or strategy_class is not None
            or username is not None
            or password_factor != 1
        ):
            raise ExecutionError("MYSQL_AUTHENTICATION_PROFILE")
        return switch(new_strategy_name, password_factor=1)

    connection._authenticator._switch_auth_strategy = selected_auth
    connection.connect(
        host=a.host,
        port=a.port,
        database=a.database,
        user=a.user,
        password=a.password,
        connection_timeout=max(1, min(10, math.ceil(owner._remaining()))),
        read_timeout=2 if control else 10,
        write_timeout=2,
        autocommit=True,
        charset="utf8mb4",
        collation="utf8mb4_0900_bin",
        ssl_ca=a.ca_file,
        ssl_verify_cert=True,
        ssl_verify_identity=a.verify_identity,
        tls_versions=["TLSv1.2", "TLSv1.3"],
        auth_plugin="caching_sha2_password",
        get_warnings=False,
        raise_on_warnings=False,
        consume_results=False,
        allow_local_infile=False,
        conn_attrs={
            "pietto_attempt": owner.attempt,
            "pietto_purpose": "control" if control else "data",
        },
    )
    owner._checkpoint()
    if type(connection) is not module.MySQLConnection:
        raise ExecutionError("EXECUTION_DRIVER_IDENTITY")
    sock = connection._socket.sock
    strategy = connection._authenticator._auth_strategy
    if (
        connection._ssl_active is not True
        or not isinstance(sock, ssl.SSLSocket)
        or sock.version() not in ("TLSv1.2", "TLSv1.3")
        or strategy is None
        or strategy.name != "caching_sha2_password"
    ):
        raise ExecutionError("MYSQL_CONNECTION_PROFILE")
    owner.control_events.append(
        (
            "connection_profile",
            "control" if control else "data",
            sock.version(),
            strategy.name,
        )
    )
    return connection


def read_control(
    owner, sql, arguments=(), *, connection=None, cleanup=False, explain=False
):
    """Only internal session/context/admission SQL; no callback or public SQL API."""
    connection = owner._connection if connection is None else connection
    if connection is None or connection.unread_result:
        raise ExecutionError("MYSQL_UNREAD_CONTEXT")
    if not cleanup:
        owner._checkpoint()
    cursor = connection.cursor(read_timeout=2 if cleanup else 10, write_timeout=2)
    owner._controls.append(cursor)
    primary = None
    try:
        cursor.execute(sql, arguments)
        metadata = tuple(cursor.description or ())
        rows = []
        if metadata:
            while True:
                batch = cursor.fetchmany(owner.request.limits.batch_rows)
                if not batch:
                    break
                rows.extend(tuple(r) for r in batch)
                owner._charge_internal(batch)
                if len(rows) > owner.request.limits.max_rows:
                    raise ExecutionError("EXECUTION_RESOURCE_LIMIT")
                if not cleanup:
                    owner._checkpoint()
        if cursor.warning_count:
            count = cursor.warning_count
            if not explain or not sql.startswith("EXPLAIN SELECT ") or arguments:
                raise ExecutionError("MYSQL_CONTROL_WARNING")
            cursor.execute("SHOW WARNINGS")
            diagnostics = tuple(
                cursor.fetchmany(min(count, owner.request.limits.max_rows) + 1)
            )
            owner._charge_internal(diagnostics)
            if len(diagnostics) != count or any(
                row[:2] != ("Note", 1003) for row in diagnostics
            ):
                raise ExecutionError("MYSQL_CONTROL_WARNING")
            if cursor.fetchone() is not None:
                raise ExecutionError("MYSQL_CONTROL_WARNING")
            owner.control_events.append(
                ("explain_notes", tuple(row[:2] for row in diagnostics))
            )
        return metadata, tuple(rows)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            cursor.close()
        except BaseException as error:
            owner._cleanup_errors.append(failure(error, "control_close"))
            if primary is None:
                raise
        else:
            owner._controls.remove(cursor)


class NativeStatement:
    """Owned prepare -> execute -> binary EOF -> close-send, never reusable."""

    def __init__(self, owner, sql, arguments, purpose):
        from pietto._project.project_execution_mysql import MySQLExecution

        if (
            type(owner) is not MySQLExecution
            or type(sql) is not bytes
            or type(arguments) is not tuple
        ):
            raise ExecutionError("MYSQL_STATEMENT_OWNER")
        self.owner, self.connection = owner, owner._owned_connection
        self.sql, self.arguments, self.purpose = sql, arguments, purpose
        self.prepared: Any = None
        self.statement_id: int | None = None
        self._prepared_state: Any = None
        self.metadata: tuple = ()
        self.metadata_eof: Any = None
        self.terminal: Any = None
        self.close_send = "NOT_STARTED"
        self.closed = False
        self.executed = False
        self._root = (owner, self.connection, sql, arguments, purpose)
        owner._statements.append(self)

    def verify(self):
        from pietto._project.project_refinement_enumeration import atom

        if (
            self.closed
            or self.connection is not self.owner._owned_connection
            or self._root[:3] != (self.owner, self.connection, self.sql)
            or tuple(atom(v) for v in self._root[3])
            != tuple(atom(v) for v in self.arguments)
            or self.purpose != self._root[4]
        ):
            raise ExecutionError("MYSQL_STATEMENT_IDENTITY")
        self.owner._verify_lifetime()
        if (
            self._prepared_state is not None
            and self._prepared_state != self._preparation_state()
        ):
            raise ExecutionError("MYSQL_PREPARED_IDENTITY")
        self.owner._checkpoint()

    def _preparation_state(self):
        p = self.prepared
        return (
            self.statement_id,
            p["statement_id"],
            p["num_params"],
            tuple(tuple(m) for m in p["parameters"]),
            p["num_columns"],
            tuple(tuple(m) for m in p["columns"]),
            p["warning_count"],
        )

    def _packet(self, packet, *, transaction=True):
        if (
            type(packet) is not dict
            or type(packet.get("status_flag")) is not int
            or packet.get("warning_count") != 0
            or packet["status_flag"] & 8
            or transaction
            and packet["status_flag"] & (1 | 8192) != (1 | 8192)
        ):
            raise ExecutionError("MYSQL_PROTOCOL_STATUS")

    def execute(self):
        self.verify()
        if self.prepared is not None or self.executed or self.connection.unread_result:
            raise ExecutionError("MYSQL_STATEMENT_REUSE")
        self.owner._verify_submission(self)
        self.owner._begin_operation(self)
        try:
            self.prepared = self.connection.cmd_stmt_prepare(
                self.sql, read_timeout=self.owner._timeout(), write_timeout=2
            )
            prepared = self.prepared
            if (
                type(prepared) is dict
                and type(prepared.get("statement_id")) is int
                and prepared["statement_id"] > 0
            ):
                self.statement_id = prepared["statement_id"]
            if (
                type(prepared) is not dict
                or type(prepared.get("statement_id")) is not int
                or prepared["statement_id"] <= 0
                or prepared.get("warning_count") != 0
                or type(prepared.get("num_params")) is not int
                or prepared["num_params"] != len(self.arguments)
                or len(prepared.get("parameters", ())) != len(self.arguments)
                or prepared.get("num_columns") != len(prepared.get("columns", ()))
                or any(
                    type(m) not in (tuple, list) or len(m) != 9
                    for m in prepared["parameters"]
                )
            ):
                raise ExecutionError("MYSQL_PREPARED_METADATA")
            self._prepared_state = self._preparation_state()
            self.verify()
            self.owner._verify_submission(self)
            result = self.connection.cmd_stmt_execute(
                prepared["statement_id"],
                data=self.arguments,
                parameters=prepared["parameters"],
                flags=0,
                read_timeout=self.owner._timeout(),
                write_timeout=2,
            )
            if (
                type(result) is not tuple
                or len(result) != 3
                or result[0] != len(result[1])
            ):
                raise ExecutionError("MYSQL_RESULT_KIND")
            self.metadata, self.metadata_eof = tuple(result[1]), result[2]
            self.executed = True
            # Pinned low-level API requires this public-property bookkeeping.
            # Only get_rows reading the actual EOF may clear it.
            self.connection.unread_result = True
            self._packet(self.metadata_eof)
            self.owner._checkpoint()
        finally:
            self.owner._end_operation(self)
        return self.metadata

    def fetch(self, count):
        self.verify()
        if (
            not self.executed
            or self.terminal is not None
            or not self.connection.unread_result
        ):
            raise ExecutionError("MYSQL_ROWSET_LIFETIME")
        self.owner._begin_operation(self)
        try:
            rows, terminal = self.connection.get_rows(
                count=count,
                binary=True,
                columns=self.metadata,
                read_timeout=self.owner._timeout(),
            )
            if len(rows) > count:
                raise ExecutionError("MYSQL_BATCH_ARITY")
            if terminal is not None:
                self._packet(terminal)
                if self.connection.unread_result:
                    raise ExecutionError("MYSQL_ROWSET_TERMINAL")
                self.terminal = terminal
                if self.purpose == "query":
                    self.owner._source = "EOF"
            self.owner._checkpoint()
            return tuple(tuple(row) for row in rows)
        finally:
            self.owner._end_operation(self)

    def close(self, *, discard=False):
        if self.closed:
            return
        if self.statement_id is None:
            self.close_send = "NO_RETURNED_STATEMENT"
        elif discard or self.connection.unread_result:
            self.close_send = "NOT_SENT_CONNECTION_DISCARDED"
        else:
            if (
                self._prepared_state is not None
                and self._prepared_state != self._preparation_state()
            ):
                raise ExecutionError("MYSQL_PREPARED_IDENTITY")
            self.close_send = "STARTED"
            self.connection.cmd_stmt_close(
                self.statement_id, read_timeout=2, write_timeout=2
            )
            self.close_send = "COMPLETE_NO_ACK"
        self.closed = True
