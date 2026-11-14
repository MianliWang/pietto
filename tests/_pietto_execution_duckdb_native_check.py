"""The checker of the Phase79 S06 native qualification (preregistration v5,
section 6). `check(report, expected)` returns ACCEPTED, DEGRADED (law 7
only), VOID (a fixture size miss, or an L6 setup above its bound: that
sub-cell only) or the first law that refused; `self_test(expected)` accepts
the honest literal report of every unit and refuses each fabricated shape.
Standard library only: it reads saved facts and judges them."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

MISSING = object()
PARTIAL = ("raised", "second_enter")
LAWS = {"raised": 3, "O": 3, "schema": 4, "batch_schemas": 4, "capture_c2": 4}
SITE = "/s06/probe/lib/python3.13/site-packages"


def _law(key: str) -> int:
    return 4 if key.startswith("rows") else LAWS.get(key, 5)


def _text(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _same(a: Any, b: Any) -> bool:
    """Literal equality that keeps JSON types apart (1, 1.0 and true differ)."""
    return _text(a) == _text(b)


def _under(path: Any, root: Any) -> bool:
    return (
        isinstance(path, str) and isinstance(root, str) and path.startswith(root + "/")
    )


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _interrupted(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    opened, ended = arg
    sent = len(got) - len(opened) - len(ended) if isinstance(got, list) else 0
    return sent >= 1 and _same(got, opened + [["interrupt"]] * sent + ended)


def _settings(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    if not isinstance(got, list) or not all(
        isinstance(row, list) and len(row) == 2 for row in got
    ):
        return False
    seen = {name: value for name, value in got}
    return all(name in seen and _same(seen[name], value) for name, value in arg)


def _same_k(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    points = ("prelock", "register", "unregister")
    if not isinstance(got, dict) or sorted(got) != sorted(points):
        return False
    first = got["prelock"]
    return (
        isinstance(first, list)
        and len(first) == 3
        and all(isinstance(rows, list) and rows for rows in first)
        and all(_same(got[point], first) for point in points)
    )


def _disjoint(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    try:
        capture, caller = got["capture"], got["caller"]
        return (
            bool(capture)
            and bool(caller)
            and all(
                end <= low or high <= start
                for start, end in capture
                for low, high in caller
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _c02a(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    """Section 4d: `path` starts with `argv1`; `pietto` from the tree's src in
    U0 and U1, from the unit's prefix and no source tree in U2 and U3."""
    if not isinstance(got, dict):
        return False
    argv1, path, pietto = got.get("argv1"), got.get("path"), got.get("pietto")
    tree, lane, prefix = got.get("tree"), got.get("lane"), got.get("prefix")
    if not (isinstance(argv1, list) and isinstance(path, list)):
        return False
    if path[: len(argv1)] != argv1:
        return False
    src = f"{tree}/src"
    wanted = {"U0": [src], "U1": [src, identity.get("unit_root")]}.get(unit, [])
    if argv1 != wanted:
        return False
    if unit in ("U0", "U1"):
        return pietto == f"{src}/pietto/__init__.py"
    return (
        prefix == identity.get("python", {}).get("prefix")
        and _under(pietto, prefix)
        and not _under(pietto, tree)
        and not _under(pietto, lane)
    )


def _excludes(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    return isinstance(got, list) and arg not in got


def _range(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    return _number(got) and arg[0] <= got < arg[1]


def _interval(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    return _number(got) and arg[0] < got <= arg[1]


def _differs(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    return (
        isinstance(got, list)
        and len(got) == 2
        and all(isinstance(ns, str) and ns for ns in got)
        and got[0] != got[1]
    )


def _bag(arg: Any, got: Any, unit: str, identity: dict) -> bool:
    return isinstance(got, list) and sorted(map(_text, got)) == sorted(map(_text, arg))


MATCHERS = {
    "$bag": _bag,
    "$interrupted": _interrupted,
    "$settings": _settings,
    "$same": _same_k,
    "$disjoint": _disjoint,
    "$c02a": _c02a,
    "$excludes": _excludes,
    "$range": _range,
    "$interval": _interval,
    "$differs": _differs,
}


def _matcher(want: Any) -> tuple[str, Any] | None:
    if isinstance(want, dict) and len(want) == 1:
        ((name, arg),) = want.items()
        if name.startswith("$"):
            return name, arg
    return None


def _matches(key: str, want: Any, got: Any, unit: str, identity: dict) -> bool:
    matcher = _matcher(want)
    if matcher is not None:
        return MATCHERS[matcher[0]](matcher[1], got, unit, identity)
    if key in PARTIAL and isinstance(want, dict):
        return isinstance(got, dict) and all(
            name in got and _same(got[name], value) for name, value in want.items()
        )
    return _same(got, want)


def declared(expected: dict, unit: str) -> list[tuple[str, str]]:
    """Law 1's (cell, sub-case) list: in U0 one skip line for each cell not
    marked U0 (law 6)."""
    cells = expected["cells"]
    if unit == "U0":
        return [
            (cell, sub)
            for cell in cells
            for sub in (
                cells[cell] if cell in expected["u0_cells"] else [expected["skip"]]
            )
        ]
    return [(cell, sub) for cell in cells for sub in cells[cell]]


def identity_problem(identity: Any, expected: dict, unit: str) -> str | None:
    """Law 2 (section 7): the requirements a unit's identity record meets."""
    if not isinstance(identity, dict):
        return "no identity record"
    want = expected["identity"]
    python = identity.get("python") or {}
    if python.get("version") != want["python"][unit]:
        return "interpreter version"
    if python.get("platform") != want["platform"]:
        return "interpreter platform"
    glibc = re.fullmatch(r"glibc (\d+)\.(\d+)", str(python.get("glibc")))
    if not glibc or [int(glibc[1]), int(glibc[2])] < want["glibc_min"]:
        return "glibc"
    if python.get("isolated") != 1 or python.get("dont_write_bytecode") != 1:
        return "interpreter flags"
    if (identity.get("env") or {}).get("PYTHONDONTWRITEBYTECODE") != "1":
        return "PYTHONDONTWRITEBYTECODE"
    if identity.get("spec_sha256") != expected["spec_sha256"]:
        return "spec digest"
    pietto = identity.get("pietto") or {}
    tree, lane, prefix = pietto.get("tree"), pietto.get("lane"), python.get("prefix")
    root = identity.get("unit_root")
    if unit in ("U0", "U1"):
        if pietto.get("file") != f"{tree}/src/pietto/__init__.py" or tree != lane:
            return "pietto is not the tree's"
    elif (
        not _under(pietto.get("file"), prefix)
        or _under(pietto.get("file"), tree)
        or _under(pietto.get("file"), lane)
        or not pietto.get("record_hashed")
        or pietto.get("record_bad") != []
        or root != prefix
    ):
        return "pietto is not the installed wheel"
    if unit == "U0":
        if identity.get("duckdb") is not None or identity.get("pyarrow") is not None:
            return "U0 has duckdb or pyarrow"
        return None
    for name in ("duckdb", "pyarrow"):
        dist = identity.get(name)
        if not isinstance(dist, dict):
            return f"no {name}"
        expected_dist = want[name]
        tags = (
            expected_dist["tags"] if name == "duckdb" else expected_dist["tags"][unit]
        )
        if dist.get("version") != expected_dist["version"] or dist.get("tags") != tags:
            return f"{name} version or tags"
        if not dist.get("record_hashed") or dist.get("record_bad") != []:
            return f"{name} RECORD"
        files = dist.get("files") or {}
        if not files or not all(_under(path, root) for path in files.values()):
            return f"{name} module outside the unit's prefix"
        if sorted(dist.get("in_record") or {}) != sorted(files) or not all(
            (dist.get("in_record") or {}).values()
        ):
            return f"{name} module not in its RECORD"
    duckdb, pyarrow = identity["duckdb"], identity["pyarrow"]
    if sorted(duckdb["files"]) != ["_duckdb", "duckdb"] or list(pyarrow["files"]) != [
        "pyarrow.lib"
    ]:
        return "module files"
    if duckdb.get("record_hashed") != want["duckdb"]["record_hashed"]:
        return "duckdb RECORD count"
    if duckdb.get("pragma_version") != want["duckdb"]["pragma_version"]:
        return "duckdb pragma_version"
    if duckdb.get("platform") != want["duckdb"]["platform"]:
        return "duckdb platform"
    return None


def _verdict(unit: Any, verdict: str, **more: Any) -> dict[str, Any]:
    return {"unit": unit, "verdict": verdict, **more}


def _refused(unit: Any, law: int, where: str) -> dict[str, Any]:
    return _verdict(unit, "REFUSED", law=law, where=where)


def check(report: Any, expected: dict) -> dict[str, Any]:
    """One unit's verdict over its saved facts (section 6, laws 1 to 8; law 8,
    no retry or fallback, holds because law 1 admits one record each)."""
    unit: Any = report.get("unit") if isinstance(report, dict) else None
    if unit not in expected["units"]:
        return _refused(unit, 1, "unit")
    identity: Any = report.get("identity")
    problem = identity_problem(identity, expected, unit)
    if problem is not None:
        return _refused(unit, 2, problem)
    skip = expected["skip"]
    wanted = declared(expected, unit)
    facts: dict[tuple[str, str], Any] = {}
    for record in report.get("records") or []:
        if not isinstance(record, dict):
            return _refused(unit, 1, "record")
        key: Any = (record.get("cell"), record.get("sub"))
        if record.get("unit") == unit and key[1] == skip and key not in wanted:
            return _refused(unit, 6, f"{key[0]} skipped")
        if record.get("unit") != unit or key not in wanted or key in facts:
            return _refused(unit, 1, f"{record.get('unit')} {key[0]} {key[1]}")
        facts[key] = record.get("facts")
    if len(facts) != len(wanted):
        missing = next(key for key in wanted if key not in facts)
        return _refused(unit, 1, f"{missing[0]} {missing[1]} missing")
    c12 = [facts[key] for key in wanted if key[0] == "C12"]
    unobserved = [
        f for f in c12 if isinstance(f, dict) and f.get("namespace") == "NOT_OBSERVED"
    ]
    if unobserved and len(unobserved) != len(c12):
        return _refused(unit, 7, "C12 observed in part")
    voids = []
    for cell, sub in wanted:
        got = facts[(cell, sub)]
        where = f"{cell} {sub}"
        if not isinstance(got, dict):
            return _refused(unit, 1, where)
        if sub == skip:
            if sorted(got) != ["skip"]:
                return _refused(unit, 6, where)
            continue
        if "skip" in got:
            return _refused(unit, 6, f"{where}: a skip is not a pass")
        if cell == "C12" and unobserved:
            continue
        if "fixture_miss" in got:
            voids.append(f"{where}: fixture size")
            continue
        want = expected["cells"][cell][sub]
        if "setup" in want:
            setup = got.get("setup")
            if not _number(setup) or setup > want["setup"]["$void_above"]:
                voids.append(f"{where}: setup {setup}")
                continue
        for key, value in want.items():
            if key == "setup":
                continue
            found = got.get(key, MISSING)
            if found is MISSING:
                return _refused(unit, _law(key), f"{where}: no {key}")
            if not _matches(key, value, found, unit, identity):
                return _refused(unit, _law(key), f"{where}: {key}")
    if voids:
        return _verdict(unit, "VOID", void=voids)
    if unobserved:
        return _verdict(unit, "DEGRADED", law=7)
    return _verdict(unit, "ACCEPTED")


# The self-test: honest literal reports and fabricated shapes.


def honest_identity(expected: dict, unit: str) -> dict[str, Any]:
    want = expected["identity"]
    lane = "/s06/lane"
    tree = lane if unit in ("U0", "U1") else "/s06/integration"
    prefix = f"/s06/venv-{unit}"
    root = {"U0": prefix, "U1": SITE}.get(unit, prefix)
    identity: dict[str, Any] = {
        "python": {
            "version": want["python"][unit],
            "platform": want["platform"],
            "glibc": "glibc 2.39",
            "isolated": 1,
            "dont_write_bytecode": 1,
            "prefix": prefix,
        },
        "env": {"PYTHONDONTWRITEBYTECODE": "1"},
        "spec_sha256": expected["spec_sha256"],
        "unit_root": root,
        "pietto": {
            "tree": tree,
            "lane": lane,
            "file": f"{tree}/src/pietto/__init__.py"
            if unit in ("U0", "U1")
            else f"{prefix}/lib/site-packages/pietto/__init__.py",
            "record_hashed": None if unit in ("U0", "U1") else 120,
            "record_bad": None if unit in ("U0", "U1") else [],
        },
        "duckdb": None,
        "pyarrow": None,
    }
    if unit != "U0":
        identity["duckdb"] = {
            "version": want["duckdb"]["version"],
            "tags": want["duckdb"]["tags"],
            "record_hashed": want["duckdb"]["record_hashed"],
            "record_bad": [],
            "files": {
                "duckdb": f"{root}/duckdb/__init__.py",
                "_duckdb": f"{root}/_duckdb.abi3.so",
            },
            "in_record": {"duckdb": True, "_duckdb": True},
            "pragma_version": want["duckdb"]["pragma_version"],
            "platform": want["duckdb"]["platform"],
        }
        identity["pyarrow"] = {
            "version": want["pyarrow"]["version"],
            "tags": want["pyarrow"]["tags"][unit],
            "record_hashed": 753,
            "record_bad": [],
            "files": {
                "pyarrow.lib": f"{root}/pyarrow/lib.cpython-313-x86_64-linux-gnu.so"
            },
            "in_record": {"pyarrow.lib": True},
        }
    return identity


def _satisfying(key: str, want: Any, unit: str, identity: dict) -> Any:
    matcher = _matcher(want)
    if matcher is None:
        return copy.deepcopy(want)
    name, arg = matcher
    k = [
        [["system", "main", "abs", "scalar", "[BIGINT]", "BIGINT"]],
        [["threads"]],
        [["system", "main", "BIGINT"]],
    ]
    pietto = identity["pietto"]
    tree = pietto["tree"]
    src = f"{tree}/src"
    argv1 = {"U0": [src], "U1": [src, identity["unit_root"]]}.get(unit, [])
    return {
        "$bag": lambda: copy.deepcopy(arg),
        "$interrupted": lambda: arg[0] + [["interrupt"]] + arg[1],
        "$settings": lambda: [["threads", "1"], *copy.deepcopy(arg)],
        "$same": lambda: {
            "prelock": k,
            "register": copy.deepcopy(k),
            "unregister": copy.deepcopy(k),
        },
        "$disjoint": lambda: {"capture": [[1000, 1016]], "caller": [[0, 32]]},
        "$c02a": lambda: {
            "argv1": argv1,
            "path": [*argv1, "/s06/python313.zip"],
            "pietto": pietto["file"],
            "tree": tree,
            "lane": pietto["lane"],
            "prefix": identity["python"]["prefix"],
        },
        "$excludes": lambda: ["postgres_rows", "postgres_adbc", "mysql_rows"],
        "$range": lambda: arg[0] + 0.1,
        "$interval": lambda: arg[1],
        "$void_above": lambda: arg / 10,
        "$differs": lambda: ["net:[4026532001]", "net:[4026531840]"],
    }[name]()


def honest(expected: dict, unit: str, observed: bool = True) -> dict[str, Any]:
    """The literal report a passing unit writes."""
    identity = honest_identity(expected, unit)
    records = []
    for cell, sub in declared(expected, unit):
        if sub == expected["skip"]:
            facts: dict[str, Any] = {"skip": "U0 has neither duckdb nor pyarrow"}
        elif cell == "C12" and not observed:
            facts = {"namespace": "NOT_OBSERVED", "reason": "unshare refused"}
        else:
            want = expected["cells"][cell][sub]
            facts = {
                key: _satisfying(key, value, unit, identity)
                for key, value in want.items()
            }
        records.append({"unit": unit, "cell": cell, "sub": sub, "facts": facts})
    return {"unit": unit, "identity": identity, "records": records}


def _facts(report: dict, cell: str, sub: str) -> dict:
    return next(
        r["facts"] for r in report["records"] if (r["cell"], r["sub"]) == (cell, sub)
    )


def _set(cell: str, sub: str, key: str, value: Any) -> Any:
    def change(report: dict) -> None:
        _facts(report, cell, sub)[key] = value

    return change


def _edit(cell: str, sub: str, key: str, edit: Any) -> Any:
    def change(report: dict) -> None:
        facts = _facts(report, cell, sub)
        facts[key] = edit(copy.deepcopy(facts[key]))

    return change


def _replaced(values: list, index: int, value: Any) -> list:
    values[index] = value
    return values


def _raised(**fields: Any) -> Any:
    return lambda raised: {**raised, **fields}


def _id(report: dict, *path: str, value: Any) -> None:
    target = report["identity"]
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value


def _drop(cell: str, sub: str) -> Any:
    def change(report: dict) -> None:
        report["records"] = [
            r for r in report["records"] if (r["cell"], r["sub"]) != (cell, sub)
        ]

    return change


def _note(hexed: str) -> Any:
    return ["Text", hexed]


NUL_B = "a\0b".encode().hex()


def _nul(rows: list, replacement: Any) -> list:
    return [[row[0], replacement] if row[1] == _note(NUL_B) else row for row in rows]


def _shapes() -> list[tuple[str, str, Any, Any]]:
    """(name, unit, change, the verdict it must get: a law number, "VOID" or
    "DEGRADED"). Section 6's list, and C10 (ii)'s detail."""
    empty_c08 = "== -1 forward"
    full_c08 = "== -9223372036854775808 forward"
    zero = ["Float", "0000000000000000"]
    shapes: list[tuple[str, str, Any, Any]] = [
        ("an omitted sub-case", "U1", _drop("C07", "P"), 1),
        (
            "an omitted cell",
            "U1",
            lambda r: r.update(records=[x for x in r["records"] if x["cell"] != "C16"]),
            1,
        ),
        (
            "a doubled record",
            "U1",
            lambda r: r["records"].append(copy.deepcopy(r["records"][0])),
            1,
        ),
        (
            "a foreign cell",
            "U1",
            lambda r: r["records"].append(
                {"unit": "U1", "cell": "C99", "sub": "", "facts": {}}
            ),
            1,
        ),
        (
            "a foreign sub-case",
            "U1",
            lambda r: r["records"].append(
                {"unit": "U1", "cell": "C07", "sub": "Q!=", "facts": {}}
            ),
            1,
        ),
        ("a relabeled unit", "U1", lambda r: r["records"][3].update(unit="U2"), 1),
        (
            "a relabeled sub-case",
            "U1",
            lambda r: next(x for x in r["records"] if x["cell"] == "C07").update(
                sub="Q=="
            ),
            1,
        ),
        (
            "another code",
            "U1",
            _edit("C04", "", "raised", _raised(code="PIE-R2006")),
            3,
        ),
        (
            "another detail",
            "U1",
            _edit("C04", "", "raised", _raised(detail="DUCKDB_SESSION_CONTEXT")),
            3,
        ),
        (
            "another phase",
            "U1",
            _edit("C11", "L9a", "raised", _raised(phase="query")),
            3,
        ),
        (
            "a phase on a cancellation",
            "U1",
            _edit("C11", "L4", "raised", _raised(phase="query")),
            3,
        ),
        (
            "UNKNOWN in L7",
            "U1",
            _edit("C11", "L7", "O", lambda o: _replaced(o, 1, "UNKNOWN")),
            3,
        ),
        (
            "UNKNOWN in L8",
            "U1",
            _edit("C11", "L8", "O", lambda o: _replaced(o, 1, "UNKNOWN")),
            3,
        ),
        (
            "COMMIT_ACK in L5",
            "U1",
            _edit("C11", "L5", "O", lambda o: _replaced(o, 1, "COMMIT_ACK")),
            3,
        ),
        (
            "COMMIT_ACK in L6",
            "U1",
            _edit("C11", "L6", "O", lambda o: _replaced(o, 1, "COMMIT_ACK")),
            3,
        ),
        (
            "a None detail in L7",
            "U1",
            _edit("C11", "L7", "raised", _raised(detail=None)),
            3,
        ),
        (
            "another cause in L7",
            "U1",
            _edit("C11", "L7", "raised", _raised(cause="InterruptException")),
            3,
        ),
        (
            "a detail in C10 (ii)",
            "U1",
            _edit("C10", "ii", "raised", _raised(detail="DUCKDB_RESULT_CHECK")),
            3,
        ),
        (
            "another cause in C10 (ii)",
            "U1",
            _edit("C10", "ii", "raised", _raised(cause="InterruptException")),
            3,
        ),
        (
            "a sqlstate",
            "U1",
            _edit("C11", "L11a", "raised", _raised(sqlstate="22003")),
            3,
        ),
        (
            "C01 as PIE-R2001",
            "U1",
            _edit("C01", "", "raised", _raised(code="PIE-R2001")),
            3,
        ),
        (
            "C01 as PIE-R2001 in U0",
            "U0",
            _edit("C01", "", "raised", _raised(code="PIE-R2001")),
            3,
        ),
        (
            "an empty C08 result with batches 1",
            "U1",
            _edit("C08", empty_c08, "O", lambda o: _replaced(o, 7, 1)),
            3,
        ),
        (
            "a non-empty C08 result with batches 0",
            "U1",
            _edit("C08", full_c08, "O", lambda o: _replaced(o, 7, 0)),
            3,
        ),
        (
            "a batch schema for an empty result",
            "U1",
            _edit(
                "C08", empty_c08, "batch_schemas", lambda s: [["id", "int64", False]]
            ),
            4,
        ),
        (
            "-0.0 as 0.0",
            "U1",
            _edit("C07", "Q==", "rows", lambda rows: [[rows[0][0], zero]]),
            4,
        ),
        ("a dropped row", "U1", _edit("C07", "P", "rows", lambda rows: rows[1:]), 4),
        (
            "a doubled row",
            "U1",
            _edit("C07", "P", "rows", lambda rows: rows + rows[:1]),
            4,
        ),
        ("a C13 row once", "U1", _edit("C13", "", "rows", lambda rows: rows[1:]), 4),
        ("permuted labels", "U1", _edit("C07", "P", "schema", lambda s: s[::-1]), 4),
        (
            "an Int as a Float",
            "U1",
            _edit(
                "C07",
                "P",
                "rows",
                lambda rows: [[["Float", "3ff0000000000000"], *rows[0][1:]], *rows[1:]],
            ),
            4,
        ),
        (
            "NULL as an empty Text",
            "U1",
            _edit(
                "C07",
                "P",
                "rows",
                lambda rows: [
                    [r[0], _note("") if r[1] is None else r[1]] for r in rows
                ],
            ),
            4,
        ),
        (
            "a NUL value cut at its first NUL",
            "U1",
            _edit("C14", "a", "rows", lambda rows: _nul(rows, _note("61"))),
            4,
        ),
        (
            "a NUL dropped",
            "U1",
            _edit("C14", "a", "rows", lambda rows: _nul(rows, _note("6162"))),
            4,
        ),
        (
            "a NUL cut in the capture",
            "U1",
            _edit(
                "C14",
                "c",
                "capture_c2",
                lambda c2: [_note("61") if v == _note(NUL_B) else v for v in c2],
            ),
            4,
        ),
        (
            "a NUL refused with PIE-R1002",
            "U1",
            _set(
                "C14",
                "a",
                "raised",
                {
                    "class": "RequestRejected",
                    "code": "PIE-R1002",
                    "detail": "DUCKDB_ARROW_SCHEMA",
                },
            ),
            3,
        ),
        (
            "a C02a pair out of order",
            "U1",
            _edit("C02a", "", "seen", lambda s: [s[1], s[0], *s[2:]]),
            5,
        ),
        ("a C02a pair missing", "U1", _edit("C02a", "", "seen", lambda s: s[:-1]), 5),
        ("a C02a module loaded", "U0", _set("C02a", "", "loaded", ["pyarrow"]), 5),
        (
            "a C02a pietto under the tree in U2",
            "U2",
            _edit(
                "C02a",
                "",
                "paths",
                lambda p: {**p, "pietto": f"{p['tree']}/src/pietto/__init__.py"},
            ),
            5,
        ),
        (
            "a C02a pietto under the tree in U3",
            "U3",
            _edit(
                "C02a",
                "",
                "paths",
                lambda p: {**p, "pietto": f"{p['tree']}/src/pietto/__init__.py"},
            ),
            5,
        ),
        (
            "a C02a path not starting with argv1",
            "U1",
            _edit("C02a", "", "paths", lambda p: {**p, "path": p["path"][1:]}),
            5,
        ),
        ("a C02a exit status", "U1", _set("C02a", "", "rc", 1), 5),
        ("a skip counted as a pass", "U1", _set("C09", "", "skip", "no engine"), 6),
        (
            "a U0 cell skipped",
            "U0",
            lambda r: next(x for x in r["records"] if x["cell"] == "C01").update(
                sub="*", facts={"skip": "x"}
            ),
            6,
        ),
        ("a U0 skip line missing", "U0", _drop("C07", "*"), 1),
        (
            "a U0 skip line per sub-case",
            "U0",
            lambda r: r["records"].append(
                {"unit": "U0", "cell": "C07", "sub": "P", "facts": {"skip": "x"}}
            ),
            1,
        ),
        (
            "a timer that never fired",
            "U1",
            _edit("C11", "L6", "O", lambda o: _replaced(o, 6, False)),
            3,
        ),
        ("an L6 elapsed time below 0.5 s", "U1", _set("C11", "L6", "elapsed", 0.3), 5),
        (
            "an L6 cancel never sent",
            "U1",
            _edit("C11", "L6", "O", lambda o: _replaced(o, 4, False)),
            3,
        ),
        ("an L6 timer still alive", "U1", _set("C11", "L6", "timer_alive", True), 5),
        (
            "an L6 timer interval above the deadline",
            "U1",
            _set("C11", "L6", "timer_interval", 0.75),
            5,
        ),
        (
            "a running cancel with cancel_sent false",
            "U1",
            _edit("C11", "L5", "O", lambda o: _replaced(o, 4, False)),
            3,
        ),
        ("an L5 resend thread alive", "U1", _set("C11", "L5", "resend_alive", True), 5),
        (
            "an L5 call log without an interrupt",
            "U1",
            _set(
                "C11",
                "L5",
                "calls",
                [
                    ["connect", ":memory:"],
                    ["register", "pietto_arrow_0"],
                    ["unregister", "pietto_arrow_0"],
                    ["close"],
                ],
            ),
            5,
        ),
        ("a tripped watchdog", "U1", _set("C11", "L5", "tripped", True), 5),
        (
            "a CALLS with an extra step",
            "U1",
            _edit(
                "C04",
                "",
                "calls",
                lambda c: [c[0], ["unregister", "pietto_arrow_0"], c[1]],
            ),
            5,
        ),
        (
            "a CALLS with a missing step",
            "U1",
            _edit("C10", "i", "calls", lambda c: c[:-1]),
            5,
        ),
        (
            "a session in C06",
            "U1",
            _set("C06", "id:int32", "calls", [["connect", ":memory:"], ["close"]]),
            5,
        ),
        (
            "a recorded hook error",
            "U1",
            _set("C10", "i", "hook_errors", [["register", "CatalogException"]]),
            5,
        ),
        (
            "a fifth extension",
            "U1",
            _edit("C10", "i", "E", lambda e: e + ["httpfs"]),
            5,
        ),
        ("E in another order", "U1", _edit("C10", "i", "E", lambda e: e[::-1]), 5),
        (
            "a K row more at unregister",
            "U1",
            _edit(
                "C10",
                "i",
                "K",
                lambda k: {
                    **k,
                    "unregister": [
                        k["unregister"][0]
                        + [["system", "main", "x", "scalar", "[]", "BIGINT"]],
                        *k["unregister"][1:],
                    ],
                },
            ),
            5,
        ),
        (
            "a K point missing",
            "U1",
            _edit(
                "C10",
                "i",
                "K",
                lambda k: {"prelock": k["prelock"], "register": k["register"]},
            ),
            5,
        ),
        (
            "a read-back row that differs",
            "U1",
            _edit(
                "C10",
                "i",
                "settings",
                lambda s: [
                    ["threads", "2"] if row[0] == "threads" else row for row in s
                ],
            ),
            5,
        ),
        ("a loaded shadow", "U1", _set("C03", "c", "modules", ["_duckdb"]), 5),
        ("a shadow that ran", "U1", _set("C03", "c", "marker", True), 5),
        (
            "duckdb loaded by a refusal",
            "U1",
            _set("C06", "price:NaN", "modules", ["duckdb"]),
            5,
        ),
        (
            "a file in HOME",
            "U1",
            _edit("C12", "ns", "after", lambda a: {**a, "home": [".duckdb"]}),
            5,
        ),
        (
            "a file in TMPDIR",
            "U1",
            _edit("C12", "ns", "after", lambda a: {**a, "tmp": ["x"]}),
            5,
        ),
        (
            "a file in the working directory",
            "U1",
            _edit("C12", "ns", "after", lambda a: {**a, "cwd": ["x"]}),
            5,
        ),
        (
            "a second interface",
            "U1",
            _set("C12", "ns", "interfaces", ["lo", "eth0"]),
            5,
        ),
        (
            "the host network namespace",
            "U1",
            _set("C12", "ns", "netns", ["net:[1]", "net:[1]"]),
            5,
        ),
        (
            "a namespace cell that differs",
            "U1",
            _edit("C12", "C07/Q==", "rows", lambda rows: [[rows[0][0], zero]]),
            4,
        ),
        (
            "a buffer shared with the caller",
            "U1",
            _set("C09", "", "ranges", {"capture": [[0, 16]], "caller": [[8, 40]]}),
            5,
        ),
        (
            "the caller's change in the delivered rows",
            "U1",
            _edit(
                "C09", "", "rows", lambda rows: [[["Int", "9"], rows[0][1]], rows[1]]
            ),
            4,
        ),
        ("one connection reused", "U1", _set("C16", "", "connections", 1), 5),
        (
            "a job store that admits duckdb_arrow",
            "U0",
            _set("C15", "job_store", "routes", ["postgres_rows", "duckdb_arrow"]),
            5,
        ),
        (
            "a workspace created",
            "U0",
            _set("C15", "save", "exists_after", [True, False]),
            5,
        ),
        (
            "another duckdb version",
            "U1",
            lambda r: _id(r, "duckdb", "version", value="1.4.0"),
            2,
        ),
        (
            "another PyArrow version",
            "U2",
            lambda r: _id(r, "pyarrow", "version", value="25.0.0"),
            2,
        ),
        (
            "another PyArrow tag in U3",
            "U3",
            lambda r: _id(
                r, "pyarrow", "tags", value=["cp313-cp313-manylinux_2_28_x86_64"]
            ),
            2,
        ),
        (
            "a duckdb RECORD that does not verify",
            "U1",
            lambda r: _id(r, "duckdb", "record_bad", value=["duckdb/__init__.py"]),
            2,
        ),
        (
            "a module file outside the unit's prefix",
            "U2",
            lambda r: _id(
                r, "duckdb", "files", "_duckdb", value="/s06/other/_duckdb.abi3.so"
            ),
            2,
        ),
        (
            "a module file not in its RECORD",
            "U1",
            lambda r: _id(r, "pyarrow", "in_record", "pyarrow.lib", value=False),
            2,
        ),
        (
            "another engine profile",
            "U3",
            lambda r: _id(
                r, "duckdb", "pragma_version", value=["v2.0.0", "0000000000"]
            ),
            2,
        ),
        (
            "duckdb in U0",
            "U0",
            lambda r: _id(r, "duckdb", value={"version": "2.0.0"}),
            2,
        ),
        (
            "another interpreter in U3",
            "U3",
            lambda r: _id(r, "python", "version", value="3.13.13"),
            2,
        ),
        (
            "an old glibc",
            "U2",
            lambda r: _id(r, "python", "glibc", value="glibc 2.17"),
            2,
        ),
        (
            "bytecode written",
            "U1",
            lambda r: _id(r, "python", "dont_write_bytecode", value=0),
            2,
        ),
        ("another spec", "U1", lambda r: _id(r, "spec_sha256", value="0" * 64), 2),
        (
            "the tree's pietto in U2",
            "U2",
            lambda r: _id(
                r, "pietto", "file", value="/s06/integration/src/pietto/__init__.py"
            ),
            2,
        ),
        (
            "an installed pietto in U1",
            "U1",
            lambda r: _id(
                r,
                "pietto",
                "file",
                value="/s06/venv-U1/lib/site-packages/pietto/__init__.py",
            ),
            2,
        ),
        (
            "C12 observed in part",
            "U1",
            lambda r: next(
                x for x in r["records"] if x["cell"] == "C12" and x["sub"] == "ns"
            ).update(facts={"namespace": "NOT_OBSERVED"}),
            7,
        ),
        (
            "C12 NOT_OBSERVED reported as ACCEPTED",
            "U1",
            lambda r: r.update(honest_unobserved=True),
            "DEGRADED",
        ),
        ("an L6 setup above 0.5 s", "U1", _set("C11", "L6", "setup", 0.7), "VOID"),
        ("an L6 setup not measured", "U1", _set("C11", "L6", "setup", None), "VOID"),
        (
            "a fixture size miss",
            "U1",
            _set("C05", "c", "fixture_miss", {"nbytes": 16777215}),
            "VOID",
        ),
        # v5: the shapes of the eleven checker mutants that v4's self-test
        # let survive (freeze-record entry 2, point 2).
        ("a judged field missing", "U1", lambda r: _facts(r, "C07", "P").pop("O"), 3),
        (
            "O's batches as true",
            "U1",
            _edit("C07", "P", "O", lambda o: _replaced(o, 7, True)),
            3,
        ),
        (
            "an extra directory in C12's listing",
            "U1",
            _edit("C12", "ns", "after", lambda a: {**a, "extra": []}),
            5,
        ),
        (
            "a C02a argv1 without the probe site in U1",
            "U1",
            _edit("C02a", "", "paths", lambda p: {**p, "argv1": p["argv1"][:1]}),
            5,
        ),
        (
            "a C02a pietto inside its tree in U2",
            "U2",
            _edit("C02a", "", "paths", lambda p: {**p, "tree": "/s06"}),
            5,
        ),
        (
            "a C02a pietto inside its lane in U3",
            "U3",
            _edit("C02a", "", "paths", lambda p: {**p, "lane": "/s06"}),
            5,
        ),
        (
            "PYTHONDONTWRITEBYTECODE unset",
            "U1",
            lambda r: _id(r, "env", "PYTHONDONTWRITEBYTECODE", value=None),
            2,
        ),
        (
            "another duckdb RECORD count",
            "U2",
            lambda r: _id(r, "duckdb", "record_hashed", value=67),
            2,
        ),
        (
            "another duckdb platform",
            "U3",
            lambda r: _id(r, "duckdb", "platform", value="linux_arm64"),
            2,
        ),
        (
            "an extra duckdb module file",
            "U1",
            lambda r: (
                _id(r, "duckdb", "files", "adbc_driver_duckdb", value=f"{SITE}/a.py"),
                _id(r, "duckdb", "in_record", "adbc_driver_duckdb", value=True),
            ),
            2,
        ),
        (
            "a U2 root above its prefix",
            "U2",
            lambda r: _id(r, "unit_root", value="/s06"),
            2,
        ),
        (
            "a U0 tree that is not the lane",
            "U0",
            lambda r: _id(r, "pietto", "lane", value="/s06/other"),
            2,
        ),
    ]
    return shapes


def self_test(expected: dict) -> list[tuple[str, dict[str, Any]]]:
    """Each unit's honest report is ACCEPTED; each fabricated shape gets the
    verdict it must get and never ACCEPTED. Raises AssertionError otherwise."""
    results = []
    for unit in expected["units"]:
        verdict = check(honest(expected, unit), expected)
        results.append((f"honest {unit}", verdict))
        assert verdict == {"unit": unit, "verdict": "ACCEPTED"}, (unit, verdict)
    for name, unit, change, wanted in _shapes():
        report = honest(expected, unit)
        change(report)
        if report.pop("honest_unobserved", False):
            report = honest(expected, unit, observed=False)
        verdict = check(report, expected)
        results.append((name, verdict))
        if wanted in ("VOID", "DEGRADED"):
            assert verdict["verdict"] == wanted, (name, verdict)
        else:
            assert verdict["verdict"] == "REFUSED" and verdict["law"] == wanted, (
                name,
                verdict,
            )
    return results


def _report(evidence: Path) -> dict[str, Any]:
    records = []
    path = evidence / "facts.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        try:
            records.append(json.loads(line))
        except ValueError:
            records.append(None)
    identity_path = evidence / "identity.json"
    return {
        "unit": evidence.name,
        "identity": json.loads(identity_path.read_text(encoding="utf-8"))
        if identity_path.exists()
        else None,
        "records": records,
    }


def main(argv: list[str]) -> int:
    """`selftest EXPECTED`, `identity EVIDENCE` (law 2 only) or `check
    EVIDENCE` (writes EVIDENCE/verdict.json)."""
    command, target = argv[0], Path(argv[1])
    if command == "selftest":
        expected = json.loads(target.read_text(encoding="utf-8"))
        for name, verdict in self_test(expected):
            print(json.dumps([name, verdict]))
        return 0
    expected = json.loads((target / "expected.json").read_text(encoding="utf-8"))
    report = _report(target)
    if command == "identity":
        problem = identity_problem(report["identity"], expected, report["unit"])
        print(json.dumps({"unit": report["unit"], "identity": problem or "MEETS"}))
        return 0 if problem is None else 1
    verdict = check(report, expected)
    (target / "verdict.json").write_text(
        json.dumps(verdict, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(verdict))
    return 0 if verdict["verdict"] in ("ACCEPTED", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
