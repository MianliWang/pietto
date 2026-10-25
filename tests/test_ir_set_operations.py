"""Authored set operations over real canonical completed input/output roots."""

from pathlib import Path
from collections import Counter
from itertools import product

import pytest
from pietto._project.project_final_outputs import (
    ProjectCompletedSetOutput,
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_set_operations import ProjectSetMultiplicityLaw
from pietto._project.project_grain import ProjectGrainBasisState, ProjectGrainOriginKind

from _pietto_project_join import (
    _completed,
)
from _pietto_ir_sources import SET_OPERATIONS as OPERATIONS
from _pietto_ir_sources import bag_apply as _bag_apply
from _pietto_ir_sources import set_entry as _entry
from _pietto_ir_sources import set_source as _source


def test_union_all_nonselect_output_replays(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source())
    assert completed.ok, completed.diagnostics
    output = _entry(completed)
    assert tuple(output.schema.fields) == ("id",)
    assert output.fields[0].identity.owner.identity is output.owner.identity
    assert output.fields[0].identity.kind.value == "relation_output"
    assert not hasattr(output.fields[0], "item")
    assert not hasattr(output.fields[0], "select_fact")
    assert (
        _entry(completed, "result").schema.fields["id"].nullability.value == "nullable"
    )


@pytest.mark.parametrize(
    "quantifier,operands", (("", ("lhs", "rhs")), ("all", ("lhs",)))
)
def test_quantifier_and_arity_are_semantic_errors(
    tmp_path: Path, quantifier: str, operands: tuple[str, ...]
) -> None:
    completed = _completed(tmp_path, _source(quantifier=quantifier, operands=operands))
    assert not completed.ok
    assert any(d.code == "PIE-S2341" for d in completed.diagnostics)


def test_exact_types_do_not_promote(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source(right_type="Float"))
    assert not completed.ok
    assert any(d.code == "PIE-S2343" for d in completed.diagnostics)


def test_width_mismatch_has_no_partial_output(tmp_path: Path) -> None:
    source = _source().replace(
        "    other: Int | None", "    other: Int | None\n    extra: Int | None"
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert any(d.code == "PIE-S2342" for d in completed.diagnostics)
    output = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "combined"
    )
    assert isinstance(output, ProjectEffectiveOutputCompletionTerminal)
    assert output.output is None
    assert not hasattr(output, "schema")


def test_existing_select_control(tmp_path: Path) -> None:
    source = (
        _source().split("table combined:", 1)[0]
        + "query result:\n    from lhs\n    select:\n        id\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics


def _evaluate(entry, leaves: dict[str, Counter]) -> Counter:
    if not isinstance(entry, ProjectCompletedSetOutput):
        return leaves[entry.owner.definition.name]
    uses = entry.root.uses
    result = _evaluate(uses[0].authority.entry, leaves)
    kind, quantifier = entry.root.multiplicity.value.rsplit("_", 1)
    for use in uses[1:]:
        result = _bag_apply(
            kind, quantifier, result, _evaluate(use.authority.entry, leaves)
        )
    return result


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
def test_six_laws_include_zero_and_null_class(
    tmp_path: Path, kind: str, quantifier: str
) -> None:
    completed = _completed(
        tmp_path,
        _source(kind, quantifier, replay=False).replace("id: Int", "id: Int | None"),
    )
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    assert entry.root.multiplicity is ProjectSetMultiplicityLaw(f"{kind}_{quantifier}")
    assert entry.root.requires_equivalence is ((kind, quantifier) != ("union", "all"))
    assert (entry.uniqueness is not None) is (quantifier == "distinct")
    for m, n in product(range(4), repeat=2):
        result = _evaluate(
            entry, {"lhs": Counter({(None,): m}), "rhs": Counter({(None,): n})}
        )
        expected = {
            ("union", "all"): m + n,
            ("union", "distinct"): int(m + n > 0),
            ("intersect", "all"): min(m, n),
            ("intersect", "distinct"): int(m > 0 and n > 0),
            ("except", "all"): max(m - n, 0),
            ("except", "distinct"): int(m > 0 and n == 0),
        }[kind, quantifier]
        assert result[(None,)] == expected


def test_repeated_operand_build_once_use_twice(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source(operands=("lhs", "lhs")))
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    left, right = entry.root.uses
    assert left is not right and left.authority.entry is right.authority.entry
    assert left.resolution.reference.operand is not right.resolution.reference.operand
    assert [d.dependency_ordinal for d in entry.dependencies] == [0, 1]
    assert (
        sum(owner is left.authority.owner for owner in completed.completion.schedule)
        == 1
    )
    assert entry.fields[0].source.uses is entry.root.uses
    assert _evaluate(entry, {"lhs": Counter({(1,): 2})}) == Counter({(1,): 4})


def test_three_operand_except_is_left_fold_and_nested_is_not_flattened(
    tmp_path: Path,
) -> None:
    source = """shape Row:
    id: Int | None
source p: Row = postgres.table("p")
source q: Row = postgres.table("q")
source s: Row = postgres.table("s")
table flat:
    except all p, q, s
table inner_right:
    except all q, s
table nested:
    except all p, inner_right
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    leaves = {
        "p": Counter({(1,): 1, (2,): 1, (3,): 1}),
        "q": Counter({(1,): 1, (2,): 1}),
        "s": Counter({(2,): 1}),
    }
    assert _evaluate(_entry(completed, "flat"), leaves) == Counter({(3,): 1})
    assert _evaluate(_entry(completed, "nested"), leaves) == Counter({(2,): 1, (3,): 1})
    nested = _entry(completed, "nested")
    assert isinstance(nested, ProjectCompletedSetOutput)
    assert len(nested.root.uses) == 2
    assert nested.root.uses[1].authority.entry is _entry(completed, "inner_right")


@pytest.mark.parametrize("type_name", ("Float", "Bytes", "Json", "Any"))
def test_union_all_separates_type_from_equivalence(
    tmp_path: Path, type_name: str
) -> None:
    source = _source(right_type=type_name).replace("id: Int", f"id: {type_name}")
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    assert not entry.root.requires_equivalence and entry.uniqueness is None
    assert all(
        use.fields[0].type_concrete and use.fields[0].reason is not None
        for use in entry.root.uses
    )


@pytest.mark.parametrize("kind,quantifier", OPERATIONS[1:])
def test_comparison_required_even_for_intersect_except_all(
    tmp_path: Path, kind: str, quantifier: str
) -> None:
    source = _source(kind, quantifier, right_type="Float").replace(
        "id: Int", "id: Float | None"
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    errors = tuple(d for d in completed.diagnostics if d.code == "PIE-S2344")
    assert len(errors) == 2 and all(
        "Float equality is not supported yet" in d.message for d in errors
    )
    assert all(d.code not in {"PIE-S2337", "PIE-S2339"} for d in completed.diagnostics)


@pytest.mark.parametrize(
    "left_type,right_type,ok",
    (
        ("Decimal(10, 2)", "Decimal(10, 2)", True),
        ("Decimal(10, 2)", "Decimal(12, 2)", False),
        ("Decimal(10, 2)", "Decimal(10, 3)", False),
        ("Decimal", "Decimal(10, 2)", False),
        ("Decimal(10, 2)", "Decimal", False),
        ("Missing", "Missing", False),
    ),
)
def test_exact_decimal_and_unknown_type_evidence(
    tmp_path: Path, left_type: str, right_type: str, ok: bool
) -> None:
    source = _source(right_type=right_type).replace(
        "id: Int", f"id: {left_type} | None"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok is ok, completed.diagnostics
    if ok:
        entry = _entry(completed)
        assert isinstance(entry, ProjectCompletedSetOutput)
        evidence = entry.fields[0].type_sources
        assert len(evidence) == 2 and evidence[0] is not evidence[1]
        assert all(
            e.decimal is not None and (e.decimal.precision, e.decimal.scale) == (10, 2)
            for e in evidence
        )
    else:
        assert any(
            d.code in {"PIE-S2342", "PIE-S2343", "PIE-S2002"}
            for d in completed.diagnostics
        )


def test_canonical_aliases_keep_provenance(tmp_path: Path) -> None:
    source = "type A = Int\ntype B = A\n" + _source(right_type="B")
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    evidence = entry.root.uses[1].fields[0]
    assert evidence.resolution is not None
    assert [item.declared_name for item in evidence.resolution.alias_chain] == [
        "B",
        "A",
    ]


def test_different_nominal_types_are_not_same_spelling(tmp_path: Path) -> None:
    (tmp_path / "a.pietto").write_text(
        'enum Status:\n    active\nshape Row:\n    id: Status | None\nsource rows: Row = postgres.table("a")\nexport source rows\n'
    )
    (tmp_path / "b.pietto").write_text(
        'enum Status:\n    active\nshape Row:\n    id: Status | None\nsource rows: Row = postgres.table("b")\nexport source rows\n'
    )
    source = 'from "a.pietto" import source rows as Left\nfrom "b.pietto" import source rows as Right\ntable combined:\n    union all Left, Right\n'
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert any(d.code == "PIE-S2343" for d in completed.diagnostics)


@pytest.mark.parametrize(
    "kind,expected",
    (("union", "nullable"), ("intersect", "non_null"), ("except", "nullable")),
)
def test_nullability_is_independent_of_type_identity(
    tmp_path: Path, kind: str, expected: str
) -> None:
    source = (
        _source(kind, "all")
        .replace("id: Int", "id: Int | None")
        .replace("other: Int | None", "other: Int")
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert entry.schema.fields["id"].nullability.value == expected


def _property_source(kind: str, quantifier: str, *, unique: bool = True) -> str:
    key = "    key_id = unique(id)\n" if unique else ""
    return f"""shape Row:
    id: Int
    name: Text | None
{key}source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
table combined:
    {kind} {quantifier} lhs, rhs
query result:
    from combined
    let l = lhs
    inner join l on True
    select:
        key = combined.id
"""


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
def test_exact_set_property_and_grain_transfer(
    tmp_path: Path, kind: str, quantifier: str
) -> None:
    completed = _completed(tmp_path, _property_source(kind, quantifier))
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    incoming = completed.effective_outputs.current_regions[-1].joins[0].left_input
    if kind == "union":
        assert not incoming.keys and not incoming.fds
    else:
        assert incoming.keys and incoming.fds
    origin = entry.row_domain.set_origin
    assert origin is not None and incoming.grain.origin_set is origin
    expected = (
        ProjectGrainOriginKind.SET_QUOTIENT
        if quantifier == "distinct"
        else ProjectGrainOriginKind.SET_ALTERNATIVES
        if kind == "union"
        else ProjectGrainOriginKind.SET_SUBSET
    )
    assert origin.kind is expected
    assert incoming.grain.state is ProjectGrainBasisState.FACTORIZED


@pytest.mark.parametrize("kind", ("intersect", "except"))
def test_duplicate_subset_does_not_choose_left_occurrence(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(tmp_path, _property_source(kind, "all", unique=False))
    assert completed.ok, completed.diagnostics
    incoming = completed.effective_outputs.current_regions[-1].joins[0].left_input
    assert incoming.grain.state is ProjectGrainBasisState.UNKNOWN
    assert not incoming.grain.active and not incoming.keys
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput) and entry.uniqueness is None


def test_union_branch_local_fd_counterexample(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _property_source("union", "all"))
    assert completed.ok, completed.diagnostics
    output = completed.effective_outputs.current_regions[-1].joins[0].left_input
    assert output.keys == output.fds == ()
    rows = _evaluate(
        _entry(completed),
        {"lhs": Counter({(1, "Alice"): 1}), "rhs": Counter({(1, "Bob"): 1})},
    )
    assert rows[(1, "Alice")] == rows[(1, "Bob")] == 1


def test_two_global_inputs_are_not_global_union(tmp_path: Path) -> None:
    source = _source(replay=False)
    before, after = source.split("table combined:", 1)
    globals_ = "table one:\n    from lhs\n    select:\n        total = count()\ntable two:\n    from rhs\n    select:\n        other_total = count()\n"
    source = (
        before
        + globals_
        + "table combined:"
        + after.replace("union all lhs, rhs", "union all one, two")
    )
    source += "query result:\n    from combined\n    let l = lhs\n    inner join l on True\n    select:\n        total = combined.total\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    assert all(
        use.authority.historical_properties is not None
        and use.authority.historical_properties.grain.state
        is ProjectGrainBasisState.GLOBAL
        for use in entry.root.uses
    )
    incoming = completed.effective_outputs.current_regions[-1].joins[0].left_input
    assert incoming.grain.state is ProjectGrainBasisState.FACTORIZED
    assert _evaluate(
        entry, {"one": Counter({(1,): 1}), "two": Counter({(1,): 1})}
    ) == Counter({(1,): 2})


def test_empty_operand_retains_label_authority(tmp_path: Path) -> None:
    source = _source(operands=("empty", "rhs"))
    before, after = source.split("table combined:", 1)
    source = (
        before
        + "table empty:\n    from lhs\n    select:\n        first_label = id\n    limit 0\n"
        + "table combined:"
        + after.replace("        id\n", "        first_label\n")
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    assert tuple(_entry(completed).schema.fields) == ("first_label",)
