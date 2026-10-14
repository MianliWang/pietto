"""Independent data-only S11 store/native correspondence; no store or driver code.

Expected values come from the frozen case manifest and the raw native records,
never from the store's query or decoding functions.
"""

from __future__ import annotations

from pathlib import Path
import copy
import json
import os
import shutil
import sqlite3
import stat

CASES = (("A", 1), ("B", 5), ("A_again", 1), ("empty", 2**63 - 1))
STORE_MODULES = (
    "pietto._project.project_job_store",
    "pietto._project.project_job_workspace",
)


def need(condition, category):
    if not condition:
        raise ValueError("S11_" + category)


def routes(target):
    return ("mysql_rows",) if target == "mysql" else ("postgres_rows", "postgres_adbc")


def rows(database: Path):
    """Plain rows of a closed, static backup copy (never the live store)."""
    connection = sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True)
    try:
        return {
            table: [
                tuple(r)
                for r in connection.execute(f"SELECT * FROM {table} ORDER BY 1")
            ]
            for table in (
                "workspace",
                "job",
                "binding",
                "generation",
                "attempt",
                "attempt_terminal",
                "operation",
            )
        }
    finally:
        connection.close()


def check_store_bridge(raw, registration, database, workspace, *, target, password):
    """Each stored attempt equals exactly one fresh native attempt's layers."""
    plan = registration["plan"]
    need(
        [route for route, _group in plan] == list(routes(target))
        and all(
            [(case, number) for case, number, *_ in group] == list(CASES)
            for _route, group in plan
        ),
        "PLAN_DENOMINATOR",
    )
    data = rows(Path(database))
    (job,) = data["job"]
    need(
        job[0] == registration["job"]
        and job[2] == registration["pin"]
        and job[3] == registration["producer"]
        and json.loads(job[4]) == json.loads(json.dumps(registration["compatibility"]))
        and (job[5], job[6]) == ("ACTIVE", 2),
        "JOB_ROW",
    )
    bindings = {r[0]: r for r in data["binding"]}
    generations = {r[0]: r for r in data["generation"]}
    attempts = {r[0]: r for r in data["attempt"]}
    terminals = {r[0]: r for r in data["attempt_terminal"]}
    count = sum(len(group) for _route, group in plan)
    need(
        len(bindings) == len(generations) == len(attempts) == len(terminals) == count
        and len(data["operation"]) == 3 + 4 * count
        and job[8] == len(data["operation"]),
        "STORE_DENOMINATOR",
    )
    results = raw["results"]
    need(len(results) == count, "RAW_DENOMINATOR")
    pids = set()
    seen_references = set(registration["binding_references"])
    for result, (route, (case, number, record, generation)) in zip(
        results,
        ((route, item) for route, group in plan for item in group),
        strict=True,
    ):
        store = result["store"]
        need(
            (result["route"], result["case"]) == (route, case)
            and (store["binding_record"], store["generation"], store["job"])
            == (record, generation, registration["job"]),
            "RESULT_CORRESPONDENCE",
        )
        need(
            json.loads(bindings[record][3]) == [["Int", str(number)]],
            "LITERAL_ORACLE",
        )
        need(
            generations[generation][1:5]
            == (registration["job"], record, route, "stable")
            and dict(json.loads(generations[generation][5]))["target"][2] == route,
            "GENERATION_ROW",
        )
        attempt = attempts.get(store["attempt"])
        need(
            attempt is not None
            and attempt[1:5] == (generation, registration["job"], 1, 2)
            and attempt[6] == result["binding"] == result["layers"]["binding_reference"]
            and result["binding"] not in seen_references,
            "ATTEMPT_LINKAGE",
        )
        seen_references.add(result["binding"])
        terminal = terminals.get(store["attempt"])
        need(
            terminal is not None
            and terminal[1:3] == ("OUTCOME", 2)
            and json.loads(terminal[3]) == json.loads(json.dumps(result["layers"])),
            "TERMINAL_LAYERS",
        )
        layers = json.loads(terminals[store["attempt"]][3])
        need(
            layers["transaction"] == result["outcome"]["transaction"]
            and layers["source"] == result["outcome"]["source"]
            and layers["delivery"] == result["outcome"]["delivery"]
            and layers["cleanup"] == result["outcome"]["cleanup"]
            and layers["local_durable_result"] == "NOT_IMPLEMENTED",
            "OUTCOME_LAYERS",
        )
        pids.add(store["pid"])
    need(
        len(pids) == 1 and registration["pid"] not in pids,
        "PROCESS_SEPARATION",
    )
    for module in STORE_MODULES:
        need(
            module in raw["origins"] and module in registration["origins"],
            "STORE_ORIGIN",
        )
    root = Path(workspace)
    need(
        stat.S_IMODE(root.stat().st_mode) == 0o700
        and sorted(p.name for p in root.iterdir())
        == ["locks", "store.sqlite", "workspace.json"],
        "WORKSPACE_FILES",
    )
    secret = password.encode()
    for path in [*root.rglob("*"), Path(database)]:
        if path.is_file():
            need(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, "PRIVATE_MODE")
            need(secret not in path.read_bytes(), "CREDENTIAL_PERSISTED")


def _coordinated(database, statements):
    connection = sqlite3.connect(database, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        for statement, parameters in statements:
            connection.execute(statement, parameters)
    finally:
        connection.close()


def check_store_bridge_damage(
    raw, registration, database, workspace, *, target, password, scratch
):
    """Coordinated raw and re-encoded store damage that keeps counts and copied IDs."""
    rejected = []
    first = raw["results"][0]
    second = raw["results"][1]
    controls = {
        "raw_attempt_swap": lambda r, d: (
            r["results"][0]["store"].__setitem__("attempt", second["store"]["attempt"]),
            r["results"][1]["store"].__setitem__("attempt", first["store"]["attempt"]),
        ),
        "raw_layers_only": lambda r, d: r["results"][0]["layers"].__setitem__(
            "transaction", "UNKNOWN"
        ),
        "raw_old_reference": lambda r, d: (
            r["results"][0].__setitem__(
                "binding", registration["binding_references"][0]
            ),
            r["results"][0]["layers"].__setitem__(
                "binding_reference", registration["binding_references"][0]
            ),
        ),
        "store_terminal_reencoded": lambda r, d: _coordinated(
            d,
            [
                (
                    "UPDATE attempt_terminal SET outcome = replace(outcome,"
                    ' \'"transaction":"COMMIT_ACK"\', \'"transaction":"UNKNOWN"\')'
                    " WHERE attempt = ?",
                    (first["store"]["attempt"],),
                ),
                (
                    "UPDATE operation SET request = replace(request,"
                    ' \'"transaction":"COMMIT_ACK"\', \'"transaction":"UNKNOWN"\')'
                    " WHERE kind = 'attempt_terminal' AND request LIKE ?",
                    ("%" + first["store"]["attempt"] + "%",),
                ),
            ],
        ),
        "store_vector_reencoded": lambda r, d: _coordinated(
            d,
            [
                (
                    "UPDATE binding SET vector = ? WHERE identity = ?",
                    ('[["Int","6"]]', first["store"]["binding_record"]),
                ),
            ],
        ),
        "store_epoch": lambda r, d: _coordinated(
            d,
            [
                (
                    "UPDATE attempt SET publisher_epoch = 1 WHERE identity = ?",
                    (first["store"]["attempt"],),
                ),
                (
                    "UPDATE attempt_terminal SET publisher_epoch = 1 WHERE attempt = ?",
                    (first["store"]["attempt"],),
                ),
            ],
        ),
        "store_generation_route": lambda r, d: _coordinated(
            d,
            [
                (
                    "UPDATE generation SET route = ? WHERE identity = ?",
                    (
                        "postgres_adbc" if target == "postgres" else "postgres_rows",
                        first["store"]["generation"],
                    ),
                ),
            ],
        ),
    }
    for name, damage in controls.items():
        changed = copy.deepcopy(raw)
        copy_path = Path(scratch) / ("damage-" + name + ".sqlite")
        shutil.copyfile(database, copy_path)
        os.chmod(copy_path, 0o600)
        try:
            damage(changed, str(copy_path))
            try:
                check_store_bridge(
                    changed,
                    registration,
                    copy_path,
                    workspace,
                    target=target,
                    password=password,
                )
            except ValueError as error:
                rejected.append([name, str(error)])
                continue
            raise ValueError("S11_STORE_DAMAGE_ACCEPTED:" + name)
        finally:
            for suffix in ("", "-wal", "-shm"):
                Path(str(copy_path) + suffix).unlink(missing_ok=True)
    return rejected
