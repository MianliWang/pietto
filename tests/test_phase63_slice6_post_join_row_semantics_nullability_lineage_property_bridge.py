from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pytest

from _pietto_phase62_join_differential_probe import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_joined_row_semantics as joined_semantics
from pietto._project import project_query_block as query_blocks
from pietto._project import project_scalar_bindings as scalar_bindings
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_scalar_references as scalar_references
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldNullability,
    ProjectSemanticResult,
)
from pietto._project.module_attribution import (
    ProjectModuleAttributionFactSet,
    ProjectModuleProjectionKind,
    ProjectModuleRowFieldKind,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinUnavailableProperty,
)
from pietto._project.project_ir_properties import (
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_multifact import ProjectMultiFactAnalysis
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_row_semantics.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md"
)
BRIDGE_SOURCE = """
query direct_renamed_orders:
    from orders
    select:
        customer_key = customer_id
        raw_amount = amount
relationship customer_direct_renamed_orders:
    endpoint customer: customers
    endpoint renamed: direct_renamed_orders
    on customer.id == renamed.customer_key
query renamed_upstream_join:
    from customers
    inner join direct_renamed_orders as renamed:
        from customers
        via customer_direct_renamed_orders: customer -> renamed
    select:
        id
query computed_orders:
    from orders
    select:
        customer_id
        adjusted = amount + 1
relationship customer_computed_orders:
    endpoint customer: customers
    endpoint computed: computed_orders
    on customer.id == computed.customer_id
query computed_upstream_join:
    from customers
    inner join computed_orders as computed:
        from customers
        via customer_computed_orders: customer -> computed
    select:
        id
query let_orders:
    from orders
    let:
        adjusted = amount + 1
    select:
        customer_id
        adjusted
relationship customer_let_orders:
    endpoint customer: customers
    endpoint derived: let_orders
    on customer.id == derived.customer_id
query let_upstream_join:
    from customers
    inner join let_orders as derived:
        from customers
        via customer_let_orders: customer -> derived
    select:
        id
query source_multihop_left:
    from customers
    left join returns as returned:
        from customers
        via customer_orders_raw: customer -> orders
        via composite_raw: orders -> returns
    select:
        id
query repeated_source_join:
    from customers
    inner join orders as first_orders:
        from customers
        via customer_orders_raw: customer -> orders
    inner join orders as second_orders:
        from customers
        via customer_orders_raw: customer -> orders
    select:
        id
query nullable_inner_join:
    from orders
    inner join returns as returned:
        from orders
        via nullable_amounts: orders -> returns
    select:
        id
query let_attached_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        maybe_customer = customer.id
    select:
        amount
query invalid_let_stage_join:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    let:
        bad = bad + amount
    select:
        amount
"""
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Existing Phase-62 Authority",
    "Final Field Occurrence Semantics",
    "Canonical Identity And Lineage",
    "Nullability Coherence",
    "Exact Property And Multi-Fact Bridge",
    "Slice-5 Attachment And Closed Results",
    "Historical And Later-Stage Boundary",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 7 Handoff",
)


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    analysis: ProjectMultiFactAnalysis
    attribution: ProjectModuleAttributionFactSet
    verification: ProjectPhase62VerificationResult
    namespaces: dict[str, scalar_namespaces.ProjectJoinedLetNamespaceResult]


def _namespace(
    analysis: ProjectMultiFactAnalysis,
    verification: ProjectPhase62VerificationResult,
    name: str,
) -> scalar_namespaces.ProjectJoinedLetNamespaceResult:
    matches = tuple(
        region
        for region in analysis.join_regions.regions
        if type(region) is ProjectIRConcreteJoinRegion
        and region.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    region = matches[0]
    query_block = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=region.ledger.owner,
        verification=verification,
        region=region,
    )
    assert type(query_block) is query_blocks.ProjectConcreteQueryBlock
    scalar_environment = scalar_references.build_project_scalar_environment(query_block)
    assert (
        type(scalar_environment) is scalar_references.ProjectConcreteScalarEnvironment
    )
    bindings = scalar_bindings.build_project_joined_scalar_binding_environment(
        scalar_environment
    )
    return scalar_namespaces.build_project_joined_let_namespaces(bindings)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic, analysis, bundle, _ = _build(
        tmp_path_factory.mktemp("p63s6") / "project",
        PRIMARY_MAIN_SOURCE + BRIDGE_SOURCE,
        reverse_creation=False,
    )
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    names = (
        "unique_target_inner",
        "unique_target_left",
        "direct_renamed_orders",
        "renamed_upstream_join",
        "computed_upstream_join",
        "let_upstream_join",
        "source_multihop_left",
        "repeated_source_join",
        "nullable_inner_join",
        "let_attached_join",
        "invalid_let_stage_join",
    )
    return _Built(
        semantic=semantic,
        analysis=analysis,
        attribution=attribution,
        verification=bundle.verification,
        namespaces={
            name: _namespace(analysis, bundle.verification, name)
            for name in names
            if name != "direct_renamed_orders"
        },
    )


def _result(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectJoinedRowSemanticsResult:
    return joined_semantics.build_project_joined_row_semantics(
        namespaces=built.namespaces[name],
        attribution=built.attribution,
    )


def _concrete(
    built: _Built,
    name: str,
) -> joined_semantics.ProjectConcreteJoinedRowSemantics:
    result = _result(built, name)
    assert type(result) is joined_semantics.ProjectConcreteJoinedRowSemantics
    return result


def test_exact_final_property_multifact_and_post_let_roots_are_retained(
    built: _Built,
) -> None:
    namespaces = built.namespaces["let_attached_join"]
    assert type(namespaces) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    result = _concrete(built, "let_attached_join")
    expected_region = next(
        item
        for item in built.analysis.concrete_regions
        if item.region is namespaces.binding_environment.region
    )
    bridge = result.property_bridge
    assert result.namespaces is namespaces
    assert result.post_let is namespaces.post_let
    assert result.let_values is namespaces.values
    assert result.row_source is namespaces.binding_environment.row_source
    assert result.final_output is result.row_source.final_output
    assert result.multifact_region is expected_region
    assert bridge.multifact_region is expected_region
    assert bridge.properties is expected_region.final_properties
    assert bridge.properties.join is result.row_source.region.joins[-1]
    assert bridge.relational is bridge.properties.relational
    assert bridge.null_extension is bridge.properties.null_extension
    assert bridge.ordering is bridge.properties.ordering
    assert bridge.keys is bridge.relational.keys
    assert bridge.fds is bridge.relational.fds
    assert bridge.fd_index is bridge.relational.fd_index
    assert bridge.grain is bridge.relational.grain
    historical = result.row_source.historical_semantic_facts.state
    assert historical.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert historical.reason is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED


def test_every_final_occurrence_is_covered_once_without_duplicate_collapse(
    built: _Built,
) -> None:
    result = _concrete(built, "unique_target_left")
    scalar_fields = result.namespaces.binding_environment.scalar_environment.fields
    joined_fields = result.final_output.row_shape.fields
    property_fields = result.property_bridge.relational.fields
    assert len(result.fields) == len(scalar_fields) == len(joined_fields) == 5
    assert tuple(item.scalar_field for item in result.fields) == scalar_fields
    assert tuple(item.joined_field for item in result.fields) == joined_fields
    assert tuple(item.property_field for item in result.fields) == property_fields
    assert tuple(item.joined_field.field_position for item in result.fields) == tuple(
        range(5)
    )
    ids = tuple(
        item for item in result.fields if item.joined_field.evidence.name == "id"
    )
    assert len(ids) == 2
    assert ids[0].joined_field is not ids[1].joined_field
    assert ids[0].property_field is not ids[1].property_field
    assert ids[0].canonical_field is not ids[1].canonical_field


def test_nullability_coheres_for_original_inner_left_and_transitive_cases(
    built: _Built,
) -> None:
    inner = _concrete(built, "nullable_inner_join")
    matched_amounts = tuple(
        item for item in inner.fields if item.joined_field.evidence.name == "amount"
    )
    assert len(matched_amounts) == 2
    assert all(
        item.joined_field.evidence.nullability is ProjectRowFieldNullability.NULLABLE
        and item.effective_nullability is ProjectRowFieldNullability.NON_NULL
        and item.scalar_field.value_type.nullability.value
        == item.effective_nullability.value
        for item in matched_amounts
    )

    left = _concrete(built, "let_attached_join")
    base_amount = next(
        item
        for item in left.fields
        if item.joined_field.evidence.name == "amount" and not item.nulling_joins
    )
    target_id = left.fields[-1]
    assert (
        base_amount.joined_field.evidence.nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    assert base_amount.effective_nullability is ProjectRowFieldNullability.NULLABLE
    assert (
        target_id.joined_field.evidence.nullability
        is ProjectRowFieldNullability.NON_NULL
    )
    assert target_id.effective_nullability is ProjectRowFieldNullability.NULLABLE
    assert len(target_id.nulling_joins) == 1

    multihop = _concrete(built, "source_multihop_left")
    assert (
        type(multihop.property_bridge.null_extension) is ProjectIRProvidedNullExtension
    )
    nulled = tuple(item for item in multihop.fields if item.nulling_joins)
    assert nulled
    assert all(
        item.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in nulled
    )
    assert max(len(item.nulling_joins) for item in nulled) == 2

    no_nulling = _concrete(built, "unique_target_inner")
    unavailable = no_nulling.property_bridge.null_extension
    assert type(unavailable) is ProjectIRJoinUnavailableProperty
    assert unavailable.availability is ProjectIRPropertyAvailability.NOT_APPLICABLE
    assert (
        no_nulling.property_bridge.ordering.availability
        is ProjectIRPropertyAvailability.UNKNOWN
    )


def test_source_and_renamed_relation_lineage_reuse_exact_attribution(
    built: _Built,
) -> None:
    source = _concrete(built, "source_multihop_left")
    assert all(
        item.canonical_field.kind is ProjectModuleRowFieldKind.SOURCE_FIELD
        and item.source_origin is not None
        and item.source_origin.source_field is item.canonical_field
        and item.output_attribution is None
        and item.lineage.paths[0].root_field is item.canonical_field
        for item in source.fields
    )
    assert all(item.source_roots == (item.canonical_field,) for item in source.fields)

    renamed = _concrete(built, "renamed_upstream_join")
    relation_fields = tuple(
        item
        for item in renamed.fields
        if item.canonical_field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
    )
    assert tuple(item.canonical_field.name for item in relation_fields) == (
        "customer_key",
        "raw_amount",
    )
    assert all(
        item.output_attribution is not None
        and item.output_attribution.identity is item.canonical_field
        and built.attribution.find_relation_output_field(item.canonical_field)
        == (item.output_attribution,)
        for item in relation_fields
    )
    assert (
        relation_fields[0].lineage.paths[0].hops[0].projection_kind
        is ProjectModuleProjectionKind.RENAMED
    )
    assert (
        relation_fields[1].lineage.paths[0].hops[0].projection_kind
        is ProjectModuleProjectionKind.RENAMED
    )


@pytest.mark.parametrize("name", ("computed_upstream_join", "let_upstream_join"))
def test_existing_nonconcrete_computed_or_let_lineage_fails_closed(
    built: _Built,
    name: str,
) -> None:
    result = _result(built, name)
    assert type(result) is joined_semantics.ProjectNonConcreteJoinedRowSemantics
    assert (
        result.reason
        is joined_semantics.ProjectJoinedRowSemanticsNonConcreteReason.UPSTREAM_LINEAGE_NON_CONCRETE
    )
    assert result.post_let is None
    assert result.property_bridge is None
    assert result.fields == ()
    assert result.lineage_issues
    assert all(
        issue.canonical_field.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
        and issue.lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE
        and built.attribution.find_row_lineage(issue.canonical_field.owner)
        == (issue.lineage,)
        for issue in result.lineage_issues
    )


def test_repeated_and_hidden_occurrences_keep_distinct_rows_and_shared_roots(
    built: _Built,
) -> None:
    repeated = _concrete(built, "repeated_source_join")
    environment = repeated.namespaces.binding_environment
    first = next(
        item for item in environment.bindings if item.binding.name == "first_orders"
    )
    second = next(
        item for item in environment.bindings if item.binding.name == "second_orders"
    )
    first_semantics = tuple(
        item
        for item in repeated.fields
        if any(item.scalar_field is field for field in first.fields)
    )
    second_semantics = tuple(
        item
        for item in repeated.fields
        if any(item.scalar_field is field for field in second.fields)
    )
    assert len(first_semantics) == len(second_semantics) == 4
    for left, right in zip(first_semantics, second_semantics, strict=True):
        assert left.joined_field is not right.joined_field
        assert left.property_field is not right.property_field
        assert left.introduction_use is not right.introduction_use
        assert left.canonical_field is right.canonical_field
        assert left.source_roots == right.source_roots

    multihop = _concrete(built, "source_multihop_left")
    hidden = multihop.namespaces.binding_environment.hidden_fields
    hidden_semantics = tuple(
        item
        for item in multihop.fields
        if any(item.scalar_field is field for field in hidden)
    )
    assert tuple(item.scalar_field for item in hidden_semantics) == hidden
    assert hidden_semantics
    assert all(item.lineage.paths for item in hidden_semantics)


def test_slice5_success_no_let_and_failure_attach_without_partial_stage(
    built: _Built,
) -> None:
    with_let = built.namespaces["let_attached_join"]
    no_let = built.namespaces["unique_target_left"]
    invalid = built.namespaces["invalid_let_stage_join"]
    assert type(with_let) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert type(no_let) is scalar_namespaces.ProjectConcreteJoinedLetNamespaces
    assert type(invalid) is scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces
    assert _concrete(built, "let_attached_join").post_let is with_let.post_let
    no_let_result = _concrete(built, "unique_target_left")
    assert no_let_result.post_let is no_let.post_let
    assert no_let_result.let_values == ()
    blocked = _result(built, "invalid_let_stage_join")
    assert type(blocked) is joined_semantics.ProjectNonConcreteJoinedRowSemantics
    assert (
        blocked.reason
        is joined_semantics.ProjectJoinedRowSemanticsNonConcreteReason.LET_NAMESPACE_NON_CONCRETE
    )
    assert blocked.upstream_blocker is invalid
    assert blocked.post_let is None
    assert blocked.property_bridge is None
    assert blocked.fields == ()


def test_historical_join_owner_never_receives_new_field_identity_or_state(
    built: _Built,
) -> None:
    result = _concrete(built, "let_attached_join")
    owner = result.row_source.region.ledger.owner
    historical = result.row_source.historical_semantic_facts
    assert historical.owner is owner
    assert historical.state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert (
        historical.state.reason is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
    )
    assert (
        built.attribution.find_relation_output_fields(
            result.final_output.row_shape.relation.identity
        )
        == ()
    )
    assert all(
        item.canonical_field.owner != result.final_output.row_shape.relation.identity
        for item in result.fields
    )


def test_slice6_scope_dependency_and_contract_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 7
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 4
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "joined occurrence != canonical upstream field identity",
        "introduction_use.output",
        "ProjectModuleAttributionFactSet from the exact same semantic root",
        "computed/LET/grouped/window module lineage remains deferred",
        "NULL_EXTENSION, ordering availability",
        "property bridge is reference-only",
        "production 167 -> 168 and tests 410 -> 411",
        "Slice 7 becomes NEXT / NOT IMPLEMENTED",
        "Slice 7 is not begun here",
    ):
        assert evidence in normalized

    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert joined_semantics.__all__ == ()
    assert not re.search(r"^class .*FieldIdentity", facts.text, re.MULTILINE)
    for required in (
        "ProjectIRJoinedRowField",
        "ProjectIROutputFieldOccurrence",
        "ProjectModuleRowFieldIdentity",
        "ProjectModuleRowFieldLineage",
        "ProjectMultiFactConcreteRegion",
        "ProjectIRJoinOutputProperties",
    ):
        assert required in facts.identifiers
    for forbidden in (
        "build_project_ir_join_region",
        "build_project_multifact_analysis",
        "projectrowschema",
        "dependencygraph",
        "filter",
        "grouping",
        "windowexpr",
        "qualify",
        "scheduler",
        "effective_output",
        "executor",
    ):
        assert forbidden not in facts.text.casefold()
    assert "pietto._project.row_lineage" not in facts.imported_modules
    for relative in (
        "src/pietto/_project/project_scalar_namespaces.py",
        "src/pietto/_project/project_ir_properties.py",
        "src/pietto/_project/project_ir_relational_properties.py",
        "src/pietto/_project/project_ir_joins.py",
        "src/pietto/_project/project_multifact.py",
        "src/pietto/_project/project_phase62_verification.py",
        "src/pietto/_project/module_attribution.py",
    ):
        assert not any(
            name.endswith(".project_joined_row_semantics")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )
