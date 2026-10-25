from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re

import pytest

from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_query_block as query_blocks
from pietto._project import project_scalar_bindings as scalar_bindings
from pietto._project import project_scalar_references as scalar_references
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
)
from pietto._project.project_current_joins import (
    ProjectCurrentJoinRegion,
    ProjectCurrentBinaryJoin,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    NameExpr,
    Span,
)
from pietto.semantic.model import EffectiveNullability


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_scalar_bindings.py"
PROFILE_SOURCE = """
shape ProfileRow:
    id: Int
    label: Text
    profile_key = unique(id)
source profiles: ProfileRow = postgres.table("profiles")
relationship customer_profiles(customer: CustomerRow, profile: ProfileRow):
    customer.id == profile.id
query profile_join:
    from customers
    let profile = profiles
    inner join profile on customer_profiles(customers, profile)
    select:
        id
"""


@dataclass(frozen=True, slots=True)
class _Built:
    direct: scalar_bindings.ProjectJoinedScalarBindingEnvironment
    multihop: scalar_bindings.ProjectJoinedScalarBindingEnvironment
    repeated: scalar_bindings.ProjectJoinedScalarBindingEnvironment
    profile: scalar_bindings.ProjectJoinedScalarBindingEnvironment
    ordinary: scalar_references.ProjectConcreteScalarEnvironment
    foreign_profile: scalar_bindings.ProjectJoinedScalarBindingEnvironment


def _span(column: int) -> Span:
    return Span(
        path="slice4.pietto",
        line=1,
        column=column,
        end_line=1,
        end_column=column + 1,
    )


def _joined_environment(
    completed: ProjectConcreteCompletedSemanticResult,
    name: str,
) -> scalar_bindings.ProjectJoinedScalarBindingEnvironment:
    matches = tuple(
        readiness.namespaces.binding_environment
        for readiness in completed.effective_outputs.current_readiness
        if readiness.namespaces.binding_environment.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    environment = matches[0]
    assert isinstance(environment.region, ProjectCurrentJoinRegion)
    assert any(
        environment.region is region
        for region in completed.effective_outputs.current_regions
    )
    return environment


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    _, completed, _, _ = _build(
        tmp_path_factory.mktemp("joined-bindings") / "project",
        PRIMARY_MAIN_SOURCE + PROFILE_SOURCE,
        reverse_creation=False,
    )
    fragments = tuple(
        fragment
        for fragment in completed.completion.plan.fragments
        if type(fragment) is ProjectIRConcreteSingleRelationFragment
        and fragment.semantic_facts.owner.definition.name == "orders_by_customer"
    )
    assert len(fragments) == 1
    ordinary_query_block = query_blocks.build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=fragments[0].semantic_facts.owner,
        fragment=fragments[0],
    )
    assert type(ordinary_query_block) is query_blocks.ProjectConcreteQueryBlock
    ordinary = scalar_references.build_project_scalar_environment(ordinary_query_block)
    assert type(ordinary) is scalar_references.ProjectConcreteScalarEnvironment
    _, foreign, _, _ = _build(
        tmp_path_factory.mktemp("foreign-joined-bindings") / "project",
        PRIMARY_MAIN_SOURCE.split("query orders_by_customer:", 1)[0] + PROFILE_SOURCE,
        reverse_creation=False,
    )
    return _Built(
        direct=_joined_environment(completed, "unique_target_left"),
        multihop=_joined_environment(completed, "multihop_join"),
        repeated=_joined_environment(completed, "reused_join"),
        profile=_joined_environment(completed, "profile_join"),
        ordinary=ordinary,
        foreign_profile=_joined_environment(foreign, "profile_join"),
    )


def _reference(
    environment: scalar_bindings.ProjectJoinedScalarBindingEnvironment,
    expression: NameExpr | DottedNameExpr,
) -> scalar_references.ProjectScalarReferenceResolution:
    return scalar_bindings.resolve_project_joined_scalar_reference(
        environment,
        scalar_references.ProjectScalarReferenceOccurrence(
            environment=environment.scalar_environment,
            expression=expression,
        ),
    )


def _binding(
    environment: scalar_bindings.ProjectJoinedScalarBindingEnvironment,
    name: str,
) -> scalar_bindings.ProjectVisibleJoinedBinding:
    matches = tuple(
        binding for binding in environment.bindings if binding.binding.name == name
    )
    assert len(matches) == 1
    return matches[0]


def test_exact_current_bindings_and_introduction_uses_are_reused(
    built: _Built,
) -> None:
    environment = built.direct
    assert environment.row_source is environment.scalar_environment.row_source
    assert environment.region is environment.row_source.region
    assert environment.ledger is environment.region.ledger
    assert all(
        retained.binding is original
        for retained, original in zip(
            environment.bindings,
            environment.ledger.bindings,
            strict=True,
        )
    )
    assert tuple(
        binding.binding.identity.binding_position for binding in environment.bindings
    ) == (
        0,
        1,
    )
    assert (
        environment.bindings[0].introduction_use
        is (environment.region.joins[0].input_uses[0])
    )
    assert (
        environment.bindings[1].introduction_use
        is (environment.region.joins[0].input_uses[1])
    )
    assert tuple(item.position for item in environment.bindings[0].fields) == (
        0,
        1,
        2,
        3,
    )
    assert tuple(item.position for item in environment.bindings[1].fields) == (4,)
    assert environment.hidden_fields == ()
    assert all(
        type(item.source_field) is ProjectIRJoinedRowField
        and item.source_field.introduction_use is binding.introduction_use
        for binding in environment.bindings
        for item in binding.fields
    )
    target_id = environment.bindings[1].fields[0]
    assert target_id.evidence.nullability.value == "non_null"
    assert target_id.value_type.nullability is EffectiveNullability.NULLABLE


def test_qualified_lookup_uses_binding_name_only_and_exact_field_occurrence(
    built: _Built,
) -> None:
    environment = built.direct
    customer_id = DottedNameExpr(span=_span(1), parts=("customer", "id"))
    concrete = _reference(environment, customer_id)
    assert concrete.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert concrete.target is environment.scalar_environment.fields[4]
    assert concrete.target is _binding(environment, "customer").fields[0]

    orders_product = _reference(
        environment,
        DottedNameExpr(span=_span(2), parts=("orders", "product_id")),
    )
    assert orders_product.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert orders_product.target is environment.scalar_environment.fields[2]

    for expression in (
        DottedNameExpr(span=_span(3), parts=("missing", "id")),
        DottedNameExpr(span=_span(4), parts=("customer", "missing")),
        DottedNameExpr(span=_span(5), parts=("customers", "id")),
        DottedNameExpr(span=_span(6), parts=("customer", "nested", "id")),
    ):
        absent = _reference(environment, expression)
        assert absent.status is ProjectModuleCandidateBucketStatus.ABSENT
        assert absent.candidates == ()
    customer = _binding(environment, "customer").binding
    assert customer.name == "customer"
    assert customer.relation_name == "customers"


def test_unqualified_lookup_is_complete_ordered_and_winner_free(built: _Built) -> None:
    environment = built.direct
    unique = _reference(
        environment,
        NameExpr(span=_span(10), name="product_id"),
    )
    absent = _reference(
        environment,
        NameExpr(span=_span(11), name="missing"),
    )
    ambiguous = _reference(
        environment,
        NameExpr(span=_span(12), name="id"),
    )
    assert unique.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert unique.target is environment.scalar_environment.fields[2]
    assert absent.status is ProjectModuleCandidateBucketStatus.ABSENT
    assert absent.target is None
    assert ambiguous.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    expected = (
        environment.scalar_environment.fields[0],
        environment.scalar_environment.fields[4],
    )
    assert all(
        actual is retained
        for actual, retained in zip(ambiguous.candidates, expected, strict=True)
    )
    assert ambiguous.target is None


def test_explicit_intermediate_binding_keeps_all_fields_and_exact_uses(
    built: _Built,
) -> None:
    environment = built.multihop
    assert isinstance(environment.region, ProjectCurrentJoinRegion)
    assert tuple(binding.binding.name for binding in environment.bindings) == (
        "customers",
        "coarse_orders",
        "coarse_returns",
    )
    assert tuple(item.position for item in environment.visible_fields) == (
        0,
        1,
        2,
        3,
        4,
        5,
    )
    assert environment.hidden_fields == ()
    middle = _binding(environment, "coarse_orders")
    assert tuple(item.evidence.name for item in middle.fields) == (
        "customer_id",
        "total",
        "order_count",
    )
    first, second = environment.region.joins
    assert isinstance(first, ProjectCurrentBinaryJoin) and isinstance(
        second, ProjectCurrentBinaryJoin
    )
    assert middle.introduction_use is first.input_uses[1]
    assert second.left_input is first.properties.relational
    assert first.use is not second.use
    assert first.condition.use is first.use and second.condition.use is second.use
    assert first.condition.use.path is second.condition.use.path is None
    assert all(
        type(item.source_field) is ProjectIRJoinedRowField
        and item.source_field.introduction_use is middle.introduction_use
        for item in middle.fields
    )
    bare = _reference(environment, NameExpr(span=_span(20), name="order_count"))
    qualified = _reference(
        environment,
        DottedNameExpr(span=_span(21), parts=("coarse_orders", "order_count")),
    )
    wrong_qualifier = _reference(
        environment,
        DottedNameExpr(span=_span(22), parts=("orders_by_customer", "order_count")),
    )
    target = _reference(
        environment,
        DottedNameExpr(span=_span(23), parts=("coarse_returns", "customer_id")),
    )
    assert (
        bare.status is qualified.status is ProjectModuleCandidateBucketStatus.CONCRETE
    )
    assert bare.target is qualified.target is middle.fields[2]
    assert wrong_qualifier.status is ProjectModuleCandidateBucketStatus.ABSENT
    assert wrong_qualifier.candidates == () and wrong_qualifier.target is None
    assert target.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert target.target is environment.scalar_environment.fields[4]


def test_repeated_relation_bindings_keep_distinct_occurrences(built: _Built) -> None:
    environment = built.repeated
    first_binding = _binding(environment, "first_orders")
    second_binding = _binding(environment, "second_orders")
    assert first_binding.binding is not second_binding.binding
    assert first_binding.binding.relation_name == second_binding.binding.relation_name
    assert first_binding.introduction_use is not second_binding.introduction_use

    first = _reference(
        environment,
        DottedNameExpr(span=_span(30), parts=("first_orders", "total")),
    )
    second = _reference(
        environment,
        DottedNameExpr(span=_span(31), parts=("second_orders", "total")),
    )
    ambiguous = _reference(
        environment,
        NameExpr(span=_span(32), name="total"),
    )
    assert first.status is second.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert first.target is not None and second.target is not None
    assert first.target is environment.scalar_environment.fields[2]
    assert second.target is environment.scalar_environment.fields[5]
    assert first.target.source_field is not second.target.source_field
    assert first.target.evidence is second.target.evidence
    assert ambiguous.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert ambiguous.candidates[0] is first.target
    assert ambiguous.candidates[1] is second.target
    assert ambiguous.target is None


def test_slice4_resolutions_feed_unchanged_slice3_type_kernel(built: _Built) -> None:
    direct = built.direct
    left = DottedNameExpr(span=_span(40), parts=("orders", "customer_id"))
    right = DottedNameExpr(span=_span(41), parts=("customer", "id"))
    arithmetic = BinaryExpr(
        span=_span(42),
        left=left,
        operator="+",
        right=right,
    )
    arithmetic_result = scalar_references.analyze_project_scalar_expression(
        environment=direct.scalar_environment,
        expression=arithmetic,
        resolutions=(_reference(direct, left), _reference(direct, right)),
    )
    assert type(arithmetic_result) is scalar_references.ProjectConcreteScalarTypeResult
    assert arithmetic_result.value_type.resolved_type.name == "Int"

    profile = built.profile
    argument = DottedNameExpr(span=_span(43), parts=("profile", "label"))
    call = CallExpr(
        span=_span(44),
        callee=NameExpr(span=_span(45), name="len"),
        arguments=(argument,),
    )
    call_result = scalar_references.analyze_project_scalar_expression(
        environment=profile.scalar_environment,
        expression=call,
        resolutions=(_reference(profile, argument),),
    )
    assert type(call_result) is scalar_references.ProjectConcreteScalarTypeResult
    assert call_result.value_type.resolved_type.name == "Int"
    assert call_result.diagnostics == ()

    ambiguous_expression = NameExpr(span=_span(46), name="id")
    ambiguous = _reference(direct, ambiguous_expression)
    blocked = scalar_references.analyze_project_scalar_expression(
        environment=direct.scalar_environment,
        expression=ambiguous_expression,
        resolutions=(ambiguous,),
    )
    assert type(blocked) is scalar_references.ProjectNonConcreteScalarTypeResult
    assert (
        blocked.reason
        is scalar_references.ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
    )
    assert blocked.blocking_resolutions == (ambiguous,)
    assert blocked.value_type is None

    invalid_call = CallExpr(
        span=_span(47),
        callee=NameExpr(span=_span(48), name="not_a_builtin"),
        arguments=(argument,),
    )
    invalid = scalar_references.analyze_project_scalar_expression(
        environment=profile.scalar_environment,
        expression=invalid_call,
        resolutions=(_reference(profile, argument),),
    )
    assert type(invalid) is scalar_references.ProjectNonConcreteScalarTypeResult
    assert [diagnostic.code for diagnostic in invalid.diagnostics] == ["PIE-S2103"]


def test_joined_binding_scope_rejects_ordinary_and_foreign_roots(built: _Built) -> None:
    with pytest.raises(TypeError, match="verified joined row source"):
        scalar_bindings.build_project_joined_scalar_binding_environment(built.ordinary)
    local, foreign = built.profile, built.foreign_profile
    assert local.region is not foreign.region
    expression = DottedNameExpr(span=_span(60), parts=("profile", "label"))
    reference = scalar_references.ProjectScalarReferenceOccurrence(
        environment=foreign.scalar_environment, expression=expression
    )
    with pytest.raises(ValueError, match="same-root"):
        scalar_bindings.resolve_project_joined_scalar_reference(local, reference)
    with pytest.raises(ValueError, match="exact base and condition roots"):
        replace(local.row_source, region=foreign.region)
    with pytest.raises(ValueError, match="JOIN provenance"):
        replace(
            _binding(local, "profile"),
            introduction_use=_binding(foreign, "profile").introduction_use,
        )


def test_slice4_scope_dependency_and_contract_are_exact() -> None:
    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert scalar_bindings.__all__ == ()
    for required in (
        "ProjectRelationBindingOccurrence",
        "ProjectRelationJoinUseLedger",
        "ProjectScalarReferenceResolution",
        "ProjectIRJoinedRowField",
    ):
        assert required in facts.identifiers
    assert re.search(r"^class .*BindingIdentity", facts.text, re.MULTILINE) is None
    assert "Mapping[str" not in facts.text
    for forbidden in (
        "rowschema",
        "synthetic",
        "letbinding",
        "shadow",
        "projection_alias",
        "qualify",
        "serializer",
        "registry",
        "cache",
        "executor",
    ):
        assert forbidden not in facts.text.casefold()

    for relative in (
        "src/pietto/_project/project_query_block.py",
        "src/pietto/_project/project_scalar_references.py",
        "src/pietto/_project/project_relationship_uses.py",
        "src/pietto/_project/project_ir_joins.py",
        "src/pietto/_project/project_ir_properties.py",
    ):
        assert not any(
            name.endswith(".project_scalar_bindings")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )
