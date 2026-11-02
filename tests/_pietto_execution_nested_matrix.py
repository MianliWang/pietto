"""Public-entry matrix of collection-carrying queries; importing acquires nothing.

- The closed classes of the ``pietto.execution`` entries by the shape they carry.
- The hand-written expected cell of each (dialect, entry, route, origin): an
  admission (A), a permanent refusal (P) or a transitional refusal (T) that
  either keeps its word or, once admitted, stops where its flat control stops.
- ``Witness``: one test function's loopback listener that every access points
  at, and counting observers of the workspace opener and the sink resolver
  that forward to the originals. ``drive`` calls one public entry twice;
  ``settle`` waits one bounded window for any connection the cells made.
- ``seam``: the one replaced name, the collection predicate of every gate.
- ``laws``: the matrix laws L1-L8 over driven facts.
- ``operations``: the collection operations of a compiled query's own records.

No driver, pyarrow or database is loaded or reached.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
import inspect
from pathlib import Path
import re
import select
import socket
import sys
import threading
import time
from typing import Any

import pietto.execution as execution
from pietto._project import project_execution_nested as nested
from pietto._project import project_job_workspace as private_workspace
from pietto.execution import _relay as relay

ENTRIES = ("execute", "save", "save_recoverable", "recover", "relay_live")
ROUTES = ("postgres_rows", "postgres_adbc", "mysql_rows")
FLAT: frozenset[str] = frozenset()
CLOSURES = (
    frozenset({"collect"}),
    frozenset({"unnest"}),
    frozenset({"collect", "unnest"}),
)

# Every public entry carries a query, a saved job, produces a query or carries
# no shape; types are values, not entries.
QUERY = frozenset(
    {"execute", "export_bundle", "save", "save_recoverable", "recover", "relay_live"}
)
SAVED = frozenset(
    {
        "open_saved_read",
        "release_saved_read",
        "verified_export",
        "publish_saved_generation",
        "retire_generation",
        "inspect_job",
    }
)
PRODUCER = frozenset({"compile_query", "load_bundle"})
NO_SHAPE = frozenset(
    {
        "create_reference_sink",
        "create_workspace",
        "open_workspace",
        "new_operation",
        "new_consumer_identity",
        "operation_result",
    }
)

SENTINEL = "MATRIXSENTINELPW"
WINDOW = 0.25
DRIVERS = ("adbc_driver", "psycopg", "pyarrow", "mysql")
COLLECTION_WORDS = frozenset(
    {
        "COLLECTION_ROUTE",
        "COLLECTION_LEAF",
        "COLLECTION_ENTRY",
        "COLLECTION_RESOURCE_LIMIT",
        "PUBLIC_R2_COLLECTION",
        "SAVED_READ_COLLECTION",
    }
)

ADMIT = ("A", "ADMIT", "ResultHandle")
ROUTE = ("P", "PIE-R1003", "COLLECTION_ROUTE")
UNAVAILABLE = ("P", "PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")
T_FOLLOWS = ("T", "PIE-R1009", "WORKSPACE_OBJECT")
P_ENTRY = ("P", "PIE-R1004", "COLLECTION_ENTRY")


def _expected() -> dict[tuple[str, str, str, str], tuple[str, str, str]]:
    """Each (dialect, entry, route, origin) cell of a collection-carrying query."""
    cells = {}
    for origin in ("live", "bundle"):
        r2 = "PUBLIC_R2_COLLECTION" if origin == "live" else "PUBLIC_R2_LIVE_QUERY"
        for entry in ENTRIES:
            cells["postgres", entry, "postgres_adbc", origin] = ROUTE
            cells["postgres", entry, "mysql_rows", origin] = UNAVAILABLE
            cells["mysql", entry, "mysql_rows", origin] = ROUTE
            cells["mysql", entry, "postgres_rows", origin] = UNAVAILABLE
            cells["mysql", entry, "postgres_adbc", origin] = UNAVAILABLE
        cells["postgres", "execute", "postgres_rows", origin] = ADMIT
        cells["postgres", "save", "postgres_rows", origin] = T_FOLLOWS
        cells["postgres", "relay_live", "postgres_rows", origin] = P_ENTRY
        for entry in ("save_recoverable", "recover"):
            cells["postgres", entry, "postgres_rows", origin] = ("P", "PIE-R1004", r2)
    return cells


EXPECTED = _expected()


@dataclass(frozen=True)
class Fact:
    """One driven cell: its word, its second run and its effects; a flag is
    set when either run set it."""

    subject: str
    dialect: str
    origin: str
    entry: str
    route: str
    closure: frozenset[str]
    code: str
    detail: str | None
    again: tuple[Any, ...]
    chained: bool = False
    leaked: bool = False
    connects: int = 0
    workspaces: int = 0
    sinks: int = 0
    files: bool = False
    threads: bool = False
    shared_connects: int = 0
    drivers: tuple[str, ...] = ()  # informative: a worker may hold them already
    leaf: str | None = None

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        return (self.subject, self.dialect, self.origin, self.entry, self.route)

    @property
    def word(self) -> tuple[str, str | None]:
        return (self.code, self.detail)

    @property
    def refused(self) -> bool:
        return self.code != "ADMIT"

    @property
    def effects(self) -> tuple[Any, ...]:
        return (self.connects, self.workspaces, self.sinks, self.files, self.threads)


def operations(query: Any) -> frozenset[str]:
    """The collection operations of the query's own compiled records."""
    root = query._template.artifact.request.verification.completed.root
    return nested.collection_operations(root.records)


@contextmanager
def seam(closure: frozenset[str] | None) -> Iterator[None]:
    """Every gate's collection predicate reports `closure`; None keeps the
    real predicate."""
    real = nested.collection_operations
    if closure is not None:
        nested.collection_operations = lambda records: closure
    try:
        yield
    finally:
        nested.collection_operations = real


def unclassified(module: Any) -> tuple[str, ...]:
    """Entries of ``module.__all__`` outside exactly one class or in a class
    their parameters contradict, and class names the module lacks."""
    classes = (QUERY, SAVED, PRODUCER, NO_SHAPE)
    wrong = set(frozenset().union(*classes) - set(module.__all__))
    for name in module.__all__:
        value = getattr(module, name)
        if isinstance(value, type):
            continue
        parameters = inspect.signature(value).parameters
        homes = [c for c in classes if name in c]
        if (
            len(homes) != 1
            or (name in QUERY) != ("query" in parameters)
            or (name in SAVED) != ("job" in parameters and "query" not in parameters)
        ):
            wrong.add(name)
    return tuple(sorted(wrong))


def public_call(
    query: Any, entry: str, route: str, *, root: Path, port: int, premise=True
) -> Callable[[], Any]:
    """A zero-argument call of one public query entry on `route`; the access
    points at `port` with the sentinel password, the workspace is never opened."""
    sources = query._template.artifact.request.sources
    schemas = tuple(dict.fromkeys(source.namespace for source in sources))
    if route == "mysql_rows":
        access: Any = execution.MySQLAccess(
            "127.0.0.1", port, "matrix", "u", SENTINEL, "/dev/null", "u@%"
        )
        deployment: Any = execution.MySQLDeploymentPremise(schemas)
    else:
        access = execution.PostgresAccess("127.0.0.1", port, "matrix", "u", SENTINEL)
        deployment = execution.PostgresDeploymentPremise(schemas + ("pg_catalog",))
    arguments: dict[str, Any] = dict(
        route=route, access=access, premise=deployment if premise else None
    )
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", str(root))
    object.__setattr__(workspace, "identity", "ws-" + "4" * 32)
    if entry == "execute":
        return lambda: execution.execute(query, **arguments)
    if entry == "save":
        return lambda: execution.save(
            workspace, query, operation=execution.new_operation(), **arguments
        )
    if entry == "relay_live":
        return lambda: execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            **arguments,
            sink_root=None,
            expected_sink_identity="snk-" + "0" * 32,
            sink_namespace="relay",
            sink_epoch=1,
            sink_retention="retention",
            sink_budget_bytes=private_workspace.DEFAULT_BUDGET,
        )
    inputs = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in sources
    )

    def r2() -> dict[str, Any]:
        return dict(
            query=query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            limits=execution.ExecutionLimits(),
            **arguments,
        )

    if entry == "save_recoverable":
        return lambda: execution.save_recoverable(workspace, **r2())
    bundle = execution.export_bundle(query)
    return lambda: execution.recover(
        workspace,
        job="job-" + "5" * 32,
        generation="gen-" + "6" * 32,
        checkpoint=None,
        expected_pin=bundle.pin,
        accepted_producer=bundle.producer,
        accepted_compatibility=bundle.compatibility,
        purpose="matrix recovery",
        seconds=1,
        **r2(),
    )


def _tree(base: Path) -> list[str]:
    return sorted(str(path.relative_to(base)) for path in base.rglob("*"))


class Witness:
    """One test function's effect witnesses over the cells it drives."""

    def __init__(self, base: Path) -> None:
        self.base = Path(base)
        self.workspaces = 0
        self.sinks = 0
        self._pending: list[Fact] = []

    def __enter__(self) -> Witness:
        self._listener = socket.create_server(("127.0.0.1", 0))
        self._listener.setblocking(False)
        self.port = self._listener.getsockname()[1]
        self._real = opener, resolver = (
            private_workspace.open_workspace,
            relay._sink_target,
        )

        def open_workspace(*arguments: Any, **keywords: Any) -> Any:
            self.workspaces += 1
            return opener(*arguments, **keywords)

        def sink_target(*arguments: Any) -> Any:
            self.sinks += 1
            return resolver(*arguments)

        private_workspace.open_workspace = open_workspace
        relay._sink_target = sink_target
        return self

    def __exit__(self, *exc: object) -> None:
        private_workspace.open_workspace, relay._sink_target = self._real
        self._listener.close()

    def accepted(self, window: float = WINDOW) -> int:
        """Connections the listener receives within the whole `window`, so a
        handshake the kernel completes late still counts here."""
        deadline = time.monotonic() + window
        count = 0
        while select.select(
            [self._listener], [], [], max(0.0, deadline - time.monotonic())
        )[0]:
            try:
                connection, _ = self._listener.accept()
            except BlockingIOError:
                continue
            connection.close()
            count += 1
        return count

    def observe(self, call: Callable[[], Any]) -> dict[str, Any]:
        """The word and the in-process effects of one call."""
        files, threads = _tree(self.base), set(threading.enumerate())
        modules, workspaces, sinks = set(sys.modules), self.workspaces, self.sinks
        chained = leaked = False
        try:
            value = call()
        except execution.RequestRejected as error:
            code, detail = error.code, error.detail
            chained = error.__cause__ is not None or error.__context__ is not None
            leaked = SENTINEL in f"{error}{error!r}{code}{detail}"
        except Exception as error:  # recorded: no public entry may raise it
            code, detail = "RAISED:" + type(error).__name__, None
            leaked = SENTINEL in f"{error}{error!r}"
        else:
            code, detail = "ADMIT", type(value).__name__
            if hasattr(value, "close"):
                value.close()
        return dict(
            code=code,
            detail=detail,
            chained=chained,
            leaked=leaked,
            workspaces=self.workspaces - workspaces,
            sinks=self.sinks - sinks,
            files=_tree(self.base) != files,
            threads=bool(set(threading.enumerate()) - threads),
            drivers=tuple(
                sorted(n for n in set(sys.modules) - modules if n.startswith(DRIVERS))
            ),
        )

    def drive(
        self,
        query: Any,
        entry: str,
        route: str,
        *,
        subject: str = "",
        closure: frozenset[str] | None = None,
        premise: bool = True,
    ) -> None:
        """Call one public entry twice under `seam(closure)`; its fact is
        returned by the next ``settle``."""
        call = public_call(
            query,
            entry,
            route,
            root=self.base / "never-opened",
            port=self.port,
            premise=premise,
        )
        operated = operations(query) if closure is None else closure
        with seam(closure):
            first = self.observe(call)
            second = self.observe(call)
        for flag in ("chained", "leaked", "files", "threads"):
            first[flag] = first[flag] or second[flag]
        again = (
            second["code"],
            second["detail"],
            second["workspaces"],
            second["sinks"],
        )
        fact = Fact(
            subject,
            query.dialect,
            query.origin,
            entry,
            route,
            operated,
            again=again,
            connects=-1,
            **first,
        )
        self._pending.append(fact)

    def settle(self) -> list[Fact]:
        """Keep the original facts; a shared connection cannot name its caller."""
        pending, self._pending = self._pending, []
        shared_connects = self.accepted()
        return [
            replace(fact, connects=0, shared_connects=shared_connects)
            for fact in pending
        ]


def _rank(word: tuple[str, str | None]) -> float:
    """The position of a refusal word in the documented precedence."""
    code, detail = word
    if detail is not None and "_DEPLOYMENT_PREMISE" in detail:
        return 4
    if code in ("PIE-R1001", "PIE-R1002") or detail == "PUBLIC_ROUTE_UNAVAILABLE":
        return 1
    order = {
        "COMPILED_FRESH_PROFILE_REQUIRED": 2,
        "COMPILED_BINDING_REQUIRED": 2,
        "COLLECTION_ROUTE": 3,
        "COLLECTION_LEAF": 6,
        "PUBLIC_R2_LIVE_QUERY": 7.0,
        "PUBLIC_R2_COLLECTION": 7.1,
        "COLLECTION_ENTRY": 8,
    }
    if detail in order:
        return order[detail]
    if detail is not None and detail.startswith("PUBLIC_R2_"):
        return 7.2
    return 5  # the execution target and result contract checks


def _applicable(fact: Fact, control: Fact | None) -> set[tuple[str, str | None]]:
    """The refusals that apply to a collection-carrying cell at once."""
    words = set()
    if control is not None and control.refused and not any(control.effects):
        words.add(control.word)
    if fact.route != "postgres_rows":
        words.add(("PIE-R1003", "COLLECTION_ROUTE"))
    if fact.entry in ("save_recoverable", "recover"):
        words.add(("PIE-R1004", "PUBLIC_R2_COLLECTION"))
    if fact.entry == "relay_live":
        words.add(("PIE-R1004", "COLLECTION_ENTRY"))
    return words


def _follows(fact: Fact, control: Fact | None) -> bool:
    """An admitted transitional cell stops where its flat control stops, with
    its word; any other word, a workspace word included, is a third outcome."""
    return (
        control is not None
        and (fact.word, fact.effects) == (control.word, control.effects)
        and fact.code != "PIE-R1999"
        and not fact.code.startswith("RAISED:")
    )


def laws(facts: Iterable[Fact], expected=EXPECTED) -> tuple[str, ...]:
    """The ids of the matrix laws the facts break; empty when all hold. A
    fact with an empty closure is the flat control of its cell."""
    facts = tuple(facts)
    controls = {f.key: f for f in facts if not f.closure}
    broken = set()
    for f in facts:
        if f.again != (f.code, f.detail, f.workspaces, f.sinks) or (
            f.refused
            and (
                f.chained
                or f.leaked
                or not re.fullmatch(r"[A-Z][A-Z0-9_]*", f.detail or "NONE")
            )
        ):
            broken.add("L6")
        if not f.closure:
            continue
        cell = expected.get((f.dialect, f.entry, f.route, f.origin))
        kind = cell[0] if cell else None
        control = controls.get(f.key)
        follows = kind == "T" and _follows(f, control)
        if f.refused and (f.shared_connects or (not follows and any(f.effects))):
            broken.add("L1")
        if control is not None and kind != "A" and not follows:
            words: set[str | None] = set(COLLECTION_WORDS)
            if control.refused and not any(control.effects):
                words.add(control.detail)
            if not f.refused or any(f.effects) or f.detail not in words:
                broken.add("L2")
        if kind == "P" and f.word != cell[1:]:
            broken.add("L4")
        if kind == "T" and not follows:
            broken.add("L5")
        applicable = _applicable(f, control)
        if len(applicable) > 1 and f.word != min(applicable, key=_rank):
            broken.add("L7")
    nested_facts = [f for f in facts if f.closure]
    closures: dict[Any, set[Any]] = {}
    leaves: dict[Any, dict[Any, set[Any]]] = {}
    for f in nested_facts:
        if f.detail != "COLLECTION_LEAF":
            closures.setdefault((f.key, f.leaf), set()).add(f.word)
        if f.leaf is not None and f.detail != "COLLECTION_LEAF":
            group = leaves.setdefault(f.key[1:] + (f.closure,), {})
            group.setdefault(f.leaf, set()).add(f.word)
    if any(len(words) > 1 for words in closures.values()):
        broken.add("L3")
    for group in leaves.values():
        if len(group) > 1 and len(set().union(*group.values())) > 1:
            broken.add("L8")
    return tuple(sorted(broken))
