from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowField,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_semantic_fact_preservation import _direct_name_leaves
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdge,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
    _child_expressions,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFact,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
    ProjectRowLineageSegment,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import (
    CastExpr,
    ConditionalExpr,
    Expression,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Nullability,
    QueryDef,
    SourceDef,
    Span,
    TableDef,
    TypeExpr,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

ROW_LINEAGE_PRIVATE_JSON_FACTS = (
    "relation_row_lineages",
    "ProjectRelationRowLineage",
    "ProjectRowLineageSegment",
    "ProjectRowLineageFact",
    "ProjectRowLineageStatus",
    "ProjectRowLineageReason",
    "let_binding",
    "source_field",
    "upstream_field",
    "output_field",
    "direct_projection",
    "renamed_projection",
    "computed_expression",
    "let_output",
    "let_expression",
    "transitive_dependency",
    "lineage",
    "dependency",
    "relation_row_dependency_graphs",
    "relation_row_schemas",
    "relation_let_scope_facts",
    "ProjectRowSchema",
    "ProjectRowField",
    "provenance",
    "direct_source_concrete",
    "missing_dependency_graph",
)


def test_row_lineage_carriers_are_private_frozen_dataclasses() -> None:
    for model_type in (
        ProjectRowLineageSegment,
        ProjectRowLineageFact,
        ProjectRelationRowLineage,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    output_segment = ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.OUTPUT_FIELD,
        name="id",
        relation_name="projected",
        output_name="id",
    )
    source_segment = ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.SOURCE_FIELD,
        name="users.id",
        source_name="users",
        field_name="id",
    )
    fact = ProjectRowLineageFact(
        kind=ProjectRowLineageFactKind.DIRECT_PROJECTION,
        output_segment=output_segment,
        upstream_segment=source_segment,
    )
    lineage = ProjectRelationRowLineage(
        status=ProjectRowLineageStatus.CONCRETE,
        reason=ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
        facts=(fact,),
    )

    assert lineage.facts == (fact,)
    assert not hasattr(lineage, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(lineage, "facts", ())


def test_direct_and_renamed_source_projection_lineage_is_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert lineage.status is ProjectRowLineageStatus.CONCRETE
    assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert _all_fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.RENAMED_PROJECTION,
            "user_email",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.email",
        ),
    )


def test_relation_backed_lineage_preserves_immediate_and_adds_transitive(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        user_id = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    lineage = semantic_result.model.relation_row_lineages[exported]

    assert lineage.status is ProjectRowLineageStatus.CONCRETE
    assert lineage.reason is ProjectRowLineageReason.RELATION_UPSTREAM_CONCRETE
    assert _all_fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.RENAMED_PROJECTION,
            "user_id",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.id",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "user_id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
    )


def test_computed_alias_lineage_is_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert _all_fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_selected_let_derived_lineage_is_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let total = score + bonus\n"
            "    select:\n"
            "        id\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    assert _all_fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.LET_OUTPUT,
            "total",
            ProjectRowLineageSegmentKind.LET_BINDING,
            "total",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_non_concrete_row_schema_states_produce_non_concrete_lineage(
    tmp_path: Path,
) -> None:
    unknown_parse, unknown_semantic = _project_semantic_result(
        _project(
            tmp_path / "unknown",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )
    grouped_parse, grouped_semantic = _project_semantic_result(
        _project(
            tmp_path / "grouped",
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )
    cycle_parse, cycle_semantic = _project_semantic_result(
        _project(
            tmp_path / "cycle",
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
            include_source=False,
        )
    )

    assert unknown_semantic.model is not None
    broken = _derived_definition(unknown_parse, "broken")
    broken_lineage = unknown_semantic.model.relation_row_lineages[broken]
    assert broken_lineage.status is ProjectRowLineageStatus.UNKNOWN
    assert broken_lineage.reason is ProjectRowLineageReason.UNKNOWN_SCHEMA
    assert broken_lineage.facts == ()

    assert grouped_semantic.model is not None
    grouped = _derived_definition(grouped_parse, "grouped")
    grouped_lineage = grouped_semantic.model.relation_row_lineages[grouped]
    assert grouped_lineage.status is ProjectRowLineageStatus.CONCRETE
    assert grouped_lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert _all_fact_values(grouped_lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "status",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.status",
        ),
        (
            ProjectRowLineageFactKind.AGGREGATE_ARGUMENT,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
    )

    assert cycle_semantic.model is not None
    first = _derived_definition(cycle_parse, "first")
    first_lineage = cycle_semantic.model.relation_row_lineages[first]
    assert first_lineage.status is ProjectRowLineageStatus.BLOCKED
    assert first_lineage.reason is ProjectRowLineageReason.CYCLE_BLOCKED
    assert first_lineage.facts == ()


def test_project_json_v2_keeps_row_lineage_private(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_lineages
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    for private_fact in ROW_LINEAGE_PRIVATE_JSON_FACTS:
        assert private_fact not in serialized


def test_row_lineage_module_does_not_call_full_semantic_analyze() -> None:
    module = (REPO_ROOT / "src/pietto/_project/row_lineage.py").read_text(
        encoding="utf-8"
    )

    assert "semantic_api.analyze" not in module
    assert "from pietto.semantic import analyze" not in module
    assert "import pietto.semantic as semantic_api" not in module


def _all_fact_values(
    lineage: ProjectRelationRowLineage,
) -> tuple[
    tuple[
        ProjectRowLineageFactKind,
        str,
        ProjectRowLineageSegmentKind,
        str,
    ],
    ...,
]:
    return tuple(
        (
            fact.kind,
            fact.output_segment.name,
            fact.upstream_segment.kind,
            fact.upstream_segment.name,
        )
        for fact in lineage.facts
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(
    root: Path,
    relation_source: str,
    *,
    include_source: bool = True,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    source_prefix = (
        "shape User:\n"
        "    id: Int\n"
        "    email: Text | None\n"
        "    score: Int\n"
        "    bonus: Int | None\n"
        "    status: Text\n"
    )
    if include_source:
        source_prefix += 'source users: User = postgres.table("users")\n'
    (root / "models.pietto").write_text(
        source_prefix + relation_source,
        encoding="utf-8",
    )
    return root


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Missing derived definition: {name}")


COMPUTED_LINEAGE_PRIVATE_JSON_FACTS = (
    "relation_row_lineages",
    "ProjectRelationRowLineage",
    "ProjectRowLineageSegment",
    "ProjectRowLineageFact",
    "ProjectRowLineageStatus",
    "ProjectRowLineageReason",
    "LET_BINDING",
    "COMPUTED_EXPRESSION",
    "LET_OUTPUT",
    "LET_EXPRESSION",
    "TRANSITIVE_DEPENDENCY",
    "let_binding",
    "computed_expression",
    "let_output",
    "let_expression",
    "transitive_dependency",
    "lineage",
    "dependency",
    "relation_row_dependency_graphs",
    "relation_row_schemas",
    "relation_let_scope_facts",
    "ProjectRowSchema",
    "ProjectRowField",
    "provenance",
    "let facts",
    "reason",
    "direct_source_concrete",
)


def test_lineage_enum_extensions_are_private_frozen_carriers() -> None:
    segment = ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.LET_BINDING,
        name="total",
        relation_name="projected",
        binding_name="total",
    )
    fact = ProjectRowLineageFact(
        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
        output_segment=segment,
        upstream_segment=ProjectRowLineageSegment(
            kind=ProjectRowLineageSegmentKind.SOURCE_FIELD,
            name="users.score",
            source_name="users",
            field_name="score",
        ),
    )
    lineage = ProjectRelationRowLineage(
        status=ProjectRowLineageStatus.CONCRETE,
        reason=ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
        facts=(fact,),
    )

    assert ProjectRowLineageSegmentKind.LET_BINDING.value == "let_binding"
    assert ProjectRowLineageFactKind.COMPUTED_EXPRESSION.value == (
        "computed_expression"
    )
    assert ProjectRowLineageFactKind.LET_OUTPUT.value == "let_output"
    assert ProjectRowLineageFactKind.LET_EXPRESSION.value == "let_expression"
    assert ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY.value == (
        "transitive_dependency"
    )
    for model_type in (
        ProjectRowLineageSegment,
        ProjectRowLineageFact,
        ProjectRelationRowLineage,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")
    assert lineage.facts == (fact,)
    with pytest.raises(FrozenInstanceError):
        setattr(segment, "binding_name", "other")


def test_computed_alias_lineage_records_source_dependencies_without_call_segments(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        normalized = lower(trim(status))\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert schema.fields["total"].field_def is None
    assert schema.fields["total"].provenance is not None
    assert (
        schema.fields["total"].provenance.kind
        is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    )
    assert _fact_values(lineage, output_name="total") == (
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )
    assert _fact_values(lineage, output_name="normalized") == (
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "normalized",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.status",
        ),
    )
    assert "lower" not in _lineage_segment_names(lineage)
    assert "trim" not in _lineage_segment_names(lineage)


def test_selected_let_output_and_expression_lineage_are_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let total = score + bonus\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    assert (
        ProjectRowLineageFactKind.LET_OUTPUT,
        ProjectRowLineageSegmentKind.OUTPUT_FIELD,
        "total",
        ProjectRowLineageSegmentKind.LET_BINDING,
        "total",
    ) in _fact_values(lineage, output_name="total")
    assert _fact_values(
        lineage,
        output_name="total",
        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
    ) == (
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )
    assert _fact_values(
        lineage,
        output_name="total",
        output_kind=ProjectRowLineageSegmentKind.LET_BINDING,
        kind=ProjectRowLineageFactKind.LET_EXPRESSION,
    ) == (
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            ProjectRowLineageSegmentKind.LET_BINDING,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            ProjectRowLineageSegmentKind.LET_BINDING,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_later_let_binding_keeps_earlier_let_segment_and_source_lineage(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let subtotal = score + bonus\n"
            "    let adjusted = subtotal + score\n"
            "    select:\n"
            "        adjusted\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert (
        ProjectRowLineageFactKind.LET_EXPRESSION,
        ProjectRowLineageSegmentKind.LET_BINDING,
        "adjusted",
        ProjectRowLineageSegmentKind.LET_BINDING,
        "subtotal",
    ) in _fact_values(
        lineage,
        output_name="adjusted",
        output_kind=ProjectRowLineageSegmentKind.LET_BINDING,
        kind=ProjectRowLineageFactKind.LET_EXPRESSION,
    )
    assert _fact_values(
        lineage,
        output_name="subtotal",
        output_kind=ProjectRowLineageSegmentKind.LET_BINDING,
        kind=ProjectRowLineageFactKind.LET_EXPRESSION,
    ) == (
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            ProjectRowLineageSegmentKind.LET_BINDING,
            "subtotal",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            ProjectRowLineageSegmentKind.LET_BINDING,
            "subtotal",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )
    assert _fact_values(
        lineage,
        output_name="adjusted",
        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
    ) == (
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.LET_BINDING,
            "subtotal",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_multi_hop_direct_and_renamed_lineage_preserves_immediate_and_transitive(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        user_id = id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        final_id = user_id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    lineage = semantic_result.model.relation_row_lineages[exported]
    facts = _fact_values(lineage, output_name="final_id")

    assert facts == (
        (
            ProjectRowLineageFactKind.RENAMED_PROJECTION,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "final_id",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.user_id",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "final_id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
    )
    assert len(facts) == len(set(facts))


def test_computed_alias_over_relation_backed_field_expands_to_source_lineage(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        boosted = total + 1\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    lineage = semantic_result.model.relation_row_lineages[exported]

    assert _fact_values(
        lineage,
        output_name="boosted",
        kind=ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
    ) == (
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "boosted",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.total",
        ),
    )
    assert _fact_values(
        lineage,
        output_name="boosted",
        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
    ) == (
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "boosted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "boosted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_let_expression_over_relation_backed_field_expands_to_source_lineage(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n"
            "query projected:\n"
            "    from seed\n"
            "    let adjusted = total + 1\n"
            "    select:\n"
            "        adjusted\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert _fact_values(
        lineage,
        output_name="adjusted",
        output_kind=ProjectRowLineageSegmentKind.LET_BINDING,
        kind=ProjectRowLineageFactKind.LET_EXPRESSION,
    ) == (
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            ProjectRowLineageSegmentKind.LET_BINDING,
            "adjusted",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.total",
        ),
    )
    assert _fact_values(
        lineage,
        output_name="adjusted",
        kind=ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
    ) == (
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.total",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            ProjectRowLineageSegmentKind.OUTPUT_FIELD,
            "adjusted",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_non_concrete_lineage_is_empty_while_grouped_aggregate_lineage_is_concrete(
    tmp_path: Path,
) -> None:
    unknown_parse, unknown_semantic = _project_semantic_result(
        _project(
            tmp_path / "unknown",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )
    grouped_parse, grouped_semantic = _project_semantic_result(
        _project(
            tmp_path / "grouped",
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )
    cycle_parse, cycle_semantic = _project_semantic_result(
        _project(
            tmp_path / "cycle",
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
            include_source=False,
        )
    )

    assert unknown_semantic.model is not None
    broken = _derived_definition(unknown_parse, "broken")
    broken_lineage = unknown_semantic.model.relation_row_lineages[broken]
    assert broken_lineage.status is ProjectRowLineageStatus.UNKNOWN
    assert broken_lineage.facts == ()

    assert grouped_semantic.model is not None
    grouped = _derived_definition(grouped_parse, "grouped")
    grouped_lineage = grouped_semantic.model.relation_row_lineages[grouped]
    assert grouped_lineage.status is ProjectRowLineageStatus.CONCRETE
    assert grouped_lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert tuple(
        (
            fact.kind,
            fact.output_segment.name,
            fact.upstream_segment.kind,
            fact.upstream_segment.name,
        )
        for fact in grouped_lineage.facts
    ) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "status",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.status",
        ),
        (
            ProjectRowLineageFactKind.AGGREGATE_ARGUMENT,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
    )

    assert cycle_semantic.model is not None
    first = _derived_definition(cycle_parse, "first")
    first_lineage = cycle_semantic.model.relation_row_lineages[first]
    assert first_lineage.status is ProjectRowLineageStatus.BLOCKED
    assert first_lineage.reason is ProjectRowLineageReason.CYCLE_BLOCKED
    assert first_lineage.facts == ()


def test_project_json_v2_keeps_computed_let_multi_hop_lineage_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    let total = score + bonus\n"
            "    select:\n"
            "        total\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        boosted = total + 1\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_lineages
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    for private_fact in COMPUTED_LINEAGE_PRIVATE_JSON_FACTS:
        assert private_fact not in serialized


def _fact_values(
    lineage: ProjectRelationRowLineage,
    *,
    output_name: str,
    output_kind: ProjectRowLineageSegmentKind = ProjectRowLineageSegmentKind.OUTPUT_FIELD,
    kind: ProjectRowLineageFactKind | None = None,
) -> tuple[
    tuple[
        ProjectRowLineageFactKind,
        ProjectRowLineageSegmentKind,
        str,
        ProjectRowLineageSegmentKind,
        str,
    ],
    ...,
]:
    values = []
    for fact in lineage.facts:
        if kind is not None and fact.kind is not kind:
            continue
        if fact.output_segment.kind is not output_kind:
            continue
        if _segment_display_name(fact.output_segment) != output_name:
            continue
        values.append(
            (
                fact.kind,
                fact.output_segment.kind,
                _segment_display_name(fact.output_segment),
                fact.upstream_segment.kind,
                _segment_display_name(fact.upstream_segment),
            )
        )
    return tuple(values)


def _lineage_segment_names(lineage: ProjectRelationRowLineage) -> set[str]:
    return {
        segment.name
        for fact in lineage.facts
        for segment in (fact.output_segment, fact.upstream_segment)
    }


def _segment_display_name(segment: ProjectRowLineageSegment) -> str:
    if segment.kind is ProjectRowLineageSegmentKind.LET_BINDING:
        return segment.binding_name or segment.name
    return segment.name


def test_direct_source_and_direct_relation_provenance_baseline(
    tmp_path: Path,
) -> None:
    source = "query seed:\n    from users\n    select:\n        id\n"
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    seed = _derived_definition(parse_result, "seed")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    seed_field = semantic_result.model.relation_row_schemas[seed].fields["id"]

    assert source_field.provenance is not None
    assert source_field.provenance.kind is ProjectRowFieldProvenanceKind.SOURCE_FIELD
    assert (
        source_field.provenance.symbol
        is semantic_result.model.source_shape_resolutions[users]
    )
    assert source_field.provenance.location is not None
    assert source_field.provenance.location.path == "models.pietto"

    _assert_direct_projection(
        relation_field=seed_field,
        origin_field=source_field,
        expected_name="id",
        expected_symbol=semantic_result.model.relation_resolutions[seed.from_clause],
        expected_line=_line_containing(text, "        id\n"),
    )


def test_table_to_query_provenance_is_immediate_upstream(
    tmp_path: Path,
) -> None:
    source = (
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        exported_id = staged.id\n"
    )
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "exported_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="exported_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        exported_id = staged.id\n"),
    )
    assert exported_field.provenance is not None
    assert (
        exported_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[staged.from_clause]
    )


def test_query_to_query_provenance_is_immediate_upstream(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        exported_id = seed.id\n"
    )
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "exported_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="exported_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        exported_id = seed.id\n"),
    )


def test_multi_hop_final_field_keeps_origin_facts_but_not_lineage_path(
    tmp_path: Path,
) -> None:
    source = (
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        user_id = staged.id\n"
        "table materialized:\n"
        "    from exported\n"
        "    select:\n"
        "        published_user_id = exported.user_id\n"
        "query final:\n"
        "    from materialized\n"
        "    select:\n"
        "        final_user_id = materialized.published_user_id\n"
    )
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    final = _derived_definition(parse_result, "final")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    final_field = semantic_result.model.relation_row_schemas[final].fields[
        "final_user_id"
    ]

    _assert_direct_projection(
        relation_field=final_field,
        origin_field=source_field,
        expected_name="final_user_id",
        expected_symbol=semantic_result.model.relation_resolutions[final.from_clause],
        expected_line=_line_containing(
            text,
            "        final_user_id = materialized.published_user_id\n",
        ),
    )
    assert final_field.provenance is not None
    assert (
        final_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[staged.from_clause]
    )
    assert (
        final_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[exported.from_clause]
    )
    assert (
        final_field.provenance.symbol
        is semantic_result.model.relation_resolutions[final.from_clause]
    )


def test_renamed_bare_projection_preserves_origin_facts(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        user_id = id\n"
    )
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "user_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="user_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        user_id = id\n"),
    )


def test_renamed_qualified_projection_preserves_origin_facts(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        user_id = seed.id\n"
    )
    parse_result, semantic_result, text = _semantic_result_with_source(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "user_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="user_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        user_id = seed.id\n"),
    )


def test_original_source_qualifier_remains_invalid_after_propagation(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _semantic_result_with_source(
        tmp_path,
        "query exported:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query published:\n"
        "    from exported\n"
        "    select:\n"
        "        users.id\n",
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_multi_part_lineage_selector_remains_invalid_after_propagation(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _semantic_result_with_source(
        tmp_path,
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        id\n"
        "query published:\n"
        "    from exported\n"
        "    select:\n"
        "        exported.staged.id\n",
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: exported.staged.id")]


def test_project_json_v2_does_not_expose_provenance_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _semantic_result_with_source(
        tmp_path,
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        id\n",
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas
    assert semantic_result.model.relation_row_schema_states
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "provenance",
        "lineage",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldProvenance",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def _assert_direct_projection(
    *,
    relation_field: ProjectRowField,
    origin_field: ProjectRowField,
    expected_name: str,
    expected_symbol: object,
    expected_line: int,
) -> None:
    assert relation_field.name == expected_name
    assert relation_field.resolved_type is origin_field.resolved_type
    assert relation_field.nullability is origin_field.nullability
    assert relation_field.field_def is origin_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )
    assert relation_field.provenance.symbol is expected_symbol
    assert relation_field.provenance.location is not None
    assert relation_field.provenance.location.path == "models.pietto"
    assert relation_field.provenance.location.line == expected_line


def _semantic_result_with_source(
    tmp_path: Path,
    relation_body: str,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult, str]:
    root, source = _project_with_source(tmp_path, relation_body)
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result), source


def _project_with_source(tmp_path: Path, relation_body: str) -> tuple[Path, str]:
    root = _project_root(tmp_path, include=("*.pietto",))
    source = (
        "shape User:\n"
        "    id: Int\n"
        "    email: Text | None\n"
        "    score: Int\n"
        'source users: User = postgres.table("users")\n'
        f"{relation_body}"
    )
    _write(root, "models.pietto", source)
    return root, source


def _source_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> SourceDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, SourceDef) and definition.name == name:
                return definition
    raise AssertionError(f"Source definition not found: {name}")


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _line_containing(source: str, marker: str) -> int:
    lines = source.splitlines(keepends=True)
    matches = [
        line_number for line_number, line in enumerate(lines, start=1) if line == marker
    ]
    assert len(matches) == 1, marker
    return matches[0]


DEPENDENCY_GRAPH_PRIVATE_JSON_FACTS = (
    "relation_row_dependency_graphs",
    "ProjectRelationRowDependencyGraph",
    "ProjectRowDependencyGraphStatus",
    "ProjectRowDependencyGraphReason",
    "ProjectRowDependencyNode",
    "ProjectRowDependencyEdge",
    "output_field",
    "upstream_field",
    "let_binding",
    "computed_expression",
    "let_output",
    "let_expression",
    "dependency",
    "lineage",
    "relation_row_schemas",
    "relation_let_scope_facts",
    "ProjectRowSchema",
    "ProjectRowField",
    "provenance",
)


def test_row_dependency_graph_carriers_are_private_frozen_dataclasses() -> None:
    for model_type in (
        ProjectRowDependencyNode,
        ProjectRowDependencyEdge,
        ProjectRelationRowDependencyGraph,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    node = ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        name="id",
        relation_name="projected",
        output_name="id",
    )
    graph = ProjectRelationRowDependencyGraph(
        status=ProjectRowDependencyGraphStatus.CONCRETE,
        reason=ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE,
        nodes=(node,),
    )

    assert graph.nodes == (node,)
    assert not hasattr(graph, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(graph, "nodes", ())


def test_direct_renamed_and_computed_output_dependencies_are_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n"
            "        normalized = lower(status)\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    graph = semantic_result.model.relation_row_dependency_graphs[projected]
    projected_schema = semantic_result.model.relation_row_schemas[projected]

    assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    assert graph.reason is ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
    assert (
        projected_schema.fields["total"].provenance is not None
        and projected_schema.fields["total"].provenance.kind
        is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.DIRECT_PROJECTION) == (
        ("id", "users.id"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.RENAMED_PROJECTION) == (
        ("user_email", "users.email"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.COMPUTED_EXPRESSION) == (
        ("normalized", "users.status"),
        ("total", "users.score"),
        ("total", "users.bonus"),
    )
    assert "lower" not in {node.name for node in graph.nodes}


def test_selected_let_outputs_and_let_expression_dependencies_are_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let total = score + bonus\n"
            "    let label = lower(status)\n"
            "    let adjusted = total + score\n"
            "    select:\n"
            "        total\n"
            "        exported = adjusted\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    graph = semantic_result.model.relation_row_dependency_graphs[projected]
    projected_schema = semantic_result.model.relation_row_schemas[projected]

    for output_name in ("total", "exported"):
        field = projected_schema.fields[output_name]
        assert field.field_def is None
        assert field.provenance is not None
        assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED

    assert _edge_values(graph, ProjectRowDependencyEdgeKind.LET_OUTPUT) == (
        ("total", "total"),
        ("exported", "adjusted"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.LET_EXPRESSION) == (
        ("total", "users.score"),
        ("total", "users.bonus"),
        ("label", "users.status"),
        ("adjusted", "total"),
        ("adjusted", "users.score"),
    )
    assert "lower" not in {node.name for node in graph.nodes}


def test_multi_hop_dependency_remains_immediate_upstream_only(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    graph = semantic_result.model.relation_row_dependency_graphs[exported]

    assert _edge_values(graph, ProjectRowDependencyEdgeKind.DIRECT_PROJECTION) == (
        ("total", "seed.total"),
    )
    assert "users.score" not in {node.name for node in graph.nodes}
    assert "users.bonus" not in {node.name for node in graph.nodes}


def test_non_concrete_row_schema_states_produce_non_concrete_graphs(
    tmp_path: Path,
) -> None:
    unknown_parse, unknown_semantic = _project_semantic_result(
        _project(
            tmp_path / "unknown",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )
    grouped_parse, grouped_semantic = _project_semantic_result(
        _project(
            tmp_path / "grouped",
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )
    cycle_parse, cycle_semantic = _project_semantic_result(
        _project(
            tmp_path / "cycle",
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
            include_source=False,
        )
    )

    assert unknown_semantic.model is not None
    broken = _derived_definition(unknown_parse, "broken")
    broken_graph = unknown_semantic.model.relation_row_dependency_graphs[broken]
    assert broken_graph.status is ProjectRowDependencyGraphStatus.UNKNOWN
    assert broken_graph.reason is ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA
    assert broken_graph.nodes == ()
    assert broken_graph.edges == ()

    assert grouped_semantic.model is not None
    grouped = _derived_definition(grouped_parse, "grouped")
    grouped_graph = grouped_semantic.model.relation_row_dependency_graphs[grouped]
    assert grouped_graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    assert grouped_graph.reason is (
        ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
    )
    assert _edge_values(
        grouped_graph,
        ProjectRowDependencyEdgeKind.DIRECT_PROJECTION,
    ) == (("status", "users.status"),)
    assert _edge_values(
        grouped_graph,
        ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT,
    ) == (("total", "users.score"),)

    assert cycle_semantic.model is not None
    first = _derived_definition(cycle_parse, "first")
    first_graph = cycle_semantic.model.relation_row_dependency_graphs[first]
    assert first_graph.status is ProjectRowDependencyGraphStatus.BLOCKED
    assert first_graph.reason is ProjectRowDependencyGraphReason.CYCLE_BLOCKED


def test_project_json_v2_keeps_row_dependency_graph_private(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let total = score + bonus\n"
            "    select:\n"
            "        id\n"
            "        total\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_dependency_graphs
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    for private_fact in DEPENDENCY_GRAPH_PRIVATE_JSON_FACTS:
        assert private_fact not in serialized


def test_row_dependency_graph_module_does_not_call_full_semantic_analyze() -> None:
    module = (REPO_ROOT / "src/pietto/_project/row_dependency_graph.py").read_text(
        encoding="utf-8"
    )

    assert "semantic_api.analyze" not in module
    assert "from pietto.semantic import analyze" not in module
    assert "import pietto.semantic as semantic_api" not in module


def test_new_expression_readers_preserve_source_order_and_repeated_occurrences() -> (
    None
):
    span = Span(path="reader.pietto", line=1, column=1, end_line=1, end_column=2)
    when_true = NameExpr(span=span, name="value")
    condition = NameExpr(span=span, name="value")
    when_false = NameExpr(span=span, name="fallback")
    conditional = ConditionalExpr(
        span=span,
        when_true=when_true,
        condition=condition,
        when_false=when_false,
    )
    membership = MembershipExpr(
        span=span,
        value=NameExpr(span=span, name="value"),
        options=(
            LiteralExpr(span=span, value=1),
            NameExpr(span=span, name="option"),
            NameExpr(span=span, name="option"),
        ),
        negated=True,
    )
    cast = CastExpr(
        span=span,
        value=NameExpr(span=span, name="value"),
        target=TypeExpr(
            span=span,
            name="Float",
            arguments=(),
            nullability=Nullability.IMPLICIT,
        ),
    )

    assert _child_expressions(conditional) == (when_true, condition, when_false)
    assert _child_expressions(membership) == (
        membership.value,
        *membership.options,
    )
    assert _child_expressions(cast) == (cast.value,)
    assert _direct_name_leaf_names(conditional) == (
        "value",
        "value",
        "fallback",
    )
    assert _direct_name_leaf_names(membership) == (
        "value",
        "option",
        "option",
    )
    assert _direct_name_leaf_names(cast) == ("value",)


def _direct_name_leaf_names(expression: Expression) -> tuple[str, ...]:
    names: list[str] = []
    for leaf in _direct_name_leaves(expression):
        assert isinstance(leaf, NameExpr)
        names.append(leaf.name)
    return tuple(names)


def _edge_values(
    graph: ProjectRelationRowDependencyGraph,
    kind: ProjectRowDependencyEdgeKind,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (edge.from_node.name, edge.to_node.name)
        for edge in graph.edges
        if edge.kind is kind
    )


def test_unknown_row_dependency_aggregate_detection_fails_closed() -> None:
    from pietto import ast_nodes as ast
    from pietto._project.row_dependency_graph import _contains_semantic_aggregate

    class UnknownExpression(ast.Expression):
        pass

    with pytest.raises(ValueError, match="Unsupported expression"):
        _contains_semantic_aggregate(
            UnknownExpression(
                span=ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
            )
        )


def test_unknown_row_dependency_children_fail_closed() -> None:
    from pietto import ast_nodes as ast

    class UnknownExpression(ast.Expression):
        pass

    with pytest.raises(ValueError, match="Unsupported expression"):
        _child_expressions(
            UnknownExpression(
                span=ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
            )
        )
