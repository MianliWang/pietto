"""Installed-consumer and real PostgreSQL 18.6 witnesses of the public
execution alpha; importing acquires nothing.

Run explicitly where the premises hold (Validation Runner Acceptance R4 row 7
for both families; row 4, Docker with the pinned image, for `postgres`):

    python tests/_pietto_execution_api_probe.py consumer --directory NEW \\
        --wheel WHEEL --interpreter CPYTHON [--house DIR] [--cache DIR]
    python tests/_pietto_execution_api_probe.py postgres --directory NEW \\
        --wheel WHEEL --interpreter CPYTHON [--house DIR] [--cache DIR]
    python tests/_pietto_execution_api_probe.py check --report REPORT

Each family materializes fresh prefixes of the exact wheel from the verified
wheelhouse of the lock's artifacts (the S18 recipe; `--house` reuses an
existing one), runs the documented example and the case workers there as
fresh `-I -B` interpreters with a clean environment (no forced
`PSYCOPG_IMPL`), the configuration and passwords on standard input and an
unrelated working directory, writes raw facts to `report.json` and exits
non-zero when the independent checker `_pietto_execution_api_check` rejects
them. The `postgres` fixture follows the documented server setup: the
documented relation, reader role and `\\password` exchange, TLS on, and the
documented `hostssl`/`host` pg_hba.conf lines (database and client address
replaced, since Docker's gateway rather than 127.0.0.1 reaches the server).
Ordinary pytest never runs a family; it runs the consumer cases against the
checkout and the checker.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.execution-api-witness.v1"
AMBIENT = (
    "PGHOST",
    "PGPASSWORD",
    "PGSERVICE",
    "SSLKEYLOGFILE",
    "OPENSSL_CONF",
    "OPENSSL_MODULES",
)
ROWS = ((0, "zero"), (1, "one"), (2, "two"), (2, "two"), (3, "three"), (5, "five"))
WIDE_ROWS = ((2, "two"), (1000, "out of domain"))
# Roles of the PostgreSQL fixture and the pg_hba.conf method each one meets.
ROLES = {
    "pietto_reader": "scram-sha-256",
    "pietto_trust": "trust",
    "pietto_cleartext": "password",
    "pietto_md5": "md5",
}


def hba():
    """pg_hba.conf of the fixture, first match wins: the refused methods, the
    documented reader lines with the database and the client address
    replaced, then the fixture's own manager."""
    from _pietto_execution_api import setup_blocks

    reader: list[str] = []
    for line in setup_blocks()["conf"].splitlines():
        if line.strip() and not line.startswith("#"):
            kind, _database, user, _address, method = line.split()
            documented = " ".join((kind, "phase66", user, "all", method))
            if documented not in reader:
                reader.append(documented)
    return (
        "local all all trust",
        "host all pietto_trust all trust",
        "host all pietto_cleartext all password",
        "host all pietto_md5 all md5",
        *reader,
        "host all pietto_manager all scram-sha-256",
    )


WORKER = r"""
import gc, json, os, sys, threading, time, warnings
from pathlib import Path
config = json.loads(sys.stdin.readline())
for entry in reversed(config.get("path", ())):
    sys.path.insert(0, entry)
case = config["case"]
result = {"case": case}
if case == "identity":
    from importlib.metadata import version
    from pietto._project.project_compiled_loading import semantic_build_identity
    result.update(identity=semantic_build_identity(),
        metadata=version("antlr4-python3-runtime"))
    print(json.dumps(result))
    raise SystemExit(0)
DRIVERS = {"psycopg", "psycopg_binary", "pyarrow"}
def loaded():
    return sorted({m.split(".")[0] for m in sys.modules} & DRIVERS)
import pietto.execution as pe
result["after_import"] = loaded()
password = config["password"]
def facts(outcome):
    p = outcome.primary
    return {"end": outcome.end, "source": outcome.source,
        "transaction": outcome.transaction, "delivery": outcome.delivery,
        "cleanup": outcome.cleanup, "remote": outcome.remote_source_use_end,
        "rows": outcome.rows, "batches": outcome.batches,
        "primary": None if p is None else [p.code, p.detail, p.phase, p.sqlstate, p.cause],
        "cleanup_failures": [[f.code, f.phase, f.cause] for f in outcome.cleanup_failures]}
def effects():
    roots = {"cwd": os.getcwd(), "home": os.environ.get("HOME", ""),
        "tmp": os.environ.get("TMPDIR", "")}
    return {"threads": sorted(t.name for t in threading.enumerate()),
        "jobs": sorted(m for m in sys.modules if m.startswith("pietto._project.project_job")),
        "files": {name: sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))
            for name, root in roots.items() if root}}
def refusal(error):
    return {"code": error.code, "detail": error.detail, "cause": error.failure.cause,
        "sqlstate": error.failure.sqlstate, "shown": password in str(error),
        "chained": error.__cause__ is not None or error.__context__ is not None,
        "outcome": None if error.outcome is None else facts(error.outcome)}
query = pe.compile_query(config["project"], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json",
    literal_policy=config.get("policy", "preserve"))
access = pe.PostgresAccess(config.get("host", "127.0.0.1"), config["port"],
    config.get("database", "phase66"), config.get("user", "pietto_reader"),
    password, config.get("sslmode", "require"))
premise = pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
limits = pe.ExecutionLimits(**config.get("limits", {}))
def attempt(**changes):
    arguments = dict(route="postgres_rows", access=access, premise=premise,
        limits=limits)
    arguments.update(changes)
    return pe.execute(query, **arguments)
handle = attempt()
result["unopened"] = [loaded(), handle.outcome.end, password in repr(handle)]
if case == "requests":
    refusals = {}
    for name, changes in (("premise_none", {"premise": None}),
            ("route_adbc", {"route": "postgres_adbc"}),
            ("socket_host", {"access": pe.PostgresAccess("/var/run/postgresql",
                5432, "phase66", "pietto_reader", password)})):
        try:
            attempt(**changes)
            refusals[name] = None
        except pe.RequestRejected as error:
            refusals[name] = [error.code, error.detail, password in str(error)]
    try:
        pe.execute("SELECT * FROM fixture.items", route="postgres_rows",
            access=access, premise=premise)
        refusals["sql_text"] = None
    except pe.RequestRejected as error:
        refusals["sql_text"] = [error.code, error.detail, False]
    result["refusals"] = refusals
elif case == "refused":
    try:
        with handle:
            result["opened"] = True
    except pe.AttemptFailed as error:
        result.update(refusal(error))
    result["after_open"] = loaded()
    psycopg = sys.modules.get("psycopg")
    result["psycopg_file"] = getattr(psycopg, "__file__", None)
elif case == "rows":
    import pyarrow as pa
    rows = []
    result["before"] = effects()
    with handle:
        for batch in handle:
            with batch:
                rows.extend(pa.record_batch(batch).to_pylist())
    result.update(rows=sorted([r["id"], r["label"]] for r in rows),
        outcome=facts(handle.outcome), after=effects())
elif case == "early_stop":
    result["before"] = effects()
    with handle:
        first = next(handle)
        result["first_rows"] = first.num_rows
        first.close()
    result.update(outcome=facts(handle.outcome), after=effects())
elif case == "failure":
    started = time.monotonic()
    try:
        with handle:
            result["opened"] = time.monotonic() - started
            for batch in handle:
                batch.close()
        result["completed"] = True
    except pe.AttemptFailed as error:
        result.update(refusal(error))
    result["seconds"] = time.monotonic() - started
elif case == "dropped":
    handle.__enter__()
    next(handle).close()
    attempt_id = handle.attempt
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del handle
        gc.collect()
    result["warnings"] = [[w.message.code, w.message.outcome.end,
        w.message.outcome.attempt == attempt_id] for w in caught
        if isinstance(w.message, pe.UnclosedHandleWarning)]
    result["dropped_at"] = time.monotonic()
print(json.dumps(result), flush=True)
"""

SHADOW = """
import pathlib
pathlib.Path(__file__).with_name("imported").write_text("yes")
class pq:
    __impl__ = "binary"
def connect(**fields):
    pathlib.Path(__file__).with_name("connected").write_text("yes")
    raise RuntimeError("shadow")
"""
FAKE_METADATA = "Metadata-Version: 2.1\nName: antlr4-python3-runtime\nVersion: 9.9.9\n"


def environment(extra=None):
    """A worker environment without ambient interpreter, project or connection
    inputs; `extra` sets exactly the variables a case examines."""
    from _pietto_target_conformance_resources import clean_environment

    env = {
        key: value
        for key, value in clean_environment().items()
        if key not in {"VIRTUAL_ENV", "PSYCOPG_IMPL"}
        and not key.startswith(("PYTHON", "UV_", "KRB5"))
    }
    env["PYTHONNOUSERSITE"] = "1"
    env.update(extra or {})
    return env


def run(python, arguments, *, cwd, stdin="", extra=None, isolated=True, seconds=120):
    flags = ("-I", "-B") if isolated else ("-E", "-s", "-B")
    started = time.monotonic()
    completed = subprocess.run(
        [str(python), *flags, *arguments],
        cwd=cwd,
        env=environment(extra),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=seconds,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-65536:],
        "stderr": completed.stderr[-16384:],
        "seconds": time.monotonic() - started,
    }


def case(python, cwd, config, **options):
    """One fresh worker; its last stdout line is the case's JSON result."""
    record = run(
        python, ["-c", WORKER], cwd=cwd, stdin=json.dumps(config) + "\n", **options
    )
    lines = record["stdout"].strip().splitlines()
    record["result"] = (
        json.loads(lines[-1]) if record["returncode"] == 0 and lines else None
    )
    record.pop("stdout")
    return record


@contextmanager
def sentinel():
    """A loopback port that only records whether anything connected."""
    listener = socket.create_server(("127.0.0.1", 0))
    listener.setblocking(False)
    state = {"port": listener.getsockname()[1]}

    def connected():
        try:
            listener.accept()[0].close()
        except BlockingIOError:
            return False
        return True

    state["connected"] = connected
    try:
        yield state
    finally:
        listener.close()


def consumer_cases(python, work, *, path=()):
    """The installed-consumer laws that need no database: imports and an
    unopened execute load nothing and connect nowhere; request refusals;
    refused environment before the driver (and before PyArrow can open the
    key log); a shadowing psycopg copy; the ANTLR label under a stray
    dist-info in the working directory. `path` puts a checkout first."""
    from _pietto_execution_api import write_example

    work.mkdir(parents=True)
    project = write_example(work)
    password = secrets.token_hex(12)
    base = {"project": str(project), "password": password, "path": list(path)}
    facts = {}
    with sentinel() as listener:
        facts["imports"] = case(
            python,
            work,
            {**base, "case": "requests", "port": listener["port"]},
            extra={"PGHOST": "127.0.0.1", "PGPORT": str(listener["port"])},
        )
        facts["imports"]["connected"] = listener["connected"]()
    ambient = {}
    for name in AMBIENT:
        values = {
            "SSLKEYLOGFILE": str(work / "keylog"),
            "OPENSSL_CONF": str(work / "empty.cnf"),
            "OPENSSL_MODULES": str(work),
        }
        (work / "empty.cnf").write_text("")
        with sentinel() as listener:
            record = case(
                python,
                work,
                {**base, "case": "refused", "port": listener["port"]},
                extra={name: values.get(name, "value-never-read")},
            )
            record["connected"] = listener["connected"]()
        record["keylog_created"] = (work / "keylog").exists()
        ambient[name] = record
    facts["ambient"] = ambient
    shadow = work / "shadow" / "psycopg"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text(SHADOW)
    with sentinel() as listener:
        record = case(
            python,
            work,
            {
                **base,
                "case": "refused",
                "port": listener["port"],
                "path": [*path, str(shadow.parent)],
            },
        )
        record["connected"] = listener["connected"]()
    record["shadow"] = str(shadow / "__init__.py")
    record["shadow_imported"] = (shadow / "imported").exists()
    record["shadow_connected"] = (shadow / "connected").exists()
    facts["shadow"] = record
    stray = work / "stray"
    info = stray / "antlr4_python3_runtime-9.9.9.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(FAKE_METADATA)
    (info / "RECORD").write_text("antlr4/__init__.py,,\n")
    facts["identity"] = {
        where: case(
            python,
            cwd,
            {**base, "case": "identity", "port": 0},
            isolated=False,
        )
        for where, cwd in (("clean", work), ("stray", stray))
    }
    return facts


def context(wheel):
    return {
        "probe": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "wheel": Path(wheel).name,
        "wheel_sha256": hashlib.sha256(Path(wheel).read_bytes()).hexdigest(),
        "docs": hashlib.sha256((ROOT / "docs/execution.md").read_bytes()).hexdigest(),
    }


def prefixes(directory, recipes, *, wheel, interpreter, house_root, cache):
    """Fresh prefixes of the exact wheel, one normal resolver command each."""
    import _pietto_phase68_slice18_probe as s18

    house, constraints, entries = s18.wheelhouse(house_root)
    cache = cache or directory / "uv-cache"
    log = directory / "install.log"
    pythons: dict[str, Path] = {}
    records: dict[str, Any] = {"wheelhouse": [e["file"] for e in entries]}
    for recipe, extras in recipes.items():
        prefix = directory / ("prefix-" + recipe)
        records[recipe] = s18.materialize(
            prefix, interpreter, wheel, extras, house, constraints, cache, log
        )
        pythons[recipe] = prefix / "bin/python"
        described = run(pythons[recipe], ["-c", DESCRIBE], cwd=directory)
        records[recipe]["python"] = (
            json.loads(described["stdout"]) if described["returncode"] == 0 else None
        )
    return pythons, records


DESCRIBE = (
    "import json, platform; print(json.dumps([platform.python_implementation(),"
    " platform.python_version(), platform.system(), platform.machine()]))"
)


def consumer(directory, *, wheel, interpreter, house_root=None, cache=None):
    directory.mkdir(mode=0o700)
    started = time.monotonic()
    pythons, install = prefixes(
        directory,
        {"core": (), "execute-postgres": ("execute-postgres",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    report = {
        "format": FORMAT,
        "family": "consumer",
        "context": context(wheel),
        "install": install,
    }
    from _pietto_execution_api import write_example

    core = directory / "core"
    core.mkdir()
    project = write_example(core)
    with sentinel() as listener:
        report["core"] = case(
            pythons["core"],
            core,
            {
                "case": "refused",
                "project": str(project),
                "password": secrets.token_hex(12),
                "port": listener["port"],
            },
        )
        report["core"]["connected"] = listener["connected"]()
    report["cases"] = consumer_cases(pythons["execute-postgres"], directory / "cases")
    report["seconds"] = time.monotonic() - started
    return finish(directory, report)


def statements(passwords):
    """The fixture: the documented relation and reader role (database `app`
    replaced), an out-of-domain relation, the reader without a server-side
    statement limit, and one role per refused authentication method (md5
    hashed as md5). The reader's password is set as `\\password` sets it."""
    from _pietto_execution_api import example_blocks, setup_blocks
    from _pietto_execution_api import statements as documented

    wide = ",".join(f"({i},'{label}')" for i, label in WIDE_ROWS)
    role = documented(setup_blocks()["sql"])
    database = [s for s in role if " DATABASE app " in s]
    assert len(database) == 1, role
    return (
        *documented(example_blocks()["sql"]),
        'CREATE TABLE fixture.items_wide (item_id int8 NOT NULL, item_label text COLLATE "C" NOT NULL)',
        "INSERT INTO fixture.items_wide VALUES " + wide,
        *(s.replace(" DATABASE app ", " DATABASE phase66 ") for s in role),
        "GRANT SELECT ON fixture.items_wide TO pietto_reader",
        # Only Pietto's own statement limit applies to the reader's sessions.
        "ALTER ROLE pietto_reader SET statement_timeout = 0",
        "CREATE ROLE pietto_trust LOGIN",
        f"CREATE ROLE pietto_cleartext LOGIN PASSWORD '{passwords['pietto_cleartext']}'",
        "SET password_encryption = 'md5'",
        f"CREATE ROLE pietto_md5 LOGIN PASSWORD '{passwords['pietto_md5']}'",
        "RESET password_encryption",
    )


def set_password(manager, role, password):
    """The documented psql commands: each SET, then what `\\password` sends:
    libpq computes the verifier under the session's password_encryption and
    only the verifier reaches the server, in one ALTER USER statement."""
    from psycopg import sql

    from _pietto_execution_api import setup_blocks

    *settings, command = setup_blocks()["psql"].splitlines()
    assert command == "\\password " + role, command
    assert settings and all(
        line.startswith("SET ") and line.endswith(";") for line in settings
    ), settings
    assert settings[-1] == "SET password_encryption = 'scram-sha-256';", settings
    for line in settings:
        with manager.cursor() as cursor:
            cursor.execute(line.rstrip(";"))
    verifier = manager.pgconn.encrypt_password(password.encode(), role.encode())
    statement = sql.SQL("ALTER USER {} PASSWORD {}").format(
        sql.Identifier(role), sql.Literal(verifier.decode())
    )
    with manager.cursor() as cursor:
        cursor.execute(statement)


def rows(connection, sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [list(row) for row in cursor.fetchall()]


def prepare_server(resources, passwords):
    """Create the fixture as documented, turn TLS on (the S09 self-signed
    fixture certificate), replace pg_hba.conf and record what the server
    reports about them (no password or hash)."""
    from _pietto_phase68_slice9_probe import enable_fixture_tls

    manager = resources.manager
    for sql in statements(passwords):
        with manager.cursor() as cursor:
            cursor.execute(sql)
    set_password(manager, "pietto_reader", passwords["pietto_reader"])
    enable_fixture_tls(resources)
    (hba_file,) = rows(manager, "SHOW hba_file")[0]
    lines = ",".join(f"({n},'{line}')" for n, line in enumerate(hba()))
    with manager.cursor() as cursor:
        cursor.execute(
            f"COPY (SELECT line FROM (VALUES {lines}) AS v(n, line) ORDER BY n)"
            f" TO '{hba_file}'"
        )
        cursor.execute("SELECT pg_reload_conf()")
    time.sleep(2)
    return {
        "version": rows(manager, "SELECT current_setting('server_version_num')")[0][0],
        "ssl": rows(manager, "SHOW ssl")[0][0],
        "password_encryption": rows(manager, "SHOW password_encryption")[0][0],
        "reader_settings": rows(
            manager, "SELECT rolconfig FROM pg_roles WHERE rolname = 'pietto_reader'"
        )[0][0],
        "hba": rows(
            manager,
            "SELECT type, user_name, auth_method, error FROM pg_hba_file_rules"
            " ORDER BY rule_number",
        ),
        "hashes": rows(
            manager,
            "SELECT rolname::text, rolpassword LIKE 'SCRAM-SHA-256$%',"
            " rolpassword LIKE 'md5%' FROM pg_authid"
            " WHERE rolname LIKE 'pietto\\_%' AND rolname <> 'pietto_manager'"
            " ORDER BY rolname",
        ),
    }


def sessions(manager, user):
    return rows(
        manager,
        "SELECT count(*) FROM pg_stat_activity WHERE usename = '"
        + user
        + "' AND pid <> pg_backend_pid()",
    )[0][0]


def dropped(python, cwd, config, manager):
    """A worker that drops its open handle: the session while the worker
    still runs (and its TLS as the server sees it), the exit delay the
    deadline timer causes, and the session once the process is gone."""
    process = subprocess.Popen(
        [str(python), "-I", "-B", "-c", WORKER],
        cwd=cwd,
        env=environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(120, process.kill)
    watchdog.start()
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps(config) + "\n")
        process.stdin.close()
        line = process.stdout.readline()
        during = sessions(manager, config["user"])
        tls = rows(
            manager,
            "SELECT s.ssl, s.version FROM pg_stat_activity a JOIN pg_stat_ssl s"
            " ON s.pid = a.pid WHERE a.usename = '"
            + config["user"]
            + "' AND a.pid <> pg_backend_pid()",
        )
        process.wait()
        ended = time.monotonic()
    finally:
        watchdog.cancel()
    after = None
    for _ in range(20):
        after = sessions(manager, config["user"])
        if after == 0:
            break
        time.sleep(0.5)
    result = json.loads(line) if line.strip() else None
    return {
        "returncode": process.returncode,
        "result": result,
        "during": during,
        "tls": tls,
        "exit_delay": None if result is None else ended - result["dropped_at"],
        "after": after,
    }


def postgres(directory, *, wheel, interpreter, house_root=None, cache=None):
    import _pietto_target_conformance_resources as resources_module
    from _pietto_execution_api import write_example

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    pythons, install = prefixes(
        directory,
        {"execute-postgres": ("execute-postgres",)},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    python = pythons["execute-postgres"]
    report = {
        "format": FORMAT,
        "family": "postgres",
        "context": context(wheel),
        "install": install,
    }
    work = directory / "work"
    work.mkdir()
    project = write_example(work)
    wide = write_example(work / "wide", relation="items_wide")
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    (directory / "resources").mkdir()
    resources = resources_module.Resources(
        "postgres", pins["targets"]["postgres"], directory / "resources"
    )
    passwords = {role: secrets.token_hex(16) for role in ROLES}
    quiet = {}
    for name in ("home", "tmp"):
        (directory / name).mkdir(mode=0o700)
        quiet["HOME" if name == "home" else "TMPDIR"] = str(directory / name)
    try:
        resources.acquire()
        manager = resources.manager
        report["server"] = prepare_server(resources, passwords)
        report["image"] = resources.runtime_image_id
        port = resources.port
        base = {"project": str(project), "port": port, "user": "pietto_reader"}
        reader = {**base, "password": passwords["pietto_reader"]}
        secret = passwords["pietto_reader"]
        # As written (TLS, channel binding), then the loopback exception.
        report["example"] = example(python, work, port, secret)
        report["example_loopback"] = example(python, work, port, secret, "disable")
        report["bind_safe"] = case(
            python, work, {**reader, "case": "rows", "policy": "bind-safe"}, extra=quiet
        )
        report["early_stop"] = case(
            python,
            work,
            {**reader, "case": "early_stop", "limits": {"batch_rows": 1}},
            extra=quiet,
        )
        report["result_check"] = case(
            python, work, {**reader, "case": "failure", "project": str(wide)}
        )
        report["authentication"] = {
            role: case(
                python,
                work,
                {**base, "case": "failure", "user": role, "password": passwords[role]},
            )
            for role in ROLES
            if role != "pietto_reader"
        }
        with manager.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute("LOCK TABLE fixture.items IN ACCESS EXCLUSIVE MODE")
        try:
            # The deadline is far beyond 10 s and the role has no server-side
            # limit, so only Pietto's own statement limit can end it.
            report["statement_timeout"] = case(
                python,
                work,
                {**reader, "case": "failure", "limits": {"seconds": 60}},
                seconds=120,
            )
        finally:
            with manager.cursor() as cursor:
                cursor.execute("ROLLBACK")
        report["dropped"] = dropped(
            python,
            work,
            {**reader, "case": "dropped", "limits": {"seconds": 4}},
            manager,
        )
    finally:
        report["cleanup"] = resources.cleanup()
    report["seconds"] = time.monotonic() - started
    return finish(directory, report)


def example(python, cwd, port, password, *sslmode):
    """The documented script, run from the directory that holds the project."""
    record = run(
        python,
        ["run_query.py", "127.0.0.1", str(port), "phase66", "pietto_reader", *sslmode],
        cwd=cwd,
        stdin=password + "\n",
    )
    record["shown"] = password in record["stdout"]
    return record


def finish(directory, report):
    import _pietto_execution_api_check as check

    path = directory / "report.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return check.check(report)


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("family", choices=("consumer", "postgres", "check"))
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--interpreter", type=Path)
    parser.add_argument("--house", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]
    if args.family == "check":
        import _pietto_execution_api_check as check

        verdict = check.check(json.loads(args.report.read_text()))
    else:
        if None in (args.directory, args.wheel, args.interpreter):
            parser.error("--directory, --wheel and --interpreter are required")
        run_family = consumer if args.family == "consumer" else postgres
        verdict = run_family(
            args.directory,
            wheel=args.wheel,
            interpreter=args.interpreter,
            house_root=args.house,
            cache=args.cache,
        )
    print(json.dumps(verdict, sort_keys=True))


if __name__ == "__main__":
    main()
