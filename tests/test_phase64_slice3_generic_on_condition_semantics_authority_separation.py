"""Real authored pre-match conditions without premature JOIN completion."""

from dataclasses import replace
from pathlib import Path
import json

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectNonConcreteJoinUse,
)
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project import project_join_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project.project_relationship_paths import ProjectRelationshipJoinShapeIndex
from pietto._project.model import ProjectRowFieldNullability
from pietto.ast_nodes import AuthoredJoinKind
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.ir import build_ir
from pietto.semantic.model import EffectiveNullability, CheckMode
from pietto import cli


BASE = """shape Row:
    id: Int not null
    key: Int nullable
    allow_any: Bool nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
"""


def _source(predicate: str | None, *, kind: str = "inner", via: str = "") -> str:
    on = "" if predicate is None else f"        on {predicate}\n"
    return (
        BASE
        + f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
{via}{on}    select:
        id = lhs.id
"""
    )


def _completed(root: Path, source: str) -> ProjectConcreteCompletedSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    parsed = check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    result = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    return result


@pytest.mark.parametrize("via", ("", "        via link: l -> r\n"))
def test_old_m1_m2_controls(tmp_path: Path, via: str) -> None:
    completed = _completed(tmp_path, _source(None, via=via))
    assert completed.ok
    uses = completed.verification.root.join_regions.uses
    assert all(isinstance(use, ProjectConcreteJoinUse) for use in uses.uses)


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
    assert fact.base_conditions == () and fact.base_guarantee is None
    assert fact.use.direct_result is None and fact.use.path is None
    assert fact.expression is fact.use.clause.on_clause.expression
    assert not completed.ok and not fact.diagnostics
    assert any(d.code == "PIE-S2334" for d in completed.diagnostics)


def test_refinement_keeps_base_and_conjunct_occurrences(tmp_path: Path) -> None:
    completed = _completed(
        tmp_path,
        _source("r.key > 0 and r.key > 0", via="        via link: l -> r\n"),
    )
    fact = completed.roots.join_conditions.entries[0]
    assert fact.ready and fact.mode == "M4"
    assert fact.scope is not None and fact.refinement_guarantee is not None
    assert fact.scope.value == "join_local_on_refinement"
    assert len(fact.base_conditions) == 1
    assert len(fact.conjuncts) == 2
    assert fact.conjuncts[0] is not fact.conjuncts[1]
    assert fact.base_conditions[0].clause.expression is not fact.expression
    assert fact.refinement_guarantee.base is fact.base_guarantee


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


def test_generic_never_calls_relationship_discovery(
    tmp_path: Path, monkeypatch
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Generic ON called relationship discovery")

    monkeypatch.setattr(ProjectRelationshipJoinShapeIndex, "resolve_direct", forbidden)
    result = _completed(tmp_path, _source("lhs.id == r.id"))
    assert result.roots.join_conditions.entries[0].ready


@pytest.mark.parametrize("kind", tuple(AuthoredJoinKind))
@pytest.mark.parametrize("via", ("", "        via link: l -> r\n"))
@pytest.mark.parametrize("on", (None, "lhs.id == r.id"))
def test_mode_kind_dispatch_keeps_operation_admission_closed(
    tmp_path: Path, kind, via, on
) -> None:
    completed = _completed(tmp_path, _source(on, kind=kind.value, via=via))
    fact = completed.roots.join_conditions.entries[0]
    bad_cross = kind is AuthoredJoinKind.CROSS and bool(via or on)
    assert fact.ready is not bad_cross
    assert fact.use.clause.kind is kind
    assert any(d.code == "PIE-S2336" for d in fact.diagnostics) is bad_cross
    old = kind in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT} and on is None
    assert completed.ok is old
    if not old:
        assert not isinstance(fact.use, ProjectConcreteJoinUse)
        assert not completed.verification.root.join_regions.structural.nodes
    if kind is AuthoredJoinKind.CROSS:
        assert fact.mode == "M5" and not fact.base_conditions


@pytest.mark.parametrize("kind", tuple(AuthoredJoinKind))
@pytest.mark.parametrize("on", (None, "lhs.id == r.id"))
def test_multi_hop_combination_rules(tmp_path: Path, kind, on) -> None:
    # A real contiguous round trip; only old INNER/LEFT without ON may admit it.
    source = _source(
        on, kind=kind.value, via="        via link: l -> r\n        via link: r -> l\n"
    )
    source = source.replace(
        f"{kind.value} join rhs as r:", f"{kind.value} join lhs as r:"
    )
    completed = _completed(tmp_path, source)
    fact = completed.roots.join_conditions.entries[0]
    allowed = kind in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT} and on is None
    assert fact.ready is allowed
    assert any(d.code == "PIE-S2336" for d in fact.diagnostics) is not allowed


@pytest.mark.parametrize(
    "predicate, proofs",
    (
        ("r.key is null", 0),
        ("r.key is not null", 1),
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
    source = _source("r.id == last.id", kind="left")
    source = source.replace(
        "    left join rhs as r:",
        f"    {kind} join rhs as r:\n        from lhs\n        via link: l -> r\n    left join rhs as last:",
    )
    completed = _completed(tmp_path, source)
    first, current = completed.roots.join_conditions.entries
    assert first.ready and current.ready
    left, right = (reference.target for reference in current.references)
    assert left is not None and right is not None
    assert isinstance(first.use, ProjectConcreteJoinUse)
    assert left.binding is first.use.target_binding
    expected = (
        ProjectRowFieldNullability.NULLABLE
        if kind == "left"
        else ProjectRowFieldNullability.NON_NULL
    )
    assert left.nullability is expected
    assert bool(left.null_extensions) is (kind == "left")
    if kind == "left":
        assert left.null_extensions[0] is first.use.path.steps[0]
    assert right.nullability is ProjectRowFieldNullability.NON_NULL
    assert not completed.verification.root.join_regions.structural.nodes


def test_c03_exact_upper_bound_survives_but_coverage_does_not(tmp_path: Path) -> None:
    source = _source("r.key > 0", kind="left", via="        via link: l -> r\n")
    source = source.replace(
        "    allow_any: Bool nullable\n",
        "    allow_any: Bool nullable\n    unique id_key on id\n",
    )
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    base, refined = fact.base_guarantee, fact.refinement_guarantee
    assert base is not None and refined is not None
    assert refined.base is base
    assert base.maximum is guarantees.ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert refined.maximum_evidence is base.maximum_evidence
    condition = fact.base_conditions[0]
    correspondence = condition.correspondences[0]
    coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=base.direction,
        correspondences=condition.correspondences,
        source_scope=correspondence.endpoint_zero.constraint_scope,
        target_scope=correspondence.endpoint_one.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    proven = guarantees.derive_directional_match_guarantee(
        base.direction, condition, base.source_output, base.target_output, coverage
    )
    narrowed = guarantees.ProjectRefinedMatchBounds(base=proven)
    assert proven.minimum is guarantees.ProjectRelationshipMinimumBound.AT_LEAST_ONE
    assert narrowed.minimum is guarantees.ProjectRelationshipMinimumBound.ZERO_ALLOWED
    assert narrowed.maximum_evidence is proven.maximum_evidence
    assert proven.coverage is coverage


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
        "inner join rhs as r", "inner join lhs as r"
    )
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    left, right = (reference.target for reference in fact.references)
    assert left is not None and right is not None
    assert fact.ready and left.binding is not right.binding
    assert left.input_field is right.input_field
    assert left is not right


def test_duplicate_alias_is_not_resolved_by_field_or_type(tmp_path: Path) -> None:
    source = _source("lhs.id == lhs.id").replace("as r:", "as lhs:")
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready
    assert all(
        ref.state.value == "ambiguous" and len(ref.binding_candidates) == 2
        for ref in fact.references
    )


def test_later_binding_reference_is_forward(tmp_path: Path) -> None:
    source = _source("later.id == r.id").replace(
        "    select:\n",
        "    inner join rhs as later:\n        from lhs\n        on lhs.id == later.id\n    select:\n",
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
        "    let:\n        local = lhs.id\n    select:\n        projected = lhs.id\n",
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
    ).replace("        from lhs\n        on", "        from view\n        on")
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
def test_single_file_check_and_direct_legacy_ir_remain_negative(
    mode: CheckMode,
) -> None:
    parsed = parse_source(_source("lhs.id == r.id"))
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast, mode_override=mode)
    assert any(d.code == "PIE-S2334" for d in semantic.diagnostics)
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is None
    assert any(d.code == "PIE-I1000" for d in lowered.diagnostics)


def test_duplicate_alias_retains_all_available_field_candidates(tmp_path: Path) -> None:
    source = _source("lhs.id == lhs.id").replace("as r:", "as lhs:")
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    for reference in fact.references:
        assert reference.state.value == "ambiguous"
        assert len(reference.candidates) == 2
        assert (
            tuple(item.binding for item in reference.candidates)
            == fact.environment.bindings
        )


def test_old_noncontiguous_path_does_not_gain_condition_readiness(
    tmp_path: Path,
) -> None:
    source = _source(None, via="        via link: l -> r\n        via link: l -> r\n")
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready
    assert not fact.diagnostics


@pytest.mark.parametrize("predicate", ("row_number() window ordered", "rn < 2"))
def test_window_and_current_window_alias_are_unavailable(
    tmp_path: Path, predicate: str
) -> None:
    source = (
        _source(predicate)
        + "        rn = row_number() window ordered\n    window ordered:\n        order by:\n            lhs.id\n"
    )
    if predicate == "row_number() window ordered":
        parsed = parse_source(source)
        assert parsed.ast is None
        assert parsed.diagnostics[0].code == "PIE-P1000"
        return
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready and fact.diagnostics


def test_unknown_project_field_type_is_unavailable(tmp_path: Path) -> None:
    source = "enum Identifier:\n    first\n    second\n" + _source(
        "lhs.key == r.key"
    ).replace("key: Int nullable", "key: Identifier nullable")
    fact = _completed(tmp_path, source).roots.join_conditions.entries[0]
    assert not fact.ready
    assert all(ref.state.value == "unavailable" for ref in fact.references)
    assert all(
        len(ref.candidates) == 1 and ref.target is None for ref in fact.references
    )


def test_set_input_and_independent_valid_branches_survive(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id")
    source = source.replace(
        "query result:\n",
        "table combined:\n    union all:\n        from lhs\n        from rhs\nquery result:\n",
    ).replace("inner join rhs as r:", "inner join combined as r:")
    source += "query valid:\n    from lhs\n    select:\n        id\n"
    result = _completed(tmp_path, source)
    fact = result.roots.join_conditions.entries[0]
    assert not fact.ready and fact.references[1].state.value == "unavailable"
    entries = {
        entry.owner.definition.name: entry for entry in result.effective_outputs.entries
    }
    combined, valid = entries["combined"], entries["valid"]
    assert isinstance(combined, ProjectEffectiveOutputTerminal)
    assert isinstance(valid, ProjectExistingEffectiveOutput)
    assert combined.output is None and combined.dependencies == ()
    assert valid.output is not None


def test_join_effective_input_stays_unavailable_before_slice4(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id").replace("query result:", "table joined:")
    source += "query downstream:\n    from joined\n    inner join rhs as last:\n        from joined\n        on joined.id == last.id\n    select:\n        id = joined.id\n"
    facts = _completed(tmp_path, source).roots.join_conditions.entries
    assert facts[0].ready and not facts[1].ready
    assert facts[1].references[0].state.value == "unavailable"


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("schema", (1, 2))
def test_project_check_modes_do_not_admit_ready_conditions(
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
    assert not result.ok and any(d.code == "PIE-S2334" for d in result.diagnostics)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_public_sql_check_negatives_and_no_partial_artifact(
    tmp_path: Path, capsys, dialect: str, mode: CheckMode
) -> None:
    path = tmp_path / "main.pietto"
    path.write_text(
        f"mode {mode.value}\n"
        + _source("lhs.id == r.id").replace("postgres.table", f"{dialect}.table")
    )
    for command in (
        ["check", str(path), "--format", "json"],
        ["emit-sql", str(path), "--dialect", dialect, "--format", "json"],
    ):
        assert cli.main(command) == 1
        captured = capsys.readouterr()
        assert not captured.err
        document = json.loads(captured.out)
        assert not document["ok"] and not document.get("artifacts", [])
        assert any(d["code"] == "PIE-S2334" for d in document["diagnostics"])


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
        "does not use project source selection" in error.message
        for error in parsed.errors
    )
