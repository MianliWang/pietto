from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project import project_row_keys as row_keys
from pietto._project import project_value_fds as value_fds
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import ProjectModuleRowFieldKind
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto.semantic.model import SemanticModel


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_value_fds.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Strict And Lax Value-FD Semantics",
    "Direct Candidate-key Derivation",
    "Exact FD Identity And Provenance",
    "Exact Field Universes",
    "Compact Compiled Indexes",
    "Targeted Strict Closure",
    "Lax Query Boundary",
    "Determination Results And Proof Witnesses",
    "Completeness Ordering And Isolation",
    "Compatibility And Production Delta",
    "Focused Assurance",
    "Slice 6 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            "shape Row:\n"
            "    a: Int not null\n"
            "    b: Int not null\n"
            "    c: Int nullable\n"
            "    d: Int\n"
            "    unique a_key on a\n"
            "    unique a_key_again on a\n"
            "    unique b_key on b\n"
            "    unique c_key on c\n"
            'source left_rows: Row is postgres.table("left_rows")\n'
            'source right_rows: Row is postgres.table("right_rows")\n'
            "shape Singleton:\n"
            "    only: Int not null\n"
            "    unique only_key on only\n"
            'source singleton_rows: Singleton is postgres.table("singleton")\n'
            "shape Unkeyed:\n"
            "    plain: Int not null\n"
            'source unkeyed_rows: Unkeyed is postgres.table("unkeyed")\n'
            "shape Composite:\n"
            "    x: Int not null\n"
            "    y: Int not null\n"
            "    z: Int not null\n"
            "    unique xy_key on x, y\n"
            'source composite_rows: Composite is postgres.table("composite")\n'
            "shape Broken:\n"
            "    broken: MissingType not null\n"
            "    unique broken_key on broken\n"
            'source broken_rows: Broken is postgres.table("broken")\n'
            "table projected_rows:\n"
            "    from left_rows\n"
            "    select:\n"
            "        a\n"
            "        b\n"
        ),
    }


def _semantic_project(
    root: Path,
    files: dict[str, str] | None = None,
) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in (files or _project_files()).items():
        (root / relative).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    return build_empty_project_semantic_result(parsed)


def _facts(
    root: Path,
    files: dict[str, str] | None = None,
) -> tuple[row_keys.ProjectRowKeySet, value_fds.ProjectValueFDBasisSet]:
    keys = row_keys.build_project_row_keys(_semantic_project(root, files))
    return keys, value_fds.build_project_value_fds(keys)


def _basis(
    result: value_fds.ProjectValueFDBasisSet,
    source_name: str,
) -> value_fds.ProjectValueFDBasis:
    bucket = tuple(
        basis
        for basis in result.bases
        if basis.universe.scope.owner.identity.declared_name == source_name
    )
    assert len(bucket) == 1
    return bucket[0]


def _field_set(
    universe: value_fds.ProjectValueFDFieldUniverse,
    *names: str,
) -> value_fds.ProjectValueFDFieldSet:
    return value_fds.ProjectValueFDFieldSet(
        universe=universe,
        fields=tuple(field for field in universe.fields if field.name in names),
    )


def _fact(
    basis: value_fds.ProjectValueFDBasis,
    determinant_name: str,
) -> value_fds.ProjectValueFDFact:
    return next(
        fact
        for fact in basis.facts
        if tuple(field.name for field in fact.identity.determinants)
        == (determinant_name,)
    )


def _fragment(
    basis: value_fds.ProjectValueFDBasis,
    determinant_name: str,
    *dependent_names: str,
) -> value_fds.ProjectValueFDFact:
    source = _fact(basis, determinant_name)
    return value_fds.ProjectValueFDFact(
        identity=value_fds.ProjectValueFDIdentity(
            scope=basis.universe.scope,
            determinants=source.identity.determinants,
            dependents=tuple(
                field
                for field in basis.universe.fields
                if field.name in dependent_names
            ),
            strength=source.identity.strength,
            premise=source.premise.identity,
        ),
        premise=source.premise,
        origin=row_keys.ProjectConstraintEvidenceOrigin.DERIVED_THEOREM,
        trust=row_keys.ProjectConstraintEvidenceTrust.TRUSTED,
        enforcement=row_keys.ProjectConstraintEnforcementPosture.MODEL_CONTRACT,
    )


def test_candidate_keys_derive_one_exact_strict_or_lax_direct_fd(
    tmp_path: Path,
) -> None:
    keys, result = _facts(tmp_path)
    left = _basis(result, "left_rows")

    assert result.row_keys is keys
    assert tuple(field.name for field in left.universe.fields) == ("a", "b", "c", "d")
    assert all(
        field.kind is ProjectModuleRowFieldKind.SOURCE_FIELD
        and field.owner == left.universe.scope.owner
        for field in left.universe.fields
    )
    assert tuple(
        (
            tuple(field.name for field in fact.identity.determinants),
            tuple(field.name for field in fact.identity.dependents),
            fact.identity.strength,
        )
        for fact in left.facts
    ) == (
        (("a",), ("b", "c", "d"), row_keys.ProjectRowUniquenessStrength.STRICT),
        (("b",), ("a", "c", "d"), row_keys.ProjectRowUniquenessStrength.STRICT),
        (("c",), ("a", "b", "d"), row_keys.ProjectRowUniquenessStrength.LAX),
    )
    a_fact = left.facts[0]
    assert len(a_fact.premise.supports) == 2
    assert tuple(
        support.declaration.unique.name for support in a_fact.premise.supports
    ) == ("a_key", "a_key_again")
    assert (
        sum(fact.identity.premise == a_fact.identity.premise for fact in left.facts)
        == 1
    )
    assert a_fact.origin is row_keys.ProjectConstraintEvidenceOrigin.DERIVED_THEOREM
    assert a_fact.trust is row_keys.ProjectConstraintEvidenceTrust.TRUSTED
    assert (
        a_fact.enforcement
        is row_keys.ProjectConstraintEnforcementPosture.MODEL_CONTRACT
    )
    assert result.row_keys.candidate_keys is keys.candidate_keys


def test_every_concrete_source_has_one_ordered_universe_and_empty_bases_are_valid(
    tmp_path: Path,
) -> None:
    keys, result = _facts(tmp_path)

    assert tuple(
        basis.universe.scope.owner.identity.declared_name for basis in result.bases
    ) == (
        "left_rows",
        "right_rows",
        "singleton_rows",
        "unkeyed_rows",
        "composite_rows",
    )
    assert _basis(result, "singleton_rows").facts == ()
    unkeyed = _basis(result, "unkeyed_rows")
    assert unkeyed.facts == ()
    assert unkeyed.index.facts == ()
    assert unkeyed.index.strict_rules == ()
    assert unkeyed.index.lax_rules == ()
    assert any(
        subject.reason is row_keys.ProjectRowKeyFailureReason.UNKNOWN_SOURCE_ROW
        for subject in keys.non_concrete
    )
    assert not result.find_owner(
        next(
            subject.identity.source
            for subject in keys.non_concrete
            if subject.source.definition.name == "broken_rows"
            and subject.identity is not None
        )
    )
    assert all(
        basis.universe.scope.owner.identity.declaration_kind.value == "source"
        for basis in result.bases
    )


def test_compiled_indexes_are_universe_local_and_support_arbitrary_width(
    tmp_path: Path,
) -> None:
    _keys, result = _facts(tmp_path / "ordinary")
    left = _basis(result, "left_rows")
    right = _basis(result, "right_rows")
    left_a = _field_set(left.universe, "a")
    right_a = _field_set(right.universe, "a")

    assert left_a.mask == right_a.mask == 1
    assert left_a.universe is not right_a.universe
    assert left.index.positions[left.universe.fields[-1]] == 3
    assert tuple(rule.fact for rule in left.index.strict_rules) == left.facts[:2]
    assert tuple(rule.fact for rule in left.index.lax_rules) == left.facts[2:]
    assert left.index.strict_incidents[0] == (0,)
    assert left.index.strict_incidents[1] == (1,)
    with pytest.raises(ValueError, match="exact field universe"):
        value_fds.strictly_determines(left.index, left_a, right_a)

    field_lines = "".join(f"    f{position}: Int not null\n" for position in range(70))
    wide_files = {
        "wide.pietto": (
            "shape Wide:\n"
            + field_lines
            + "    unique wide_key on f0\n"
            + 'source wide_rows: Wide is postgres.table("wide")\n'
        )
    }
    _wide_keys, wide_result = _facts(tmp_path / "wide", wide_files)
    wide = _basis(wide_result, "wide_rows")
    rule = wide.index.strict_rules[0]
    closure = value_fds.strict_value_fd_closure(
        wide.index,
        _field_set(wide.universe, "f0"),
    )
    assert len(wide.universe.fields) == 70
    assert rule.lhs_mask == 1
    assert rule.rhs_mask.bit_count() == 69
    assert rule.rhs_mask & (1 << 69)
    assert closure.fields.mask.bit_count() == 70
    assert closure.fields.fields[-1].name == "f69"


def test_indexed_strict_closure_reaches_fixed_point_and_handles_composites_and_cycles(
    tmp_path: Path,
) -> None:
    _keys, result = _facts(tmp_path)
    left = _basis(result, "left_rows")
    a_to_b = _fragment(left, "a", "b")
    b_to_c = _fragment(left, "b", "c")
    chain = value_fds._compile_project_value_fd_index(
        left.universe,
        (a_to_b, b_to_c),
    )
    closure = value_fds.strict_value_fd_closure(
        chain,
        _field_set(left.universe, "a"),
    )
    assert tuple(field.name for field in closure.fields.fields) == ("a", "b", "c")
    assert tuple(step.fact for step in closure.witness) == (a_to_b, b_to_c)

    cycle = value_fds._compile_project_value_fd_index(
        left.universe,
        (a_to_b, _fragment(left, "b", "a")),
    )
    cyclic = value_fds.strict_value_fd_closure(
        cycle,
        _field_set(left.universe, "a"),
    )
    assert tuple(field.name for field in cyclic.fields.fields) == ("a", "b")
    assert len(cyclic.witness) == 1

    composite = _basis(result, "composite_rows")
    x_only = value_fds.strict_value_fd_closure(
        composite.index,
        _field_set(composite.universe, "x"),
    )
    xy = value_fds.strict_value_fd_closure(
        composite.index,
        _field_set(composite.universe, "x", "y"),
    )
    assert tuple(field.name for field in x_only.fields.fields) == ("x",)
    assert tuple(field.name for field in xy.fields.fields) == ("x", "y", "z")


def test_lax_rules_remain_direct_and_are_never_used_by_strict_closure(
    tmp_path: Path,
) -> None:
    _keys, result = _facts(tmp_path)
    left = _basis(result, "left_rows")
    lax = _fact(left, "c")
    assert lax.identity.strength is row_keys.ProjectRowUniquenessStrength.LAX
    assert left.index.lax_rules[0].fact is lax

    closure = value_fds.strict_value_fd_closure(
        left.index,
        _field_set(left.universe, "c"),
    )
    assert tuple(field.name for field in closure.fields.fields) == ("c",)
    assert closure.witness == ()

    mixed = value_fds._compile_project_value_fd_index(
        left.universe,
        (_fragment(left, "c", "a"), _fragment(left, "a", "b")),
    )
    mixed_closure = value_fds.strict_value_fd_closure(
        mixed,
        _field_set(left.universe, "c"),
    )
    assert tuple(field.name for field in mixed_closure.fields.fields) == ("c",)
    assert not hasattr(value_fds, "lax_value_fd_closure")


def test_determination_is_epistemic_and_witness_ties_follow_direct_rule_order(
    tmp_path: Path,
) -> None:
    _keys, result = _facts(tmp_path)
    left = _basis(result, "left_rows")
    first = _fragment(left, "a", "c")
    second = _fragment(left, "a", "b", "c")
    index = value_fds._compile_project_value_fd_index(
        left.universe,
        (first, second),
    )
    seed = _field_set(left.universe, "a")

    proven = value_fds.strictly_determines(
        index,
        seed,
        _field_set(left.universe, "b", "c"),
    )
    not_proven = value_fds.strictly_determines(
        index,
        seed,
        _field_set(left.universe, "d"),
    )
    assert proven.status is value_fds.ProjectValueFDDeterminationStatus.PROVEN
    assert not_proven.status is (value_fds.ProjectValueFDDeterminationStatus.NOT_PROVEN)
    assert tuple(step.fact for step in proven.closure.witness) == (first, second)
    assert tuple(
        tuple(field.name for field in step.derived_fields)
        for step in proven.closure.witness
    ) == (("c",), ("b",))
    assert len(proven.closure.witness) == 2
    assert tuple(value_fds.ProjectValueFDDeterminationStatus) == (
        value_fds.ProjectValueFDDeterminationStatus.PROVEN,
        value_fds.ProjectValueFDDeterminationStatus.NOT_PROVEN,
    )

    b_first = _fragment(left, "b", "c")
    a_second = _fragment(left, "a", "c")
    distinct_lhs = value_fds._compile_project_value_fd_index(
        left.universe,
        (b_first, a_second),
    )
    distinct_lhs_result = value_fds.strict_value_fd_closure(
        distinct_lhs,
        _field_set(left.universe, "a", "b"),
    )
    assert tuple(step.fact for step in distinct_lhs_result.witness) == (b_first,)

    with pytest.raises(ValueError, match="replay the exact fixed point"):
        value_fds.ProjectStrictClosureResult(
            seed=seed,
            fields=_field_set(left.universe, "a", "b"),
            witness=(),
        )


def test_private_boundary_adds_no_operator_key_grain_or_public_authority(
    tmp_path: Path,
) -> None:
    keys, result = _facts(tmp_path)

    assert value_fds.__all__ == ()
    assert "value_fds" not in {field.name for field in fields(ProjectSemanticResult)}
    assert "value_fds" not in {field.name for field in fields(SemanticModel)}
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
    assert all(
        basis.universe.scope.owner.identity.declaration_kind.value == "source"
        for basis in result.bases
    )
    assert all(
        candidate.identity == retained.identity
        and candidate.supports is retained.supports
        for candidate, retained in zip(
            keys.candidate_keys,
            result.row_keys.candidate_keys,
            strict=True,
        )
    )
    forbidden_fields = {
        "grain",
        "cardinality",
        "fanout",
        "join",
        "relationship",
        "operator",
    }
    assert not forbidden_fields & {
        field.name
        for carrier in (
            value_fds.ProjectValueFDIdentity,
            value_fds.ProjectValueFDFact,
            value_fds.ProjectValueFDFieldUniverse,
            value_fds.ProjectValueFDBasis,
        )
        for field in fields(carrier)
    }


def test_source_is_private_deterministic_and_uses_only_existing_exact_authority() -> (
    None
):
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.module_attribution",
        "pietto._project.module_catalog",
        "pietto._project.module_semantic_fact_preservation",
        "pietto._project.project_relationship_conditions",
        "pietto._project.project_row_keys",
    } <= facts.imported_modules
    assert (
        not {
            "pietto._project.project_relationships",
            "pietto.ir",
            "pietto.sql",
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
        "cache",
        "relationship_correspondences",
        "where",
        "group_by",
    ):
        assert forbidden not in facts.identifiers
    for required in (
        "ProjectCandidateKeyFact",
        "ProjectModuleRowFieldIdentity",
        "ProjectExactRowOutputConstraintScope",
        "MappingProxyType",
        "bit_count",
        "deque",
    ):
        assert required in facts.identifiers


def test_contract_locks_fd_semantics_indexes_closure_non_goals_and_handoff() -> None:
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
        "b38247f6d115e1cbcf24b47b4d60322fa68e0fa4",
        "11f0b216e4a7273bd2fef6f8a8357443ecb6923e",
        "33477493108",
        "A3/M6/D0",
        "strict FD != lax FD",
        "lax FD is not generally transitive",
        "K -> (U - K)",
        "origin = DERIVED_THEOREM trust = TRUSTED enforcement = MODEL_CONTRACT",
        "bit position != semantic identity",
        "STRICT closure only",
        "indexed worklist",
        "NOT_PROVEN != DISPROVEN",
        "proof witness != semantic identity",
        "Slice-4 candidate frontier remains authoritative",
        "PHASE33_WHOLE_SOURCE_SUBSTRING_READER_CONFUSES_INTERNAL_IDENTIFIER_SUBSTRING_WITH_FORBIDDEN_PROJECT_COMPILATION_CAPABILITY",
        "Slice 5 repair batches used cumulatively: 2",
        "maximum cumulative validator accounting: 2/2",
        "Value FD kernel != GrainDependency kernel",
        "Phase 62 Slice 6 — Factorized Intrinsic Grain Basis, Grain Dependencies, Optional Factors, And GLOBAL Grain",
        "Add Phase 62 value functional dependencies",
        "PASS — PHASE62_SLICE5_STRICT_LAX_VALUE_FD_BASIS_COMPACT_INDEXES_TARGETED_CLOSURE_END_TO_END",
    ):
        assert evidence in normalized
