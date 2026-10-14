"""Offline fixtures of the public execution tests; importing acquires nothing.

- The documented example project, relation and scripts and the documented
  server setup, read from docs/execution.md.
- A one-source project over the SQL emission JOIN witness, for either target.
- A protocol-level PostgreSQL stub on loopback: it answers an SSLRequest,
  reads the startup packet, asks for one authentication method and records
  whether the client sends anything back (a password, a hash or a token).
- A Linux inotify observer of the files a library opens in one directory.
- A `psycopg_c` copy that calls itself psycopg's binary implementation.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import re
import socket
import struct
import threading

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/execution.md"
SSL_REQUEST = 80877103
GSSENC_REQUEST = 80877104
# Authentication request codes of the PostgreSQL protocol.
AUTH = {"trust": 0, "password": 3, "md5": 5, "gss": 7, "sspi": 9}
IN_OPEN = 0x20


def _blocks(heading, languages):
    """The fenced blocks of one documented section, one per language."""
    text = DOCS.read_text(encoding="utf-8")
    section = text.split("\n## " + heading + "\n", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```(\w+)\n(.*?)```", section, re.S)
    found = dict(blocks)
    assert len(found) == len(blocks) and set(found) == set(languages), sorted(found)
    return found


def example_blocks():
    """The documented example: layout, project files, relation and script."""
    return _blocks("Example", ("text", "toml", "pietto", "json", "sql", "python"))


def bundle_blocks():
    """The documented bundle script."""
    return _blocks("Query bundles", ("python",))


def results_blocks():
    """The documented bounded-consumption script and its output."""
    return _blocks("Results", ("python", "text"))


def setup_blocks():
    """The documented server setup: role statements, the psql password
    commands and the pg_hba.conf lines."""
    return _blocks("Connection and trust requirements", ("sql", "psql", "conf"))


def statements(block):
    """The SQL statements of a documented block, in order."""
    return [s.strip() for s in block.split(";") if s.strip()]


def write_example(directory, *, relation="items"):
    """Write the documented project and its three scripts into `directory`;
    `relation` renames the physical relation only."""
    blocks = example_blocks()
    project = Path(directory) / "demo-exec"
    project.mkdir(parents=True)
    (project / "pietto.toml").write_text(blocks["toml"], encoding="utf-8")
    (project / "main.pietto").write_text(blocks["pietto"], encoding="utf-8")
    physical = '"namespace": "fixture", "name": "items"}'
    assert blocks["json"].count(physical) == 1
    contract = blocks["json"].replace(
        physical, '"namespace": "fixture", "name": "' + relation + '"}'
    )
    (project / "contract.json").write_text(contract, encoding="utf-8")
    (Path(directory) / "run_query.py").write_text(blocks["python"], encoding="utf-8")
    (Path(directory) / "bundle_query.py").write_text(
        bundle_blocks()["python"], encoding="utf-8"
    )
    (Path(directory) / "consume_query.py").write_text(
        results_blocks()["python"], encoding="utf-8"
    )
    return project


def write_join_witness(directory, target, body):
    """Write a project whose `body` follows the JOIN witness header and whose
    contract publishes only its `lhs` source; returns the project root."""
    import json

    import _pietto_sql_emission as probe

    item = probe.join_witness(target, body)
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    project = Path(directory)
    project.mkdir(parents=True)
    (project / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (project / "main.pietto").write_text(item["source"], encoding="utf-8")
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return project


# psycopg 3.3.5 hands every connection string, password included, to its
# selected implementation's `Conninfo.parse`; this copy records each one.
PSYCOPG_C = """
import pathlib
here = pathlib.Path(__file__).parent
(here / "imported").write_text("yes")
class pq:
    __impl__ = "binary"
    __build_version__ = 180006
    def version():
        return 180006
    class Conninfo:
        def parse(conninfo):
            with open(here / "received", "ab") as stream:
                stream.write(conninfo + b"\\n")
            return []
        def get_defaults():
            return []
    class PGconn:
        pass
    PGresult = Escaping = PGcancel = PGcancelConn = object
"""


def write_psycopg_c(directory):
    """Write the copy as the package `psycopg_c` into `directory` and return
    the package directory, where it records `imported` and `received`."""
    package = Path(directory) / "psycopg_c"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(PSYCOPG_C, encoding="utf-8")
    return package


class PostgresStub:
    """One loopback connection of a PostgreSQL server that never authenticates."""

    def __init__(self, *, ssl=b"N", auth="password"):
        self.ssl, self.auth = ssl, AUTH[auth]
        self.events = []
        self.startup = {}
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(20)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        self.thread.join(20)
        self.listener.close()
        assert not self.thread.is_alive(), "stub still serving"

    @staticmethod
    def _exact(connection, size):
        data = b""
        while len(data) < size:
            chunk = connection.recv(size - len(data))
            if not chunk:
                raise EOFError
            data += chunk
        return data

    def _serve(self):
        try:
            connection, _ = self.listener.accept()
        except OSError as error:
            self.events.append(("no_connection", type(error).__name__))
            return
        connection.settimeout(20)
        try:
            while True:
                length, code = struct.unpack("!ii", self._exact(connection, 8))
                body = self._exact(connection, length - 8)
                if code == SSL_REQUEST:
                    self.events.append(("ssl_request",))
                    connection.sendall(self.ssl)
                    if self.ssl == b"S":
                        # A TLS ClientHello follows; this stub speaks no TLS.
                        self.events.append(("tls_hello", bool(connection.recv(4096))))
                        return
                    continue
                if code == GSSENC_REQUEST:
                    self.events.append(("gssenc_request",))
                    connection.sendall(b"N")
                    continue
                fields = body.split(b"\0")
                startup = dict(zip(fields[0::2], fields[1::2]))
                self.startup = startup
                self.events.append(
                    (
                        "startup",
                        startup[b"user"].decode(),
                        startup[b"database"].decode(),
                    )
                )
                break
            if self.auth == AUTH["md5"]:
                connection.sendall(b"R" + struct.pack("!ii", 12, 5) + b"salt")
            else:
                connection.sendall(b"R" + struct.pack("!ii", 8, self.auth))
            if self.auth == AUTH["trust"]:
                connection.sendall(
                    b"S" + struct.pack("!i", 21) + b"server_version\x0018.6\x00"
                )
                connection.sendall(b"Z" + struct.pack("!i", 5) + b"I")
            self.events.append(("reply", self._exact(connection, 1).decode()))
        except (EOFError, OSError) as error:
            self.events.append(("closed", type(error).__name__))
        finally:
            connection.close()

    @property
    def replied(self):
        """Whether the client sent any message after the authentication request."""
        return any(event[0] == "reply" for event in self.events)


class OpenWatch:
    """Names of the files opened in one directory while the watch is active."""

    def __init__(self, directory):
        libc = ctypes.CDLL(None, use_errno=True)
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        assert self.fd >= 0, ctypes.get_errno()
        watch = libc.inotify_add_watch(self.fd, os.fsencode(directory), IN_OPEN)
        assert watch >= 0, ctypes.get_errno()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        os.close(self.fd)
        return False

    def opened(self):
        names = []
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return names
            offset = 0
            while offset < len(data):
                _wd, _mask, _cookie, size = struct.unpack_from("iIII", data, offset)
                name = data[offset + 16 : offset + 16 + size].rstrip(b"\0")
                names.append(os.fsdecode(name))
                offset += 16 + size
