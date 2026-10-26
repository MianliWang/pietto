"""Real semantic products retained in one independently verified combined IR."""

from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
from pietto._project.project_join_conditions import ProjectJoinConditionKeyMatch
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockTerminal,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project import project_query_block_ir_pure_boundary as pure
from pietto._project.project_query_block_ir_pure_boundary import (
    PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT,
    ProjectQueryBlockIRPureStatus,
    ProjectQueryBlockIRPureValue,
    evaluate_project_query_block_ir_document,
)
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from _pietto_project_join import (
    BASE,
    _completed,
    _source,
)
from _pietto_ir_sources import vertical_source as _vertical_source


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


@pytest.mark.parametrize("kind", ("inner", "left", "cross", "right", "full"))
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
    assert len(joined.output.row_shape.fields) == 6
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
    id: Int | None
source rows: Row = postgres.table("rows")
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
    from _pietto_ir_sources import set_source as set_source

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
    from _pietto_ir_sources import set_source as set_source

    source = set_source(right_type=type_name).replace(
        "id: Int", f"id: {type_name} | None"
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
    "scenario", ("unproved", "matched_key", "guarded_key", "right_limit", "global")
)
def test_single_match_retains_actual_boundary_proof_and_warning(
    tmp_path: Path, scenario: str
) -> None:
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from _pietto_project_single_match import (
        _request,
        _asymmetric_source,
        _limited_source,
    )

    if scenario == "unproved":
        source = _source("True", kind="left") + "    limit 1\n"
    elif scenario in {"matched_key", "guarded_key"}:
        source = _asymmetric_source(target_unique=True)
        if scenario == "guarded_key":
            source = source.replace(
                "inner join r on Link(lhs, r)",
                "inner join r on Link(lhs, r) and r.id > 0",
            )
    elif scenario == "right_limit":
        source = _limited_source(right_limit=1)
    else:
        from _pietto_project_join_output import (
            _tail_source,
        )

        source, _ = _tail_source("global")
        source += "query result:\n    from lhs\n    let r = upstream\n    left join r on True\n    select:\n        id = lhs.id\n"
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
        assert assessment.condition is not None
        if scenario in {"matched_key", "guarded_key"}:
            assert [proof.kind.value for proof in assessment.proofs] == ["matched_key"]
        elif scenario == "right_limit":
            assert [proof.kind.value for proof in assessment.proofs] == ["right_limit"]
        elif scenario == "global":
            assert [proof.kind.value for proof in assessment.proofs] == ["right_global"]
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
def test_explicit_join_requirements_keep_distinct_composed_boundaries(
    tmp_path: Path, both_unique: bool
) -> None:
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import (
        ProjectSingleMatchScope,
        ProjectSingleMatchState,
    )
    from _pietto_plan_joins import _path_source, _path_requests

    original = _completed(tmp_path, _path_source(all_unique=both_unique))
    requests = _path_requests(original)
    assert len(requests) == 2
    assert all(
        request.scope is ProjectSingleMatchScope.DIRECT_BINARY for request in requests
    )
    completed = with_project_single_match_requests(original, requests)
    assert completed.ok, completed.diagnostics
    assessments = completed.single_matches.entries
    assert [
        [proof.kind.value for proof in assessment.proofs] for assessment in assessments
    ] == [
        ["matched_key"],
        ["matched_key"] if both_unique else [],
    ]
    assert [
        assessment.downstream_enforcement_required for assessment in assessments
    ] == [False, not both_unique]
    snapshot = build_project_query_block_ir(completed)
    entry = next(
        entry for entry in snapshot.entries if entry.owner.definition.name == "result"
    )
    assert (
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    first, second = entry.join_prefix.joins
    assert second.input_uses[0].output is first.output.occurrence
    assert first.input_uses[0].output is second.input_uses[1].output
    assert first.input_uses[0] is not second.input_uses[1]
    assert len(snapshot.requirements) == 2
    for request, assessment, retained, boundary in zip(
        requests, assessments, snapshot.requirements, (first, second), strict=True
    ):
        assert assessment.request is request and retained.assessment is assessment
        assert retained.owner_entry is entry and retained.boundaries == (boundary,)
        assert retained.input_pairs == (
            (boundary.input_uses[0], boundary.input_uses[1]),
        )
        assert assessment.condition is not None
        for image, proof in zip(retained.proofs, assessment.proofs, strict=True):
            assert image.source is proof and proof.kind.value == "matched_key"
            condition, match, key, *equalities = proof.roots
            assert type(match) is ProjectJoinConditionKeyMatch
            assert condition is assessment.condition and match.condition is condition
            assert match.binding is request.use.target_binding and match.key is key
            assert tuple(equalities) == match.equalities
    assert assessments[0].state is ProjectSingleMatchState.PROVED
    assert assessments[1].state is (
        ProjectSingleMatchState.PROVED
        if both_unique
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert [d.code for d in completed.diagnostics] == (
        [] if both_unique else ["PIE-S2337"]
    )
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    assert (
        b"direct_binary" in product.canonical_bytes
        and b"matched_key" in product.canonical_bytes
    )
    left, right = assessments[0].input_pairs[0]
    for wrong_pairs in (((right, left),), assessments[1].input_pairs):
        forged = replace(requests[0], input_pairs=wrong_pairs)
        rejected = with_project_single_match_requests(original, (forged,))
        assert (
            rejected.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
        )
        assert [d.code for d in rejected.diagnostics] == ["PIE-S2338"]


def test_grouped_output_left_join_window_qualify_retains_all_stages(
    tmp_path: Path,
) -> None:
    from _pietto_project_join_output import (
        _tail_source,
    )

    source, _ = _tail_source("grouped")
    source += "query result:\n    from lhs\n    let u = upstream\n    left join u on u.total > 0\n    select:\n        id = lhs.id\n        total = u.total\n        rn = row_number() window(order by lhs.id)\n    qualify:\n        rn <= 2\n"
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
        f"    let s = rhs\n    {kind} join s on r.id == s.id\n    select:\n",
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
    from _pietto_ir_sources import set_source as set_source

    source = set_source(right_type="Decimal(10, 2)").replace(
        "id: Int", "id: Decimal(10, 2) | None"
    )
    source += "table joined:\n    from result\n    let r = result\n    inner join r on True\n    select distinct:\n        price = result.id\ntable final:\n    except distinct joined, joined, joined\n"
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
    from _pietto_project_single_match import (
        _request,
    )

    source = _source("True").replace("query result:", "table invalid_owner:")
    source += "table blocked:\n    union all invalid_owner, invalid_owner\nquery valid:\n    from lhs\n    select:\n        id\n"
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


LET_SET = (
    BASE
    + """query result:
    let left_rows:
        from lhs
        select:
            id
            key
    let right_rows:
        from rhs
        select:
            id
            key
    union distinct left_rows, right_rows
"""
)


def test_inlined_def_calls_serialize_as_the_ordinary_expressions_they_are(
    tmp_path: Path,
) -> None:
    completed = _completed(
        tmp_path,
        _source("same(lhs.id, r.id)", kind="left").replace(
            "    select:\n", "    where pos(lhs.id) and pos(lhs.id)\n    select:\n"
        )
        + "def same(a: Int, b: Int) -> Bool | None: return a == b\n"
        + "def pos(x: Int) -> Bool | None: return x > 0 and x < 9\n",
    )
    assert completed.ok, completed.diagnostics
    verification = verify_project_query_block_ir(
        build_project_query_block_ir(completed)
    )
    assert verification.verified, verification.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )
    outcome = pure.evaluate_project_query_block_ir_document(product.document)
    assert outcome.status is ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes


def _let_document(tmp_path: Path):
    completed = _completed(tmp_path, LET_SET)
    assert completed.ok, completed.diagnostics
    verification = verify_project_query_block_ir(
        build_project_query_block_ir(completed)
    )
    assert verification.verified, verification.issues
    return build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verification)
    )


def _value(record, key):
    (value,) = (field.value for field in record.fields if field.key == key)
    return value


def test_a_relation_let_owner_keeps_its_let_coordinate(tmp_path: Path) -> None:
    import json

    product = _let_document(tmp_path)
    records = product.document.records
    owners = {
        _value(record, "ref").ref: _value(record, "declared_name").text
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    }
    lets = [
        (owners[_value(record, "owner").ref], _value(record, "let_position").integer)
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_LET
    ]
    assert lets == [("left_rows", 0), ("right_rows", 1)]
    selected = [
        json.loads(cast(str, _value(record, "capability").text))["selected"]["owner"]
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.TYPE_EQUIVALENCE
    ]
    # Each let field names its let; the declaration `result` has the same names.
    assert {
        (owner["identity"]["declared_name"], owner.get("let_position"))
        for owner in selected
    } == {("left_rows", 0), ("right_rows", 1)}
    outcome = pure.evaluate_project_query_block_ir_document(product.document)
    assert outcome.status is ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes
    assert b"owner_let\towner=" in product.canonical_bytes


def _moved_lets(document, positions):
    """Rewrite the let records as (owner ref position, let position) pairs."""

    kind = pure.ProjectQueryBlockIRRecordKind.OWNER_LET
    first = next(i for i, r in enumerate(document.records) if r.kind is kind)
    rest = tuple(r for r in document.records if r.kind is not kind)
    moved = tuple(
        pure.ProjectQueryBlockIRPureRecord(
            kind=kind,
            fields=(
                pure.ProjectQueryBlockIRPureField(
                    key="owner",
                    value=pure.project_query_block_ir_pure_ref(
                        pure.ProjectQueryBlockIRPortableRef(
                            domain=pure.ProjectQueryBlockIRPortableRefDomain.OWNER_ENTRY,
                            position=owner,
                        )
                    ),
                ),
                pure.ProjectQueryBlockIRPureField(
                    key="let_position",
                    value=pure.project_query_block_ir_pure_integer(position),
                ),
            ),
        )
        for owner, position in positions
    )
    return replace(document, records=rest[:first] + moved + rest[first:])


@pytest.mark.parametrize(
    ("mutation", "status"),
    (
        ("dropped", "INVALID_ENTRY"),
        ("onto_declaration", "INVALID_REF"),
        ("renumbered", "INVALID_REF"),
        ("swapped", "INVALID_REF"),
        ("unordered", "INVALID_REF"),
    ),
)
def test_a_let_coordinate_is_never_dropped_moved_or_swapped(
    tmp_path: Path, mutation: str, status: str
) -> None:
    product = _let_document(tmp_path)
    document = product.document
    owners = {
        _value(record, "declared_name").text: cast(
            pure.ProjectQueryBlockIRPortableRef, _value(record, "ref").ref
        ).position
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    }
    left, right, result = owners["left_rows"], owners["right_rows"], owners["result"]
    assert left < right
    pairs = {
        "dropped": (),
        # The declaration takes the let coordinate its own let lost.
        "onto_declaration": tuple(sorted(((result, 0), (right, 1)))),
        "renumbered": ((left, 2), (right, 1)),
        "swapped": ((left, 1), (right, 0)),
        "unordered": ((right, 1), (left, 0)),
    }[mutation]
    outcome = pure.evaluate_project_query_block_ir_document(
        _moved_lets(document, pairs)
    )
    assert outcome.status is ProjectQueryBlockIRPureStatus[status]
    assert outcome.canonical_bytes is None


def test_predicate_inspection_retains_all_calls_keys_and_located_equalities(
    tmp_path: Path,
) -> None:
    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
    row_key = unique(id)
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
relationship Same(a: Row, b: Row):
    a.id == b.id and b.id > 0
query result:
    from lhs
    inner join rhs on Same(lhs, rhs) and Same(lhs, rhs)
    where Same(lhs, rhs) or not Same(lhs, rhs)
    select:
        matched = Same(lhs, rhs)
        id = lhs.id
""",
    )
    assert completed.ok, completed.diagnostics
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import ProjectSingleMatchRequest

    condition = completed.roots.join_conditions.entries[0]
    request = ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)
    completed = with_project_single_match_requests(completed, (request, request))
    assert all(
        [proof.kind.value for proof in assessment.proofs] == ["matched_key"]
        for assessment in completed.single_matches.entries
    )
    snapshot = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(snapshot)
    assert checked.verified, checked.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(checked)
    )
    observed = product.inspection
    canonical = completed.roots.join_conditions.predicate_expressions
    expected = tuple(call for record in canonical for call in record.calls)
    assert len(expected) == 5
    assert len(observed.predicate_calls) == len(expected)
    assert all(
        actual is original
        for actual, original in zip(observed.predicate_calls, expected, strict=True)
    )
    assert [call.ordinal for call in observed.predicate_calls] == list(range(5))
    assert [proof.conjunct_position for proof in observed.predicate_equalities] == [
        0,
        2,
    ]
    assert [proof.calls for proof in observed.predicate_equalities] == [
        (expected[0],),
        (expected[1],),
    ]
    assert [
        proof.binding.identity.binding_position
        for proof in observed.predicate_key_matches
    ] == [0, 1]
    assert all(
        proof.minimum.value == "zero_allowed"
        for proof in observed.predicate_key_matches
    )
    assert [len(call.mandatory_equalities) for call in expected] == [1, 1, 0, 0, 0]
    records = product.document.records
    position = next(
        i
        for i, record in enumerate(records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.PREDICATE_EXPRESSION
    )
    original = records[position]
    changed = replace(
        original,
        fields=tuple(
            replace(
                field,
                value=pure.project_query_block_ir_pure_refs(
                    tuple(reversed(field.value.refs))
                ),
            )
            if field.key == "calls"
            else field
            for field in original.fields
        ),
    )
    damaged = replace(
        product.document,
        records=(*records[:position], changed, *records[position + 1 :]),
    )
    assert (
        evaluate_project_query_block_ir_document(damaged).status
        is not ProjectQueryBlockIRPureStatus.OK
    )


def test_any_inspection_retains_authored_and_generated_occurrences(
    tmp_path: Path,
) -> None:
    from pietto._project.project_query_block_ir_inspection import (
        _derive_project_query_block_ir_inspection,
        _existence_uses,
        _project_query_block_ir_document,
    )

    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
source regions: Row = postgres.table("regions")
query result:
    from orders
    where any(buyer.id == orders.id for buyer in customers)
    inner join regions on orders.id == regions.id
    where orders.id > 0 and not any(buyer.id == regions.id for buyer in customers)
    select:
        id = orders.id
""",
    )
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    verified = verify_project_query_block_ir(snapshot)
    assert verified.verified, verified.issues
    inspection = _derive_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verified)
    )
    (first,) = _existence_uses(snapshot)
    (last,) = inspection.scalar_existence_uses
    assert inspection.existence_uses == (first,)
    assert first.input_ordinal == 1 and first.preceding_join_count == 0
    assert first.expression is not last.expression
    assert len(inspection.scalar_existence_values) == 1
    document = _project_query_block_ir_document(inspection)
    (record,) = pure._records(
        document, pure.ProjectQueryBlockIRRecordKind.EXISTENCE_USE
    )
    assert pure._integer(record, "input_ordinal") == 1
    assert pure._integer(record, "preceding_join_count") == 0
    assert pure._field(record, "node").tag is pure.ProjectQueryBlockIRPureTag.REF


def test_scalar_any_inspection_keeps_nested_bindings_and_rejects_missing_field(
    tmp_path: Path,
) -> None:
    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
query result:
    from orders
    where orders.id > 0 or any(any(other.id == buyer.id for other in customers) and buyer.id == orders.id for buyer in customers)
    select id = orders.id
""",
    )
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    verified = verify_project_query_block_ir(snapshot)
    assert verified.verified, verified.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verified)
    )
    inspection = product.inspection
    outer, inner = inspection.scalar_existence_values
    assert outer.nested == (inner,)
    assert outer.input.binding.origin is inspection.scalar_existence_uses[0]
    assert inner.input.binding.origin is inspection.scalar_existence_uses[1]
    assert len(outer.references) == len(inner.references) == 2
    target = inner.references[1].target
    assert target is not None
    assert target.binding is outer.input.binding
    assert (
        evaluate_project_query_block_ir_document(product.document).status
        is ProjectQueryBlockIRPureStatus.OK
    )
    records = list(product.document.records)
    position = next(
        i
        for i, record in enumerate(records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_FIELD
    )
    damaged = replace(
        product.document, records=(*records[:position], *records[position + 1 :])
    )
    assert (
        evaluate_project_query_block_ir_document(damaged).status
        is not ProjectQueryBlockIRPureStatus.OK
    )
    uses = [
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_USE
    ]
    outer_use, inner_use = (pure._ref(record, "ref") for record in uses)
    inner_record = next(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_VALUE
        and pure._ref(record, "use") == inner_use
    )
    inner_references = pure._refs(inner_record, "references")
    candidate_position = next(
        i
        for i, record in enumerate(records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_CANDIDATE
        and pure._field(record, "local").tag is pure.ProjectQueryBlockIRPureTag.REF
        and pure._ref(record, "local") == outer_use
        and pure._text(record, "name") == "buyer"
        and pure._ref(record, "reference") in inner_references
    )
    candidate = records[candidate_position]
    changed = replace(
        candidate,
        fields=tuple(
            replace(field, value=pure.project_query_block_ir_pure_ref(inner_use))
            if field.key == "local"
            else field
            for field in candidate.fields
        ),
    )
    graft = replace(
        product.document,
        records=(
            *records[:candidate_position],
            changed,
            *records[candidate_position + 1 :],
        ),
    )
    assert (
        evaluate_project_query_block_ir_document(graft).status
        is not ProjectQueryBlockIRPureStatus.OK
    )


@pytest.mark.parametrize("captured", ("orders", "regions"))
def test_scalar_any_outer_capture_cannot_be_retargeted(
    tmp_path: Path, captured: str
) -> None:
    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
source regions: Row = postgres.table("regions")
query result:
    from orders
    inner join regions on orders.id == regions.id
    where any(buyer.id == orders.id and buyer.id == regions.id for buyer in customers)
    select id = orders.id
""",
    )
    assert completed.ok, completed.diagnostics
    verified = verify_project_query_block_ir(build_project_query_block_ir(completed))
    assert verified.verified, verified.issues
    document = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verified)
    ).document
    assert (
        evaluate_project_query_block_ir_document(document).status
        is ProjectQueryBlockIRPureStatus.OK
    )
    owners = {
        pure._text(record, "declared_name"): pure._ref(record, "ref")
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    }
    records = document.records
    (position,) = (
        i
        for i, record in enumerate(records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_CANDIDATE
        and pure._text(record, "name") == captured
    )
    candidate = records[position]
    assert pure._ref(candidate, "target") == owners[captured]
    changed = replace(
        candidate,
        fields=tuple(
            replace(
                field, value=pure.project_query_block_ir_pure_ref(owners["customers"])
            )
            if field.key == "target"
            else field
            for field in candidate.fields
        ),
    )
    damaged = replace(
        document, records=(*records[:position], changed, *records[position + 1 :])
    )
    assert evaluate_project_query_block_ir_document(
        damaged
    ) == pure.ProjectQueryBlockIRPureOutcome(
        status=ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT,
        record_position=0,
        field_position=0,
    )


@pytest.mark.parametrize("captured", ("orders", "regions", "buyer"))
def test_scalar_any_capture_is_bound_to_its_verified_input_fields(
    tmp_path: Path, captured: str
) -> None:
    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
    code: Text | None
    rank: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
source regions: Row = postgres.table("regions")
query result:
    from orders
    inner join regions on orders.id == regions.id
    where any(buyer.id == orders.id and buyer.id == regions.id for buyer in customers)
    select id = orders.id
""",
    )
    assert completed.ok, completed.diagnostics
    verified = verify_project_query_block_ir(build_project_query_block_ir(completed))
    assert verified.verified, verified.issues
    document = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(verified)
    ).document
    records = document.records
    owners = {
        pure._text(record, "declared_name"): pure._ref(record, "ref")
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    }
    position = next(
        i
        for i, record in enumerate(records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.SCALAR_ANY_CANDIDATE
        and pure._text(record, "name") == captured
    )
    candidate = records[position]
    assert pure._field(candidate, "input_names").texts == ("id", "code", "rank")
    assert pure._enumeration(candidate, "nullability") == "non_null"
    customers = pure.project_query_block_ir_pure_ref(owners["customers"])
    damages: dict[str, tuple[tuple[int, str, ProjectQueryBlockIRPureValue], ...]] = {
        "nullability": (
            (
                position,
                "nullability",
                pure.project_query_block_ir_pure_enumeration("nullable"),
            ),
        ),
        "extra name": (
            (
                position,
                "input_names",
                pure.project_query_block_ir_pure_texts(("id", "code", "rank", "x")),
            ),
        ),
        "rotated names": (
            (
                position,
                "input_names",
                pure.project_query_block_ir_pure_texts(("id", "rank", "code")),
            ),
        ),
    }
    if captured != "buyer":
        assert pure._ref(candidate, "target") == owners[captured]
        (dependency,) = (
            i
            for i, record in enumerate(records)
            if record.kind is pure.ProjectQueryBlockIRRecordKind.DEPENDENCY
            and pure._ref(record, "consumer") == owners["result"]
            and pure._integer(record, "ordinal") == pure._integer(candidate, "position")
        )
        assert pure._ref(records[dependency], "target") == owners[captured]
        damages["dependency"] = ((dependency, "target", customers),)
        damages["target and dependency"] = (
            (position, "target", customers),
            (dependency, "target", customers),
        )
    for name, changes in damages.items():
        damaged = list(records)
        for at, key, value in changes:
            damaged[at] = replace(
                damaged[at],
                fields=tuple(
                    replace(field, value=value) if field.key == key else field
                    for field in damaged[at].fields
                ),
            )
        assert evaluate_project_query_block_ir_document(
            replace(document, records=tuple(damaged))
        ) == pure.ProjectQueryBlockIRPureOutcome(
            status=ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT,
            record_position=0,
            field_position=0,
        ), name


def test_tail_scalar_any_retains_nested_let_capture(tmp_path: Path) -> None:
    completed = _completed(
        tmp_path,
        """shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
query result:
    from orders
    let floor = orders.id
    where any(any(other.id > floor and other.id == buyer.id for other in customers) for buyer in customers)
    select id = orders.id
""",
    )
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(snapshot)
    assert checked.verified, checked.issues
    product = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(checked)
    )
    assert not product.inspection.existence_uses
    assert len(product.inspection.scalar_existence_uses) == 2
    outer, inner = product.inspection.scalar_existence_values
    assert outer.nested == (inner,)
    assert any(
        getattr(reference.target, "binding", None) is not None
        for reference in inner.captures
    )
    assert (
        evaluate_project_query_block_ir_document(product.document).status
        is ProjectQueryBlockIRPureStatus.OK
    )
