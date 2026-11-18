"""Generated opened forms against the independent oracle, through public entries.

Each registered case (tests/_pietto_harness_generated_forms.py) runs through
single-file ``check``, ``explain`` and ``emit-sql`` for PostgreSQL and MySQL,
and in an explicit-module project through ``compile_sql``,
``explain --project``, ``compile_query`` and ``export_bundle`` for PostgreSQL,
and also for MySQL in the narrow profile. Every route must accept the case,
except that single-file ``explain`` describes no JOIN relation (PIE-I1000),
and each route that reports result columns must report the oracle's names,
types and nullability. A failure names the seed, the profile and the module,
which reproduce it on every supported Python.
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path

import _pietto_harness_generated_forms as forms
import pytest

from pietto import cli
from pietto.compiler import compile_sql
from pietto.execution import compile_query, export_bundle


def _cli(*argv: str) -> tuple[int, dict]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(list(argv))
    return code, json.loads(out.getvalue())


def _write(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return root


def _emitted(document: dict) -> list:
    nullable = {True: forms.NULLABLE, False: forms.NON_NULL, "unknown": forms.UNKNOWN}
    return [
        [c["label"], c["logical_type"]["name"], nullable[c["nullable"]]]
        for c in document["columns"]
    ]


def observe(case: forms.Case, root: Path) -> list[str]:
    """Every disagreement of the public routes with the oracle for ``case``."""
    expected = [list(column) for column in forms.expected_columns(case)]
    problems = []

    def compare(route: str, columns: list) -> None:
        if columns != expected:
            problems.append(f"{route}: columns {columns} != oracle {expected}")

    for target in ("postgres", "mysql"):
        path = root / f"{target}.pietto"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(forms.module_text(case, target), encoding="utf-8")
        code, report = _cli("check", str(path), "--format", "json")
        errors = [d for d in report["diagnostics"] if d["severity"] == "error"]
        if code != 0 or errors:
            problems.append(f"check {target}: exit {code}, {errors}")
        code, report = _cli("explain", str(path), "--format", "json")
        relations = [
            r
            for r in report.get("metadata", {}).get("relations", ())
            if r["name"] == "q"
        ]
        # Single-file explain describes no JOIN relation (PIE-I1000).
        if case.form == "join":
            errors = [
                d["code"] for d in report["diagnostics"] if d["severity"] == "error"
            ]
            if code != 1 or errors != ["PIE-I1000"]:
                problems.append(
                    f"explain {target}: exit {code}, {report['diagnostics']}"
                )
        elif code != 0 or len(relations) != 1:
            problems.append(f"explain {target}: exit {code}, {report['diagnostics']}")
        else:
            fields = relations[0]["output_schema"]["fields"]
            compare(
                f"explain {target}",
                [[f["name"], f["type"]["name"], f["nullability"]] for f in fields],
            )
        code, report = _cli(
            "emit-sql", str(path), "--dialect", target, "--format", "json"
        )
        if code != 0:
            problems.append(f"emit-sql {target}: exit {code}, {report['diagnostics']}")

    targets = ("postgres", "mysql") if case.profile == "narrow" else ("postgres",)
    for target in targets:
        project = _write(root / f"project-{target}", forms.project_files(case, target))
        arguments = {
            "module": "main.pietto",
            "kind": "query",
            "name": "q",
            "dialect": target,
            "emission_contract": "contract.json",
        }
        emission = compile_sql(project, **arguments)
        document = json.loads(emission.document)
        if emission.status != "VERIFIED":
            reasons = (
                document["diagnostics"] + document["cli_errors"] + document["blockers"]
            )
            problems.append(f"compile_sql {target}: {emission.status}, {reasons}")
            continue
        compare(f"compile_sql {target}", _emitted(document))
        query = compile_query(project, **arguments)
        # The query's emission carries only its contract, with the same SQL.
        emitted = json.loads(query.emission or b"null")
        if emitted["sql"] != document["sql"]:
            problems.append(f"compile_query {target}: SQL differs from compile_sql")
        compare(f"compile_query {target}", _emitted(emitted))
        if not export_bundle(query).payload:
            problems.append(f"export_bundle {target}: empty payload")
        code, report = _cli("explain", "--project", str(project), "--format", "json")
        relation = [r for r in report.get("relations", ()) if r["name"] == "q"]
        if code != 0 or len(relation) != 1:
            problems.append(
                f"explain --project {target}: exit {code}, {report['diagnostics']}"
            )
        else:
            columns = relation[0]["columns"]
            compare(
                f"explain --project {target}",
                [[c["name"], c["type"]["name"], c["nullability"]] for c in columns],
            )
    return problems


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", forms.SEEDS)
def test_generated_case_matches_the_oracle_on_every_route(
    seed: int, profile: str, tmp_path: Path
) -> None:
    case = forms.generate(seed, profile)
    problems = observe(case, tmp_path)
    assert not problems, (
        f"seed {seed}, profile {profile}\n"
        + forms.module_text(case, "postgres")
        + "\n".join(problems)
    )


def test_registered_corpus_is_the_same_on_every_python() -> None:
    digest = hashlib.sha256()
    for seed in forms.SEEDS:
        for profile in forms.PROFILES:
            digest.update(repr(forms.generate(seed, profile)).encode() + b"\n")
    assert digest.hexdigest() == forms.CORPUS_SHA256


def test_oracle_restates_the_documents_without_pietto() -> None:
    tree = ast.parse(Path(forms.__file__).read_text(encoding="utf-8"))
    imported = {
        name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for name in (
            [a.name for a in node.names]
            if isinstance(node, ast.Import)
            else [node.module or ""]
        )
    }
    assert imported == {"__future__", "dataclasses", "json", "random", "typing"}
    on = (
        "bool",
        "and",
        ("cmp", "==", ("field", "t.f0"), ("field", "r.f0")),
        ("bool", "or", ("isnone", ("field", "r.f1"), True), ("lit", "Bool", "True")),
    )
    case = forms.Case(
        seed=-1,
        profile="broad",
        form="join",
        fields=(("id", "Int", False), ("f0", "Int", True), ("f1", "Text", True)),
        join=("inner", on),
        lets=(),
        where=("isnone", ("field", "t.f1"), True),
        keys=(),
        items=(
            ("a", ("field", "t.f0")),  # an INNER JOIN's equality proves its fields
            ("b", ("field", "r.f1")),  # `or` proves nothing
            ("c", ("field", "t.f1")),  # WHERE does not narrow (Nullability v1)
            ("d", ("arith", "+", ("field", "t.id"), ("lit", "Int", "1"))),
            ("e", ("call", "coalesce", ("field", "r.f1"), ("lit", "Text", '"a"'))),
            ("f", ("call", "lower", ("field", "r.f1"))),
            ("g", ("neg", ("field", "r.f0"))),
            ("h", ("cmp", "<", ("field", "t.id"), ("lit", "Int", "1"))),
        ),
        order=(("t.id", False),),
        limit=None,
    )
    assert forms.expected_columns(case) == (
        ("a", "Int", "non_null"),
        ("b", "Text", "nullable"),
        ("c", "Text", "nullable"),
        ("d", "Int", "unknown"),
        ("e", "Text", "non_null"),
        ("f", "Text", "nullable"),
        ("g", "Int", "non_null"),
        ("h", "Bool", "unknown"),
    )
    left = replace(case, join=("left", on))
    assert [state for *_, state in forms.expected_columns(left)][:3] == ["nullable"] * 3
    assert forms.typed(case, ("agg", "avg", ("field", "f0"))) == ("Float", "nullable")
    assert forms.typed(case, ("agg", "count", ("field", "f0"))) == ("Int", "non_null")


def _census(case: forms.Case) -> set[tuple]:
    """What a case reaches: its form, JOIN kind, nodes and oracle premises."""
    reached: set[tuple] = {("form", case.profile, case.form)}
    if case.join is not None:
        reached.add(("join", case.join[0]))
    tested = set()
    conjuncts = [case.where] if case.where else []
    while conjuncts:
        node = conjuncts.pop()
        if node[:2] == ("bool", "and"):
            conjuncts += node[2:]
        elif node[0] == "isnone" and node[2]:
            tested.add(node[1])

    def walk(node: tuple) -> None:
        reached.add(("node", node[0], node[1] if node[0] in ("call", "agg") else ""))
        for part in node[1:]:
            if isinstance(part, tuple):
                walk(part)

    for (_, expression), (_, _, state) in zip(
        case.items, forms.expected_columns(case), strict=True
    ):
        walk(expression)
        reached.add(("state", state))
        declared = forms.typed(replace(case, join=None), expression)
        if expression in tested and state == forms.NULLABLE:
            reached.add(("premise", "where_does_not_narrow"))
        if case.join is not None and expression[0] == "field" and declared[1] != state:
            reached.add(("premise", f"join_{case.join[0]}_{state}"))
    return reached


def test_registered_corpus_reaches_every_oracle_rule() -> None:
    """Coverage is an observation, not a proof (R13); the registered seeds
    must still reach each form, production and rule of the oracle."""
    reached = set().union(
        *(_census(forms.generate(s, p)) for s in forms.SEEDS for p in forms.PROFILES)
    )
    required = {
        ("form", profile, form) for profile in forms.PROFILES for form in forms.FORMS
    }
    required |= {("join", kind) for kind in ("inner", "left", "right", "full", "cross")}
    tags = ("field", "let", "lit", "neg", "arith", "cmp", "bool", "isnone")
    required |= {("node", tag, "") for tag in tags}
    required |= {
        ("node", "call", name) for name in ("abs", "coalesce", "lower", "upper")
    }
    required |= {
        ("node", "agg", name) for name in ("count", "min", "max", "sum", "avg")
    }
    required |= {
        ("state", state) for state in (forms.NON_NULL, forms.NULLABLE, forms.UNKNOWN)
    }
    required |= {
        ("premise", "where_does_not_narrow"),
        ("premise", "join_inner_non_null"),
    }
    required |= {
        ("premise", f"join_{kind}_nullable") for kind in ("left", "right", "full")
    }
    assert not required - reached, required - reached
