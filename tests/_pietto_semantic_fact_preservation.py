from __future__ import annotations

from dataclasses import replace
from itertools import permutations
from pathlib import Path
from typing import cast

import pietto._project.check as project_check
import pietto._project.module_semantic_fact_preservation as preservation
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    QueryDef,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/_project/module_semantic_fact_preservation.py"


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in sources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _semantic_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, sources, schema_version=schema_version)
    )
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _fact_set(
    semantic: ProjectSemanticResult,
) -> preservation.ProjectModuleSemanticFactSet:
    facts = semantic.module_semantic_facts
    assert facts is not None
    return facts


def _relation(
    semantic: ProjectSemanticResult,
    module_path: str,
    name: str,
) -> preservation.ProjectModuleRelationSemanticFacts:
    matches = tuple(
        fact
        for environment in _fact_set(semantic).environments
        for fact in environment.relation_facts
        if fact.owner.identity.module_path == module_path
        and fact.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _replace_relation_in_final_semantic(
    semantic: ProjectSemanticResult,
    original: preservation.ProjectModuleRelationSemanticFacts,
    replacement: preservation.ProjectModuleRelationSemanticFacts,
) -> ProjectSemanticResult:
    facts = _fact_set(semantic)
    environments = tuple(
        replace(
            environment,
            relation_facts=tuple(
                replacement if fact is original else fact
                for fact in environment.relation_facts
            ),
        )
        if any(fact is original for fact in environment.relation_facts)
        else environment
        for environment in facts.environments
    )
    replaced_facts = replace(facts, environments=environments)
    return replace(semantic, module_semantic_facts=replaced_facts)


def _replace_window_in_final_semantic(
    semantic: ProjectSemanticResult,
    relation: preservation.ProjectModuleRelationSemanticFacts,
    original: preservation.ProjectModuleWindowOutputFact,
    replacement: preservation.ProjectModuleWindowOutputFact,
) -> ProjectSemanticResult:
    replaced_relation = replace(
        relation,
        window_outputs=tuple(
            replacement if output is original else output
            for output in relation.window_outputs
        ),
    )
    return _replace_relation_in_final_semantic(
        semantic,
        relation,
        replaced_relation,
    )


def _library_source(*, export_relation: str = "table projected") -> str:
    return (
        "shape Row:\n"
        "    id: Int\n"
        "    amount: Int\n"
        "    name: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount\n"
        "        name\n"
        f"export {export_relation}\n"
    )


def _prefix() -> str:
    return (
        "shape Row:\n"
        "    id: Int\n"
        "    amount: Int\n"
        "    category: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
    )


def _query(body: str) -> str:
    return _prefix() + "query result:\n    from rows\n" + body


def _unavailable_candidate_body(
    expressions: tuple[str, ...],
    *,
    relation_qualifier: str,
) -> str:
    lines = [f"    let key = {expression}" for expression in expressions]
    lines.extend(
        (
            f"    let qualified_key = {relation_qualifier}.id",
            "    let wrong_qualified_key = other.id",
        )
    )
    lines.extend(
        (
            "    group by:",
            "        id",
            "    select:",
            "        projected = key",
            f"        qualified_projected = {relation_qualifier}.id",
            "        wrong_qualified_projected = other.id",
        )
    )
    lines.extend(f"        total = sum({expression})" for expression in expressions)
    lines.extend(
        (
            "    having:",
            "        total > 0",
            "    order by:",
            "        total",
        )
    )
    return "\n".join(lines) + "\n"


def _assert_unavailable_candidate_matrix(
    tmp_path: Path,
    *,
    source_head: str,
    relation_status: ProjectRelationRowSchemaStatus,
    relation_reason: ProjectRelationRowSchemaReason,
    bucket_status: preservation.ProjectModuleCandidateBucketStatus,
    relation_qualifier: str,
    expect_issues: bool = False,
) -> None:
    expression_orders = (
        (),
        ("id",),
        ("id", "amount"),
        *tuple(permutations(("id", "amount", "id + amount"))),
    )
    for case_ordinal, expressions in enumerate(expression_orders):
        _, semantic = _semantic_project(
            tmp_path / f"case-{case_ordinal}",
            {
                "main.pietto": source_head
                + _unavailable_candidate_body(
                    expressions,
                    relation_qualifier=relation_qualifier,
                )
            },
        )
        relation = _relation(semantic, "main.pietto", "result")
        definition = cast(QueryDef, relation.owner.definition)
        expected_lets = (
            ()
            if definition.let_clause is None
            else tuple(
                binding
                for binding in definition.let_clause.bindings
                if binding.name == "key"
            )
        )
        expected_outputs = tuple(
            item for item in definition.select_items if item.alias == "total"
        )
        projected = next(
            item for item in relation.select_facts if item.output_name == "projected"
        )
        assert relation.state.status is relation_status
        assert relation.state.reason is relation_reason
        assert relation.aggregate_result_facts == ()
        assert all(item.aggregate_result_fact is None for item in relation.select_facts)
        assert len(projected.references) == 1
        assert projected.references[0].let_candidates == expected_lets
        assert projected.references[0].status is bucket_status
        qualified_references = (
            next(
                fact
                for fact in relation.let_bindings
                if fact.binding.name == "qualified_key"
            ).references[0],
            next(
                fact
                for fact in relation.let_bindings
                if fact.binding.name == "wrong_qualified_key"
            ).references[0],
            next(
                fact
                for fact in relation.select_facts
                if fact.output_name == "qualified_projected"
            ).references[0],
            next(
                fact
                for fact in relation.select_facts
                if fact.output_name == "wrong_qualified_projected"
            ).references[0],
        )
        assert tuple(reference.role for reference in qualified_references) == (
            preservation.ProjectModuleFactOccurrenceRole.LET_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.LET_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
        )
        for reference in qualified_references:
            assert type(reference.expression) is DottedNameExpr
            assert reference.input_field is None
            assert reference.let_candidates == ()
            assert reference.selected_output_candidates == ()
            assert reference.status is bucket_status
        dependencies = {fact.role: fact for fact in relation.clause_dependencies}
        group_key = dependencies[preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY]
        satisfying = dependencies[
            preservation.ProjectModuleFactOccurrenceRole.SATISFYING
        ]
        grouped_order = dependencies[
            preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
        ]
        assert group_key.status is bucket_status
        assert group_key.target_occurrences == ()
        for dependency in (satisfying, grouped_order):
            assert dependency.status is bucket_status
            assert dependency.target_occurrences == expected_outputs
            assert dependency.target_fields == ()
            assert dependency.aggregate_result_facts == ()
        if relation_status is ProjectRelationRowSchemaStatus.UNKNOWN:
            assert relation.state.schema is not None
            assert relation.state.schema.fields == {}
        else:
            assert relation.state.schema is None
        if expect_issues:
            assert _fact_set(semantic).issues


def _window_call(identity: str) -> str:
    if identity in {
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
    }:
        return f"{identity}()"
    if identity == "ntile":
        return "ntile(4)"
    if identity == "lag":
        return "lag(amount, 2, amount)"
    if identity in {"first_value", "last_value"}:
        return f"{identity}(amount)"
    if identity == "nth_value":
        return "nth_value(amount, 2)"
    return "lead(amount, 0, amount)"


def _window_lines(identities: tuple[str, ...]) -> str:
    lines = ["    select:", "        id"]
    for position, identity in enumerate(identities):
        lines.append(
            f"        w{position} = {_window_call(identity)} window(partition by category order by id desc)"
        )
    return "\n".join(lines) + "\n"
