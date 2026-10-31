"""Offline PostgreSQL execution collaborators for execution-layer tests."""

from types import SimpleNamespace

from pietto._project import project_arrow_result as scalar
from pietto._project import project_execution_postgres as pg
from pietto._project import project_execution_reader as payloads


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.position = 0
        self.kind = "control"
        self.description = (
            SimpleNamespace(name="renamed", type_code=20, null_ok=None),
            SimpleNamespace(name="other", type_code=20, null_ok=None),
        )
        self.pgresult = SimpleNamespace(ntuples=4)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def execute(self, sql, params=None, prepare=None):
        self.connection.operations.append((sql, params, prepare))
        if sql.startswith("BEGIN"):
            self.connection.strength = (
                "serializable" if "SERIALIZABLE" in sql else "repeatable read"
            )
        elif sql == "COMMIT" and self.connection.fail == "commit":
            raise OSError("injected lost commit response")
        elif sql.startswith("SELECT current_user"):
            self.kind = "context"
        elif sql.startswith("SELECT pg_catalog.set_config"):
            pass
        elif sql.startswith("SELECT"):
            self.kind = "data"
            if self.connection.fail == "execute":
                raise OSError("injected execute failure")

    def fetchone(self):
        return (
            "pietto_query",
            self.connection.strength,
            "on",
            "UTF8",
            "pg_catalog",
            123,
        )

    def fetchmany(self, size):
        if self.connection.fail == "read" and self.position:
            raise OSError("injected later read")
        rows = self.connection.rows[self.position : self.position + size]
        self.position += len(rows)
        return rows

    def close(self):
        pass


class Connection:
    def __init__(self, fail=""):
        self.info = SimpleNamespace(server_version=180006, backend_pid=123)
        self.rows = [
            (9007199254740993, None),
            (9007199254740993, None),
            (0, 0),
            (-1, 1),
        ]
        self.operations = []
        self.fail = fail
        self.closed = False
        self.strength = "repeatable read"
        self.pgconn = SimpleNamespace(finish=lambda: setattr(self, "closed", True))

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.closed = True
        if self.fail == "cleanup":
            raise OSError("injected close response")

    def cancel_safe(self, timeout):
        self.operations.append(("cancel", timeout, None))


class CheckedRows:
    nested = False

    def __init__(self, request, description):
        self.producer = payloads.bind_native_projection(request, description)
        self.rows = self.batches = self.bytes = 0

    def accept(self, rows):
        values = tuple(
            tuple(
                scalar._value(value, bound)
                for value, bound in zip(row, self.producer.fields, strict=True)
            )
            for row in rows
        )
        self.rows += len(rows)
        self.batches += 1
        self.bytes += len(rows) * 16
        return values


def install(monkeypatch, connection):
    monkeypatch.setattr(pg, "_connect", lambda request: connection)
    monkeypatch.setattr(pg, "ExecutionPayloads", CheckedRows)
