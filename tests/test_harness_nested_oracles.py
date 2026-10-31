"""Independent nested oracles: typed literal expectations.

Expected values below are written by hand from the seed literals, never read
back from the oracle under test.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import hashlib
import itertools
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import UUID

import pytest

import _pietto_execution_nested_oracle as oracle
from pietto._project.check import check_project_parse_only

# Pure test helpers: no storage, native, Arrow, generated, golden or package premise.
pytestmark = pytest.mark.ci_workload("general-runtime")

TESTS = Path(__file__).resolve().parent
S = oracle.Segment


def _isolated(code: str, tmp_path: Path, seed: str = "0") -> str:
    """Run code with only tests/ importable and pietto and pyarrow blocked."""
    env = {
        **os.environ,
        "PYTHONPATH": str(TESTS),
        "PYTHONHASHSEED": seed,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    prelude = (
        "import sys\nsys.modules['pietto'] = None\nsys.modules['pyarrow'] = None\n"
    )
    done = subprocess.run(
        [sys.executable, "-P", "-c", prelude + code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def rows(name: str, set_name: str = "MINIMAL", leaves=oracle.DEFAULT_LEAVES):
    return oracle.example(oracle.expected(name, set_name, leaves))


def _bag(found, *labels):
    return sorted(
        (tuple(row[label] for label in labels) for row in found),
        key=lambda item: [(value is None, value) for value in item],
    )


def test_literal_oracle_evaluates_every_program_without_pietto_or_arrow(tmp_path):
    out = _isolated(
        "import _pietto_execution_nested_oracle as o\n"
        "for leaves in (o.DEFAULT_LEAVES, o.LEAVES):\n"
        "    for set_name in o.SETS:\n"
        "        for item in o.programs(leaves):\n"
        "            o.expected(item.name, set_name, leaves)\n"
        "            print(len(leaves), set_name, item.name)\n"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in {'pietto', 'pyarrow'}))\n",
        tmp_path,
    )
    *evaluated, modules = out.splitlines()
    assert evaluated == [
        f"{len(leaves)} {set_name} {item.name}"
        for leaves in (oracle.DEFAULT_LEAVES, oracle.LEAVES)
        for set_name in oracle.SETS
        for item in oracle.programs(leaves)
    ]
    assert {"C1_closed", "C10_grouped_let", "U6_left_true_where_v_gt_10"} <= {
        line.split()[-1] for line in evaluated
    }
    assert modules == "['pietto', 'pyarrow']"


@pytest.mark.parametrize("helper", ["_pietto_execution_nested_oracle"])
def test_helpers_never_import_pyarrow_on_import(tmp_path, helper):
    env = {**os.environ, "PYTHONPATH": str(TESTS), "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            f"import sys, {helper}\n"
            "print('pyarrow' in sys.modules, 'pietto' in sys.modules)",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert (done.returncode, done.stdout.strip()) == (0, "False False"), done.stderr


def test_minimal_seed_reproduces_the_brief_counterexamples():
    collected = rows("C2_captured")
    assert [row["id"] for row in collected] == [1, 1, 2]
    assert [[child["v"] for child in row["recent"]] for row in collected] == [
        [7, 7],
        [7, 7],
        [],
    ]
    assert sum(len(row["recent"]) for row in collected) == 4
    assert len(rows("U1_cross")) == 4
    assert len(rows("U2_inner_true")) == 4
    assert _bag(rows("U4_left_true"), "id", "v") == [(1, 7)] * 4 + [(2, None)]
    assert _bag(rows("U5_left_v_gt_10"), "id", "v") == [(1, None), (1, None), (2, None)]
    siblings = rows("C6_siblings")
    assert [(len(r["recent"]), len(r["paid"])) for r in siblings] == [
        (2, 3),
        (2, 3),
        (0, 0),
    ]
    assert siblings[0]["paid"] == [{"v": 100}, {"v": 200}, {"v": None}]
    expected = oracle.expected("C6_siblings", "MINIMAL")
    real_null_lost = [dict(siblings[0], paid=siblings[0]["paid"][:2]), *siblings[1:]]
    null_invented = [*siblings[:2], dict(siblings[2], paid=[{"v": None}])]
    assert oracle.check(siblings, expected) == []
    assert oracle.check(real_null_lost, expected)
    assert oracle.check(null_invented, expected)


def test_three_valued_logic_and_left_placeholders_on_the_full_seed():
    captured = rows("C2_captured", "FULL")
    assert [len(row["recent"]) for row in captured] == [3, 3, 0, 6, 1, 0]
    assert captured[5]["id"] is None and captured[5]["recent"] == []
    assert all(child["id"] != 40 for row in captured for child in row["recent"])
    assert _bag(rows("U3_inner_v_gt_10", "FULL"), "id", "v") == [
        (3, 11),
        (3, 12),
        (3, 13),
        (3, 14),
        (3, 15),
    ]
    assert _bag(rows("U5_left_v_gt_10", "FULL"), "id", "v") == [
        (1, None),
        (1, None),
        (2, None),
        (3, 11),
        (3, 12),
        (3, 13),
        (3, 14),
        (3, 15),
        (4, None),
        (None, None),
    ]
    left = _bag(rows("U4_left_true", "FULL"), "id", "v")
    assert left.count((2, None)) == 1 and left.count((None, None)) == 1
    assert left.count((3, None)) == 1 and len(left) == 3 + 3 + 1 + 6 + 1 + 1
    assert _bag(rows("U6_left_true_where_v_gt_10", "FULL"), "id", "v") == [
        (3, 11),
        (3, 12),
        (3, 13),
        (3, 14),
        (3, 15),
    ]


def test_unnest_outside_the_modeled_spellings_fails_closed():
    fields = oracle.child_fields()
    tables = oracle.seed("MINIMAL")
    left_false = oracle.Unnest("left", "False", False, False, fields)
    assert _bag(oracle.example(oracle.evaluate(left_false, tables)), "id", "v") == [
        (1, None),
        (1, None),
        (2, None),
    ]
    inner_false = oracle.Unnest("inner", "False", False, False, fields)
    assert oracle.evaluate(inner_false, tables) == ()
    for join, on in (
        ("right", "True"),
        ("full", "True"),
        ("lateral", None),
        ("cross", "True"),
        ("inner", None),
        ("left", None),
        ("inner", "o.k > 100"),
        ("left", "o.v < 0"),
    ):
        with pytest.raises(ValueError, match="not modeled"):
            oracle.Unnest(join, on, False, False, fields)


def _groups(name: str, parent_id: int):
    for segment in oracle.expected(name, "FULL"):
        for parent in segment.candidates:
            if parent["id"] == parent_id:
                return [
                    sorted(repr(child["v"]) for child in group.candidates)
                    for group in parent["recent"].segments
                ]
    raise AssertionError(parent_id)


def test_postgresql_null_posture_and_closed_order_key_types():
    assert _groups("C5_hidden_nullable_key_asc", 3) == [
        ["11"],
        ["13", "14"],
        ["15"],
        ["12", "None"],
    ]
    assert _groups("C5_hidden_nullable_key_desc", 3) == [
        ["12", "None"],
        ["15"],
        ["13", "14"],
        ["11"],
    ]
    tables = oracle.seed("FULL", oracle.LEAVES)
    for key in ("note", "ratio", "ship_day", "seen_at", "token"):
        let = oracle.Let("x", "orders", ("v",), ((key, False),))
        with pytest.raises(ValueError, match="order key"):
            oracle.evaluate(oracle.Collect((let,)), tables)
    with pytest.raises(ValueError, match="no order by"):
        oracle.evaluate(
            oracle.Collect((oracle.Let("x", "orders", ("v",), ()),)), tables
        )


def test_comparator_accepts_ties_and_boundary_subsets_and_nothing_else():
    expected = (
        S(({"v": 1},), 1),
        S(({"v": 2}, {"v": 3}, {"v": 4}), 3),
        S(({"v": 5}, {"v": 6}, {"v": 7}), 2),
    )
    for middle in itertools.permutations([2, 3, 4]):
        for tail in itertools.permutations([5, 6, 7], 2):
            found = [{"v": v} for v in (1, *middle, *tail)]
            assert oracle.check(found, expected) == []
            assert (
                oracle.check(
                    [{"id": 9, "c": found}],
                    (S(({"id": 9, "c": oracle.Nested(expected)},), 1),),
                )
                == []
            )
    rejected = (
        [2, 1, 3, 4, 5, 6],  # swap across groups
        [1, 2, 3, 5, 4, 6],
        [1, 2, 3, 4, 5],  # boundary subset too small
        [1, 2, 3, 4, 5, 6, 7],  # boundary subset too large
        [1, 2, 3, 4, 5, 8],  # value outside the boundary group
        [1, 2, 3, 4, 5, 5],
    )
    for values in rejected:
        assert oracle.check([{"v": v} for v in values], expected), values
    duplicated = (S(({"v": 2}, {"v": 2}), 2),)
    assert oracle.check([{"v": 2}, {"v": 2}], duplicated) == []
    assert oracle.check([{"v": 2}], duplicated)  # one duplicate missing
    assert oracle.check([{"v": 2}] * 3, duplicated)  # one extra row
    assert oracle.check({"v": 2}, duplicated) == ["rows: not a list"]


def test_every_damage_control_turns_a_pass_into_a_failure():
    expected = oracle.expected("C6_siblings", "FULL", oracle.LEAVES)
    realized = oracle.example(expected)
    assert oracle.check(realized, expected) == []
    damaged = oracle.damages(realized)
    assert set(damaged) == {
        "bool_as_int",
        "int_as_float",
        "decimal_scale",
        "signed_zero",
        "empty_text_as_null",
        "empty_collection_as_null",
        "all_null_record_dropped",
        "same_type_swap",
        "child_moved",
        "duplicate_parent_dropped",
        "parent_fields_reordered",
        "child_fields_reordered",
    }
    for name, found in damaged.items():
        assert oracle.check(found, expected), name
    assert oracle.check(realized, expected) == []  # damages copy, never mutate


def test_type_exact_leaves_keep_distinct_values_apart():
    pairs = (
        (True, 1),
        (1, 1.0),
        (Decimal("1.0"), Decimal("1.00")),
        (0.0, -0.0),
        ("", None),
        (date(2024, 1, 1), datetime(2024, 1, 1)),
        (UUID(int=1), "00000000-0000-0000-0000-000000000001"),
    )
    for left, right in pairs:
        assert oracle.leaf(left) != oracle.leaf(right), (left, right)
    container = (S(({"c": oracle.Nested(())},), 1),)
    assert oracle.check([{"c": []}], container) == []
    assert oracle.check([{"c": None}], container)
    assert oracle.check([{"c": [{"v": None}]}], container)


def test_duplicate_parents_use_bipartite_matching():
    ties = oracle.expected("C4_ties", "FULL")
    realized = oracle.example(ties)
    first, second = realized[0], realized[1]
    assert (first["id"], second["id"]) == (1, 1)
    a10, a11, a12 = (
        {"id": 10, "v": 7, "k": 5, "flag": True, "note": "a"},
        {"id": 11, "v": 7, "k": 5, "flag": True, "note": "a"},
        {"id": 12, "v": 8, "k": 5, "flag": False, "note": "b"},
    )
    for left, right in (([a10, a11], [a11, a12]), ([a12, a10], [a12, a10])):
        found = [dict(first, recent=left), dict(second, recent=right), *realized[2:]]
        assert oracle.check(found, ties) == []
    assert oracle.check([dict(first, recent=[a10, a10]), *realized[1:]], ties)
    one = oracle.Nested((S(({"v": 1},), 1),))
    two = oracle.Nested((S(({"v": 2},), 1),))
    bag = (S(({"id": 1, "c": one}, {"id": 1, "c": two}), 2),)
    assert (
        oracle.check([{"id": 1, "c": [{"v": 2}]}, {"id": 1, "c": [{"v": 1}]}], bag)
        == []
    )
    assert oracle.check([{"id": 1, "c": [{"v": 1}]}, {"id": 1, "c": [{"v": 1}]}], bag)


@pytest.mark.parametrize("leaves", [oracle.DEFAULT_LEAVES, oracle.LEAVES])
def test_every_program_renders_a_parseable_v2_project(tmp_path, leaves):
    unnest = re.compile(r"^    let o = unnest\(with_orders\.recent\)$")
    for item in oracle.programs(leaves):
        root = tmp_path / item.name
        root.mkdir()
        files = dict(item.files)
        assert files["pietto.toml"].startswith("schema_version = 2\n")
        for name, text in files.items():
            (root / name).write_text(text, encoding="utf-8")
        assert check_project_parse_only(root).ok, item.name
        source = files["main.pietto"]
        lines = [line for line in source.splitlines() if "unnest(" in line]
        assert all(unnest.match(line) for line in lines), item.name
        if isinstance(item.spec, oracle.Collect):
            assert all(let.order for let in item.spec.lets), item.name
            assert source.count(" = collect ") == len(item.spec.lets)
            assert source.count("        order by ") == len(item.spec.lets)
        elif item.spec.lateral:
            assert lines == [] and item.twin is not None
        else:
            assert len(lines) == 1 and "        order by id\n" in source
    twins = {item.name: item.twin for item in oracle.programs(leaves) if item.twin}
    assert all(twins[twin] == name for name, twin in twins.items())


def test_seed_discipline_for_every_admitted_leaf():
    values = [
        value
        for table in oracle.seed("FULL", oracle.LEAVES).values()
        for row in table.rows
        for value in row
        if value is not None
    ]
    kinds = Counter(type(value).__name__ for value in values)
    assert {
        "int",
        "bool",
        "str",
        "float",
        "Decimal",
        "date",
        "datetime",
        "UUID",
    } <= set(kinds)
    assert all(v.as_tuple().exponent == -4 for v in values if type(v) is Decimal)
    assert all(v.tzinfo is None for v in values if type(v) is datetime)
    assert any(v.microsecond for v in values if type(v) is datetime)
    floats = [v for v in values if type(v) is float]
    assert all(math.isfinite(v) for v in floats)
    assert any(v == 0 and math.copysign(1, v) < 0 for v in floats)
    texts = [v for v in values if type(v) is str]
    assert all("\x00" not in text for text in texts)
    assert {oracle.SENTINEL, ',{}"\\', "", "NULL"} <= set(texts)
    assert any(not text.isascii() for text in texts)


def test_canonical_documents_do_not_depend_on_the_hash_seed(tmp_path):
    code = (
        "import hashlib, _pietto_execution_nested_oracle as o\n"
        "for s in o.SETS:\n"
        "    for leaves in (o.DEFAULT_LEAVES, o.LEAVES):\n"
        "        print(hashlib.sha256(o.document(s, leaves)).hexdigest())\n"
    )
    first = _isolated(code, tmp_path, seed="1")
    assert first == _isolated(code, tmp_path, seed="2")
    here = [
        hashlib.sha256(oracle.document(s, leaves)).hexdigest()
        for s in oracle.SETS
        for leaves in (oracle.DEFAULT_LEAVES, oracle.LEAVES)
    ]
    assert first.split() == here
