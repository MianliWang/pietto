from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pytest

from _pietto_phase62_join_differential_probe import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_query_block as query_blocks
from pietto._project import project_scalar_references as scalar_references
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
)
from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    Span,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_scalar_references.py"
FIELD_ADAPTER = REPO_ROOT / "src/pietto/_project/row_expression_type_facts.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md"
)
TEXT_SOURCE = """
shape LabelRow:
    label: Text not null
source labels: LabelRow is postgres.table("labels")
query label_query:
    from labels
    select:
        label
"""
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Occurrence-Complete Scalar Environment",
    "Scalar Reference Occurrence",
    "Complete Resolution Facts Without Lookup",
    "Project Field Adapter",
    "Existing Type-Kernel Composition",
    "Dependency Direction And Non-Goals",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 4 Handoff",
)


@dataclass(frozen=True, slots=True)
class _Built:
    ordinary_numeric: query_blocks.ProjectConcreteQueryBlock
    ordinary_text: query_blocks.ProjectConcreteQueryBlock
    joined: query_blocks.ProjectConcreteQueryBlock
    non_concrete: query_blocks.ProjectNonConcreteQueryBlock


def _span(column: int) -> Span:
    return Span(
        path="slice3.pietto",
        line=1,
        column=column,
        end_line=1,
        end_column=column + 1,
    )


def _fragment(
    analysis,
    name: str,
) -> ProjectIRConcreteSingleRelationFragment:
    matches = tuple(
        fragment
        for fragment in analysis.evaluation.project_plan.fragments
        if type(fragment) is ProjectIRConcreteSingleRelationFragment
        and fragment.semantic_facts.owner.definition.name == name
    )
    assert len(matches) == 1
    return matches[0]


def _region(
    analysis,
    name: str,
    expected_type: type[ProjectIRConcreteJoinRegion]
    | type[ProjectIRNonConcreteJoinRegion],
) -> ProjectIRConcreteJoinRegion | ProjectIRNonConcreteJoinRegion:
    matches = tuple(
        region
        for region in analysis.join_regions.regions
        if type(region) is expected_type and region.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    return matches[0]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    _, analysis, bundle, _ = _build(
        tmp_path_factory.mktemp("p63s3") / "project",
        PRIMARY_MAIN_SOURCE + TEXT_SOURCE,
        reverse_creation=False,
    )
    numeric_fragment = _fragment(analysis, "orders_by_customer")
    text_fragment = _fragment(analysis, "label_query")
    joined_region = _region(analysis, "unique_target_left", ProjectIRConcreteJoinRegion)
    non_concrete_region = _region(
        analysis,
        "ambiguous_fact_join",
        ProjectIRNonConcreteJoinRegion,
    )
    assert type(joined_region) is ProjectIRConcreteJoinRegion
    assert type(non_concrete_region) is ProjectIRNonConcreteJoinRegion

    numeric = query_blocks.build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=numeric_fragment.semantic_facts.owner,
        fragment=numeric_fragment,
    )
    text = query_blocks.build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=text_fragment.semantic_facts.owner,
        fragment=text_fragment,
    )
    joined = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=joined_region.ledger.owner,
        verification=bundle.verification,
        region=joined_region,
    )
    non_concrete = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=non_concrete_region.ledger.owner,
        verification=bundle.verification,
        region=non_concrete_region,
    )
    assert type(numeric) is query_blocks.ProjectConcreteQueryBlock
    assert type(text) is query_blocks.ProjectConcreteQueryBlock
    assert type(joined) is query_blocks.ProjectConcreteQueryBlock
    assert type(non_concrete) is query_blocks.ProjectNonConcreteQueryBlock
    return _Built(
        ordinary_numeric=numeric,
        ordinary_text=text,
        joined=joined,
        non_concrete=non_concrete,
    )


def _concrete_environment(
    query_block: query_blocks.ProjectConcreteQueryBlock,
) -> scalar_references.ProjectConcreteScalarEnvironment:
    environment = scalar_references.build_project_scalar_environment(query_block)
    assert type(environment) is scalar_references.ProjectConcreteScalarEnvironment
    return environment


def _resolution(
    environment: scalar_references.ProjectConcreteScalarEnvironment,
    expression: NameExpr | DottedNameExpr,
    *positions: int,
) -> scalar_references.ProjectScalarReferenceResolution:
    return scalar_references.ProjectScalarReferenceResolution(
        reference=scalar_references.ProjectScalarReferenceOccurrence(
            environment=environment,
            expression=expression,
        ),
        candidates=tuple(environment.fields[position] for position in positions),
    )


def test_ordinary_and_joined_environments_retain_exact_occurrences(
    built: _Built,
) -> None:
    ordinary = _concrete_environment(built.ordinary_numeric)
    ordinary_source = built.ordinary_numeric.row_source
    assert type(ordinary_source) is query_blocks.ProjectExistingRelationRowSource
    source_fields = ordinary_source.output.row_shape.fields
    assert ordinary.query_block is built.ordinary_numeric
    assert ordinary.row_source is ordinary_source
    assert all(
        item.source_field is source
        for item, source in zip(ordinary.fields, source_fields, strict=True)
    )
    assert tuple(item.position for item in ordinary.fields) == tuple(
        range(len(source_fields))
    )
    assert all(
        item.evidence is source.evidence
        for item, source in zip(ordinary.fields, source_fields, strict=True)
    )

    joined = _concrete_environment(built.joined)
    joined_source = built.joined.row_source
    assert type(joined_source) is query_blocks.ProjectVerifiedJoinedRowSource
    assert joined.row_source is joined_source
    assert all(
        item.source_field is source
        for item, source in zip(joined.fields, joined_source.fields, strict=True)
    )
    names = tuple(item.evidence.name for item in joined.fields)
    id_positions = tuple(
        position for position, name in enumerate(names) if name == "id"
    )
    assert id_positions == (0, 4)
    left_id, right_id = (joined.fields[position] for position in id_positions)
    assert left_id is not right_id
    assert left_id.source_field is joined_source.fields[0]
    assert right_id.source_field is joined_source.fields[4]
    assert left_id.value_type.nullability is EffectiveNullability.NON_NULL
    assert right_id.evidence.nullability is ProjectRowFieldNullability.NON_NULL
    assert right_id.value_type.nullability is EffectiveNullability.NULLABLE
    assert isinstance(joined.fields, tuple)


def test_non_concrete_query_block_has_no_partial_scalar_environment(
    built: _Built,
) -> None:
    environment = scalar_references.build_project_scalar_environment(built.non_concrete)
    assert type(environment) is scalar_references.ProjectNonConcreteScalarEnvironment
    assert environment.query_block is built.non_concrete
    assert environment.state is built.non_concrete.state
    assert environment.fields == ()


def test_reference_occurrence_and_zero_one_many_resolution_are_exact(
    built: _Built,
) -> None:
    environment = _concrete_environment(built.joined)
    absent_expression = NameExpr(span=_span(1), name="id")
    concrete_expression = DottedNameExpr(
        span=_span(2),
        parts=("left", "id"),
    )
    ambiguous_expression = NameExpr(span=_span(3), name="id")
    absent = _resolution(environment, absent_expression)
    concrete_candidates = (environment.fields[0],)
    concrete = scalar_references.ProjectScalarReferenceResolution(
        reference=scalar_references.ProjectScalarReferenceOccurrence(
            environment=environment,
            expression=concrete_expression,
        ),
        candidates=concrete_candidates,
    )
    ambiguous_candidates = (environment.fields[0], environment.fields[4])
    ambiguous = scalar_references.ProjectScalarReferenceResolution(
        reference=scalar_references.ProjectScalarReferenceOccurrence(
            environment=environment,
            expression=ambiguous_expression,
        ),
        candidates=ambiguous_candidates,
    )

    assert absent.status is ProjectModuleCandidateBucketStatus.ABSENT
    assert absent.target is None
    assert absent.candidates == ()
    assert concrete.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert concrete.reference.expression is concrete_expression
    assert concrete.reference.environment is environment
    assert concrete.reference.query_block is environment.query_block
    assert concrete.candidates is concrete_candidates
    assert concrete.target is environment.fields[0]
    assert ambiguous.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert ambiguous.candidates is ambiguous_candidates
    assert ambiguous.target is None

    unmatched = NameExpr(span=_span(4), name="not_looked_up_here")
    supplied = _resolution(environment, unmatched, 4)
    assert supplied.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert supplied.target is environment.fields[4]


def test_resolution_rejects_duplicate_reordered_and_foreign_candidates(
    built: _Built,
) -> None:
    joined = _concrete_environment(built.joined)
    ordinary = _concrete_environment(built.ordinary_numeric)
    expression = NameExpr(span=_span(5), name="id")
    reference = scalar_references.ProjectScalarReferenceOccurrence(
        environment=joined,
        expression=expression,
    )
    with pytest.raises(ValueError, match="cannot repeat"):
        scalar_references.ProjectScalarReferenceResolution(
            reference=reference,
            candidates=(joined.fields[0], joined.fields[0]),
        )
    with pytest.raises(ValueError, match="environment order"):
        scalar_references.ProjectScalarReferenceResolution(
            reference=reference,
            candidates=(joined.fields[4], joined.fields[0]),
        )
    with pytest.raises(ValueError, match="exact environment"):
        scalar_references.ProjectScalarReferenceResolution(
            reference=reference,
            candidates=(ordinary.fields[0],),
        )


def test_direct_nested_boolean_and_builtin_call_reuse_existing_kernel(
    built: _Built,
) -> None:
    numeric = _concrete_environment(built.ordinary_numeric)
    text = _concrete_environment(built.ordinary_text)

    direct_leaf = NameExpr(span=_span(10), name="candidate_discovery_is_later")
    direct = scalar_references.analyze_project_scalar_expression(
        environment=numeric,
        expression=direct_leaf,
        resolutions=(_resolution(numeric, direct_leaf, 0),),
    )
    assert type(direct) is scalar_references.ProjectConcreteScalarTypeResult
    assert direct.value_type is numeric.fields[0].value_type
    assert direct.value_types[direct_leaf] is numeric.fields[0].value_type

    left = NameExpr(span=_span(11), name="customer_id")
    right = NameExpr(span=_span(12), name="order_count")
    nested = BinaryExpr(
        span=_span(13),
        left=left,
        operator="+",
        right=BinaryExpr(
            span=_span(14),
            left=right,
            operator="+",
            right=LiteralExpr(span=_span(15), value=1),
        ),
    )
    nested_result = scalar_references.analyze_project_scalar_expression(
        environment=numeric,
        expression=nested,
        resolutions=(
            _resolution(numeric, left, 0),
            _resolution(numeric, right, 2),
        ),
    )
    assert type(nested_result) is scalar_references.ProjectConcreteScalarTypeResult
    assert nested_result.value_type.resolved_type.name == "Int"
    assert nested_result.value_type.nullability is EffectiveNullability.UNKNOWN

    first = NameExpr(span=_span(16), name="customer_id")
    second = NameExpr(span=_span(17), name="order_count")
    predicate = BinaryExpr(
        span=_span(18),
        left=ComparisonExpr(
            span=_span(19),
            left=first,
            operator=">",
            right=LiteralExpr(span=_span(20), value=0),
        ),
        operator="and",
        right=ComparisonExpr(
            span=_span(21),
            left=second,
            operator=">",
            right=LiteralExpr(span=_span(22), value=0),
        ),
    )
    predicate_result = scalar_references.analyze_project_scalar_expression(
        environment=numeric,
        expression=predicate,
        resolutions=(
            _resolution(numeric, first, 0),
            _resolution(numeric, second, 2),
        ),
    )
    assert type(predicate_result) is scalar_references.ProjectConcreteScalarTypeResult
    assert predicate_result.value_type.resolved_type.name == "Bool"

    argument = NameExpr(span=_span(23), name="label")
    callee = NameExpr(span=_span(24), name="len")
    call = CallExpr(
        span=_span(25),
        callee=callee,
        arguments=(argument,),
    )
    assert scalar_references.scalar_field_reference_leaves(call) == (argument,)
    call_result = scalar_references.analyze_project_scalar_expression(
        environment=text,
        expression=call,
        resolutions=(_resolution(text, argument, 0),),
    )
    assert type(call_result) is scalar_references.ProjectConcreteScalarTypeResult
    assert call_result.value_type.resolved_type.name == "Int"
    assert callee not in call_result.value_types


def test_duplicate_joined_spellings_keep_distinct_occurrence_nullability(
    built: _Built,
) -> None:
    environment = _concrete_environment(built.joined)
    left = NameExpr(span=_span(30), name="id")
    right = NameExpr(span=_span(31), name="id")
    expression = ComparisonExpr(
        span=_span(32),
        left=left,
        operator="==",
        right=right,
    )
    result = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=expression,
        resolutions=(
            _resolution(environment, left, 0),
            _resolution(environment, right, 4),
        ),
    )
    assert type(result) is scalar_references.ProjectConcreteScalarTypeResult
    assert result.value_types[left] is environment.fields[0].value_type
    assert result.value_types[right] is environment.fields[4].value_type
    assert result.value_types[left].nullability is EffectiveNullability.NON_NULL
    assert result.value_types[right].nullability is EffectiveNullability.NULLABLE
    assert result.value_type.resolved_type.name == "Bool"


def test_resolution_blockers_and_kernel_diagnostics_publish_no_partial_type(
    built: _Built,
) -> None:
    environment = _concrete_environment(built.ordinary_text)
    text_leaf = NameExpr(span=_span(40), name="label")

    absent = _resolution(environment, text_leaf)
    absent_result = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=text_leaf,
        resolutions=(absent,),
    )
    assert type(absent_result) is scalar_references.ProjectNonConcreteScalarTypeResult
    assert (
        absent_result.reason
        is scalar_references.ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
    )
    assert absent_result.blocking_resolutions == (absent,)
    assert absent_result.value_type is None
    assert absent_result.kernel_value_type is None

    invalid = BinaryExpr(
        span=_span(41),
        left=text_leaf,
        operator="+",
        right=LiteralExpr(span=_span(42), value=1),
    )
    invalid_result = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=invalid,
        resolutions=(_resolution(environment, text_leaf, 0),),
    )
    assert type(invalid_result) is scalar_references.ProjectNonConcreteScalarTypeResult
    assert (
        invalid_result.reason
        is scalar_references.ProjectScalarTypeNonConcreteReason.TYPE_KERNEL_NON_CONCRETE
    )
    assert invalid_result.value_type is None
    assert [diagnostic.code for diagnostic in invalid_result.diagnostics] == [
        "PIE-S2105"
    ]

    argument = NameExpr(span=_span(43), name="label")
    unknown_call = CallExpr(
        span=_span(44),
        callee=NameExpr(span=_span(45), name="not_a_builtin"),
        arguments=(argument,),
    )
    unknown_result = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=unknown_call,
        resolutions=(_resolution(environment, argument, 0),),
    )
    assert type(unknown_result) is scalar_references.ProjectNonConcreteScalarTypeResult
    assert [diagnostic.code for diagnostic in unknown_result.diagnostics] == [
        "PIE-S2103"
    ]

    aggregate_argument = NameExpr(span=_span(46), name="label")
    aggregate = CallExpr(
        span=_span(47),
        callee=NameExpr(span=_span(48), name="sum"),
        arguments=(aggregate_argument,),
    )
    aggregate_result = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=aggregate,
        resolutions=(_resolution(environment, aggregate_argument, 0),),
    )
    assert (
        type(aggregate_result) is scalar_references.ProjectNonConcreteScalarTypeResult
    )
    assert aggregate_result.value_type is None


def test_missing_extra_reordered_and_foreign_resolution_facts_are_rejected(
    built: _Built,
) -> None:
    numeric = _concrete_environment(built.ordinary_numeric)
    text = _concrete_environment(built.ordinary_text)
    left = NameExpr(span=_span(50), name="customer_id")
    right = NameExpr(span=_span(51), name="order_count")
    expression = BinaryExpr(
        span=_span(52),
        left=left,
        operator="+",
        right=right,
    )
    left_fact = _resolution(numeric, left, 0)
    right_fact = _resolution(numeric, right, 2)
    with pytest.raises(ValueError, match="one fact per reference"):
        scalar_references.analyze_project_scalar_expression(
            environment=numeric,
            expression=expression,
            resolutions=(left_fact,),
        )
    with pytest.raises(ValueError, match="one fact per reference"):
        scalar_references.analyze_project_scalar_expression(
            environment=numeric,
            expression=left,
            resolutions=(left_fact, right_fact),
        )
    with pytest.raises(ValueError, match="exact leaf order and root"):
        scalar_references.analyze_project_scalar_expression(
            environment=numeric,
            expression=expression,
            resolutions=(right_fact, left_fact),
        )
    foreign_fact = _resolution(
        text,
        NameExpr(span=_span(53), name="label"),
        0,
    )
    with pytest.raises(ValueError, match="exact leaf order and root"):
        scalar_references.analyze_project_scalar_expression(
            environment=numeric,
            expression=expression,
            resolutions=(left_fact, foreign_fact),
        )


@pytest.mark.parametrize(
    ("project_nullability", "semantic_nullability"),
    (
        (ProjectRowFieldNullability.NON_NULL, EffectiveNullability.NON_NULL),
        (ProjectRowFieldNullability.NULLABLE, EffectiveNullability.NULLABLE),
        (ProjectRowFieldNullability.UNKNOWN, EffectiveNullability.UNKNOWN),
    ),
)
def test_project_field_adapter_reuses_existing_type_and_nullability_semantics(
    project_nullability: ProjectRowFieldNullability,
    semantic_nullability: EffectiveNullability,
) -> None:
    field = ProjectRowField(
        name="value",
        resolved_type=ProjectResolvedType(
            name="Int",
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=ProjectRowFieldNullability.NON_NULL,
    )
    value_type = project_row_field_to_semantic_value_type(
        field,
        project_nullability,
    )
    assert value_type.resolved_type.name == "Int"
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is semantic_nullability
    assert value_type.kind is ValueTypeKind.KNOWN


def test_unknown_project_field_adapter_matches_existing_kernel_result() -> None:
    field = ProjectRowField(
        name="custom",
        resolved_type=ProjectResolvedType(
            name="CustomType",
            kind=ProjectResolvedTypeKind.TYPE_ALIAS,
        ),
        nullability=ProjectRowFieldNullability.NON_NULL,
    )
    adapted = project_row_field_to_semantic_value_type(
        field,
        ProjectRowFieldNullability.NULLABLE,
    )
    expression = NameExpr(span=_span(60), name="custom")
    value_types: dict[Expression, ValueType] = {}
    diagnostics = []
    expected = infer_row_expression(
        expression,
        project_row_schema_to_semantic_row_schema(
            ProjectRowSchema(fields={"custom": field})
        ),
        value_types,
        diagnostics,
        report_unknown_name=True,
    )
    assert adapted == expected
    assert adapted.kind is ValueTypeKind.UNKNOWN
    assert adapted.resolved_type.name == "<unknown>"
    assert adapted.nullability is EffectiveNullability.UNKNOWN
    assert diagnostics == []


def test_slice3_adapter_matches_ordinary_row_schema_kernel(built: _Built) -> None:
    environment = _concrete_environment(built.ordinary_numeric)
    row_source = built.ordinary_numeric.row_source
    assert type(row_source) is query_blocks.ProjectExistingRelationRowSource
    schema = row_source.semantic_facts.state.schema
    assert schema is not None
    left = NameExpr(span=_span(70), name="customer_id")
    right = NameExpr(span=_span(71), name="order_count")
    expression = BinaryExpr(
        span=_span(72),
        left=left,
        operator="+",
        right=right,
    )
    adapted = scalar_references.analyze_project_scalar_expression(
        environment=environment,
        expression=expression,
        resolutions=(
            _resolution(environment, left, 0),
            _resolution(environment, right, 2),
        ),
    )
    direct_types: dict[Expression, ValueType] = {}
    direct_diagnostics = []
    direct = infer_row_expression(
        expression,
        project_row_schema_to_semantic_row_schema(schema),
        direct_types,
        direct_diagnostics,
        report_unknown_name=True,
    )
    assert type(adapted) is scalar_references.ProjectConcreteScalarTypeResult
    assert adapted.value_type == direct
    assert adapted.diagnostics == tuple(direct_diagnostics)
    assert adapted.value_types == direct_types


def test_slice3_scope_dependency_and_contract_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 8
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 5
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "one ordered entry per source field occurrence",
        "Duplicate spellings remain separate",
        "CallExpr children are arguments only",
        "ProjectModuleCandidateBucketStatus remains the only candidate-status taxonomy",
        "Slice 3 does not decide which entries match a spelling",
        "Slice 4 owns candidate discovery",
        "infer_row_expression then runs with an empty row schema and no name lookup",
        "value_type = None",
        "production 164 -> 165 and tests 407 -> 408",
        "Slice 4 becomes NEXT / NOT IMPLEMENTED",
        "Slice 4 is not begun here",
    ):
        assert evidence in normalized

    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert scalar_references.__all__ == ()
    assert "infer_row_expression" in facts.identifiers
    assert "child_expressions" in facts.identifiers
    assert "project_row_field_to_semantic_value_type" in facts.identifiers
    assert "Mapping[str" not in facts.text
    for forbidden in (
        "resolve_name",
        "lookup_name",
        "qualifier_map",
        "visible_name",
        "alias_map",
        "binding_table",
        "effective_output",
        "projectsemanticresult",
        "qualify",
        "serializer",
        "registry",
        "cache",
        "executor",
    ):
        assert forbidden not in facts.text.casefold()

    for relative in (
        "src/pietto/_project/project_query_block.py",
        "src/pietto/_project/project_ir_properties.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/aggregates.py",
        "src/pietto/semantic/model.py",
    ):
        assert not any(
            name.endswith(".project_scalar_references")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )

    adapter_source = REPOSITORY_FACTS.python(FIELD_ADAPTER).text
    assert "def project_row_field_to_semantic_value_type(" in adapter_source
    assert "infer_row_expression" in adapter_source
