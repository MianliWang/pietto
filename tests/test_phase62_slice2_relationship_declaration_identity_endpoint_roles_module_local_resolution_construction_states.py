from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
import pietto._project.project_relationships as relationships
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto.ast_nodes import Definition, Script
from pietto.errors import Diagnostic
from pietto.ir.model import RelationIR, ScriptIR
from pietto.semantic.model import RelationshipSemanticInfo, SemanticModel


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_relationships.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Existing Semantic And Project Authority",
    "Private Carriers And Identity Laws",
    "Module Ownership Endpoint Roles And Resolution",
    "Construction States Completeness And Ordering",
    "Implementation Boundary And Non-goals",
    "Focused Assurance",
    "Compatibility And Production Delta",
    "Later-owner Boundaries",
    "Slice 3 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    source remote as Imported\n'
            "shape Local:\n    id: Int not null\n"
            'source local: Local is postgres.table("local")\n'
            "relationship self_link:\n"
            "    endpoint manager: local\n"
            "    endpoint report: local\n"
            "relationship imported_link:\n"
            "    endpoint local_role: local\n"
            "    endpoint remote_role: Imported\n"
            "relationship pair_one:\n"
            "    endpoint left: local\n"
            "    endpoint right: Imported\n"
            "relationship pair_two:\n"
            "    endpoint left: local\n"
            "    endpoint right: Imported\n"
            "relationship broken:\n"
            "    endpoint known: local\n"
            "    endpoint missing: absent\n"
            "relationship after_broken:\n"
            "    endpoint left: local\n"
            "    endpoint right: Imported\n"
        ),
        "b.pietto": (
            "shape Remote:\n    id: Int not null\n"
            'source remote: Remote is postgres.table("remote")\n'
            "export:\n    source remote\n"
        ),
    }


def _non_concrete_files() -> dict[str, str]:
    return {
        "a.pietto": (
            "shape Row:\n    id: Int not null\n"
            'source shared: Row is postgres.table("shared")\n'
            "table shared:\n"
            "    from shared\n"
            "    select:\n"
            "        id\n"
            'source ok: Row is postgres.table("ok")\n'
            "relationship valid:\n"
            "    endpoint first: ok\n"
            "    endpoint second: ok\n"
            "relationship duplicate:\n"
            "    endpoint first: ok\n"
            "    endpoint second: ok\n"
            "relationship duplicate:\n"
            "    endpoint first: ok\n"
            "    endpoint second: ok\n"
            "relationship duplicate_roles:\n"
            "    endpoint same: ok\n"
            "    endpoint same: ok\n"
            "relationship ambiguous_target:\n"
            "    endpoint ambiguous: shared\n"
            "    endpoint known: ok\n"
            "relationship unknown_target:\n"
            "    endpoint missing: absent\n"
            "    endpoint known: ok\n"
            "relationship final:\n"
            "    endpoint first: ok\n"
            "    endpoint second: ok\n"
        )
    }


def _semantic_project(root: Path, files: dict[str, str]) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in files.items():
        (root / relative).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    result = build_empty_project_semantic_result(parsed)
    assert result.module_relation_resolutions is not None
    return result


def _environment(
    result: relationships.ProjectRelationshipSet,
    module_path: str,
) -> relationships.ProjectModuleRelationshipEnvironment:
    matches = result.find_module_path(module_path)
    assert len(matches) == 1
    return matches[0]


def _subjects_named(
    environment: relationships.ProjectModuleRelationshipEnvironment,
    name: str,
) -> tuple[relationships.ProjectRelationshipSubject, ...]:
    return tuple(
        subject for subject in environment.subjects if subject.occurrence.name == name
    )


def _observation(
    result: relationships.ProjectRelationshipSet,
) -> tuple[object, ...]:
    return tuple(
        (
            subject.occurrence.identity,
            subject.state,
            tuple(
                (
                    endpoint.identity,
                    endpoint.authored_role,
                    endpoint.authored_relation_spelling,
                    None
                    if endpoint.target is None
                    else endpoint.target.target_identity,
                )
                for endpoint in subject.occurrence.endpoints
            ),
        )
        for subject in result.subjects
    )


def test_real_relationships_retain_identity_roles_resolution_and_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path, _project_files())
    checked: list[
        tuple[tuple[RelationshipSemanticInfo, ...], tuple[Diagnostic, ...]]
    ] = []
    checker = relationships.check_relationship_metadata

    def recording_checker(
        script: Script,
        relation_symbols: Mapping[str, Definition],
    ) -> tuple[tuple[RelationshipSemanticInfo, ...], tuple[Diagnostic, ...]]:
        result = checker(script, relation_symbols)
        checked.append(result)
        return result

    monkeypatch.setattr(
        relationships,
        "check_relationship_metadata",
        recording_checker,
    )
    result = relationships.build_project_relationships(semantic)
    environment = _environment(result, "a.pietto")

    assert result.semantic_result is semantic
    assert all(
        item.module is module
        for item, module in zip(result.environments, semantic.modules, strict=True)
    )
    assert tuple(subject.occurrence.name for subject in environment.subjects) == (
        "self_link",
        "imported_link",
        "pair_one",
        "pair_two",
        "broken",
        "after_broken",
    )
    assert tuple(subject.state for subject in environment.subjects) == (
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.UNKNOWN,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
    )

    self_link = _subjects_named(environment, "self_link")[0]
    assert type(self_link) is relationships.ProjectConcreteRelationshipSubject
    parsed_input = environment.module.parsed_input
    assert parsed_input is not None
    assert self_link.occurrence.identity.module == environment.module.identity
    assert self_link.occurrence.identity.module_position == environment.module.position
    assert self_link.occurrence.identity.relationship_position == 0
    assert self_link.occurrence.relationship is parsed_input.script.relationships[0]
    first, second = self_link.occurrence.endpoints
    assert first.identity != second.identity
    assert first.authored_role == "manager"
    assert second.authored_role == "report"
    assert first.target is second.target
    assert first.target is not None
    assert first.target.target_identity.module_path == "a.pietto"

    imported = _subjects_named(environment, "imported_link")[0]
    assert type(imported) is relationships.ProjectConcreteRelationshipSubject
    imported_target = imported.occurrence.endpoints[1].target
    assert imported_target is not None
    assert (
        imported_target
        is environment.relation_environment.find_relation_name("Imported")[0]
    )
    assert imported_target.local_name == "Imported"
    assert imported_target.target_identity.module_path == "b.pietto"
    checked_imported = next(
        item
        for admitted, _diagnostics in checked
        for item in admitted
        if item.name == "imported_link"
    )
    assert imported.occurrence.semantic is checked_imported
    assert imported.occurrence.semantic is environment.semantic_relationships[1]
    imported_semantic = imported.occurrence.semantic
    assert imported_semantic is not None
    assert all(
        endpoint.semantic is semantic_endpoint
        for endpoint, semantic_endpoint in zip(
            imported.occurrence.endpoints,
            imported_semantic.endpoints,
            strict=True,
        )
    )

    pair_one = _subjects_named(environment, "pair_one")[0]
    pair_two = _subjects_named(environment, "pair_two")[0]
    assert pair_one.occurrence.identity != pair_two.occurrence.identity
    assert tuple(item.target for item in pair_one.occurrence.endpoints) == tuple(
        item.target for item in pair_two.occurrence.endpoints
    )
    assert tuple(item.authored_role for item in pair_one.occurrence.endpoints) == (
        "left",
        "right",
    )
    assert tuple(item.authored_role for item in pair_two.occurrence.endpoints) == (
        "left",
        "right",
    )

    broken = _subjects_named(environment, "broken")[0]
    after = _subjects_named(environment, "after_broken")[0]
    assert type(broken) is relationships.ProjectNonConcreteRelationshipSubject
    assert broken.state is relationships.ProjectRelationshipConstructionState.UNKNOWN
    assert [item.code for item in broken.diagnostics] == ["PIE-S2601"]
    assert type(after) is relationships.ProjectConcreteRelationshipSubject


def test_non_concrete_states_are_distinct_and_do_not_erase_concrete_subjects(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _non_concrete_files())
    result = relationships.build_project_relationships(semantic)
    environment = _environment(result, "a.pietto")

    assert len(environment.subjects) == 7
    assert tuple(subject.state for subject in environment.subjects) == (
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.AMBIGUOUS,
        relationships.ProjectRelationshipConstructionState.BLOCKED,
        relationships.ProjectRelationshipConstructionState.AMBIGUOUS,
        relationships.ProjectRelationshipConstructionState.UNKNOWN,
        relationships.ProjectRelationshipConstructionState.CONCRETE,
    )
    duplicate = _subjects_named(environment, "duplicate")
    assert len(duplicate) == 2
    assert type(duplicate[0]) is relationships.ProjectConcreteRelationshipSubject
    assert type(duplicate[1]) is relationships.ProjectNonConcreteRelationshipSubject
    assert [item.code for item in duplicate[1].diagnostics] == ["PIE-S2602"]

    roles = _subjects_named(environment, "duplicate_roles")[0]
    ambiguous = _subjects_named(environment, "ambiguous_target")[0]
    unknown = _subjects_named(environment, "unknown_target")[0]
    final = _subjects_named(environment, "final")[0]
    assert type(roles) is relationships.ProjectNonConcreteRelationshipSubject
    assert [item.code for item in roles.diagnostics] == ["PIE-S2603"]
    assert type(ambiguous) is relationships.ProjectNonConcreteRelationshipSubject
    assert ambiguous.relation_issues
    assert any(
        item.status.value == "ambiguous_local_relation_name"
        for item in ambiguous.relation_issues
    )
    assert type(unknown) is relationships.ProjectNonConcreteRelationshipSubject
    assert unknown.relation_issues == ()
    assert type(final) is relationships.ProjectConcreteRelationshipSubject
    assert relationships.ProjectRelationshipConstructionState.DEFERRED not in {
        subject.state for subject in environment.subjects
    }
    with pytest.raises(ValueError, match="belong to unresolved endpoints"):
        relationships.ProjectNonConcreteRelationshipSubject(
            occurrence=unknown.occurrence,
            state=relationships.ProjectRelationshipConstructionState.AMBIGUOUS,
            relation_issues=ambiguous.relation_issues,
        )
    cloned_issue = replace(ambiguous.relation_issues[0])
    cloned_ambiguous = replace(ambiguous, relation_issues=(cloned_issue,))
    with pytest.raises(ValueError, match="exact resolution authority"):
        replace(
            environment,
            subjects=tuple(
                cloned_ambiguous if subject is ambiguous else subject
                for subject in environment.subjects
            ),
        )


def test_carriers_reject_detached_authority_and_unreachable_deferred(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _project_files())
    result = relationships.build_project_relationships(semantic)
    environment = _environment(result, "a.pietto")
    concrete = environment.subjects[0]
    unknown = _subjects_named(environment, "broken")[0]
    assert type(concrete) is relationships.ProjectConcreteRelationshipSubject
    assert type(unknown) is relationships.ProjectNonConcreteRelationshipSubject

    first, second = concrete.occurrence.endpoints
    assert first.target is not None
    detached_endpoint = replace(first, target=replace(first.target))
    detached_occurrence = replace(
        concrete.occurrence,
        endpoints=(detached_endpoint, second),
    )
    detached_subject = relationships.ProjectConcreteRelationshipSubject(
        occurrence=detached_occurrence
    )
    with pytest.raises(ValueError, match="exact relation target"):
        replace(
            environment,
            subjects=(detached_subject, *environment.subjects[1:]),
        )

    cloned_diagnostic = replace(unknown.diagnostics[0])
    cloned_unknown = replace(unknown, diagnostics=(cloned_diagnostic,))
    with pytest.raises(ValueError, match="exact semantic diagnostic"):
        replace(
            environment,
            subjects=tuple(
                cloned_unknown if subject is unknown else subject
                for subject in environment.subjects
            ),
        )

    with pytest.raises(ValueError, match="no reachable DEFERRED"):
        relationships.ProjectNonConcreteRelationshipSubject(
            occurrence=unknown.occurrence,
            state=relationships.ProjectRelationshipConstructionState.DEFERRED,
        )

    detached_resolution = replace(environment.relation_environment)
    detached_environment = replace(
        environment,
        relation_environment=detached_resolution,
    )
    with pytest.raises(ValueError, match="exact resolution authority"):
        replace(
            result,
            environments=tuple(
                detached_environment if item is environment else item
                for item in result.environments
            ),
        )


def test_ordering_is_stable_and_uses_no_cwd_or_environment_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path / "project", _project_files())
    first = relationships.build_project_relationships(semantic)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv("PIETTO_UNRELATED_RELATIONSHIP_VALUE", "ignored")
    second = relationships.build_project_relationships(semantic)

    assert _observation(first) == _observation(second)
    assert tuple(item.module for item in first.environments) == semantic.modules
    assert tuple(item.module for item in second.environments) == semantic.modules


def test_private_carriers_are_nominal_frozen_and_keep_later_fields_absent(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _project_files())
    result = relationships.build_project_relationships(semantic)
    subject = _environment(result, "a.pietto").subjects[0]

    assert relationships.__all__ == ()
    assert tuple(relationships.ProjectRelationshipConstructionState) == (
        relationships.ProjectRelationshipConstructionState.CONCRETE,
        relationships.ProjectRelationshipConstructionState.UNKNOWN,
        relationships.ProjectRelationshipConstructionState.DEFERRED,
        relationships.ProjectRelationshipConstructionState.BLOCKED,
        relationships.ProjectRelationshipConstructionState.AMBIGUOUS,
    )
    assert tuple(
        item.name
        for item in fields(relationships.ProjectRelationshipDeclarationIdentity)
    ) == ("module", "module_position", "relationship_position")
    assert tuple(
        item.name for item in fields(relationships.ProjectRelationshipEndpointIdentity)
    ) == ("declaration", "endpoint_position")
    assert not {
        "name",
        "left",
        "right",
        "cardinality",
        "match_condition",
        "key",
        "fd",
        "grain",
        "fanout",
        "path",
        "join",
    } & {
        item.name
        for carrier in (
            relationships.ProjectRelationshipDeclarationIdentity,
            relationships.ProjectRelationshipEndpointIdentity,
            relationships.ProjectRelationshipEndpointOccurrence,
            relationships.ProjectRelationshipDeclarationOccurrence,
            relationships.ProjectConcreteRelationshipSubject,
            relationships.ProjectNonConcreteRelationshipSubject,
        )
        for item in fields(carrier)
    }
    with pytest.raises(FrozenInstanceError):
        subject.occurrence.identity.relationship_position = 4  # type: ignore[misc]


def test_existing_public_semantic_ir_and_project_ir_shapes_are_unchanged() -> None:
    assert tuple(item.name for item in fields(SemanticModel)) == (
        "mode",
        "type_symbols",
        "callable_symbols",
        "relation_symbols",
        "type_resolutions",
        "type_expansions",
        "type_nullability",
        "decimal_precision_scales",
        "decimal_expression_precision_scales",
        "source_row_schemas",
        "from_resolutions",
        "relation_row_schemas",
        "expression_value_types",
        "window_expression_analyses",
        "named_window_namespaces",
        "result_predicates",
        "let_scopes",
        "relationships",
    )
    assert tuple(item.name for item in fields(RelationIR)) == (
        "symbol",
        "name",
        "kind",
        "source",
        "filter",
        "projections",
        "row_schema",
        "span",
        "order_by",
        "limit",
        "group_keys",
        "result_predicate",
        "named_windows",
    )
    assert tuple(item.name for item in fields(ScriptIR)) == ("definitions",)
    assert tuple(item.name for item in ProjectIRLogicalOperatorKind) == (
        "RELATION_INPUT",
        "ROW_FILTER",
        "GROUP_AGGREGATE",
        "RESULT_FILTER",
        "WINDOW_EVALUATION",
        "FINAL_PROJECTION",
        "RELATION_ORDERING",
        "LIMIT",
    )


def test_source_uses_existing_resolution_and_semantic_authority_without_scans() -> None:
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.model",
        "pietto._project.module_carrier",
        "pietto._project.module_relation_resolution",
        "pietto.semantic.relationship_metadata",
        "pietto.semantic.model",
    } <= facts.imported_modules
    assert (
        not {
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
        "cwd",
        "sha256",
        "hash",
    ):
        assert forbidden not in facts.identifiers
    for required in (
        "check_relationship_metadata",
        "find_module_path",
        "find_relation_name",
        "target_occurrence",
        "semantic_relationships",
    ):
        assert required in facts.identifiers


def test_contract_locks_slice_owner_non_goals_handoff_and_gate() -> None:
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
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "d3a698a3a4916cac39a0852bb43ef4243876b18e",
        "33463294917",
        "existing public RelationshipSemanticInfo != private Project relationship occurrence",
        "relationship declaration occurrence != endpoint occurrence",
        "endpoint local role/name != endpoint identity",
        "CONCRETE UNKNOWN DEFERRED BLOCKED AMBIGUOUS",
        "deterministic order != semantic identity",
        "field correspondences",
        "UNIQUE/key semantics",
        "value FD engine",
        "grain",
        "referential coverage/cardinality",
        "relationship paths/fanout",
        "authored JOIN syntax/use",
        "Project IR JOIN region",
        "multi-fact alignment",
        "relationship import/export",
        "public relationship schema",
        "Phase 62 Slice 3 — Exact Field Correspondences, ON/WHERE Separation, Equality/Null Behavior, And Constraint-Scope Boundary",
        "Add Phase 62 relationship identity foundation",
        "PASS — PHASE62_SLICE2_RELATIONSHIP_DECLARATION_IDENTITY_ENDPOINT_ROLES_MODULE_LOCAL_RESOLUTION_CONSTRUCTION_STATES_END_TO_END",
    ):
        assert evidence in normalized
