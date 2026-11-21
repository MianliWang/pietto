"""Shrinking generated cases (tests/_pietto_harness_shrink.py).

Over the generator's registered seeds, a shrunk case still fails and no
candidate of it does, every candidate is smaller and accepted by single-file
``check`` for both targets, a budget bounds the calls of the predicate, the
same case and predicate give the same result under any hash seed, and a
disagreement of ``compile_sql`` with a mutated oracle shrinks to its one
cause.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import _pietto_harness_generated_forms as forms
import _pietto_harness_shrink as shrink
import pytest

from pietto import cli
from pietto.compiler import compile_sql

CASES = [(seed, profile) for seed in forms.SEEDS for profile in forms.PROFILES]
_PROGRAM = """
import _pietto_harness_generated_forms as forms
import _pietto_harness_shrink as shrink

def nullable(case):
    return any(state == forms.NULLABLE for *_, state in forms.expected_columns(case))

for seed in forms.SEEDS:
    for profile in forms.PROFILES:
        case = forms.generate(seed, profile)
        if nullable(case):
            print(repr(shrink.shrink(case, nullable)))
"""


def _nullable(case: forms.Case) -> bool:
    """A stand-in failure: some selected column is nullable."""
    return any(state == forms.NULLABLE for *_, state in forms.expected_columns(case))


def test_shrunk_case_still_fails_and_no_candidate_of_it_does() -> None:
    shrunk = 0
    for seed, profile in CASES:
        case = forms.generate(seed, profile)
        if _nullable(case):
            result = shrink.shrink(case, _nullable)
            assert _nullable(result), (seed, profile)
            assert not any(map(_nullable, shrink.candidates(result))), (seed, profile)
            shrunk += shrink.size(result) < shrink.size(case)
    assert shrunk


def test_shrink_ends_within_its_size_and_its_budget() -> None:
    for seed, profile in CASES:
        case = forms.generate(seed, profile)
        assert all(shrink.size(c) < shrink.size(case) for c in shrink.candidates(case))
        calls: list[forms.Case] = []

        def fails(candidate: forms.Case) -> bool:
            calls.append(candidate)
            return True

        floor = shrink.shrink(case, fails)
        steps = len(calls)
        assert steps < shrink.size(case) and not list(shrink.candidates(floor))
        calls.clear()
        bounded = shrink.shrink(case, fails, budget=2)
        assert len(calls) == min(2, steps)
        assert bounded == (calls[-1] if calls else case)
        assert shrink.shrink(case, lambda _: False) == case


def test_shrink_gives_the_same_result_under_any_hash_seed() -> None:
    here = [
        repr(shrink.shrink(case, _nullable))
        for case in (forms.generate(seed, profile) for seed, profile in CASES)
        if _nullable(case)
    ]
    for hash_seed in ("0", "1"):
        environment = {
            **os.environ,
            "PYTHONHASHSEED": hash_seed,
            "PYTHONPATH": str(Path(__file__).parent),
        }
        run = subprocess.run(
            [sys.executable, "-B", "-c", _PROGRAM],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        assert run.stdout.splitlines() == here


@pytest.mark.parametrize(("seed", "profile"), CASES)
def test_every_candidate_is_accepted_by_check(
    seed: int, profile: str, tmp_path: Path
) -> None:
    for index, candidate in enumerate(shrink.candidates(forms.generate(seed, profile))):
        for target in ("postgres", "mysql"):
            path = tmp_path / f"{index}-{target}.pietto"
            path.write_text(forms.module_text(candidate, target), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["check", str(path), "--format", "json"])
            report = json.loads(out.getvalue())
            errors = [d for d in report["diagnostics"] if d["severity"] == "error"]
            assert code == 0 and not errors, (index, target, path.read_text())


def _narrowed(case: forms.Case) -> tuple[tuple[str, str, str], ...]:
    """The oracle mutated so that WHERE narrows a field it tests ``is not None``."""
    tested, conjuncts = [], [case.where] if case.where else []
    while conjuncts:
        node = conjuncts.pop()
        if node[:2] == ("bool", "and"):
            conjuncts += node[2:]
        elif node[0] == "isnone" and node[2]:
            tested.append(node[1])
    return tuple(
        (name, kind, forms.NON_NULL if expression in tested else state)
        for (name, kind, state), (_, expression) in zip(
            forms.expected_columns(case), case.items, strict=True
        )
    )


def test_compile_sql_disagreement_with_a_mutated_oracle_shrinks_to_its_cause(
    tmp_path: Path,
) -> None:
    states = {True: forms.NULLABLE, False: forms.NON_NULL, "unknown": forms.UNKNOWN}

    def disagrees(case: forms.Case) -> bool:
        project = tmp_path / str(len(list(tmp_path.iterdir())))
        project.mkdir()
        for name, text in forms.project_files(case, "postgres").items():
            (project / name).write_text(text, encoding="utf-8")
        emission = compile_sql(
            project,
            module="main.pietto",
            kind="query",
            name="q",
            dialect="postgres",
            emission_contract="contract.json",
        )
        if emission.status != "VERIFIED":  # another failure, not this one
            return False
        columns = json.loads(emission.document)["columns"]
        emitted = tuple(
            (c["label"], c["logical_type"]["name"], states[c["nullable"]])
            for c in columns
        )
        return emitted != _narrowed(case)

    case = next(
        case
        for case in (forms.generate(seed, profile) for seed, profile in CASES)
        if case.form == "row" and _narrowed(case) != forms.expected_columns(case)
    )
    assert disagrees(case)
    result = shrink.shrink(case, disagrees)
    ((_, expression),) = result.items
    assert expression[0] == "field" and result.where == ("isnone", expression, True)
    assert len(result.fields) == 2 and result.fields[1][2]
    assert (result.lets, result.limit) == ((), None)
    assert [key for key, _ in result.order] == ["id"]
