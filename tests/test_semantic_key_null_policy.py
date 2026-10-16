from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import ProjectModuleSourceFieldOrigin
from pietto._project import project_row_keys as row_keys
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_relationship_conditions import (
    ProjectExactRowOutputConstraintScope,
)
from pietto.ast_nodes import Script, ShapeDef, SourceDef
from pietto.errors import Diagnostic
from pietto.ir.model import ShapeUniqueIR
from pietto.parser_api import parse_source
from pietto.semantic.model import SemanticModel

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_row_keys.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Existing UNIQUE Admission Authority",
    "Declaration Application And Evidence Identity",
    "Shape To Source Authority Chain",
    "Pietto UNIQUE NULL Policy",
    "Strict And Lax Row Uniqueness",
    "Evidence Origin Trust And Enforcement",
    "Exact Row-output Scope And Determinants",
    "Non-concrete Subjects",
    "Candidate-key Facts And Frontier",
    "No FD Or Later-owner Inference",
    "Compatibility And Production Delta",
    "Focused Assurance",
    "Slice 5 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _project_files(*, mode: str | None = None) -> dict[str, str]:
    header = "" if mode is None else f"mode {mode}\n"
    return {
        "a.pietto": (
            header + 'import "b.pietto":\n    shape RemoteRow as ImportedRow\n'
            "shape UserRow:\n"
            "    id: Int not null\n"
            "    tenant_id: Int nullable\n"
            "    implicit_id: Int\n"
            "    alt_id: Int not null\n"
            "    unique id_key on id\n"
            "    unique id_key_again on id\n"
            "    unique alt_key on alt_id\n"
            "    unique tenant_key on tenant_id\n"
            "    unique tenant_id_key on tenant_id, id\n"
            "    unique strict_composite on alt_id, id\n"
            "    unique implicit_key on implicit_id\n"
            "    unique missing_key on missing\n"
            "    unique repeated_key on id, id\n"
            "    unique collision on id\n"
            "    index collision on id\n"
            'source users_one: UserRow is postgres.table("users_one")\n'
            'source users_two: UserRow is postgres.table("users_two")\n'
            'source imported_rows: ImportedRow is postgres.table("imported")\n'
            'source missing_rows: MissingShape is postgres.table("missing")\n'
            "shape BrokenRow:\n"
            "    broken_id: MissingType not null\n"
            "    unique broken_key on broken_id\n"
            'source broken_rows: BrokenRow is postgres.table("broken")\n'
            "shape AmbiguousRow:\n"
            "    id: Int not null\n"
            "shape AmbiguousRow:\n"
            "    id: Int not null\n"
            'source ambiguous_rows: AmbiguousRow is postgres.table("ambiguous")\n'
            "table projected_users:\n"
            "    from users_one\n"
            "    select:\n"
            "        id\n"
            "        tenant_id\n"
        ),
        "b.pietto": (
            header + "shape RemoteRow:\n"
            "    remote_id: Int not null\n"
            "    unique remote_key on remote_id\n"
            "export:\n    shape RemoteRow\n"
        ),
    }


def _semantic_project(
    root: Path,
    *,
    mode: str | None = None,
) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in _project_files(mode=mode).items():
        (root / relative).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    return build_empty_project_semantic_result(parsed)


def _row_keys(root: Path, *, mode: str | None = None) -> row_keys.ProjectRowKeySet:
    return row_keys.build_project_row_keys(_semantic_project(root, mode=mode))


def _evidence(
    result: row_keys.ProjectRowKeySet,
    source_name: str,
    unique_name: str,
) -> tuple[row_keys.ProjectRowUniquenessEvidence, ...]:
    return tuple(
        evidence
        for evidence in result.evidence
        if evidence.source_shape_resolution.reference.source.name == source_name
        and evidence.declaration.unique.name == unique_name
    )


def _source_name(subject: row_keys.ProjectRowUniquenessSubject) -> str:
    if type(subject) is row_keys.ProjectRowUniquenessEvidence:
        return subject.source_shape_resolution.reference.source.name
    if type(subject) is row_keys.ProjectNonConcreteRowUniquenessSubject:
        definition = subject.source.definition
        assert type(definition) is SourceDef
        return definition.name
    raise AssertionError("Unhandled row uniqueness subject type.")


def test_current_unique_syntax_remains_unchanged() -> None:
    parsed = parse_source(
        "shape User:\n"
        "    user_id: Int not null\n"
        "    tenant_id: Int nullable\n"
        "    unique user_id_key on user_id\n"
        "    unique tenant_user_key on tenant_id, user_id\n"
    )

    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    shape = parsed.ast.definitions[0]
    assert isinstance(shape, ShapeDef)
    assert tuple((item.name, item.field_names) for item in shape.uniques) == (
        ("user_id_key", ("user_id",)),
        ("tenant_user_key", ("tenant_id", "user_id")),
    )
    assert row_keys.__all__ == ()


def test_unique_declaration_and_source_application_identities_remain_distinct(
    tmp_path: Path,
) -> None:
    result = _row_keys(tmp_path)
    id_declarations = tuple(
        declaration
        for declaration in result.declarations
        if declaration.unique.name == "id_key"
    )
    assert len(id_declarations) == 1
    declaration = id_declarations[0]
    assert declaration.admitted
    assert declaration.identity.shape_item_position == 4

    applications = tuple(
        evidence for evidence in result.evidence if evidence.declaration is declaration
    )
    assert len(applications) == 2
    assert tuple(
        evidence.source_shape_resolution.reference.source.name
        for evidence in applications
    ) == ("users_one", "users_two")
    assert applications[0].identity.declaration == applications[1].identity.declaration
    assert applications[0].identity.source != applications[1].identity.source
    assert applications[0].scope.owner != applications[1].scope.owner
    assert all(
        type(evidence.scope) is ProjectExactRowOutputConstraintScope
        for evidence in applications
    )

    imported = _evidence(result, "imported_rows", "remote_key")
    assert len(imported) == 1
    imported_evidence = imported[0]
    assert imported_evidence.declaration.shape_occurrence.identity.module_path == (
        "b.pietto"
    )
    assert imported_evidence.identity.source.identity.module_path == "a.pietto"
    assert (
        imported_evidence.source_shape_resolution.target_symbol.imported_binding
        is not None
    )
    determinant = imported_evidence.determinants[0]
    assert type(determinant.source_origin) is ProjectModuleSourceFieldOrigin
    assert determinant.shape_field_identity.owner.identity.module_path == "b.pietto"
    assert determinant.source_field_identity.owner.identity.module_path == "a.pietto"


def test_null_policy_strength_trust_and_enforcement_are_exact(tmp_path: Path) -> None:
    result = _row_keys(tmp_path)
    strict = _evidence(result, "users_one", "id_key")[0]
    nullable = _evidence(result, "users_one", "tenant_key")[0]
    unknown = _evidence(result, "users_one", "implicit_key")[0]

    assert strict.null_policy is row_keys.ProjectUniqueNullPolicy.NULLS_DISTINCT
    assert strict.strength is row_keys.ProjectRowUniquenessStrength.STRICT
    assert nullable.strength is row_keys.ProjectRowUniquenessStrength.LAX
    assert unknown.strength is row_keys.ProjectRowUniquenessStrength.LAX
    assert strict.determinants[0].nullability is ProjectRowFieldNullability.NON_NULL
    assert nullable.determinants[0].nullability is ProjectRowFieldNullability.NULLABLE
    assert unknown.determinants[0].nullability is ProjectRowFieldNullability.UNKNOWN
    assert all(
        evidence.origin is row_keys.ProjectConstraintEvidenceOrigin.AUTHORED_CONTRACT
        and evidence.trust is row_keys.ProjectConstraintEvidenceTrust.TRUSTED
        and evidence.enforcement
        is row_keys.ProjectConstraintEnforcementPosture.MODEL_CONTRACT
        for evidence in result.evidence
    )
    assert tuple(row_keys.ProjectUniqueNullPolicy) == (
        row_keys.ProjectUniqueNullPolicy.NULLS_DISTINCT,
        row_keys.ProjectUniqueNullPolicy.NULLS_NOT_DISTINCT,
    )


@pytest.mark.parametrize("mode", ["loose", "checked", "strict"])
def test_check_mode_does_not_change_authored_contract_trust(
    tmp_path: Path,
    mode: str,
) -> None:
    result = _row_keys(tmp_path / mode, mode=mode)
    evidence = _evidence(result, "users_one", "id_key")[0]
    assert evidence.origin is row_keys.ProjectConstraintEvidenceOrigin.AUTHORED_CONTRACT
    assert evidence.trust is row_keys.ProjectConstraintEvidenceTrust.TRUSTED
    assert evidence.enforcement is (
        row_keys.ProjectConstraintEnforcementPosture.MODEL_CONTRACT
    )


def test_invalid_unique_and_unavailable_sources_retain_non_concrete_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[tuple[Diagnostic, ...]] = []
    checker = row_keys.check_shape_structures

    def recording_checker(script: Script) -> list[Diagnostic]:
        diagnostics = checker(script)
        checked.append(tuple(diagnostics))
        return diagnostics

    monkeypatch.setattr(row_keys, "check_shape_structures", recording_checker)
    result = _row_keys(tmp_path)
    checker_diagnostics = tuple(
        diagnostic for diagnostics in checked for diagnostic in diagnostics
    )

    invalid_names = {"missing_key", "repeated_key", "collision"}
    invalid_declarations = tuple(
        declaration
        for declaration in result.declarations
        if declaration.unique.name in invalid_names
    )
    assert len(invalid_declarations) == 3
    assert all(not declaration.admitted for declaration in invalid_declarations)
    assert {
        diagnostic.code
        for declaration in invalid_declarations
        for diagnostic in declaration.diagnostics
    } == {"PIE-S2501", "PIE-S2502", "PIE-S2503"}
    assert all(
        any(
            diagnostic is checked_diagnostic
            for checked_diagnostic in checker_diagnostics
        )
        for declaration in invalid_declarations
        for diagnostic in declaration.diagnostics
    )
    assert not any(
        evidence.declaration.unique.name in invalid_names
        for evidence in result.evidence
    )
    assert (
        sum(
            subject.reason
            is row_keys.ProjectRowKeyFailureReason.INVALID_UNIQUE_DECLARATION
            for subject in result.non_concrete
        )
        == 6
    )

    by_source = {
        name: tuple(
            subject for subject in result.non_concrete if _source_name(subject) == name
        )
        for name in ("missing_rows", "ambiguous_rows", "broken_rows")
    }
    assert len(by_source["missing_rows"]) == 1
    assert by_source["missing_rows"][0].identity is None
    assert by_source["missing_rows"][0].reason is (
        row_keys.ProjectRowKeyFailureReason.UNRESOLVED_SOURCE_SHAPE
    )
    assert by_source["missing_rows"][0].state is (
        row_keys.ProjectRowKeyConstructionState.UNKNOWN
    )
    assert len(by_source["ambiguous_rows"]) == 1
    assert by_source["ambiguous_rows"][0].reason is (
        row_keys.ProjectRowKeyFailureReason.AMBIGUOUS_SOURCE_SHAPE
    )
    assert by_source["ambiguous_rows"][0].state is (
        row_keys.ProjectRowKeyConstructionState.AMBIGUOUS
    )
    assert len(by_source["broken_rows"]) == 1
    assert by_source["broken_rows"][0].reason is (
        row_keys.ProjectRowKeyFailureReason.UNKNOWN_SOURCE_ROW
    )
    assert by_source["broken_rows"][0].state is (
        row_keys.ProjectRowKeyConstructionState.UNKNOWN
    )
    assert _evidence(result, "users_one", "id_key")
    assert _evidence(result, "users_two", "alt_key")


def test_candidate_frontier_is_complete_non_dominated_and_support_preserving(
    tmp_path: Path,
) -> None:
    result = _row_keys(tmp_path)
    users_one = tuple(
        candidate
        for candidate in result.candidate_keys
        if candidate.identity.owner.identity.declared_name == "users_one"
    )
    assert tuple(
        (
            tuple(field.name for field in candidate.identity.determinants),
            candidate.identity.strength,
            tuple(support.declaration.unique.name for support in candidate.supports),
        )
        for candidate in users_one
    ) == (
        (
            ("id",),
            row_keys.ProjectRowUniquenessStrength.STRICT,
            ("id_key", "id_key_again"),
        ),
        (("alt_id",), row_keys.ProjectRowUniquenessStrength.STRICT, ("alt_key",)),
        (
            ("tenant_id",),
            row_keys.ProjectRowUniquenessStrength.LAX,
            ("tenant_key",),
        ),
        (
            ("implicit_id",),
            row_keys.ProjectRowUniquenessStrength.LAX,
            ("implicit_key",),
        ),
    )
    assert not any(
        tuple(field.name for field in candidate.identity.determinants)
        in {("id", "tenant_id"), ("id", "alt_id")}
        for candidate in users_one
    )
    assert all(candidate.identity.determinants for candidate in result.candidate_keys)

    id_field = users_one[0].identity.determinants[0]
    alt_field = users_one[1].identity.determinants[0]
    strict = row_keys.ProjectRowUniquenessStrength.STRICT
    lax = row_keys.ProjectRowUniquenessStrength.LAX
    assert row_keys._dominates(
        frozenset({id_field}), strict, frozenset({id_field, alt_field}), strict
    )
    assert row_keys._dominates(
        frozenset({id_field}), strict, frozenset({id_field, alt_field}), lax
    )
    assert row_keys._dominates(
        frozenset({id_field}), lax, frozenset({id_field, alt_field}), lax
    )
    assert not row_keys._dominates(
        frozenset({id_field}), lax, frozenset({id_field, alt_field}), strict
    )

    composite = _evidence(result, "users_one", "tenant_id_key")[0]
    assert tuple(
        determinant.field_def.name for determinant in composite.determinants
    ) == ("tenant_id", "id")
    assert tuple(
        field.name for field in row_keys._normalized_determinants(composite)
    ) == ("id", "tenant_id")


def test_shape_unique_does_not_transfer_to_table_or_query_outputs(
    tmp_path: Path,
) -> None:
    result = _row_keys(tmp_path)
    subject_sources = {_source_name(subject) for subject in result.subjects}
    assert "projected_users" not in subject_sources
    assert all(
        evidence.identity.source.identity.declaration_kind.value == "source"
        for evidence in result.evidence
    )
    assert all(
        candidate.identity.owner.identity.declaration_kind.value == "source"
        for candidate in result.candidate_keys
    )


def test_row_key_construction_is_cwd_and_environment_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path / "project")
    first = row_keys.build_project_row_keys(semantic)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv("PIETTO_UNRELATED_ROW_KEY", "ignored")
    second = row_keys.build_project_row_keys(semantic)

    def reason(
        subject: row_keys.ProjectRowUniquenessSubject,
    ) -> row_keys.ProjectRowKeyFailureReason | None:
        if type(subject) is row_keys.ProjectNonConcreteRowUniquenessSubject:
            return subject.reason
        return None

    def observation(result: row_keys.ProjectRowKeySet) -> tuple[object, ...]:
        return (
            tuple(declaration.identity for declaration in result.declarations),
            tuple(
                (
                    subject.identity,
                    subject.state,
                    reason(subject),
                )
                for subject in result.subjects
            ),
            tuple(candidate.identity for candidate in result.candidate_keys),
        )

    assert observation(first) == observation(second)


def test_set_rejects_detached_resolution_and_support_authority(tmp_path: Path) -> None:
    result = _row_keys(tmp_path)
    evidence = _evidence(result, "users_one", "id_key")[0]
    detached_resolution = replace(evidence.source_shape_resolution)
    detached_evidence = replace(
        evidence,
        source_shape_resolution=detached_resolution,
    )
    with pytest.raises(ValueError, match="Project root authority"):
        replace(
            result,
            subjects=tuple(
                detached_evidence if subject is evidence else subject
                for subject in result.subjects
            ),
        )


def test_non_concrete_terminals_reject_mixed_state_and_payload(tmp_path: Path) -> None:
    result = _row_keys(tmp_path)
    missing = next(
        subject
        for subject in result.non_concrete
        if _source_name(subject) == "missing_rows"
    )
    with pytest.raises(ValueError, match="resolution roots"):
        replace(missing, state=row_keys.ProjectRowKeyConstructionState.BLOCKED)
    duplicated_issue = replace(
        missing,
        resolution_issues=(
            missing.resolution_issues[0],
            missing.resolution_issues[0],
        ),
    )
    with pytest.raises(ValueError, match="complete exact issue roots"):
        replace(
            result,
            subjects=tuple(
                duplicated_issue if subject is missing else subject
                for subject in result.subjects
            ),
        )

    invalid = next(
        subject
        for subject in result.non_concrete
        if subject.declaration is not None
        and subject.declaration.unique.name == "missing_key"
        and _source_name(subject) == "users_one"
    )
    semantic = _evidence(result, "users_one", "id_key")[0].source_semantic
    with pytest.raises(ValueError, match="exact diagnostics"):
        replace(invalid, source_semantic=semantic)

    broken = next(
        subject
        for subject in result.non_concrete
        if _source_name(subject) == "broken_rows"
    )
    with pytest.raises(ValueError, match="construction state"):
        replace(broken, state=row_keys.ProjectRowKeyConstructionState.BLOCKED)


def test_private_carriers_add_no_fd_grain_cardinality_or_join_authority() -> None:
    assert row_keys.__all__ == ()
    assert tuple(row_keys.ProjectUniqueNullPolicy) == (
        row_keys.ProjectUniqueNullPolicy.NULLS_DISTINCT,
        row_keys.ProjectUniqueNullPolicy.NULLS_NOT_DISTINCT,
    )
    assert tuple(row_keys.ProjectRowUniquenessStrength) == (
        row_keys.ProjectRowUniquenessStrength.STRICT,
        row_keys.ProjectRowUniquenessStrength.LAX,
    )
    assert tuple(row_keys.ProjectConstraintEvidenceOrigin) == (
        row_keys.ProjectConstraintEvidenceOrigin.AUTHORED_CONTRACT,
        row_keys.ProjectConstraintEvidenceOrigin.CATALOG_CONSTRAINT,
        row_keys.ProjectConstraintEvidenceOrigin.DERIVED_THEOREM,
        row_keys.ProjectConstraintEvidenceOrigin.RUNTIME_OBSERVATION,
        row_keys.ProjectConstraintEvidenceOrigin.UNVERIFIED_HINT,
    )
    assert tuple(field.name for field in fields(ShapeUniqueIR)) == (
        "name",
        "fields",
        "span",
    )
    assert tuple(field.name for field in fields(SemanticModel))[-1] == "relationships"
    assert "row_keys" not in {field.name for field in fields(ProjectSemanticResult)}
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
    forbidden = {
        "functional_dependency",
        "grain",
        "cardinality",
        "fanout",
        "join",
        "relationship_match_guarantee",
    }
    assert not forbidden & {
        field.name
        for carrier in (
            row_keys.ProjectUniqueDeclarationIdentity,
            row_keys.ProjectRowUniquenessEvidenceIdentity,
            row_keys.ProjectUniqueDeterminantField,
            row_keys.ProjectRowUniquenessEvidence,
            row_keys.ProjectCandidateKeyIdentity,
            row_keys.ProjectCandidateKeyFact,
        )
        for field in fields(carrier)
    }


def test_source_reuses_exact_existing_authority_without_repository_scans() -> None:
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.model",
        "pietto._project.module_attribution",
        "pietto._project.module_catalog",
        "pietto._project.module_resolution",
        "pietto._project.module_semantic_fact_preservation",
        "pietto._project.project_relationship_conditions",
        "pietto.semantic.shapes",
    } <= facts.imported_modules
    assert (
        not {
            "pietto.ir",
            "pietto.sql",
            "pietto._project.project_ir",
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
        "cwd",
        "sha256",
        "hash",
    ):
        assert forbidden not in facts.identifiers
    for required in (
        "check_shape_structures",
        "find_source",
        "find_owner",
        "find_row_lineage",
        "find_source_field_origin",
        "ProjectExactRowOutputConstraintScope",
    ):
        assert required in facts.identifiers


def test_contract_locks_null_trust_strength_frontier_non_goals_and_handoff() -> None:
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
        "933a13ea6ecb5e2701f7360fc5220ed3884ace18",
        "2fb40f3c3b64ef68ecc00156621f94b02cd3db21",
        "33469961091",
        "A3/M6/D0",
        "Shape UNIQUE declaration != row-uniqueness evidence occurrence != derived candidate-key fact",
        "NULLS_DISTINCT",
        "NULLS_NOT_DISTINCT",
        "NULLS_DISTINCT + all determinant fields NON_NULL -> STRICT",
        "NULLS_DISTINCT + any determinant NULLABLE/UNKNOWN -> LAX",
        "origin = AUTHORED_CONTRACT trust = TRUSTED enforcement = MODEL_CONTRACT",
        "candidate-key set = antichain, not winner",
        "Slice-4 key frontier = uniqueness-based frontier only",
        "row-key authority != FD authority",
        "Phase 62 Slice 5 — Strict/Lax Value-FD Basis, Compact Indexes, And Targeted Closure",
        "Add Phase 62 row uniqueness and candidate keys",
        "PASS — PHASE62_SLICE4_UNIQUE_NULL_POLICY_EVIDENCE_TRUST_STRICT_LAX_ROW_UNIQUENESS_CANDIDATE_KEYS_END_TO_END",
    ):
        assert evidence in normalized
