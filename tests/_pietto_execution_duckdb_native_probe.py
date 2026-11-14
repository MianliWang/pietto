"""The producer and runner of the Phase79 S06 native qualification
(preregistration v5, sections 6 to 8).

`unit` runs one installation unit in the preregistered order: the run-start
check, the run's frozen.sha256, the checker's self-test, the oracle's
regeneration, the identity record, every cell in a fresh `-I -B`
interpreter (C12 in a network namespace with empty HOME, TMPDIR and working
directory), then the checker. `identity` and `cell` are those fresh
interpreters: they write raw facts only, and nothing here judges a cell."""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import sysconfig
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.append(str(TESTS))

import _pietto_execution_duckdb_native_cases as cases  # noqa: E402

NAMES = {
    "cases": "_pietto_execution_duckdb_native_cases.py",
    "oracle": "_pietto_execution_duckdb_native_oracle.py",
    "producer": "_pietto_execution_duckdb_native_probe.py",
    "checker": "_pietto_execution_duckdb_native_check.py",
}
S06 = Path(".cache/lane-p79/s06")
SPEC = Path("docs/spec/duckdb-arrow-route-v1.md")
ALLOWLIST = Path("ci/phase67-arrow-compatibility-requirements.txt")
CHILD_SHA256 = "e88dafbbc7e4a06a442bc61f5c1ca4c5ea2909398d019f404861143bd600db77"
UNIT_SECONDS = 30 * 60
RUN = (
    "import importlib, sys; sys.path.insert(0, sys.argv[1]); "
    "sys.exit(importlib.import_module(sys.argv[2]).main(sys.argv[3:]))"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _modules(*roots: str) -> list[str]:
    return sorted(name for name in sys.modules if name.partition(".")[0] in roots)


# The runner (section 8).


def _env(home: Path, tmp: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }


def _sums(path: Path) -> dict[str, str]:
    sums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        sums[name] = digest
    return sums


def _first_entry(record: Path) -> dict[str, str]:
    """The `- key: value` lines of the freeze record's first `## Entry`."""
    parts = re.split(r"^## Entry ", record.read_text(encoding="utf-8"), flags=re.M)
    lines = parts[1].splitlines() if len(parts) > 1 else []
    return dict(re.findall(r"^- ([^:]+): (\S+)$", "\n".join(lines), flags=re.M))


def _child(prereg: Path) -> bytes:
    """Section 4d: the lines strictly between the first line exactly
    ```python after the 4d heading and the next line exactly ```."""
    lines = prereg.read_text(encoding="utf-8").split("\n")
    heading = next(i for i, line in enumerate(lines) if line.startswith("### 4d."))
    opening = next(i for i in range(heading, len(lines)) if lines[i] == "```python")
    closing = next(i for i in range(opening + 1, len(lines)) if lines[i] == "```")
    return "".join(line + "\n" for line in lines[opening + 1 : closing]).encode()


def _start(lane: Path, evidence: Path, erratum: str | None) -> list[str]:
    """Section 0's run-start check and this run's frozen.sha256."""
    frozen = lane / S06 / "frozen"
    start = evidence / "start"
    start.mkdir()
    sources = {
        "frozen-preregistration-v5.md": frozen / "preregistration-v5.md",
        "lane-preregistration-v5.md": lane / S06 / "preregistration-v5.md",
        "freeze-record.md": frozen / "freeze-record.md",
        "FROZEN.sha256": frozen / "FROZEN.sha256",
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        return [f"missing {path}" for path in missing]
    for name, source in sources.items():
        shutil.copyfile(source, start / name)
    digests = {name: _sha(start / name) for name in sources}
    (start / "copies.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in digests.items()),
        encoding="utf-8",
    )
    entry = _first_entry(start / "freeze-record.md")
    voids = [
        f"{name} is not the v5 of the freeze record's first entry"
        for name in ("frozen-preregistration-v5.md", "lane-preregistration-v5.md")
        if digests[name] != entry.get("preregistration-v5.md")
    ]
    if digests["FROZEN.sha256"] != entry.get("FROZEN.sha256"):
        voids.append("FROZEN.sha256 is not the one of the freeze record's first entry")
    if voids:
        return voids
    try:
        child = _child(start / "frozen-preregistration-v5.md")
    except StopIteration:
        return ["no C02a child in the frozen v5"]
    (evidence / "c02a-child.py").write_bytes(child)
    files = {NAMES[role]: TESTS / NAMES[role] for role in NAMES}
    files.update(
        {
            "expected.json": frozen / "expected.json",
            "c02a-child.py": evidence / "c02a-child.py",
            "preregistration-v5.md": start / "frozen-preregistration-v5.md",
        }
    )
    sums = {name: _sha(path) for name, path in files.items()}
    (evidence / "frozen.sha256").write_text(
        "".join(f"{sums[name]}  {path}\n" for name, path in files.items()),
        encoding="utf-8",
    )
    if sums["c02a-child.py"] != CHILD_SHA256:
        voids.append("C02a's child digest differs from section 4d")
    pinned = _sums(start / "FROZEN.sha256")
    if sorted(pinned) != sorted(sums):
        voids.append("FROZEN.sha256 names other files")
    for name, digest in sums.items():
        if pinned.get(name) == digest:
            continue
        if name == NAMES["checker"] and erratum and Path(erratum).is_file():
            shutil.copyfile(erratum, start / "erratum-approval")
            continue
        voids.append(f"{name} differs from FROZEN.sha256")
    return voids


def _void(evidence: Path, reasons: list[str]) -> int:
    verdict = {"unit": evidence.name, "verdict": "VOID", "void": reasons}
    (evidence / "void.json").write_text(
        json.dumps(verdict, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(verdict))
    return 2


def _log(evidence: Path, step: str, result: Any) -> None:
    with (evidence / "children.jsonl").open("a", encoding="utf-8") as log:
        entry = {
            "step": step,
            "rc": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }
        log.write(json.dumps(entry) + "\n")


def _module(python: str, name: str, *argv: str, env: dict, timeout: float) -> Any:
    command = [python, "-I", "-B", "-c", RUN, str(TESTS), name, *argv]
    return subprocess.run(
        command, capture_output=True, text=True, env=env, timeout=timeout
    )


def _emit(out: Path, unit: str, cell: str, sub: str, facts: dict) -> None:
    record = {"unit": unit, "cell": cell, "sub": sub, "facts": facts}
    with out.open("a", encoding="utf-8") as records:
        records.write(json.dumps(record, default=repr) + "\n")


def unit_main(args: argparse.Namespace) -> int:
    unit = args.unit
    lane = Path(args.lane).resolve()
    tree = Path(args.tree).resolve() if args.tree else lane
    site = str(Path(args.site).resolve()) if args.site else None
    if (unit == "U1") != (site is not None) or (unit in ("U0", "U1") and tree != lane):
        raise SystemExit("U1 alone takes --site; U0 and U1 run the lane's own tree")
    if unit in ("U2", "U3") and not args.wheel:
        raise SystemExit("U2 and U3 take --tree and --wheel")
    evidence = Path(args.run).resolve() / unit
    evidence.mkdir(parents=True)
    for name in ("home", "tmp", "work", "shadow"):
        (evidence / name).mkdir()
    began = time.monotonic()
    python = sys.executable
    producer = str(TESTS / NAMES["producer"])
    argv1 = {"U0": [str(tree / "src")], "U1": [str(tree / "src"), site]}.get(unit, [])
    env = _env(evidence / "home", evidence / "tmp")
    frozen = lane / S06 / "frozen"

    def remaining() -> float:
        return began + UNIT_SECONDS - time.monotonic()

    voids = _start(lane, evidence, args.erratum)
    if voids:
        return _void(evidence, voids)
    try:
        result = _module(
            python,
            "_pietto_execution_duckdb_native_check",
            "selftest",
            str(frozen / "expected.json"),
            env=env,
            timeout=remaining(),
        )
        _log(evidence, "self-test", result)
        if result.returncode != 0:
            return _void(evidence, ["the checker's self-test failed"])
        result = _module(
            python,
            "_pietto_execution_duckdb_native_oracle",
            str(evidence / "expected.json"),
            env=env,
            timeout=remaining(),
        )
        _log(evidence, "oracle", result)
        regenerated = evidence / "expected.json"
        if result.returncode != 0 or not regenerated.is_file():
            return _void(evidence, ["the oracle did not regenerate expected.json"])
        if regenerated.read_bytes() != (frozen / "expected.json").read_bytes():
            return _void(evidence, ["the regenerated expected.json differs"])
        identity = [python, "-I", "-B", producer, "identity", "--unit", unit]
        identity += [
            "--evidence",
            str(evidence),
            "--lane",
            str(lane),
            "--tree",
            str(tree),
        ]
        identity += [
            "--argv1",
            json.dumps(argv1),
            "--out",
            str(evidence / "identity.json"),
        ]
        identity += ["--site", site] if site else []
        identity += ["--wheel", str(Path(args.wheel).resolve())] if args.wheel else []
        uv = {
            name: value for name, value in os.environ.items() if name.startswith("UV_")
        }
        result = subprocess.run(
            identity,
            capture_output=True,
            text=True,
            env={**env, **uv},
            timeout=remaining(),
        )
        _log(evidence, "identity", result)
        result = _module(
            python,
            "_pietto_execution_duckdb_native_check",
            "identity",
            str(evidence),
            env=env,
            timeout=remaining(),
        )
        _log(evidence, "identity check", result)
        if result.returncode != 0:
            return _void(evidence, [f"identity: {result.stdout.strip()}"])
        records = evidence / "facts.jsonl"
        records.touch()
        if unit == "U0":
            for cell in cases.CELLS:
                if cell not in cases.U0_CELLS:
                    _emit(records, unit, cell, cases.SKIP, {"skip": cases.U0_SKIP})
                    print(f"SKIP {cell}: {cases.U0_SKIP}")
        marker = repr(str(evidence / "shadow-marker"))
        (evidence / "shadow" / "_duckdb.py").write_text(
            f"open({marker}, 'w').close()\nraise RuntimeError('the shadow ran')\n",
            encoding="utf-8",
        )
        for cell, subs, shadowed in cases.processes(unit):
            path = [str(evidence / "shadow")] * shadowed + argv1
            command = [python, "-I", "-B", producer, "cell", "--unit", unit]
            command += ["--cell", cell, "--subs", json.dumps(list(subs))]
            command += [
                "--evidence",
                str(evidence),
                "--lane",
                str(lane),
                "--tree",
                str(tree),
            ]
            command += ["--path", json.dumps(path), "--argv1", json.dumps(argv1)]
            command += ["--out", str(records)]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=env,
                cwd=evidence / "work",
                timeout=remaining(),
            )
            _log(evidence, f"{cell} {','.join(subs)}", result)
        if unit != "U0":
            _c12(python, producer, unit, evidence, lane, tree, argv1, env, remaining())
    except subprocess.TimeoutExpired:
        return _void(evidence, ["the unit exceeded 30 minutes"])
    result = _module(
        python,
        "_pietto_execution_duckdb_native_check",
        "check",
        str(evidence),
        env=env,
        timeout=600,
    )
    _log(evidence, "check", result)
    print(result.stdout.strip())
    return result.returncode


def _c12(
    python: str,
    producer: str,
    unit: str,
    evidence: Path,
    lane: Path,
    tree: Path,
    argv1: list[str],
    env: dict,
    timeout: float,
) -> None:
    """C07, C10, C11 and C14 again in a new network namespace (only `lo`),
    with new empty HOME, TMPDIR and working directory; NOT_OBSERVED (law 7)
    when the namespace cannot be made."""
    dirs = {name: evidence / "c12" / name for name in ("home", "tmp", "cwd")}
    for directory in dirs.values():
        directory.mkdir(parents=True)
    unshare = ["unshare", "--user", "--map-root-user", "--net"]
    try:
        made = subprocess.run(
            [*unshare, "true"], capture_output=True, text=True, env=env, timeout=60
        )
        reason = None if made.returncode == 0 else made.stderr.strip()[-500:]
    except (OSError, subprocess.TimeoutExpired) as error:
        reason = repr(error)
    records = evidence / "facts.jsonl"
    if reason is not None:
        for sub in cases.CELLS["C12"]:
            facts = {"namespace": "NOT_OBSERVED", "reason": reason}
            _emit(records, unit, "C12", sub, facts)
        return
    command = [*unshare, python, "-I", "-B", producer, "cell", "--unit", unit]
    command += ["--cell", "C12", "--subs", json.dumps(list(cases.CELLS["C12"]))]
    command += ["--evidence", str(evidence), "--lane", str(lane), "--tree", str(tree)]
    command += ["--path", json.dumps(argv1), "--argv1", json.dumps(argv1)]
    command += ["--out", str(records), "--host-netns", os.readlink("/proc/self/ns/net")]
    command += ["--dirs", json.dumps({name: str(path) for name, path in dirs.items()})]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env={**env, "HOME": str(dirs["home"]), "TMPDIR": str(dirs["tmp"])},
        cwd=dirs["cwd"],
        timeout=timeout,
    )
    _log(evidence, "C12", result)


# The identity record (section 7).


def _verified(entry: Any) -> bool:
    try:
        data = Path(str(entry.locate())).read_bytes()
    except OSError:
        return False
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return entry.hash.mode == "sha256" and entry.hash.value == digest.decode()


def _record(dist: Any) -> dict[str, Any]:
    files = list(dist.files or [])
    hashed = [entry for entry in files if entry.hash is not None]

    def digest(name: str) -> str | None:
        found = [e for e in files if str(e).endswith(".dist-info/" + name)]
        return _sha(Path(str(found[0].locate()))) if found else None

    return {
        "version": dist.version,
        "record_hashed": len(hashed),
        "record_bad": [str(entry) for entry in hashed if not _verified(entry)],
        "metadata_sha256": digest("METADATA"),
        "record_sha256": digest("RECORD"),
    }


def _dist(name: str, modules: tuple[str, ...]) -> dict[str, Any] | None:
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None
    fact = _record(dist)
    base = Path(str(dist.locate_file("")))
    listed = {str(entry) for entry in dist.files or []}
    origins = {}
    for module in modules:
        spec = importlib.util.find_spec(module)
        origins[module] = None if spec is None else spec.origin
    wheel = dist.read_text("WHEEL") or ""
    fact.update(
        base=str(base),
        tags=[
            line.split(":", 1)[1].strip()
            for line in wheel.splitlines()
            if line.startswith("Tag:")
        ],
        files=origins,
        in_record={
            module: origin is not None and os.path.relpath(origin, base) in listed
            for module, origin in origins.items()
        },
    )
    return fact


def _engine() -> dict[str, Any]:
    """pragma_version() and the platform, on a separate default connection
    that is not a route session."""
    connection = importlib.import_module("duckdb").connect(":memory:")
    try:
        rows = connection.sql("SELECT library_version, source_id FROM pragma_version()")
        version = [list(row) for row in rows.fetchall()]
        found = None
        for query in ("SELECT platform FROM pragma_platform()", "PRAGMA platform"):
            try:
                found = connection.execute(query).fetchall()[0][0]
                break
            except Exception:
                continue
    finally:
        connection.close()
    return {
        "pragma_version": version[0] if len(version) == 1 else version,
        "platform": found,
    }


def _git(tree: Path) -> dict[str, Any]:
    def run(*command: str) -> bytes | None:
        result = subprocess.run(
            ["git", "-C", str(tree), *command], capture_output=True, timeout=120
        )
        return result.stdout if result.returncode == 0 else None

    head = run("rev-parse", "HEAD")
    diff = run("diff", "--binary", "HEAD")
    untracked = run("ls-files", "--others", "--exclude-standard", "-z")
    return {
        "head": head.decode().strip() if head else None,
        "diff_sha256": None if diff is None else hashlib.sha256(diff).hexdigest(),
        "untracked_sha256": None
        if untracked is None
        else hashlib.sha256(b"\0".join(sorted(untracked.split(b"\0")))).hexdigest(),
    }


def _uv(tree: Path) -> dict[str, Any]:
    env = {**os.environ, "UV_OFFLINE": "1", "UV_PYTHON_DOWNLOADS": "never"}
    command = ["uv", "export", "--locked", "--no-dev", "--no-emit-project"]
    command += ["--extra", "arrow", "--extra", "execute-duckdb"]
    try:
        version = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, timeout=60
        )
        export = subprocess.run(
            command, cwd=tree, env=env, capture_output=True, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"error": repr(error)}
    return {
        "version": version.stdout.strip(),
        "export_rc": export.returncode,
        "export_sha256": hashlib.sha256(export.stdout).hexdigest(),
        "lock_sha256": _sha(tree / "uv.lock"),
        "allowlist_sha256": _sha(tree / ALLOWLIST),
    }


def _fstype(path: Path) -> str | None:
    text, best = str(path.resolve()), ("", None)
    for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
        _device, point, kind, *_rest = line.split()
        inside = text == point or text.startswith(point.rstrip("/") + "/")
        if inside and len(point) >= len(best[0]):
            best = (point, kind)
    return best[1]


def identity_main(args: argparse.Namespace) -> int:
    sys.path[:0] = json.loads(args.argv1)
    unit = args.unit
    lane, tree = Path(args.lane).resolve(), Path(args.tree).resolve()
    memory = dict(
        line.split(":", 1)
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
        if ":" in line
    )
    uname = os.uname()
    executable = Path(sys.executable).resolve()
    spec = importlib.util.find_spec("pietto")
    pietto: dict[str, Any] = {
        "file": None if spec is None else spec.origin,
        "tree": str(tree),
        "lane": str(lane),
        "git": _git(tree),
        "record_hashed": None,
        "record_bad": None,
    }
    if unit in ("U2", "U3"):
        pietto.update(_record(importlib.metadata.distribution("pietto")))
        wheel = Path(args.wheel)
        pietto.update(wheel={"name": wheel.name, "sha256": _sha(wheel)}, uv=_uv(tree))
    record = {
        "host": {
            "uname": f"{uname.sysname} {uname.release} {uname.machine}",
            "proc_version": Path("/proc/version").read_text(encoding="utf-8").strip(),
            "cpus": os.cpu_count(),
            "MemTotal": memory.get("MemTotal", "").strip(),
            "MemAvailable": memory.get("MemAvailable", "").strip(),
            "load1": os.getloadavg()[0],
            "filesystem": _fstype(Path(args.evidence)),
        },
        "python": {
            "version": platform.python_version(),
            "version_text": sys.version,
            "executable": str(executable),
            "executable_sha256": _sha(executable),
            "cache_tag": sys.implementation.cache_tag,
            "platform": sysconfig.get_platform(),
            "glibc": os.confstr("CS_GNU_LIBC_VERSION"),
            "isolated": sys.flags.isolated,
            "dont_write_bytecode": sys.flags.dont_write_bytecode,
            "no_user_site": sys.flags.no_user_site,
            "prefix": sys.prefix,
        },
        "env": {
            name: os.environ.get(name)
            for name in ("PATH", "HOME", "TMPDIR", "LANG", "PYTHONPATH")
            + ("PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE")
        },
        "sys_path": sys.path,
        "spec_sha256": _sha(tree / SPEC),
        "unit_root": args.site if unit == "U1" else sys.prefix,
        "pietto": pietto,
        "duckdb": _dist("duckdb", ("duckdb", "_duckdb")),
        "pyarrow": _dist("pyarrow", ("pyarrow.lib",)),
    }
    if record["duckdb"] is not None:
        record["duckdb"].update(_engine())
    Path(args.out).write_text(
        json.dumps(record, indent=1, default=repr) + "\n", encoding="utf-8"
    )
    return 0


# The cells (section 4): each returns the raw facts of one sub-case.


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        from pietto import execution
        from pietto.execution import _duckdb as route

        self.execution, self.route = execution, route
        self.unit = args.unit
        self.evidence = Path(args.evidence)
        self.lane, self.tree = Path(args.lane), Path(args.tree)
        self.argv1 = json.loads(args.argv1)
        self.work = self.evidence / "work" / f"{args.cell}-{os.getpid()}"
        self.work.mkdir(parents=True)
        self._queries: dict[tuple[str, str], Any] = {}

    @property
    def pa(self) -> Any:
        return importlib.import_module("pyarrow")

    def query(self, project: str, body: str) -> Any:
        if (project, body) not in self._queries:
            root = cases.write_project(
                self.work / f"q{len(self._queries)}", project, body
            )
            self._queries[(project, body)] = self.execution.compile_query(
                root,
                module="main.pietto",
                kind="query" if body.startswith("query") else "table",
                name="result",
                dialect="duckdb",
                emission_contract="contract.json",
            )
        return self._queries[(project, body)]

    def handle(self, query: Any, table: Any, **arguments: Any) -> Any:
        arguments.setdefault(
            "parameters", {"min_amount": 10} if query.parameters else None
        )
        return self.execution.execute(
            query,
            route="duckdb_arrow",
            access=self.execution.DuckDBArrowInput("orders", table),
            premise=None,
            **arguments,
        )


def _raised(error: BaseException) -> dict[str, Any]:
    fact: dict[str, Any] = {"class": type(error).__name__}
    for name in ("code", "detail"):
        if hasattr(error, name):
            fact[name] = getattr(error, name)
    failure = getattr(error, "failure", None)
    if failure is not None:
        fact.update(phase=failure.phase, sqlstate=failure.sqlstate, cause=failure.cause)
    return fact


def _failure(failure: Any) -> Any:
    if failure is None:
        return None
    return [
        failure.code,
        failure.detail,
        failure.phase,
        failure.sqlstate,
        failure.cause,
    ]


def _outcome(handle: Any) -> list[Any]:
    o = handle.outcome
    return [
        o.end,
        o.transaction,
        o.cleanup,
        o.cancel_requested,
        o.cancel_sent,
        o.cancel_observed,
        o.deadline_expired,
        o.batches,
    ]


def _recorded(handle: Any) -> dict[str, Any]:
    o = handle.outcome
    return {
        "attempt": o.attempt,
        "source": o.source,
        "delivery": o.delivery,
        "rows": o.rows,
        "bytes": o.bytes,
        "primary": _failure(o.primary),
        "cleanup_failures": [_failure(f) for f in o.cleanup_failures],
    }


def _schema(schema: Any) -> list[list[Any]]:
    return [[field.name, str(field.type), field.nullable] for field in schema]


def _attempt(ctx: Context, handle: Any, schema: bool = False) -> dict[str, Any]:
    """Enter the handle and read every batch: rows as typed values, the
    batches' schemas, the AttemptFailed and O."""
    pa = ctx.pa
    facts: dict[str, Any] = {}
    if schema:
        facts["schema"] = _schema(pa.schema(handle))
    rows: list[Any] = []
    schemas: list[Any] = []
    raised = None
    try:
        with handle as result:
            for batch in result:
                record = pa.record_batch(batch)
                if _schema(record.schema) not in schemas:
                    schemas.append(_schema(record.schema))
                rows += [cases.encode_row(row.values()) for row in record.to_pylist()]
    except ctx.execution.AttemptFailed as error:
        facts["raised_at"] = time.monotonic()
        raised = _raised(error)
    facts.update(
        raised=raised,
        O=_outcome(handle),
        rows=rows,
        batch_schemas=schemas,
        recorded=_recorded(handle),
    )
    return facts


def _execute(ctx: Context, query: Any, table: Any, **arguments: Any) -> tuple[Any, Any]:
    try:
        return ctx.handle(query, table, **arguments), None
    except BaseException as error:
        return None, _raised(error)


def _refusal(call: Any) -> Any:
    try:
        value = call()
    except BaseException as error:
        return _raised(error)
    getattr(value, "close", lambda: None)()
    return None


@contextlib.contextmanager
def _patched(target: Any, **values: Any) -> Any:
    saved = {name: getattr(target, name) for name in values}
    for name, value in values.items():
        setattr(target, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(target, name, value)


class _Connection:
    """J2: the attempt's real connection, recording what the route asks of it
    and running the cell's hooks; a hook's exception is recorded, never
    raised into the route."""

    def __init__(self, connection: Any, recorder: _Recorder) -> None:
        self._connection, self._recorder, self._registered = connection, recorder, False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def _hook(self, name: str) -> None:
        hook = self._recorder.hooks.get(name)
        if hook is not None:
            try:
                hook(self._connection)
            except BaseException as error:
                self._recorder.errors.append([name, type(error).__name__])

    def execute(self, query: str, *args: Any, **kwargs: Any) -> Any:
        if query == "SET enable_external_access = false":
            self._hook("prelock")
        return self._connection.execute(query, *args, **kwargs)

    def sql(self, query: str, *args: Any, **kwargs: Any) -> Any:
        if self._registered:
            self._hook("statement")
        return self._connection.sql(query, *args, **kwargs)

    def register(self, name: str, table: Any) -> Any:
        self._recorder.calls.append(["register", name])
        if self._recorder.register_raises:
            raise RuntimeError("register")
        self._hook("register")
        result = self._connection.register(name, table)
        self._registered = True
        return result

    def interrupt(self) -> Any:
        self._recorder.calls.append(["interrupt"])
        return self._connection.interrupt()

    def unregister(self, name: str) -> Any:
        self._recorder.calls.append(["unregister", name])
        self._hook("unregister")
        return self._connection.unregister(name)

    def close(self) -> Any:
        self._recorder.calls.append(["close"])
        return self._connection.close()


class _Driver:
    def __init__(self, driver: Any, recorder: _Recorder) -> None:
        self._driver, self._recorder = driver, recorder

    def __getattr__(self, name: str) -> Any:
        return getattr(self._driver, name)

    def connect(self, database: str) -> _Connection:
        self._recorder.calls.append(["connect", database])
        connection = self._driver.connect(database)
        self._recorder.connections.append(connection)
        return _Connection(connection, self._recorder)


class _Recorder:
    """J2 for one call: `route._driver` returns the real driver wrapped, as
    S04's `_recorded` does."""

    def __init__(self, route: Any) -> None:
        self.route = route
        self.calls: list[list[str]] = []
        self.hooks: dict[str, Any] = {}
        self.errors: list[list[str]] = []
        self.connections: list[Any] = []
        self.register_raises = False

    def __enter__(self) -> _Recorder:
        self.real = self.route._driver
        self.route._driver = lambda: _Driver(self.real(), self)
        return self

    def __exit__(self, *exc: Any) -> None:
        self.route._driver = self.real


class _Threads:
    """The route's `threading`, recording each thread it creates."""

    def __init__(self) -> None:
        self.created: list[tuple[Any, threading.Thread]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(threading, name)

    def Thread(self, *args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(*args, **kwargs)
        self.created.append((kwargs.get("target"), thread))
        return thread


def _slow(recorder: _Recorder, handle: Any) -> tuple[Any, Any, list[float]]:
    """J4: the SLOW statement reads `pietto_running`, an endless Arrow stream
    registered on the attempt's own connection (DuckDB's Python UDFs need
    NumPy, which the execute-duckdb closure lacks). The engine pulls each
    batch from the generator: the first sets `running`; 30 s after it, the
    watchdog fails the statement."""
    pa = importlib.import_module("pyarrow")
    running, tripped, first = threading.Event(), threading.Event(), []
    batch = pa.record_batch([pa.array([0], pa.int64())], names=["i"])

    def batches() -> Any:
        while True:
            now = time.monotonic()
            if not first:
                first.append(now)
            elif now > first[0] + cases.WATCHDOG_SECONDS:
                tripped.set()
                raise TimeoutError("watchdog")
            running.set()
            yield batch

    recorder.hooks["register"] = lambda connection: connection.register(
        "pietto_running", pa.RecordBatchReader.from_batches(batch.schema, batches())
    )
    handle._owner._sql = cases.SLOW_SQL
    return running, tripped, first


def c01(ctx: Context, sub: str) -> dict:
    query = ctx.query("P0", cases.P_BODY)
    access = ctx.execution.DuckDBArrowInput("orders", object())
    raised = _refusal(
        lambda: ctx.execution.execute(
            query, route="duckdb_arrow", access=access, premise=None
        )
    )
    return {"raised": raised, "modules": _modules("duckdb", "_duckdb", "pyarrow")}


def c02a(ctx: Context, sub: str) -> dict:
    root = cases.write_project(ctx.work / "c02a", "P0", cases.q_body(">="))
    child = ctx.evidence / "c02a-child.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(child), json.dumps(ctx.argv1), str(root)],
        capture_output=True,
        text=True,
        cwd=ctx.work,
        timeout=300,
    )
    try:
        printed = json.loads(result.stdout)
    except ValueError:
        printed = {}
    return {
        "rc": result.returncode,
        "seen": printed.get("seen"),
        "loaded": printed.get("loaded"),
        "paths": {
            "argv1": ctx.argv1,
            "path": printed.get("path"),
            "pietto": printed.get("pietto"),
            "tree": str(ctx.tree),
            "lane": str(ctx.lane),
            "prefix": sys.prefix,
        },
        "child_sha256": _sha(child),
        "stderr": result.stderr[-2000:],
    }


def c02b(ctx: Context, sub: str) -> dict:
    x = ctx.execution
    query = ctx.query("P0", cases.q_body(">="))
    table = cases.table(ctx.pa, cases.T1)
    short = table.drop_columns(["ok"])
    limits = x.ExecutionLimits
    ok = {
        "route": "duckdb_arrow",
        "access": x.DuckDBArrowInput("orders", table),
        "premise": None,
        "parameters": {"min_amount": 1},
    }
    changes = [
        {"access": x.DuckDBArrowInput("Orders", table)},
        {"access": x.DuckDBArrowInput("orders ", table)},
        {"isolation": "serializable"},
        {"isolation": 1},
        {"limits": limits(batch_rows=0)},
        {"limits": limits(seconds=float("nan"))},
        {"access": x.DuckDBArrowInput("orders", short)},
        {"access": x.DuckDBArrowInput("other", table), "isolation": "serializable"},
        {"isolation": "x", "limits": limits(batch_rows=0)},
        {"limits": limits(batch_rows=0), "access": x.DuckDBArrowInput("orders", short)},
    ]
    seen: list[Any] = []
    for change in changes:
        raised = _refusal(lambda change=change: x.execute(query, **{**ok, **change}))
        seen.append(
            None
            if raised is None
            else [raised["class"], raised.get("code"), raised.get("detail")]
        )
    handle = x.execute(query, **ok)
    end = handle.outcome.end
    handle.close()
    return {"seen": seen, "end": end, "modules": _modules("duckdb", "_duckdb")}


def c02c(ctx: Context, sub: str) -> dict:
    x = ctx.execution
    query = ctx.query("P0", cases.q_body(">="))
    table = cases.table(ctx.pa, cases.T5)
    captured: list[Any] = []

    def recorder(*args: Any) -> Any:
        captured.append(len(args))
        return None, "PIETTO_S06_RECORDER"

    def unloadable(name: str) -> Any:
        raise ImportError(name)

    patch = {
        "a": {"PYARROW": ("pietto-no-such-arrow", "26.0.1", "pyarrow")},
        "b": {"PYARROW": ("pyarrow", "0.0.1", "pyarrow")},
        "c": {"owner_versions": lambda *_: frozenset()},
        "d": {"_owned": unloadable},
    }[sub]
    with _patched(ctx.route, capture=recorder, **patch):
        raised = _refusal(
            lambda: x.execute(
                query,
                route="duckdb_arrow",
                access=x.DuckDBArrowInput("orders", table),
                premise=None,
                parameters={"min_amount": 1},
            )
        )
    return {"raised": raised, "captured": len(captured)}


def c03(ctx: Context, sub: str) -> dict:
    route = ctx.route
    owners = route.owner_versions

    def unowned(distribution: str, module: Any) -> Any:
        if getattr(module, "__name__", None) == "_duckdb":
            return frozenset()
        return owners(distribution, module)

    patch = {
        "a": {"DRIVER": ("pietto-no-such-duckdb", "2.0.0", "duckdb")},
        "b": {"DRIVER": ("duckdb", "1.0.0", "duckdb")},
        "c": {},
        "d": {"owner_versions": unowned},
    }[sub]
    with _Recorder(route) as recorder, _patched(route, **patch):
        facts = _attempt(
            ctx,
            ctx.handle(ctx.query("P0", cases.P_BODY), cases.table(ctx.pa, cases.T5)),
        )
    facts["calls"] = recorder.calls
    if sub == "c":
        facts["modules"] = _modules("duckdb", "_duckdb")
        facts["marker"] = (ctx.evidence / "shadow-marker").exists()
        facts["sys_path_head"] = sys.path[:2]
    return facts


def c04(ctx: Context, sub: str) -> dict:
    with (
        _Recorder(ctx.route) as recorder,
        _patched(ctx.route, ENGINE=[("v2.0.0", "0000000000")]),
    ):
        facts = _attempt(
            ctx,
            ctx.handle(ctx.query("P0", cases.P_BODY), cases.table(ctx.pa, cases.T5)),
        )
    facts["calls"] = recorder.calls
    return facts


def c05(ctx: Context, sub: str) -> dict:
    pa = ctx.pa
    query = ctx.query("P0", cases.q_body(">="))
    sizes: dict[str, Any] = {}
    target = None
    if sub in ("a", "b"):
        table = cases.table(
            pa, [(1, 5, None, True, 0.0)] * (cases.MAX_ROWS + (sub == "b"))
        )
    elif sub in ("c", "d"):
        target = cases.MAX_BYTES + (sub == "d")
        table = cases.sized(pa, target)
    else:
        target = cases.MAX_BYTES + 1
        table, sizes["five_nbytes"] = cases.padded(pa)
    sizes.update(rows=table.num_rows, nbytes=table.nbytes, columns=table.column_names)
    if target is not None and (
        table.nbytes != target or sizes.get("five_nbytes", 0) > cases.MAX_BYTES
    ):
        return {"fixture_miss": sizes}
    with _Recorder(ctx.route) as recorder:
        handle, raised = _execute(ctx, query, table, parameters={"min_amount": 1})
        facts: dict[str, Any] = {"raised": raised}
        if handle is not None:
            facts["end"] = handle.outcome.end
            handle.close()
    facts.update(
        calls=recorder.calls, modules=_modules("duckdb", "_duckdb"), sizes=sizes
    )
    return facts


def c06(ctx: Context, sub: str) -> dict:
    query = ctx.query("P2" if sub.startswith("P2:") else "P0", cases.q_body(">="))
    table = cases.forged(ctx.pa, sub)
    with _Recorder(ctx.route) as recorder:
        handle, raised = _execute(ctx, query, table, parameters={"min_amount": 1})
        if handle is not None:
            handle.close()
    return {
        "raised": raised,
        "calls": recorder.calls,
        "modules": _modules("duckdb", "_duckdb"),
    }


def c07(ctx: Context, sub: str) -> dict:
    if sub == "P":
        query, arguments = ctx.query("P0", cases.P_BODY), {}
    else:
        query = ctx.query("P0", cases.q_body("=="))
        arguments = {"parameters": {"min_amount": 10}}
    with _Recorder(ctx.route) as recorder:
        handle = ctx.handle(query, cases.table(ctx.pa, cases.T5), **arguments)
        facts = _attempt(ctx, handle, schema=True)
    facts["calls"] = recorder.calls
    return facts


def c08(ctx: Context, sub: str) -> dict:
    operator, value, order = sub.split(" ")
    rows = (*cases.T5, cases.ROW6)
    if order == "reversed":
        rows = rows[::-1]
    query = ctx.query("P1", cases.q_body(operator))
    table = cases.table(ctx.pa, rows)
    handle = ctx.handle(query, table, parameters={"min_amount": int(value)})
    return _attempt(ctx, handle, schema=True)


def _ranges(columns: Any) -> list[list[int]]:
    return [
        [buffer.address, buffer.address + buffer.size]
        for column in columns
        for chunk in column.chunks
        for buffer in chunk.buffers()
        if buffer is not None and buffer.size
    ]


def c09(ctx: Context, sub: str) -> dict:
    pa = ctx.pa
    memory = bytearray((7).to_bytes(8, "little") * 4)
    ids = pa.Array.from_buffers(pa.int64(), 4, [None, pa.py_buffer(memory)])
    table = cases.table(pa, ((0, 5, "a", True, 1.0),) * 4, id=ids)
    table = table.append_column("extra", pa.array([1, 2, 3, 4])).slice(1, 2)
    handle = ctx.handle(
        ctx.query("P0", cases.q_body(">=")), table, parameters={"min_amount": 1}
    )
    owned = handle._owner._capture
    facts = {
        "capture_names": owned.column_names,
        "capture_rows": owned.num_rows,
        "c0_data_size": owned.column(0).chunks[0].buffers()[1].size,
        "ranges": {"capture": _ranges(owned.columns), "caller": _ranges(table.columns)},
    }
    memory[8:16] = (9).to_bytes(8, "little")
    facts["caller_ids_after"] = table.column(0).to_pylist()
    facts.update(_attempt(ctx, handle, schema=True))
    return facts


def _k(connection: Any) -> list[Any]:
    return [[list(row) for row in connection.sql(q).fetchall()] for q in cases.K_SQL]


def c10(ctx: Context, sub: str) -> dict:
    query, t5 = ctx.query("P0", cases.P_BODY), cases.table(ctx.pa, cases.T5)
    if sub == "i":
        seen: dict[str, Any] = {}

        def prelock(connection: Any) -> None:
            rows = connection.sql(cases.E_SQL).fetchall()
            seen.update(E=[row[0] for row in rows], prelock=_k(connection))

        def register(connection: Any) -> None:
            rows = connection.sql(cases.SETTINGS_SQL).fetchall()
            seen.update(settings=[list(row) for row in rows], register=_k(connection))

        with _Recorder(ctx.route) as recorder:
            recorder.hooks.update(
                prelock=prelock,
                register=register,
                unregister=lambda connection: seen.update(unregister=_k(connection)),
            )
            facts = _attempt(ctx, ctx.handle(query, t5), schema=True)
        points = ("prelock", "register", "unregister")
        facts.update(
            calls=recorder.calls,
            hook_errors=recorder.errors,
            E=seen.get("E"),
            settings=seen.get("settings"),
            K={point: seen[point] for point in points if point in seen},
            K_sizes={
                point: [len(rows) for rows in seen[point]]
                for point in points
                if point in seen
            },
        )
        return facts
    # A table the route must not read, in the calling frame and its globals.
    pietto_frame_table = cases.table(ctx.pa, cases.T5)
    globals()["pietto_frame_table"] = pietto_frame_table
    try:
        with _Recorder(ctx.route) as recorder:
            handle = ctx.handle(query, t5)
            handle._owner._sql = cases.FRAME_SQL
            facts = _attempt(ctx, handle)
    finally:
        globals().pop("pietto_frame_table", None)
    facts["calls"] = recorder.calls
    return facts


class _Breaking:
    """J7: close() closes the real connection, then raises."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def close(self) -> None:
        self._connection.close()
        raise RuntimeError("close")


def c11(ctx: Context, sub: str) -> dict:
    x, route = ctx.execution, ctx.route
    query, t5 = ctx.query("P0", cases.P_BODY), cases.table(ctx.pa, cases.T5)
    if sub == "L1":
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            handle.close()
        return {"raised": None, "O": _outcome(handle), "calls": recorder.calls}
    if sub == "L2":
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            with handle:
                pass
            again = _refusal(handle.__enter__)
        return {
            "raised": None,
            "O": _outcome(handle),
            "calls": recorder.calls,
            "second_enter": again,
        }
    if sub == "L3":
        mine = LookupError("the consumer's own error")
        raised: Any = None
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            try:
                with handle as result:
                    next(iter(result))
                    raise mine
            except LookupError as error:
                raised = {"class": type(error).__name__, "same": error is mine}
            except BaseException as error:
                raised = _raised(error)
        primary = handle.outcome.primary
        return {
            "raised": raised,
            "O": _outcome(handle),
            "primary": None if primary is None else [primary.code, primary.phase],
            "calls": recorder.calls,
        }
    if sub == "L4":
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            handle.cancel()
            facts = _attempt(ctx, handle)
        facts["calls"] = recorder.calls
        return facts
    if sub == "L5":
        threads = _Threads()
        with _Recorder(route) as recorder, _patched(route, threading=threads):
            handle = ctx.handle(query, t5)
            running, tripped, _first = _slow(recorder, handle)
            canceller = threading.Thread(
                target=lambda: running.wait(60) and handle.cancel()
            )
            canceller.start()
            facts = _attempt(ctx, handle)
            canceller.join(60)
        owner = handle._owner
        resends = [
            thread for target, thread in threads.created if target == owner._resend
        ]
        for thread in resends:
            thread.join(cases.WATCHDOG_SECONDS)
        facts.update(
            calls=recorder.calls,
            hook_errors=recorder.errors,
            resend_threads=len(resends),
            resend_alive=any(thread.is_alive() for thread in resends),
            tripped=tripped.is_set(),
        )
        return facts
    if sub == "L6":
        importlib.import_module("duckdb")
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5, limits=x.ExecutionLimits(seconds=0.5))
            _running, tripped, first = _slow(recorder, handle)
            owner = handle._owner
            entered = time.monotonic()
            facts = _attempt(ctx, handle)
        timer = owner._timer
        interval = None if timer is None else timer.interval
        if timer is not None:
            timer.join(cases.WATCHDOG_SECONDS)
        facts.update(
            calls=recorder.calls,
            hook_errors=recorder.errors,
            elapsed=facts["raised_at"] - entered if "raised_at" in facts else None,
            timer_interval=interval,
            timer_alive=None if timer is None else timer.is_alive(),
            tripped=tripped.is_set(),
            setup=first[0] - owner._started
            if first and owner._started is not None
            else None,
            duckdb_preloaded=True,
        )
        return facts
    if sub == "L7":
        offset = [0.0]
        clock = SimpleNamespace(monotonic=lambda: time.monotonic() + offset[0])
        with _Recorder(route) as recorder, _patched(route, time=clock):
            recorder.hooks["statement"] = lambda connection: offset.__setitem__(
                0, offset[0] + 3600.0
            )
            facts = _attempt(ctx, ctx.handle(query, t5))
        facts.update(
            calls=recorder.calls, hook_errors=recorder.errors, offset=offset[0]
        )
        return facts
    if sub == "L8":
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            owner, check, trigger = handle._owner, handle._owner._checkpoint, []

            def late() -> Any:
                if owner._ended.is_set() and not trigger:
                    trigger.append([owner._running, owner._ended.is_set()])
                    handle.cancel()
                return check()

            owner._checkpoint = late
            facts = _attempt(ctx, handle)
        facts.update(calls=recorder.calls, trigger=trigger[0] if trigger else None)
        return facts
    if sub in ("L9a", "L9b", "L9c"):
        patch = {
            "L9a": {
                "SETTINGS": (*route.SETTINGS, ("pietto_no_such_setting", "1", "1"))
            },
            "L9b": {"READ_BACK": (*route.READ_BACK, ("threads", "2"))},
            "L9c": {},
        }[sub]
        with _Recorder(route) as recorder, _patched(route, **patch):
            recorder.register_raises = sub == "L9c"
            handle = ctx.handle(query, t5)
            handle._owner._sql = cases.NEVER_SQL
            facts = _attempt(ctx, handle)
        facts["calls"] = recorder.calls
        return facts
    if sub == "L10":
        raised = None
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            try:
                with handle as result:
                    handle._owner._connection = _Breaking(handle._owner._connection)
                    for _batch in result:
                        pass
            except x.AttemptFailed as error:
                raised = _raised(error)
        return {
            "raised": raised,
            "O": _outcome(handle),
            "cleanup_failures": [
                [f.code, f.phase, f.cause] for f in handle.outcome.cleanup_failures
            ],
            "calls": recorder.calls,
        }
    if sub in ("L11a", "L11b"):
        with _Recorder(route) as recorder:
            handle = ctx.handle(query, t5)
            handle._owner._sql = (
                cases.OVERFLOW_SQL if sub == "L11a" else cases.RELABEL_SQL
            )
            facts = _attempt(ctx, handle)
        facts["calls"] = recorder.calls
        return facts
    with _Recorder(route) as recorder:
        facts = _attempt(
            ctx, ctx.handle(query, t5, limits=x.ExecutionLimits(max_rows=4))
        )
    facts["calls"] = recorder.calls
    return facts


def c13(ctx: Context, sub: str) -> dict:
    table = cases.table(ctx.pa, cases.T5 * 2)
    return _attempt(ctx, ctx.handle(ctx.query("P0", cases.P_BODY), table), schema=True)


def c14(ctx: Context, sub: str) -> dict:
    pa = ctx.pa
    arguments: dict[str, Any] = {}
    if sub == "c":
        whole = cases.table(pa, cases.TN * 500)
        table = pa.concat_tables(
            [whole.slice(0, 2000), whole.slice(2000, 2000), whole.slice(4000)]
        )
    else:
        table = cases.table(pa, cases.TN)
    if sub == "b":
        query = ctx.query("P0", cases.q_body("!=", ("id", "note")))
        arguments["parameters"] = {"min_amount": 1}
    else:
        query = ctx.query("P0", cases.P_BODY)
    with _Recorder(ctx.route) as recorder:
        handle = ctx.handle(query, table, **arguments)
        capture = [
            cases.encode(value)
            for value in handle._owner._capture.column(2).to_pylist()
        ]
        facts = _attempt(ctx, handle, schema=True)
    facts.update(
        capture_c2=capture, calls=recorder.calls, chunks=table.column(0).num_chunks
    )
    return facts


def c15(ctx: Context, sub: str) -> dict:
    x = ctx.execution
    query = ctx.query("P0", cases.q_body(">="))
    if sub == "job_store":
        from pietto._project import project_job_store

        return {"routes": list(project_job_store.ROUTES)}
    if sub == "bundle":
        return {"raised": _refusal(lambda: x.export_bundle(query))}
    absent, sink = ctx.work / "absent", ctx.work / "sink"
    workspace = x.WorkspaceRef(str(absent), "ws-" + "0" * 32)
    common = {
        "route": "duckdb_arrow",
        "operation": x.new_operation(),
        "access": x.DuckDBArrowInput("orders", object()),
        "premise": None,
        "limits": x.ExecutionLimits(),
    }
    calls = {
        "save": lambda: x.save(workspace, query, **common),
        "save_recoverable": lambda: x.save_recoverable(
            workspace, query, source_requirements=(), **common
        ),
        "recover": lambda: x.recover(
            workspace,
            job="j",
            generation="g",
            checkpoint=None,
            query=query,
            source_requirements=(),
            expected_pin="0" * 64,
            accepted_producer="x",
            accepted_compatibility="x",
            purpose="p",
            seconds=1,
            **common,
        ),
        "relay_live": lambda: x.relay_live(
            workspace,
            query,
            sink_root=str(sink),
            expected_sink_identity="x",
            sink_namespace="x",
            sink_epoch=1,
            sink_retention="x",
            sink_budget_bytes=1,
            **common,
        ),
    }
    raised = _refusal(calls[sub])
    return {"raised": raised, "exists_after": [absent.exists(), sink.exists()]}


def c16(ctx: Context, sub: str) -> dict:
    query = ctx.query("P0", cases.P_BODY)
    with _Recorder(ctx.route) as recorder:
        first = ctx.handle(query, cases.table(ctx.pa, cases.T5))
        one = _attempt(ctx, first)
        again = _refusal(first.__enter__)
        second = ctx.handle(query, cases.table(ctx.pa, cases.T5))
        two = _attempt(ctx, second)
    return {
        "rows1": one["rows"],
        "rows2": two["rows"],
        "raised": [one["raised"], two["raised"]],
        "connects": [call for call in recorder.calls if call[0] == "connect"],
        "connections": len({id(connection) for connection in recorder.connections}),
        "attempts": len({first.outcome.attempt, second.outcome.attempt}),
        "second_enter": again,
        "calls": recorder.calls,
    }


CELLS = {
    "C01": c01,
    "C02a": c02a,
    "C02b": c02b,
    "C02c": c02c,
    "C03": c03,
    "C04": c04,
    "C05": c05,
    "C06": c06,
    "C07": c07,
    "C08": c08,
    "C09": c09,
    "C10": c10,
    "C11": c11,
    "C13": c13,
    "C14": c14,
    "C15": c15,
    "C16": c16,
}


def _facts(cell: Any, ctx: Context, sub: str) -> dict:
    """One sub-case's facts; an exception of the producer itself is a fact
    too, never retried (law 8)."""
    try:
        return cell(ctx, sub)
    except BaseException as error:
        return {"producer_error": [type(error).__name__, str(error)[-500:]]}


def _listing(dirs: dict[str, Path]) -> dict[str, list[str]]:
    return {
        name: sorted(str(path.relative_to(directory)) for path in directory.rglob("*"))
        for name, directory in dirs.items()
    }


def cell_main(args: argparse.Namespace) -> int:
    sys.path[:0] = json.loads(args.path)
    ctx = Context(args)
    out = Path(args.out)
    subs = json.loads(args.subs)
    if args.cell != "C12":
        for sub in subs:
            _emit(out, args.unit, args.cell, sub, _facts(CELLS[args.cell], ctx, sub))
        return 0
    dirs = {name: Path(path) for name, path in json.loads(args.dirs).items()}
    before = _listing(dirs)
    for sub in subs:
        if sub != "ns":
            cell, inner = sub.split("/", 1)
            _emit(out, args.unit, "C12", sub, _facts(CELLS[cell], ctx, inner))
    try:
        link = subprocess.run(
            ["ip", "-o", "link"], capture_output=True, text=True, timeout=30
        )
        ip_link: Any = [link.returncode, link.stdout]
    except (OSError, subprocess.TimeoutExpired) as error:
        ip_link = repr(error)
    facts = {
        "interfaces": [name for _index, name in socket.if_nameindex()],
        "netns": [os.readlink("/proc/self/ns/net"), args.host_netns],
        "before": before,
        "after": _listing(dirs),
        "ip_link": ip_link,
    }
    _emit(out, args.unit, "C12", "ns", facts)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("unit", "identity", "cell"))
    parser.add_argument("--unit", required=True, choices=cases.UNITS)
    for name in ("run", "lane", "tree", "site", "wheel", "erratum", "evidence"):
        parser.add_argument(f"--{name}")
    for name in ("cell", "subs", "path", "argv1", "out", "host-netns", "dirs"):
        parser.add_argument(f"--{name}")
    args = parser.parse_args(argv)
    command = {"unit": unit_main, "identity": identity_main, "cell": cell_main}
    return command[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
