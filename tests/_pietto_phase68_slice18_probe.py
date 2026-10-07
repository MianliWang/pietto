"""S18 installation, compatibility and installed native handoff; import
acquires nothing.

Explicit bounded families, each in registered workers with fresh interpreters
(`-I -B`, clean environment, unrelated working directory):

- install: a verified wheelhouse of the lock's exact artifacts, six fresh
  prefixes each materialized by one normal resolver command (no --no-deps, no
  preloaded drivers), `uv pip check`, an installed fact worker per prefix, two
  resolver negatives and three damaged-installation negatives.
- compat: the v1-v7 capability matrix of the current installed runtime and of
  the installed archived S17 runtime, unknown envelopes before SQLite, a
  recognized schema damage, the archived S16 runtime on an S18 v7 workspace,
  S17 compiled-code incompatibility and a fresh current acceptance.
- native: per target family, route x live/bundle x source/installed cells
  through the original S17 programs in route-specific prefixes, routed union
  captures with no-fallback controls, source deletion, a real sink lost reply
  and the driver-free Arrow tail (publication query, S13 restart window,
  retained consumer, reclaim, Arrow-only refusal of new extraction/R2).

Producers write raw facts only; `_pietto_phase68_slice18_check` judges.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import tomllib
import urllib.request

import _pietto_phase68_slice16_probe as s16
import _pietto_phase68_slice17_probe as s17

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice18-"
RECIPES = {
    "core": (),
    "arrow": ("arrow",),
    "execute-postgres": ("execute-postgres",),
    "execute-mysql": ("execute-mysql",),
    "execute-postgres-adbc": ("execute-postgres-adbc",),
    "union": ("execute-postgres", "execute-mysql", "execute-postgres-adbc"),
}
ROUTE_RECIPE = {
    "postgres_rows": "execute-postgres",
    "postgres_adbc": "execute-postgres-adbc",
    "mysql_rows": "execute-mysql",
}
# The exact CPython 3.13 Linux x86-64 artifact of each selected distribution.
WHEELHOUSE = {
    "antlr4-python3-runtime": "antlr4_python3_runtime-4.13.2-py3-none-any.whl",
    "pyarrow": "pyarrow-25.0.1-cp313-cp313-manylinux_2_28_x86_64.whl",
    "psycopg": "psycopg-3.3.5-py3-none-any.whl",
    "psycopg-binary": "psycopg_binary-3.3.5-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
    "mysql-connector-python": "mysql_connector_python-26.7.0-cp313-cp313-manylinux_2_28_x86_64.whl",
    "adbc-driver-manager": "adbc_driver_manager-1.12.0-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
    "adbc-driver-postgresql": "adbc_driver_postgresql-1.12.0-py3-none-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl",
    "importlib-resources": "importlib_resources-6.5.2-py3-none-any.whl",
    "typing-extensions": "typing_extensions-4.15.0-py3-none-any.whl",
}
TRACKED = (
    "psycopg",
    "psycopg_binary",
    "psycopg_c",
    "mysql",
    "_mysql_connector",
    "adbc_driver_manager",
    "adbc_driver_postgresql",
    "pyarrow",
)
INPUTS = {
    "check_input": "examples/basic/types.pietto",
    "postgres_input": "tests/fixtures/postgres/compatibility_ordering_metadata.pietto",
    "mysql_input": "tests/fixtures/mysql/compatibility_ordering_metadata.pietto",
}
MAX_ARTIFACT = 96 * 1024 * 1024


_write = s16._write_private


def _environment(cache):
    """The registered-worker environment without any ambient interpreter,
    project or uv configuration; installers get an explicit owned cache."""
    from _pietto_target_conformance_resources import clean_environment

    env = {
        k: v
        for k, v in clean_environment().items()
        if k
        not in {
            "VIRTUAL_ENV",
            "PYTHONPATH",
            "PYTHONHOME",
            "UV_PYTHON",
            "UV_PROJECT_ENVIRONMENT",
            "UV_NO_SYNC",
            "UV_LOCKED",
            "CONDA_PREFIX",
        }
    }
    env.update(UV_CACHE_DIR=str(cache), UV_NO_CONFIG="1", UV_NO_PROGRESS="1")
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _run(argv, log, *, env, cwd, seconds=900):
    with log.open("ab") as handle:
        handle.write(("$ " + " ".join(map(str, argv)) + "\n").encode())
        handle.flush()
        result = subprocess.run(
            [str(a) for a in argv],
            cwd=cwd,
            env=env,
            capture_output=True,
            timeout=seconds,
        )
        handle.write(result.stdout + result.stderr)
    return {
        "argv": [str(a) for a in argv],
        "returncode": result.returncode,
        "stdout": result.stdout.decode("utf-8", "replace")[-16384:],
        "stderr": result.stderr.decode("utf-8", "replace")[-16384:],
    }


def _download(url, path, size, attempts=3):
    """A bounded transfer of an exact recorded artifact from its URL: 1 MiB
    reads, an idle timeout and a deadline per attempt, at most `attempts`
    attempts, each recorded; a partial file never survives an attempt."""
    temporary = path.with_name(path.name + ".partial")
    record = []
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        temporary.unlink(missing_ok=True)
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "pietto-s18-probe"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                final, status, received = response.geturl(), response.status, 0
                with temporary.open("wb") as out:
                    while True:
                        if time.monotonic() - started > 900:
                            raise TimeoutError("S18_ARTIFACT_DEADLINE")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > min(size, MAX_ARTIFACT):
                            raise ValueError("S18_ARTIFACT_SIZE:" + path.name)
                        out.write(chunk)
            if received != size:
                raise ValueError("S18_ARTIFACT_SIZE:" + path.name)
            temporary.rename(path)
            record.append(
                {
                    "attempt": attempt,
                    "status": status,
                    "final_url_host": final.split("/")[2],
                    "bytes": received,
                    "seconds": time.monotonic() - started,
                }
            )
            return record
        except (OSError, TimeoutError) as error:
            record.append(
                {
                    "attempt": attempt,
                    "error": type(error).__name__,
                    "seconds": time.monotonic() - started,
                }
            )
    temporary.unlink(missing_ok=True)
    raise ValueError("S18_ARTIFACT_TRANSFER:" + path.name + ":" + json.dumps(record))


def wheelhouse(directory):
    """The lock's exact artifacts, verified by size and hash; reused when an
    identical verified file already exists in this owned directory."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    target = directory / (PREFIX + "wheelhouse")
    target.mkdir(mode=0o700, exist_ok=True)
    entries = []
    packages = {p["name"]: p for p in lock["package"]}
    for name, filename in WHEELHOUSE.items():
        (wheel,) = [
            w
            for w in packages[name]["wheels"]
            if w["url"].rsplit("/", 1)[1] == filename
        ]
        path = target / filename
        transfer = None
        if not path.exists():
            transfer = _download(wheel["url"], path, wheel["size"])
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != wheel["size"] or "sha256:" + digest != wheel["hash"]:
            raise ValueError("S18_WHEELHOUSE:" + filename)
        entries.append(
            {
                "name": name,
                "version": packages[name]["version"],
                "file": filename,
                "url": wheel["url"],
                "bytes": len(data),
                "sha256": digest,
                "transfer": transfer,
            }
        )
    constraints = directory / (PREFIX + "constraints.txt")
    constraints.write_text(
        "".join(e["name"] + "==" + e["version"] + "\n" for e in entries)
    )
    return target, constraints, entries


def materialize(prefix, interpreter, wheel, extras, house, constraints, cache, log):
    """One fresh prefix and one normal resolver command for this selection."""
    env = _environment(cache)
    cwd = prefix.parent
    venv = _run(["uv", "venv", "--python", interpreter, prefix], log, env=env, cwd=cwd)
    if venv["returncode"]:
        raise ValueError("S18_PREFIX:" + prefix.name)
    python = prefix / "bin/python"
    target = str(wheel) + ("[" + ",".join(extras) + "]" if extras else "")
    install = _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "--no-index",
            "--find-links",
            house,
            "--constraint",
            constraints,
            "--link-mode",
            "copy",
            "--strict",
            target,
        ],
        log,
        env=env,
        cwd=cwd,
    )
    check = _run(["uv", "pip", "check", "--python", python], log, env=env, cwd=cwd)
    freeze = _run(["uv", "pip", "freeze", "--python", python], log, env=env, cwd=cwd)
    return {"venv": venv, "install": install, "check": check, "freeze": freeze}


INSTALLED = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import hashlib, importlib, importlib.abc, importlib.metadata, io, json, os, platform
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["cwd"])
TRACKED = set(config["tracked"])
def loaded():
    return sorted({n.split(".")[0] for n in sys.modules} & TRACKED)
facts = {"prefix": sys.prefix, "executable": sys.executable, "python": sys.version,
    "platform": [platform.system(), platform.machine(), list(platform.libc_ver())]}
connection = sqlite3.connect(":memory:")
facts["sqlite"] = {"version": sqlite3.sqlite_version,
    "source_id": connection.execute("SELECT sqlite_source_id()").fetchone()[0],
    "options": [r[0] for r in connection.execute("PRAGMA compile_options")]}
connection.close()
facts["distributions"] = {d.metadata["Name"]: d.version
    for d in importlib.metadata.distributions()}
own = importlib.metadata.distribution("pietto")
facts["direct_url"] = json.loads(own.read_text("direct_url.json") or "null")
facts["installer"] = (own.read_text("INSTALLER") or "").strip()
facts["wheel_sha256"] = hashlib.sha256(Path(config["wheel"]).read_bytes()).hexdigest()
import pietto
root = Path(pietto.__file__).resolve().parent
names = sorted("pietto." + str(p.relative_to(root).with_suffix("")).replace("/", ".")
    for p in root.rglob("*.py"))
for name in names:
    importlib.import_module(name[:-9] if name.endswith(".__init__") else name)
facts["lazy"] = loaded()
facts["origins"] = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
        path = Path(filename).resolve()
        facts["origins"][name] = {"path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
from pietto import cli
def run(*arguments):
    out = io.StringIO()
    with redirect_stdout(out):
        try:
            status = cli.main(list(arguments))
        except SystemExit as error:
            status = error.code
    return [status, hashlib.sha256(out.getvalue().encode()).hexdigest()]
facts["cli"] = {"check": run("check", config["check_input"])[0],
    "postgres": run("emit-sql", config["postgres_input"], "--dialect", "postgres"),
    "mysql": run("emit-sql", config["mysql_input"], "--dialect", "mysql",
        "--format", "json")}
from pietto._project import project_execution_postgres as pg
from pietto._project import project_execution_postgres_adbc_native as adbc
from pietto._project import project_execution_mysql_native as my
from pietto._project.project_execution import ExecutionError
LOADERS = {"postgres_rows": pg.drivers, "postgres_adbc": adbc.drivers,
    "mysql_rows": my.drivers}
def attempt(route):
    before = set(loaded())
    try:
        LOADERS[route]()
        result = "OK"
    except ExecutionError as error:
        result = str(error)
    except ImportError as error:
        result = type(error).__name__
    return {"result": result, "loaded": sorted(set(loaded()) - before)}
if config["recipe"] == "union":
    # Each route's own module made unavailable in a combined installation:
    # the selected route refuses; no other installed driver is a substitute.
    blocked = []
    for route, module in (("postgres_adbc", "adbc_driver_postgresql"),
            ("postgres_rows", "psycopg"), ("mysql_rows", "mysql")):
        class Block(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name == module or name.startswith(module + "."):
                    raise ModuleNotFoundError("unavailable", name=name)
                return None
        blocker = Block()
        sys.meta_path.insert(0, blocker)
        try:
            blocked.append({"route": route, "module": module, **attempt(route)})
        finally:
            sys.meta_path.remove(blocker)
    facts["no_fallback"] = blocked
facts["routes"] = {route: attempt(route) for route in LOADERS}
from pietto._project.project_arrow_result import _arrow
from pietto._project.project_result_contract import ResultError
try:
    facts["arrow"] = _arrow().__version__
except ResultError as error:
    facts["arrow"] = str(error)
from pietto._project import project_job_workspace as w
try:
    w.storage_profile(config["cwd"])
    facts["storage"] = "QUALIFIED"
except w.JobStoreError as error:
    facts["storage"] = str(error)
Path(config["raw"]).write_text(json.dumps(facts, sort_keys=True))
"""

DRIVER_CHECK = r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import ctypes.util, importlib, json, os
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["cwd"])
from pietto._project.project_execution import ExecutionError
module = importlib.import_module("pietto._project." + config["owner"])
try:
    module.drivers()
    result = "OK"
except ExecutionError as error:
    result = str(error)
except ImportError as error:
    result = type(error).__name__
Path(config["raw"]).write_text(json.dumps({"result": result, "prefix": sys.prefix,
    "psycopg_impl_env": os.environ.get("PSYCOPG_IMPL"),
    "libpq": ctypes.util.find_library("pq")}))
"""


def _worker(
    directory,
    ledger,
    interpreter,
    program,
    config,
    name,
    *,
    origin,
    seconds=600,
    drop=(),
    inputs=(),
):
    """One registered fresh interpreter in an unrelated working directory (with
    copies of the named checkout inputs)."""
    from _pietto_phase68_slice8_probe import worker_process
    from _pietto_target_conformance_resources import clean_environment

    cwd = directory / (name + "-cwd")
    cwd.mkdir(mode=0o700)
    for relative in inputs:
        (cwd / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, cwd / relative)
    raw = directory / (name + "-raw.json")
    path = directory / (name + "-config.json")
    _write(path, {**config, "cwd": str(cwd), "raw": str(raw)})
    env = {
        k: v
        for k, v in clean_environment().items()
        if k not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", *drop}
    }
    env["PYTHONNOUSERSITE"] = "1"
    with (directory / (name + ".log")).open("wb") as log:
        status = worker_process(
            [str(interpreter), "-I", "-B", "-c", program, str(path)],
            env,
            ledger,
            log,
            origin=origin,
            group="s18-" + name.removeprefix(PREFIX),
            directory=directory,
            seconds=seconds,
        )
    path.unlink(missing_ok=True)
    if status:
        raise ValueError("S18_WORKER:" + name + ":" + str(status))
    return json.loads(raw.read_text())


def _distributions(prefix):
    import importlib.metadata as md

    sites = list((prefix / "lib").glob("python3.*/site-packages"))
    return {
        d.metadata["Name"]: d.version
        for site in sites
        for d in md.distributions(path=[str(site)])
    }


def install(directory, ledger, *, dist, interpreter, cache, house_root=None):
    """Six clean resolver cells over one wheel, then the negatives; the
    independent checker and the installation damages judge the raw record."""
    import _pietto_phase68_slice18_check as check

    directory.mkdir(mode=0o700)
    (wheel,) = sorted(Path(dist).glob("*.whl"))
    (sdist,) = sorted(Path(dist).glob("*.tar.gz"))
    started = time.monotonic()
    house, constraints, entries = wheelhouse(house_root or directory)
    log = directory / (PREFIX + "install-commands.log")
    cells, prefixes = [], {}
    for recipe, extras in RECIPES.items():
        prefix = directory / (PREFIX + "env-" + recipe)
        commands = materialize(
            prefix, interpreter, wheel, extras, house, constraints, cache, log
        )
        if commands["install"]["returncode"]:
            raise ValueError("S18_RESOLVER:" + recipe)
        facts = _worker(
            directory,
            ledger,
            prefix / "bin/python",
            INSTALLED,
            {"recipe": recipe, "wheel": str(wheel), "tracked": list(TRACKED), **INPUTS},
            PREFIX + "facts-" + recipe,
            origin="installed",
            inputs=tuple(INPUTS.values()),
        )
        prefixes[recipe] = prefix
        cells.append(
            {
                "recipe": recipe,
                "extras": list(extras),
                "prefix": str(prefix),
                "wheel": str(wheel),
                "interpreter": str(interpreter),
                "install": commands["install"],
                "check": commands["check"],
                "freeze": commands["freeze"]["stdout"].splitlines(),
                "facts": facts,
            }
        )
    negatives = []
    conflicting = directory / (PREFIX + "constraints-conflicting.txt")
    conflicting.write_text(
        constraints.read_text().replace("pyarrow==25.0.1", "pyarrow==25.0.0")
    )
    partial = directory / (PREFIX + "wheelhouse-without-mysql")
    partial.mkdir(mode=0o700)
    for item in house.iterdir():
        if not item.name.startswith("mysql_connector_python"):
            shutil.copy2(item, partial / item.name)
    # Both failing resolutions target one fresh prefix, empty after each.
    prefix = directory / (PREFIX + "negative")
    for index, (kind, recipe, use_house, use_constraints) in enumerate(
        (
            ("conflicting_constraint", "arrow", house, conflicting),
            ("missing_artifact", "execute-mysql", partial, constraints),
        )
    ):
        env = _environment(cache)
        if index == 0:
            venv = _run(
                ["uv", "venv", "--python", interpreter, prefix],
                log,
                env=env,
                cwd=directory,
            )
            if venv["returncode"]:
                raise ValueError("S18_PREFIX:" + prefix.name)
        extras = RECIPES[recipe]
        install = _run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                prefix / "bin/python",
                "--no-index",
                "--find-links",
                use_house,
                "--constraint",
                use_constraints,
                "--link-mode",
                "copy",
                "--strict",
                str(wheel) + "[" + ",".join(extras) + "]",
            ],
            log,
            env=env,
            cwd=directory,
        )
        negatives.append(
            {
                "kind": kind,
                "recipe": recipe,
                "returncode": install["returncode"],
                "stderr": install["stderr"][-2000:],
                "distributions": _distributions(prefix),
            }
        )
    damaged = []
    # One copy of the combined installation carries all three damages; each
    # route's own check reads only its own pins and library.
    copy = directory / (PREFIX + "damaged-union")
    shutil.copytree(prefixes["union"], copy, symlinks=True)
    (site,) = list((copy / "lib").glob("python3.*/site-packages"))
    (meta,) = list(site.glob("mysql_connector_python-26.7.0.dist-info/METADATA"))
    meta.write_text(meta.read_text().replace("Version: 26.7.0", "Version: 26.6.0", 1))
    (site / "adbc_driver_postgresql/libadbc_driver_postgresql.so").unlink()
    for native in (site / "psycopg_binary").glob("*.so"):
        native.write_bytes(b"")
    # The registered-worker environment forces PSYCOPG_IMPL=binary (Phase66
    # facility); the broken binary is also checked without that override.
    for label, owner, drop in (
        ("driver_version", "project_execution_mysql_native", ()),
        ("adbc_library", "project_execution_postgres_adbc_native", ()),
        ("psycopg_binary", "project_execution_postgres", ()),
        ("psycopg_binary_unforced", "project_execution_postgres", ("PSYCOPG_IMPL",)),
    ):
        result = _worker(
            directory,
            ledger,
            copy / "bin/python",
            DRIVER_CHECK,
            {"owner": owner},
            PREFIX + "damaged-" + label,
            origin="installed-damaged",
            drop=drop,
        )
        damaged.append({"kind": label, "recipe": "union", **result})
    evidence = {
        "wheel_bytes": wheel.read_bytes(),
        "sdist_bytes": sdist.read_bytes(),
        "lock": tomllib.loads((ROOT / "uv.lock").read_text()),
        "wheelhouse": [
            {k: e[k] for k in ("file", "url", "bytes", "sha256")} for e in entries
        ],
        "cells": cells,
        "negatives": negatives,
        "damaged": damaged,
    }
    raw = {
        k: v
        for k, v in evidence.items()
        if k not in ("wheel_bytes", "sdist_bytes", "lock")
    }
    raw.update(
        wheel={
            "path": str(wheel),
            "sha256": hashlib.sha256(evidence["wheel_bytes"]).hexdigest(),
            "bytes": len(evidence["wheel_bytes"]),
        },
        sdist={
            "path": str(sdist),
            "sha256": hashlib.sha256(evidence["sdist_bytes"]).hexdigest(),
            "bytes": len(evidence["sdist_bytes"]),
        },
        wheelhouse_transfers=entries,
    )
    _write(directory / (PREFIX + "install-raw.json"), raw)
    report: dict = {"verdict": check.check_install(evidence)}
    evidence["foreign_sha256"] = _foreign_member()
    report["damages"] = {
        kind: check.rejects(kind, evidence)
        for kind, (_d, family, _law) in check.DAMAGES.items()
        if family == "install"
    }
    report["seconds"] = time.monotonic() - started
    _write(directory / (PREFIX + "install-report.json"), report)
    return report


S17_WHEEL = (
    Path.home()
    / ".local/state/pietto/evidence/pietto-phase68-slice17-20261006T081611Z"
    / "pietto-phase68-slice17-wheel01/pietto-0.1.0-py3-none-any.whl"
)
S16_WHEEL = (
    Path.home()
    / ".local/state/pietto/evidence/pietto-phase68-slice16-20261006T034808Z"
    / "pietto-phase68-slice16-wheel01/pietto-0.1.0-py3-none-any.whl"
)


def _foreign_member():
    """The same-version (0.1.0) archived S17 wheel's own bytes of a module that
    S18 changed: an origin substituted from another installation (D3)."""
    import zipfile

    with zipfile.ZipFile(S17_WHEEL) as archive:
        data = archive.read("pietto/_project/project_job_runtime.py")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Compatibility: formats, envelopes, schema, archived runtimes, compiled code.

ORIGINS = r"""
def origins():
    out = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            path = Path(filename).resolve()
            out[name] = {"path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return out
"""

HEADER = (
    r"""
import sys
if sys.stdin.read(1) != "1":
    raise RuntimeError("registered worker gate required")
import hashlib, json, os, shutil, sqlite3
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
os.chdir(config["cwd"])
CWD = Path(config["cwd"])
"""
    + ORIGINS
)

MATRIX = r"""
from pietto._project import project_job_workspace as w
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_extraction as x, project_job_delivery as d
from pietto._project import project_job_publication as p, project_job_collection as col
from pietto._project import project_job_runtime as rt
Z = "0" * 32
OBSERVERS = {
    "result-chunks": lambda ws: c.checkpoint_snapshot(ws, "job-" + Z, "gen-" + Z),
    "saved-replay": lambda ws: r.consumer_state(ws, "csm-" + Z),
    "extraction-resume": lambda ws: x.extraction_state(ws, "job-" + Z, "gen-" + Z),
    "cooperative-delivery": lambda ws: d.stream_state(ws, "stm-" + Z),
    "complete-publication": lambda ws: p.publication(ws, "job-" + Z, "gen-" + Z),
    "concurrent-gc": lambda ws: col.protection(ws, "job-" + Z),
}
def rows(ws):
    con = ws.use()
    names = [n for (n,) in con.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name")]
    return {n: sorted(map(repr, con.execute('SELECT * FROM "' + n + '"'))) for n in names}
def outcome(call):
    try:
        call()
        return "RETURNED"
    except w.JobStoreError as error:
        return str(error)
def opened(ws):
    runtime = rt.open_runtime(ws.root, expected_identity=ws.identity, policy=rt.Policy())
    runtime.close(timeout=30)
matrix = {}
for index, fmt in enumerate(w.VERSIONS, start=1):
    root = CWD / ("v" + str(index))
    ws = w.create_workspace(str(root), format=fmt)
    envelope = json.loads((root / w.ENVELOPE).read_text())
    con = ws.use()
    schema = sorted(con.execute(
        "SELECT type, name, tbl_name, coalesce(sql, '') FROM sqlite_schema"))
    before = rows(ws)
    gates = {f: outcome(lambda o=o: o(ws)) for f, o in OBSERVERS.items()}
    unchanged = rows(ws) == before
    gate = outcome(lambda: opened(ws))
    gates["bounded-job-runtime"] = "OPENED" if gate == "RETURNED" else gate
    if gate != "RETURNED":
        unchanged = unchanged and rows(ws) == before
    matrix[envelope["format"]] = {"features": envelope["features"],
        "user_version": con.execute("PRAGMA user_version").fetchone()[0],
        "application_id": con.execute("PRAGMA application_id").fetchone()[0],
        "schema_sha256": hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
        "dirs": sorted(q.name for q in root.iterdir() if q.is_dir()),
        "gates": gates, "runtime": gates["bounded-job-runtime"], "unchanged": unchanged}
    ws.close()
Path(config["raw"]).write_text(json.dumps({"matrix": matrix, "origins": origins(),
    "prefix": sys.prefix}))
"""

ENVELOPES = r"""
from pietto._project import project_job_workspace as w
def tree(path):
    return sorted((os.path.relpath(os.path.join(d, n), path),
        os.lstat(os.path.join(d, n)).st_size, os.lstat(os.path.join(d, n)).st_mtime_ns)
        for d, names, files in os.walk(path) for n in names + files)
valid = CWD / "valid-v7"
ws = w.create_workspace(str(valid), format=w.FORMAT_V7)
identity = ws.identity
ws.close()
DAMAGES = {
    "future_format": lambda e: {**e, "format": "pietto.job-workspace.v8"},
    "unknown_feature": lambda e: {**e, "features": e["features"] + ["gc"]},
    "relabeled_v6": lambda e: {**e, "format": "pietto.job-workspace.v6"},
    "reordered_features": lambda e: {**e, "features": list(reversed(e["features"]))},
}
results = []
for name, damage in DAMAGES.items():
    copy = CWD / name
    shutil.copytree(valid, copy)
    envelope = json.loads((copy / w.ENVELOPE).read_text())
    (copy / w.ENVELOPE).write_text(json.dumps(damage(envelope)))
    before = tree(copy)
    try:
        w.open_workspace(str(copy), expected_identity=identity).close()
        outcome = "ACCEPTED"
    except w.JobStoreError as error:
        outcome = str(error)
    results.append({"damage": name, "outcome": outcome, "unchanged": tree(copy) == before})
schema = CWD / "schema-damage"
shutil.copytree(valid, schema)
con = sqlite3.connect(schema / w.DATABASE)
con.execute("CREATE TABLE s18_extra (value INTEGER)")
con.commit()
con.close()
try:
    w.open_workspace(str(schema), expected_identity=identity).close()
    recognized = "ACCEPTED"
except w.JobStoreError as error:
    recognized = str(error)
old = CWD / "for-archived-s16"
shutil.copytree(valid, old)
Path(config["raw"]).write_text(json.dumps({"envelopes": results,
    "schema": {"outcome": recognized}, "archived_subject": str(old),
    "archived_identity": identity, "origins": origins(), "prefix": sys.prefix}))
"""

OLD16 = r"""
from pietto._project import project_job_workspace as w
def tree(path):
    return sorted((os.path.relpath(os.path.join(d, n), path),
        os.lstat(os.path.join(d, n)).st_size, os.lstat(os.path.join(d, n)).st_mtime_ns)
        for d, names, files in os.walk(path) for n in names + files)
before = tree(config["subject"])
try:
    w.open_workspace(config["subject"], expected_identity=config["identity"]).close()
    outcome = "ACCEPTED"
except w.JobStoreError as error:
    outcome = str(error)
Path(config["raw"]).write_text(json.dumps({"outcome": outcome,
    "unchanged": tree(config["subject"]) == before, "format": w.FORMAT,
    "origins": origins(), "prefix": sys.prefix}))
"""

PRODUCE = r"""
sys.path.insert(0, config["tests"])
from _pietto_phase68_slice11_probe import compiled_template
from pietto._project.project_compiled_loading import load_compiled, supported_compatibility
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_capture as c
from pietto._project.project_execution_template import bind_values
template, built = compiled_template(CWD / "project", entry="bundle")
bundle = CWD / "bundle.json"
bundle.write_bytes(built.payload)
trust = dict(expected_pin=built.pin, accepted_producer=built.producer,
    accepted_compatibility=tuple(built.compatibility))
load_compiled(built.payload, **trust)
ws = w.create_workspace(str(CWD / "workspace"), format=w.FORMAT_V7)
job = s.register_job(ws, template, operation=s.new_operation()).get("job")
publisher = s.claim_publisher(ws, job, operation=s.new_operation())
binding = bind_values(template, tuple(zip(template.slots, (1,), strict=True)))
record = s.register_binding(publisher, binding, operation=s.new_operation()).get("binding")
generation = s.register_generation(publisher, record, binding, route="postgres_rows",
    isolation="stable", operation=s.new_operation()).get("generation")
publisher.close()
c.stored_binding(ws, job, generation, **trust)
identity = ws.identity
ws.close()
Path(config["raw"]).write_text(json.dumps({"identity": supported_compatibility()[-1],
    "compatibility": list(built.compatibility), "pin": built.pin,
    "producer": built.producer, "bundle": str(bundle),
    "workspace": str(CWD / "workspace"), "workspace_identity": identity, "job": job,
    "generation": generation, "self_load": "LOADED", "self_binding": "BOUND",
    "origins": origins(), "prefix": sys.prefix}))
"""

CONSUME = r"""
from pietto._project.project_compiled_loading import load_compiled, supported_compatibility
from pietto._project.project_compiled_schema import CompiledError
from pietto._project import project_job_workspace as w, project_job_capture as c
old = config["old"]
trust = dict(expected_pin=old["pin"], accepted_producer=old["producer"],
    accepted_compatibility=tuple(old["compatibility"]))
try:
    load_compiled(Path(old["bundle"]).read_bytes(), **trust)
    load = "LOADED"
except CompiledError as error:
    load = str(error)
ws = w.open_workspace(old["workspace"], expected_identity=old["workspace_identity"])
def bound(**trust_):
    try:
        c.stored_binding(ws, old["job"], old["generation"], **trust_)
        return "BOUND"
    except (w.JobStoreError, CompiledError) as error:
        return str(error)
binding_old = bound(**trust)
binding_current = bound(**{**trust, "accepted_compatibility": supported_compatibility()})
ws.close()
sys.path.insert(0, config["tests"])
from _pietto_phase68_slice11_probe import compiled_template
from pietto._project import project_job_store as s
from pietto._project.project_execution_template import bind_values
template, built = compiled_template(CWD / "project", entry="bundle")
fresh = w.create_workspace(str(CWD / "fresh"), format=w.FORMAT_V7)
job = s.register_job(fresh, template, operation=s.new_operation()).get("job")
publisher = s.claim_publisher(fresh, job, operation=s.new_operation())
binding = bind_values(template, tuple(zip(template.slots, (1,), strict=True)))
record = s.register_binding(publisher, binding, operation=s.new_operation()).get("binding")
generation = s.register_generation(publisher, record, binding, route="postgres_rows",
    isolation="stable", operation=s.new_operation()).get("generation")
publisher.close()
c.stored_binding(fresh, job, generation, expected_pin=built.pin,
    accepted_producer=built.producer, accepted_compatibility=tuple(built.compatibility))
fresh.close()
Path(config["raw"]).write_text(json.dumps({"identity": supported_compatibility()[-1],
    "load": load, "open": "OPENED", "binding_s17": binding_old,
    "binding_current": binding_current, "fresh": "ACCEPTED",
    "origins": origins(), "prefix": sys.prefix}))
"""


def compat(
    directory,
    ledger,
    *,
    wheel,
    current,
    house,
    constraints,
    interpreter,
    cache,
    archived_from=None,
):
    """Format matrix (current vs archived S17 runtime), envelopes before SQLite,
    recognized schema damage, archived S16 refusal, S17 code compatibility."""
    import _pietto_phase68_slice13_probe as s13
    import _pietto_phase68_slice18_check as check
    from pietto._project.project_compiled_loading import supported_compatibility

    directory.mkdir(mode=0o700)
    started = time.monotonic()
    log = directory / (PREFIX + "compat-commands.log")
    archived = {}
    for label, path, digest in (
        (
            "s16",
            S16_WHEEL,
            "035fa6057afce966045c8003855a7cf2eaeae2c472ed2b6d865251867a0c5a7a",
        ),
        (
            "s17",
            S17_WHEEL,
            "8d4e9044633f4bb3da31d050858bb80f3cd212a9a7b11df4e347aeffd2368c12",
        ),
    ):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("S18_ARCHIVED_WHEEL:" + label)
        if archived_from is None:
            prefix = directory / (PREFIX + "archived-" + label)
            commands = materialize(
                prefix, interpreter, path, (), house, constraints, cache, log
            )
            if commands["install"]["returncode"]:
                raise ValueError("S18_ARCHIVED_INSTALL:" + label)
        else:
            # An exact-input archived materialization reused with its recorded
            # provenance; every worker below re-verifies its origins by bytes.
            prefix = Path(archived_from) / (PREFIX + "archived-" + label)
            recorded = json.loads(
                (Path(archived_from) / (PREFIX + "compat-raw.json")).read_text()
            )["archived"][label]
            commands = {
                "install": recorded["install"],
                "check": recorded["check"],
                "reused_from": str(archived_from),
            }
        archived[label] = {"prefix": prefix, "wheel": path, "commands": commands}

    def run(interpreter_, program, name, config=None):
        return _worker(
            directory,
            ledger,
            interpreter_,
            HEADER + program,
            {"tests": str(ROOT / "tests"), **(config or {})},
            PREFIX + name,
            origin="installed",
        )

    current_python = Path(current) / "bin/python"
    s17_python = archived["s17"]["prefix"] / "bin/python"
    matrices = {
        "current": run(current_python, MATRIX, "matrix-current"),
        "s17": run(s17_python, MATRIX, "matrix-s17"),
    }
    envelopes = run(current_python, ENVELOPES, "envelopes")
    old16 = run(
        archived["s16"]["prefix"] / "bin/python",
        OLD16,
        "archived-s16-refusal",
        {
            "subject": envelopes["archived_subject"],
            "identity": envelopes["archived_identity"],
        },
    )
    produced = run(s17_python, PRODUCE, "s17-producer")
    consumed = run(current_python, CONSUME, "current-consumer", {"old": produced})
    for data, origin_wheel in (
        (matrices["current"], wheel),
        (envelopes, wheel),
        (consumed, wheel),
        (matrices["s17"], S17_WHEEL),
        (produced, S17_WHEEL),
        (old16, S16_WHEEL),
    ):
        s13.installed_members(data, origin_wheel)
    (antlr,) = sorted(Path(house).glob("antlr4_python3_runtime-*.whl"))
    evidence = {
        "formats": {k: v["matrix"] for k, v in matrices.items()},
        "envelopes": envelopes["envelopes"],
        "schema": envelopes["schema"],
        "s16": {k: old16[k] for k in ("outcome", "unchanged", "format")},
        "code": {
            "s17_identity": produced["identity"],
            "current_identity": consumed["identity"],
            "source_identity": supported_compatibility()[-1],
            "s17_self": produced["self_load"],
            "s17_binding": produced["self_binding"],
            **{
                k: consumed[k]
                for k in ("load", "open", "binding_s17", "binding_current", "fresh")
            },
        },
        "s17_wheel": S17_WHEEL.read_bytes(),
        "current_wheel": Path(wheel).read_bytes(),
        "antlr_wheel": antlr.read_bytes(),
    }
    raw = {k: v for k, v in evidence.items() if not k.endswith("_wheel")}
    raw["archived"] = {
        label: {
            "prefix": str(a["prefix"]),
            "wheel": str(a["wheel"]),
            "install": a["commands"]["install"],
            "check": a["commands"]["check"],
            "reused_from": a["commands"].get("reused_from"),
        }
        for label, a in archived.items()
    }
    _write(directory / (PREFIX + "compat-raw.json"), raw)
    report: dict = {"verdict": check.check_compat(evidence)}
    report["damages"] = {
        kind: check.rejects(kind, evidence)
        for kind, (_d, family, _law) in check.DAMAGES.items()
        if family == "compat"
    }
    report["seconds"] = time.monotonic() - started
    _write(directory / (PREFIX + "compat-report.json"), report)
    return report


# ---------------------------------------------------------------------------
# Native: route-specific installations, routed union, driver-free saved tail.

UNION = r"""
import importlib.abc
from pietto._project import project_job_chunks as chunks
TRACK = {"psycopg", "psycopg_binary", "mysql", "adbc_driver_manager",
    "adbc_driver_postgresql"}
def drivers_loaded():
    return {n.split(".")[0] for n in sys.modules} & TRACK
def admissions(workspace):
    return workspace.use().execute("SELECT count(*) FROM admission").fetchone()[0]
trust_ = (config["pin"], config["producer"], tuple(config["compatibility"]))
values_ = tuple(scalar_read(v).value for v in config["values"])
template = prepare_compiled_template(load_compiled(Path(config["bundle"]).read_bytes(),
    expected_pin=config["pin"], accepted_producer=config["producer"],
    accepted_compatibility=tuple(config["compatibility"])))
workspace = w.create_workspace(config["workspace"], format=w.FORMAT_V7)
runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
    policy=policy)
blocked = []
for route_, module in config["blocked"]:
    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name == module or name.startswith(module + "."):
                raise ModuleNotFoundError("unavailable", name=name)
            return None
    job_, generation_ = register(workspace, template, values_, route_)
    before, count = drivers_loaded(), admissions(workspace)
    blocker = Block()
    sys.meta_path.insert(0, blocker)
    try:
        runtime.submit(unit(workspace, "CAPTURE", job_, generation_, trust_, values_,
            source=source(route_, 2), durable=16 * 1024 * 1024))
        result = "ACCEPTED"
    except ex.ExecutionError as error:
        result = str(error)
    finally:
        sys.meta_path.remove(blocker)
    blocked.append({"route": route_, "module": module, "result": result,
        "loaded": sorted(drivers_loaded() - before), "admissions_before": count,
        "admissions_after": admissions(workspace), "records": len(runtime._records)})
routed = []
for route_ in config["routes"]:
    job_, generation_ = register(workspace, template, values_, route_)
    before = drivers_loaded()
    handle = runtime.submit(unit(workspace, "CAPTURE", job_, generation_, trust_, values_,
        source=source(route_, 2), durable=16 * 1024 * 1024))
    done = runtime.wait(handle, 900)
    output = c.stored_output(workspace, job_, generation_, expected_pin=config["pin"],
        accepted_producer=config["producer"],
        accepted_compatibility=tuple(config["compatibility"]))
    snap = c.checkpoint_snapshot(workspace, job_, generation_)
    wires = []
    with c.SnapshotReader(workspace, snap, output) as reader:
        for index in range(len(snap.members)):
            table = reader.read(index).table
            wires.extend([[chunks.coordinate_wire(row[n]) for n in table.column_names]
                for row in table.to_pylist()])
    routed.append({"route": route_, "terminal": done.terminal, "failure": done.failure,
        "loaded": sorted(drivers_loaded() - before), "wires": wires})
facts.update(blocked=blocked, routed=routed, verify=verify_store(workspace))
runtime.close()
workspace.close()
write_facts()
"""

SINK_CUT = r"""
from pietto._project import project_job_capture as c, project_job_store as s
from pietto._project import project_job_workspace as w, project_job_delivery as d
from pietto._project import project_job_sink as k
from pietto._project.project_compiled_schema import scalar_read
item = config["store"]
workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
publisher = s.claim_publisher(workspace, item["job"], operation=s.new_operation())
handle = k.create_sink(config["sink"], namespace=config["namespace"], epoch=1,
    retention_seconds=86400)
sink = d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
    epoch=1, retention=handle.retention, purpose="s18-lost-reply", seconds=3600)
snapshot = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
window = d.accept_window(workspace, item["job"], item["generation"],
    checkpoint=snapshot.checkpoint, purpose="s18-lost-reply", route=item["route"],
    values=tuple(scalar_read(v).value for v in item["values"]),
    expected_pin=item["pin"], accepted_producer=item["producer"],
    accepted_compatibility=tuple(item["compatibility"]), seconds=3600, batch_rows=4096)
stream = d.register_stream(publisher, window, sink, operation=s.new_operation()).get(
    "stream")
session = d.open_stream(publisher, stream, sink, operation=s.new_operation())
session.adopt(window, operation=s.new_operation())
issued = session.next(config["rows"], operation=s.new_operation())
statuses = session.send(issued)
effects = handle.use().execute("SELECT count(*) FROM effect").fetchone()[0]
retain_raw({"stream": stream, "checkpoint": snapshot.checkpoint,
    "sink": handle.root, "sink_identity": handle.identity,
    "namespace": handle.namespace, "issued": [issued.start, issued.stop],
    "statuses": {str(k_): v for k_, v in statuses.items()}, "effects": effects,
    "rows": snapshot.frontier, "connections": connections,
    "installed_drivers": installed_drivers,
    "loaded_drivers": sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS),
    "origins": origins(), "prefix": sys.prefix})
sys.stdout.write("cut\n")
sys.stdout.flush()
while True:
    time.sleep(60)
"""

SINK_RECONCILE = r"""
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_delivery as d, project_job_sink as k
from pietto._project.project_compiled_schema import scalar_read
item, cut = config["store"], config["cut"]
workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
handle = k.open_sink(cut["sink"], expected_identity=cut["sink_identity"])
after_cut = handle.use().execute("SELECT count(*) FROM effect").fetchone()[0]
confirmed_after_cut = d.stream_state(workspace, cut["stream"]).position
publisher = s.claim_publisher(workspace, item["job"], operation=s.new_operation())
sink = d.accept_sink(handle, instance=handle.identity, namespace=handle.namespace,
    epoch=1, retention=handle.retention, purpose="s18-lost-reply", seconds=3600)
# Fresh read permission naming the latest adopted window's checkpoint.
window = d.accept_window(workspace, item["job"], item["generation"],
    checkpoint=cut["checkpoint"], purpose="s18-lost-reply", route=item["route"],
    values=tuple(scalar_read(v).value for v in item["values"]),
    expected_pin=item["pin"], accepted_producer=item["producer"],
    accepted_compatibility=tuple(item["compatibility"]), seconds=3600, batch_rows=4096)
session = d.open_stream(publisher, cut["stream"], sink, window=window,
    operation=s.new_operation())
first, extents = None, []
while True:
    got = session.next(config["rows"], operation=s.new_operation())
    if isinstance(got, d.Waiting):
        waiting = [got.terminal, got.position]
        break
    statuses = session.send(got)
    if first is None:
        first = {"prior": sorted(got.prior), "extent": [got.start, got.stop],
            "statuses": {str(k_): v for k_, v in statuses.items()}}
    session.confirm(got, operation=s.new_operation())
    extents.append([got.start, got.stop])
session.close()
final = [list(r_) for r_ in handle.use().execute(
    "SELECT position, commit_identity FROM effect ORDER BY position")]
position = d.stream_state(workspace, cut["stream"]).position
publisher.close()
handle.close()
workspace.close()
retain_raw({"after_cut": after_cut, "confirmed_after_cut": confirmed_after_cut,
    "first": first, "extents": extents, "waiting": waiting, "final": final,
    "position": position, "connections": connections,
    "installed_drivers": installed_drivers,
    "loaded_drivers": sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS),
    "origins": origins(), "prefix": sys.prefix})
"""

SAVED = r"""
from pietto._project import project_job_capture as c, project_job_replay as r
from pietto._project import project_job_store as s, project_job_workspace as w
from pietto._project import project_job_runtime as rt, project_job_collection as col
from pietto._project import project_job_chunks as chunks, project_job_publication as p
from pietto._project import project_execution as ex
from pietto._project.project_compiled_schema import scalar_read
from pietto._project.project_job_store_verification import verify_store
def op():
    return s.new_operation()
def trust(item):
    return dict(expected_pin=item["pin"], accepted_producer=item["producer"],
        accepted_compatibility=tuple(item["compatibility"]))
def values(item):
    return tuple(scalar_read(v).value for v in item["values"])
def unit(workspace, mode, item, generation, job, **fields):
    return rt.Unit(mode=mode, root=workspace.root, workspace=workspace.identity,
        job=job, generation=generation,
        trust=(item["pin"], item["producer"], tuple(item["compatibility"])),
        values=values(item), seconds=3600, **fields)
def admissions(workspace):
    return workspace.use().execute("SELECT count(*) FROM admission").fetchone()[0]
def drain(runtime, handle):
    acked, wires, extents = set(), [], []
    while runtime.query(handle).terminal is None:
        got = runtime.take(handle, 1)
        if got is None or got.identity in acked:
            time.sleep(0.01)
            continue
        data = pa.record_batch(got.batch)
        columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
        wires.extend([chunks.coordinate_wire(column[j]) for column in columns]
            for j in range(data.num_rows))
        extents.append([got.start, got.stop])
        acked.add(got.identity)
        runtime.ack(handle, got)
    return acked, wires, extents
ca = Path(config["runtime_cwd"]) / "unused-ca.pem"
ca.write_text("unused\n")
def native_source(route):
    if route == "mysql_rows":
        access = ex.MySQLAccess("127.0.0.1", 9, "phase66", "pietto_query", "unused",
            str(ca), "pietto_query@%", verify_identity=False, loopback_tls_exception=True)
        schemas = ("phase66",)
    else:
        access = ex.PostgresAccess("127.0.0.1", 9, "phase66", "pietto_query", "unused",
            "disable")
        schemas = ("public", "pg_catalog")
    return rt.NativeSource(route, access, schemas,
        ex.ExecutionLimits(batch_rows=2, seconds=60))
def direct_owner(binding, route):
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
    source = native_source(route)
    sources = binding.artifact.request.sources
    if route == "mysql_rows":
        premise = {"mysql_deployment": ex.MySQLDeploymentPremise(source.access, sources,
            source.schemas)}
    else:
        premise = {"postgres_deployment": ex.PostgresDeploymentPremise(source.access,
            sources, source.schemas, route)}
    request = ex.prepare_compiled_execution(binding, source.access, route=route,
        limits=source.limits, **premise)
    owners = {"postgres_rows": PostgresExecution, "postgres_adbc": PostgresADBCExecution,
        "mysql_rows": MySQLExecution}
    return owners[route](request)
results = []
for item in config["stores"]:
    out = {"key": item["key"], "route": item["route"]}
    workspace = w.open_workspace(item["workspace"], expected_identity=item["identity"])
    runtime = rt.open_runtime(workspace.root, expected_identity=workspace.identity,
        policy=rt.Policy(workers=3, connections=3))
    try:
        # New extraction and R2 in this Arrow-only installation: properly
        # authorized requests meet the selected-route boundary first.
        refusals = []
        latest = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        for mode in ("RECOVER", "CAPTURE"):
            before = admissions(workspace)
            try:
                runtime.submit(unit(workspace, mode, item, item["generation"],
                    item["job"], source=native_source(item["route"]),
                    checkpoint=latest.checkpoint, interrupt=True,
                    durable=1024 * 1024))
                result = "ACCEPTED"
            except ex.ExecutionError as error:
                result = str(error)
            refusals.append({"kind": "submit", "mode": mode, "result": result,
                "admissions_before": before, "admissions_after": admissions(workspace),
                "records": len(runtime._records)})
        _t, binding, route = c.stored_binding(workspace, item["job"], item["generation"],
            **trust(item))
        owner = direct_owner(binding, route)
        attempts = len(connections)
        try:
            owner.open()
            result = "OPENED"
        except ex.ExecutionError as error:
            result = str(error)
        refusals.append({"kind": "owner", "route": route, "result": result,
            "socket_attempts": len(connections) - attempts,
            "connected": owner._connection is not None})
        distinct = list(item["distinct"])
        retained = distinct.pop() if distinct else None
        if retained is not None:
            # A retired unpublished generation kept alive only by a consumer.
            key_r, job_r, gen_r = retained
            it_r = item["trusts"][gen_r]
            snap_r = c.checkpoint_snapshot(workspace, job_r, gen_r)
            holder = s.claim_publisher(workspace, job_r, operation=op())
            accepted = r.accept_saved_read(workspace, job_r, gen_r,
                checkpoint=snap_r.checkpoint, consumer=r.new_consumer(),
                scope="complete_capture", extent=snap_r.frontier, purpose="s18-retained",
                route=item["route"], values=values(it_r), seconds=3600, batch_rows=4096,
                **trust(it_r))
            r.register_consumer(holder, accepted, operation=op())
            consumer_retention = r.consumer_state(workspace, accepted.consumer).retention
            col.retire_generation(holder, gen_r, operation=op())
            holder.close()
        targets = [(item, item["generation"], item["job"], item["closing"])] + [
            (item["trusts"][g], g, j, item["closings"][g]) for _k, j, g in distinct]
        publishes = []
        for it, g, j, closing in targets:
            snap = c.checkpoint_snapshot(workspace, j, g)
            publishes.append(runtime.submit(unit(workspace, "PUBLISH", it, g, j,
                checkpoint=snap.checkpoint, closing=closing)))
        c_job, c_generation = item["contention"]
        holder = s.claim_publisher(workspace, c_job, operation=op())
        col.retire_generation(holder, c_generation, operation=op())
        holder.close()
        during = runtime.collect()
        published = [runtime.wait(h, 1800) for h in publishes]
        after = runtime.collect()
        queried = {g: p.publication(workspace, j, g) is not None for _i, g, j, _c in targets}
        reads, acked_all, handles = {}, set(), list(publishes)
        for it, g, j, _closing in targets:
            snap = c.checkpoint_snapshot(workspace, j, g)
            h = runtime.submit(unit(workspace, "REPLAY", it, g, j,
                checkpoint=snap.checkpoint, extent=snap.frontier, rows=5, batch_rows=5))
            acked, wires, extents = drain(runtime, h)
            acked_all |= acked
            reads[g] = {"terminal": runtime.query(h).terminal, "wires": wires,
                "extents": extents}
            handles.append(h)
        # S13 restart window: issued but unacknowledged, then a new session.
        main = c.checkpoint_snapshot(workspace, item["job"], item["generation"])
        holder = s.claim_publisher(workspace, item["job"], operation=op())
        accepted = r.accept_saved_read(workspace, item["job"], item["generation"],
            checkpoint=main.checkpoint, consumer=r.new_consumer(),
            scope="complete_capture", extent=main.frontier, purpose="s18-restart",
            route=item["route"], values=values(item), seconds=3600, batch_rows=4096,
            **trust(item))
        r.register_consumer(holder, accepted, operation=op())
        first_session = r.open_replay(holder, accepted, operation=op())
        first = first_session.next(2, operation=op())
        issued = [first.start, first.stop]
        first.batch.close()
        first_session.close()
        before_restart = [list(x) for x in
            r.consumer_state(workspace, accepted.consumer).acknowledged]
        second_session = r.open_replay(holder, accepted, operation=op())
        second = second_session.next(2, operation=op())
        second_session.acknowledge(second, operation=op())
        acked_all.add(second.identity)
        second.batch.close()
        second_session.close()
        restart = {"first": issued, "reissued": [second.start, second.stop],
            "consumer": accepted.consumer, "delivery": second.identity,
            "acknowledged_before_restart": before_restart,
            "acknowledged_after": [list(x) for x in
                r.consumer_state(workspace, accepted.consumer).acknowledged]}
        holder.close()
        retained_facts = None
        if retained is not None:
            protected = runtime.collect()
            view = {g.generation: g for g in col.protection(workspace, job_r)}[gen_r]
            holder = s.claim_publisher(workspace, job_r, operation=op())
            c.release_retention(holder, consumer_retention, operation=op())
            holder.close()
            released = runtime.collect()
            retained_facts = {"generation": gen_r,
                "roots": [list(map(str, root)) for root in view.roots],
                "protected_members": sorted(view.protected),
                "decided_while_retained": sorted(d_[0] for part in (during, after,
                    protected) for d_ in part.decided if d_[1] == gen_r),
                "removed_while_retained": [list(x) for part in (during, after,
                    protected) for x in part.removed],
                "removed_after_release": [list(x) for x in released.removed]}
        names = set(os.listdir(os.path.join(workspace.root, "chunks")))
        vectors = {row[0]: json.loads(row[4]) for row in workspace.use().execute(
            "SELECT * FROM admission")}
        units = {}
        for h in handles:
            q = runtime.query(h)
            units[h] = {"events": [list(e) for e in q.events], "vector": vectors.get(h),
                "job": q.job, "generation": q.generation,
                "durable_cancel": q.durable_cancel, "settlement": q.settlement,
                "terminal": q.terminal, "failure": q.failure,
                "runtime": runtime.owner.epoch}
        out.update(refusals=refusals, published=[[q.terminal, q.failure] for q in published],
            queried=queried, during=[list(d_) for d_ in during.decided],
            during_busy=list(during.busy), after=[list(d_) for d_ in after.decided],
            removed=[list(x) for x in during.removed + after.removed], reads=reads,
            acked=sorted(acked_all), units=units, restart=restart, retained=retained_facts,
            main_present=all(m.file in names for m in main.members),
            old_present=all(n + ".chunk" in names for n in item["old_members"]),
            verify=verify_store(workspace))
        backup = item["workspace"] + "-final.sqlite"
        with sqlite3.connect(backup) as copy:
            workspace.use().backup(copy)
        copy.close()
        out["backup"] = backup
    except Exception as error:
        out["error"] = type(error).__name__ + ":" + str(error)[:300]
    finally:
        runtime.close()
        workspace.close()
    results.append(out)
loaded = sorted(n for n in sys.modules if n.split(".")[0] in DRIVERS)
retain_raw({"results": results, "connections": connections,
    "installed_drivers": installed_drivers, "loaded_drivers": loaded,
    "origins": origins(), "prefix": sys.prefix})
"""


def _spawn_cut(directory, ledger, interpreter, program, config, name):
    """A registered worker killed at its `cut` barrier (real SIGKILL)."""
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice11_probe import kill, until

    path = directory / (name + "-config.json")
    _write(path, config)
    with (directory / (name + ".log")).open("w") as log:
        child = s14._spawn(interpreter, program, path, ledger, log, name)
        try:
            until(child, "cut", 600)
            code, _ = kill(child)
        finally:
            if child.poll() is None:
                kill(child)
            s14._reaped(ledger, child, child.returncode)
    path.unlink()
    if code != -9:
        raise ValueError("S18_CUT:" + name + ":" + str(code))
    return json.loads(Path(config["raw"]).read_text())


def lost_reply(directory, ledger, interpreter, store, wheel):
    """A real sink lost reply in the driver-free installation: the sink commits,
    the process dies before local confirmation, a fresh process queries by the
    same identity and resubmits nothing."""
    import _pietto_phase68_slice13_probe as r13
    import _pietto_phase68_slice14_probe as s14

    name = PREFIX + "lost-reply-" + store["key"]
    common = {
        "runtime_cwd": str(directory),
        "library_source": str(ROOT / "src"),
        "origin": "installed",
        "store": store,
        "rows": 2,
    }
    cut = _spawn_cut(
        directory,
        ledger,
        interpreter,
        r13.REPLAY_HEADER + ORIGINS + SINK_CUT,
        {
            **common,
            "raw": str(directory / (name + "-cut.json")),
            "sink": str(directory / (name + "-sink")),
            "namespace": "s18.lost-reply." + store["key"],
        },
        name + "-cut",
    )
    resumed = _worker(
        directory,
        ledger,
        interpreter,
        r13.REPLAY_HEADER + ORIGINS + SINK_RECONCILE,
        {**common, "cut": cut},
        name + "-reconcile",
        origin="installed",
    )
    for data in (cut, resumed):
        s14._origin_check(data, "installed", wheel)
    return cut, resumed


def native(
    directory,
    ledger,
    *,
    target,
    interpreters,
    union,
    saved_interpreter,
    wheel,
    cells,
):
    """Per route and (origin, entry) cell, the original S17 joined history in that
    route's own selected installation (source cells keep its recipe but import
    the checkout): an R2 relay held by a stalled sink beside a same-route
    contention capture and (bundle) the S16 distinctions, SIGKILL, a replacement
    runtime RECOVERs with fresh qualification while another job is cancelled
    under pressure. Then routed union captures with no-fallback controls, the
    source is deleted, installed bundle stores show a real sink lost reply, and
    an Arrow-only driver-free runtime publishes, queries, replays, restarts a
    window, keeps a retained consumer, reclaims, and refuses new extraction."""
    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice13_probe as r13
    import _pietto_phase68_slice14_probe as s14
    from _pietto_phase68_slice6_probe import manager, session_gone
    from _pietto_phase68_slice6_probe import setup as setup_general
    from _pietto_phase68_slice7_cases import manifest as guard_manifest
    from _pietto_phase68_slice7_probe import fill
    from _pietto_phase68_slice8_probe import event, worker_process
    from _pietto_phase68_slice11_probe import kill, until
    from _pietto_target_conformance_resources import Resources, clean_environment
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources(target, pins["targets"][target], directory)
    state = json.loads(ledger.read_text())
    state["owned_resources"].append(
        {
            "kind": "database_resource",
            "target": target,
            "name": resource.name,
            "network_name": resource.network_name,
            "directory": str(directory),
        }
    )
    ledger.write_text(json.dumps(state, indent=2) + "\n")
    event(
        ledger,
        {"kind": "s18_native_start", "directory": str(directory), "target": target},
    )
    routes = ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]
    report: dict = {
        "status": "STARTED",
        "target": target,
        "routes": routes,
        "histories": [],
    }
    report_path = directory / (PREFIX + "native.json")
    started = time.monotonic()
    timings: dict = {}
    cell = {
        "group": "refined",
        "case": "R2_seven",
        "variant": "39_values",
        "excluded": False,
    }
    stores = []
    try:
        mark = time.monotonic()
        resource.acquire()
        if target == "mysql":
            manager(resource, "USE phase66")
        providers = setup_general(resource)
        s16.guard_sources(resource)
        bag = next(c for c in guard_manifest() if c["name"] == "bag_one")
        fill(
            resource,
            bag["lhs"],
            bag["rhs"],
            wide_text=bag["options"].get("wide_text", False),
        )
        if target == "mysql":
            for table in ("threads", "events_transactions_current"):
                manager(
                    resource,
                    "GRANT SELECT ON performance_schema."
                    + table
                    + " TO 'pietto_query'@'%'",
                )

        def bundle(reference_cell, name):
            reference = s10.build_native_reference(
                directory / (PREFIX + name + "-source"),
                target,
                reference_cell,
                providers,
            )
            if reference is None:
                raise ValueError("S18_NATIVE_REFERENCE:" + name)
            artifact, preparation, query, _output, _binding = reference
            built = build_compiled(artifact, guarded=preparation, refinement=query)
            path = directory / (PREFIX + name + "-bundle.json")
            path.write_bytes(built.payload)
            path.chmod(0o600)
            return {
                "bundle": str(path),
                "pin": built.pin,
                "producer": built.producer,
                "compatibility": list(built.compatibility),
                "values": [
                    scalar_wire(Scalar(v.tag.value, v.value))
                    for v in artifact.fixed_values
                ],
            }

        main = bundle(cell, "reference")
        distinctions = {s16.label(d): bundle(d, s16.label(d)) for d in s17.DISTINCT}
        ordinary = distinctions[s16.label(s17.DISTINCT[0])]
        timings["preparation"] = time.monotonic() - mark
        common = {
            "target": target,
            "cell": cell,
            "providers": providers,
            "build_helpers": str(ROOT / "tests"),
            "library_source": str(ROOT / "src"),
            "port": resource.port,
            "password": resource._passwords[1],
            "ca_path": str(resource.ca_path) if target == "mysql" else None,
            "request_seconds": 900,
            **main,
        }

        def spawn(interpreter, name, program, config, *, cut=False):
            path = directory / (name + "-config.json")
            runtime_cwd = directory / (name + "-runtime")
            runtime_cwd.mkdir(mode=0o700)
            facts = directory / (name + "-facts.json")
            _write(
                path,
                {
                    **common,
                    **config,
                    "runtime_cwd": str(runtime_cwd),
                    "facts": str(facts),
                },
            )
            with (directory / (name + "-worker.log")).open("w") as log:
                child = s14._spawn(interpreter, program, path, ledger, log, name)
                try:
                    if cut:
                        until(child, "cut", 1800)
                        code, _ = kill(child)
                    else:
                        code = child.wait(timeout=3600)
                finally:
                    if child.poll() is None:
                        kill(child)
                    s14._reaped(ledger, child, child.returncode)
            path.unlink()
            if code != (-9 if cut else 0):
                raise ValueError("S18_NATIVE_WORKER:" + name + ":" + str(code))
            return json.loads(facts.read_text())

        for route in routes:
            for origin, entry in cells:
                key = route + "-" + origin + "-" + entry
                name = PREFIX + key
                record: dict = {
                    "key": key,
                    "route": route,
                    "origin": origin,
                    "entry": entry,
                    "interpreter": str(interpreters[route]),
                }
                report["histories"].append(record)
                items = []
                if entry == "bundle":
                    for d in s17.DISTINCT:
                        items.append(
                            {
                                "key": key + "-" + s16.label(d),
                                **distinctions[s16.label(d)],
                            }
                        )
                mark = time.monotonic()
                captured = spawn(
                    interpreters[route],
                    name + "-capture",
                    s17.NATIVE_HEADER + s17.NATIVE_CAPTURE,
                    {
                        "route": route,
                        "role": "capture",
                        "origin": origin,
                        "entry": entry,
                        "workspace": str(directory / (name + "-workspace")),
                        "sink": str(directory / (name + "-sink")),
                        "namespace": "s18.native." + key,
                        "live_project": str(directory / (name + "-source")),
                        "contention": ordinary,
                        "contention_route": route,
                        "distinctions": items,
                    },
                    cut=True,
                )
                s14._origin_check(captured, origin, wheel)
                if captured.get("session") is not None:
                    captured["session_gone"] = session_gone(
                        resource, captured["session"]
                    )
                record["capture"] = captured
                timings[key + ":capture"] = time.monotonic() - mark
                mark = time.monotonic()
                recovered = spawn(
                    interpreters[route],
                    name + "-recover",
                    s17.NATIVE_HEADER + s17.NATIVE_RECOVER,
                    {
                        **{
                            k: captured[k]
                            for k in ("workspace", "identity", "job", "generation")
                        },
                        "route": route,
                        "role": "recover",
                        "origin": origin,
                        "entry": "bundle",
                        "pressure": ordinary,
                        "sink": str(directory / (name + "-pressure-sink")),
                        "namespace": "s18.pressure." + key,
                    },
                )
                s14._origin_check(recovered, origin, wheel)
                record["recover"] = recovered
                timings[key + ":recover"] = time.monotonic() - mark
                stores.append(
                    {
                        "key": key,
                        "route": route,
                        "origin": origin,
                        "entry": entry,
                        "workspace": captured["workspace"],
                        "identity": captured["identity"],
                        "job": captured["job"],
                        "generation": captured["generation"],
                        "closing": recovered["closing"],
                        "old_members": [m[3] for m in captured["members"]],
                        "contention": captured["contention"],
                        "distinct": captured["distinct"],
                        "closings": captured["closings"],
                        "trusts": {
                            g: distinctions[k[len(key) + 1 :]]
                            for k, _j, g in captured["distinct"]
                        },
                        **main,
                    }
                )
                report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        mark = time.monotonic()
        modules = {
            "postgres_rows": "psycopg",
            "postgres_adbc": "adbc_driver_postgresql",
            "mysql_rows": "mysql",
        }
        report["union"] = spawn(
            union,
            PREFIX + "union",
            s17.NATIVE_HEADER + UNION,
            {
                "route": routes[0],
                "role": "union",
                "origin": "installed",
                "entry": "bundle",
                "workspace": str(directory / (PREFIX + "union-workspace")),
                "routes": routes,
                "blocked": [[route, modules[route]] for route in routes],
            },
        )
        s14._origin_check(report["union"], "installed", wheel)
        timings["union"] = time.monotonic() - mark
        mark = time.monotonic()
        report["source_cleanup"] = resource.cleanup()
        timings["source_cleanup"] = time.monotonic() - mark
        mark = time.monotonic()
        report["lost_replies"] = {}
        for store in stores:
            if (store["origin"], store["entry"]) == ("installed", "bundle"):
                cut, resumed = lost_reply(
                    directory, ledger, saved_interpreter, store, wheel
                )
                report["lost_replies"][store["key"]] = {"cut": cut, "resumed": resumed}
        timings["lost_reply"] = time.monotonic() - mark
        mark = time.monotonic()
        for origin in sorted({o for o, _e in cells}):
            raw = directory / (PREFIX + "saved-" + origin + ".json")
            path = directory / (PREFIX + "saved-" + origin + "-config.json")
            runtime_cwd = directory / (PREFIX + "saved-" + origin + "-runtime")
            runtime_cwd.mkdir(mode=0o700)
            _write(
                path,
                {
                    "runtime_cwd": str(runtime_cwd),
                    "library_source": str(ROOT / "src"),
                    "origin": origin,
                    "raw": str(raw),
                    "stores": [s_ for s_ in stores if s_["origin"] == origin],
                },
            )
            with (directory / (PREFIX + "saved-" + origin + ".log")).open("wb") as log:
                status = worker_process(
                    [
                        str(saved_interpreter),
                        "-I",
                        "-B",
                        "-c",
                        r13.REPLAY_HEADER + "import sqlite3\n" + ORIGINS + SAVED,
                        str(path),
                    ],
                    clean_environment(),
                    ledger,
                    log,
                    origin=origin,
                    group="s18-native-saved",
                    directory=directory,
                    seconds=3600,
                )
            path.unlink()
            if status:
                raise ValueError("S18_NATIVE_SAVED:" + str(status))
            data = json.loads(raw.read_text())
            s14._origin_check(data, origin, wheel)
            report.setdefault("saved_processes", {})[origin] = {
                k: data[k]
                for k in (
                    "connections",
                    "installed_drivers",
                    "loaded_drivers",
                    "prefix",
                )
            }
            for result in data["results"]:
                for record in report["histories"]:
                    if record["key"] == result["key"]:
                        record["saved"] = result
        timings["saved"] = time.monotonic() - mark
        report["cell_count"] = len(report["histories"])
        mark = time.monotonic()
        native_check(directory, target, report, cells)
        timings["audit"] = time.monotonic() - mark
        report["status"] = "CHECKED"
    except BaseException as error:
        report.update(
            status="FAILED",
            error_kind=type(error).__name__,
            error=resource.without_secrets(str(error)),
        )
        raise
    finally:
        if "source_cleanup" not in report:
            report["source_cleanup"] = resource.cleanup()
        report["seconds"] = time.monotonic() - started
        report["timings"] = timings
        report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
        event(
            ledger,
            {
                "kind": "s18_native_terminal",
                "directory": str(directory),
                "status": report["status"],
                "cleanup": report["source_cleanup"],
                "seconds": report["seconds"],
            },
        )
    return report


def _saved_facts(record, saved_process, lost):
    """The checker's saved-tail view of one history (raw observations only);
    an absent retained or lost-reply stage is None, never a stand-in record."""
    saved = record["saved"]
    retained = saved["retained"]
    view = {
        "installed_drivers": saved_process["installed_drivers"],
        "loaded_drivers": saved_process["loaded_drivers"],
        "connections": saved_process["connections"],
        "refusals": saved["refusals"],
        "restart": saved["restart"],
        "query": {
            "published": bool(saved["queried"]) and all(saved["queried"].values()),
            "read_terminal": saved["reads"][record["capture"]["generation"]][
                "terminal"
            ],
        },
        "reclaimed": len(saved["removed"]),
        "retained": None,
        "lost_reply": None,
    }
    if retained is not None:
        protected = set(retained["protected_members"])
        view["retained"] = {
            "protected": bool(protected) and retained["decided_while_retained"] == [],
            "removed": [
                x for x in retained["removed_while_retained"] if x[0] in protected
            ],
            "root": "CONSUMER"
            if any("CONSUMER" in root for root in retained["roots"])
            else "NONE",
            "released_removed": len(
                [x for x in retained["removed_after_release"] if x[0] in protected]
            ),
        }
    if lost is not None:
        cut, resumed = lost["cut"], lost["resumed"]
        view["lost_reply"] = {
            "issued": cut["issued"][1] - cut["issued"][0],
            "sink_effects_after_cut": resumed["after_cut"],
            "confirmed_after_cut": resumed["confirmed_after_cut"],
            "statuses": resumed["first"]["statuses"],
            "sink_effects_final": len(resumed["final"]),
            "rows": cut["rows"],
            "positions_final": [row[0] for row in resumed["final"]],
            "commits_final": len({row[1] for row in resumed["final"]}),
        }
    return view


def native_check(directory, target, report, cells):
    """Independent judgement: literal value oracles outside every worker, the S17
    laws over raw rows/files/events, S18 routing, saved-tail observations, lost
    replies, cell inventory and the saved/inventory damages."""
    import _pietto_phase68_slice15_check as s15check
    import _pietto_phase68_slice16_check as s16check
    import _pietto_phase68_slice17_check as check17
    import _pietto_phase68_slice18_check as check
    from _pietto_phase68_slice6_check import expected
    from _pietto_phase68_slice7_cases import manifest as guard_manifest

    def oracle(cell):
        if cell["group"] == "guarded":
            case = next(c for c in guard_manifest() if c["name"] == cell["case"])
            return s16check.encoded(case["rows"]), False
        return expected(target, cell["case"], cell["variant"], None)

    check.check_inventory(report, cells)
    literal, ordered = oracle(
        {"group": "refined", "case": "R2_seven", "variant": "39_values"}
    )
    union = report["union"]
    for blocked in union["blocked"]:
        check.need(
            blocked["result"] == "EXECUTION_DEPENDENCY_MISSING"
            and blocked["loaded"] == []
            and blocked["admissions_before"] == blocked["admissions_after"]
            and blocked["records"] == 0,
            "UNION_NO_FALLBACK",
        )
    for routed in union["routed"]:
        decoded = [[s15check.decode_wire(v) for v in row] for row in routed["wires"]]
        check.need(
            routed["terminal"] == "COMPLETED"
            and set(routed["loaded"]) <= check.ROUTE_MODULES[routed["route"]]
            and s16check.same_rows(decoded, literal, ordered=ordered),
            "UNION_ROUTED",
        )
    check.need(
        sorted(b["route"] for b in union["blocked"]) == sorted(report["routes"])
        and sorted(r["route"] for r in union["routed"]) == sorted(report["routes"]),
        "INVENTORY",
    )
    saved_views, damaged = {}, set()
    for record in report["histories"]:
        captured, recovered, saved = (
            record["capture"],
            record["recover"],
            record["saved"],
        )
        check.need("error" not in saved, "NATIVE_SAVED")
        check.need(
            captured["blocked"][0] == "WAITING_FOR_DOWNSTREAM"
            and captured["still"] == captured["blocked"]
            and all(t == "COMPLETED" for t, _f in captured["others"]),
            "NATIVE_HIGH_WATER",
        )
        check.need(
            recovered["recovered"][0] == "COMPLETED"
            and recovered["original"][0] == "INTERRUPTED"
            and recovered["original"][1]["transaction"] == "UNKNOWN"
            and recovered["coverage"],
            "NATIVE_R2",
        )
        check.need(
            all(t == "COMPLETED" for t, _f in saved["published"])
            and saved["main_present"]
            and saved["old_present"]
            and (saved["during"] or saved["after"]),
            "NATIVE_SAVED_GC",
        )
        main = saved["reads"][captured["generation"]]
        decoded = [[s15check.decode_wire(v) for v in row] for row in main["wires"]]
        check.need(
            main["terminal"] == "COMPLETED"
            and s16check.same_rows(decoded, literal, ordered=ordered),
            "NATIVE_READ_VALUES",
        )
        retained = saved["retained"]
        retained_generation = retained["generation"] if retained else None
        for key, _job, generation in captured["distinct"]:
            if generation == retained_generation:
                continue
            cell_ = next(d for d in s17.DISTINCT if key.endswith(s16.label(d)))
            literal_, ordered_ = oracle(cell_)
            got = saved["reads"][generation]
            decoded_ = [[s15check.decode_wire(v) for v in row] for row in got["wires"]]
            check.need(
                got["terminal"] == "COMPLETED"
                and s16check.same_rows(decoded_, literal_, ordered=ordered_),
                "NATIVE_DISTINCT_VALUES",
            )
        lost = report["lost_replies"].get(record["key"])
        view = _saved_facts(record, report["saved_processes"][record["origin"]], lost)
        check.need(
            (view["retained"] is not None) is (record["entry"] == "bundle")
            and (view["lost_reply"] is not None)
            is ((record["origin"], record["entry"]) == ("installed", "bundle")),
            "INVENTORY",
        )
        check.check_saved(view)
        record["saved_view"] = view
        saved_views[record["key"]] = view
        data = check17.load(saved["backup"])
        units = {
            h: u
            for part in (captured["units"], recovered["units"], saved["units"])
            for h, u in part.items()
            if u["vector"] is not None
        }
        evidence = {
            "data": data,
            "units": units,
            "policy": {
                "connections": 3,
                "workers": 3,
                "memory": 512 * 1024 * 1024,
                "durable": 128 * 1024 * 1024,
                "operations": 65536,
            },
            "files": check17.inventory(captured["workspace"]),
            "killed": [captured["attempt"]],
            "acked": set(saved["acked"]),
        }
        record["checked"] = check17.check_all(evidence)
        if record["route"] not in damaged:
            damaged.add(record["route"])
            record["damages17"] = {
                kind: check17.rejects(kind, evidence)
                for kind in check17.DAMAGES
                if kind
                not in (
                    "D07_stale_snapshot_read",
                    "D10_replacement_object",
                    "D11_credited_not_removed",
                    "D14_promoted_unlink",
                )
            }
    for lost in report["lost_replies"].values():
        cut, resumed = lost["cut"], lost["resumed"]
        check.need(
            cut["connections"] == []
            and cut["installed_drivers"] == []
            and cut["loaded_drivers"] == []
            and resumed["connections"] == []
            and resumed["installed_drivers"] == []
            and resumed["loaded_drivers"] == [],
            "SAVED_SOURCE_ACCESS",
        )
    if saved_views:
        sample = next(
            (v for v in saved_views.values() if v["lost_reply"] is not None),
            next(iter(saved_views.values())),
        )
        report["damages18"] = {
            "D7_hidden_source_access": check.rejects(
                "D7_hidden_source_access", {"saved": sample}
            ),
            "D8_cell_removed": check.rejects(
                "D8_cell_removed", {"report": report, "requested": cells}
            ),
        }
    return report
