"""Oracle-free metamorphic laws over nested results, their bounded corpus and
law-targeted damages.

Expected facts below are written by hand from the seed literals and the law
catalog, never read back from the helper under test.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import hashlib
import itertools
import os
from pathlib import Path
import random
import re
import subprocess
import sys

import pytest

import _pietto_execution_nested_oracle as oracle
import _pietto_harness_nested_metamorphic as laws
from pietto._project.check import check_project_parse_only

# Pure test helpers: no storage, native, Arrow, generated, golden or package premise.
pytestmark = pytest.mark.ci_workload("general-runtime")

TESTS = Path(__file__).resolve().parent
LEAF_SETS = {"default": oracle.DEFAULT_LEAVES, "every-leaf": oracle.LEAVES}
BOTH = pytest.mark.parametrize("leaves", list(LEAF_SETS.values()), ids=list(LEAF_SETS))
EACH_DATASET = pytest.mark.parametrize(
    ("leaves", "dataset"),
    [
        pytest.param(leaves, d.name, id=f"{label}-{d.name}")
        for label, leaves in LEAF_SETS.items()
        for d in laws.datasets(leaves)
    ],
)
LAW_IDS = [
    "C-PARENT",
    "C-EMPTY",
    "C-COUNT",
    "C-BAG",
    "C-DUP",
    "C-CLOSED",
    "C-SIBLING",
    "O-SORTED",
    "O-HIDDEN",
    "O-TOPK",
    "O-MONO",
    "O-REVERSE",
    "O-PARENT",
    "U-INNER-TRUE",
    "U-INNER-FALSE",
    "U-LEFT-TRUE",
    "U-LEFT-ON",
    "U-LEFT-FALSE",
    "U-WHERE",
    "U-LATERAL",
]
# Laws whose premise turns false on corpus data (LIMIT boundary ties).
NATURAL = {"C-BAG", "C-DUP", "C-CLOSED", "O-MONO", "U-LATERAL"}
# Hand-made instances whose programs break the law's premise.
WITNESSES = {
    "C-PARENT": (("C2_captured", "G_strip_id_2"), ""),
    "C-EMPTY": (("C2_captured", "U4_left_true"), "recent"),
    "C-SIBLING": (("C6_siblings", "G_paid", "C2_captured"), ""),
    "O-SORTED": (("C8_text_quoting",), "notes"),
    "O-HIDDEN": (("C5_hidden_nullable_key_asc", "G_captured_k_desc_all"), "recent"),
    "O-TOPK": (("C3_topk", "C2_captured"), ""),
    "O-REVERSE": (("C3_topk", "C2_captured"), ""),
    "O-PARENT": (("C2_captured", "G_strip", "G_strip"), ""),
    "U-INNER-TRUE": (("U2_inner_true", "U4_left_true"), ""),
    "U-LEFT-TRUE": (("U4_left_true", "U1_cross", "G_paid"), ""),
    "U-LEFT-ON": (("U5_left_v_gt_10", "U3_inner_v_gt_10", "C3_topk"), ""),
    "U-WHERE": (("U6_left_true_where_v_gt_10", "U2_inner_true"), ""),
}
# Collected lets ordered by a key they do not select; O-HIDDEN checks each.
HIDDEN_ORDER = {
    ("C5_hidden_nullable_key_asc", "recent"),
    ("C5_hidden_nullable_key_desc", "recent"),
    ("C6_siblings", "paid"),
    ("C8_text_quoting", "notes"),
    ("G_paid", "paid"),
}
LAW_TARGETED_DAMAGES = {
    "left_placeholder_dropped",
    "left_placeholder_invented",
    "topk_wrong_end",
    "child_order_reversed",
    "hidden_order_reversed",
    "duplicate_child_collapsed",
    "parent_duplicated",
    "sibling_crossed",
    "closed_divergence",
    "on_where_confused",
    "closed_last_dropped",
    "distinct_ignored",
    "null_record_dropped",
    "group_count_off",
    "null_group_dropped",
}


def _isolated(code: str, tmp_path: Path, seed: str = "0") -> str:
    """Run code with only tests/ importable and pietto and pyarrow blocked."""
    env = {
        **os.environ,
        "PYTHONPATH": str(TESTS),
        "PYTHONHASHSEED": seed,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    blocked = "import sys\nsys.modules['pietto'] = sys.modules['pyarrow'] = None\n"
    done = subprocess.run(
        [sys.executable, "-P", "-c", blocked + code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _violated(report) -> list:
    return [key for key, verdict in report.items() if verdict.value == laws.VIOLATED]


def _touching(leaves=oracle.DEFAULT_LEAVES) -> dict[str, tuple]:
    found: dict[str, list] = {}
    for instance in laws.instances(leaves):
        for name in dict.fromkeys(instance.programs):
            found.setdefault(name, []).append(instance)
    return {name: tuple(chosen) for name, chosen in found.items()}


def _only(found, chosen, dataset, name, rows, leaves=oracle.DEFAULT_LEAVES):
    """Law verdicts of the instances that read ``name``, with its rows replaced."""
    base = {(p, dataset): found[(p, dataset)] for i in chosen for p in i.programs}
    return laws.law_verdicts({**base, (name, dataset): rows}, leaves, chosen)


def _rows(found, dataset) -> dict:
    return {name: value for (name, at), value in found.items() if at == dataset}


def _damages(found, dataset, leaves=oracle.DEFAULT_LEAVES) -> list:
    """Tools damages of every member plus the law-targeted damages."""
    rows = _rows(found, dataset)
    cases = [
        (damage, name, value)
        for name in rows
        for damage, value in oracle.damages(rows[name]).items()
    ]
    return cases + [
        (damage, name, value)
        for damage, (name, value) in laws.law_damages(rows, leaves).items()
    ]


def test_law_catalog_is_closed_and_every_verdict_carries_a_reason():
    assert list(laws.LAWS) == LAW_IDS
    families = {"C": "collect", "O": "order", "U": "unnest"}
    for law_id, law in laws.LAWS.items():
        assert (law.id, law.family) == (law_id, families[law_id[0]])
        assert law.premise and len(law.arity) > 0
    report = laws.verdicts(laws.realized())
    values = {laws.HOLDS, laws.VIOLATED, laws.NOT_APPLICABLE}
    assert all(v.value in values and v.reason for v in report.values())
    assert {key[0] for key in report} == {"law", "oracle"}
    assert list(report) == sorted(report)


def test_unknown_programs_and_data_sets_fail_closed():
    rows = laws.realized()[("C2_captured", "MINIMAL")]
    for key, message in (
        (("C2_captrued", "MINIMAL"), "unknown program C2_captrued"),
        (("C2_captured", "MINMAL"), "unknown data set MINMAL"),
    ):
        for judge in (laws.law_verdicts, laws.verdicts):
            with pytest.raises(ValueError, match=message):
                judge({("C2_captured", "MINIMAL"): rows, key: rows})


def test_laws_never_read_the_oracle(monkeypatch):
    found = laws.realized()
    before = laws.law_verdicts(found)

    def forbidden(*args, **kwargs):
        raise AssertionError("a law read the oracle")

    for name in ("evaluate", "expected", "check", "leaf", "encode"):
        monkeypatch.setattr(oracle, name, forbidden)
    monkeypatch.setattr(laws, "expected", forbidden)
    assert laws.law_verdicts(found) == before
    shorter = {
        **found,
        ("C2_captured", "MINIMAL"): found[("C2_captured", "MINIMAL")][1:],
    }
    assert _violated(laws.law_verdicts(shorter))


@BOTH
def test_every_law_holds_on_the_oracle_realizations(leaves):
    report = laws.verdicts(laws.realized(leaves), leaves)
    assert _violated(report) == []
    members = {member.name: member for member in laws.corpus(leaves)}
    unmodeled = [
        key for key, v in report.items() if key[0] == "oracle" and v.value != laws.HOLDS
    ]
    assert unmodeled
    for _, _, name in unmodeled:
        spec = members[name].spec
        assert isinstance(spec, laws.Flatten) and spec.let.limit is not None
    assert {report[key].reason for key in unmodeled} == {
        "a LIMIT boundary splits a tie group of the collected let"
    }


@EACH_DATASET
def test_laws_ignore_ties_on_every_valid_realization(leaves, dataset):
    found, touching = laws.realized(leaves), _touching(leaves)
    tables = {d.name: d.tables for d in laws.datasets(leaves)}[dataset]
    checked = 0
    for member in laws.corpus(leaves):
        try:
            want = laws.expected(member, tables)
        except ValueError:
            want = None
        for rows in itertools.islice(laws.realizations(member, tables), 1, None):
            assert want is None or oracle.check(rows, want) == [], member.name
            chosen = touching[member.name]
            report = _only(found, chosen, dataset, member.name, rows, leaves)
            assert _violated(report) == [], member.name
            checked += 1
    assert checked or not tables["customers"].rows  # no parents: nothing to re-pick


def test_no_law_is_vacuous():
    outcomes: dict[str, set[str]] = {law: set() for law in laws.LAWS}
    for leaves in LEAF_SETS.values():
        report = laws.law_verdicts(laws.realized(leaves), leaves)
        for key, verdict in report.items():
            outcomes[key[2]].add(verdict.value)
        # Every offered instance holds somewhere, so none is dead weight.
        holds = {key[2:] for key, v in report.items() if v.value == laws.HOLDS}
        offered = laws.instances(leaves)
        assert holds == {(i.law, i.field, *i.programs) for i in offered}
        hidden = {(i.programs[0], i.field) for i in offered if i.law == "O-HIDDEN"}
        assert hidden == HIDDEN_ORDER
    assert all(laws.HOLDS in values for values in outcomes.values())
    natural = {law for law, values in outcomes.items() if laws.NOT_APPLICABLE in values}
    assert natural == NATURAL
    premised = {law_id for law_id, law in laws.LAWS.items() if law.premise != "None."}
    assert premised == NATURAL | set(WITNESSES)
    found = laws.realized()
    for law, (programs, field) in WITNESSES.items():
        chosen = (laws.Instance(law, programs, field),)
        report = laws.law_verdicts(found, chosen=chosen)
        assert len(report) == len(laws.datasets()) and {
            v.value for v in report.values()
        } == {laws.NOT_APPLICABLE}, law
    covered = {name for instance in laws.instances() for name in instance.programs}
    assert covered == {member.name for member in laws.corpus()}


@EACH_DATASET
def test_every_damage_is_caught_by_the_oracle_and_by_a_law(leaves, dataset):
    found, touching = laws.realized(leaves), _touching(leaves)
    members = {member.name: member for member in laws.corpus(leaves)}
    tables = {d.name: d.tables for d in laws.datasets(leaves)}[dataset]
    oracle_only: set[tuple[str, str, str]] = set()
    wants: dict[str, tuple | None] = {}
    for damage, name, value in _damages(found, dataset, leaves):
        if name not in wants:
            try:
                wants[name] = laws.expected(members[name], tables)
            except ValueError:
                assert isinstance(members[name].spec, laws.Flatten)
                wants[name] = None
        if (want := wants[name]) is None:
            continue
        key = (damage, name, dataset)
        assert oracle.check(value, want), key
        caught = any(  # stops at the first law that catches it
            _violated(_only(found, (instance,), dataset, name, value, leaves))
            for instance in touching[name]
        )
        assert caught != (damage in laws.ORACLE_ONLY), key
        if not caught:
            oracle_only.add(key)
    assert {key[0] for key in oracle_only} <= set(laws.ORACLE_ONLY)


def test_a_law_still_fails_when_the_oracle_agrees_with_a_wrong_result():
    found = laws.realized()
    rows = {
        name: found[(name, "MINIMAL")]
        for name, dataset in found
        if dataset == "MINIMAL"
    }
    name, wrong = laws.law_damages(rows)["left_placeholder_dropped"]
    agreeing = tuple(oracle.Segment((row,), 1) for row in wrong)
    assert oracle.check(wrong, agreeing) == []
    report = laws.law_verdicts({**found, (name, "MINIMAL"): wrong})
    assert {key[2] for key in _violated(report)} == {
        "U-LEFT-TRUE",
        "U-LATERAL",
        "U-LEFT-ON",
    }


@pytest.mark.parametrize("name", ["C2_captured", "U4_left_true"])
def test_laws_are_total_and_malformed_rows_are_violations(name):
    found = laws.realized()
    rows = found[(name, "FULL")]
    first = rows[0]
    bad = {
        "not a list": tuple(rows),
        "missing key": [{k: v for k, v in first.items() if k != "id"}, *rows[1:]],
        "wrong leaf type": [{**first, "id": "1"}, *rows[1:]],
    }
    if name == "C2_captured":
        child = {**first["recent"][0], "v": "7"}
        bad["container is None"] = [{**first, "recent": None}, *rows[1:]]
        bad["wrong child leaf type"] = [{**first, "recent": [child]}, *rows[1:]]
    chosen = _touching()[name]
    for label, value in bad.items():
        reading = _only(found, chosen, "FULL", name, value)
        assert reading and {v.value for v in reading.values()} == {laws.VIOLATED}, label


def test_a_signalling_nan_leaf_is_a_violation():
    every = laws.realized(oracle.LEAVES)
    rows = every[("C2_captured", "FULL")]
    child = {**rows[0]["recent"][0], "price": Decimal("sNaN")}
    bad = [{**rows[0], "recent": [child, *rows[0]["recent"][1:]]}, *rows[1:]]
    chosen = _touching(oracle.LEAVES)["C2_captured"]
    base = {(p, "FULL"): every[(p, "FULL")] for i in chosen for p in i.programs}
    found = {**base, ("C2_captured", "FULL"): bad}
    for judge in (laws.law_verdicts, laws.verdicts):
        report = judge(found, oracle.LEAVES)
        reading = {v.value for key, v in report.items() if "C2_captured" in key}
        assert reading == {laws.VIOLATED}, judge


def test_rule_witnesses():
    found = laws.realized()
    report = laws.law_verdicts(found)
    # R3: A appears twice on MINIMAL; each A container has 2 rows, CROSS has 4 for A.
    c2, u1 = found[("C2_captured", "MINIMAL")], found[("U1_cross", "MINIMAL")]
    assert [len(p["recent"]) for p in c2 if p["id"] == 1] == [2, 2]
    assert [r["id"] for r in u1].count(1) == 4
    count = ("law", "MINIMAL", "C-COUNT", "recent", "C2_captured", "U1_cross")
    assert report[count].value == laws.HOLDS
    # R4: on FULL the real all-NULL child of parent 3 looks like a placeholder.
    fields = oracle.child_fields()
    u4 = found[("U4_left_true", "FULL")]
    blank = Counter(r["id"] for r in u4 if all(r[f] is None for f in fields))
    assert blank == {2: 1, None: 1, 3: 1}
    moved = [
        {**r, "id": 2} if r["id"] == 3 and all(r[f] is None for f in fields) else r
        for r in u4
    ]
    left = ("law", "FULL", "U-LEFT-TRUE", "", "U4_left_true", "U1_cross", "C2_captured")
    assert report[left].value == laws.HOLDS
    after = _only(found, _touching()["U4_left_true"], "FULL", "U4_left_true", moved)
    assert after[left].value == laws.VIOLATED
    # R5: Unnest rows compare as a bag.
    rng = random.Random(5)
    spec = {member.name: member.spec for member in laws.corpus()}
    shuffled = {
        key: rows
        if isinstance(spec[key[0]], oracle.Collect)
        else rng.sample(rows, len(rows))
        for key, rows in found.items()
    }
    assert shuffled != found and laws.law_verdicts(shuffled) == report
    # R7: type-exact leaves on FULL with every leaf.
    every = laws.realized(oracle.LEAVES)
    c2 = every[("C2_captured", "FULL")]
    for damage in ("bool_as_int", "int_as_float", "decimal_scale"):
        bad = oracle.damages(c2)[damage]
        chosen = _touching(oracle.LEAVES)["C2_captured"]
        report = _only(every, chosen, "FULL", "C2_captured", bad, oracle.LEAVES)
        assert _violated(report), damage


def test_counterexamples_on_the_minimal_seed():
    found = laws.realized()
    report = laws.law_verdicts(found)

    def rows(name):
        return found[(name, "MINIMAL")]

    empty = [p["id"] for p in rows("C2_captured") if p["recent"] == []]
    assert (len(rows("U4_left_true")), len(rows("U1_cross")), empty) == (5, 4, [2])
    assert (len(rows("U5_left_v_gt_10")), len(rows("U3_inner_v_gt_10"))) == (3, 0)
    assert rows("U6_left_true_where_v_gt_10") == []  # LEFT ON p is not LEFT + WHERE p
    sizes = [(len(p["recent"]), len(p["paid"])) for p in rows("C6_siblings")]
    assert sizes == [(2, 3), (2, 3), (0, 0)]
    for key in (
        ("U-LEFT-TRUE", "", "U4_left_true", "U1_cross", "C2_captured"),
        ("U-LEFT-ON", "", "U5_left_v_gt_10", "U3_inner_v_gt_10", "C2_captured"),
        ("C-SIBLING", "", "C6_siblings", "C2_captured", "G_paid"),
    ):
        assert report[("law", "MINIMAL", *key)].value == laws.HOLDS
    child = dict.fromkeys(("id", *oracle.child_fields()))
    bad = [p if p["id"] != 2 else {**p, "recent": [child]} for p in rows("C2_captured")]
    after = _only(found, _touching()["C2_captured"], "MINIMAL", "C2_captured", bad)
    empty_key = ("law", "MINIMAL", "C-EMPTY", "recent", "C2_captured", "U1_cross")
    assert after[empty_key].value == laws.VIOLATED  # [{v: None}] is not []


def test_corpus_document_is_hash_seed_free_and_pietto_free(tmp_path):
    code = (
        "import hashlib, _pietto_harness_nested_metamorphic as m\n"
        "for leaves in (m.oracle.DEFAULT_LEAVES, m.oracle.LEAVES):\n"
        "    print(hashlib.sha256(m.document(leaves)).hexdigest())\n"
    )
    first = _isolated(code, tmp_path, seed="1")
    assert first == _isolated(code, tmp_path, seed="2")
    assert first.split() == [
        hashlib.sha256(laws.document(leaves)).hexdigest()
        for leaves in (oracle.DEFAULT_LEAVES, oracle.LEAVES)
    ]
    env = {**os.environ, "PYTHONPATH": str(TESTS), "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            "import sys, _pietto_harness_nested_metamorphic\n"
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


@BOTH
def test_corpus_is_bounded_and_covers_the_listed_features(leaves):
    members, sets = laws.corpus(leaves), laws.datasets(leaves)
    # Budget: at most 96 programs, 8 data sets, 32 rows per table, 1 MiB.
    assert len(members) <= 96 and len(sets) <= 8
    assert len(laws.document(leaves)) <= 1 << 20
    assert max(len(t.rows) for d in sets for t in d.tables.values()) <= 32
    assert [d.seed is None for d in sets] == [True, True] + [False] * (len(sets) - 2)
    assert len({m.name for m in members}) == len(members)
    assert {p.name for p in oracle.programs(leaves)} <= {m.name for m in members}
    fields = oracle.child_fields(leaves)
    found = laws.realized(leaves)
    features: set[str] = set()
    for d in sets:
        parents = [row["id"] for row in d.tables["customers"].records()]
        orders = d.tables["orders"].records()
        owners = Counter(row["customer_id"] for row in orders)
        for table in ("orders", "payments"):
            ids = [row["id"] for row in d.tables[table].records()]
            assert len(ids) == len(set(ids)), (d.name, table)  # the unique-key premise
        features |= {
            name
            for name, present in (
                (
                    "duplicate parents",
                    any(n > 1 for p, n in Counter(parents).items() if p is not None),
                ),
                ("NULL parent key", None in parents),
                (
                    "childless parent",
                    any(p is not None and not owners[p] for p in parents),
                ),
                (
                    "all-NULL child",
                    any(all(r[f] is None for f in fields) for r in orders),
                ),
                ("orphan child", None in owners),
                ("no parents", not parents),
                ("no children", not orders),
                (
                    "no child over 10",
                    any(
                        owners[p]
                        and all(
                            r["v"] is None or r["v"] <= 10
                            for r in orders
                            if r["customer_id"] == p
                        )
                        for p in parents
                        if p is not None
                    ),
                ),
            )
            if present
        }
        hidden = found[("C5_hidden_nullable_key_asc", d.name)]
        for parent in hidden:
            if len({repr(c) for c in parent["recent"]}) < len(parent["recent"]):
                features.add("identical hidden-key children")
    assert features == {
        "duplicate parents",
        "NULL parent key",
        "childless parent",
        "all-NULL child",
        "orphan child",
        "no parents",
        "no children",
        "no child over 10",
        "identical hidden-key children",
    }
    targeted = {
        damage
        for d in sets
        for damage in laws.law_damages(_rows(found, d.name), leaves)
    }
    assert targeted == LAW_TARGETED_DAMAGES
    # Tools pins its own catalog; these are the classes this corpus applies.
    tool_damages = {
        "bool_as_int",
        "int_as_float",
        "empty_text_as_null",
        "empty_collection_as_null",
        "all_null_record_dropped",
        "same_type_swap",
        "child_moved",
        "duplicate_parent_dropped",
    }
    if leaves == oracle.LEAVES:
        tool_damages |= {"decimal_scale", "signed_zero"}
    assert tool_damages <= {
        damage
        for d in sets
        for rows in _rows(found, d.name).values()
        for damage in oracle.damages(rows)
    }
    split: set[int | None] = set()
    for member in members:
        lets = member.spec.lets if isinstance(member.spec, oracle.Collect) else ()
        for d in sets:
            for segment in laws.expected(member, d.tables) if lets else ():
                for parent in segment.candidates:
                    for let in lets:
                        groups = parent[let.name].segments
                        if any(g.take < len(g.candidates) for g in groups):
                            split.add(let.limit)
    used = {
        let.limit
        for member in members
        if isinstance(member.spec, oracle.Collect)
        for let in member.spec.lets
        if let.limit is not None
    }
    assert split == used == {1, 2}


@BOTH
def test_every_member_renders_a_parseable_project(tmp_path, leaves):
    unnest = re.compile(r"    let o = unnest\(with_orders\.\w+\)")
    kinds = {
        (name, column.name): column.kind
        for name, table in oracle.seed("FULL", leaves).items()
        for column in table.columns
    }
    for member in laws.corpus(leaves):
        root = tmp_path / member.name
        root.mkdir()
        files = dict(member.files)
        assert files["pietto.toml"].startswith("schema_version = 2\n")
        for name, text in files.items():
            (root / name).write_text(text, encoding="utf-8")
        assert check_project_parse_only(root).ok, member.name
        source, spec = files["main.pietto"], member.spec
        lines = [line for line in source.splitlines() if "unnest(" in line]
        if isinstance(spec, oracle.Collect):
            lets, collected = spec.lets, spec.lets
            assert all(
                kinds[("customers", key)] in oracle.ORDERABLE for key, _ in spec.order
            )
        else:
            lets = (spec.let,) if isinstance(spec, laws.Flatten) else ()
            collected = () if spec.lateral else lets
            assert len(lines) == (0 if spec.lateral else 1), member.name
            assert all(unnest.fullmatch(line) for line in lines), member.name
            assert spec.lateral == bool(re.search(r"^    let o = \w+$", source, re.M))
            if isinstance(spec, oracle.Unnest) and not spec.lateral:
                assert "        order by id\n" in source, member.name
        assert all(let.order for let in collected), member.name
        assert source.count(" = collect ") == len(collected) + (
            isinstance(spec, oracle.Unnest) and not spec.lateral
        )
        for let in lets:
            assert all(
                kinds[(let.table, key)] in oracle.ORDERABLE for key, _ in let.order
            )


def test_native_matrix_requires_actual_denominator_and_holding_laws():
    from copy import deepcopy

    covered = set()
    for profile, leaves in laws.NATIVE_LEAVES.items():
        realized = laws.realized(leaves)
        found = {
            (program, dataset): deepcopy(realized[program, dataset])
            for program in laws.NATIVE_PROGRAMS[profile]
            for dataset in laws.NATIVE_DATASETS
        }
        report = laws.native_verdicts(found, profile)
        covered.update(
            key[2]
            for key, value in report.items()
            if key[0] == "law" and value.value == laws.HOLDS
        )
        missing = dict(found)
        del missing[next(iter(missing))]
        with pytest.raises(ValueError, match="denominator"):
            laws.native_verdicts(missing, profile)
        found["U1_cross", "FULL"].pop()
        with pytest.raises(ValueError, match="violated"):
            laws.native_verdicts(found, profile)
    assert covered == set(LAW_IDS)
