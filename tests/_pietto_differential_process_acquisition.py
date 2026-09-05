"""Parent-side process-cell acquisition for the historical differential families.

Every logical differential request keeps its exact environment cell, its own
probe ``observation`` invocation, and its own exact bytes. This module only
decides which requests may share one child interpreter, and coordinates that
acquisition across serial and xdist execution inside one pytest run.

Grouping is acquisition topology, never semantic identity. There is no
persistent cache: the store lives under the current pytest run's temporary root
and is never reused by another run.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import site
import subprocess
import sys
import time
from typing import cast

import _pietto_differential_probe_batch as batch

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
BATCH_CHILD = TESTS_ROOT / "_pietto_differential_probe_batch.py"
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))
FAMILY_ORDER = ("phase58", "phase59", "phase60", "phase61", "phase62", "phase63")
MODES = ("checkout", "relocated", "installed")
# Every file a relocated or installed batch cell may import outside the
# checkout. This manifest is frozen; nothing else is copied.
RELOCATION_SUPPORT_MANIFEST = (
    "_pietto_differential_probe_batch.py",
    "_pietto_project_explain_scenarios.py",
    "_pietto_project_explain_differential_probe.py",
    "_pietto_phase59_graph_differential_probe.py",
    "_pietto_phase60_window_differential_probe.py",
    "_pietto_phase61_project_ir_differential_probe.py",
    "_pietto_phase62_join_differential_probe.py",
    "_pietto_phase63_query_block_ir_differential_probe.py",
)
COMBINED_RELOCATED_CELLS = (((3, 12), "1"), ((3, 13), "4294967295"))
ACQUISITION_TIMEOUT_SECONDS = 900.0
POLL_SECONDS = 0.05


class AcquisitionFailure(RuntimeError):
    """One exact process cell could not be acquired."""


@dataclass(frozen=True, slots=True, order=True)
class Cell:
    """One exact process-compatible environment cell."""

    version: tuple[int, int]
    seed: str
    mode: str

    def __post_init__(self) -> None:
        assert self.seed in SEEDS
        assert self.mode in MODES

    @property
    def name(self) -> str:
        return f"python{self.version[0]}.{self.version[1]}-seed{self.seed}-{self.mode}"


@dataclass(frozen=True, slots=True, order=True)
class Request:
    """One logical differential request inside exactly one cell."""

    family: str
    key: str
    cell: Cell
    ambient: str

    @property
    def request_id(self) -> str:
        """Identify this request uniquely inside its shared process cell."""

        return f"{self.family}/{self.key}"


def _site_packages() -> str:
    candidates = tuple(site.getsitepackages())
    assert candidates
    return str(candidates[0])


def _interpreter_version(executable: str) -> tuple[int, int] | None:
    try:
        completed = subprocess.run(
            (executable, "-c", "import sys; print(*sys.version_info[:2])"),
            check=True,
            text=True,
            capture_output=True,
        )
        return cast(tuple[int, int], tuple(map(int, completed.stdout.split())))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


_INTERPRETERS: dict[tuple[int, int], str] | None = None


def available_supported_interpreters() -> dict[tuple[int, int], str]:
    """Discover the supported interpreters once per worker process."""

    global _INTERPRETERS
    if _INTERPRETERS is None:
        current = sys.version_info[:2]
        assert current in SUPPORTED_INTERPRETERS
        available = {current: sys.executable}
        for version in SUPPORTED_INTERPRETERS:
            if version == current:
                continue
            executable = shutil.which(f"python{version[0]}.{version[1]}")
            if executable is not None and _interpreter_version(executable) == version:
                available[version] = executable
        _INTERPRETERS = available
    return dict(_INTERPRETERS)


def _current() -> tuple[int, int]:
    return cast(tuple[int, int], sys.version_info[:2])


def _explain_family_requests(
    family: str,
    interpreters: dict[tuple[int, int], str],
    *,
    combined: bool,
) -> tuple[Request, ...]:
    current = _current()
    requests = [
        Request(family, f"seed:{seed}", Cell(current, seed, "checkout"), f"seed-{seed}")
        for seed in SEEDS
    ]
    for version in interpreters:
        if version == current:
            continue
        key = f"python{version[0]}.{version[1]}"
        requests.append(Request(family, key, Cell(version, "0", "checkout"), key))
    requests.append(
        Request(
            family,
            "project-relocated",
            Cell(current, "0", "checkout"),
            "project-relocated",
        )
    )
    requests.append(
        Request(
            family,
            "source-relocated",
            Cell(current, "0", "relocated"),
            "source-relocated",
        )
    )
    if combined:
        for version, seed in COMBINED_RELOCATED_CELLS:
            if version not in interpreters:
                continue
            key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"
            requests.append(Request(family, key, Cell(version, seed, "relocated"), key))
    requests.append(
        Request(
            family,
            "installed-wheel",
            Cell(current, "0", "installed"),
            "installed-wheel",
        )
    )
    return tuple(requests)


def _matrix_family_requests(
    family: str,
    interpreters: dict[tuple[int, int], str],
) -> tuple[Request, ...]:
    requests: list[Request] = []
    for version in interpreters:
        label = f"python{version[0]}.{version[1]}"
        for seed in SEEDS:
            key = f"source:{label}:seed:{seed}"
            requests.append(Request(family, key, Cell(version, seed, "checkout"), key))
    for version in interpreters:
        label = f"python{version[0]}.{version[1]}"
        key = f"relocated:{label}:seed:7"
        requests.append(Request(family, key, Cell(version, "7", "relocated"), key))
    for version in interpreters:
        label = f"python{version[0]}.{version[1]}"
        key = f"installed:{label}:seed:7"
        requests.append(Request(family, key, Cell(version, "7", "installed"), key))
    return tuple(requests)


def family_requests(
    family: str,
    interpreters: dict[tuple[int, int], str],
) -> tuple[Request, ...]:
    """Return the exact logical request manifest for one family."""

    if family == "phase58":
        return _explain_family_requests(family, interpreters, combined=False)
    if family in {"phase59", "phase60", "phase61"}:
        return _explain_family_requests(family, interpreters, combined=True)
    if family in {"phase62", "phase63"}:
        return _matrix_family_requests(family, interpreters)
    raise KeyError(f"Unknown differential family: {family!r}")


def all_requests(
    interpreters: dict[tuple[int, int], str],
) -> tuple[Request, ...]:
    return tuple(
        request
        for family in FAMILY_ORDER
        for request in family_requests(family, interpreters)
    )


def cell_plan(
    interpreters: dict[tuple[int, int], str],
) -> dict[Cell, tuple[Request, ...]]:
    """Group every logical request into exact process-compatible cells."""

    plan: dict[Cell, list[Request]] = {}
    for request in all_requests(interpreters):
        plan.setdefault(request.cell, []).append(request)
    return {
        cell: tuple(
            sorted(
                requests,
                key=lambda item: (FAMILY_ORDER.index(item.family), item.key),
            )
        )
        for cell, requests in sorted(plan.items())
    }


def _atomic_write(path: Path, text: str) -> None:
    pending = path.with_name(f"{path.name}.pending")
    pending.write_text(text, encoding="utf-8")
    os.replace(pending, path)


def _owner_alive(lock: Path) -> bool:
    try:
        pid = int(lock.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class DifferentialAcquisition:
    """One ephemeral per-pytest-run acquisition store shared by every worker."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.interpreters = available_supported_interpreters()
        self.plan = cell_plan(self.interpreters)
        self._memo: dict[Cell, dict[str, object]] = {}

    # -- shared resources -------------------------------------------------

    def _guarded(self, name: str, produce) -> Path:
        target = self.root / name
        marker = self.root / f"{name}.done"
        failure = self.root / f"{name}.failed"
        lock = self.root / f"{name}.lock"
        deadline = time.monotonic() + ACQUISITION_TIMEOUT_SECONDS
        while True:
            if marker.exists():
                return target
            if failure.exists():
                raise AcquisitionFailure(failure.read_text(encoding="utf-8"))
            try:
                handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not _owner_alive(lock) and not marker.exists():
                    lock.unlink(missing_ok=True)
                    continue
                if time.monotonic() > deadline:
                    raise AcquisitionFailure(f"Timed out waiting for {name}.")
                time.sleep(POLL_SECONDS)
                continue
            try:
                os.write(handle, str(os.getpid()).encode("ascii"))
            finally:
                os.close(handle)
            try:
                if target.exists():
                    shutil.rmtree(target)
                produce(target)
            except BaseException as error:
                _atomic_write(failure, f"{type(error).__name__}: {error}")
                raise
            finally:
                lock.unlink(missing_ok=True)
            _atomic_write(marker, "ok")
            return target

    def _produce_relocated(self, target: Path) -> None:
        shutil.copytree(
            REPO_ROOT / "src",
            target / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        tests = target / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        for name in RELOCATION_SUPPORT_MANIFEST:
            shutil.copyfile(TESTS_ROOT / name, tests / name)

    def relocated_root(self) -> Path:
        return self._guarded("source-relocated", self._produce_relocated)

    def _produce_installed(self, target: Path) -> None:
        dist = target / "dist"
        wheel_source_root = target / "wheel-source"
        empty_cache = target / "empty-uv-cache"
        probes = target / "probes"
        for directory in (dist, wheel_source_root, empty_cache, probes):
            directory.mkdir(parents=True, exist_ok=True)
        assert not tuple(empty_cache.iterdir())
        subprocess.run(
            ("uv", "build", "--offline", "--wheel", "--out-dir", str(dist)),
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            env=self.environment(None, "0", "wheel-build"),
        )
        wheels = tuple(dist.glob("pietto-0.1.0-*.whl"))
        assert len(wheels) == 1
        install_environment = self.environment(None, "0", "wheel-install")
        install_environment["UV_CACHE_DIR"] = str(empty_cache)
        subprocess.run(
            (
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--target",
                str(wheel_source_root / "src"),
                str(wheels[0]),
            ),
            check=True,
            capture_output=True,
            cwd=target,
            env=install_environment,
        )
        for name in RELOCATION_SUPPORT_MANIFEST:
            shutil.copyfile(TESTS_ROOT / name, probes / name)

    def installed_root(self) -> Path:
        return self._guarded("installed-wheel", self._produce_installed)

    def installed_source_root(self) -> Path:
        return self.installed_root() / "wheel-source"

    def empty_install_cache(self) -> Path:
        return self.installed_root() / "empty-uv-cache"

    # -- cell acquisition -------------------------------------------------

    def environment(
        self,
        source_root: Path | None,
        seed: str,
        ambient: str,
    ) -> dict[str, str]:
        environment = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
            environment.pop(name, None)
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONNOUSERSITE"] = "1"
        for marker in sorted(set(batch.FAMILY_AMBIENT.values())):
            environment[marker] = ambient
        if source_root is not None:
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(source_root / "src"), _site_packages())
            )
        return environment

    def _cell_child(self, cell: Cell) -> tuple[Path, Path]:
        if cell.mode == "checkout":
            return BATCH_CHILD, REPO_ROOT
        if cell.mode == "relocated":
            relocated = self.relocated_root()
            return relocated / "tests" / BATCH_CHILD.name, relocated
        installed = self.installed_root()
        return installed / "probes" / BATCH_CHILD.name, self.installed_source_root()

    def _run_cell(self, cell: Cell, cell_root: Path) -> dict[str, object]:
        requests = self.plan[cell]
        child, source_root = self._cell_child(cell)
        work = cell_root / "work"
        work.mkdir(parents=True, exist_ok=True)
        manifest_requests = []
        for request in requests:
            slug = f"{request.family}-{request.key.replace(':', '-')}"
            manifest_requests.append(
                {
                    "family": request.family,
                    "key": request.request_id,
                    "ambient": request.ambient,
                    "workspace": str(work / slug / "workspace"),
                    "cwd": str(work / slug / "run"),
                }
            )
        manifest = cell_root / "manifest.json"
        output = cell_root / "cell.json"
        manifest.write_text(
            json.dumps({"requests": manifest_requests}, separators=(",", ":")),
            encoding="utf-8",
        )
        completed = subprocess.run(
            (
                self.interpreters[cell.version],
                str(child),
                "--manifest",
                str(manifest),
                "--output",
                str(output),
            ),
            capture_output=True,
            cwd=work,
            env=self.environment(source_root, cell.seed, f"cell:{cell.name}"),
        )
        if completed.returncode != 0 or not output.exists():
            raise AcquisitionFailure(
                f"Batch cell {cell.name} failed with exit {completed.returncode}:\n"
                f"{completed.stderr.decode('utf-8', 'replace')}"
            )
        assert completed.stdout == b""
        payload = cast(
            dict[str, object], json.loads(output.read_text(encoding="utf-8"))
        )
        assert payload["python_version"] == list(cell.version)
        assert payload["hash_seed"] == cell.seed
        results = cast(dict[str, str], payload["results"])
        assert set(results) == {request.request_id for request in requests}
        return payload

    def _cell_payload(self, cell: Cell) -> dict[str, object]:
        memo = self._memo.get(cell)
        if memo is not None:
            return memo
        cell_root = self.root / f"cell-{cell.name}"
        cell_root.mkdir(parents=True, exist_ok=True)
        output = cell_root / "cell.json"
        failure = cell_root / "cell.failed"
        lock = cell_root / "cell.lock"
        deadline = time.monotonic() + ACQUISITION_TIMEOUT_SECONDS
        while True:
            if output.exists():
                break
            if failure.exists():
                raise AcquisitionFailure(failure.read_text(encoding="utf-8"))
            try:
                handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not _owner_alive(lock) and not output.exists():
                    lock.unlink(missing_ok=True)
                    continue
                if time.monotonic() > deadline:
                    raise AcquisitionFailure(f"Timed out waiting for cell {cell.name}.")
                time.sleep(POLL_SECONDS)
                continue
            try:
                os.write(handle, str(os.getpid()).encode("ascii"))
            finally:
                os.close(handle)
            try:
                self._run_cell(cell, cell_root)
            except BaseException as error:
                _atomic_write(failure, f"{type(error).__name__}: {error}")
                raise
            finally:
                lock.unlink(missing_ok=True)
            break
        payload = cast(
            dict[str, object], json.loads(output.read_text(encoding="utf-8"))
        )
        self._memo[cell] = payload
        return payload

    # -- family views ------------------------------------------------------

    def documents(self, family: str) -> dict[str, bytes]:
        """Return every exact family observation document by historical key."""

        documents: dict[str, bytes] = {}
        for request in family_requests(family, self.interpreters):
            payload = self._cell_payload(request.cell)
            results = cast(dict[str, str], payload["results"])
            document = base64.b64decode(results[request.request_id])
            assert document.endswith(b"\n") and not document.endswith(b"\n\n")
            documents[request.key] = document
        return documents

    def import_origin(self, cell: Cell) -> Path:
        """Report `pietto.__file__` from the child that produced the cell."""

        payload = self._cell_payload(cell)
        return Path(str(payload["import_origin"]))

    def installed_origins(self) -> dict[tuple[int, int], Path]:
        origins: dict[tuple[int, int], Path] = {}
        for cell in self.plan:
            if cell.mode == "installed":
                origins[cell.version] = self.import_origin(cell)
        return origins


_SESSION: DifferentialAcquisition | None = None


def acquisition(tmp_path_factory) -> DifferentialAcquisition:
    """Return this pytest run's shared ephemeral acquisition store."""

    global _SESSION
    if _SESSION is None:
        base = tmp_path_factory.getbasetemp()
        run_root = base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base
        _SESSION = DifferentialAcquisition(run_root / "pietto-differential-acquisition")
    return _SESSION
