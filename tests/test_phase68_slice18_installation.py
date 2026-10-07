"""S18 installable route selections and the selected-dependency boundary.

Core (no Arrow, no database, no network): exact extras, lock and per-selection
closures, artifact METADATA with requirement extras, the pinned-driver decision
table (CONTROLLED: the distribution/version and module lookups are replaced per
case), the runtime refusing an unavailable selected route before any admission
or worker, a direct owner refusing before it connects, and lazy imports. Real
clean resolver installations, installed origins, archived runtimes and the
native handoff come from scripts/phase68_slice18_probe.py.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import tomllib
from types import SimpleNamespace

import pytest

import _pietto_phase68_slice12_probe as s12
import _pietto_phase68_slice17_probe as s17
from _pietto_phase68_slice11_probe import compiled_template, qualified
from test_phase11_packaging_smoke import REPO_ROOT, _metadata_bytes, smoke
from test_phase67_slice13_optional_arrow_extra import _artifact, _inspect
from pietto._project import project_execution as ex
from pietto._project import project_execution_mysql_native as mysql
from pietto._project import project_execution_postgres as postgres
from pietto._project import project_execution_postgres_adbc_native as adbc
from pietto._project import project_job_runtime as rt
from pietto._project.project_job_workspace import JobStoreError

# The selections chosen by the S18 dispatch, stated independently of pyproject.
EXTRAS = {
    "arrow": ["pyarrow==25.0.1"],
    "execute-postgres": ["pyarrow==25.0.1", "psycopg[binary]==3.3.5"],
    "execute-mysql": ["pyarrow==25.0.1", "mysql-connector-python==26.7.0"],
    "execute-postgres-adbc": [
        "pyarrow==25.0.1",
        "adbc-driver-postgresql==1.12.0",
        "adbc-driver-manager==1.12.0",
    ],
}
ROUTES = ("execute-postgres", "execute-mysql", "execute-postgres-adbc")
CORE = {"antlr4-python3-runtime==4.13.2"}
ARROW = CORE | {"pyarrow==25.0.1"}
POSTGRES = ARROW | {
    "psycopg==3.3.5",
    "psycopg-binary==3.3.5 ; implementation_name != 'pypy'",
    "typing-extensions==4.15.0 ; python_full_version < '3.13'",
    "tzdata==2026.4 ; sys_platform == 'win32'",
}
MYSQL = ARROW | {"mysql-connector-python==26.7.0"}
ADBC = ARROW | {
    "adbc-driver-manager==1.12.0",
    "adbc-driver-postgresql==1.12.0",
    "importlib-resources==6.5.2",
    "typing-extensions==4.15.0",
}
CLOSURES = {
    (): CORE,
    ("arrow",): ARROW,
    ("execute-postgres",): POSTGRES,
    ("execute-mysql",): MYSQL,
    ("execute-postgres-adbc",): ADBC,
    # psycopg's conditional typing-extensions edge is absorbed by ADBC's own.
    ROUTES: (POSTGRES | MYSQL | ADBC)
    - {"typing-extensions==4.15.0 ; python_full_version < '3.13'"},
}
DRIVER_MODULES = (
    "psycopg",
    "psycopg_binary",
    "mysql",
    "adbc_driver_manager",
    "adbc_driver_postgresql",
    "pyarrow",
)


def test_selections_are_exactly_the_dispatch_extras_and_core_is_unchanged():
    document = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project = document["project"]
    assert (project["name"], project["version"], project["requires-python"]) == (
        "pietto",
        "0.1.0",
        ">=3.12",
    )
    assert project["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["optional-dependencies"] == EXTRAS
    assert project["scripts"] == {"pietto": "pietto.cli:main"}
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
    packages = {p["name"]: p for p in lock["package"]}
    package = packages["pietto"]
    assert package["dependencies"] == [{"name": "antlr4-python3-runtime"}]
    assert package["optional-dependencies"] == {
        "arrow": [{"name": "pyarrow"}],
        "execute-mysql": [{"name": "mysql-connector-python"}, {"name": "pyarrow"}],
        "execute-postgres": [
            {"name": "psycopg", "extra": ["binary"]},
            {"name": "pyarrow"},
        ],
        "execute-postgres-adbc": [
            {"name": "adbc-driver-manager"},
            {"name": "adbc-driver-postgresql"},
            {"name": "pyarrow"},
        ],
    }
    assert package["metadata"]["provides-extras"] == list(EXTRAS)
    assert {
        name: packages[name]["version"]
        for name in (
            "adbc-driver-manager",
            "adbc-driver-postgresql",
            "antlr4-python3-runtime",
            "importlib-resources",
            "mysql-connector-python",
            "psycopg",
            "psycopg-binary",
            "pyarrow",
            "ruff",
            "typing-extensions",
        )
    } == {
        "adbc-driver-manager": "1.12.0",
        "adbc-driver-postgresql": "1.12.0",
        "antlr4-python3-runtime": "4.13.2",
        "importlib-resources": "6.5.2",
        "mysql-connector-python": "26.7.0",
        "psycopg": "3.3.5",
        "psycopg-binary": "3.3.5",
        "pyarrow": "25.0.1",
        "ruff": "0.16.10",
        "typing-extensions": "4.15.0",
    }
    edges = {
        name: [d["name"] for d in packages[name].get("dependencies", ())]
        for name in ("adbc-driver-manager", "adbc-driver-postgresql")
    }
    assert edges == {
        "adbc-driver-manager": ["typing-extensions"],
        "adbc-driver-postgresql": ["adbc-driver-manager", "importlib-resources"],
    }
    # The tested ADBC Linux wheels keep their recorded S01 URL/hash provenance.
    premise = (REPO_ROOT / "ci/phase68-executor-premise-requirements.txt").read_text()
    for name in ("adbc-driver-postgresql", "adbc-driver-manager"):
        found = re.search(
            rf"^{name} @ (\S+)#sha256=([0-9a-f]{{64}})$", premise, re.MULTILINE
        )
        assert found is not None
        (wheel,) = [w for w in packages[name]["wheels"] if w["url"] == found[1]]
        assert wheel["hash"] == "sha256:" + found[2]


@pytest.mark.parametrize("extras", list(CLOSURES))
def test_locked_closure_of_each_selection(extras):
    command = [
        "uv",
        "export",
        "--locked",
        "--no-dev",
        "--no-emit-project",
        "--no-header",
        "--no-hashes",
        "--format",
        "requirements-txt",
    ]
    for extra in extras:
        command += ["--extra", extra]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "UV_PYTHON": sys.executable,
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        },
    )
    assert result.returncode == 0, result.stderr
    exported = {
        line.strip() for line in result.stdout.splitlines() if line[:1].isalpha()
    }
    assert exported == CLOSURES[extras]


@pytest.mark.parametrize(
    "text",
    (
        "psycopg[binary]==3.3.5; extra == 'execute-postgres'",
        'psycopg [ binary ] == 3.3.5 ; (extra=="execute-postgres")',
        "Psycopg[Binary]==3.3.5;extra=='execute-postgres'",
    ),
)
def test_artifact_requirement_extras_are_parsed_and_kept(text):
    assert smoke._dependency(text) == (
        "psycopg",
        ("binary",),
        "==",
        "3.3.5",
        "execute-postgres",
    )


def test_dropped_or_malformed_requirement_extras_never_match():
    assert smoke._dependency("psycopg==3.3.5; extra == 'execute-postgres'")[1] == ()
    for bad in (
        "psycopg[,binary]==3.3.5",
        "psycopg[binary,]==3.3.5",
        "psycopg[bin ary]==3.3.5",
        "psycopg[binary]]==3.3.5",
        "psycopg[binary==3.3.5",
    ):
        with pytest.raises(smoke.SmokeFailure, match="unsupported artifact"):
            smoke._dependency(bad)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "before,after",
    (
        # A route dependency loses its own requirement extra.
        (
            b"Requires-Dist: psycopg[binary]==3.3.5;",
            b"Requires-Dist: psycopg==3.3.5;",
        ),
        # A required route dependency is removed.
        (
            b"Requires-Dist: mysql-connector-python==26.7.0; extra == 'execute-mysql'\n",
            b"",
        ),
        # An optional dependency is moved into the unconditional core.
        (
            b"Requires-Dist: pyarrow==25.0.1; extra == 'execute-mysql'\n",
            b"Requires-Dist: pyarrow==25.0.1\n",
        ),
        (
            b"Requires-Dist: adbc-driver-manager==1.12.0;",
            b"Requires-Dist: adbc-driver-manager==1.11.0;",
        ),
        (
            b"adbc-driver-postgresql==1.12.0; extra == 'execute-postgres-adbc'",
            b"adbc-driver-postgresql==1.12.0; extra == 'execute-postgres'",
        ),
        (b"Provides-Extra: execute-postgres-adbc\n", b""),
        (
            b"Provides-Extra: execute-mysql\n",
            b"Provides-Extra: execute-mysql\nProvides-Extra: execute-all\n",
        ),
    ),
)
def test_route_extra_metadata_damage_fails_each_artifact(tmp_path, kind, before, after):
    original = _metadata_bytes()
    assert original.count(before) == 1
    with pytest.raises(smoke.SmokeFailure):
        _inspect(_artifact(tmp_path, kind, original.replace(before, after)), kind)


def _controlled(monkeypatch, versions, modules):
    """CONTROLLED distribution/version and module lookups for one case."""

    def version(name):
        if name not in versions:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]

    def load(name):
        found = modules[name]
        if isinstance(found, BaseException):
            raise found
        return found

    monkeypatch.setattr(importlib.metadata, "version", version)
    monkeypatch.setattr(importlib, "import_module", load)


PINS = (
    ("dist-a", "1.0", "pkg_a"),
    ("dist-b", "2.0", None),
    ("dist-c", "3.0", "pkg_c.sub.mod"),
)


def test_pinned_modules_returns_exactly_the_selected_modules(monkeypatch):
    a, e = object(), object()
    _controlled(
        monkeypatch,
        {"dist-a": "1.0", "dist-b": "2.0", "dist-c": "3.0"},
        {"pkg_a": a, "pkg_c.sub.mod": e},
    )
    assert ex.pinned_modules(PINS, "VERSION_CODE") == [a, e]


@pytest.mark.parametrize(
    "versions,failure,code",
    (
        ({"dist-a": "1.0", "dist-c": "3.0"}, None, "EXECUTION_DEPENDENCY_MISSING"),
        ({"dist-a": "1.0", "dist-b": "2.1", "dist-c": "3.0"}, None, "VERSION_CODE"),
        (
            {"dist-a": "1.0", "dist-b": "2.0", "dist-c": "3.0"},
            ModuleNotFoundError("absent", name="pkg_c.sub.mod"),
            "EXECUTION_DEPENDENCY_MISSING",
        ),
        (
            {"dist-a": "1.0", "dist-b": "2.0", "dist-c": "3.0"},
            ModuleNotFoundError("absent", name="pkg_c"),
            "EXECUTION_DEPENDENCY_MISSING",
        ),
    ),
)
def test_absent_or_other_version_is_a_named_refusal(
    monkeypatch, versions, failure, code
):
    _controlled(
        monkeypatch,
        versions,
        {
            "pkg_a": object(),
            "pkg_c.sub.mod": failure if failure is not None else object(),
        },
    )
    with pytest.raises(ex.ExecutionError, match="^" + code + "$"):
        ex.pinned_modules(PINS, "VERSION_CODE")


def test_every_distribution_is_checked_before_any_import(monkeypatch):
    """psycopg without psycopg-binary under a forced binary implementation would
    otherwise fail inside the first import instead of being named missing."""
    _controlled(
        monkeypatch,
        {"dist-a": "1.0", "dist-c": "3.0"},
        {"pkg_a": ImportError("requested binary implementation unavailable")},
    )
    with pytest.raises(ex.ExecutionError, match="^EXECUTION_DEPENDENCY_MISSING$"):
        ex.pinned_modules(PINS, "VERSION_CODE")


@pytest.mark.parametrize(
    "failure",
    (
        ModuleNotFoundError("transitive", name="dns"),
        ModuleNotFoundError("inside the package", name="pkg_c.sub.mod.part"),
        ModuleNotFoundError("string prefix, not a parent", name="pkg"),
        ModuleNotFoundError("unnamed"),
        ImportError("libexample.so: cannot open shared object file"),
    ),
)
def test_broken_transitive_or_native_import_is_never_called_missing(
    monkeypatch, failure
):
    _controlled(
        monkeypatch,
        {"dist-a": "1.0", "dist-b": "2.0", "dist-c": "3.0"},
        {"pkg_a": object(), "pkg_c.sub.mod": failure},
    )
    with pytest.raises(type(failure)) as raised:
        ex.pinned_modules(PINS, "VERSION_CODE")
    assert raised.value is failure


def _pins(requirements):
    out = {}
    for text in requirements:
        found = re.fullmatch(r"([a-z0-9-]+)(?:\[binary\])?==(.+)", text)
        assert found is not None
        out[found[1]] = found[2]
    return out


def test_each_route_checks_exactly_its_declared_selection():
    declared = {extra: _pins(EXTRAS[extra]) for extra in ROUTES}
    pins = {
        "execute-postgres": postgres.DRIVERS,
        "execute-mysql": mysql.DRIVERS,
        "execute-postgres-adbc": adbc.DRIVERS,
    }
    checked = {extra: {d: v for d, v, _m in pin} for extra, pin in pins.items()}
    # psycopg[binary] is psycopg plus psycopg-binary of the same release.
    assert checked["execute-postgres"] == {
        "psycopg": "3.3.5",
        "psycopg-binary": "3.3.5",
    }
    assert declared["execute-postgres"] == {"pyarrow": "25.0.1", "psycopg": "3.3.5"}
    assert checked["execute-mysql"] == {
        k: v for k, v in declared["execute-mysql"].items() if k != "pyarrow"
    }
    # The ADBC owner itself imports Arrow; the row routes leave Arrow to its owner.
    assert checked["execute-postgres-adbc"] == declared["execute-postgres-adbc"]
    modules = {m for pin in pins.values() for _d, _v, m in pin if m is not None}
    assert modules == {
        "psycopg",
        "mysql.connector.connection",
        "adbc_driver_postgresql",
        "adbc_driver_manager",
        "pyarrow",
    }


def test_postgres_rows_refuses_a_non_selected_libpq_implementation(monkeypatch):
    for impl in ("python", "c"):
        fake = SimpleNamespace(pq=SimpleNamespace(__impl__=impl))
        monkeypatch.setattr(postgres, "pinned_modules", lambda pins, code: [fake])
        with pytest.raises(ex.ExecutionError, match="^POSTGRES_DRIVER_LIBRARY$"):
            postgres.drivers()


def test_ambient_psycopg_implementation_override_is_refused(tmp_path: Path):
    """PSYCOPG_IMPL would silently load a system libpq instead of the pinned one."""
    code = """
import ctypes.util
from pietto._project import project_execution_postgres as p
try:
    p.drivers()
except Exception as error:
    print(type(error).__name__, str(error), bool(ctypes.util.find_library("pq")))
else:
    print("ACCEPTED")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PSYCOPG_IMPL": "python"},
    )
    assert result.returncode == 0, result.stderr
    kind, *rest = result.stdout.split()
    system = rest[-1] == "True"
    if system:
        assert (kind, rest[0]) == ("ExecutionError", "POSTGRES_DRIVER_LIBRARY")
    else:
        assert kind == "ImportError"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return compiled_template(tmp_path_factory.mktemp("s18") / "small", entry="bundle")


@pytest.fixture
def setup(tmp_path, built, monkeypatch):
    if not qualified(tmp_path):
        yield None
        return
    s17.arrow_free(monkeypatch)
    template, compiled = built
    workspace, job, publisher, binding, record, generation = s17.store(
        tmp_path / "workspace", template
    )
    publisher.close()
    x = s17.setup_namespace(
        workspace=workspace,
        job=job,
        binding=binding,
        record=record,
        generation=generation,
        built=compiled,
        template=template,
        root=tmp_path,
        runtimes=[],
    )
    yield x
    for runtime in x.runtimes:
        runtime.close(timeout=30)
    workspace.close()


def _application(workspace):
    """Every application row (the SQLite schema and settings are not rows)."""
    connection = workspace.use()
    tables = [
        r[0]
        for r in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
        )
    ]
    return {
        t: sorted(map(repr, connection.execute('SELECT * FROM "' + t + '"')))
        for t in tables
    }


def _source(route):
    access = ex.PostgresAccess(
        "127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable"
    )
    return rt.NativeSource(
        route,
        access,
        ("public", "pg_catalog"),
        ex.ExecutionLimits(batch_rows=2, seconds=600),
    )


@pytest.mark.parametrize("mode", ("CAPTURE", "RELAY", "RECOVER"))
def test_runtime_refuses_an_unavailable_selected_route_before_admission(
    setup, monkeypatch, mode
):
    x = setup
    if x is None:
        return
    calls = []

    def absent():
        calls.append("postgres_adbc")
        raise ex.ExecutionError("EXECUTION_DEPENDENCY_MISSING")

    def forbidden():
        raise AssertionError("another route's driver was loaded")

    monkeypatch.setattr(adbc, "drivers", absent)
    monkeypatch.setattr(postgres, "drivers", forbidden)
    monkeypatch.setattr(mysql, "drivers", forbidden)
    runtime = s17.open_runtime(x)
    x.runtimes.append(runtime)
    before = _application(x.workspace)
    threads = {t.ident for t in threading.enumerate()}
    unit = s17.unit(x, mode, source=_source("postgres_adbc"))
    with pytest.raises(ex.ExecutionError, match="^EXECUTION_DEPENDENCY_MISSING$"):
        runtime.submit(unit)
    assert calls == ["postgres_adbc"]
    assert runtime._records == {} and not runtime._queue
    assert {t.ident for t in threading.enumerate()} <= threads
    assert _application(x.workspace) == before
    assert before["admission"] == []


def test_runtime_unknown_route_and_broken_library_are_distinct(setup, monkeypatch):
    x = setup
    if x is None:
        return
    runtime = s17.open_runtime(x)
    x.runtimes.append(runtime)
    before = _application(x.workspace)
    with pytest.raises(JobStoreError, match="^RUNTIME_ROUTE$"):
        runtime.submit(s17.unit(x, "CAPTURE", source=_source("postgres_native")))
    broken = ImportError("libpq.so.5: cannot open shared object file")

    def failing():
        raise broken

    monkeypatch.setattr(postgres, "drivers", failing)
    with pytest.raises(ImportError) as raised:
        runtime.submit(s17.unit(x, "CAPTURE", source=_source("postgres_rows")))
    assert raised.value is broken
    assert runtime._records == {} and _application(x.workspace) == before


def test_saved_units_never_load_a_route_driver(setup, monkeypatch):
    x = setup
    if x is None:
        return
    loaded = []
    for module in (postgres, mysql, adbc):
        monkeypatch.setattr(module, "drivers", lambda m=module: loaded.append(m))
    runtime = s17.open_runtime(x)
    x.runtimes.append(runtime)
    handles = [
        runtime.submit(s17.unit(x, mode, checkpoint="ckp-" + "0" * 32))
        for mode in ("REPLAY", "PUBLISH")
    ]
    for handle in handles:
        assert runtime.wait(handle, 60).terminal is not None
    assert loaded == []


def test_direct_owner_refuses_before_any_connection(built, monkeypatch):
    template, _compiled = built
    from pietto._project.project_execution_template import bind_values

    binding = bind_values(template, tuple(zip(template.slots, (1,), strict=True)))
    owner = s12.pg_owner(binding)
    attempts = []

    def connect(self, *args, **kwargs):
        attempts.append(args)
        raise AssertionError("a connection was attempted")

    def absent():
        raise ex.ExecutionError("EXECUTION_DEPENDENCY_MISSING")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(postgres, "drivers", absent)
    for key in tuple(os.environ):
        if key.startswith("PG") or key == "SSLKEYLOGFILE":
            monkeypatch.delenv(key)
    with pytest.raises(ex.ExecutionError, match="^EXECUTION_DEPENDENCY_MISSING$"):
        owner.open()
    assert attempts == [] and owner._connection is None
    outcome = owner.outcome
    assert (outcome.source, outcome.delivery) == ("FAILED", "FAILED")
    assert outcome.primary is not None and outcome.primary.kind == "ExecutionError"


def test_saved_and_metadata_owners_import_no_driver_or_arrow(tmp_path: Path):
    owners = (
        "project_job_workspace",
        "project_job_store",
        "project_job_store_verification",
        "project_job_chunks",
        "project_job_capture",
        "project_job_replay",
        "project_job_extraction",
        "project_job_delivery",
        "project_job_sink",
        "project_job_publication",
        "project_job_runtime",
        "project_job_collection",
        "project_execution",
        "project_execution_postgres",
        "project_execution_postgres_adbc",
        "project_execution_postgres_adbc_native",
        "project_execution_mysql",
        "project_execution_mysql_native",
        "project_compiled_loading",
        "project_compiled_build",
    )
    code = """
import importlib, sys
for name in %r:
    importlib.import_module("pietto._project." + name)
loaded = sorted(n for n in sys.modules if n.split(".")[0] in %r)
assert loaded == [], loaded
""" % (owners, DRIVER_MODULES)
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
