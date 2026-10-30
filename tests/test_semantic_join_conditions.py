"""Real authored pre-match conditions without premature JOIN completion."""

from dataclasses import replace
from pathlib import Path
import json

import pytest

from _pietto_project_join import BASE, _completed, _parsed, _source
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_relationship_uses import (
    ProjectNonConcreteJoinUse,
    ProjectRelationBindingOccurrence,
)
from pietto._project.project_completion import (
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import ProjectCompletedSetOutput
from pietto._project import project_join_conditions as conditions
from pietto._project.model import ProjectRowFieldNullability
from pietto.ast_nodes import AuthoredJoinKind, FromClause, NameExpr, QueryDef
from pietto.parser_api import parse_source
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic import analyze
from pietto.ir import build_ir
from pietto.semantic.model import EffectiveNullability, CheckMode
from pietto import cli
from pietto.semantic.model import (
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
)
from _pietto_semantic_joins import JOIN_PREFIX, located, run_joins


@pytest.mark.parametrize(
    "predicate", ("lhs.id == r.id", "lhs.allow_any", "lhs.id + 1 > 0")
)
def test_generic_bool_readiness_is_separate_from_completion(
    tmp_path: Path, predicate: str
) -> None:
    completed = _completed(tmp_path, _source(predicate))
    root = completed.roots.join_conditions
    fact = root.entries[0]
    assert fact.root is root
    assert fact.value_type is not None and fact.scope is not None
    assert isinstance(fact.use, ProjectNonConcreteJoinUse)
    assert fact.use.clause.on_clause is not None
    assert fact.ready and fact.value_type.resolved_type.name == "Bool"
    assert fact.mode == "M3" and fact.scope.value == "generic_join_match"
    assert fact.expression is fact.use.clause.on_clause.expression
    assert completed.ok and not fact.diagnostics
    assert not any(d.code == "PIE-S2334" for d in completed.diagnostics)


def test_predicate_filter_keeps_call_and_conjunct_occurrences(tmp_path: Path) -> None:
    completed = _completed(
        tmp_path, _source("Link(lhs, r) and r.key > 0 and r.key > 0")
    )
    fact = completed.roots.join_conditions.entries[0]
    assert fact.ready and fact.mode == "M3"
    assert fact.scope is not None and fact.scope.value == "generic_join_match"
    assert len(fact.conjuncts) == 3
    assert fact.conjuncts[1] is not fact.conjuncts[2]
    predicate = fact.environment.predicate_expression
    assert predicate is not None and len(predicate.calls) == 1
    assert len(fact.mandatory_equalities) == 1
    assert fact.mandatory_equalities[0].calls == predicate.calls


def test_c04_disjunction_has_no_unconditional_key_proof(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source("lhs.key == r.key or lhs.allow_any"))
    fact = completed.roots.join_conditions.entries[0]
    assert fact.ready and fact.conjuncts == (fact.expression,)
    assert not fact.null_rejections
    assert len(fact.references) == 3


@pytest.mark.parametrize("predicate", ("1", "missing.id == r.id", "sum(r.id) > 0"))
def test_invalid_conditions_retain_exact_additive_diagnostics(
    tmp_path: Path, predicate: str
) -> None:
    completed = _completed(tmp_path, _source(predicate))
    fact = completed.roots.join_conditions.entries[0]
    assert not fact.ready and fact.diagnostics
    assert all(
        any(d is retained for retained in completed.diagnostics)
        for d in fact.diagnostics
    )


def test_foreign_root_and_forged_positive_are_rejected(tmp_path: Path) -> None:
    local = _completed(tmp_path / "local", _source("lhs.id == r.id"))
    foreign = _completed(tmp_path / "foreign", _source("lhs.id == r.id"))
    fact = local.roots.join_conditions.entries[0]
    with pytest.raises(ValueError, match="exact"):
        replace(fact, use=foreign.roots.join_conditions.entries[0].use)
    with pytest.raises((ValueError, TypeError), match="init=False"):
        replace(fact, ready=True)


# SEMI and ANTI have no JOIN spelling: only an `any` filter before a later JOIN
# makes one.
@pytest.mark.parametrize(
    "kind",
    tuple(
        kind
        for kind in AuthoredJoinKind
        if kind not in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
    ),
)
@pytest.mark.parametrize(
    "predicate", (None, "Link(lhs, r)", "Link(lhs, r) and r.key > 0")
)
def test_explicit_condition_kind_dispatch(tmp_path: Path, kind, predicate) -> None:
    completed = _completed(tmp_path, _source(predicate, kind=kind.value))
    fact = completed.roots.join_conditions.entries[0]
    valid = (predicate is None) is (kind is AuthoredJoinKind.CROSS)
    assert fact.ready is valid and completed.ok is valid
    assert fact.use.clause.kind is kind
    assert isinstance(fact.use, ProjectNonConcreteJoinUse)
    if kind is AuthoredJoinKind.CROSS:
        assert fact.mode == "M5"
    elif valid:
        assert fact.mode == "M3" and len(fact.mandatory_equalities) == 1


@pytest.mark.parametrize(
    "predicate, proofs",
    (
        ("r.key is None", 0),
        ("r.key is not None", 1),
        ("r.key > 0", 1),
        ("lhs.id == r.id and lhs.id == r.id", 4),
        ("lhs.allow_any", 1),
        ("lhs.id + r.id > 0", 0),
        ("lhs.allow_any or r.allow_any", 0),
        ("lhs.id == r.id and (lhs.key == r.key or lhs.allow_any)", 2),
    ),
)
def test_sound_ordered_null_rejection_proofs(
    tmp_path: Path, predicate: str, proofs: int
) -> None:
    fact = _completed(tmp_path, _source(predicate)).roots.join_conditions.entries[0]
    assert fact.ready
    assert len(fact.null_rejections) == proofs
    for proof in fact.null_rejections:
        assert proof.condition is fact
        assert proof.field is proof.reference.target
        assert any(proof.reference is reference for reference in fact.references)
        assert proof.field.environment is fact.environment
    if proofs:
        with pytest.raises(ValueError, match="exact"):
            replace(fact.null_rejections[0], conjunct_position=100)


def test_nullable_bool_and_current_outer_join_inputs(tmp_path: Path) -> None:
    fact = _completed(
        tmp_path, _source("lhs.allow_any", kind="left")
    ).roots.join_conditions.entries[0]
    assert fact.value_type is not None
    assert fact.ready and fact.value_type.nullability is EffectiveNullability.NULLABLE
    target_id = next(
        item
        for item in fact.environment.fields
        if item.binding.name == "r" and item.input_field.evidence.name == "id"
    )
    assert target_id.nullability is ProjectRowFieldNullability.NON_NULL
    assert not target_id.null_extensions


@pytest.mark.parametrize("kind", ("left", "inner"))
def test_previous_join_nullability_is_retained_without_prefix_ir(
    tmp_path: Path, kind: str
) -> None:
    source = _source("Link(lhs, r)", kind=kind).replace(
        "    select:\n",
        "    let last = rhs\n    left join last on r.id == last.id\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    first, current = completed.roots.join_conditions.entries
    assert first.ready and current.ready
    left, right = (reference.target for reference in current.references)
    assert left is not None and right is not None
    assert isinstance(first.use, ProjectNonConcreteJoinUse)
    assert left.binding is first.use.target_binding
    expected = (
        ProjectRowFieldNullability.NULLABLE
        if kind == "left"
        else ProjectRowFieldNullability.NON_NULL
    )
    assert left.nullability is expected
    assert bool(left.null_extensions) is (kind == "left")
    if kind == "left":
        assert left.null_extensions[0] is first.use.identity
    assert right.nullability is ProjectRowFieldNullability.NON_NULL


def test_extra_filter_preserves_matched_key_upper_bound_without_coverage(
    tmp_path: Path,
) -> None:
    from _pietto_project_join_full import _unique_source

    fact = _completed(
        tmp_path, _unique_source("left", "Link(lhs, r) and r.key > 0")
    ).roots.join_conditions.entries[0]
    matches = tuple(m for m in fact.key_matches if m.binding is fact.use.target_binding)
    assert len(matches) == 1
    match = matches[0]
    assert match.maximum is conditions.ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert match.minimum is conditions.ProjectRelationshipMinimumBound.ZERO_ALLOWED
    assert match.condition is fact and match.equalities == fact.mandatory_equalities
    assert any(key is match.key for key in match.properties.keys)


@pytest.mark.parametrize(
    "predicate, state, count",
    (
        ("id == 1", "ambiguous", 2),
        ("r.missing == 1", "unknown", 0),
        ("outer.id == 1", "unknown", 0),
    ),
)
def test_reference_buckets_never_choose_winners(
    tmp_path: Path, predicate, state, count
) -> None:
    fact = _completed(tmp_path, _source(predicate)).roots.join_conditions.entries[0]
    reference = fact.references[0]
    assert reference.state.value == state
    assert len(reference.candidates) == count and reference.target is None
    assert not fact.ready


def test_self_use_keeps_exact_input_field_and_distinct_bindings(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id").replace(
        "let r = rhs\n    inner join r", "let r = lhs\n    inner join r"
    )
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    left, right = (reference.target for reference in fact.references)
    assert left is not None and right is not None
    assert fact.ready and left.binding is not right.binding
    assert left.input_field is right.input_field
    assert left is not right


def test_duplicate_alias_is_not_resolved_by_field_or_type(tmp_path: Path) -> None:
    source = (
        _source("lhs.id == lhs.id")
        .replace("let r = rhs", "let lhs = rhs")
        .replace("join r on", "join lhs on")
    )
    authored = parse_source(source, path="main.pietto")
    assert authored.ast is not None and authored.diagnostics == ()
    query = authored.ast.definitions[-1]
    assert isinstance(query, QueryDef) and isinstance(query.from_clause, FromClause)
    assert query.from_clause.source_name == "lhs"
    (binding,) = query.naming_declarations
    assert isinstance(binding.expression, NameExpr)
    assert binding.name == "lhs" and binding.expression.name == "rhs"
    (join,) = query.join_clauses
    assert join.target_relation_name == "lhs"
    parsed = _parsed(tmp_path, source)
    assert not parsed.ok and not parsed.errors
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in parsed.diagnostics
    ] == [("PIE-S2604", "Ambiguous JOIN input: lhs", join.span.line, join.span.column)]


def test_later_binding_reference_is_forward(tmp_path: Path) -> None:
    source = _source("later.id == r.id").replace(
        "    select:\n",
        "    let later = rhs\n    inner join later on lhs.id == later.id\n    select:\n",
    )
    facts = _completed(tmp_path, source).roots.join_conditions.entries
    reference = facts[0].references[0]
    assert reference.state.value == "forward" and reference.target is None
    assert reference.binding_candidates == (facts[1].use.target_binding,)
    assert not facts[1].ready


@pytest.mark.parametrize("predicate", ("local > 0", "projected > 0", "sum(r.id) > 0"))
def test_current_block_later_stage_values_do_not_leak(
    tmp_path: Path, predicate: str
) -> None:
    source = _source(predicate).replace(
        "    select:\n",
        "    let local = lhs.id\n    select:\n        projected = lhs.id\n",
    )
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready and fact.diagnostics


def test_available_exported_projection_is_an_input(tmp_path: Path) -> None:
    source = _source("view.renamed == r.id")
    source = source.replace(
        "query result:\n",
        "table view:\n    from lhs\n    select:\n        renamed = id\nquery result:\n",
    )
    source = source.replace(
        "query result:\n    from lhs", "query result:\n    from view"
    )
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert fact.ready
    assert fact.references[0].target is not None
    assert fact.references[0].target.input_field.evidence.name == "renamed"


def test_condition_rejects_equal_looking_foreign_input_root(tmp_path: Path) -> None:
    local = _completed(tmp_path / "local", _source("lhs.id == r.id"))
    foreign = _completed(tmp_path / "foreign", _source("lhs.id == r.id"))
    root = local.roots.join_conditions
    ledger = root.uses.ledgers[0]
    foreign_target = foreign.roots.join_conditions.entries[0].use.target_binding
    graft = replace(
        ledger.bindings[1], target=foreign_target.target, output=foreign_target.output
    )
    use = replace(ledger.uses[0], target_binding=graft)
    grafted_ledger = replace(ledger, bindings=(ledger.bindings[0], graft), uses=(use,))
    grafted_uses = replace(root.uses, ledgers=(grafted_ledger,))
    with pytest.raises(ValueError, match="exact"):
        conditions.build_project_join_conditions(grafted_uses)


def test_field_reference_and_proof_constructors_enforce_membership(
    tmp_path: Path,
) -> None:
    source = _source("lhs.id == r.id and lhs.key == r.key")
    local = _completed(tmp_path / "local", source).roots.join_conditions.entries[0]
    foreign = _completed(tmp_path / "foreign", source).roots.join_conditions.entries[0]
    local_field = local.references[0].target
    foreign_field = foreign.references[0].target
    assert local_field is not None and foreign_field is not None
    for attribute in ("binding", "input_field", "nullability", "value_type"):
        with pytest.raises((ValueError, TypeError), match="init=False"):
            replace(
                local_field,
                **{attribute: getattr(foreign_field, attribute)},
            )
    with pytest.raises(ValueError, match="exact"):
        replace(local.null_rejections[0], reference=foreign.references[0])
    with pytest.raises(ValueError, match="exact"):
        replace(local.references[0], position=1000)
    with pytest.raises(ValueError, match="exact"):
        replace(local_field, position=-1)


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_single_file_condition_keeps_its_exact_join_in_ir(mode: CheckMode) -> None:
    parsed = parse_source(_source("lhs.id == r.id"))
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast, mode_override=mode)
    assert semantic.diagnostics == ()
    query = semantic.model.relation_symbols["result"]
    assert isinstance(query, QueryDef)
    info = semantic.model.relation_joins[query]
    assert len(info.inputs) == 2 and len(info.joins) == 1
    assert info.joins[0].clause is query.join_clauses[0]
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    legacy = analyze_project_namespace(parsed.ast)
    assert legacy.model.relation_joins == {}
    legacy_lowered = build_ir(parsed.ast, legacy.model)
    assert legacy_lowered.ir is None
    assert any(d.code == "PIE-I1000" for d in legacy_lowered.diagnostics)


def test_duplicate_alias_reports_every_ambiguous_join_occurrence(
    tmp_path: Path,
) -> None:
    source = (
        _source("lhs.id == lhs.id")
        .replace("let r = rhs", "let lhs = rhs")
        .replace("join r on", "join lhs on")
    )
    source += "query repeated:" + source.split("query result:", 1)[1]
    authored = parse_source(source, path="main.pietto")
    assert authored.ast is not None and authored.diagnostics == ()
    first, second = authored.ast.definitions[-2:]
    assert isinstance(first, QueryDef) and isinstance(second, QueryDef)
    assert first.join_clauses[0] is not second.join_clauses[0]
    parsed = _parsed(tmp_path, source)
    assert not parsed.ok and not parsed.errors
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in parsed.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Ambiguous JOIN input: lhs",
            query.join_clauses[0].span.line,
            query.join_clauses[0].span.column,
        )
        for query in (first, second)
    ]
    assert parsed.diagnostics[0] is not parsed.diagnostics[1]


@pytest.mark.parametrize("predicate", ("row_number() window ordered", "rn < 2"))
def test_window_and_current_window_alias_are_unavailable(
    tmp_path: Path, predicate: str
) -> None:
    source = (
        _source(predicate).replace(
            "    select:\n", "    let ordered = window(order by lhs.id)\n    select:\n"
        )
        + "        rn = row_number() window ordered\n"
    )
    if predicate == "row_number() window ordered":
        parsed = parse_source(source)
        assert parsed.ast is None
        assert parsed.diagnostics[0].code == "PIE-P1000"
        return
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready and fact.diagnostics


def test_unknown_project_field_type_is_unavailable(tmp_path: Path) -> None:
    source = "shape Identifier:\n    code: Text\n" + _source(
        "lhs.key == r.key"
    ).replace("key: Int | None", "key: Identifier | None")
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready
    assert all(ref.state.value == "unavailable" for ref in fact.references)
    assert all(
        len(ref.candidates) == 1 and ref.target is None for ref in fact.references
    )


def test_an_enum_project_field_type_is_available(tmp_path: Path) -> None:
    """A field of an enum is typed as that enum, as in a single file, so an
    `on` that compares two such fields is ready. Before, the enum was of
    unknown type and the condition unavailable."""
    source = "enum Identifier:\n    first\n    second\n" + _source(
        "lhs.key == r.key"
    ).replace("key: Int | None", "key: Identifier | None")
    result = _completed(tmp_path, source)
    fact = result.roots.join_conditions.entries[0]
    assert fact.ready
    assert all(
        ref.state.value == "resolved" and ref.target is not None
        for ref in fact.references
    )
    assert result.diagnostics == ()


def test_set_input_and_independent_valid_branches_survive(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id")
    source = source.replace(
        "query result:\n",
        "table combined:\n    union all lhs, rhs\nquery result:\n",
    ).replace("let r = rhs\n    inner join r", "let r = combined\n    inner join r")
    source += "query valid:\n    from lhs\n    select:\n        id\n"
    result = _completed(tmp_path, source)
    fact = result.roots.join_conditions.entries[0]
    assert result.ok, result.diagnostics
    assert fact.ready and fact.references[1].state.value == "resolved"
    entries = {
        entry.owner.definition.name: entry for entry in result.effective_outputs.entries
    }
    combined, valid = entries["combined"], entries["valid"]
    assert isinstance(combined, ProjectCompletedSetOutput)
    assert isinstance(valid, ProjectExistingEffectiveOutput)
    assert [d.target.definition.name for d in combined.dependencies] == ["lhs", "rhs"]
    assert len(combined.root.uses) == 2
    for ordinal, (use, dependency) in enumerate(
        zip(combined.root.uses, combined.dependencies, strict=True)
    ):
        assert use.dependency is dependency
        assert use.resolution is dependency.evidence
        assert use.resolution.reference.operand_ordinal == ordinal
        assert use.authority.entry is entries[dependency.target.definition.name]
    assert fact.inputs is not None
    right = fact.inputs.scope.bindings[1].authority
    assert right is not None and right.entry is combined
    assert valid.output is not None


def test_join_effective_input_uses_current_slice4_authority(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id").replace("query result:", "table joined:")
    source += "query downstream:\n    from joined\n    let last = rhs\n    inner join last on joined.id == last.id\n    select:\n        id = joined.id\n"
    facts = _completed(tmp_path, source).roots.join_conditions.entries
    assert facts[0].ready and facts[1].ready
    assert facts[1].references[0].state.value == "resolved"
    assert facts[1].inputs is not None


@pytest.mark.parametrize("kind", ("inner", "left"))
def test_distinct_producer_uses_current_condition_authority(
    tmp_path: Path, kind: str
) -> None:
    source = (
        BASE
        + f"""query d:
    from lhs
    select distinct:
        id
query result:
    from d
    let r = rhs
    {kind} join r on d.id == r.id
    select:
        id = d.id
"""
    )
    completed = _completed(tmp_path, source)
    assert completed.ok and completed.diagnostics == ()
    outputs = completed.effective_outputs
    operative = outputs.operative_conditions
    assert isinstance(operative, conditions.ProjectJoinConditionCompletion)
    assert operative.historical is outputs.condition_authority
    assert operative is completed.roots.join_conditions
    (fact,) = operative.entries
    (historical,) = operative.historical.entries
    assert fact is not historical
    assert fact.use is historical.use and fact.ledger is historical.ledger
    assert fact.ready and fact.inputs is not None
    assert outputs.current_regions[0].joins[0].condition is fact
    assert fact.inputs.scope is outputs.input_scopes[0]
    assert outputs.input_scopes and outputs.allocation_events
    assert fact.references[0].target is not None
    assert fact.references[0].target.binding.name == "d"


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("schema", (1, 2))
def test_project_check_modes_admit_only_completed_explicit_module_conditions(
    tmp_path: Path, mode: CheckMode, schema: int
) -> None:
    source = f"mode {mode.value}\n" + _source("lhs.id == r.id")
    _completed(tmp_path, source)
    (tmp_path / "pietto.toml").write_text(
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n'
    )
    parsed = check_project_parse_only(tmp_path)
    assert parsed.ok
    semantic = build_empty_project_semantic_result(parsed)
    result = (
        build_project_completed_semantic_result(semantic) if schema == 2 else semantic
    )
    assert result.ok is (schema == 2)
    assert any(d.code == "PIE-S2334" for d in result.diagnostics) is (schema == 1)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("valid", (False, True))
def test_public_sql_condition_admission_and_no_partial_artifact(
    tmp_path: Path, capsys, dialect: str, mode: CheckMode, valid: bool
) -> None:
    path = tmp_path / "main.pietto"
    path.write_text(
        f"mode {mode.value}\n"
        + _source("lhs.id == r.id" if valid else "1").replace(
            "postgres.table", f"{dialect}.table"
        )
    )
    for command in (
        ["check", str(path), "--format", "json"],
        ["emit-sql", str(path), "--dialect", dialect, "--format", "json"],
    ):
        assert cli.main(command) == (0 if valid else 1)
        captured = capsys.readouterr()
        assert not captured.err
        document = json.loads(captured.out)
        assert document["ok"] is valid
        if valid:
            assert document["diagnostics"] == []
            if command[0] == "emit-sql":
                assert document["artifacts"]
        else:
            assert not document.get("artifacts", [])
            assert [d["code"] for d in document["diagnostics"]] == ["PIE-S2202"]


def test_package_root_boundary_precedes_condition_analysis(tmp_path: Path) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 3\n[package]\npath = "pkg"\nnamespace = "test"\nname = "example"\nversion = "1.0.0"\nsha256 = "'
        + "a" * 64
        + '"\n'
    )
    (tmp_path / "main.pietto").write_text(_source("lhs.id == r.id"))
    parsed = check_project_parse_only(tmp_path)
    assert not parsed.ok and not parsed.parsed_inputs
    assert any(
        "package-root project is read by explain --project" in error.message
        for error in parsed.errors
    )


# The `on` of JOIN c is at line 23, column 21: the binder of an `any` before a
# later JOIN (a hidden SEMI JOIN), a later binding, a `let` name and an unused
# def around it.
_ON_TEMPLATE = (
    JOIN_PREFIX + "query q:\n    from orders\n    let gone = regions\n"
    "    where any(gone.id == orders.amount for gone in gone)\n"
    "    let c = customers\n    inner join c on {}\n"
    "    let later = regions\n    cross join later\n"
    "    let big = 1\n    select:\n        x = orders.id\n"
    "def inc(x: Int) -> Int | None: return x + 1\n"
)


@pytest.mark.parametrize(
    ("condition", "expected"),
    (
        ("gone.id == 1", "JOIN ON reference is unknown: gone.id"),
        ("customers.id == 1", "JOIN ON reference is unknown: customers.id"),
        ("c.nope == 1", "JOIN ON reference is unknown: c.nope"),
        ("c.name.x == 1", "JOIN ON reference is unknown: c.name.x"),
        ("big == 1", "JOIN ON reference is unknown: big"),
        ("label == 1", "JOIN ON reference is unknown: label"),
        ("later.id == 1", "JOIN ON reference is forward: later.id"),
        ("id == 1", "JOIN ON reference is ambiguous: id; write orders.id or c.id"),
    ),
)
def test_single_file_join_on_references_resolve_against_the_on_row(
    condition: str, expected: str
) -> None:
    run = run_joins(_ON_TEMPLATE.format(condition))
    checks, _ = run.checks()
    assert run.diagnostics == []
    assert located(checks.reads) == [("PIE-S2335", expected, 23, 21)]
    # The failed reference explains the condition's unknown type.
    assert (checks.diagnostics, checks.facts) == ((), {})


def test_single_file_join_on_reads_are_typed_from_their_own_row() -> None:
    run = run_joins(_ON_TEMPLATE.format("c.id == orders.customer_id and later.id == 1"))
    checks, _ = run.checks()
    assert located(checks.reads) == [
        ("PIE-S2335", "JOIN ON reference is forward: later.id", 23, 52)
    ]
    run = run_joins(_ON_TEMPLATE.format("c.id == orders.customer_id"))
    checks, value_types = run.checks()
    query = run.relation("q")
    info = checks.facts[query]
    assert (checks.diagnostics, checks.reads) == ((), ())
    semi, inner, cross = query.join_clauses
    assert semi.on_clause is not None and inner.on_clause is not None
    condition = inner.on_clause.expression
    assert [join.condition for join in info.joins] == [
        semi.on_clause.expression,
        condition,
        None,
    ]
    assert [(join.mode, join.null_extends) for join in info.joins] == [
        ("M3", ()),
        ("M3", ()),
        ("M5", ()),
    ]
    assert sorted(
        (leaf.span.line, leaf.span.column, read.input, read.field)
        for leaf, read in info.field_reads.items()
    ) == [
        (21, 15, 1, "id"),
        (21, 26, 0, "amount"),
        (23, 21, 2, "id"),
        (23, 29, 0, "customer_id"),
        (28, 13, 0, "id"),
    ]
    assert value_types[condition] == ValueType(
        ResolvedType("Bool", TypeKind.BUILTIN), EffectiveNullability.UNKNOWN
    )
    assert all(read in value_types for read in info.field_reads if read.span.line < 28)


@pytest.mark.parametrize(
    ("condition", "expected"),
    (
        pytest.param(
            "count() > 1",
            ("PIE-S2335", "Aggregate expressions are unavailable in JOIN ON."),
            id="aggregate",
        ),
        pytest.param(
            "orders.amount + 1",
            ("PIE-S2202", "Expected Bool expression in JOIN ON"),
            id="not_bool",
        ),
        pytest.param(
            'orders.id == "x"',
            (
                "PIE-S2105",
                "Invalid operands for operator ==: expected comparable operands",
            ),
            id="operands_once",
        ),
        pytest.param(
            "inc(orders.customer_id) == c.id",
            (
                "PIE-S2395",
                "Invalid argument for def inc at position 1 (x): expected Int, "
                "got Int | None",
            ),
            id="def_argument_reads_the_on_row",
        ),
    ),
)
def test_single_file_join_on_typing_reports_each_error_once(
    condition: str, expected: tuple[str, str]
) -> None:
    run = run_joins(_ON_TEMPLATE.format(condition))
    checks, _ = run.checks()
    assert located(checks.diagnostics) == [(*expected, 23, 21)]
    assert (checks.reads, checks.facts) == ((), {})
    clean = run_joins(_ON_TEMPLATE.format("inc(c.id) == orders.id")).checks()[0]
    assert (clean.diagnostics, clean.reads) == ((), ())
    assert len(clean.facts) == 1


_UNAVAILABLE = (
    "PIE-S2202",
    "JOIN ON expression type is unavailable; the fields it reads need known types.",
    21,
    21,
)


@pytest.mark.parametrize(
    ("condition", "expected"),
    (
        pytest.param("o.v", [_UNAVAILABLE], id="unknown_condition"),
        pytest.param("o.v == orders.id", [_UNAVAILABLE], id="comparison"),
        pytest.param("o.v is not None", [_UNAVAILABLE], id="null_test"),
        pytest.param("inc(o.v) == orders.id", [_UNAVAILABLE], id="def_argument"),
        pytest.param(
            "upper(o.v)",
            [("PIE-S2202", "Expected Bool expression in JOIN ON", 21, 21)],
            id="known_not_bool",
        ),
        pytest.param(
            'o.v == orders.id and orders.id == "x"',
            [
                (
                    "PIE-S2105",
                    "Invalid operands for operator ==: expected comparable operands",
                    21,
                    42,
                )
            ],
            id="operand_error",
        ),
        pytest.param("o.w == orders.id", [], id="known_field"),
    ),
)
def test_single_file_join_on_that_reads_a_field_of_unknown_type_is_refused(
    condition: str, expected: list[tuple[str, str, int, int]]
) -> None:
    run = run_joins(
        JOIN_PREFIX + "query q:\n    from orders\n    let o = odd\n"
        f"    inner join o on {condition}\n"
        "    select:\n        x = orders.id\n"
        "table odd:\n    from orders\n    select:\n        v = orders.id\n"
        "        w = orders.id\n"
        "def inc(x: Int) -> Int | None: return x + 1\n"
    )
    odd = run.relation("odd")
    unknown = ResolvedType("<unknown>", TypeKind.UNKNOWN)
    integer = ResolvedType("Int", TypeKind.BUILTIN)
    rows = {
        **run.model.relation_row_schemas,
        odd: RowSchema(
            fields={
                "v": RowField("v", unknown, EffectiveNullability.UNKNOWN),
                "w": RowField("w", integer, EffectiveNullability.NON_NULL),
            }
        ),
    }
    checks, _ = run.checks(rows)
    # One diagnostic per `on`: a known non-Bool type or an operand error
    # inside it is reported instead of the unknown type.
    assert located(checks.diagnostics) == expected
    assert checks.reads == ()
    assert list(checks.facts) == ([] if expected else [run.relation("q")])
    assert isinstance(run.relation("q"), QueryDef)


_N = EffectiveNullability.NULLABLE.value
_NN = EffectiveNullability.NON_NULL.value


@pytest.mark.parametrize(
    ("join", "proven"),
    (
        pytest.param(
            "orders.customer_id == c.id and c.region_id is not None and c.active",
            {"orders.customer_id", "c.region_id", "c.active"},
            id="comparison_null_test_and_bool_field",
        ),
        pytest.param(
            "orders.customer_id == c.id or c.active",
            set(),
            id="disjunction",
        ),
        pytest.param(
            "orders.customer_id > 0",
            {"orders.customer_id"},
            id="earlier_input_against_a_literal",
        ),
        pytest.param(
            "c.region_id is None",
            set(),
            id="null_test",
        ),
        pytest.param(
            "order_customer(orders, c) and c.region_id > 0",
            {"orders.customer_id", "c.region_id"},
            id="relationship_and_on",
        ),
    ),
)
def test_single_file_inner_join_proofs_make_fields_non_null(
    join: str, proven: set[str]
) -> None:
    run = run_joins(
        JOIN_PREFIX
        + "query q:\n    from orders\n    let c = customers\n"
        + f"    inner join c on {join}\n"
        + "    select:\n        x = orders.id\n"
    )
    rows = run.rows("q")
    assert rows is not None
    nullable = {"orders.customer_id", "c.region_id", "c.active"} - proven
    assert {
        key for key, field in rows.tail.fields.items() if field.nullability.value == _N
    } == nullable
    assert all(
        field.nullability.value == _NN
        for key, field in rows.tail.fields.items()
        if key not in nullable
    )


def test_single_file_join_proof_needs_one_binding_for_its_field() -> None:
    run = run_joins(
        JOIN_PREFIX + "query q:\n    from customers\n"
        "    let peer = customers\n"
        "    inner join peer on region_id is not None\n"
        "    select:\n        x = customers.id\n"
    )
    rows = run.rows("q")
    assert rows is not None
    assert (
        rows.tail.fields["customers.region_id"].nullability.value,
        rows.tail.fields["peer.region_id"].nullability.value,
    ) == (_N, _N)


def test_project_predicate_adapter_keeps_every_call_and_its_exact_row_occurrences(
    tmp_path: Path,
) -> None:
    from pietto.ast_nodes import ComparisonExpr, JoinOnClause, SelectItem, WhereClause

    completed = _completed(
        tmp_path,
        "shape Row:\n"
        "    id: Int\n"
        'source lhs: Row = postgres.table("lhs")\n'
        'source rhs: Row = postgres.table("rhs")\n'
        "relationship Same(a: Row, b: Row):\n"
        "    a.id == b.id\n"
        "query result:\n"
        "    from lhs\n"
        "    inner join rhs on Same(lhs, rhs) and Same(lhs, rhs)\n"
        "    where Same(lhs, rhs) or not Same(lhs, rhs)\n"
        "    select matched = Same(lhs, rhs), id = lhs.id\n",
    )
    root = completed.roots.join_conditions
    records = root.predicate_expressions
    assert [type(item.context) for item in records] == [
        JoinOnClause,
        WhereClause,
        SelectItem,
        SelectItem,
    ]
    assert [len(item.calls) for item in records] == [2, 2, 1, 0]
    assert [call.ordinal for item in records for call in item.calls] == list(range(5))
    condition = root.entries[0]
    assert condition.ready
    assert condition.expression is records[0].expression
    assert condition.expression is not records[0].authored
    assert len(condition.references) == 4
    for record in records:
        for call, bindings in zip(record.calls, record.argument_bindings, strict=True):
            assert bindings == condition.ledger.bindings
            assert all(
                isinstance(binding, ProjectRelationBindingOccurrence)
                and argument.occurrence is binding.site
                for argument, binding in zip(call.arguments, bindings, strict=True)
            )
            if type(record.context) is JoinOnClause:
                assert len(call.mandatory_equalities) == 1
                assert isinstance(call.mandatory_equalities[0], ComparisonExpr)
            else:
                assert call.mandatory_equalities == ()


def test_project_predicate_uses_current_outer_join_nullability(tmp_path: Path) -> None:
    completed = _completed(
        tmp_path,
        "shape Row:\n"
        "    id: Int\n"
        "    active: Bool\n"
        'source lhs: Row = postgres.table("lhs")\n'
        'source rhs: Row = postgres.table("rhs")\n'
        'source last: Row = postgres.table("last")\n'
        "relationship Active(row: Row):\n"
        "    row.active\n"
        "query result:\n"
        "    from lhs\n"
        "    left join rhs on lhs.id == rhs.id\n"
        "    inner join last on Active(rhs)\n"
        "    select id = lhs.id\n",
    )
    fact = completed.roots.join_conditions.entries[1]
    assert fact.ready
    assert fact.value_type is not None
    assert fact.value_type.nullability is EffectiveNullability.NULLABLE
    (reference,) = fact.references
    assert reference.target is not None
    assert reference.target.binding is fact.ledger.bindings[1]
    assert reference.target.value_type.nullability is EffectiveNullability.NULLABLE
    record = fact.environment.predicate_expression
    assert record is not None
    assert record.argument_bindings == ((fact.ledger.bindings[1],),)


def test_project_tail_any_captures_checked_let_before_inner_field_shadowing(
    tmp_path: Path,
) -> None:
    from pietto.ast_nodes import DottedNameExpr
    from pietto._project.existence_values import ProjectAnyLetValue
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectConcreteNoJoinReplay,
    )

    completed = _completed(
        tmp_path,
        "shape Order:\n    id: Int\n    threshold: Int | None\n"
        "shape Customer:\n    id: Int\n    customers: Int\n"
        'source orders: Order = postgres.table("orders")\n'
        'source customers: Customer = postgres.table("customers")\n'
        "query result:\n    from orders\n"
        "    let customers = orders.threshold\n"
        "    where any(buyer.id > customers for buyer in customers)\n"
        "    select id = orders.id\n",
    )
    assert completed.ok, completed.diagnostics
    assert completed.roots.join_conditions.entries == ()
    entry = next(
        item
        for item in completed.effective_outputs.entries
        if item.owner.definition.name == "result"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    assert isinstance(entry.root, ProjectConcreteNoJoinReplay)
    analysis = entry.root.where.expression_analysis
    assert analysis is not None
    (value,) = analysis.existence_values
    (capture,) = value.captures
    target = capture.target
    assert isinstance(target, ProjectAnyLetValue)
    assert target.binding is analysis.let_scope.bindings[0]
    assert isinstance(capture.expression, NameExpr)
    assert target.binding.name == capture.expression.name == "customers"
    assert target.value_type.nullability is EffectiveNullability.NULLABLE
    assert isinstance(target.expression, DottedNameExpr)
    assert target.expression.parts == ("orders", "threshold")
    assert value.input.binding.name == "buyer"


def test_project_any_in_join_on_retains_nullable_prefix_capture(tmp_path: Path) -> None:
    from pietto._project.existence_values import ProjectAnyField

    completed = _completed(
        tmp_path,
        "shape Row:\n    id: Int\n"
        'source lhs: Row = postgres.table("lhs")\n'
        'source rhs: Row = postgres.table("rhs")\n'
        'source last: Row = postgres.table("last")\n'
        'source candidates: Row = postgres.table("candidates")\n'
        "relationship Same(a: Row, b: Row):\n    a.id == b.id\n"
        "query result:\n    from lhs\n"
        "    left join rhs on lhs.id == rhs.id\n"
        "    inner join last on any(Same(rhs, candidate) for candidate in candidates) or last.id == lhs.id\n"
        "    select id = lhs.id\n",
    )
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[1]
    assert condition.ready
    (value,) = condition.environment.existence_values
    assert value.predicate is not value.authored_expression.predicate
    (capture,) = value.captures
    target = capture.target
    assert isinstance(target, ProjectAnyField)
    source_field = target.source_field
    assert source_field is next(
        field
        for field in condition.environment.fields
        if field.binding is condition.ledger.bindings[1]
        and field.input_field.evidence.name == "id"
    )
    assert target.binding is condition.ledger.bindings[1]
    assert target.value_type.nullability is EffectiveNullability.NULLABLE
    assert value.value_type.nullability is EffectiveNullability.NON_NULL
    assert value.input.binding.name == "candidate"
    assert all(field.binding is value.input.binding for field in value.fields)


def test_project_any_in_where_or_and_select_keeps_binder_occurrences_local(
    tmp_path: Path,
) -> None:
    from pietto._project.existence_values import ProjectAnyField
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
    from pietto._project.project_scalar_namespaces import (
        ProjectConcreteJoinedNamespaceExpression,
    )

    completed = _completed(
        tmp_path,
        "shape Row:\n    id: Int\n"
        'source lhs: Row = postgres.table("lhs")\n'
        'source rhs: Row = postgres.table("rhs")\n'
        'source candidates: Row = postgres.table("candidates")\n'
        "query result:\n    from lhs\n"
        "    left join rhs on lhs.id == rhs.id\n"
        "    where any(candidate.id == rhs.id for candidate in candidates) or lhs.id > 0\n"
        "    select matched = any(candidate.id == rhs.id for candidate in candidates) or any(candidate.id == lhs.id for candidate in candidates)\n",
    )
    assert completed.ok, completed.diagnostics
    output = next(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == "result"
    )
    assert isinstance(output, ProjectCompletedEffectiveOutput)
    source = output.fields[0].source
    assert isinstance(source, ProjectConcreteJoinedNamespaceExpression)
    first, second = source.existence_values
    assert first.input.binding is not second.input.binding
    assert first.input.binding.name == second.input.binding.name == "candidate"
    assert first.input.binding.target is second.input.binding.target
    assert first.expression is not second.expression
    (first_capture,) = first.captures
    (second_capture,) = second.captures
    first_target, second_target = first_capture.target, second_capture.target
    assert isinstance(first_target, ProjectAnyField)
    assert isinstance(second_target, ProjectAnyField)
    assert first_target.binding is not second_target.binding
    assert isinstance(first_target.binding, ProjectRelationBindingOccurrence)
    assert isinstance(second_target.binding, ProjectRelationBindingOccurrence)
    assert first_target.binding.name == "rhs"
    assert second_target.binding.name == "lhs"
    assert first_target.value_type.nullability is EffectiveNullability.NULLABLE
    assert second_target.value_type.nullability is EffectiveNullability.NON_NULL
    assert first_target.source_field is next(
        field
        for binding in source.namespace.bindings
        if binding.binding is first_target.binding
        for field in binding.fields
        if field.evidence.name == "id"
    )


_UNKNOWN_ON_CALL = """shape Order:
    id: Int
    customer_id: Int | None
shape Customer:
    id: Int
    name: Text
source orders: Order = postgres.table("orders")
source customers: Customer = postgres.table("customers")
query q:
    from orders
    let c = customers
    inner join c on {on}
    select:
        x = orders.id
"""


def _project_located(root: Path, files: dict[str, str], capsys) -> list:
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    return [
        (
            d["code"],
            d["message"],
            d["location"]["path"],
            d["location"]["line"],
            d["location"]["column"],
        )
        for d in json.loads(capsys.readouterr().out)["diagnostics"]
    ]


@pytest.mark.parametrize(
    ("on", "name"),
    (
        ("order_customer(orders, c)", "order_customer"),
        ("lowr(orders) == c.name", "lowr"),
        ("nosuch(orders, c, 1)", "nosuch"),
    ),
)
def test_an_unknown_call_in_on_reports_the_call_not_its_rows(
    tmp_path: Path, capsys, on: str, name: str
) -> None:
    """A bare JOIN input passed to an unknown function, as to a relationship
    the file does not declare, is a row, not an unknown ON reference: the
    call alone is reported (PIE-S2103), in a single file and in a project."""

    source = _UNKNOWN_ON_CALL.format(on=on)
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    message = f"Unknown function: {name}"
    assert located(analyze(parsed.ast).diagnostics) == [("PIE-S2103", message, 12, 21)]
    assert _project_located(tmp_path / "p", {"main.pietto": source}, capsys) == [
        ("PIE-S2103", message, "main.pietto", 12, 21)
    ]


_UNKNOWN_TAIL_CALL = """shape Order:
    id: Int
    customer_id: Int | None
shape Customer:
    id: Int
    name: Text
source orders: Order = postgres.table("orders")
source customers: Customer = postgres.table("customers")
query q_where:
    from orders
    let c = customers
    inner join c on orders.customer_id == c.id
    where order_customer(orders, c)
    select:
        x = orders.id
query q_let:
    from orders
    let c = customers
    inner join c on orders.customer_id == c.id
    let m = order_customer(orders, c)
    select:
        x = orders.id
        m
query q_any:
    from orders
    where any(order_customer(orders, c) for c in customers)
    select:
        x = id
"""


def test_an_unknown_call_in_where_let_or_any_reports_the_call_not_its_rows(
    tmp_path: Path, capsys
) -> None:
    """The callee is resolved before its arguments, in WHERE, a `let` and an
    `any(...)` as in `on`: a call of a relationship the file does not declare
    is PIE-S2103, and its rows are no unknown fields or ANY references, in a
    single file and in a project."""

    parsed = parse_source(_UNKNOWN_TAIL_CALL)
    assert parsed.ast is not None and parsed.diagnostics == ()
    message = "Unknown function: order_customer"
    expected = [
        ("PIE-S2103", message, 13, 11),
        ("PIE-S2103", message, 20, 13),
        ("PIE-S2103", message, 26, 15),
    ]
    assert located(analyze(parsed.ast).diagnostics) == expected
    assert _project_located(
        tmp_path / "p", {"main.pietto": _UNKNOWN_TAIL_CALL}, capsys
    ) == [
        (code, text, "main.pietto", line, column)
        for code, text, line, column in expected
    ]


def test_a_relationship_of_another_module_says_it_cannot_be_imported(
    tmp_path: Path, capsys
) -> None:
    head, query = _UNKNOWN_ON_CALL.split("query q:\n")
    models = (
        head
        + "relationship order_customer(o: Order, c: Customer): o.customer_id == c.id\n"
        + "export (\n    shape Order,\n    shape Customer,\n    source orders,\n"
        + "    source customers)\n"
    )
    main = (
        'from "models.pietto" import (\n    shape Order,\n    shape Customer,\n'
        "    source orders,\n    source customers)\n"
        + "query q:\n"
        + query.format(on="order_customer(orders, c)")
    )
    assert _project_located(
        tmp_path / "p", {"main.pietto": main, "models.pietto": models}, capsys
    ) == [
        (
            "PIE-S2103",
            "Unknown function: order_customer; order_customer is a relationship of "
            "models.pietto, which a module cannot import: declare it in this module",
            "main.pietto",
            9,
            21,
        )
    ]


def test_a_relationship_of_another_module_is_named_in_where_let_and_any(
    tmp_path: Path, capsys
) -> None:
    head, queries = _UNKNOWN_TAIL_CALL.split("query q_where:\n")
    models = (
        head
        + "relationship order_customer(o: Order, c: Customer): o.customer_id == c.id\n"
        + "export (\n    shape Order,\n    shape Customer,\n    source orders,\n"
        + "    source customers)\n"
    )
    main = (
        'from "models.pietto" import (\n    shape Order,\n    shape Customer,\n'
        "    source orders,\n    source customers)\n" + "query q_where:\n" + queries
    )
    message = (
        "Unknown function: order_customer; order_customer is a relationship of "
        "models.pietto, which a module cannot import: declare it in this module"
    )
    assert _project_located(
        tmp_path / "p", {"main.pietto": main, "models.pietto": models}, capsys
    ) == [
        ("PIE-S2103", message, "main.pietto", 10, 11),
        ("PIE-S2103", message, "main.pietto", 17, 13),
        ("PIE-S2103", message, "main.pietto", 23, 15),
    ]
