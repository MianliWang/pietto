from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType

import pytest

import pietto._project.module_attribution as attribution
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-output-identity-authority-readiness-continuation-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/module_attribution.py"
SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority And Observed Blocker",
    "Frozen Reader And Changed-path Closure",
    "Identity And Lineage Architecture Decision",
    "Complete Semantic Output Attribution",
    "Legacy-lineage Reconciliation",
    "Build Direction And Root Integrity",
    "Fact-set Integrity And Lookup",
    "Phase 61 Integration Boundary",
    "Determinism Immutability And Privacy",
    "Focused Assurance Contract",
    "Integration Non-goals",
    "Slice 5 Resume Handoff",
    "Gate Lifecycle And Publication",
)


def _source() -> str:
    return """shape Row:
    id: Int not null
    amount: Int nullable
    category: Text nullable
source rows: Row is postgres.table("rows")
query direct:
    from rows
    select:
        id
        amount
query renamed:
    from rows
    select:
        key = id
        amount
query grouped:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
query aggregate_only:
    from rows
    select:
        total = sum(amount)
query windowed:
    from rows
    select:
        id
        ranking = row_number() window:
            order by:
                id
query mixed:
    from rows
    group by:
        category
    select:
        category
        total = sum(amount)
        ranking = row_number() window:
            order by:
                total desc
query same_a:
    from rows
    select:
        id
query same_b:
    from rows
    select:
        id
query broken:
    from rows
    select:
        missing
"""


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parse_result = project_check.check_project_parse_only(root)
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _relation(
    semantic: ProjectSemanticResult,
    name: str,
) -> ProjectModuleRelationSemanticFacts:
    fact_set = semantic.module_semantic_facts
    assert fact_set is not None
    matches = tuple(
        relation
        for environment in fact_set.environments
        for relation in environment.relation_facts
        if relation.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _owner(
    relation: ProjectModuleRelationSemanticFacts,
) -> attribution.ProjectDeclarationOccurrenceIdentity:
    occurrence = relation.owner
    return attribution.ProjectDeclarationOccurrenceIdentity(
        identity=occurrence.identity,
        module_position=occurrence.module_position,
        declaration_position=occurrence.declaration_position,
    )


def test_controlling_contract_locks_decision_authority_scope_and_handoff() -> None:
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
        "RELATION_OUTPUT_IDENTITY_COUPLED_TO_DIRECT_LINEAGE_AVAILABILITY",
        "6359867c7e9c51d9b59bd23642d7bd2492b24862",
        "ba3d57d0b7217cbf4ec47c2ec6b4fae40c8a3d02",
        "33317947197",
        "A2/M9/D0",
        "output-field occurrence identity != row-lineage availability",
        "ProjectModuleRelationOutputFieldAttribution",
        "`ProjectModuleRowFieldIdentity` remains the single canonical row-field "
        "identity domain",
        "relation resolution -> semantic facts -> attribution completion",
        "Phase 61 route remains exactly 12 slices",
        "Add complete Project relation output identities",
        "PASS — PHASE61_SLICE5_OUTPUT_IDENTITY_AUTHORITY_READINESS_"
        "CONTINUATION_END_TO_END",
        "Slice 5 remains next / unstarted",
    ):
        assert evidence in normalized


def test_direct_and_renamed_identities_reuse_exact_existing_lineage_objects(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    facts = semantic.module_attribution_facts
    assert facts is not None
    for name, expected_names in (
        ("direct", ("id", "amount")),
        ("renamed", ("key", "amount")),
    ):
        relation = _relation(semantic, name)
        owner = _owner(relation)
        outputs = facts.find_relation_output_fields(owner)
        lineages = facts.find_row_lineage(owner)
        assert len(lineages) == 1
        lineage = lineages[0]
        assert lineage.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert tuple(item.identity.name for item in outputs) == expected_names
        assert len(outputs) == len(lineage.fields)
        assert all(
            output.identity is field_lineage.field
            for output, field_lineage in zip(
                outputs,
                lineage.fields,
                strict=True,
            )
        )


@pytest.mark.parametrize(
    ("name", "expected_names"),
    (
        ("grouped", ("category", "total")),
        ("aggregate_only", ("total",)),
        ("windowed", ("id", "ranking")),
        ("mixed", ("category", "total", "ranking")),
    ),
)
def test_concrete_semantic_outputs_are_complete_while_legacy_lineage_is_deferred(
    tmp_path: Path,
    name: str,
    expected_names: tuple[str, ...],
) -> None:
    semantic = _semantic_project(tmp_path)
    facts = semantic.module_attribution_facts
    assert facts is not None
    relation = _relation(semantic, name)
    owner = _owner(relation)
    assert relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    outputs = facts.find_relation_output_fields(owner)
    assert tuple(item.identity.name for item in outputs) == expected_names
    assert tuple(item.identity.field_position for item in outputs) == tuple(
        range(len(expected_names))
    )
    assert all(item.identity.owner == owner for item in outputs)
    assert relation.state.schema is not None
    semantic_fields = tuple(relation.state.schema.fields.values())
    assert len(outputs) == len(semantic_fields)
    assert all(
        item.relation is relation and item.semantic_field is semantic_field
        for item, semantic_field in zip(outputs, semantic_fields, strict=True)
    )
    lineage = facts.find_row_lineage(owner)[0]
    assert lineage.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert lineage.fields == ()


def test_nonconcrete_relation_has_no_output_identities_and_equal_names_do_not_merge(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    facts = semantic.module_attribution_facts
    assert facts is not None
    broken = _relation(semantic, "broken")
    assert broken.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
    assert facts.find_relation_output_fields(_owner(broken)) == ()

    first = facts.find_relation_output_fields(_owner(_relation(semantic, "same_a")))
    second = facts.find_relation_output_fields(_owner(_relation(semantic, "same_b")))
    assert len(first) == len(second) == 1
    assert first[0].identity.name == second[0].identity.name == "id"
    assert first[0].identity != second[0].identity
    assert first[0].identity.owner != second[0].identity.owner


def test_fact_set_lookup_integrity_is_tuple_backed_complete_and_no_winner(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    facts = semantic.module_attribution_facts
    assert facts is not None
    relation = _relation(semantic, "mixed")
    outputs = facts.find_relation_output_fields(_owner(relation))
    assert type(outputs) is tuple
    assert isinstance(facts._relation_output_fields_by_owner, MappingProxyType)
    assert isinstance(facts._relation_output_fields_by_identity, MappingProxyType)
    assert all(
        facts.find_relation_output_field(item.identity) == (item,) for item in outputs
    )
    with pytest.raises(TypeError):
        facts._relation_output_fields_by_owner[_owner(relation)] = ()  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        facts.relation_output_fields = ()  # type: ignore[misc]
    with pytest.raises(ValueError, match="must not repeat exact facts"):
        replace(
            facts,
            relation_output_fields=(outputs[0], outputs[0]),
        )
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(facts, relation_output_fields=())


def test_semantic_to_attribution_dependency_is_exact_and_downstream_roots_close(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path)
    attribution_facts = semantic.module_attribution_facts
    semantic_facts = semantic.module_semantic_facts
    package_identity = semantic.module_package_identity_facts
    inspection = semantic.module_inspection_facts
    assert attribution_facts is not None
    assert semantic_facts is not None
    assert package_identity is not None
    assert inspection is not None
    assert attribution_facts._authority.semantic_facts is semantic_facts
    assert package_identity.authority.attribution is attribution_facts
    assert package_identity.authority.semantic is semantic_facts
    assert inspection.authority.attribution is attribution_facts
    assert inspection.authority.semantic is semantic_facts


def test_identity_domain_and_legacy_lineage_kinds_are_not_widened() -> None:
    assert tuple(attribution.ProjectModuleRowFieldKind) == (
        attribution.ProjectModuleRowFieldKind.SHAPE_FIELD,
        attribution.ProjectModuleRowFieldKind.SOURCE_FIELD,
        attribution.ProjectModuleRowFieldKind.RELATION_OUTPUT,
    )
    assert tuple(attribution.ProjectModuleProjectionKind) == (
        attribution.ProjectModuleProjectionKind.DIRECT,
        attribution.ProjectModuleProjectionKind.RENAMED,
    )
    assert not any(
        name in vars(attribution)
        for name in (
            "ProjectModuleSemanticOutputIdentity",
            "ProjectModuleAggregateOutputIdentity",
            "ProjectModuleWindowOutputIdentity",
        )
    )
    assert tuple(
        item.name
        for item in fields(attribution.ProjectModuleRelationOutputFieldAttribution)
    ) == ("identity", "relation", "semantic_field")


def test_output_identity_formation_is_hash_seed_and_cwd_independent(
    tmp_path: Path,
) -> None:
    script = f"""
from pathlib import Path
from pietto._project import check as project_check
from pietto._project.model import build_empty_project_semantic_result
root = Path.cwd()
(root / 'pietto.toml').write_text('schema_version = 2\\n\\n[sources]\\ninclude = [\"*.pietto\"]\\n', encoding='utf-8')
(root / 'main.pietto').write_text({_source()!r}, encoding='utf-8')
parse_result = project_check.check_project_parse_only(root)
semantic = build_empty_project_semantic_result(parse_result)
facts = semantic.module_attribution_facts
assert facts is not None
print(tuple((item.identity.owner.module_position, item.identity.owner.declaration_position, item.identity.field_position, item.identity.name, item.semantic_field.resolved_type.name) for item in facts.relation_output_fields))
"""
    outputs = []
    for seed, directory in (("1", tmp_path / "first"), ("888", tmp_path / "second")):
        directory.mkdir()
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            (sys.executable, "-c", script),
            cwd=directory,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
    assert str(tmp_path) not in outputs[0]


def test_project_ir_sql_and_public_surfaces_remain_unintegrated() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "ProjectIRStructuralStage",
        "ProjectIRPropertyStage",
        "ProjectIRLogicalOperatorStage",
        "build_project_ir",
        "render_relation_sql",
    ):
        assert forbidden not in source
    public_readers = (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        REPO_ROOT / "src/pietto/ir/model.py",
        REPO_ROOT / "src/pietto/sql/relations.py",
        REPO_ROOT / "src/pietto/sql/mysql_relations.py",
    )
    assert all(
        "ProjectModuleRelationOutputFieldAttribution"
        not in path.read_text(encoding="utf-8")
        for path in public_readers
    )
