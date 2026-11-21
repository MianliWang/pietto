"""Metamorphic relations of the generated opened forms, through public entries.

Each registered case of tests/_pietto_harness_generated_forms.py and each
rewrite of it by a relation of tests/_pietto_harness_generated_forms_metamorphic.py
run through single-file ``check``, ``explain`` and ``emit-sql`` for
PostgreSQL and MySQL, and in an explicit-module project through
``compile_sql``, ``compile_query`` and ``explain --project`` for PostgreSQL,
and also for MySQL in the narrow profile. Each route's exit or status,
diagnostic codes, result columns and SQL for the rewrite must be what the
relation keeps of the original's, with no oracle. A failure names the seed,
the profile and the relation, which reproduce it.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re

import _pietto_harness_generated_forms as forms
import _pietto_harness_generated_forms_metamorphic as meta
import pytest

from pietto import cli
from pietto.compiler import compile_sql
from pietto.execution import CompileRejected, compile_query


def _cli(*argv: str) -> tuple[int, dict]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(list(argv))
    return code, json.loads(out.getvalue())


def _codes(report: dict, *keys: str) -> tuple[str, ...]:
    return tuple(d.get("code") or "" for key in keys for d in report.get(key, ()))


def _emission(status: str, document: dict) -> tuple:
    columns = [
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in document.get("columns") or ()
    ]
    codes = _codes(document, "diagnostics", "cli_errors", "blockers")
    return status, codes, columns, document.get("sql")


def observe(
    case: forms.Case, text: Callable[[str], str], root: Path
) -> dict[str, tuple]:
    """Each route's (exit or status, codes, columns, SQL) for the module
    ``text(target)`` over ``case``'s sources."""
    seen: dict[str, tuple] = {}
    for target in ("postgres", "mysql"):
        path = root / f"{target}.pietto"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text(target), encoding="utf-8")
        code, report = _cli("check", str(path), "--format", "json")
        seen[f"check {target}"] = (code, _codes(report, "diagnostics"), None, None)
        code, report = _cli("explain", str(path), "--format", "json")
        columns = next(
            (
                [(f["name"], f["type"]["name"], f["nullability"]) for f in fields]
                for r in report.get("metadata", {}).get("relations", ())
                if r["name"] == "q"
                for fields in [r["output_schema"]["fields"]]
            ),
            None,
        )
        seen[f"explain {target}"] = (code, _codes(report, "diagnostics"), columns, None)
        code, report = _cli(
            "emit-sql", str(path), "--dialect", target, "--format", "json"
        )
        sql = next((a["sql"] for a in report["artifacts"] if a["name"] == "q"), None)
        seen[f"emit-sql {target}"] = (code, _codes(report, "diagnostics"), None, sql)

    targets = ("postgres", "mysql") if case.profile == "narrow" else ("postgres",)
    for target in targets:
        project = root / f"project-{target}"
        project.mkdir(parents=True)
        files = forms.project_files(case, target) | {"main.pietto": text(target)}
        for name, content in files.items():
            (project / name).write_text(content, encoding="utf-8")
        arguments = {
            "module": "main.pietto",
            "kind": "query",
            "name": "q",
            "dialect": target,
            "emission_contract": "contract.json",
        }
        emission = compile_sql(project, **arguments)
        seen[f"compile_sql {target}"] = _emission(
            emission.status, json.loads(emission.document)
        )
        try:
            query = compile_query(project, **arguments)
        except CompileRejected as error:
            emitted = _emission(error.status, json.loads(error.emission))
        else:
            emitted = _emission("VERIFIED", json.loads(query.emission or b"{}"))
        seen[f"compile_query {target}"] = emitted
        code, report = _cli("explain", "--project", str(project), "--format", "json")
        columns = next(
            (
                [(c["name"], c["type"]["name"], c["nullability"]) for c in r["columns"]]
                for r in report.get("relations") or ()
                if r["name"] == "q"
            ),
            None,
        )
        seen[f"explain --project {target}"] = (
            code,
            _codes(report, "diagnostics"),
            columns,
            None,
        )
    return seen


def kept(
    seen: dict[str, tuple], relation: str, *, rewritten: bool = False
) -> dict[str, tuple]:
    """What ``relation`` compares of an observation: of the original's, as
    its rewrite must show it, or of the rewrite's own (``rewritten``)."""
    result = {}
    for route, (status, codes, columns, sql) in seen.items():
        if not rewritten and relation == "reverse" and columns is not None:
            columns = columns[::-1]
        if not rewritten and relation == "rename" and sql is not None:
            sql = re.sub(r'(["`])r\1', r"\1s\1", sql)
        if relation in ("reverse", "commute", "duplicate") or (
            relation == "inline" and route.startswith("compile")
        ):
            sql = None
        result[route] = (status, codes, columns, sql)
    return result


def differences(
    original: dict[str, tuple], rewritten: dict[str, tuple], relation: str
) -> list[str]:
    expected = kept(original, relation)
    actual = kept(rewritten, relation, rewritten=True)
    return [
        f"{route}: {actual[route]} != {expected[route]}"
        for route in expected
        if actual[route] != expected[route]
    ]


@pytest.mark.parametrize("profile", forms.PROFILES)
@pytest.mark.parametrize("seed", forms.SEEDS)
def test_generated_case_keeps_what_each_relation_keeps(
    seed: int, profile: str, tmp_path: Path
) -> None:
    case = forms.generate(seed, profile)
    original = observe(
        case, lambda target: forms.module_text(case, target), tmp_path / "original"
    )
    for relation in meta.RELATIONS:
        if meta.module_text(case, relation, "postgres") == forms.module_text(
            case, "postgres"
        ):
            continue
        rewritten = observe(
            case,
            lambda target: meta.module_text(case, relation, target),
            tmp_path / relation,
        )
        problems = differences(original, rewritten, relation)
        assert not problems, (
            f"seed {seed}, profile {profile}, relation {relation}\n"
            + meta.module_text(case, relation, "postgres")
            + "\n".join(problems)
        )


def test_a_layout_that_changes_the_meaning_is_caught(tmp_path: Path) -> None:
    """The comparison is not vacuous: a layout that reads ``is not None`` as
    ``is None`` keeps every column and code, and only its SQL tells."""
    case = next(
        case
        for case in (forms.generate(s, p) for s in forms.SEEDS for p in forms.PROFILES)
        if case.form == "row" and " is not None" in forms.module_text(case, "postgres")
    )
    original = observe(
        case, lambda target: forms.module_text(case, target), tmp_path / "original"
    )

    def wrong(target: str) -> str:
        text = meta.module_text(case, "layout", target)
        return text.replace(" is not None", " is None")

    problems = differences(original, observe(case, wrong, tmp_path / "wrong"), "layout")
    assert problems and all(p.startswith(("emit-sql", "compile")) for p in problems)


def test_each_rewrite_keeps_the_oracle_columns() -> None:
    """The rewrites mean the same by the documented rules too: the oracle
    gives each the original's columns, reversed for ``reverse``."""
    for seed in forms.SEEDS:
        for profile in forms.PROFILES:
            case = forms.generate(seed, profile)
            expected = forms.expected_columns(case)
            for relation in meta.RELATIONS:
                columns = forms.expected_columns(meta.rewrite(case, relation))
                reverse = relation == "reverse"
                assert columns == (expected[::-1] if reverse else expected), (
                    seed,
                    profile,
                    relation,
                )


def test_registered_corpus_reaches_each_relation_in_each_form() -> None:
    """Coverage is an observation, not a proof (R13); each relation still
    changes a registered case of each form it applies to, and no other."""
    reached = {
        (relation, case.form)
        for case in (forms.generate(s, p) for s in forms.SEEDS for p in forms.PROFILES)
        for relation in meta.RELATIONS
        if meta.module_text(case, relation, "postgres")
        != forms.module_text(case, "postgres")
    }
    applies = {"rename": ("row", "join"), "inline": ("row",)}
    assert reached == {
        (relation, form)
        for relation in meta.RELATIONS
        for form in applies.get(relation, forms.FORMS)
    }
