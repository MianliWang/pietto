from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project import project_grain as grain
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
    ProjectIRAggregateEvaluationContext,
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_properties import ProjectIRProvidedLocalGrainEvidence
from pietto.ast_nodes import NameExpr, SourceDef
from pietto.semantic.model import SemanticModel


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_grain.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Grain States And Origin Boundaries",
    "Source-domain Identity And Witness",
    "Grouped And GLOBAL Authority",
    "GrainBasis And Domain Factors",
    "Typed Grain-dependency Kernel",
    "Optional-factor Readiness",
    "Phase-61 Local-grain Separation",
    "Completeness And Non-concrete Isolation",
    "Compatibility And Production Delta",
    "Focused Assurance",
    "Slice 7 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    category: Text nullable
    amount: Int nullable
    unique id_key on id
source rows_one: Row is postgres.table("rows_one")
source rows_two: Row is postgres.table("rows_two")
shape NoKey:
    plain: Int nullable
source unkeyed_rows: NoKey is postgres.table("unkeyed")
shape Broken:
    broken: MissingType not null
source broken_rows: Broken is postgres.table("broken")
query grouped_one:
    from rows_one
    group by:
        category
    select:
        category
        total = sum(amount)
query grouped_two:
    from rows_one
    group by:
        category
    select:
        category
        total = sum(amount)
query global_total:
    from rows_one
    select:
        total = sum(amount)
query plain_projection:
    from rows_one
    select:
        id
query filtered_limited:
    from rows_one
    where id > 0
    select:
        id
    order by:
        id
    limit 1
query broken_group:
    from rows_one
    group by:
        missing
    select:
        missing
"""


def _semantic_project(root: Path, source: str | None = None) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(source or _source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    return build_empty_project_semantic_result(parsed)


def _grain(root: Path, source: str | None = None) -> grain.ProjectGrainOriginSet:
    semantic = _semantic_project(root, source)
    keys = row_keys.build_project_row_keys(semantic)
    fds = value_fds.build_project_value_fds(keys)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    stage = build_project_ir_evaluation_context_stage(plan)
    return grain.build_project_grain_origins(fds, stage)


def _origin(
    result: grain.ProjectGrainOriginSet,
    name: str,
) -> grain.ProjectConcreteGrainOrigin:
    matches = tuple(
        origin
        for origin in result.origins
        if origin.identity.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def test_concrete_sources_create_distinct_required_intrinsic_domains(
    tmp_path: Path,
) -> None:
    result = _grain(tmp_path)
    assert tuple(
        origin.identity.owner.identity.declared_name for origin in result.source_origins
    ) == ("rows_one", "rows_two", "unkeyed_rows")
    for origin in result.source_origins:
        assert origin.identity.kind is grain.ProjectGrainOriginKind.SOURCE_ROW_DOMAIN
        assert origin.basis.state is grain.ProjectGrainBasisState.FACTORIZED
        assert len(origin.basis.universe.factors) == 1
        assert origin.basis.dependencies == ()
        assert origin.basis.dependency_index.rules == ()
        witness = origin.basis.witness
        assert type(witness) is grain.ProjectSourceGrainWitness
        assert witness.semantic is witness.value_fds.universe.scope.relation

    assert _origin(result, "unkeyed_rows").basis.universe.factors
    first = _origin(result, "rows_one").basis.universe.factors[0]
    second = _origin(result, "rows_two").basis.universe.factors[0]
    assert type(first.identity) is grain.ProjectSourceGrainFactorIdentity
    assert type(second.identity) is grain.ProjectSourceGrainFactorIdentity
    assert first.identity != second.identity
    first_source = first.identity.semantic.owner.definition
    second_source = second.identity.semantic.owner.definition
    assert type(first_source) is SourceDef and type(second_source) is SourceDef
    assert first_source.shape_name == second_source.shape_name


def test_grouped_and_global_origins_retain_exact_evaluation_authority(
    tmp_path: Path,
) -> None:
    result = _grain(tmp_path)
    assert tuple(
        origin.identity.owner.identity.declared_name
        for origin in result.aggregate_origins
    ) == ("grouped_one", "grouped_two", "global_total")
    grouped_one = _origin(result, "grouped_one")
    grouped_two = _origin(result, "grouped_two")
    for grouped in (grouped_one, grouped_two):
        assert grouped.identity.kind is grain.ProjectGrainOriginKind.GROUPED_RESULT
        assert grouped.basis.state is grain.ProjectGrainBasisState.FACTORIZED
        witness = grouped.basis.witness
        assert type(witness) is grain.ProjectGroupedGrainWitness
        assert type(witness.context) is ProjectIRAggregateEvaluationContext
        assert witness.group_keys is witness.context.group_keys
        assert type(witness.group_keys[0].key) is NameExpr
        assert witness.group_keys[0].key.name == "category"
        assert any(
            type(property_) is ProjectIRProvidedLocalGrainEvidence
            for property_ in witness.context.fragment.property_stage.provided
        )
    assert grouped_one.basis.universe.factors[0].identity != (
        grouped_two.basis.universe.factors[0].identity
    )

    global_total = _origin(result, "global_total")
    assert global_total.identity.kind is grain.ProjectGrainOriginKind.GLOBAL_AGGREGATE
    assert global_total.basis.state is grain.ProjectGrainBasisState.GLOBAL
    assert global_total.basis.universe.factors == ()
    assert global_total.basis.dependencies == ()
    global_witness = global_total.basis.witness
    assert type(global_witness) is grain.ProjectGlobalGrainWitness
    assert global_witness.context.group_keys == ()
    assert global_witness.context.aggregate_results
    assert not any(
        type(property_) is ProjectIRProvidedLocalGrainEvidence
        for property_ in global_witness.context.fragment.property_stage.provided
    )


def test_plain_unary_and_limit_outputs_create_no_new_origin_or_global_grain(
    tmp_path: Path,
) -> None:
    result = _grain(tmp_path)
    owner_names = {
        origin.identity.owner.identity.declared_name for origin in result.origins
    }
    assert (
        not {
            "plain_projection",
            "filtered_limited",
            "broken_group",
        }
        & owner_names
    )
    assert tuple(ProjectIRLogicalOperatorKind) == (
        ProjectIRLogicalOperatorKind.RELATION_INPUT,
        ProjectIRLogicalOperatorKind.ROW_FILTER,
        ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
        ProjectIRLogicalOperatorKind.RESULT_FILTER,
        ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
        ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ProjectIRLogicalOperatorKind.RELATION_ORDERING,
        ProjectIRLogicalOperatorKind.LIMIT,
    )


def test_non_concrete_origins_are_isolated_without_fake_basis(tmp_path: Path) -> None:
    result = _grain(tmp_path)
    subjects = {
        (
            subject.kind,
            subject.semantic.owner.identity.declared_name,
        )
        for subject in result.non_concrete
    }
    assert (
        grain.ProjectNonConcreteGrainOriginKind.SOURCE_ROW_DOMAIN,
        "broken_rows",
    ) in subjects
    assert (
        grain.ProjectNonConcreteGrainOriginKind.AGGREGATE_CONTEXT,
        "broken_group",
    ) in subjects
    assert _origin(result, "rows_one").basis.state is (
        grain.ProjectGrainBasisState.FACTORIZED
    )
    with pytest.raises(ValueError, match="complete and exact"):
        replace(result, non_concrete=())


def test_origin_carriers_reject_detached_factor_and_context_authority(
    tmp_path: Path,
) -> None:
    result = _grain(tmp_path)
    first = _origin(result, "rows_one")
    second = _origin(result, "rows_two")
    with pytest.raises(ValueError, match="factor and witness"):
        replace(
            first.basis,
            universe=second.basis.universe,
            dependency_index=second.basis.dependency_index,
        )

    grouped_one = _origin(result, "grouped_one")
    grouped_two = _origin(result, "grouped_two")
    with pytest.raises(ValueError, match="exact domain factor"):
        replace(grouped_one, basis=grouped_two.basis)


def test_dependency_kernel_is_typed_local_finite_and_arbitrary_width(
    tmp_path: Path,
) -> None:
    sources = "".join(
        f'source rows_{position}: Row is postgres.table("rows_{position}")\n'
        for position in range(70)
    )
    result = _grain(
        tmp_path,
        "shape Row:\n    id: Int not null\n" + sources,
    )
    factors = tuple(
        origin.basis.universe.factors[0] for origin in result.source_origins
    )
    universe = grain.ProjectGrainFactorUniverse(factors=factors)
    dependency = grain.ProjectGrainDependencyFact(
        determinants=(factors[0].identity,),
        dependents=(factors[-1].identity,),
    )
    index = grain._compile_grain_dependency_index(universe, (dependency,))
    seed = grain.ProjectGrainFactorSet(
        universe=universe,
        factors=(factors[0].identity,),
    )
    closure = grain.grain_dependency_closure(index, seed)
    assert len(universe.factors) == 70
    assert index.rules[0].rhs_mask == 1 << 69
    assert closure.mask.bit_count() == 2
    assert closure.factors == (factors[0].identity, factors[-1].identity)
    assert type(dependency) is not value_fds.ProjectValueFDFact
    with pytest.raises(ValueError, match="exact local universe"):
        grain.grain_dependency_closure(
            index,
            grain.ProjectGrainFactorSet(
                universe=grain.ProjectGrainFactorUniverse(factors=(factors[0],)),
                factors=(factors[0].identity,),
            ),
        )


def test_states_optional_seam_and_private_boundary_are_exact(tmp_path: Path) -> None:
    result = _grain(tmp_path)
    assert tuple(grain.ProjectGrainBasisState) == (
        grain.ProjectGrainBasisState.FACTORIZED,
        grain.ProjectGrainBasisState.GLOBAL,
        grain.ProjectGrainBasisState.UNKNOWN,
        grain.ProjectGrainBasisState.CONFLICT,
    )
    assert tuple(grain.ProjectOptionalGrainFactorReadiness) == (
        grain.ProjectOptionalGrainFactorReadiness.NOT_CONSTRUCTIBLE_BEFORE_LOGICAL_JOIN,
    )
    assert all(origin.basis.dependencies == () for origin in result.origins)
    assert grain.__all__ == ()
    assert "grain" not in {field.name for field in fields(ProjectSemanticResult)}
    assert "grain" not in {field.name for field in fields(SemanticModel)}


def test_source_uses_exact_authority_without_name_hash_or_operator_transfer() -> None:
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.project_value_fds",
        "pietto._project.project_ir_evaluation_context",
        "pietto._project.module_semantic_fact_preservation",
    } <= facts.imported_modules
    assert (
        not {
            "pietto._project.project_relationships",
            "pietto._project.project_relationship_conditions",
            "pietto.sql",
            "pietto.ir",
            "pathlib",
            "os",
        }
        & facts.imported_modules
    )
    for forbidden in (
        "sorted",
        "sort",
        "glob",
        "rglob",
        "getcwd",
        "sha256",
        "hash",
        "intern",
        "cardinality",
        "fanout",
    ):
        assert forbidden not in facts.identifiers
    assert "ProjectValueFDFact" not in facts.identifiers
    assert "ProjectCompiledValueFDRule" not in facts.identifiers


def test_contract_locks_grain_origins_dependencies_non_goals_and_handoff() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == SPEC_HEADINGS
    )
    normalized = " ".join(document.split())
    for evidence in (
        "d33a3e81d3405b95879becf6bcccebb433ea298f",
        "e4ab46583b1dc9f6aa2649f67bd073d99f1e027d",
        "33488399817",
        "A3/M5/D0",
        "intrinsic grain != visible key fields != Value FD != row uniqueness != cardinality",
        "UNKNOWN != GLOBAL",
        "CONFLICT != UNKNOWN",
        "absence of visible key != unknown intrinsic grain",
        "GLOBAL grain != empty candidate key != max-one-row != LIMIT 1",
        "FieldSet -> FieldSet != GrainFactorSet -> GrainFactorSet",
        "factor bit position != grain-factor identity",
        "intrinsic grain-domain factor != future factor-use occurrence",
        "existing LOCAL_GRAIN_EVIDENCE != intrinsic GrainBasis",
        "Phase 62 Slice 7 — Existing-Operator Key/FD/Grain Transfer And Grain Comparison",
        "Add Phase 62 intrinsic grain foundation",
        "PASS — PHASE62_SLICE6_FACTORIZED_INTRINSIC_GRAIN_BASIS_DEPENDENCIES_OPTIONAL_FACTORS_GLOBAL_GRAIN_END_TO_END",
    ):
        assert evidence in normalized
