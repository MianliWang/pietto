"""Old-flat regression check: public CLI outputs of two materialized trees.

python tests/_pietto_harness_flat_regression.py --baseline DIR --candidate DIR \\
  --baseline-id TREE --candidate-id TREE --scratch DIR --report FILE \\
  [--approve-message CODE ...] [--allow FILE] [--limit N]

The corpus is discovered in the baseline tree by one child process: every
``examples/**/*.pietto`` and ``tests/fixtures/**/*.pietto`` file, every
```` ```pietto ```` block of ``README.md``, ``docs/language.md`` and
``docs/style.md``, the ``schema_version = 2`` project-mode fixtures of the
baseline's own ``_pietto_sql_emission.fixture()`` over its ``VARIANTS`` and
both targets (``check --project``, ``emit-sql --project``), and the
``schema_version = 4`` Project Explain scenarios the baseline's
``_pietto_project_explain_differential_probe._projects()`` writes (``explain
--project``, JSON and text; explain refuses every other schema version). Each
tree then runs the same public CLI argv through ``pietto.cli.main`` in one
child process with the same cwd, relative paths and environment; the
parent compares exit codes and stdout/stderr bytes, and the frozen files
byte for byte. Nothing here reads Git, uses the network or writes a tree.

Classes: IDENTICAL; APPROVED_MESSAGE_DELTA (only the message/suggestion text
of an ``--approve-message`` code differs, in JSON or in that code's text
lines); DRIFT (anything else, SQL bytes included); ALLOWED (a DRIFT named by
an ``--allow`` entry); ADDED (a frozen file only the candidate has); STALE
(an allow entry that matches no actual difference). Exit 0 only without DRIFT
and STALE.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

FORMAT = "pietto.flat-regression-report.v1"
DOCS = ("README.md", "docs/language.md", "docs/style.md")
SINGLE_ROOTS = ("examples", "tests/fixtures")
KINDS = ("docs", "files", "projects", "explain")
FROZEN = (
    "tests/fixtures/**/*",
    "examples/**/*",
    "tests/*.json",
    "tests/_pietto_*_vectors.py",
)
ENV = {
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
    "LC_ALL": "C.UTF-8",
}
CLASSES = (
    "IDENTICAL",
    "APPROVED_MESSAGE_DELTA",
    "DRIFT",
    "ALLOWED",
    "ADDED",
    "STALE",
)
_FENCE = re.compile(r"^```pietto(?:\s.*)?$")
_RESULT = re.compile(r"^(table|query) result\b", re.MULTILINE)
_TEXT_DIAGNOSTIC = re.compile(r"^(.*:\d+:\d+ (PIE-[A-Z]+\d+) [a-z]+): ")


# Corpus discovery (runs in a child bound to the baseline tree) ---------------


def _doc_blocks(text: str) -> list[str]:
    blocks, current = [], None
    for line in text.splitlines(keepends=True):
        if current is None:
            if _FENCE.match(line.rstrip("\n")):
                current = []
        elif line.rstrip("\n") == "```":
            blocks.append("".join(current))
            current = None
        else:
            current.append(line)
    return blocks


def extract(tree: Path) -> dict[str, Any]:
    import _pietto_project_explain_differential_probe as explain_probe
    import _pietto_sql_emission as emission

    for origin in (emission.__file__, explain_probe.__file__):
        if not Path(origin).resolve().is_relative_to(tree / "tests"):
            raise SystemExit("corpus fixtures do not come from the baseline tree")
    files = []
    for root in SINGLE_ROOTS:
        for path in sorted((tree / root).rglob("*.pietto")):
            relative = path.relative_to(tree).as_posix()
            data = base64.b64encode(path.read_bytes()).decode()
            files.append({"id": f"file:{relative}", "path": relative, "data": data})
    docs = []
    for name in DOCS:
        text = (tree / name).read_text(encoding="utf-8")
        for index, block in enumerate(_doc_blocks(text), start=1):
            path = f"docs/{name.replace('/', '_')}/{index:03d}.pietto"
            docs.append({"id": f"doc:{name}#{index}", "path": path, "text": block})
    projects = []
    for case, variants in emission.VARIANTS.items():
        for variant in variants:
            for target in ("postgres", "mysql"):
                item = emission.fixture(target, case, variant)
                modules = emission.source_files(item["source"])
                found = [
                    (name, match.group(1))
                    for name, text in sorted(modules.items())
                    for match in _RESULT.finditer(text)
                ]
                module, kind = found[0] if len(found) == 1 else ("main.pietto", "query")
                projects.append(
                    {
                        "id": f"project:{case}/{variant}/{target}",
                        "path": f"projects/{case}/{variant}/{target}",
                        "modules": dict(sorted(modules.items())),
                        "config": emission.CONFIG,
                        "contract": item["contract"],
                        "policy": "bind-safe"
                        if item["policy"] == "bind_safe_literals"
                        else "preserve",
                        "target": target,
                        "module": module,
                        "kind": kind,
                    }
                )
    workspace = Path.cwd() / "explain-source"
    workspace.mkdir()
    explain = []
    for name, root in explain_probe._projects(workspace).items():
        found = (
            sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
        )
        explain.append(
            {
                "id": f"explain:{name}",
                "path": f"explain/{name}",
                "files": {
                    p.relative_to(root).as_posix(): base64.b64encode(
                        p.read_bytes()
                    ).decode()
                    for p in found
                },
            }
        )
    return {"docs": docs, "explain": explain, "files": files, "projects": projects}


def _limited(corpus: dict[str, Any], limit: int | None) -> dict[str, Any]:
    if limit is None:
        return corpus
    order = sorted(
        (index, KINDS.index(kind), item["id"])
        for kind in KINDS
        for index, item in enumerate(corpus[kind])
    )
    keep = {item_id for _, _, item_id in order[:limit]}
    return {kind: [i for i in corpus[kind] if i["id"] in keep] for kind in KINDS}


def commands(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in corpus["files"] + corpus["docs"]:
        path = item["path"]
        for presentation in ("json", "text"):
            result.append(
                {"input": item["id"], "argv": ["check", "--format", presentation, path]}
            )
        for dialect in ("postgres", "mysql"):
            for presentation in ("text", "json"):
                argv = ["emit-sql", "--dialect", dialect, "--format", presentation]
                result.append({"input": item["id"], "argv": [*argv, path]})
    for item in corpus["projects"]:
        root = item["path"]
        argv = ["check", "--project", root, "--format", "json"]
        result.append({"input": item["id"], "argv": argv})
        argv = ["emit-sql", "--project", root, "--module", item["module"]]
        argv += ["--kind", item["kind"], "--name", "result", "--dialect"]
        argv += [item["target"], "--emission-contract", "contract.json"]
        argv += ["--literal-policy", item["policy"], "--format", "json"]
        result.append({"input": item["id"], "argv": argv})
    for item in corpus["explain"]:
        for presentation in ("json", "text"):
            argv = ["explain", "--project", item["path"], "--format", presentation]
            result.append({"input": item["id"], "argv": argv})
    return result


def materialize(corpus: dict[str, Any], work: Path) -> None:
    for item in corpus["files"]:
        target = work / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(item["data"]))
    for item in corpus["docs"]:
        target = work / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item["text"].encode("utf-8"))
    for item in corpus["projects"]:
        root = work / item["path"]
        root.mkdir(parents=True)
        (root / "pietto.toml").write_bytes(item["config"].encode("utf-8"))
        (root / "contract.json").write_bytes(item["contract"].encode("utf-8"))
        for name, text in item["modules"].items():
            if Path(name).name != name or not name.endswith(".pietto"):
                raise ValueError("closed fixture module path required")
            (root / name).write_bytes(text.encode("utf-8"))
    for item in corpus["explain"]:
        for name, data in item["files"].items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("closed explain scenario path required")
            target = work / item["path"] / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(data))


# Tree runs (one child per tree) -------------------------------------------


def _decoded(data: bytes) -> dict[str, str]:
    try:
        return {"text": data.decode("utf-8")}
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(data).decode()}


def run_tree(tree: Path, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import pietto
    from pietto.cli import main

    if not Path(pietto.__file__).resolve().is_relative_to(tree / "src"):
        raise SystemExit("pietto does not come from the tree under test")
    records = []
    for item in plan:
        out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")
        err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")
        saved = sys.stdin
        sys.stdin = io.StringIO("")
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    status: int | str = main(item["argv"])
                except BaseException as error:  # a traceback is itself the record
                    status = f"raised {type(error).__name__}"
        finally:
            sys.stdin = saved
        out.flush()
        err.flush()
        records.append(
            {
                "exit": status,
                "stdout": _decoded(out.buffer.getvalue()),  # type: ignore[attr-defined]
                "stderr": _decoded(err.buffer.getvalue()),  # type: ignore[attr-defined]
            }
        )
    return records


def _child(mode: str, tree: Path, cwd: Path, home: Path, *paths: Path):
    pythonpath = [str(tree / "src")] + (
        [str(tree / "tests")] if mode == "--_extract" else []
    )
    env = {**ENV, "PATH": os.environ.get("PATH", ""), "HOME": str(home)}
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    argv = [sys.executable, "-P", str(Path(__file__).resolve()), mode, str(tree)]
    return subprocess.Popen(
        argv + [str(path) for path in paths],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def _wait(*children) -> None:
    codes = [child.wait() for child in children]
    if any(codes):
        raise SystemExit(f"tree child failed: {codes}")


# Comparison ---------------------------------------------------------------


def _text(stream: dict[str, str]) -> str | None:
    return stream.get("text")


def _strip(value: Any, approved: frozenset[str]) -> Any:
    if type(value) is dict:
        drop = value.get("code") in approved
        return {
            key: _strip(item, approved)
            for key, item in value.items()
            if not (drop and key in {"message", "suggestion"})
        }
    if type(value) is list:
        return [_strip(item, approved) for item in value]
    return value


def _lines_approved(base: str, cand: str, approved: frozenset[str]) -> bool:
    left, right = base.split("\n"), cand.split("\n")
    if len(left) != len(right):
        return False
    for a, b in zip(left, right, strict=True):
        if a != b:
            ma, mb = _TEXT_DIAGNOSTIC.match(a), _TEXT_DIAGNOSTIC.match(b)
            if not (
                ma and mb and ma.group(1) == mb.group(1) and ma.group(2) in approved
            ):
                return False
    return True


def _stream_approved(base: dict, cand: dict, approved: frozenset[str]) -> bool:
    if base == cand:
        return True
    left, right = _text(base), _text(cand)
    if left is None or right is None:
        return False
    try:
        a, b = json.loads(left), json.loads(right)
    except ValueError:
        return _lines_approved(left, right, approved)
    return a != b and _strip(a, approved) == _strip(b, approved)


def _sha(stream: dict[str, str]) -> str:
    data = stream.get("text", "").encode() or base64.b64decode(stream.get("base64", ""))
    return hashlib.sha256(data).hexdigest()


def _first_difference(base: dict, cand: dict) -> dict[str, Any]:
    for name in ("stdout", "stderr"):
        left = (_text(base[name]) or "").split("\n")
        right = (_text(cand[name]) or "").split("\n")
        for index in range(max(len(left), len(right))):
            a = left[index] if index < len(left) else None
            b = right[index] if index < len(right) else None
            if a != b:
                return {
                    "stream": name,
                    "line": index + 1,
                    "baseline": None if a is None else a[:300],
                    "candidate": None if b is None else b[:300],
                }
    return {}


def classify(base: dict, cand: dict, approved: frozenset[str]) -> tuple[str, dict]:
    """Compare one command's two records; SQL bytes have no exemption."""
    if base == cand:
        return "IDENTICAL", {}
    detail: dict[str, Any] = {
        "exit": [base["exit"], cand["exit"]],
        "stdout_sha256": [_sha(base["stdout"]), _sha(cand["stdout"])],
        "stderr_sha256": [_sha(base["stderr"]), _sha(cand["stderr"])],
    }
    if (
        approved
        and base["exit"] == cand["exit"]
        and _stream_approved(base["stdout"], cand["stdout"], approved)
        and _stream_approved(base["stderr"], cand["stderr"], approved)
    ):
        return "APPROVED_MESSAGE_DELTA", detail
    return "DRIFT", {**detail, "first_difference": _first_difference(base, cand)}


def frozen_files(tree: Path) -> dict[str, str]:
    found = {}
    for pattern in FROZEN:
        for path in tree.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                found[path.relative_to(tree).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    return dict(sorted(found.items()))


def compare_frozen(base: dict[str, str], cand: dict[str, str]) -> list[dict[str, Any]]:
    records = []
    for path in sorted(set(base) | set(cand)):
        if path not in cand:
            records.append({"class": "DRIFT", "path": path, "detail": "removed"})
        elif path not in base:
            records.append({"class": "ADDED", "path": path, "detail": "added"})
        elif base[path] != cand[path]:
            records.append(
                {"class": "DRIFT", "path": path, "detail": [base[path], cand[path]]}
            )
        else:
            records.append({"class": "IDENTICAL", "path": path})
    return records


def apply_allow(
    records: list[dict[str, Any]], allow: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Mark allowed DRIFTs; every entry must match an actual difference."""
    stale = []
    for entry in allow:
        if type(entry.get("decision")) is not str or not entry["decision"]:
            raise SystemExit("every allow entry needs a decision reference")
        used = False
        for record in records:
            same = (
                record.get("path") == entry["path"]
                if "path" in entry
                else record.get("input") == entry.get("input")
                and record.get("argv") == entry.get("argv")
            )
            if same and record["class"] != "IDENTICAL":
                used = True
                if record["class"] == "DRIFT":
                    record["class"] = "ALLOWED"
                    record["decision"] = entry["decision"]
        if not used:
            stale.append({"class": "STALE", "allow": entry})
    return stale


def compare(
    plan: list[dict[str, Any]],
    base: list[dict[str, Any]],
    cand: list[dict[str, Any]],
    approved: frozenset[str],
) -> list[dict[str, Any]]:
    records = []
    for item, left, right in zip(plan, base, cand, strict=True):
        verdict, detail = classify(left, right, approved)
        record = {"class": verdict, "input": item["input"], "argv": item["argv"]}
        if detail:
            record["detail"] = detail
        records.append(record)
    return records


def report(
    arguments: argparse.Namespace,
    corpus: dict[str, Any],
    records: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    frozen_count: int,
) -> dict[str, Any]:
    everything = records + stale
    counts = {name: sum(r["class"] == name for r in everything) for name in CLASSES}
    return {
        "approved_codes": sorted(arguments.approve_message),
        "baseline": arguments.baseline_id,
        "candidate": arguments.candidate_id,
        "commands": sum("argv" in r for r in records),
        "corpus_sha256": hashlib.sha256(
            json.dumps(corpus, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "counts": counts,
        "differences": [r for r in everything if r["class"] != "IDENTICAL"],
        "format": FORMAT,
        "frozen_files": frozen_count,
        "inputs": {kind: len(corpus[kind]) for kind in KINDS},
        "limit": arguments.limit,
        "ok": counts["DRIFT"] == 0 and counts["STALE"] == 0,
    }


def run(arguments: argparse.Namespace) -> int:
    baseline = arguments.baseline.resolve()
    candidate = arguments.candidate.resolve()
    scratch = arguments.scratch.resolve()
    for tree in (baseline, candidate):
        if not (tree / "src" / "pietto" / "cli.py").is_file():
            raise SystemExit(f"not a Pietto tree: {tree}")
        for path in (scratch, arguments.report.resolve()):
            if path.is_relative_to(tree):
                raise SystemExit("scratch and report must be outside both trees")
    scratch.mkdir(parents=True, exist_ok=False)
    work, home = scratch / "work", scratch / "home"
    work.mkdir()
    home.mkdir()
    corpus_path = scratch / "corpus.json"
    _wait(_child("--_extract", baseline, scratch, home, corpus_path))
    corpus = _limited(json.loads(corpus_path.read_text()), arguments.limit)
    materialize(corpus, work)
    plan = commands(corpus)
    plan_path = scratch / "plan.json"
    plan_path.write_text(json.dumps(plan))
    outputs = {
        "baseline": scratch / "baseline.json",
        "candidate": scratch / "candidate.json",
    }
    _wait(
        _child("--_run", baseline, work, home, plan_path, outputs["baseline"]),
        _child("--_run", candidate, work, home, plan_path, outputs["candidate"]),
    )
    approved = frozenset(arguments.approve_message)
    records = compare(
        plan,
        json.loads(outputs["baseline"].read_text()),
        json.loads(outputs["candidate"].read_text()),
        approved,
    )
    base_frozen, cand_frozen = frozen_files(baseline), frozen_files(candidate)
    records += compare_frozen(base_frozen, cand_frozen)
    allow = [] if arguments.allow is None else json.loads(arguments.allow.read_text())
    stale = apply_allow(records, allow)
    document = report(arguments, corpus, records, stale, len(base_frozen | cand_frozen))
    arguments.report.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    )
    return 0 if document["ok"] else 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["--_extract"]:
        Path(argv[2]).write_text(json.dumps(extract(Path(argv[1])), ensure_ascii=False))
        return 0
    if argv[:1] == ["--_run"]:
        plan = json.loads(Path(argv[2]).read_text())
        records = run_tree(Path(argv[1]), plan)
        Path(argv[3]).write_text(json.dumps(records, ensure_ascii=False))
        return 0
    parser = argparse.ArgumentParser(
        description="Old-flat public CLI regression check."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--approve-message", action="append", default=[])
    parser.add_argument("--allow", type=Path)
    parser.add_argument("--limit", type=int)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
