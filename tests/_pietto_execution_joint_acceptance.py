"""Joint acceptance of the Phase70 shapes on one candidate wheel: every public
operation on every route over one declarative shape table; importing acquires
nothing.

Run explicitly where the premises hold (Validation Runner Acceptance R4 row 4:
Docker with the pinned PostgreSQL 18.6 and MySQL 8.4.12 images, nothing
pulled):

    python tests/_pietto_execution_joint_acceptance.py run --directory NEW \\
        --wheel WHEEL --interpreter CPYTHON --house DIR [--cache DIR] \\
        [--target postgres|mysql|all]
    python tests/_pietto_execution_joint_acceptance.py check --report REPORT \\
        [--report REPORT]

`run` materializes one prefix of the exact wheel with the three route extras
from the S18 wheelhouse. Then, one target at a time, it acquires one owned
container through the target-conformance facility, installs the retained-source
fixture of the public R2 witnesses (`setup_target`) and runs this module's
worker in the prefix as a fresh `-I -B` interpreter, with the tests directory,
never `src`, on its path and the access on standard input; the container is
removed before the next target. For each shape of SHAPES and each route of the
target the worker records raw facts only: compile, bundle export, load and
re-export, a probe of execute, save, save_recoverable, recover and relay_live
against a loopback port that only counts connections and a workspace and sink
that do not exist (so a request that passes every request check stops at the
workspace or sink, before any connection), the parameter negatives, and, for
each operation whose probe passed, the real operation: execute (live and
loaded), save with R1 (open_saved_read with ack, verified_export,
publish_saved_generation, refused value and parameter restatements,
release_saved_read), save_recoverable with a failed prefix then refused
parameter restatements and recover, and relay_live. `report.json`
records the probe, checker, docs and wheel digests, and the independent checker
`_pietto_execution_joint_acceptance_check` judges it against literal oracles;
`check` judges the reports of two single-target campaigns as one.
Ordinary pytest never runs a target; it runs `offline_report` (the same facts
through the probes, against the checkout) with the native steps against a
stand-in owner, and the checker.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, fields
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.execution-joint-acceptance.v1"
ROUTES = {
    "postgres_rows": "postgres",
    "postgres_adbc": "postgres",
    "mysql_rows": "mysql",
}
OPERATIONS = ("execute", "save", "save_recoverable", "recover", "relay_live")
# Where a probe that passed every request check stops: an unopened handle, the
# workspace that does not exist, or the sink that does not exist.
REACHED = {
    "save": ("PIE-R1009", "WORKSPACE_OBJECT"),
    "save_recoverable": ("PIE-R1009", "WORKSPACE_OBJECT"),
    "recover": ("PIE-R1009", "WORKSPACE_OBJECT"),
    "relay_live": ("PIE-R1002", "SINK_IDENTITY"),
}
RECIPE = ("execute-postgres", "execute-postgres-adbc", "execute-mysql")
LIMITS = {"batch_rows": 4, "max_rows": 64, "seconds": 60}
BUDGET = 8 * 1024 * 1024
WORKER_SECONDS = 3600
TEXT = "雪?%s $1"


@dataclass(frozen=True)
class Shape:
    """One query `result` over the published emission rows: `rows` reads the
    relation "phase66 source é" (id BIG, BIG, 0, 1) and `other`, when
    declared, the relation `p0`, which holds the same four rows; a
    `sourceless` shape reads neither and its contract describes no source.
    `values` restates the slots of the literal policy, `bindings` gives the
    declared parameters of each execution (None: no header; the first one is
    saved), `negatives` are execute bindings (one that names its dialects
    applies to their routes only), `vectors` R1 value restatements
    and `restated` R1 and R2 parameter restatements that must be refused.
    `recovers` is False for a shape of fewer than nine rows that R2 accepts:
    no prefix of it would fail, so R2 runs its probes only."""

    name: str
    body: str
    other: bool = False
    sourceless: bool = False
    policy: str = "preserve"
    values: tuple = ()
    bindings: tuple = (None,)
    negatives: tuple = ()
    vectors: tuple = ()
    restated: tuple = ()
    recovers: bool = True


# Every shape whose R2 must succeed produces more than 8 rows, so the prefix
# limits of the public R2 witnesses leave a FAILED prefix to recover; the
# others are kept small, since every row is saved, read and relayed once per
# route.
SHAPES = (
    # S03: two chained lets, a CROSS JOIN inside the second (16 rows, NULL flag).
    Shape(
        "let_chain",
        """query result:
    let kept:
        from rows
        where id >= 0
        select:
            id
            flag
    let paired:
        from rows
        let k = kept
        cross join k
        select:
            a = rows.id
            f = k.flag
    from paired
    select:
        a
        f
""",
        policy="bind-safe",
        values=(0,),
        vectors=(("other_value", (1,)), ("bool_for_int", (False,))),
    ),
    # S03: `other` is read only inside a let (16 rows).
    Shape(
        "let_hidden_source",
        """query result:
    let picked:
        from other
        select:
            id
            text
    from rows
    let r = picked
    cross join r
    select:
        a = rows.id
        t = r.text
""",
        other=True,
    ),
    # S05g: a computed Bool group key and min/max of another let value.
    Shape(
        "computed_key",
        """query result:
    from rows
    let positive = id > 0
    let same = id * 1
    group by:
        positive
    select:
        positive
        total = count()
        top = max(same)
        bottom = min(same)
""",
    ),
    # S04a/S04b: WHERE and SELECT reads, a binding obligation, a NULL echo.
    Shape(
        "param_where",
        """query result(low: Int, label: Text | None):
    from rows
    where id > low
    select:
        id
        echo = label
        above = low + 1
""",
        policy="bind-safe",
        values=(1,),
        bindings=({"low": 0, "label": None}, {"low": 1, "label": TEXT}),
        negatives=(
            ("missing", {"low": 0}),
            ("extra", {"low": 0, "label": None, "high": 1}),
            ("not_a_dict", [("low", 0), ("label", None)]),
            ("bool_for_int", {"low": False, "label": None}),
            ("null_for_not_null", {"low": None, "label": None}),
            ("int_for_text", {"low": 0, "label": 0}),
            ("obligation", {"low": 2**63 - 1, "label": None}),
        ),
        restated=(("empty_for_null", {"low": 0, "label": ""}),),
        recovers=False,
    ),
    # S04r: a computed key, LET aggregates, HAVING and a grouped ORDER.
    Shape(
        "param_grouped",
        """query result(low: Int, high: Int | None):
    from rows
    let k = id * low
    let s = id + high
    group by:
        k
    select:
        k
        c = count()
        n = count(s)
        a = avg(s)
        m = max(s)
    having:
        c > low
    order by:
        n desc
""",
        bindings=({"low": 1, "high": None}, {"low": 0, "high": None}),
        # `id * 2` may leave signed 64 bits: MySQL refuses the binding, while
        # PostgreSQL's checked bigint `*` bounds it (Q2) and accepts it.
        negatives=(
            ("obligation", {"low": 2, "high": None}, ("mysql",)),
            ("null_for_not_null", {"low": None, "high": None}),
        ),
    ),
    # S04r: a builtin value argument, QUALIFY and a restated ORDER key.
    Shape(
        "param_result",
        """query result(low: Int, label: Text | None):
    from rows
    where contains(text, label)
    select:
        id
        s = id * low
        u = lower(label)
        r = row_number() window(order by id)
    qualify:
        r <= low + 1
    order by:
        id * low
""",
        bindings=({"low": 1, "label": "a"}, {"low": 1, "label": None}),
        # `low + 1` past the int8 top never fits signed 64 bits, so both
        # dialects refuse it; `id * low` alone PostgreSQL would check (Q2).
        negatives=(("obligation", {"low": 2**63 - 1, "label": "a"}),),
        recovers=False,
    ),
    # S04w: a lag offset and default, an ntile bucket, an nth_value position.
    Shape(
        "param_window",
        """query result(k: Int, b: Int, p: Int, f: Int):
    from rows
    select:
        id
        a = lag(id, k, f) window(order by id)
        n = ntile(b) window(order by id)
        t = nth_value(id, p) window(
            order by id rows between unbounded preceding and unbounded following
        )
""",
        bindings=({"k": 1, "b": 2, "p": 2, "f": -1}, {"k": 0, "b": 1, "p": 1, "f": 0}),
        negatives=(
            ("negative_offset", {"k": -1, "b": 1, "p": 1, "f": 0}),
            ("zero_bucket", {"k": 0, "b": 0, "p": 1, "f": 0}),
            ("zero_position", {"k": 0, "b": 1, "p": 0, "f": 0}),
            ("null_count", {"k": None, "b": 1, "p": 1, "f": 0}),
        ),
        recovers=False,
    ),
    # S05: `base` is read before it is written and by two lets (a diamond);
    # the body CROSS JOINs them (12 rows).
    Shape(
        "let_reuse",
        """query result:
    let low:
        from base
        where id >= 0
        select:
            a = id
    let high:
        from base
        where id > 0
        select:
            a = id
    let base:
        from rows
        select:
            id
    from low
    let h = high
    cross join h
    select:
        x = low.a
        y = h.a
""",
    ),
    # S05j: a computed key that reads both sides of a fanning-out JOIN.
    Shape(
        "computed_key_join",
        """query result:
    from rows
    let o = other
    inner join o on rows.id == o.id
    let positive = rows.id > 0 and o.id > 0
    let level = o.id + rows.id * 0
    group by:
        positive
    select:
        positive
        total = count()
        low = min(level)
        top = max(level)
""",
        other=True,
    ),
    # S06: a typed VALUES let joined with the physical source.
    Shape(
        "values_join",
        """query result:
    let seed:
        values(rid: Int, label: Text | None):
            0, "z"
            1, None
            1, "y"
    from rows
    let s = seed
    inner join s on rows.id == s.rid
    select:
        a = rows.id
        b = s.label
""",
    ),
    # S06: VALUES alone (a duplicate row and an all-NULL tail), no source.
    Shape(
        "values_only",
        """query result:
    values(id: Int, label: Text | None, ratio: Float | None, flag: Bool | None):
        1, "a", 0.5, True
        1, "a", 0.5, True
        2, None, None, None
""",
        sourceless=True,
    ),
    # S08: `other` is read only through EXISTS; a true and a false read.
    Shape(
        "exists_closed",
        """query result:
    let positive:
        from other
        where id > 0
        select:
            id
    let none:
        from rows
        where id < 0
        select:
            id
    from rows
    where exists positive and not exists none
    select:
        id
        some = exists positive
        empty = exists none
""",
        other=True,
    ),
    # S07: scalar reads of one row (MIN) and of no row (NULL).
    Shape(
        "scalar_closed",
        """query result:
    let low:
        from rows
        select:
            k = min(id)
    let none:
        from rows
        where id < 0
        select:
            id
    from rows
    where id > scalar low.k
    select:
        id
        least = scalar low.k
        missing = scalar none.id
""",
    ),
    # S07: a scalar read of four rows is the database's own runtime error.
    Shape(
        "scalar_many",
        """query result:
    from rows
    select:
        id
        one = scalar rows.id
""",
    ),
    # S09: IN over a LIMIT let, and the IN/NOT IN truth table of every flag
    # against no, duplicated TRUE, NULL-only and all four flags.
    Shape(
        "in_closed",
        """query result:
    let smallest:
        from rows
        select:
            id
        order by:
            id
        limit 1
    let flags:
        from rows
        select:
            flag
    let none_flags:
        from flags
        where flag and not flag
        select:
            flag
    let true_flags:
        from flags
        where flag
        select:
            flag
    let null_flags:
        from flags
        where flag is None
        select:
            flag
    from rows
    select:
        id
        flag
        capped = id in smallest
        in_none = flag in none_flags
        out_none = flag not in none_flags
        in_true = flag in true_flags
        out_true = flag not in true_flags
        in_null = flag in null_flags
        out_null = flag not in null_flags
        in_all = flag in flags
        out_all = flag not in flags
""",
    ),
    # S10: correlated EXISTS in WHERE (keeps a row when some `other` row with
    # an id at most its own has a NULL flag) and in SELECT; BIG twice.
    Shape(
        "exists_correlated",
        """query result:
    let bigger:
        capture rows
        from other
        where other.id > rows.id
        select:
            id
    let lower_null:
        capture rows
        from other
        where other.id <= rows.id and other.flag is None
        select:
            id
    from rows
    where exists lower_null
    select:
        id
        has_bigger = exists bigger
""",
        other=True,
    ),
    # S12: CROSS JOIN LATERAL of a top-1 let, then INNER JOIN LATERAL of a
    # let that captures the first JOIN's binding, with an ON over it.
    Shape(
        "lateral_inner",
        """query result:
    let least_bigger:
        capture rows
        from other
        where other.id > rows.id
        select:
            b = id
        order by:
            id
        limit 1
    let twin:
        capture g
        from other
        where other.id == g.b
        select:
            i = id
            f = flag
    from rows
    let g = least_bigger
    cross join g
    let s = twin
    inner join s on s.i > 1
    select:
        a = rows.id
        b = g.b
        f = s.f
""",
        other=True,
    ),
    # S13: LEFT JOIN LATERAL: a left row without any row of the let (BIG) and
    # a left row whose pairs the ON rejects (1) each keep one NULL row.
    Shape(
        "lateral_left",
        """query result:
    let bigger:
        capture rows
        from other
        where other.id > rows.id
        select:
            b = id
    from rows
    let g = bigger
    left join g on g.b == 1
    select:
        a = rows.id
        b = g.b
""",
        other=True,
    ),
    # S14: a correlated scalar of no or one row, IN and NOT IN over
    # correlated lets with empty, NULL-holding and NULL-free rows.
    Shape(
        "scalar_in_correlated",
        """query result:
    let twin_text:
        capture rows
        from other
        where other.id == rows.id and other.id < 2
        select:
            t = text
    let lower_flags:
        capture rows
        from other
        where other.id < rows.id
        select:
            flag
    let higher_flags:
        capture rows
        from other
        where other.id > rows.id
        select:
            flag
    from rows
    select:
        id
        t = scalar twin_text.t
        low_in = flag in lower_flags
        high_out = flag not in higher_flags
""",
        other=True,
    ),
    # S14: positive IN over correlated top-1 lets, PostgreSQL only. Over
    # `other` where other.id >= rows.id, `a` reads the DESC pick and `b` the
    # ASC pick: without the LIMIT `a` would always be TRUE, and a LIMIT taken
    # before the correlation would make `b` FALSE for BIG and 1.
    Shape(
        "in_limit",
        """query result:
    let top_desc:
        capture rows
        from other
        where other.id >= rows.id
        select:
            id
        order by:
            id desc
        limit 1
    let top_asc:
        capture rows
        from other
        where other.id >= rows.id
        select:
            id
        order by:
            id
        limit 1
    from rows
    select:
        id
        a = id in top_desc
        b = id in top_asc
""",
        other=True,
    ),
    # S15: a descending series alone (no source), PostgreSQL only.
    Shape(
        "series_only",
        """query result:
    from generate_series(5, -1, -3) as n
    select:
        n
""",
        sourceless=True,
    ),
    # S15: a series joined with the physical source, PostgreSQL only.
    Shape(
        "series_join",
        """query result:
    from generate_series(2, 0, -1) as n
    let r = rows
    inner join r on n.n == r.id
    select:
        n = n.n
        t = r.text
""",
    ),
    # S11 with S10/S13: header parameters read inside a let joined LEFT
    # LATERAL, in that JOIN's ON and inside a let read by EXISTS.
    Shape(
        "param_capture",
        """query result(cut: Int, label: Text | None):
    let bigger:
        capture rows
        from other
        where other.id > rows.id and other.id > cut
        select:
            b = id
    let tagged:
        capture rows
        from other
        where other.id == rows.id and other.text != label
        select:
            id
    from rows
    let g = bigger
    left join g on rows.id != cut
    where exists tagged
    select:
        a = rows.id
        b = g.b
""",
        other=True,
        bindings=({"cut": 1, "label": "a "}, {"cut": 0, "label": TEXT}),
    ),
    # S11: a parameter read by a let and by the body; nine rows, so R2
    # recovers the saved binding, and R1 and R2 refuse its restatements.
    Shape(
        "param_r2",
        """query result(low: Int):
    let kept:
        from other
        where id >= low
        select:
            id
    from rows
    let k = kept
    cross join k
    where rows.id >= low
    select:
        a = rows.id
        b = k.id
""",
        other=True,
        bindings=({"low": 1}, {"low": 2}),
        restated=(
            ("other_value", {"low": 2}),
            ("bool_for_int", {"low": True}),
            ("missing", {}),
        ),
    ),
)


def write_project(directory: Path, target: str, shape: Shape) -> Path:
    """The published one-source fixture (exact identifier case and the native
    parameter protocol) with `shape.body` as its query, plus `other`."""
    import _pietto_sql_emission as emission

    item = emission.parameterized_fixture(target, shape.body)
    source, contract = item["source"], json.loads(item["contract"])
    if shape.sourceless:
        contract["sources"] = []
    if shape.other:
        other = json.loads(json.dumps(contract["sources"][0]))
        other["selector"]["name"] = "other"
        other["relation"]["name"] = "p0"
        contract["sources"].append(other)
        head, marker, rest = source.partition("query result")
        source = head + f'source other: Row = {target}.table("other")\n'
        source += marker + rest
    project = directory / (shape.name + "-" + target)
    project.mkdir(parents=True)
    (project / "pietto.toml").write_text(emission.CONFIG, encoding="utf-8")
    (project / "main.pietto").write_text(source, encoding="utf-8")
    (project / "contract.json").write_bytes(emission.encoded(contract))
    return project


def _refusal(error: Any) -> dict[str, Any]:
    return {
        "outcome": "refused",
        "error": type(error).__name__,
        "code": getattr(error, "code", None),
        "detail": getattr(error, "detail", None),
    }


def _guarded(call: Any) -> Any:
    """Run one native step; any exception becomes its raw fact, with the
    server's SQLSTATE and the ended attempt's terminal and cleanup facts."""
    try:
        return call()
    except Exception as error:
        fact = _refusal(error) | {"outcome": "failed", "reason": str(error)[:200]}
        fact["sqlstate"] = getattr(getattr(error, "failure", None), "sqlstate", None)
        outcome = getattr(error, "outcome", None)
        if outcome is not None:
            fact["attempt"] = [
                outcome.end,
                outcome.transaction,
                outcome.cleanup,
                [[item.code, item.phase] for item in outcome.cleanup_failures],
            ]
        return fact


def _keywords(function: Any, parameters: Any) -> dict[str, Any]:
    """`parameters=` for an operation whose signature takes it."""
    if parameters is None or "parameters" not in inspect.signature(function).parameters:
        return {}
    return {"parameters": parameters}


def _compile(execution: Any, project: Path, target: str, policy: str) -> Any:
    try:
        query = execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=target,
            emission_contract="contract.json",
            literal_policy=policy,
        )
    except execution.CompileRejected as error:
        document = json.loads(error.emission)
        blockers = document.get("blockers", ())
        return None, {
            "outcome": "rejected",
            "status": error.status,
            "codes": [item["code"] for item in (*document["diagnostics"], *blockers)],
            "details": [(item.get("subject") or {}).get("detail") for item in blockers],
        }
    except execution.ExecutionError as error:
        return None, _refusal(error)
    document = json.loads(query.emission)
    return query, {
        "outcome": "compiled",
        "origin": query.origin,
        "format": document["format"],
        "parameters": [list(item) for item in query.parameters],
        "slots": list(query.slots),
        "sql": document["sql"],
    }


def _bundle(execution: Any, query: Any) -> Any:
    try:
        bundle = execution.export_bundle(query)
        loaded = execution.load_bundle(
            bundle.payload,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        )
        again = execution.export_bundle(loaded)
    except execution.ExecutionError as error:
        return None, None, _refusal(error)
    return (
        loaded,
        bundle,
        {
            "outcome": "loaded",
            "records": [bundle.pin, bundle.producer, bundle.compatibility],
            "query": [
                loaded.origin,
                loaded.module,
                loaded.kind,
                loaded.name,
                loaded.dialect,
                loaded.literal_policy,
                list(loaded.slots),
                [list(item) for item in loaded.parameters],
                loaded.emission,
            ],
            "reexported": [
                again.payload == bundle.payload,
                again.pin == bundle.pin,
                again.producer == bundle.producer,
                again.compatibility == bundle.compatibility,
            ],
        },
    )


@contextmanager
def sentinel():
    """A loopback port that accepts and closes every connection and counts
    them, so a request that connected fails fast instead of waiting."""
    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(0.01)
    accepted: list[int] = []
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                connection, _ = listener.accept()
            except OSError:
                continue
            accepted.append(1)
            connection.close()

    thread = threading.Thread(target=serve, name="joint-sentinel", daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1], accepted
    finally:
        stop.set()
        thread.join()
        listener.setblocking(False)
        while True:
            try:
                listener.accept()[0].close()
            except OSError:
                break
            accepted.append(1)
        listener.close()


@dataclass(frozen=True)
class Case:
    """One shape compiled for one route, with its bundle when it has one."""

    execution: Any
    work: Path
    target: str
    route: str
    shape: Shape
    query: Any
    loaded: Any
    bundle: Any

    def inputs(self, access: dict[str, Any], schemas: Any) -> tuple[Any, Any]:
        e = self.execution
        if self.target == "postgres":
            return e.PostgresAccess(**access), e.PostgresDeploymentPremise(
                tuple(schemas)
            )
        return e.MySQLAccess(**access), e.MySQLDeploymentPremise(tuple(schemas))

    def records(self) -> dict[str, str]:
        """The bundle's trust records (zeros for a query without a bundle)."""
        found = self.bundle
        return {
            "expected_pin": "0" * 64 if found is None else found.pin,
            "accepted_producer": "0" * 64 if found is None else found.producer,
            "accepted_compatibility": "0" * 64
            if found is None
            else found.compatibility,
        }

    def requirements(self, access: dict[str, Any], providers: Any) -> tuple:
        """One R2 source input per compiled source in compiled order (the
        public R2 witnesses' private reading of that order); a source without
        a provider gets an input that could never qualify."""
        role = access.get("account") or access["user"]
        by_source = {(item["namespace"], item["name"]): item for item in providers}
        inputs = []
        for source in self.query._template.artifact.request.sources:
            item = by_source.get((source.namespace, source.name)) or {
                "provider": "unqualified",
                "version": "v1",
                "revision": "r1",
                "namespace": source.namespace,
                "registry": "unqualified",
                "definition": "SELECT 1",
                "tokens": ["p68_part", "p68_lid"],
            }
            inputs.append(
                self.execution.R2SourceInput(
                    source.namespace,
                    source.name,
                    item["provider"],
                    item["version"],
                    item["revision"],
                    item["namespace"],
                    item["registry"],
                    item["definition"],
                    tuple(item["tokens"]),
                    role,
                    "Owned fixture: immutable token/payload and complete visible "
                    "domain; version retained until explicit target cleanup.",
                )
            )
        return tuple(inputs)

    def call(self, name: str, /, *args: Any, binding: Any, values=None, **keywords):
        """One public operation with the shape's values (or `values`) and,
        when its signature takes it, `parameters=binding`."""
        function = getattr(self.execution, name)
        return function(
            *args,
            values=self.shape.values if values is None else values,
            **keywords,
            **_keywords(function, binding),
        )


def _probe(case: Case, operation: str, binding: Any, access, schemas) -> dict:
    """One request on the sentinel port with an unopened workspace and sink."""
    e = case.execution
    root = case.work / ("unopened-" + secrets.token_hex(6))
    with sentinel() as (port, accepted):
        probe_access, premise = case.inputs(
            access | {"port": port, "password": "probe"}, schemas
        )
        workspace = object.__new__(e.WorkspaceRef)
        object.__setattr__(workspace, "root", str(root))
        object.__setattr__(workspace, "identity", "ws-" + "0" * 32)
        common = dict(
            route=case.route,
            access=probe_access,
            premise=premise,
            limits=e.ExecutionLimits(**LIMITS),
        )
        saved = dict(common, operation=e.new_operation())
        r2 = dict(saved, source_requirements=case.requirements(access, ()))
        args, keywords = {
            "execute": ((case.query,), common),
            "save": ((workspace, case.query), saved),
            "save_recoverable": ((workspace, case.query), r2),
            "recover": (
                (workspace,),
                dict(
                    r2,
                    **case.records(),
                    query=case.query,
                    job="job-" + "0" * 32,
                    generation="gen-" + "0" * 32,
                    checkpoint=None,
                    purpose="s17-joint-probe",
                    seconds=LIMITS["seconds"],
                ),
            ),
            "relay_live": (
                (workspace, case.query),
                dict(
                    saved,
                    sink_root=str(case.work / ("unopened-" + secrets.token_hex(6))),
                    expected_sink_identity="sink-" + "0" * 32,
                    sink_namespace="s17",
                    sink_epoch=1,
                    sink_retention="r",
                    sink_budget_bytes=BUDGET,
                ),
            ),
        }[operation]
        fact: dict[str, Any]
        try:
            value = case.call(operation, *args, binding=binding, **keywords)
        except e.ExecutionError as error:
            fact = _refusal(error)
        else:
            fact = {"outcome": "prepared" if operation == "execute" else "replied"}
            getattr(value, "close", lambda: None)()
        fact["parameters"] = bool(_keywords(getattr(e, operation), binding))
    fact["connected"] = bool(accepted)
    fact["workspace"] = os.path.lexists(root)
    return fact


def _passed(probe: dict[str, Any], operation: str) -> bool:
    if operation == "execute":
        return probe.get("outcome") == "prepared"
    return (probe.get("code"), probe.get("detail")) == REACHED[operation]


def _plain(batch: Any) -> list[list[Any]]:
    """The rows of one result batch, read through PyArrow (an installed
    route extra, never imported by ordinary pytest)."""
    pa = importlib.import_module("pyarrow")

    def value(item: Any) -> Any:
        if item is None or type(item) in (bool, int, float, str):
            return item
        return {"type": type(item).__name__, "text": str(item)}

    rows = pa.record_batch(batch).to_pylist()
    return [[value(item) for item in row.values()] for row in rows]


def _execute(case: Case, query: Any, access: Any, premise: Any, binding: Any):
    rows: list[list[Any]] = []
    with case.call(
        "execute",
        query,
        binding=binding,
        route=case.route,
        access=access,
        premise=premise,
        limits=case.execution.ExecutionLimits(**LIMITS),
    ) as result:
        for batch in result:
            with batch:
                rows += _plain(batch)
    outcome = result.outcome
    primary = outcome.primary
    return {
        "outcome": "rows",
        "rows": rows,
        "end": outcome.end,
        "transaction": outcome.transaction,
        "primary": None if primary is None else [primary.code, primary.detail],
    }


def _exported(case: Case, workspace: Any, captured: Any, binding: Any):
    rows: list[list[Any]] = []
    with case.call(
        "verified_export",
        workspace,
        binding=binding,
        **case.records(),
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        scope="complete_capture",
        extent=captured.extent,
        purpose="s17-joint-export",
        route=case.route,
        seconds=LIMITS["seconds"],
        batch_rows=LIMITS["batch_rows"],
    ) as exported:
        for batch in exported:
            with batch:
                rows += _plain(batch)
    return rows


def _r1(case: Case, workspace: Any, captured: Any, binding: Any) -> dict:
    """The four R1 entries on one complete generation, then the refusals."""
    e = case.execution
    new = e.new_operation
    common = dict(
        case.records(),
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        scope="complete_capture",
        extent=captured.extent,
        purpose="s17-joint-r1",
        route=case.route,
        batch_rows=LIMITS["batch_rows"],
        seconds=LIMITS["seconds"],
    )

    def opened(consumer: str, register: Any, values=None, parameters=binding):
        return case.call(
            "open_saved_read",
            workspace,
            binding=parameters,
            values=values,
            consumer=consumer,
            register_operation=register,
            open_operation=new(),
            **common,
        )

    def refused(consumer: str, register: Any, values=None, parameters=binding):
        try:
            opened(consumer, register, values, parameters).close()
        except e.ExecutionError as error:
            return _refusal(error)
        return {"outcome": "opened"}

    consumer = e.new_consumer_identity()
    facts: dict[str, Any] = {}
    rows: list[list[Any]] = []
    reader = opened(consumer, new())
    try:
        while True:
            item = reader.next(LIMITS["batch_rows"], operation=new())
            if type(item) is e.SavedReadEnd:
                facts["end"] = [
                    item.terminal,
                    item.checkpoint == captured.checkpoint,
                    item.extent,
                    item.acknowledged,
                ]
                break
            with item.batch:
                rows += _plain(item.batch)
            reader.ack(item, operation=new())
    finally:
        reader.close()
    facts["rows"] = rows
    facts["export"] = _exported(case, workspace, captured, binding)
    published = case.call(
        "publish_saved_generation",
        workspace,
        binding=binding,
        **case.records(),
        job=captured.job,
        generation=captured.identity,
        checkpoint=captured.checkpoint,
        closing=captured.closings[-1],
        purpose="s17-joint-publication",
        route=case.route,
        isolation="stable",
        seconds=LIMITS["seconds"],
        operation=new(),
    )
    facts["publication"] = [published.terminal, published.extent]
    facts["vectors"] = {
        name: refused(e.new_consumer_identity(), new(), values)
        for name, values in case.shape.vectors
    }
    facts["restated"] = {
        name: refused(e.new_consumer_identity(), new(), parameters=parameters)
        for name, parameters in case.shape.restated
    }
    released = case.call(
        "release_saved_read",
        workspace,
        binding=binding,
        consumer=consumer,
        operation=new(),
        **common,
    )
    facts["release"] = released.kind
    facts["released_reopen"] = refused(consumer, None)
    return facts


def _saved(case: Case, journey: Any, access: Any, premise: Any, binding: Any):
    e = case.execution
    workspace = e.create_workspace(case.work / "save", budget_bytes=BUDGET)
    reply = case.call(
        "save",
        workspace,
        case.query,
        binding=binding,
        operation=e.new_operation(),
        route=case.route,
        access=access,
        premise=premise,
        limits=e.ExecutionLimits(**LIMITS),
    )
    facts = {
        "terminal": reply.terminal,
        "settlement": reply.settlement,
        "cleanup": reply.cleanup is not None,
    }
    if reply.terminal != "COMPLETED":
        return facts
    captured = journey.generation(e, workspace, reply)
    return facts | {
        "extent": captured.extent,
        "closings": len(captured.closings),
        "r1": _guarded(lambda: _r1(case, workspace, captured, binding)),
    }


def _recoverable(case, journey, access, premise, requirements, binding) -> dict:
    """A FAILED prefix under the R2 witnesses' prefix limits, then recover."""
    from _pietto_execution_recovery_cases import prefix_limits, recovery_limits

    e = case.execution
    workspace = e.create_workspace(case.work / "r2", budget_bytes=BUDGET)
    common = dict(
        source_requirements=requirements,
        route=case.route,
        access=access,
        premise=premise,
    )
    failed = case.call(
        "save_recoverable",
        workspace,
        case.query,
        binding=binding,
        operation=e.new_operation(),
        limits=prefix_limits(),
        **common,
    )
    prefix = journey.generation(e, workspace, failed, complete=False)
    recovery = dict(
        common,
        **case.records(),
        query=case.query,
        job=prefix.job,
        generation=prefix.identity,
        checkpoint=prefix.checkpoint,
        limits=recovery_limits(),
        purpose="s17-joint-r2",
        seconds=int(recovery_limits().seconds),
    )
    restated: dict[str, Any] = {}
    for name, parameters in case.shape.restated:
        try:
            case.call(
                "recover",
                workspace,
                binding=parameters,
                operation=e.new_operation(),
                **recovery,
            )
        except e.ExecutionError as error:
            restated[name] = _refusal(error)
        else:
            restated[name] = {"outcome": "recovered"}
    recovered = case.call(
        "recover", workspace, binding=binding, operation=e.new_operation(), **recovery
    )
    completed = journey.generation(e, workspace, recovered)
    return {
        "prefix": [failed.terminal, failed.cleanup is not None],
        "prefix_closings": len(prefix.closings),
        "restated": restated,
        "recover": [
            recovered.terminal,
            recovered.settlement,
            recovered.cleanup is not None,
        ],
        "extent": completed.extent,
        "closings": len(completed.closings),
        "rows": _exported(case, workspace, completed, binding),
    }


def _relayed(case: Case, journey: Any, access: Any, premise: Any, binding: Any):
    e = case.execution
    workspace = e.create_workspace(case.work / "relay", budget_bytes=BUDGET)
    sink = e.create_reference_sink(
        str(case.work / "sink"), namespace="s17", epoch=1, retention_seconds=60
    )
    reply = case.call(
        "relay_live",
        workspace,
        case.query,
        binding=binding,
        operation=e.new_operation(),
        route=case.route,
        access=access,
        premise=premise,
        sink_root=sink.root,
        expected_sink_identity=sink.identity,
        sink_namespace=sink.namespace,
        sink_epoch=sink.epoch,
        sink_retention=sink.retention,
        sink_budget_bytes=sink.budget_bytes,
        sink_busy_seconds=sink.busy_seconds,
        limits=e.ExecutionLimits(**LIMITS),
    )
    facts = {
        "terminal": reply.terminal,
        "settlement": reply.settlement,
        "cleanup": reply.cleanup is not None,
    }
    if reply.terminal != "COMPLETED":
        return facts
    return facts | {"extent": journey.generation(e, workspace, reply).extent}


def _native(case: Case, probes: dict[str, Any], native: dict[str, Any]) -> dict:
    """Each operation whose probe passed, for real on the target."""
    import _pietto_execution_public_journey_check as journey

    access, premise = case.inputs(native["access"], native["schemas"])
    binding = case.shape.bindings[0]
    facts: dict[str, Any] = {}
    if _passed(probes["execute"], "execute"):
        facts["execute"] = [
            {
                "live": _guarded(
                    lambda: _execute(case, case.query, access, premise, item)
                ),
                "loaded": None
                if case.loaded is None
                else _guarded(
                    lambda: _execute(case, case.loaded, access, premise, item)
                ),
            }
            for item in case.shape.bindings
        ]
    if _passed(probes["save"], "save"):
        facts["save"] = _guarded(
            lambda: _saved(case, journey, access, premise, binding)
        )
    if (
        case.shape.recovers
        and _passed(probes["save_recoverable"], "save_recoverable")
        and _passed(probes["recover"], "recover")
    ):
        requirements = case.requirements(native["access"], native["providers"])
        facts["r2"] = _guarded(
            lambda: _recoverable(case, journey, access, premise, requirements, binding)
        )
    if _passed(probes["relay_live"], "relay_live"):
        facts["relay_live"] = _guarded(
            lambda: _relayed(case, journey, access, premise, binding)
        )
    return facts


def target_facts(
    execution, work, target, routes, access, schemas, native=None, table=SHAPES
):
    """{shape: {"dialects": {target: ...}, "routes": {route: ...}}} for one
    target and each shape of `table`; `access`/`schemas` shape the probe
    access, and `native(case, probes)`, when given, adds each route's real
    operations."""
    shapes: dict[str, Any] = {}
    for shape in table:
        directory = work / shape.name
        directory.mkdir(parents=True)
        project = write_project(directory, target, shape)
        query, compiled = _compile(execution, project, target, shape.policy)
        dialect = {"compile": compiled, "bundle": None}
        record = shapes[shape.name] = {"dialects": {target: dialect}, "routes": {}}
        if query is None:
            continue
        loaded, bundle, dialect["bundle"] = _bundle(execution, query)
        for route in routes:
            case = Case(
                execution,
                directory / route,
                target,
                route,
                shape,
                query,
                loaded,
                bundle,
            )
            case.work.mkdir()
            probes = {
                operation: _probe(case, operation, shape.bindings[0], access, schemas)
                for operation in OPERATIONS
            }
            facts: dict[str, Any] = {
                "probe": probes,
                "negatives": {
                    name: _probe(case, "execute", parameters, access, schemas)
                    for name, parameters, *dialects in shape.negatives
                    if not dialects or target in dialects[0]
                },
            }
            if native is not None:
                facts["native"] = native(case, probes)
            record["routes"][route] = facts
    return shapes


def merge(into: dict[str, Any], shapes: dict[str, Any]) -> None:
    for name, record in shapes.items():
        entry = into.setdefault(name, {"dialects": {}, "routes": {}})
        entry["dialects"].update(record["dialects"])
        entry["routes"].update(record["routes"])


def _fields(value: Any) -> dict[str, Any]:
    return {item.name: getattr(value, item.name) for item in fields(value)}


def probe_inputs(target: str, ca: Path) -> tuple[dict[str, Any], list[str]]:
    """The access fields and premise schemas of the public R2 witnesses
    (`target_inputs`) for a resource that was never acquired; `ca` is never
    read."""
    from _pietto_execution_recovery_cases import target_inputs

    resource = SimpleNamespace(
        target=target, port=1, _passwords=("", "probe"), ca_path=ca
    )
    access, premise = target_inputs(resource)
    return _fields(access), list(premise.schemas)


def offline_report(directory: Path, native: Any = None, table=SHAPES) -> dict:
    """The database-free facts of each shape of `table` on every route with
    the importable Pietto: compile, bundle, probes and negatives, no
    connection. `native` is passed to `target_facts` (pytest passes the
    native steps of a stand-in owner)."""
    import pietto.execution as execution

    report: dict[str, Any] = {"format": FORMAT, "mode": "offline", "shapes": {}}
    for target in ("postgres", "mysql"):
        access, schemas = probe_inputs(target, directory / "unread-ca.pem")
        merge(
            report["shapes"],
            target_facts(
                execution,
                directory / target,
                target,
                [route for route, owner in ROUTES.items() if owner == target],
                access,
                schemas,
                native,
                table,
            ),
        )
    return report


def worker() -> int:
    """Run inside the installed prefix: one target's facts to `output`."""
    config = json.loads(sys.stdin.readline())
    sys.path.insert(0, config["tests"])
    import pietto
    import pietto.execution as execution

    inputs = {
        "access": config["access"],
        "schemas": config["schemas"],
        "providers": config["providers"],
    }
    facts = {
        "origin": "checkout"
        if Path(pietto.__file__).resolve().is_relative_to(ROOT / "src")
        else "installed",
        "shapes": target_facts(
            execution,
            Path(config["work"]),
            config["target"],
            config["routes"],
            config["access"],
            config["schemas"],
            lambda case, probes: _native(case, probes, inputs),
        ),
    }
    descriptor = os.open(config["output"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(facts, stream, sort_keys=True)
    return 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context(wheel: Path) -> dict[str, str]:
    return {
        "probe": _sha256(Path(__file__)),
        "check": _sha256(ROOT / "tests/_pietto_execution_joint_acceptance_check.py"),
        "docs": _sha256(ROOT / "docs/execution.md"),
        "wheel": wheel.name,
        "wheel_sha256": _sha256(wheel),
    }


def finish(directory: Path, report: dict[str, Any], secrets_: tuple) -> Any:
    import _pietto_execution_joint_acceptance_check as check

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if any(secret and secret in encoded for secret in secrets_):
        raise ValueError("credential in report")
    path = directory / "report.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(encoded)
    return check.check(json.loads(path.read_text(encoding="utf-8")))


def run(
    directory: Path,
    *,
    wheel: Path,
    interpreter: Path,
    house_root=None,
    cache=None,
    targets=("postgres", "mysql"),
):
    """One explicit campaign: one prefix, then one owned container per target."""
    import _pietto_execution_api_probe as api_probe
    import _pietto_execution_jobs_probe as workspace_probe
    import _pietto_target_conformance_resources as resources_module
    from _pietto_execution_recovery_cases import setup_target, target_inputs

    directory.mkdir(mode=0o700)
    # The saved-result workspaces live below `directory`: refuse an
    # unqualified storage profile before any installation or container.
    if not workspace_probe.qualified(directory):
        raise ValueError("UNQUALIFIED_STORAGE")
    started = time.monotonic()
    pythons, install = api_probe.prefixes(
        directory,
        {"routes": RECIPE},
        wheel=wheel,
        interpreter=interpreter,
        house_root=house_root or directory,
        cache=cache,
    )
    report: dict[str, Any] = {
        "format": FORMAT,
        "mode": "native",
        "context": context(wheel),
        "install": install,
        "targets": list(targets),
        "workers": {},
        "shapes": {},
        "cleanup": {},
    }
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    passwords: list[str] = []
    try:
        for target in targets:
            root = directory / ("resources-" + target)
            root.mkdir(mode=0o700)
            resource = resources_module.Resources(target, pins["targets"][target], root)
            passwords.extend(resource._passwords)
            try:
                resource.acquire()
                if target == "mysql":
                    from _pietto_execution_api_mysql_native import _configure_tls

                    _configure_tls(resource)
                providers = setup_target(resource)
                access, premise = target_inputs(resource)
                work = directory / ("work-" + target)
                work.mkdir(mode=0o700)
                output = directory / ("facts-" + target + ".json")
                config = {
                    "tests": str(ROOT / "tests"),
                    "work": str(work),
                    "output": str(output),
                    "target": target,
                    "routes": [r for r, owner in ROUTES.items() if owner == target],
                    "access": _fields(access),
                    "schemas": list(premise.schemas),
                    "providers": providers,
                }
                record = api_probe.run(
                    pythons["routes"],
                    [str(Path(__file__)), "worker"],
                    cwd=work,
                    stdin=json.dumps(config) + "\n",
                    seconds=WORKER_SECONDS,
                )
                report["workers"][target] = {
                    "returncode": record["returncode"],
                    "seconds": record["seconds"],
                    "stderr": record["stderr"][-4096:],
                }
                if record["returncode"] == 0:
                    facts = json.loads(output.read_text(encoding="utf-8"))
                    report["workers"][target]["origin"] = facts["origin"]
                    merge(report["shapes"], facts["shapes"])
            except Exception as error:
                report["workers"][target] = {"returncode": None} | _refusal(error)
            finally:
                report["cleanup"][target] = resource.cleanup()["status"]
    finally:
        report["seconds"] = time.monotonic() - started
    return finish(directory, report, tuple(passwords))


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("family", choices=("run", "check", "worker"))
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--interpreter", type=Path)
    parser.add_argument("--house", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--report", type=Path, action="append")
    parser.add_argument("--target", choices=("postgres", "mysql", "all"), default="all")
    args = parser.parse_args()
    if args.family == "worker":
        raise SystemExit(worker())
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]
    import _pietto_execution_joint_acceptance_check as check

    if args.family == "check":
        if not args.report:
            parser.error("--report is required")
        reports = [json.loads(p.read_text(encoding="utf-8")) for p in args.report]
        report = reports[0] if len(reports) == 1 else check.combined(reports)
        verdict = check.check(report)
    else:
        if None in (args.directory, args.wheel, args.interpreter, args.house):
            parser.error("--directory, --wheel, --interpreter and --house are required")
        verdict = run(
            args.directory,
            wheel=args.wheel,
            interpreter=args.interpreter,
            house_root=args.house,
            cache=args.cache,
            targets=("postgres", "mysql") if args.target == "all" else (args.target,),
        )
    print(json.dumps(verdict, sort_keys=True))


if __name__ == "__main__":
    main()
