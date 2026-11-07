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
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import socket
import ssl
import struct
import subprocess
import threading
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/execution.md"
SSL_REQUEST = 80877103
GSSENC_REQUEST = 80877104
# Authentication request codes of the PostgreSQL protocol.
AUTH = {"trust": 0, "password": 3, "md5": 5, "gss": 7, "sspi": 9}
IN_OPEN = 0x20
DECIMAL256 = Decimal("12345678901234567890123456789012345678901234567856.7890")


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


def write_nested_collect(directory, *, closed=False):
    """Write one real S12 Collect project and its exact emission document.

    The product fixture owns the source/contract construction.  This harness
    only keeps the resulting project bytes so the installed wheel compiles the
    same public live query that the PostgreSQL probe later executes.
    """
    import _pietto_results_nested as nested
    import _pietto_results_product as product

    project = Path(directory) / ("nested-closed" if closed else "nested-captured")
    project.parent.mkdir(parents=True, exist_ok=True)
    output = nested.collected(product, project, closed=closed)
    (project / "contract.json").write_bytes(output.artifact.request.accepted_bytes)
    return project


def write_nested_unnest(directory, name, leaves=None, *, decimal256=False):
    """A literal-oracle project, with only its actual physical sources."""
    import _pietto_execution_nested_oracle as oracle

    leaves = oracle.DEFAULT_LEAVES if leaves is None else oracle.leaves_of(leaves)
    return write_nested_program(
        directory, oracle.program(name, leaves).files, leaves, decimal256=decimal256
    )


def write_nested_program(
    directory, files, leaves, *, decimal256=False, relation_prefix=""
):
    """Materialize authored files with an exact physical fixture mapping."""
    import _pietto_execution_nested_oracle as oracle
    import _pietto_sql_nested_collect as collecting

    project = Path(directory)
    project.mkdir(parents=True)
    for name, contents in files:
        if decimal256:
            contents = contents.replace("Decimal(18, 4)", "Decimal(60, 4)")
            contents = contents.replace(
                'postgres.table("orders")', 'postgres.table("orders_decimal256")'
            )
        (project / name).write_text(contents, encoding="utf-8")
    text = "".join(contents for _, contents in files)
    contract = json.loads(collecting.oracle_contract())
    representations = {
        "Float": (
            {"kind": "pg_float8"},
            {"kind": "finite_float", "format": "binary64"},
        ),
        "Decimal": (
            {"kind": "pg_numeric", "precision": 18, "scale": 4},
            {"kind": "decimal", "precision": 18, "scale": 4},
        ),
        "Date": ({"kind": "pg_date"}, {"kind": "date"}),
        "Timestamp": (
            {"kind": "pg_timestamp", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "UUID": ({"kind": "pg_uuid"}, {"kind": "uuid", "encoding": "standard_bytes"}),
    }
    tables = oracle.seed("FULL", leaves)
    for source in contract["sources"]:
        table = tables[source["selector"]["name"]]
        fields = []
        for ordinal, column in enumerate(table.columns):
            representation = collecting._ORACLE_REPRESENTATIONS.get(column.kind)
            if representation is None:
                storage, domain = representations[column.kind]
            else:
                storage, domain = representation["storage"], representation["domain"]
            fields.append(
                {
                    "ordinal": ordinal,
                    "name": column.name,
                    "column": column.name,
                    "representation": {
                        "storage": storage,
                        "nullable": column.nullable,
                        "domain": domain,
                    },
                }
            )
        source["fields"] = fields
        if decimal256 and source["selector"]["name"] == "orders":
            source["relation"]["name"] = "orders_decimal256"
            for field in source["fields"]:
                if field["name"] == "price":
                    field["representation"] = {
                        "storage": {"kind": "pg_numeric", "precision": 60, "scale": 4},
                        "nullable": True,
                        "domain": {"kind": "decimal", "precision": 60, "scale": 4},
                    }
    for source in contract["sources"]:
        source["relation"]["name"] = relation_prefix + source["relation"]["name"]
    contract["sources"] = [
        source
        for source in contract["sources"]
        if f"from {source['selector']['name']}" in text
    ]
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return project


def write_composed_nested(directory, *, outer=False):
    from _pietto_plan_nested import (
        retained_unnest_sources,
        retained_outer_sources,
        retained_unnest_contract,
    )

    directory = Path(directory)
    directory.mkdir(parents=True)
    files = retained_outer_sources() if outer else retained_unnest_sources()
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    contract = retained_unnest_contract()
    prefix = "pietto_s16_outer_" if outer else "pietto_s16_"
    for source in contract["sources"]:
        source["relation"]["name"] = prefix + source["selector"]["name"]
    (directory / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return directory


def write_grouped_composed_nested(directory):
    directory = write_composed_nested(directory)
    parent = directory / "parent.pietto"
    parent.write_text(
        parent.read_text().replace(
            "        from orders\n        select:\n            id\n            total\n",
            "        from orders\n        group by customer_id\n        select:\n            id = customer_id\n            total = sum(total)\n",
        ),
        encoding="utf-8",
    )
    main = directory / "main.pietto"
    main.write_text(
        main.read_text()
        .replace("query result:", "query result(min_child: Int):")
        .replace(
            "    inner join tags on child.id == tags.id\n",
            "    inner join tags on child.id == tags.id\n    where child.id > min_child\n",
        ),
        encoding="utf-8",
    )
    contract_path = directory / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        }
    )
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return directory


def composed_setup_statements():
    statements = []
    for prefix in ("pietto_s16_", "pietto_s16_outer_"):
        statements.extend(
            (
                f"CREATE TABLE public.{prefix}rows (id bigint NOT NULL, other bigint)",
                f"CREATE TABLE public.{prefix}orders (id bigint NOT NULL, customer_id bigint NOT NULL, total bigint NOT NULL, created_at bigint NOT NULL)",
                f"CREATE TABLE public.{prefix}tags (id bigint NOT NULL, other bigint)",
            )
        )
    statements.extend(
        (
            "INSERT INTO public.pietto_s16_rows VALUES (1,10),(2,20)",
            "INSERT INTO public.pietto_s16_orders VALUES (1,1,10,1),(2,1,20,2),(3,2,30,3),(4,2,40,4)",
            "INSERT INTO public.pietto_s16_tags VALUES (1,NULL),(2,NULL),(3,NULL)",
            "INSERT INTO public.pietto_s16_outer_orders VALUES (1,1,10,1),(2,1,20,2)",
            "INSERT INTO public.pietto_s16_outer_tags VALUES (7,NULL)",
        )
    )
    return tuple(statements)


def _oracle_sql_value(item):
    if item is None:
        return "NULL"
    if type(item) is bool:
        return "TRUE" if item else "FALSE"
    if type(item) is int:
        return str(item)
    if type(item) is float:
        # Parse the authored float directly, retaining negative zero.
        return "'" + repr(item) + "'::double precision"
    if type(item) is Decimal:
        return str(item)
    if type(item) is datetime:
        return "TIMESTAMP '" + item.isoformat(sep=" ") + "'"
    if type(item) is date:
        return "DATE '" + item.isoformat() + "'"
    if type(item) is UUID:
        return "'" + str(item) + "'::uuid"
    if type(item) is str:
        return "'" + item.replace("'", "''") + "'"
    raise ValueError("Unnest native fixture leaf")


def _oracle_table_statements(tables, prefix=""):
    result = []
    for name, table in tables.items():
        columns = [
            f'"{column.name}" '
            + {
                "Int": "int8",
                "Bool": "boolean",
                "Text": 'text COLLATE "C"',
                "Float": "double precision",
                "Decimal": "numeric(18,4)",
                "Date": "date",
                "Timestamp": "timestamp(6)",
                "UUID": "uuid",
            }[column.kind]
            + ("" if column.nullable else " NOT NULL")
            for column in table.columns
        ]
        result.append(
            f'CREATE TABLE public."{prefix}{name}" (' + ",".join(columns) + ")"
        )
        result.append(
            f'INSERT INTO public."{prefix}{name}" VALUES '
            + ",".join(
                "(" + ",".join(_oracle_sql_value(cell) for cell in row) + ")"
                for row in table.rows
            )
        )
    return result


def nested_oracle_setup_statements():
    import _pietto_execution_nested_oracle as oracle

    return tuple(
        statement
        for dataset in ("MINIMAL", "FULL")
        for statement in _oracle_table_statements(
            oracle.seed(dataset, oracle.LEAVES), "pietto_s21_" + dataset.lower() + "_"
        )
    )


def unnest_setup_statements():
    """Populate the complete literal-oracle FULL seed in the owned PG fixture."""
    import _pietto_execution_nested_oracle as oracle

    tables = oracle.seed("FULL", oracle.LEAVES)
    result = _oracle_table_statements(
        {name: tables[name] for name in ("customers", "orders")}
    )
    decimal_tables = oracle.seed("FULL", ("Int", "Decimal"))
    orders = decimal_tables["orders"]
    columns = []
    for column in orders.columns:
        kind = (
            "numeric(60,4)"
            if column.name == "price"
            else {"Int": "int8", "Decimal": "numeric(18,4)"}[column.kind]
        )
        columns.append(
            f'"{column.name}" ' + kind + ("" if column.nullable else " NOT NULL")
        )
    rows = []
    for row in orders.rows:
        values = list(row)
        if values[0] == 23:
            values[orders.columns.index(orders.column("price"))] = DECIMAL256
        rows.append("(" + ",".join(_oracle_sql_value(cell) for cell in values) + ")")
    result.append('CREATE TABLE public."orders_decimal256" (' + ",".join(columns) + ")")
    result.append('INSERT INTO public."orders_decimal256" VALUES ' + ",".join(rows))
    return tuple(result)


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


def tls_material(directory):
    """Two test CAs and four server certificates made by the host `openssl`,
    all signed by `ca` (`other_ca` signed none): `server` has the SAN
    127.0.0.1, `elsewhere` only the SAN elsewhere.invalid, and the common name
    127.0.0.1 is in `common` beside only that DNS SAN and in `other_ip` beside
    only the SAN 127.0.0.2. Returns the PEM paths."""
    directory = Path(directory)

    def openssl(*arguments):
        subprocess.run(
            ("openssl", *arguments),
            cwd=directory,
            check=True,
            capture_output=True,
            timeout=30,
        )

    key = ("-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes")
    for ca in ("ca", "other_ca"):
        openssl(
            *("req", "-x509", *key, "-sha256", "-days", "2"),
            *("-subj", "/CN=pietto-test-" + ca),
            *("-addext", "basicConstraints=critical,CA:true"),
            *("-keyout", ca + "-key.pem", "-out", ca + ".pem"),
        )
    for name, common, san in (
        ("server", "server", "IP:127.0.0.1"),
        ("elsewhere", "elsewhere", "DNS:elsewhere.invalid"),
        ("common", "127.0.0.1", "DNS:elsewhere.invalid"),
        ("other_ip", "127.0.0.1", "IP:127.0.0.2"),
    ):
        openssl(
            *("req", "-new", *key, "-sha256", "-subj", "/CN=" + common),
            *("-addext", "subjectAltName=" + san),
            *("-keyout", name + "-key.pem", "-out", name + ".csr"),
        )
        openssl(
            *("x509", "-req", "-in", name + ".csr", "-CA", "ca.pem"),
            *("-CAkey", "ca-key.pem", "-CAcreateserial", "-days", "2"),
            *("-sha256", "-copy_extensions", "copy", "-out", name + ".pem"),
        )
    return {
        name: directory / (name + ".pem")
        for name in ("ca", "other_ca", "server", "elsewhere", "common", "other_ip")
    }


def server_tls(material, name):
    """A TLS server context that presents the certificate `name`."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(material[name], material[name].with_name(name + "-key.pem"))
    return context


class PostgresStub:
    """One loopback connection of a PostgreSQL server that never authenticates;
    with a `tls` server context it accepts TLS and reads the startup through it."""

    def __init__(self, *, ssl=b"N", auth="password", tls=None):
        self.ssl, self.auth, self.tls = ssl, AUTH[auth], tls
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
                    if self.ssl == b"S" and self.tls is not None:
                        try:
                            connection = self.tls.wrap_socket(
                                connection, server_side=True
                            )
                        except OSError as error:
                            self.events.append(("tls_failed", type(error).__name__))
                            return
                        self.events.append(("tls", connection.version()))
                    elif self.ssl == b"S":
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
