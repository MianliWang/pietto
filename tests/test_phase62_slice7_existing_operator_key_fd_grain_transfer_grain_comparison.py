from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain as grain
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_row_keys as row_keys
from pietto._project import project_value_fds as value_fds
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)
from pietto.semantic.model import SemanticModel

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md"
)


def _semantic(root: Path, source: str | None = None) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(
        source
        or """shape Row:
    id: Int not null
    category: Text nullable
    amount: Int nullable
    unique id_key on id
source rows: Row is postgres.table("rows")
shape Loose:
    value: Int nullable
source unkeyed: Loose is postgres.table("loose")
shape Pair:
    a: Int not null
    b: Int not null
    unique pair_key on a, b
source pairs: Pair is postgres.table("pairs")
query aliases:
    from rows
    select:
        id_a = id
        id_b = id
        computed = id + 1
        category_alias = category
query pair_aliases:
    from pairs
    select:
        a_one = a
        a_two = a
        b_one = b
        b_two = b
query filtered:
    from rows
    where id > 0
    select:
        id
        category
        amount
    order by:
        id
    limit 1
query grouped:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
query grouped_by_id:
    from rows
    group by:
        id
    select:
        id
        total = sum(amount)
query grouped_other:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
query global_total:
    from rows
    select:
        total = sum(amount)
""",
        encoding="utf-8",
    )
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    return build_empty_project_semantic_result(parsed)


def _stage(
    root: Path, source: str | None = None
) -> relational.ProjectIRRelationalPropertyStage:
    semantic = _semantic(root, source)
    keys = row_keys.build_project_row_keys(semantic)
    fds = value_fds.build_project_value_fds(keys)
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = grain.build_project_grain_origins(fds, evaluation)
    analyses = build_project_ir_analysis_bundle(verify_project_ir_stage(evaluation))
    return relational.build_project_ir_relational_property_stage(origins, analyses)


def _outputs(stage, name):
    return tuple(
        item
        for item in stage.outputs
        if item.output.row_shape.relation.identity.identity.declared_name == name
    )


def test_stage_covers_verified_topological_outputs(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    assert stage.origins.evaluation is stage.analyses.stage
    assert (
        tuple(item.output.occurrence.producer for item in stage.outputs)
        == stage.analyses.topological_order
    )


def test_source_and_unary_outputs_transfer_keys_fds_and_grain(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    rows = _outputs(stage, "rows")
    assert len(rows) == 1 and rows[0].keys and rows[0].fds
    filtered = _outputs(stage, "filtered")
    assert filtered
    assert filtered[-1].keys
    assert filtered[-1].grain.state is grain.ProjectGrainBasisState.FACTORIZED
    assert filtered[-1].grain.active == rows[0].grain.active
    assert not any(not key.determinants for item in filtered for key in item.keys)
    unkeyed = _outputs(stage, "unkeyed")[0]
    assert unkeyed.keys == () and unkeyed.grain.active


def test_group_and_global_replace_active_grain_without_empty_keys(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    grouped = _outputs(stage, "grouped")
    group_output = grouped[-1]
    assert group_output.keys[0].strength is row_keys.ProjectRowUniquenessStrength.STRICT
    assert group_output.grain.dependencies
    assert len(group_output.grain.active) == 1
    source_grain = _outputs(stage, "rows")[0].grain
    comparison = relational.compare_project_ir_grain(source_grain, group_output.grain)
    assert comparison.status is relational.ProjectIRGrainComparisonStatus.LEFT_FINER
    assert (
        comparison.left_to_right.status
        is relational.ProjectIRGrainDirectionStatus.PROVEN
    )
    assert (
        comparison.right_to_left.status
        is relational.ProjectIRGrainDirectionStatus.NOT_PROVEN
    )
    reverse = relational.compare_project_ir_grain(group_output.grain, source_grain)
    assert reverse.status is relational.ProjectIRGrainComparisonStatus.RIGHT_FINER
    strict_group = _outputs(stage, "grouped_by_id")[-1]
    assert (
        relational.compare_project_ir_grain(source_grain, strict_group.grain).status
        is relational.ProjectIRGrainComparisonStatus.EQUAL
    )
    independent = relational.compare_project_ir_grain(
        group_output.grain, _outputs(stage, "grouped_other")[-1].grain
    )
    assert independent.status is relational.ProjectIRGrainComparisonStatus.INCOMPARABLE
    assert (
        independent.left_to_right.status
        is independent.right_to_left.status
        is (relational.ProjectIRGrainDirectionStatus.NOT_PROVEN)
    )
    assert independent.left_to_right.witness == independent.right_to_left.witness == ()
    global_output = _outputs(stage, "global_total")[-1]
    assert global_output.grain.state is grain.ProjectGrainBasisState.GLOBAL
    assert global_output.grain.active == ()
    assert global_output.keys == () and global_output.fds == ()
    factorized_global = relational.compare_project_ir_grain(
        group_output.grain, global_output.grain
    )
    assert (
        factorized_global.status is relational.ProjectIRGrainComparisonStatus.LEFT_FINER
    )
    assert factorized_global.left_to_right.witness == ()
    global_comparison = relational.compare_project_ir_grain(
        global_output.grain, global_output.grain
    )
    assert global_comparison.status is relational.ProjectIRGrainComparisonStatus.EQUAL
    assert global_comparison.left_to_right.witness == ()


def test_comparison_vocabulary_and_public_boundaries_are_unchanged(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    same = relational.compare_project_ir_grain(
        stage.outputs[0].grain, stage.outputs[0].grain
    )
    assert same.status is relational.ProjectIRGrainComparisonStatus.EQUAL
    assert (
        same.left_to_right.status
        is same.right_to_left.status
        is (relational.ProjectIRGrainDirectionStatus.PROVEN)
    )
    assert same.left_to_right.seed.domain is same.right_to_left.seed.domain
    assert tuple(relational.ProjectIRGrainComparisonStatus) == (
        relational.ProjectIRGrainComparisonStatus.EQUAL,
        relational.ProjectIRGrainComparisonStatus.LEFT_FINER,
        relational.ProjectIRGrainComparisonStatus.RIGHT_FINER,
        relational.ProjectIRGrainComparisonStatus.INCOMPARABLE,
        relational.ProjectIRGrainComparisonStatus.UNKNOWN,
        relational.ProjectIRGrainComparisonStatus.CONFLICT,
    )
    assert relational.__all__ == ()
    assert "relational_properties" not in {
        item.name for item in fields(ProjectSemanticResult)
    }
    assert "relational_properties" not in {item.name for item in fields(SemanticModel)}


def test_alias_classes_are_complete_factorized_and_computed_values_are_distinct(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    aliases = _outputs(stage, "aliases")[-1]
    key = aliases.keys[0]
    assert len(key.determinants) == 1
    assert tuple(member.field_position for member in key.determinants[0].members) == (
        0,
        1,
    )
    assert all(
        value_class is not key.determinants[0]
        for value_class in aliases.value_classes
        if any(member.field_position == 2 for member in value_class.members)
    )
    pair = _outputs(stage, "pair_aliases")[-1]
    assert len(pair.keys) == 1
    assert tuple(len(item.members) for item in pair.keys[0].determinants) == (2, 2)


def test_comparison_witness_is_indexed_replayable_and_normative_ordered(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    source = _outputs(stage, "rows")[0].grain
    grouped = _outputs(stage, "grouped")[-1].grain
    other = _outputs(stage, "grouped_other")[-1].grain
    a, b, c = source.active[0], grouped.active[0], other.active[0]
    all_factors = (*source.factors, *grouped.factors[-1:], *other.factors[-1:])
    first = grain.ProjectGrainDependencyFact(determinants=(b,), dependents=(c,))
    second = grain.ProjectGrainDependencyFact(determinants=(a,), dependents=(c,))
    left = replace(
        source,
        factors=all_factors,
        active=(a, b),
        dependencies=(first, second),
    )
    right = replace(other, factors=all_factors, active=(c,), dependencies=())
    comparison = relational.compare_project_ir_grain(left, right)
    direction = comparison.left_to_right
    assert direction.status is relational.ProjectIRGrainDirectionStatus.PROVEN
    assert tuple(step.fact for step in direction.witness) == (first,)
    assert direction.closure.factors == (a, b, c)
    reversed_seed = relational.compare_project_ir_grain(
        replace(left, active=(b, a)), right
    ).left_to_right
    assert tuple(step.fact for step in reversed_seed.witness) == (first,)
    with pytest.raises(ValueError, match="replay the indexed fixed point"):
        replace(direction, witness=())
    with pytest.raises(ValueError, match="replay the indexed fixed point"):
        replace(
            direction,
            witness=(replace(direction.witness[0], derived=(b,)),),
        )

    chain_first = grain.ProjectGrainDependencyFact(determinants=(a,), dependents=(b,))
    chain_second = grain.ProjectGrainDependencyFact(determinants=(b,), dependents=(c,))
    chain = relational.compare_project_ir_grain(
        replace(left, active=(a,), dependencies=(chain_first, chain_second)), right
    ).left_to_right
    assert tuple(step.fact for step in chain.witness) == (chain_first, chain_second)
    with pytest.raises(ValueError, match="replay the indexed fixed point"):
        replace(chain, witness=tuple(reversed(chain.witness)))

    foreign = relational.compare_project_ir_grain(source, grouped).left_to_right
    with pytest.raises(ValueError, match="one exact comparison domain"):
        replace(direction, seed=foreign.seed)

    composite = grain.ProjectGrainDependencyFact(determinants=(a, b), dependents=(c,))
    assert (
        relational.compare_project_ir_grain(
            replace(left, dependencies=(composite,)), right
        ).left_to_right.status
        is relational.ProjectIRGrainDirectionStatus.PROVEN
    )
    assert (
        relational.compare_project_ir_grain(
            replace(left, active=(a,), dependencies=(composite,)), right
        ).left_to_right.status
        is relational.ProjectIRGrainDirectionStatus.NOT_PROVEN
    )

    cycle = grain.ProjectGrainDependencyFact(determinants=(c,), dependents=(a,))
    cyclic = replace(left, active=(a,), dependencies=(second, cycle))
    assert (
        relational.compare_project_ir_grain(cyclic, right).left_to_right.status
        is relational.ProjectIRGrainDirectionStatus.PROVEN
    )


def test_output_fd_index_strict_closure_lax_boundary_and_witness_order(
    tmp_path: Path,
) -> None:
    output = _outputs(_stage(tmp_path), "filtered")[-1]
    a, b, c = output.value_classes
    strict_ab = relational.ProjectIROutputValueFD(
        output=output.output,
        determinants=(a,),
        dependents=(b,),
        strength=row_keys.ProjectRowUniquenessStrength.STRICT,
        supports=(output,),
    )
    strict_bc = relational.ProjectIROutputValueFD(
        output=output.output,
        determinants=(b,),
        dependents=(c,),
        strength=row_keys.ProjectRowUniquenessStrength.STRICT,
        supports=(output,),
    )
    lax_ac = relational.ProjectIROutputValueFD(
        output=output.output,
        determinants=(a,),
        dependents=(c,),
        strength=row_keys.ProjectRowUniquenessStrength.LAX,
        supports=(output,),
    )
    index = relational._compile_output_fd_index(
        output.output, output.value_classes, (strict_ab, strict_bc, lax_ac)
    )
    seed = relational.ProjectIROutputValueClassSet(index=index, classes=(a,))
    requested = relational.ProjectIROutputValueClassSet(index=index, classes=(c,))
    result = relational.strictly_determines_output(index, seed, requested)
    assert result.status is relational.ProjectIROutputDeterminationStatus.PROVEN
    assert tuple(step.fact for step in result.closure.witness) == (
        strict_ab,
        strict_bc,
    )
    assert index.lax_rules[0].fact is lax_ac
    with pytest.raises(ValueError, match="exact output-local universe"):
        relational.strict_output_fd_closure(output.fd_index, seed)


def test_output_fd_masks_support_more_than_seventy_value_classes(
    tmp_path: Path,
) -> None:
    fields_source = "".join(
        f"    f{position}: Int not null\n" for position in range(72)
    )
    stage = _stage(
        tmp_path,
        "shape Wide:\n"
        + fields_source
        + 'source wide: Wide is postgres.table("wide")\n',
    )
    wide = _outputs(stage, "wide")[0]
    assert len(wide.fd_index.universe) == 72
    all_classes = relational.ProjectIROutputValueClassSet(
        index=wide.fd_index,
        classes=wide.value_classes,
    )
    assert all_classes.mask.bit_count() == 72

    sources = "".join(
        f'source rows_{position}: Wide is postgres.table("rows_{position}")\n'
        for position in range(72)
    )
    comparison_stage = _stage(
        tmp_path / "comparison", "shape Wide:\n" + fields_source + sources
    )
    grains = tuple(
        _outputs(comparison_stage, f"rows_{position}")[0].grain
        for position in range(72)
    )
    factors = tuple(item.active[0] for item in grains)
    domain_factors = tuple(item.factors[0] for item in grains)
    dependency = grain.ProjectGrainDependencyFact(
        determinants=(factors[0],), dependents=(factors[-1],)
    )
    left = replace(
        grains[0],
        factors=domain_factors,
        active=(factors[0],),
        dependencies=(dependency,),
    )
    right = replace(
        grains[-1], factors=domain_factors, active=(factors[-1],), dependencies=()
    )
    comparison = relational.compare_project_ir_grain(left, right)
    assert len(comparison.domain.factors) == 72
    assert comparison.domain.rules[0].rhs_mask == 1 << 71
    assert (
        comparison.left_to_right.status
        is relational.ProjectIRGrainDirectionStatus.PROVEN
    )


def test_contract_locks_transfer_comparison_and_handoff() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "88dbfb51a35504b0b753e299c6c90b6303a8e450",
        "724f2b8ce113bf01072e83f7cd4792cae4a9d8be",
        "33491899112",
        "A3/M5/D0",
        "ProjectIRAnalysisBundle.topological_order",
        "LIMIT 1 does not create GLOBAL grain",
        "ProjectIRProvidedLocalGrainEvidence remains unchanged",
        "Phase 62 Slice 8 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 key FD grain transfer and comparison",
    ):
        assert evidence in normalized
