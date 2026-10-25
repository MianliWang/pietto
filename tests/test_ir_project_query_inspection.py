from __future__ import annotations

import ast
from copy import copy
from dataclasses import replace
from pathlib import Path

import pytest

from pietto._project import project_query_block_ir_inspection as inspection
from pietto._project import project_query_block_ir_pure_boundary as pure
from pietto._project import project_phase62_inspection as base_inspection
from pietto._project import project_phase62_pure_boundary as base_pure
from pietto._project.project_phase62_verification import (
    build_project_phase62_analysis_bundle,
)
from pietto._project.project_ir import _declaration_identity
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationIssue,
    ProjectIRQueryBlockVerificationIssueKind,
    ProjectIRQueryBlockVerificationStatus,
)
from _pietto_project_aggregate import _build

REPO_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_SOURCE = (
    REPO_ROOT / "src/pietto/_project/project_query_block_ir_inspection.py"
)
PURE_SOURCE = REPO_ROOT / "src/pietto/_project/project_query_block_ir_pure_boundary.py"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    return _build(tmp_path_factory.mktemp("aggregate_inspection"))


@pytest.fixture(scope="module")
def bundle(built):
    return built[2]


@pytest.fixture(scope="module")
def product(built):
    return built[3]


def _same_objects(actual, expected):
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _unsafe(value, **changes):
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


def _record(document, kind):
    return next(i for i, item in enumerate(document.records) if item.kind is kind)


def _field(record, key):
    return next(i for i, item in enumerate(record.fields) if item.key == key)


def _replace_field(document, position, field_position, value):
    record = document.records[position]
    fields = list(record.fields)
    fields[field_position] = replace(fields[field_position], value=value)
    records = list(document.records)
    records[position] = replace(record, fields=tuple(fields))
    return replace(document, records=tuple(records))


def test_owners_are_private_pure_and_single_encoder():
    assert inspection.__all__ == pure.__all__ == ()
    pure_source = PURE_SOURCE.read_text(encoding="utf-8")
    inspection_source = INSPECTION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(pure_source)
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"__future__", "dataclasses", "enum", "heapq", "typing"}
    assert (
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_encode_document"
            for node in ast.walk(tree)
        )
        == 1
    )
    assert "project_bag_null_oracle" not in pure_source + inspection_source
    assert "deserialize" not in pure_source + inspection_source
    assert ".encode(" not in inspection_source


def test_verified_bundle_only_admission_and_exact_runtime_closure(bundle, product):
    observed = product.inspection
    root = bundle.root
    assert observed.analysis_bundle is bundle
    assert observed.verification is bundle.verification
    assert observed.root is root
    assert observed.completed is root.completed
    assert observed.project_completion is root.completed.completion
    assert observed.effective_output_completion is root.completed.effective_outputs
    assert observed.phase62_verification is root.completed.verification
    assert observed.phase62_root is root.completed.verification.root
    assert observed.base_plan is root.base_plan
    assert observed.join_stage is root.join_stage
    assert observed.owners is root.owners
    assert observed.dependencies is root.dependencies
    assert observed.schedule is root.schedule
    assert observed.entries is root.entries
    assert observed.combined_reverse_uses is bundle.combined_reverse_uses
    assert observed.combined_topological_order is bundle.combined_topological_order
    assert observed.combined_reachability is bundle.combined_reachability
    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_query_block_ir_inspection(root)
    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_query_block_ir_inspection(bundle.verification)
    invalid = _unsafe(
        bundle.verification,
        status=ProjectIRQueryBlockVerificationStatus.INVALID,
        issues=(
            ProjectIRQueryBlockVerificationIssue(
                kind=ProjectIRQueryBlockVerificationIssueKind.ROOT_CONTINUITY
            ),
        ),
    )
    with pytest.raises(ValueError, match="VERIFIED"):
        inspection.build_project_query_block_ir_inspection(
            _unsafe(bundle, verification=invalid)
        )


def test_complete_runtime_sections_retain_occurrences_not_winners(product):
    observed = product.inspection
    root = observed.root
    base = root.base_plan.structural_stage
    join = root.join_stage.structural
    for actual, expected in (
        (observed.combined_nodes, (*base.nodes, *join.nodes, *root.structural.nodes)),
        (
            observed.combined_outputs,
            (*base.outputs, *join.outputs, *root.structural.outputs),
        ),
        (
            observed.combined_input_slots,
            (*base.input_slots, *join.input_slots, *root.structural.input_slots),
        ),
        (observed.combined_uses, (*base.uses, *join.uses, *root.structural.uses)),
    ):
        assert _same_objects(actual, expected)
    assert observed.algebra_joins
    assert all(
        len(item.inputs) == len(item.input_uses) == 2 for item in observed.algebra_joins
    )
    left = tuple(
        item for item in observed.algebra_joins if item.source.kind.value == "left"
    )
    assert left and all(
        any(field.nulling_joins for field in item.source.output.row_shape.fields)
        for item in left
    )
    assert observed.predicate_calls and observed.predicate_equalities
    assert all(
        item.fd_index.facts == item.fds for item in observed.relational_properties
    )
    assert (
        tuple(item.blocker for item in observed.terminals) == observed.terminal_blockers
    )
    assert observed.terminals
    assert observed.summary.entry_count == len(observed.entries)
    assert observed.summary.analysis_entry_count == sum(
        map(
            len,
            (
                observed.combined_reverse_uses,
                observed.combined_topological_order,
                observed.combined_reachability,
            ),
        )
    )


def test_current_predicate_inventory_matches_every_authored_call_and_exact_inputs(
    product,
):
    from pietto import ast_nodes as nodes
    from pietto.semantic.inline_functions import _tree_nodes

    observed = product.inspection
    root = observed.root
    semantic = root.completed.semantic_result
    names = {
        module.path: {
            template.name
            for template in module.parsed_input.script.relationship_templates
        }
        for module in semantic.modules
        if module.parsed_input is not None
    }
    authored = tuple(
        node
        for owner in root.owners
        for node in _tree_nodes(owner.definition)
        if type(node) is nodes.CallExpr
        and type(node.callee) is nodes.NameExpr
        and node.callee.name in names[owner.identity.module_path]
    )
    assert authored
    assert _same_objects(
        tuple(call.call for call in observed.predicate_calls), authored
    )
    canonical = root.completed.roots.join_conditions.predicate_expressions
    expected = tuple(
        record
        for owner in root.owners
        for record in canonical
        if record.owner is owner and record.calls
    )
    assert _same_objects(observed.predicate_expressions, expected)
    for record in expected:
        for call, bindings in zip(record.calls, record.argument_bindings, strict=True):
            assert (
                call.context is record.context and call.owner is record.owner.definition
            )
            for argument, binding in zip(call.arguments, bindings, strict=True):
                assert binding.owner is record.owner and binding.target is not None
                assert argument.occurrence is binding.site
                assert argument.relation is binding.target.target_occurrence.definition
    conditions = tuple(
        joined.condition
        for joined in sorted(
            (*observed.historical_matches, *observed.algebra_joins),
            key=lambda joined: joined.node.ref.position,
        )
        if joined.condition.environment.predicate_expression is not None
        and joined.condition.environment.predicate_expression.calls
    )
    assert conditions
    assert _same_objects(
        observed.predicate_equalities,
        tuple(
            equality
            for condition in conditions
            for equality in condition.mandatory_equalities
        ),
    )
    assert _same_objects(
        observed.predicate_key_matches,
        tuple(match for condition in conditions for match in condition.key_matches),
    )
    assert observed.predicate_key_matches
    for equality in observed.predicate_equalities:
        assert equality.calls and all(
            any(call is retained for retained in observed.predicate_calls)
            for call in equality.calls
        )
    (control,) = tuple(
        entry
        for entry in root.completed.effective_outputs.entries
        if entry.owner.definition.name == "aggregate_left_outputs"
    )
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput

    assert isinstance(control, ProjectCompletedEffectiveOutput)
    assert tuple(control.schema.fields) == ("order_id", "matched_customer_id")
    from pietto._project.model import ProjectRowFieldNullability

    assert (
        control.schema.fields["order_id"].nullability
        is ProjectRowFieldNullability.NON_NULL
    )
    assert (
        control.schema.fields["matched_customer_id"].nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    (entry,) = tuple(value for value in root.entries if value.owner is control.owner)
    assert (
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    joined = entry.join_prefix.final_join
    assert (
        joined.inputs[0].producer is not None and joined.inputs[1].producer is not None
    )
    assert joined.inputs[0].producer.definition.name == "orders"
    assert joined.inputs[1].producer.definition.name == "customers"
    left_width = len(joined.inputs[0].source_properties.fields)
    assert all(
        not field.nulling_joins for field in joined.output.row_shape.fields[:left_width]
    )
    assert all(
        len(field.nulling_joins) == 1 and field.nulling_joins[0] is joined.node.ref
        for field in joined.output.row_shape.fields[left_width:]
    )


@pytest.mark.parametrize(
    "owner_name",
    (
        "aggregate_pair_outputs",
        "aggregate_pair_same_input",
        "aggregate_pair_keyed",
        "aggregate_pair_shared_inputs",
    ),
)
def test_current_aggregate_candidates_keep_all_authorities_and_common_grains(
    product, owner_name
):
    from pietto._project.project_grain import (
        ProjectGrainFactorSet,
        grain_dependency_closure,
    )
    from pietto._project.project_multifact import (
        ProjectActualGrainAuthorityKind,
        ProjectCommonGrainStatus,
        ProjectCurrentMultiFactRegion,
    )
    from pietto.ast_nodes import QueryDef, TableDef
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
        ProjectNonConcreteJoinedAggregation,
        ProjectJoinedAggregateOccurrence,
    )

    completed = product.inspection.completed
    base_facts = completed.verification.root.facts
    assert len(base_facts) > len({fact.identity.aggregate_node for fact in base_facts})
    (result,) = tuple(
        result
        for tail in completed.effective_outputs.current_tails
        for result in tail.window_set.aggregation_set.results
        if result.input_filter.entry.owner.definition.name == owner_name
    )
    if type(result) is ProjectConcreteJoinedAggregation:
        aggregates = result.aggregates
    else:
        assert type(result) is ProjectNonConcreteJoinedAggregation
        aggregates = result.aggregate_results
    assert len(aggregates) == len(result.grain_linkages) == 2
    assert all(type(item) is ProjectJoinedAggregateOccurrence for item in aggregates), (
        aggregates
    )
    definition = result.input_filter.entry.owner.definition
    assert isinstance(definition, (QueryDef, TableDef))
    assert all(
        aggregate.selected_output_ordinal == ordinal
        and aggregate.item is definition.select_items[ordinal]
        for ordinal, aggregate in enumerate(aggregates)
    )
    (pair,) = result.pair_linkages
    left, right = result.grain_linkages
    assert pair.left is left and pair.right is right
    assert left.aggregate is aggregates[0] and right.aggregate is aggregates[1]
    assert left.aggregate.call is not right.aggregate.call
    region = left.multifact_region
    assert right.multifact_region is region
    assert type(region) is ProjectCurrentMultiFactRegion
    expected = tuple(
        authority
        for join, properties in zip(
            region.region.joins, region.region.join_properties, strict=True
        )
        for authority in (
            (
                ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT,
                (join, join.input_uses[0], join.left_input.grain),
            ),
            (
                ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT,
                (join, join.input_uses[1], join.right_input.grain),
            ),
            (
                ProjectActualGrainAuthorityKind.JOIN_OUTPUT,
                (join, properties.relational.grain),
            ),
        )
    )
    assert region.actual_candidates
    positions = []
    candidate_positions = []
    for candidate in region.actual_candidates:
        selected = []
        for authority in candidate.authorities:
            (position,) = tuple(
                i
                for i, (kind, evidence) in enumerate(expected)
                if authority.kind is kind
                and _same_objects(authority.evidence, evidence)
            )
            selected.append(position)
        assert selected == sorted(selected)
        positions.extend(selected)
        candidate_positions.append(tuple(selected))
    assert sorted(positions) == list(range(len(expected)))
    common = pair.common_grain
    assert common.actual_candidates is region.actual_candidates
    index = region.grain_index
    closures = tuple(
        grain_dependency_closure(
            index,
            ProjectGrainFactorSet(
                universe=index.universe, factors=link.contextual_grain.factors
            ),
        )
        for link in (left, right)
    )
    expected_common = tuple(
        candidate
        for candidate in region.actual_candidates
        if all(candidate.factors.mask & ~closure.mask == 0 for closure in closures)
    )
    assert _same_objects(
        tuple(item.candidate for item in common.common_candidates), expected_common
    )
    candidate_closures = {
        id(candidate): grain_dependency_closure(index, candidate.factors).mask
        for candidate in expected_common
    }
    expected_retained = tuple(
        candidate
        for candidate in expected_common
        if not any(
            candidate.factors.mask & ~candidate_closures[id(other)] == 0
            and other.factors.mask & ~candidate_closures[id(candidate)] != 0
            for other in expected_common
        )
    )
    assert _same_objects(
        tuple(item.candidate for item in common.candidates), expected_retained
    )
    assert left.contextual_grain.factors and right.contextual_grain.factors
    left_reaches_right = set(right.contextual_grain.factors) <= set(closures[0].factors)
    right_reaches_left = set(left.contextual_grain.factors) <= set(closures[1].factors)
    if owner_name == "aggregate_pair_outputs":
        # The key-proved local right -> prior-input dependencies (orders ->
        # customers, returned -> dimension) make both closures reach the first
        # join's three grains: the ambiguous chasm of aggregate_pair_shared_inputs.
        assert len(region.region.joins) == 3
        assert tuple(candidate_positions) == (
            (0,),
            (1,),
            (2, 3),
            (4,),
            (5, 6),
            (7,),
            (8,),
        )
        assert _same_objects(expected_common, region.actual_candidates[:3])
        assert _same_objects(expected_retained, expected_common)
        assert type(result) is ProjectNonConcreteJoinedAggregation
        assert common.status is ProjectCommonGrainStatus.AMBIGUOUS
        assert common.candidate is None
        assert not left_reaches_right and not right_reaches_left
        assert len(pair.chasm_candidates) == 3
        assert _same_objects(pair.chasm_candidates, common.candidates)
    elif owner_name == "aggregate_pair_same_input":
        assert len(expected_retained) == 1
        assert common.status is ProjectCommonGrainStatus.UNIQUE
        assert common.candidate is expected_retained[0]
        assert left_reaches_right and right_reaches_left
        assert pair.chasm_candidates == ()
    else:
        assert len(expected_retained) >= 2
        assert common.status is ProjectCommonGrainStatus.AMBIGUOUS
        assert common.candidate is None
        if owner_name == "aggregate_pair_keyed":
            assert type(result) is ProjectConcreteJoinedAggregation
            assert left_reaches_right and right_reaches_left
            assert pair.chasm_candidates == ()
        else:
            assert not left_reaches_right and not right_reaches_left
            assert _same_objects(pair.chasm_candidates, common.candidates)
    for linkage in (left, right):
        for exposure in linkage.multiplicity_exposures:
            assert any(exposure.join is join for join in region.region.joins)
            assert exposure.factor_additions


def test_typed_queries_are_scope_closed_and_return_complete_buckets(product, tmp_path):
    observed = product.inspection
    for entry in observed.entries:
        identity = _declaration_identity(entry.owner)
        bucket = tuple(
            item
            for item in observed.entries
            if _declaration_identity(item.owner) == identity
        )
        assert _same_objects(
            inspection.query_project_query_block_entries(observed, identity), bucket
        )
        assert _same_objects(
            inspection.query_project_query_block_terminals(observed, identity),
            tuple(
                item
                for item in observed.terminals
                if _declaration_identity(item.owner) == identity
            ),
        )
        concrete = (
            ProjectIRReusedEffectiveOutput,
            ProjectIRReboundExistingOutput,
            ProjectIRCompletedQueryBlockOutput,
            ProjectIRCompletedSetOperationOutput,
        )
        expected_roots = tuple(
            (item.active_output, item.active_properties)
            for item in bucket
            if isinstance(item, concrete)
        )
        actual_roots = inspection.query_project_query_block_active_roots(
            observed, identity
        )
        assert len(actual_roots) == len(expected_roots)
        assert all(
            actual_output is expected_output
            and actual_properties is expected_properties
            for (actual_output, actual_properties), (
                expected_output,
                expected_properties,
            ) in zip(actual_roots, expected_roots, strict=True)
        )
        expected_inputs = tuple(
            item.relation_input
            for item in bucket
            if isinstance(
                item,
                (ProjectIRReboundExistingOutput, ProjectIRCompletedQueryBlockOutput),
            )
            and item.relation_input is not None
        )
        assert _same_objects(
            inspection.query_project_query_block_relation_inputs(observed, identity),
            expected_inputs,
        )
    for items, query in (
        (observed.combined_nodes, inspection.query_project_query_block_nodes),
        (observed.combined_outputs, inspection.query_project_query_block_outputs),
        (
            observed.combined_input_slots,
            inspection.query_project_query_block_input_slots,
        ),
        (observed.combined_uses, inspection.query_project_query_block_uses),
    ):
        assert items
        for item in items:
            assert _same_objects(
                query(observed, item.ref),
                tuple(other for other in items if other.ref == item.ref),
            )
    for node in observed.combined_nodes:
        assert _same_objects(
            inspection.query_project_query_block_reachability(observed, node.ref),
            tuple(
                item
                for item in observed.combined_reachability
                if item.source.ref == node.ref
            ),
        )
        assert _same_objects(
            inspection.query_project_query_block_grain_origins(observed, node.ref),
            tuple(
                item for item in observed.grain_origins if item.operator.ref == node.ref
            ),
        )
    for output in observed.combined_outputs:
        assert _same_objects(
            inspection.query_project_query_block_reverse_uses(observed, output.ref),
            tuple(
                item
                for item in observed.combined_reverse_uses
                if item.output.ref == output.ref
            ),
        )
    for field in observed.query_block_row_fields:
        if field.final_identity is not None:
            assert _same_objects(
                inspection.query_project_query_block_final_fields(
                    observed, field.final_identity
                ),
                tuple(
                    item
                    for item in observed.query_block_row_fields
                    if item.final_identity is field.final_identity
                ),
            )
    for factor in observed.grain_factors:
        assert _same_objects(
            inspection.query_project_query_block_grain_factors(
                observed, factor.identity
            ),
            tuple(
                item
                for item in observed.grain_factors
                if item.identity is factor.identity
            ),
        )
    foreign = _build(tmp_path / "foreign")[3].inspection
    with pytest.raises(ValueError, match="snapshot scope"):
        inspection.query_project_query_block_nodes(
            foreign, observed.combined_nodes[0].ref
        )
    with pytest.raises(ValueError, match="VERIFIED analysis bundle"):
        replace(observed, analysis_bundle=foreign.analysis_bundle)
    with pytest.raises(ValueError, match="combined_outputs"):
        replace(
            observed,
            combined_outputs=(*observed.combined_outputs, foreign.combined_outputs[-1]),
        )


def test_current_and_retained_base_portable_coordinate_contracts_are_explicit(product):
    outcome = pure.evaluate_project_query_block_ir_document(product.document)
    assert outcome.status is pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes
    domains = {
        pure.ProjectQueryBlockIRPortableRefDomain.PLAN_NODE,
        pure.ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE,
        pure.ProjectQueryBlockIRPortableRefDomain.INPUT_SLOT,
        pure.ProjectQueryBlockIRPortableRefDomain.USE,
    }

    def shift(ref):
        return replace(ref, position=ref.position + 7) if ref.domain in domains else ref

    records = tuple(
        replace(
            record,
            fields=tuple(
                replace(
                    field,
                    value=(
                        replace(field.value, ref=shift(field.value.ref))
                        if field.value.tag is pure.ProjectQueryBlockIRPureTag.REF
                        else replace(
                            field.value, refs=tuple(map(shift, field.value.refs))
                        )
                        if field.value.tag is pure.ProjectQueryBlockIRPureTag.REFS
                        else replace(field.value, integer=field.value.integer + 7)
                        if record.kind is pure.ProjectQueryBlockIRRecordKind.HEADER
                        and field.key
                        in {
                            "node_start",
                            "output_start",
                            "slot_start",
                            "use_start",
                            "node_end",
                            "output_end",
                            "slot_end",
                            "use_end",
                        }
                        else field.value
                    ),
                )
                for field in record.fields
            ),
        )
        for record in product.document.records
    )
    shifted = pure.evaluate_project_query_block_ir_document(
        replace(product.document, records=records)
    )
    assert shifted.status is pure.ProjectQueryBlockIRPureStatus.INVALID_COUNT
    assert shifted.canonical_bytes is None

    retained = base_inspection.build_project_phase62_inspection(
        build_project_phase62_analysis_bundle(product.inspection.completed.verification)
    )
    assert (
        base_pure.evaluate_project_phase62_document(retained.document).canonical_bytes
        == retained.canonical_bytes
    )
    base_domains = {
        base_pure.ProjectPhase62PortableRefDomain.PLAN_NODE,
        base_pure.ProjectPhase62PortableRefDomain.OUTPUT_VALUE,
        base_pure.ProjectPhase62PortableRefDomain.INPUT_SLOT,
        base_pure.ProjectPhase62PortableRefDomain.USE,
    }

    def shift_base(ref):
        return (
            replace(ref, position=ref.position + 7)
            if ref.domain in base_domains
            else ref
        )

    shifted_base = replace(
        retained.document,
        records=tuple(
            replace(
                record,
                fields=tuple(
                    replace(
                        field,
                        value=replace(field.value, ref=shift_base(field.value.ref))
                        if field.value.tag is base_pure.ProjectPhase62PureTag.REF
                        else replace(
                            field.value, refs=tuple(map(shift_base, field.value.refs))
                        )
                        if field.value.tag is base_pure.ProjectPhase62PureTag.REFS
                        else field.value,
                    )
                    for field in record.fields
                ),
            )
            for record in retained.document.records
        ),
    )
    base_outcome = base_pure.evaluate_project_phase62_document(shifted_base)
    assert base_outcome.status is base_pure.ProjectPhase62PureStatus.OK
    assert base_outcome.canonical_bytes != retained.canonical_bytes


def test_pure_evaluator_normalizes_malformed_documents_without_text_echo(product):
    document = product.document
    evaluate = pure.evaluate_project_query_block_ir_document
    status = pure.ProjectQueryBlockIRPureStatus
    assert evaluate(object()).status is status.INVALID_DOCUMENT
    unknown = evaluate(replace(document, format_marker="untrusted\ntext"))
    assert unknown.status is status.UNKNOWN_FORMAT and unknown.canonical_bytes is None
    assert not hasattr(unknown, "message")
    missing = evaluate(replace(document, records=document.records[1:]))
    assert missing.status is status.INVALID_HEADER and missing.record_position == 0
    node = _record(document, pure.ProjectQueryBlockIRRecordKind.NODE)
    dependency = _record(document, pure.ProjectQueryBlockIRRecordKind.DEPENDENCY)
    records = list(document.records)
    records[node], records[dependency] = records[dependency], records[node]
    assert (
        evaluate(replace(document, records=tuple(records))).status
        is status.INVALID_SECTION_ORDER
    )
    algebra = _record(document, pure.ProjectQueryBlockIRRecordKind.ALGEBRA)
    inputs = _field(document.records[algebra], "inputs")
    refs = document.records[algebra].fields[inputs].value.refs
    malformed = evaluate(
        _replace_field(
            document, algebra, inputs, pure.project_query_block_ir_pure_refs(refs[:1])
        )
    )
    assert (
        malformed.status is status.INVALID_OPERATOR
        and malformed.canonical_bytes is None
    )
    use = _record(document, pure.ProjectQueryBlockIRRecordKind.USE)
    output = _field(document.records[use], "output")
    dangling = pure.project_query_block_ir_pure_ref(
        pure.ProjectQueryBlockIRPortableRef(
            domain=pure.ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE,
            position=10**6,
        )
    )
    assert (
        evaluate(_replace_field(document, use, output, dangling)).status
        is status.DANGLING_REF
    )
    invalid = _unsafe(
        document.records[algebra].fields[inputs].value, refs="untrusted\ntext"
    )
    outcome = evaluate(_replace_field(document, algebra, inputs, invalid))
    assert outcome.status is status.INVALID_VALUE
    assert (outcome.record_position, outcome.field_position) == (algebra, inputs)
    assert outcome.canonical_bytes is None and not hasattr(outcome, "message")


def test_projection_is_zero_mutation_and_repeatable(bundle, product):
    root = bundle.root
    observed = product.inspection
    before = (
        root,
        root.structural,
        root.entries,
        bundle.verification,
        bundle.combined_reverse_uses,
        bundle.combined_topological_order,
        bundle.combined_reachability,
        *observed.combined_nodes,
        *observed.combined_outputs,
        *observed.combined_input_slots,
        *observed.combined_uses,
    )
    repeated = inspection.build_project_query_block_ir_inspection(bundle)
    after = (
        bundle.root,
        root.structural,
        root.entries,
        bundle.verification,
        bundle.combined_reverse_uses,
        bundle.combined_topological_order,
        bundle.combined_reachability,
        *repeated.inspection.combined_nodes,
        *repeated.inspection.combined_outputs,
        *repeated.inspection.combined_input_slots,
        *repeated.inspection.combined_uses,
    )
    assert _same_objects(after, before)
    assert repeated.document == product.document
    assert repeated.canonical_bytes == product.canonical_bytes
