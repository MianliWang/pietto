"""Real semantic products retained in one independently verified combined IR."""

from pathlib import Path

import pytest

from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockTerminal,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT,
    ProjectQueryBlockIRPureStatus,
    evaluate_project_query_block_ir_document,
)
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)


def _vertical_source(kind: str, side: str) -> str:
    source = _source("lhs.id == r.id", kind=kind)
    prepared = """table prepared:
    from rhs
    inner join lhs as x:
        from rhs
        on rhs.id == x.id
    select:
        id = rhs.id
"""
    source = source.replace("query result:\n", prepared + "query result:\n")
    head, query = source.split("query result:\n", 1)
    if side == "right":
        query = query.replace(f"{kind} join rhs as r:", f"{kind} join prepared as r:")
    else:
        query = query.replace("from lhs", "from prepared").replace(
            "lhs.id", "prepared.id"
        )
    return head + "query result:\n" + query


@pytest.mark.parametrize("kind", ("inner", "left"))
@pytest.mark.parametrize("side", ("left", "right"))
def test_effective_input_vertical_to_verified_private_observation(
    tmp_path: Path, kind: str, side: str
) -> None:
    completed = _completed(tmp_path, _vertical_source(kind, side))
    assert completed.ok, completed.diagnostics
    semantics = {
        entry.owner.definition.name: entry
        for entry in completed.effective_outputs.entries
    }
    assert isinstance(semantics["prepared"], ProjectCompletedEffectiveOutput)
    snapshot = build_project_query_block_ir(completed)
    assert not any(
        isinstance(entry, ProjectIRQueryBlockTerminal) for entry in snapshot.entries
    )
    entries = {entry.owner.definition.name: entry for entry in snapshot.entries}
    prepared, result = entries["prepared"], entries["result"]
    assert isinstance(prepared, ProjectIRCompletedQueryBlockOutput)
    assert isinstance(result, ProjectIRCompletedQueryBlockOutput)
    assert result.join_prefix is not None and prepared.join_prefix is not None
    joined = result.join_prefix.final_join
    ordinal = 0 if side == "left" else 1
    assert joined.inputs[ordinal].producer is prepared.owner
    assert joined.inputs[ordinal].use.output is prepared.active_output.occurrence
    assert joined.source is not prepared.join_prefix.final_join.source
    assert joined.node is not joined.source.node
    assert joined.output is not joined.source.output
    assert result.source_properties.output is joined.output
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    bundle = build_project_query_block_ir_analysis_bundle(verification)
    product = build_project_query_block_ir_inspection(bundle)
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )
    assert product.inspection.algebra_joins == (
        *prepared.join_prefix.joins,
        *result.join_prefix.joins,
    )
    outcome = evaluate_project_query_block_ir_document(product.document)
    assert outcome.status is ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes
    assert b"input_correspondence\t" in product.canonical_bytes
    assert b"condition\t" in product.canonical_bytes


@pytest.mark.parametrize(
    "kind", ("inner", "left", "cross", "right", "full", "semi", "anti")
)
def test_all_join_kinds_keep_original_matching_and_two_input_uses(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(
        tmp_path, _source(None if kind == "cross" else "lhs.id == r.id", kind=kind)
    )
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    entry = next(
        entry for entry in snapshot.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    joined = entry.join_prefix.final_join
    assert joined.condition.use.kind.value == kind
    assert len(joined.inputs) == 2
    assert joined.inputs[0].use is not joined.inputs[1].use
    assert (
        joined.condition.expression is None
        if kind == "cross"
        else joined.condition.expression is not None
    )
    expected = 3 if kind in {"semi", "anti"} else 6
    assert len(joined.output.row_shape.fields) == expected
    for old, new in zip(
        joined.source.output.row_shape.fields,
        joined.output.row_shape.fields,
        strict=True,
    ):
        assert old.evidence is new.evidence
        assert old.effective_nullability is new.effective_nullability
        assert len(old.nulling_joins) == len(new.nulling_joins)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )


def test_distinct_visible_comparison_before_order_limit_and_downstream(
    tmp_path: Path,
) -> None:
    from pietto._project.project_query_block_ir import ProjectIRDistinctComparison

    source = """shape Row:
    id: Int nullable
source rows: Row is postgres.table("rows")
table dedup:
    from rows
    select distinct:
        id
    order by:
        id
    limit 2
query result:
    from dedup
    select:
        id
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    entry = next(
        entry for entry in snapshot.entries if entry.owner.definition.name == "dedup"
    )
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    assert [operator.kind.value for operator in entry.operators] == [
        "relation_input",
        "final_projection",
        "distinct",
        "relation_ordering",
        "limit",
    ]
    comparison = entry.operators[2].evidence
    assert isinstance(comparison, ProjectIRDistinctComparison)
    assert comparison.semantic is entry.semantic_entry.row_domain.distinct
    assert comparison.input_output is entry.row_outputs[1]
    assert comparison.fields[0].semantic_source is entry.semantic_entry.fields[0]
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )
    assert (
        b"distinct\t" in product.canonical_bytes
        and b"type_equivalence\t" in product.canonical_bytes
    )


@pytest.mark.parametrize("kind", ("union", "intersect", "except"))
@pytest.mark.parametrize("quantifier", ("all", "distinct"))
def test_six_set_forms_bind_every_authored_use_and_canonical_nonselect_output(
    tmp_path: Path, kind: str, quantifier: str
) -> None:
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedSetOperationOutput,
    )
    from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
        _source as set_source,
    )

    completed = _completed(
        tmp_path, set_source(kind, quantifier, operands=("lhs", "rhs", "lhs"))
    )
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    entries = {entry.owner.definition.name: entry for entry in snapshot.entries}
    combined = entries["combined"]
    assert isinstance(combined, ProjectIRCompletedSetOperationOutput)
    assert [
        operand.producer.owner.definition.name for operand in combined.operands
    ] == ["lhs", "rhs", "lhs"]
    assert len({use.ref for use in combined.uses}) == 3
    assert combined.operands[0].producer is combined.operands[2].producer
    assert combined.operands[0].use is not combined.operands[2].use
    assert (
        combined.active_output.row_shape.fields[0].final_identity
        is combined.semantic_entry.fields[0].identity
    )
    assert (
        combined.active_output.row_shape.fields[0].semantic_source
        is combined.semantic_entry.fields[0]
    )
    assert combined.semantic_entry.root.multiplicity.value == f"{kind}_{quantifier}"
    downstream = entries["result"]
    assert isinstance(downstream, ProjectIRCompletedQueryBlockOutput)
    assert (
        downstream.relation_input is not None
        and downstream.relation_input.use.output is combined.active_output.occurrence
    )
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    bundle = build_project_query_block_ir_analysis_bundle(verification)
    users = next(
        item.uses
        for item in bundle.combined_reverse_uses
        if item.output is combined.operands[0].producer.active_output.occurrence
    )
    assert all(
        any(use is retained for retained in users)
        for use in (combined.uses[0], combined.uses[2])
    )
    product = build_project_query_block_ir_inspection(bundle)
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )
    assert (
        b"set_operand\t" in product.canonical_bytes
        and b"set_field_map\t" in product.canonical_bytes
    )


@pytest.mark.parametrize("type_name", ("Float", "Decimal(10, 2)"))
def test_supported_set_types_survive_ir_and_portable_evidence(
    tmp_path: Path, type_name: str
) -> None:
    from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
        _source as set_source,
    )

    source = set_source(right_type=type_name).replace(
        "id: Int not null", f"id: {type_name} nullable"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )


@pytest.mark.parametrize(
    "scenario", ("unproved", "relationship", "refinement", "right_limit", "global")
)
def test_single_match_retains_actual_boundary_proof_and_warning(
    tmp_path: Path, scenario: str
) -> None:
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _request,
        _asymmetric_source,
        _limited_source,
    )

    if scenario == "unproved":
        source = _source("true", kind="semi") + "    limit 1\n"
    elif scenario in {"relationship", "refinement"}:
        source = _asymmetric_source(target_unique=True)
        if scenario == "refinement":
            source = source.replace(
                "        from lhs\n    select:",
                "        from lhs\n        via link: l -> r\n        on r.id > 0\n    select:",
            )
    elif scenario == "right_limit":
        source = _limited_source(right_limit=1)
    else:
        from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
            _tail_source,
        )

        source, _ = _tail_source("global")
        source += "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
    original = _completed(tmp_path, source)
    request = _request(original, -1)
    completed = with_project_single_match_requests(original, (request, request))
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    assert len(snapshot.requirements) == 2
    for requirement, assessment in zip(
        snapshot.requirements, completed.single_matches.entries, strict=True
    ):
        assert requirement.assessment is assessment
        assert len(requirement.input_pairs) == 1
        assert all(
            image.source is source
            for image, source in zip(requirement.proofs, assessment.proofs, strict=True)
        )
        assert assessment.downstream_enforcement_required is (scenario == "unproved")
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert product.inspection.requirements is snapshot.requirements
    assert (
        product.document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
    )
    if scenario == "unproved":
        assert len(completed.diagnostics) == 1
        assert (
            product.inspection.diagnostics[0]
            is completed.single_matches.entries[0].diagnostic
        )
        assert b"PIE-S2337" in product.canonical_bytes


@pytest.mark.parametrize("both_unique", (False, True))
def test_hop_and_whole_path_requirements_keep_distinct_composed_scopes(
    tmp_path: Path, both_unique: bool
) -> None:
    from dataclasses import replace
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import ProjectSingleMatchScope
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _request,
        _asymmetric_source,
    )

    source = (
        _asymmetric_source(target_unique=True, source_unique=both_unique)
        .replace("inner join rhs as r:", "inner join lhs as r:")
        .replace(
            "        from lhs\n    select:",
            "        from lhs\n        via link: l -> r\n        via link: r -> l\n    select:",
        )
    )
    original = _completed(tmp_path, source)
    request = _request(original)
    path = original.roots.join_conditions.entries[0].effective_use.path
    assert path is not None
    hop = replace(
        request, scope=ProjectSingleMatchScope.PATH_HOP, path=path, hop=path.steps[0]
    )
    whole = replace(request, scope=ProjectSingleMatchScope.WHOLE_PATH, path=path)
    completed = with_project_single_match_requests(original, (hop, whole))
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    assert [len(requirement.boundaries) for requirement in snapshot.requirements] == [
        1,
        2,
    ]
    assert (
        snapshot.requirements[0].boundaries[0] is snapshot.requirements[1].boundaries[0]
    )
    assert (
        snapshot.requirements[1].assessment.downstream_enforcement_required
        is not both_unique
    )
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert b"whole_path" in product.canonical_bytes


def test_grouped_output_left_join_window_qualify_retains_all_stages(
    tmp_path: Path,
) -> None:
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
        _tail_source,
    )

    source, _ = _tail_source("grouped")
    source += "query result:\n    from lhs\n    left join upstream as u:\n        from lhs\n        on u.total > 0\n    select:\n        id = lhs.id\n        total = u.total\n        rn = row_number() window:\n            order by:\n                lhs.id\n    qualify:\n        rn <= 2\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    result = next(
        entry for entry in snapshot.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(result, ProjectIRCompletedQueryBlockOutput)
        and result.join_prefix is not None
    )
    assert [op.kind.value for op in result.operators] == [
        "window_evaluation",
        "qualify",
        "final_projection",
    ]
    assert result.join_prefix.final_join.inputs[1].producer is next(
        entry.owner
        for entry in snapshot.entries
        if entry.owner.definition.name == "upstream"
    )
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    assert build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    ).canonical_bytes


@pytest.mark.parametrize("kind", ("right", "full"))
def test_accumulated_join_nulls_whole_left_in_composed_coordinates(
    tmp_path: Path, kind: str
) -> None:
    source = _source("lhs.id == r.id").replace(
        "    select:\n",
        f"    {kind} join rhs as s:\n        from lhs\n        on r.id == s.id\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    result = next(
        entry for entry in snapshot.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(result, ProjectIRCompletedQueryBlockOutput)
        and result.join_prefix is not None
    )
    first, second = result.join_prefix.joins
    assert second.inputs[0].use.output is first.output.occurrence
    assert all(
        any(ref is second.node.ref for ref in member.nulling_joins)
        for member in second.output.row_shape.fields[:6]
    )
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    assert build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    ).canonical_bytes


def test_decimal_set_join_distinct_and_named_nested_set_keep_parameter_sources(
    tmp_path: Path,
) -> None:
    from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
        _source as set_source,
    )

    source = set_source(right_type="Decimal(10, 2)").replace(
        "id: Int not null", "id: Decimal(10, 2) nullable"
    )
    source += "table joined:\n    from result\n    inner join result as r:\n        from result\n        on true\n    select distinct:\n        price = result.id\ntable final:\n    except distinct:\n        from joined\n        from joined\n        from joined\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert len(product.inspection.set_entries) == 2
    assert (
        b"Decimal" in product.canonical_bytes and b"except" in product.canonical_bytes
    )


def test_invalid_request_blocks_owner_and_all_set_membership_dependencies(
    tmp_path: Path,
) -> None:
    from dataclasses import replace
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _request,
    )

    source = _source("true").replace("query result:", "table invalid_owner:")
    source += "table blocked:\n    union all:\n        from invalid_owner\n        from invalid_owner\nquery valid:\n    from lhs\n    select:\n        id\n"
    original = _completed(tmp_path, source)
    request = replace(_request(original), input_pairs=())
    completed = with_project_single_match_requests(original, (request,))
    assert not completed.ok
    snapshot = build_project_query_block_ir(completed)
    entries = {entry.owner.definition.name: entry for entry in snapshot.entries}
    bad, blocked = entries["invalid_owner"], entries["blocked"]
    assert isinstance(bad, ProjectIRQueryBlockTerminal) and isinstance(
        blocked, ProjectIRQueryBlockTerminal
    )
    assert bad.reason.value == "invalid_single_match"
    assert blocked.blocker == (bad, bad)
    assert bad.starting_allocation is bad.ending_allocation
    assert blocked.starting_allocation is blocked.ending_allocation
    assert not isinstance(entries["valid"], ProjectIRQueryBlockTerminal)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert b"PIE-S2338" in product.canonical_bytes
