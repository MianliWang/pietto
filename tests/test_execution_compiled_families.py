"""Complete original named families are the source-side differential reference."""

import pytest

import _pietto_sql_emission as emission
from _pietto_execution_binding import proof_artifact
from _pietto_execution_compiled import retained_unmapped_source
from _pietto_execution_refinement import capabilities
from _pietto_execution_rows_cases import CASES, build
from _pietto_execution_guard_cases import manifest, case_preparation
from pietto._project.project_compiled_build import CompiledBuild, build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_execution_template import BindingError
from pietto._project.project_result_output import prepare_output
from pietto._project.project_sql_emission import serialize_project_sql_emission


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", CASES)
def test_original_named_family_closure(tmp_path, target, case, variant):
    original = build(tmp_path / "source-build", target, case, variant)
    if original.status == "BLOCKED":
        assert original.artifact is None and original.blockers
        with pytest.raises(BindingError, match="^BINDING_ARTIFACT$"):
            build_compiled(original.artifact)
        return
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("operator", ("is None", "is not None"))
def test_loaded_null_test_rehydrates_non_null_bool(tmp_path, target, operator):
    item = emission.fixture(target, "T_row_direct", "query_bind")
    source = (
        item["source"]
        if operator == "is None"
        else item["source"].replace(
            "missing = flag is None", "missing = flag " + operator
        )
    )
    checked, original = emission.build_case(
        tmp_path / operator.replace(" ", "-"),
        source,
        item["contract"],
        item["policy"],
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    candidate = emit_compiled(
        loaded, tuple(value.value for value in original.artifact.fixed_values)
    )
    assert candidate.rendered.sql == original.artifact.rendered.sql
    assert (" IS NOT NULL" if operator == "is not None" else " IS NULL") in (
        candidate.rendered.sql.decode()
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_abs_replays_from_compiled_input(tmp_path, target):
    """`abs` of an Int, a Float and a Decimal keeps its type and realization."""
    item = emission.fixture(target, "T_row_direct", "table_preserve")
    source = item["source"].split("table result:", 1)[0] + (
        "table result:\n    from rows\n    select:\n"
        "        widened = abs(id + 0)\n"
        "        ratio_size = abs(ratio)\n"
        "        money_size = abs(money)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    # The R2 refinement page verifier reads no scalar call yet (fails closed).
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("variant", ("let_key", "bind"))
def test_computed_let_determinant_replays_from_compiled_input(
    tmp_path, target, variant
):
    """A CASE determinant and MAX over a CASE LET value replay their own ports."""
    item = emission.fixture(target, "Y_aggregate_computed", variant)
    checked, original = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (6 if variant == "bind" else 0)
    # The R2 refinement page verifier does not read CASE yet (fails closed).
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
def test_computed_comparison_determinant_refines_from_compiled_input(
    tmp_path, target, bound
):
    """A comparison determinant and MAX over a LET value also keep the compiled
    refinement differential; the public R2 entry still refuses this shape."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let big = value > 5\n"
        "    let level = 3\n    group by:\n        big\n    select:\n        big\n"
        "        total = count()\n        top = max(level)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "value",
    (
        "1 if key > 1 else 0",
        "1 <= key <= 3",
        "key in (1, 2)",
        "Float(key)",
    ),
)
def test_row_let_operation_keeps_its_requirement_rules_on_replay(
    tmp_path, target, value
):
    """The compiled input attributes each retained demand as the source did."""
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        f"query result:\n    from agg\n    let w = {value}\n"
        "    select:\n        w\n        rid\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    # The independent public consumer derives the source rules on its own.
    emission.decode_public(serialize_project_sql_emission(original))
    # The R2 refinement page verifier does not read these operations yet.
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (
        ("L_relation_exists", "kept"),
        ("L_relation_exists", "correlated"),
        ("L_relation_scalar", "kept"),
        ("L_relation_membership", "correlated"),
    ),
)
def test_block_read_keeps_its_requirement_rules_on_replay(
    tmp_path, target, case, variant
):
    """An `exists`, `scalar` or `in` read keeps its R11 demand in the compiled
    input, as the source attributes it (an `any` read: the named families)."""
    item = emission.fixture(target, case, variant)
    checked, original = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert "R11" in {r.rule for r in original.artifact.original_requirements}
    emission.decode_public(serialize_project_sql_emission(original))
    # R2 refines no `exists`, `scalar` or `in` read yet (fails closed).
    _compare(original.artifact, refinement=False)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
@pytest.mark.parametrize(
    "tail", ("", "    having:\n        b\n    order by:\n        b desc\n")
)
def test_joined_computed_determinant_replays_from_compiled_input(
    tmp_path, target, bound, tail
):
    """S05j: compiled replay re-derives the two-sided determinant's risk law,
    MIN/MAX over the joined LET value and filtering/ordering by its output."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = (
        emission.AGGREGATE_HEADER.format(target=target)
        + emission.AGGREGATE_COMPUTED_JOIN
        + tail
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("bound", (False, True))
def test_joined_field_free_let_extrema_replay_from_compiled_input(
    tmp_path, target, bound
):
    """A12: MIN/MAX over a joined LET value that reads no field replay with no
    field dependency and the source's own linkage."""
    item = emission.fixture(
        target, "Y_aggregate_satisfying", "bind" if bound else "retained"
    )
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.key == r.key\n    let level = 3 * 2\n"
        "    group by:\n        agg.rid\n        r.rid\n    select:\n"
        "        rid = agg.rid\n        low = min(level)\n        top = max(level)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    assert len(original.artifact.parameter_uses) == (2 if bound else 0)
    _compare(original.artifact)


_RIGHT_R = (
    "relationship link(many: Agg, one: Agg):\n    many.key == one.rid\n"
    "query result:\n    from agg\n    let r = agg\n"
    "    right join r on link(agg, r)\n"
)


def _right_case(tmp_path, target, body):
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + _RIGHT_R + body
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    plan = emit_compiled(
        built.root, tuple(v.value for v in original.artifact.fixed_values)
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    return original.artifact, built, evidence


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "body",
    (
        "    select:\n        n = count(agg.rid)\n",
        "    let p = agg\n    inner join p on link(p, agg)\n"
        "    select:\n        n = count(p.rid)\n",
    ),
    ids=("left_argument", "matched_input"),
)
def test_right_join_match_replays_only_for_aggregates_skipping_unmatched_rows(
    tmp_path, target, body
):
    """A RIGHT JOIN's at-most-one match gives no left-to-right grain dependency
    in the replay either, and an aggregate that never reads a right row that
    matches no left row (its argument is NULL there, or it reads an input
    matched from the left side) gets it back the same way: the replayed fan-out
    evidence equals the original and repeats no row."""

    artifact, built, evidence = _right_case(tmp_path, target, body)
    _compare(artifact, built=built)
    (right,) = (j for j in evidence.region.joins if j.record.get("kind") == "right")
    introduced = evidence.region.uses[right.record.get("inputs")[1]].ref
    assert not any(
        factor.introduction_use is introduced
        for dependency in right.properties.relational.grain.dependencies
        for factor in (*dependency.determinants, *dependency.dependents)
    )
    (linkage,) = evidence.grain_linkages
    assert linkage.closure.factors == evidence.region.final_properties.grain.active
    assert not linkage.multiplicity_exposures


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("nullable_key", (False, True))
def test_correlated_match_and_non_null_group_key_replay(tmp_path, target, nullable_key):
    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    header = emission.AGGREGATE_HEADER.format(target=target)
    body = _RIGHT_R
    if nullable_key:
        header = header.replace(
            "    agg_row = unique(rid)",
            "    agg_match = unique(key)\n    agg_row = unique(rid)",
        )
        body = body.removesuffix("\n") + " and r.flag\n"
    match = "link(p, r) and p.rid > 0"
    body += (
        "    let p = agg\n"
        + (
            f"    inner join p on {match}\n"
            if nullable_key
            else f"    where any({match} for p in p)\n"
        )
        + "    let x = agg\n    cross join x\n"
        "    group by agg.rid"
        + (", p.key" if nullable_key else "")
        + "\n    select:\n        n = count(x.rid)\n"
    )
    checked, original = emission.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    built = build_compiled(original.artifact)
    _compare(original.artifact, built=built)
    plan = emit_compiled(
        built.root, tuple(v.value for v in original.artifact.fixed_values)
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    if nullable_key:
        from dataclasses import replace
        from pietto._project.project_compiled_schema import CompiledError
        from pietto._project.project_joined_aggregation import (
            verify_compiled_aggregate_evidence,
        )
        from pietto._project.project_row_keys import ProjectRowUniquenessStrength

        assert all(
            key.strength is ProjectRowUniquenessStrength.STRICT
            for protection in evidence.group_protections
            for key in protection.strict_keys
        )
        (protection,) = (
            protection
            for protection in evidence.group_protections
            if any(
                member.field_position == 0
                for value_class in protection.seed.classes
                for member in value_class.members
            )
        )
        assert not protection.protected_factors
        (nullable,) = (
            key
            for key in protection.input_properties.keys
            if key.strength is ProjectRowUniquenessStrength.LAX
        )
        forged = replace(protection, strict_keys=(*protection.strict_keys, nullable))
        supplied = (
            replace(
                evidence,
                group_protections=tuple(
                    forged if p is protection else p for p in evidence.group_protections
                ),
            ),
        )
        with pytest.raises(CompiledError, match="^COMPILED_GROUP_PROTECTION_KEYS$"):
            verify_compiled_aggregate_evidence(plan.ir, supplied)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("retained", (False, True), ids=("selected", "retained"))
@pytest.mark.parametrize(
    "variant",
    ("reordered", "duplicates", "wrong_pair", "missing_duplicate", "extra_on"),
)
def test_reordered_composite_reverse_match_replays_with_authored_order(
    tmp_path, monkeypatch, target, retained, variant
):
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
        compiled_orphan_free_dependencies,
        orphan_free_dependencies,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    forward = "many.key == one.rid and many.value == one.rid"
    reverse = "one.rid == many.value and one.rid == many.key"
    if variant in {"duplicates", "missing_duplicate"}:
        forward += " and many.key == one.rid"
    if variant == "duplicates":
        reverse += " and one.rid == many.key"
    elif variant == "wrong_pair":
        reverse = "one.rid == many.value and one.rid == many.rid"
    proved = variant in {"reordered", "duplicates"}
    extra_on = " and r.flag" if variant == "extra_on" else ""
    # Independent grouping keeps the negative controls valid without this proof.
    group = "agg.rid" if proved else "agg.rid, r.rid"
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        f"relationship forward_match(many: Agg, one: Agg):\n    {forward}\n"
        f"relationship reverse_match(one: Agg, many: Agg):\n    {reverse}\n"
        "query result:\n    from agg\n    let r = agg\n"
        f"    right join r on forward_match(agg, r){extra_on}\n"
        "    let p = agg\n    where any(reverse_match(r, p) for p in p)\n"
        f"    let x = agg\n    cross join x\n    group by {group}\n"
        "    select:\n        n = count(x.rid)\n"
    )
    logical = []
    if retained:
        # The request fixture needs a matching boundary; INNER TRUE keeps the product.
        source = (
            source.replace("query result:", "query unused:").replace(
                "cross join x", "inner join x on True"
            )
            + "query result:\n    from agg\n    select:\n        rid\n"
        )

        def witness(*args, **kwargs):
            return {**item, "source": source}

        monkeypatch.setattr(emission, "join_witness", witness)
        original = proof_artifact(tmp_path, retained=True)
        checker = verification.verify_logical_export

        def capture(description, checked, correspondence):
            checker(description, checked, correspondence)
            logical.append(checked.plan)

        monkeypatch.setattr(verification, "verify_logical_export", capture)
    else:
        checked, original = emission.build_case(
            tmp_path, source, item["contract"], item["policy"]
        )
        assert checked.verified
    assert original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    if retained:
        loaded = load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
        replay = emit_compiled(loaded, tuple(v.value for v in artifact.fixed_values))
        assert replay.rendered.sql == artifact.rendered.sql
        assert len(replay.parameter_uses) == len(artifact.parameter_uses)
        (reference,) = logical
        assert not replay.request.plan.single_matches
        assert replay.request.plan.all_single_matches
        _compare_aggregate_evidence(reference, replay.request.plan)
    else:
        replay = _compare(artifact, built=built)
        reference = artifact.request.plan
    (source_aggregate,) = (
        a.authority.source
        for a in reference.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    (evidence,) = replay.request.plan.aggregate_evidence
    if retained:
        (source_request,) = (
            a
            for a in artifact.request.verification.completed.single_matches.entries
            if a.request.use.identity.join_position == 2
        )
        (compiled_request,) = (
            o.assessment
            for o in replay.request.plan.all_single_matches
            if o.request.use.get("boundaries")
            == (evidence.region.joins[-1].record.address,)
        )
        for assessment in (source_request, compiled_request):
            assert assessment.state.value == "legal_unproved"
            assert not assessment.proofs
            assert assessment.downstream_enforcement_required
    (source_occurrence,) = source_aggregate.aggregates
    (aggregate_address,) = evidence.stage.record.get("values")
    arguments = replay.request.plan.ir.completed.root.records[aggregate_address].get(
        "arguments"
    )
    old_dependencies = orphan_free_dependencies(source_occurrence)
    new_dependencies = compiled_orphan_free_dependencies(
        replay.request.plan.ir, evidence.region, evidence.stage, arguments
    )

    def signature(dependencies, grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return tuple(
            (
                tuple(positions[f] for f in dependency.determinants),
                tuple(positions[f] for f in dependency.dependents),
            )
            for dependency in dependencies
        )

    source_region = source_aggregate.input_filter.joined_semantics.multifact_region
    expected = (((0,), (1,)),) if proved else ()
    assert (
        signature(old_dependencies, source_region.final_properties.relational.grain)
        == signature(new_dependencies, evidence.region.final_properties.grain)
        == expected
    )
    (linkage,) = evidence.grain_linkages
    assert linkage.closure.factors == evidence.region.final_properties.grain.active
    assert not linkage.multiplicity_exposures


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "where",
    (
        "x.rid is None",
        "r.rid > 5 and r.rid < 3",
        "agg.rid is not None or x.rid is None",
        "r.rid == 3",
    ),
    ids=("never_none", "contradiction", "vacuous_or", "key_held"),
)
def test_unmatched_row_value_proofs_replay_with_the_compiled_records(
    tmp_path, target, where
):
    """D-11: the compiled records give back the left-to-right dependency of a
    RIGHT JOIN whose unmatched rows the aggregate reads through values only
    (a never-None field tested `is None`, contradictory bounds, a vacuous
    `or`) or of one right row only (a key held to one value), as the written
    query does, so the replay finds no repeated rows either."""
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
        compiled_orphan_free_dependencies,
        orphan_free_dependencies,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "relationship forward_match(many: Agg, one: Agg):\n"
        "    many.key == one.rid\n"
        "query result:\n    from agg\n    let r = agg\n"
        "    right join r on forward_match(agg, r)\n    let x = agg\n"
        f"    cross join x\n    where {where}\n    group by agg.rid\n"
        "    select:\n        n = count(x.rid)\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified
    assert original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    replay = _compare(artifact)
    reference = artifact.request.plan
    (source_aggregate,) = (
        a.authority.source
        for a in reference.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    (evidence,) = replay.request.plan.aggregate_evidence
    (source_occurrence,) = source_aggregate.aggregates
    (aggregate_address,) = evidence.stage.record.get("values")
    arguments = replay.request.plan.ir.completed.root.records[aggregate_address].get(
        "arguments"
    )

    def signature(dependencies, grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return tuple(
            (
                tuple(positions[f] for f in dependency.determinants),
                tuple(positions[f] for f in dependency.dependents),
            )
            for dependency in dependencies
        )

    source_region = source_aggregate.input_filter.joined_semantics.multifact_region
    assert (
        signature(
            orphan_free_dependencies(source_occurrence),
            source_region.final_properties.relational.grain,
        )
        == signature(
            compiled_orphan_free_dependencies(
                replay.request.plan.ir, evidence.region, evidence.stage, arguments
            ),
            evidence.region.final_properties.grain,
        )
        == (((0,), (1,)),)
    )
    (linkage,) = evidence.grain_linkages
    assert not linkage.multiplicity_exposures


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_joined_single_read_computed_key_replays_as_computed(tmp_path, target):
    """`r.rid + 0` reads one field through an operation: replay keeps it a
    computed key recorded on the right side, never a direct key seeding that
    side's class, and forged records are refused."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_joined_aggregation import (
        verify_compiled_aggregate_evidence,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    source = emission.AGGREGATE_HEADER.format(target=target) + (
        "query result:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.key == r.key\n    let k = r.rid + 0\n"
        "    group by:\n        k\n        agg.rid\n    select:\n        k\n"
        "        rid = agg.rid\n        total = count()\n"
    )
    checked, original = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    assert original.artifact is not None
    _compare(original.artifact)
    plan = emit_compiled(
        build_compiled(original.artifact).root,
        tuple(v.value for v in original.artifact.fixed_values),
    ).request.plan
    (evidence,) = plan.aggregate_evidence
    right, left = evidence.group_protections
    assert right.group_keys == () and len(right.computed_keys) == 1
    assert len(left.group_keys) == 1 and left.computed_keys == ()
    assert not right.protected_factors and left.protected_factors
    for forged in (
        (replace(right, group_keys=right.computed_keys, computed_keys=()), left),
        (
            replace(right, computed_keys=()),
            replace(left, computed_keys=right.computed_keys),
        ),
    ):
        with pytest.raises(CompiledError, match="^COMPILED_GROUP_PROTECTION_ROOT$"):
            verify_compiled_aggregate_evidence(
                plan.ir, (replace(evidence, group_protections=forged),)
            )
    (linkage,) = evidence.grain_linkages
    assert linkage.computed_key_factors
    assert linkage.computed_key_factors != linkage.group_protection_factors
    for factors in ((), linkage.group_protection_factors):
        with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_LINKAGE_ROOT$"):
            verify_compiled_aggregate_evidence(
                plan.ir,
                (
                    replace(
                        evidence,
                        grain_linkages=(
                            replace(linkage, computed_key_factors=factors),
                        ),
                    ),
                ),
            )


def _compare(artifact, *, refinement=True, built: CompiledBuild | None = None):
    assert artifact is not None
    reference = prepare_output(artifact)
    if built is None:
        built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    values = tuple(v.value for v in artifact.fixed_values)
    candidate = emit_compiled(loaded, values)
    observed = prepare_output(candidate)
    assert candidate.rendered.sql == artifact.rendered.sql
    assert tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.nullable,
            c.realization.domain,
        )
        for c in observed.columns
    ) == tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.nullable,
            c.realization.domain,
        )
        for c in reference.columns
    )
    assert tuple(
        (
            f.ordinal,
            f.label,
            f.shape.canonical.name,
            f.shape.canonical.kind,
            f.nullability.value,
            None if f.meaning is None else f.meaning.law,
        )
        for f in observed.contract.shape.fields
    ) == tuple(
        (
            f.ordinal,
            f.label,
            f.shape.canonical.name,
            f.shape.canonical.kind,
            f.nullability.value,
            None if f.meaning is None else f.meaning.law,
        )
        for f in reference.contract.shape.fields
    )
    from pietto._project.project_query_block_ir_verification import (
        _class_signatures,
        _actual_key_signatures,
        _actual_fd_signatures,
    )

    original_properties = next(
        d.entry.active_properties.relational
        for d in artifact.request.plan.bindings.definitions
        if d.entry.owner is artifact.request.verification.selected_owner
    )
    loaded_properties = candidate.request.plan.ir.selected.properties.relational
    for signature in (_class_signatures, _actual_key_signatures, _actual_fd_signatures):
        assert signature(loaded_properties) == signature(original_properties)

    def grain_signature(grain):
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        return (
            grain.state.value,
            tuple(f.identity.kind.value for f in grain.factors),
            tuple(positions[f] for f in grain.active),
            tuple(
                (
                    tuple(positions[f] for f in d.determinants),
                    tuple(positions[f] for f in d.dependents),
                )
                for d in grain.dependencies
            ),
        )

    assert grain_signature(loaded_properties.grain) == grain_signature(
        original_properties.grain
    )
    _compare_requirements(artifact, candidate)
    _compare_aggregate_evidence(artifact.request.plan, candidate.request.plan)
    if refinement:
        _compare_refinement(artifact)
    assert len(candidate.parameter_uses) == len(artifact.parameter_uses)
    assert all(
        new is not old
        for new, old in zip(
            candidate.request.sources, artifact.request.sources, strict=True
        )
    )
    return candidate


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_original_maximum_static_limit_round_trip(tmp_path, target):
    import _pietto_sql_emission as emission
    from pietto.semantic.relation_limits import MAX_RELATION_LIMIT

    fixture = emission.fixture(target, "O_result_limit", "zero")
    source = fixture["source"]
    assert "limit 0" in source
    source = source.replace("limit 0", "limit " + str(MAX_RELATION_LIMIT))
    checked, outcome = emission.build_case(
        tmp_path, source, fixture["contract"], "preserve_literals"
    )
    assert checked.verified and outcome.status == "VERIFIED"
    _compare(outcome.artifact)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "precision,state", [(p, s) for p in (39, 65) for s in ("values", "empty", "null")]
)
def test_original_seven_scalar_templates(tmp_path, target, precision, state):
    from _pietto_execution_rows_cases import seven_artifact

    original = seven_artifact(
        tmp_path / "seven-build", target, precision=precision, state=state
    )
    _compare(original)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,left_key,right_key,kind,match,expected",
    (
        ("forward", False, True, "inner", "call", (((0,), (1,)),)),
        ("reverse", True, False, "inner", "call", (((1,), (0,)),)),
        ("both", True, True, "inner", "call", (((0,), (1,)), ((1,), (0,)))),
        ("swapped", True, True, "inner", "swapped", (((0,), (1,)), ((1,), (0,)))),
        ("left", True, True, "left", "call", (((0,), (1,)),)),
        ("right", True, True, "right", "call", (((1,), (0,)),)),
        # Hand-written ON equalities prove what the call proves.
        (
            "handwritten",
            True,
            True,
            "inner",
            "handwritten",
            (((0,), (1,)), ((1,), (0,))),
        ),
        ("nonmandatory", True, True, "inner", "or", ()),
        ("same_side", True, True, "inner", "same_side", ()),
        (
            "chain",
            True,
            True,
            "inner",
            "call",
            (((0,), (1,)), ((1,), (0,)), ((0, 1), (2,)), ((2,), (0, 1))),
        ),
    ),
    ids=(
        "forward",
        "reverse",
        "both",
        "swapped",
        "left",
        "right",
        "handwritten",
        "nonmandatory",
        "same_side",
        "chain",
    ),
)
def test_compiled_predicate_keys_preserve_complete_grain_dependencies(
    tmp_path, target, case, left_key, right_key, kind, match, expected
):
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_grain import ProjectGrainDependencyFact
    from pietto._project.project_query_block_ir import build_compiled_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_compiled_join_grain,
    )

    key = "    row_id = unique(id)\n"
    equality = (
        "r.id == l.id and r.key == l.key"
        if match == "swapped"
        else "l.id == r.id and l.key == r.key"
    )
    predicate = (
        "lhs.id == r.id and lhs.key == r.key"
        if match == "handwritten"
        else "Link(lhs, r) or True"
        if match == "or"
        else "LeftOnly(lhs) and r.id > 0"
        if match == "same_side"
        else "Link(lhs, r)"
    )
    later = (
        "    let again = rhs\n    inner join again on Link(lhs, again)\n"
        if case == "chain"
        else ""
    )
    source = f"""shape LeftRow:
    id: Int
    key: Int | None
{key if left_key else ""}shape RightRow:
    id: Int
    key: Int | None
{key if right_key else ""}source lhs: LeftRow = {target}.table("lhs")
source rhs: RightRow = {target}.table("rhs")
relationship Link(l: LeftRow, r: RightRow):
    {equality}
relationship LeftOnly(l: LeftRow):
    l.id == l.id
query result:
    from lhs
    let r = rhs
    {kind} join r on {predicate}
{later}    select:
        left_id = lhs.id
        right_key = r.key
"""
    fixture = emission.join_witness(target, "")
    verified, outcome = emission.build_case(
        tmp_path / case, source, fixture["contract"]
    )
    assert verified.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, ())
    assert replay.rendered.sql == outcome.artifact.rendered.sql
    ir = replay.request.plan.ir
    joins = tuple(operator for operator in ir.operators if operator.kind == "join")
    operator = joins[-1]
    properties = operator.properties.relational
    grain = properties.grain
    positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
    observed = tuple(
        (
            tuple(positions[f] for f in d.determinants),
            tuple(positions[f] for f in d.dependents),
        )
        for d in grain.dependencies
    )
    assert observed == expected
    assert operator.record.get("equalities") == ()
    parents = {item.record.address: item for item in ir.operators}
    verify_compiled_join_grain(ir, operator, parents)
    extra = ProjectGrainDependencyFact(
        determinants=(grain.active[0],), dependents=(grain.active[-1],)
    )
    damages = [(*grain.dependencies, extra)]
    if grain.dependencies:
        first = grain.dependencies[0]
        damages.extend(
            (
                grain.dependencies[1:],
                (*grain.dependencies, first),
                (
                    replace(
                        first,
                        determinants=first.dependents,
                        dependents=first.determinants,
                    ),
                    *grain.dependencies[1:],
                ),
            )
        )
        foreign = build_compiled_query_block_ir(ir.completed)
        foreign_operator = next(
            item
            for item in foreign.operators
            if item.record.address == operator.record.address
        )
        foreign_first = foreign_operator.properties.relational.grain.dependencies[0]
        damages.append((foreign_first, *grain.dependencies[1:]))
    if len(grain.dependencies) > 1:
        damages.append(tuple(reversed(grain.dependencies)))
    for dependencies in damages:
        forged = replace(
            operator,
            properties=replace(
                operator.properties,
                relational=replace(
                    properties, grain=replace(grain, dependencies=dependencies)
                ),
            ),
        )
        with pytest.raises(
            CompiledError, match="^COMPILED_PROPERTY_JOIN_DEPENDENCIES$"
        ):
            verify_compiled_join_grain(ir, forged, parents)


@pytest.mark.parametrize(
    "target,case,kind,predicate,local_factors",
    [
        pytest.param(target, case, kind, predicate, factors, id=f"{target}-{case}")
        for target in ("postgres", "mysql")
        for case, kind, predicate, factors in (
            ("inner", "inner", "Many(dimension, signal)", (1,)),
            ("right", "right", "Many(dimension, signal)", (1,)),
            ("left", "left", "Many(dimension, signal)", ()),
            ("full", "full", "Many(dimension, signal)", ()),
            ("or", "inner", "Many(dimension, signal) or True", ()),
            ("not", "inner", "not Many(dimension, signal)", ()),
            ("missing_composite", "inner", "Partial(dimension, signal)", ()),
            (
                "multiple_bindings",
                "inner",
                "Many(dimension, signal) and Many(agg, signal)",
                (0, 1),
            ),
        )
        if target == "postgres" or kind != "full"
    ],
)
def test_compiled_local_key_grain_does_not_bound_accumulated_left(
    tmp_path, target, case, kind, predicate, local_factors
):
    """An event-expanded left row keeps each independently proved local edge."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
    from pietto._project.project_grain import (
        CompiledGrainFactorIdentity,
        ProjectGrainDependencyFact,
        ProjectJoinGrainFactorIdentity,
    )
    from pietto._project.project_query_block_ir_verification import (
        verify_compiled_join_grain,
    )

    item = emission.fixture(target, "Y_aggregate_satisfying", "retained")
    header = emission.AGGREGATE_HEADER.format(target=target)
    composite = case == "missing_composite"
    suffix = " and a.label == b.label" if composite else ""
    if composite:
        header = header.replace("unique(rid)", "unique(rid, label)")
    source = header + (
        f"relationship Same(a: Agg, b: Agg):\n    a.rid == b.rid{suffix}\n"
        f"relationship Many(a: Agg, b: Agg):\n    a.rid == b.key{suffix}\n"
        "relationship Partial(a: Agg, b: Agg):\n    a.rid == b.key\n"
        "query result:\n    from agg\n    let dimension = agg\n"
        "    inner join dimension on Same(agg, dimension)\n"
        "    let event = agg\n    inner join event on Many(agg, event)\n"
        f"    let signal = agg\n    {kind} join signal on {predicate}\n"
        "    select:\n        account_id = agg.rid\n"
        "        dimension_id = dimension.rid\n        event_id = event.rid\n"
        "        signal_id = signal.rid\n"
    )
    checked, outcome = emission.build_case(
        tmp_path, source, item["contract"], item["policy"]
    )
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    replay = _compare(artifact, refinement=False)
    (region,) = (
        artifact.request.verification.completed.effective_outputs.current_regions
    )
    original = region.joins[-1]
    assert isinstance(original, ProjectCurrentBinaryJoin)
    ir = replay.request.plan.ir
    joins = tuple(item for item in ir.operators if item.kind == "join")
    operator = joins[-1]
    properties = operator.properties.relational
    grain = properties.grain
    parents = {item.record.address: item for item in ir.operators}
    left_use = ir.completed.root.records[operator.record.get("inputs")[0]]
    left = parents[left_use.get("producer")].properties.relational
    expected = (
        ((0,), (1,)),
        ((1,), (0,)),
        ((2,), (0, 1)),
        *(((3,), (factor,)) for factor in local_factors),
    )
    columns = tuple(name for name, _ in emission.AGGREGATE_COLUMNS)
    key = tuple(
        i
        for i, name in enumerate(columns)
        if name == "rid" or composite and name == "label"
    )
    event_key = tuple(2 * len(columns) + i for i in key)
    signal_key = tuple(3 * len(columns) + i for i in key)
    for incoming, current, node, introductions in (
        (
            original.left_input,
            original.properties.relational,
            original.node.ref,
            (
                region.joins[0].input_uses[0].ref,
                *(join.input_uses[1].ref for join in region.joins),
            ),
        ),
        (
            left,
            properties,
            operator.ref,
            (
                ir.references[joins[0].record.get("inputs")[0]],
                *(ir.references[j.record.get("inputs")[1]] for j in joins),
            ),
        ),
    ):
        # The only accumulated key belongs to event, not the matched dimension.
        for value, positions in (
            (incoming, event_key),
            (current, (*event_key, *signal_key)),
        ):
            assert tuple(
                tuple(m.field_position for c in k.determinants for m in c.members)
                for k in value.keys
            ) == (positions,)
        current_grain = current.grain
        positions = {f.identity: i for i, f in enumerate(current_grain.factors)}
        assert (
            tuple(
                (
                    tuple(positions[f] for f in d.determinants),
                    tuple(positions[f] for f in d.dependents),
                )
                for d in current_grain.dependencies
            )
            == expected
        )
        identities = tuple(
            f.identity
            for f in current_grain.factors
            if isinstance(
                f.identity,
                (ProjectJoinGrainFactorIdentity, CompiledGrainFactorIdentity),
            )
        )
        assert len(identities) == len(current_grain.factors)
        assert len({f.base for f in identities}) == 1
        assert len({f.introduction_use for f in identities}) == 4
        assert tuple(positions[f] for f in current_grain.active) == (0, 1, 2, 3)
        for factor, use in zip(current_grain.active, introductions, strict=True):
            assert isinstance(
                factor, (ProjectJoinGrainFactorIdentity, CompiledGrainFactorIdentity)
            )
            assert factor.introduction_use is use
            assert factor.kind.value == "source_domain"
        left_nulling = (node,) if kind in {"right", "full"} else ()
        right_nulling = (node,) if kind in {"left", "full"} else ()
        assert tuple(f.nulling_joins for f in identities) == (
            left_nulling,
            left_nulling,
            left_nulling,
            right_nulling,
        )
    verify_compiled_join_grain(ir, operator, parents)
    # A local match cannot determine the unmatched event or the whole left row.
    damages = []
    for dependents in ((grain.active[2],), grain.active[:3]):
        extra = ProjectGrainDependencyFact(
            determinants=(grain.active[3],), dependents=dependents
        )
        damages.append((*grain.dependencies, extra))
    if case == "multiple_bindings":
        prefix = grain.dependencies[:-2]
        account, dimension = grain.dependencies[-2:]
        damages.extend(
            (
                (*prefix, dimension),
                (*prefix, account),
                (*prefix, dimension, account),
            )
        )
    for dependencies in damages:
        forged = replace(
            operator,
            properties=replace(
                operator.properties,
                relational=replace(
                    properties,
                    grain=replace(grain, dependencies=dependencies),
                ),
            ),
        )
        with pytest.raises(
            CompiledError, match="^COMPILED_PROPERTY_JOIN_DEPENDENCIES$"
        ):
            verify_compiled_join_grain(ir, forged, parents)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("right_unique", (False, True))
def test_original_relationship_property_laws(tmp_path, target, right_unique):
    from _pietto_execution_guard_cases import planned, DIRECT
    from pietto._project.project_sql_emission import emit_project_sql

    body = DIRECT.replace("        on lhs.id == r.id\n", "        via link: l -> r\n")
    verified, contract = planned(
        tmp_path / "relationship",
        target,
        body,
        requested=False,
        link=True,
        right_unique=right_unique,
    )
    outcome = emit_project_sql(verified, contract)
    assert outcome.status == "VERIFIED"
    _compare(outcome.artifact)


@pytest.mark.parametrize(
    "target,case",
    [
        (target, case)
        for target in ("postgres", "mysql")
        for case in manifest()
        if target == "postgres" or not case["options"].get("postgres_only", False)
    ],
    ids=lambda value: value["name"] if isinstance(value, dict) else value,
)
def test_original_guard_preparation_closure(tmp_path, target, case):
    from pietto._project.project_guard_preparation import (
        prepare_compiled_guarded,
        prepare_guarded_template,
    )
    from pietto._project.project_guard_program import (
        prepare_program,
        pure_static_proofs,
    )
    from pietto._project.project_execution_template import bind_values

    original = case_preparation(tmp_path / "guard-source", target, case)
    source_refinement = None
    if case["options"].get("refined", False):
        from pietto._project.project_guard_preparation import prepare_guarded_output
        from pietto._project.project_refinement import prepare_refinement, TieRefinement

        source_refinement = prepare_refinement(
            original.artifact,
            capabilities(original.artifact),
            policy=TieRefinement(),
            output=prepare_guarded_output(original),
        )
    built = build_compiled(
        original.artifact, guarded=original, refinement=source_refinement
    )
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    artifact = emit_compiled(
        root, tuple(v.value for v in original.artifact.fixed_values)
    )
    candidate = prepare_compiled_guarded(artifact)
    reference, observed = prepare_program(original), prepare_program(candidate)
    assert artifact.rendered.sql == original.artifact.rendered.sql
    assert len(observed.subjects) == len(reference.subjects)
    assert tuple(
        len(pure_static_proofs(observed, s)) for s in observed.subjects
    ) == tuple(len(pure_static_proofs(reference, s)) for s in reference.subjects)
    assert tuple(
        (o.request.scope.value, o.assessment.state.value, len(o.proofs), len(o.joins))
        for o in candidate.scope.obligations
    ) == tuple(
        (o.request.scope.value, o.assessment.state.value, len(o.proofs), len(o.joins))
        for o in original.scope.obligations
    )
    template = prepare_guarded_template(candidate)
    values = tuple(v.value for v in original.artifact.fixed_values)
    rebound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    assert rebound.guarded is not None
    assert rebound.artifact.rendered.sql == artifact.rendered.sql
    assert len(prepare_program(rebound.guarded, binding=rebound).subjects) == len(
        reference.subjects
    )
    from pietto._project.project_guard_program import statement_for
    from pietto._project.project_guard_rendering import render_guard
    from pietto._project.project_guard_verification import verify_native_guard

    if source_refinement is not None:
        from pietto._project.project_refinement import prepare_compiled_refinement

        refined = prepare_compiled_refinement(
            rebound.artifact, binding=rebound, guarded=rebound.guarded
        )
        _compare_refined_structure(source_refinement, refined)
        observed = prepare_program(rebound.guarded, binding=rebound, refinement=refined)
    if any(not pure_static_proofs(observed, subject) for subject in observed.subjects):
        native = render_guard(statement_for(observed, "guard"))
        verify_native_guard(native)


def test_compiled_requirement_correspondence_rejects_coordinated_damage(tmp_path):
    from dataclasses import replace
    from types import MappingProxyType
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project.project_sql_plan_requirements import (
        verify_compiled_requirement_report,
        build_project_sql_requirement_report,
    )
    from pietto._project.project_compiled_verification import verify_compiled_emission

    source = template(tmp_path / "requirements-source")
    built = build_compiled(source.artifact)
    artifact = emit_compiled(
        built.root, tuple(v.value for v in source.artifact.fixed_values)
    )
    report = artifact.request.report
    assert artifact.original_requirements and artifact.generated_requirements
    assert (
        verify_compiled_requirement_report(report, artifact.request.verification)
        is report
    )
    with pytest.raises(
        ValueError,
        match=r"^Requirement report construction requires complete current plan evidence\.$",
    ):
        build_project_sql_requirement_report(artifact.request.verification)
    damaged = (
        replace(report, entries=()),
        replace(report, entries=report.entries[::-1]),
        replace(report, entries=(*report.entries, report.entries[-1])),
        replace(
            report,
            entries=(),
            links=(),
            by_family=MappingProxyType({}),
            by_subject=MappingProxyType({}),
            by_definition=MappingProxyType({}),
            by_stage=MappingProxyType({}),
            by_input_use=MappingProxyType({}),
            proved=(),
            enforcement_required=(),
        ),
        replace(
            report,
            entries=(
                replace(report.entries[0], origin=report.entries[-1].origin),
                *report.entries[1:],
            ),
        ),
    )
    codes = ("INVENTORY", "ENTRY", "INVENTORY", "INVENTORY", "ENTRY")
    for candidate, code in zip(damaged, codes, strict=True):
        with pytest.raises(ValueError, match="^COMPILED_REQUIREMENT_%s$" % code):
            verify_compiled_requirement_report(candidate, artifact.request.verification)
    for candidate, code in (
        (replace(artifact, original_requirements=()), "ORIGINAL"),
        (replace(artifact, generated_requirements=()), "GENERATED"),
        (
            replace(
                artifact, generated_requirements=artifact.generated_requirements[::-1]
            ),
            "GENERATED",
        ),
    ):
        with pytest.raises(
            ValueError, match="^COMPILED_EMISSION_%s_REQUIREMENTS$" % code
        ):
            verify_compiled_emission(candidate, artifact.request)


def _compare_aggregate_evidence(source, candidate):
    from dataclasses import replace
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
    )
    from pietto._project.project_sql_plan_verification import verify_compiled_sql_plan

    original = tuple(
        a.authority.source
        for a in source.aggregations
        if type(a.authority.source) is ProjectConcreteJoinedAggregation
    )
    assert len(candidate.aggregate_evidence) == len(original)
    assert len(candidate.aggregate_risks) == len(source.aggregate_risks)
    for observed, expected in zip(candidate.aggregate_evidence, original, strict=True):
        old_region = expected.input_filter.joined_semantics.multifact_region
        new_region = observed.region
        old_grain = old_region.final_properties.relational.grain
        new_grain = new_region.final_properties.grain
        old_factors = {f.identity: i for i, f in enumerate(old_grain.factors)}
        new_factors = {f.identity: i for i, f in enumerate(new_grain.factors)}
        old_uses = {
            use.ref: (i, j)
            for i, join in enumerate(old_region.region.joins)
            for j, use in enumerate(join.input_uses)
        }
        new_uses = {
            candidate.references[a]: (i, j)
            for i, join in enumerate(new_region.joins)
            for j, a in enumerate(join.record.get("inputs"))
        }
        assert tuple(f.kind.value for f in old_grain.active) == tuple(
            f.kind.value for f in new_grain.active
        )

        def classes(values):
            return tuple(tuple(f.field_position for f in c.members) for c in values)

        new_keys = {
            candidate.references[a]: i
            for i, a in enumerate(observed.stage.record.get("keys"))
        }

        def protection(value, factors, uses, ordinal):
            return (
                uses[value.introduction_use.ref],
                len(value.group_keys),
                tuple(ordinal(k) for k in value.computed_keys),
                classes(value.seed.classes),
                tuple(
                    (classes(k.determinants), k.strength.value, len(k.supports))
                    for k in value.strict_keys
                ),
                tuple(
                    (
                        d.status.value,
                        classes(d.seed.classes),
                        classes(d.requested.classes),
                        classes(d.closure.classes.classes),
                        tuple(classes(step.derived) for step in d.closure.witness),
                    )
                    for d in value.determinations
                ),
                tuple(factors[f] for f in value.protected_factors),
            )

        assert tuple(
            protection(p, new_factors, new_uses, new_keys.__getitem__)
            for p in observed.group_protections
        ) == tuple(
            protection(p, old_factors, old_uses, lambda k: k.source_ordinal)
            for p in expected.group_protections
        )

        def direction(value, factors):
            return (
                value.status.value,
                tuple(factors[f] for f in value.seed.factors),
                tuple(factors[f] for f in value.requested.factors),
                tuple(factors[f] for f in value.closure.factors),
            )

        def comparison(value, factors):
            return (
                value.status.value,
                direction(value.left_to_right, factors),
                direction(value.right_to_left, factors),
            )

        def linkage(value, factors):
            return (
                tuple(factors[f] for f in value.argument_factors),
                tuple(factors[f] for f in value.group_protection_factors),
                tuple(factors[f] for f in value.computed_key_factors),
                tuple(factors[f] for f in value.combined_seed.factors),
                tuple(factors[f] for f in value.closure.factors),
                value.contextual_grain.state.value,
                comparison(value.final_comparison, factors),
                tuple(
                    tuple(factors[f] for f in e.factor_additions)
                    for e in value.multiplicity_exposures
                ),
                tuple(r.value for r in value.multiplicity_risks),
                tuple(r.value for r in value.requirements),
            )

        assert tuple(linkage(v, new_factors) for v in observed.grain_linkages) == tuple(
            linkage(v, old_factors) for v in expected.grain_linkages
        )
        assert tuple(
            (
                v.function,
                len(v.arguments),
                tuple(
                    (new_uses[d.introduction_use.ref], d.input_field.field_position)
                    for d in v.field_dependencies
                ),
            )
            for v in observed.aggregates
        ) == tuple(
            (
                v.function_name,
                len(v.call.arguments),
                tuple(
                    (
                        old_uses[d.field_semantics.introduction_use.ref],
                        d.field_semantics.input_field.field_position,
                    )
                    for d in v.field_dependencies
                ),
            )
            for v in expected.aggregates
        )

        def candidates(values, factors):
            return tuple(
                (
                    tuple(factors[f] for f in c.factors.factors),
                    tuple(a.kind.value for a in c.authorities),
                )
                for c in values
            )

        assert candidates(new_region.actual_candidates, new_factors) == candidates(
            old_region.actual_candidates, old_factors
        )

        def pair(value, factors, linkages):
            common = value.common_grain
            return (
                linkages.index(value.left),
                linkages.index(value.right),
                comparison(value.grain_comparison, factors),
                common.status.value,
                candidates(common.actual_candidates, factors),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in common.common_candidates
                ),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in common.candidates
                ),
                tuple(
                    tuple(factors[f] for f in item.candidate.factors.factors)
                    for item in value.chasm_candidates
                ),
                value.structural.value,
                None if value.finer is None else linkages.index(value.finer),
                tuple(r.value for r in value.multiplicity_risks),
                tuple(r.value for r in value.requirements),
            )

        assert tuple(
            pair(v, new_factors, observed.grain_linkages)
            for v in observed.pair_linkages
        ) == tuple(
            pair(v, old_factors, expected.grain_linkages)
            for v in expected.pair_linkages
        )
    if original:
        with pytest.raises(ValueError):
            verify_compiled_sql_plan(replace(candidate, aggregate_evidence=()))
        with pytest.raises(ValueError):
            verify_compiled_sql_plan(
                replace(candidate, aggregate_risks=candidate.aggregate_risks[:-1])
            )


def _compare_refinement(artifact):
    from pietto._project.project_refinement import (
        TieRefinement,
        prepare_refinement,
        prepare_compiled_refinement,
    )

    reference = prepare_refinement(
        artifact, capabilities(artifact), policy=TieRefinement()
    )
    built = build_compiled(artifact, refinement=reference)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    candidate = emit_compiled(root, tuple(v.value for v in artifact.fixed_values))
    observed = prepare_compiled_refinement(candidate)
    _compare_refined_structure(reference, observed)


def _compare_refined_structure(reference, observed):
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import verify_native
    from pietto._project.project_execution_source import requirement_state

    def descriptor(source):
        state = requirement_state(source)
        assert state is not None
        return state[1:]

    assert tuple(descriptor(s) for s in observed.sources) == tuple(
        descriptor(s) for s in reference.sources
    )
    assert len(observed.units) == len(reference.units)
    assert tuple(
        (
            u.address,
            u.dependencies,
            u.coordinates,
            u.order_coordinates,
            u.directions,
            u.capacity,
        )
        for u in observed.units
    ) == tuple(
        (
            u.address,
            u.dependencies,
            u.coordinates,
            u.order_coordinates,
            u.directions,
            u.capacity,
        )
        for u in reference.units
    )
    assert tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.domain,
            c.realization.nullable,
        )
        for c in observed.output.columns
    ) == tuple(
        (
            c.ordinal,
            c.label,
            c.realization.tag,
            c.realization.storage,
            c.realization.domain,
            c.realization.nullable,
        )
        for c in reference.output.columns
    )
    assert tuple(i for i, _ in observed.erasure) == tuple(
        i for i, _ in reference.erasure
    )
    native = render(observed.statement, observed.original)
    assert verify_native(native, observed) == ()


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant",
    (("R2_mixed", "joint"), ("R2_repeated", "tied_limit"), ("R2_bound", "range")),
)
def test_additional_original_refinement_families(tmp_path, target, case, variant):
    from _pietto_execution_source_assurance_cases import original

    _compare(original(tmp_path / "refinement-source", target, case, variant))


def _compare_requirements(reference, observed):
    source = reference.request.report.report
    target = observed.request.report

    def source_ref(value):
        return (
            ("scope", 0)
            if value is reference.request.plan.scope
            else (value.kind.value, value.position)
        )

    def compiled_ref(value):
        return value.kind, value.position

    def owner_key(owner):
        return owner.module_position, owner.declaration_position

    expected = tuple(
        (
            entry.position,
            entry.family.value,
            None if entry.subkind is None else entry.subkind.value,
            source_ref(entry.ref),
            source_ref(entry.subject),
            source_ref(entry.scope.definition),
            tuple(source_ref(r) for r in entry.scope.stages),
            tuple(source_ref(r) for r in entry.scope.input_uses),
            source_ref(entry.origin.ref),
            source_ref(entry.origin.subject),
            entry.origin.role.value,
            entry.origin.provenance.value,
            owner_key(entry.origin.owner),
            tuple(source_ref(r) for r in entry.origin.antecedents),
            (
                entry.origin.cause.span.path,
                entry.origin.cause.span.line,
                entry.origin.cause.span.column,
                entry.origin.cause.span.end_line,
                entry.origin.cause.span.end_column,
            ),
        )
        for entry in source.entries
    )
    actual = tuple(
        (
            entry.position,
            entry.family.value,
            None if entry.subkind is None else entry.subkind.value,
            compiled_ref(entry.ref),
            compiled_ref(entry.subject),
            compiled_ref(entry.scope.definition),
            tuple(compiled_ref(r) for r in entry.scope.stages),
            tuple(compiled_ref(r) for r in entry.scope.input_uses),
            compiled_ref(entry.origin.ref),
            compiled_ref(entry.origin.subject),
            entry.origin.role.value,
            entry.origin.provenance.value,
            owner_key(entry.origin.owner),
            tuple(compiled_ref(r) for r in entry.origin.antecedents),
            entry.origin.location,
        )
        for entry in target.entries
    )
    assert actual == expected
    assert tuple(
        (e.position, e.kind.value, e.source.position, e.target.position)
        for e in target.links
    ) == tuple(
        (e.position, e.kind.value, e.source.position, e.target.position)
        for e in source.links
    )
    assert tuple(r.rule for r in observed.original_requirements) == tuple(
        r.rule for r in reference.original_requirements
    )


@pytest.mark.parametrize("retained", (True, "let", "capture"))
def test_retained_unselected_requests_rederive_without_execution_or_source(
    tmp_path, monkeypatch, retained
):
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project import project_execution_template

    # With "let" the retained request owner is a let of the unselected query,
    # and the compiled closure carries that let without its block. With
    # "capture" the unselected query reads a capturing let by EXISTS.
    source = proof_artifact(tmp_path / "retained-source", retained=retained).artifact
    assert source is not None
    original = prepare_template(source)
    assert len(original.slots) == 1
    expected = []
    for value in (1, 2, 1):
        bound = bind_values(original, ((original.slots[0], value),))
        expected.append(
            tuple(
                (
                    r.request.owner.declaration_position,
                    r.request.scope.value,
                    r.state.value,
                    tuple(p.kind.value for p in r.proofs),
                )
                for r in bound.artifact.request.verification.completed.single_matches.entries
            )
        )
    built = build_compiled(source)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    if retained == "capture":
        import dataclasses
        from pietto._project.project_compiled_schema import CompiledError, Record
        from pietto._project.project_compiled_verification import (
            verify_description,
        )

        # The retained owner's let is inline at its read, and its one capture
        # record is the FROM input row of that owner's reading body.
        description = root.description
        records = {r.address: r for r in description.records}
        (capture,) = (r for r in description.records if r.address.kind == "capture_use")
        block = records[capture.get("read")]
        reader = records[block.get("consumer")]
        assert records[reader.get("owner")].get("label") == "unused"
        assert records[block.get("producer")].get("layout") == (
            None,
            (),
            "s0",
            False,
            None,
        )
        (use,) = (
            r
            for r in description.records
            if r.address.kind == "use" and r.get("consumer") == reader.address
        )
        assert capture.get("ordinal") == 0
        assert capture.get("ports") == use.get("ports")[:2]
        forged = dataclasses.replace(
            description,
            members=tuple(
                (
                    name,
                    tuple(
                        Record(r.address, (r.values[0], 7, r.values[2]))
                        if r.address == capture.address
                        else r
                        for r in group
                    ),
                )
                for name, group in description.members
            ),
        )
        with pytest.raises(CompiledError, match="CAPTURE_ORDINALS"):
            verify_description(forged)
    if retained == "let":
        import dataclasses
        from pietto._project.project_compiled_schema import (
            FIELDS,
            CompiledError,
            Record,
        )
        from pietto._project.project_compiled_verification import (
            verify_description,
        )

        # Moved under the selected query, whose closure never reads it, the
        # retained let is refused: a block reads every let of it.
        description = built.root.description
        names = FIELDS["declaration"]
        (result,) = (
            r
            for r in description.records
            if r.address.kind == "declaration" and r.get("label") == "result"
        )

        def moved(record):
            if record.address.kind != "declaration" or record.get("label") != "j":
                return record
            values = dict(zip(names, record.values, strict=True)) | {
                n: result.get(n) for n in ("module", "module_position", "position")
            }
            return Record(record.address, tuple(values[n] for n in names))

        forged = dataclasses.replace(
            description,
            members=tuple(
                (name, tuple(moved(r) for r in records))
                for name, records in description.members
            ),
        )
        assert forged != description
        with pytest.raises(CompiledError, match="DECLARATION"):
            verify_description(forged)

    def forbidden(*args, **kwargs):
        raise AssertionError("source specialization must not run for a compiled bind")

    monkeypatch.setattr(project_execution_template, "_specialize", forbidden)
    artifact = emit_compiled(root, (1,))
    assert artifact.rendered.sql == source.rendered.sql
    assert len(artifact.request.plan.single_matches) == 1
    assert len(artifact.request.plan.all_single_matches) == 2
    template = prepare_template(artifact)
    assert len(template.slots) == 1
    for value, signatures in zip((1, 2, 1), expected, strict=True):
        bound = bind_values(template, ((template.slots[0], value),))
        plan = bound.artifact.request.plan
        assert len(plan.single_matches) == 1 and len(plan.all_single_matches) == 2
        assert (
            tuple(
                (
                    o.request.owner.declaration_position,
                    o.request.scope.value,
                    o.assessment.state.value,
                    tuple(p.kind.value for p in o.assessment.proofs),
                )
                for o in plan.all_single_matches
            )
            == signatures
        )
        assert bound.artifact.rendered.sql == source.rendered.sql
        assert len(bound.arguments) == 1


def test_a_retained_lateral_join_of_a_capturing_let_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # An unselected request owner that joins a capturing let LATERAL has no
    # retained compiled form yet: the build refuses it, never a lookup error.
    source = proof_artifact(tmp_path / "retained-source", retained="lateral").artifact
    assert source is not None
    with pytest.raises(CompiledError, match="COMPILED_RETAINED_CAPTURE"):
        build_compiled(source)


def test_a_retained_collect_read_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # D-S09-8: an unselected request owner's Collect read has no retained
    # compiled form (no guarded or R2 owner admits a nested value); the build
    # refuses it before its export, never with a lookup error.
    source = proof_artifact(tmp_path / "retained-source", retained="collect").artifact
    assert source is not None and not source.request.plan.collects
    with pytest.raises(CompiledError, match="COMPILED_RETAINED_COLLECT"):
        build_compiled(source)


def test_a_retained_order_with_a_hidden_key_is_refused(tmp_path):
    from pietto._project.project_compiled_schema import CompiledError

    # An unselected request owner's ORDER BY without DISTINCT carries its key
    # beside the projection, which has no retained compiled form yet: the
    # build refuses it, never a zip error.
    source = proof_artifact(tmp_path / "retained-source", retained="ordered").artifact
    assert source is not None
    with pytest.raises(CompiledError, match="^COMPILED_RETAINED_ORDER$"):
        build_compiled(source)


@pytest.mark.parametrize("shared_reads", (False, True))
def test_retained_unselected_relation_reads_export_and_verify(
    tmp_path, monkeypatch, shared_reads
):
    """An unselected request owner's NOT IN, EXISTS and scalar reads export and
    verify like the selected path's: each operation names one block use of its actual
    producer, a producer reached only through such a read is retained, a read
    of a relation shared with the selected statement stays one block use, and
    the loaded replay is the source statement."""
    from dataclasses import replace
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_compiled_schema import CompiledError, Record

    original = emission.join_witness
    projection = "    select:\n        value = lhs.id\n"

    def with_reads(target, body, **options):
        selected, unused = body.split("query unused:", 1)
        if shared_reads:
            selected = selected.replace(
                projection, "    where lhs.id in ranked_ids\n" + projection
            ).replace(
                "    from rhs\n", "    from rhs\n    where id not in ranked_ids\n", 1
            )
        unused = unused.replace(
            projection,
            "    where lhs.id not in ranked_ids\n"
            + projection
            + "        seen = exists ranked_ids\n"
            + "        top = scalar ranked_ids.id\n",
        )
        return original(
            target,
            "query ranked_ids:\n    from rhs\n    select:\n        id\n"
            + selected
            + "query unused:"
            + unused,
            **options,
        )

    captured = []
    checker = verification.verify_logical_export

    def capture(description, checked, references):
        checker(description, checked, references)
        captured.append((description, checked, references))

    monkeypatch.setattr(emission, "join_witness", with_reads)
    monkeypatch.setattr(verification, "verify_logical_export", capture)
    source = proof_artifact(tmp_path / "retained-reads", retained=True).artifact
    assert source is not None
    built = build_compiled(source)
    records = built.root.records

    def label(address):
        return records[records[address].get("owner")].get("label")

    assert [
        (
            records[r.get("operation")].get("operator"),
            r.get("column"),
            label(r.get("producer")),
            label(r.get("consumer")),
        )
        for r in records.values()
        if r.address.kind == "expression_block_use"
    ] == [
        *(
            [
                (("relation_membership", "not_in"), 0, "ranked_ids", "ranked"),
                (("relation_membership", "in"), 0, "ranked_ids", "result"),
            ]
            * shared_reads
        ),
        (("relation_membership", "not_in"), 0, "ranked_ids", "unused"),
        (("exists", "exists"), None, "ranked_ids", "unused"),
        (("scalar", "scalar"), 0, "ranked_ids", "unused"),
    ]
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, tuple(v.value for v in source.fixed_values))
    assert replay.rendered.sql == source.rendered.sql
    # The retained component is re-derived from its own plan: another
    # operator or another producer for its membership read, and another
    # operator or no column for its scalar read, are refused.
    ((child, checked, references),) = captured
    described = {r.address: r for r in child.records}
    membership, scalar_read = (
        r
        for r in described.values()
        if r.address.kind == "expression_block_use"
        and r.get("column") == 0
        and described[described[r.get("consumer")].get("owner")].get("label")
        == "unused"
    )
    operation = described[membership.get("operation")]
    scalar_operation = described[scalar_read.get("operation")]
    assert scalar_operation.get("operator") == ("scalar", "scalar")
    for changed, word in (
        (
            Record(
                operation.address,
                (("relation_membership", "in"), *operation.values[1:]),
            ),
            "EXPRESSION",
        ),
        (
            Record(
                membership.address,
                (*membership.values[:2], membership.get("consumer"), 0),
            ),
            "BLOCK_READ",
        ),
        (
            Record(
                scalar_operation.address,
                (("exists", "exists"), *scalar_operation.values[1:]),
            ),
            "EXPRESSION",
        ),
        (Record(scalar_read.address, (*scalar_read.values[:3], None)), "BLOCK_READ"),
    ):
        forged = replace(
            child,
            members=tuple(
                (
                    name,
                    tuple(
                        changed if r.address == changed.address else r for r in group
                    ),
                )
                for name, group in child.members
            ),
        )
        with pytest.raises(CompiledError, match=f"^COMPILED_RETAINED_{word}$"):
            checker(forged, checked, references)


def test_embedded_json_depth_is_checked_before_decoder_recursion(tmp_path):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project.project_compiled_schema import (
        Record,
        MAX_DEPTH,
        encode,
        content_pin,
        CompiledError,
    )

    source = template(tmp_path / "bounded-source")
    built = build_compiled(source.artifact)
    for kind, field in (
        ("field", "physical"),
        ("target", "contract"),
        ("premise", "value"),
    ):
        target = next(
            r for r in built.root.description.records if r.address.kind == kind
        )
        values = list(target.values)
        from pietto._project.project_compiled_schema import FIELDS

        values[FIELDS[kind].index(field)] = (
            "[" * (MAX_DEPTH + 1) + "0" + "]" * (MAX_DEPTH + 1)
        )
        damaged = Record(target.address, tuple(values))
        description = replace(
            built.root.description,
            members=tuple(
                (
                    name,
                    tuple(
                        damaged if r.address == target.address else r for r in records
                    ),
                )
                for name, records in built.root.description.members
            ),
        )
        raw = encode(description)
        with pytest.raises(CompiledError, match="^COMPILED_DEPTH_LIMIT$"):
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )


def test_repinned_slot_and_requirement_damage_refuses(tmp_path):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    import _pietto_results_product as product
    from pietto._project.project_compiled_schema import (
        FIELDS,
        Record,
        encode,
        content_pin,
    )

    source = template(
        tmp_path / "damage-source",
        product.source("postgres").replace(
            "renamed = id", "renamed = 1\n        another = 1"
        ),
    )
    built = build_compiled(source.artifact)
    records = built.root.description.records
    slots = tuple(r for r in records if r.address.kind == "slot")
    assert len(slots) == 2
    first_site = built.root.records[slots[0].get("site")]

    def altered(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    damages = (
        altered(first_site, role="limit"),
        altered(first_site, ancestry=(("unary", 0),)),
        altered(slots[1], site=slots[0].get("site"), literal=slots[0].get("literal")),
        altered(
            next(r for r in records if r.address.kind == "requirement"), family="window"
        ),
        altered(
            next(r for r in records if r.address.kind == "target"),
            profile="finite_mysql_v1",
        ),
    )
    codes = (
        "SLOT_ELIGIBILITY",
        "SLOT_ANCESTRY",
        "SLOT_ALIAS",
        "REQUIREMENT_SUBKIND",
        "PROFILE",
    )
    for damaged, code in zip(damages, codes, strict=True):
        description = replace(
            built.root.description,
            members=tuple(
                (
                    name,
                    tuple(
                        damaged if r.address == damaged.address else r for r in members
                    ),
                )
                for name, members in built.root.description.members
            ),
        )
        raw = encode(description)
        with pytest.raises(ValueError, match="^COMPILED_%s$" % code):
            load_compiled(
                raw,
                expected_pin=content_pin(raw),
                accepted_producer=built.producer,
                accepted_compatibility=built.compatibility,
            )


def test_repinned_cross_family_comparison_refuses_derivation_and_verification(
    tmp_path, monkeypatch
):
    from dataclasses import replace
    from _pietto_execution_postgres_rows_probe import template
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_completed_semantics import (
        derive_compiled_semantics,
        verify_compiled_semantics,
    )
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Record,
        Scalar,
        content_pin,
        encode,
    )
    from pietto.semantic import expressions
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
    )

    # The default template filters `id > 1` with the literal bound to an Int slot.
    built = build_compiled(template(tmp_path / "comparison-source").artifact)
    records = built.root.description.records
    slot = next(r for r in records if r.address.kind == "slot")
    literal = built.root.records[slot.get("literal")]

    def altered(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    damaged = {
        r.address: r
        for r in (
            altered(literal, tag="Text", value=Scalar("Text", "1")),
            altered(slot, tag="Text"),
        )
    }
    description = replace(
        built.root.description,
        members=tuple(
            (name, tuple(damaged.get(r.address, r) for r in members))
            for name, members in built.root.description.members
        ),
    )
    raw = encode(description)
    root = load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    # The shared comparison law refuses Int > Text before any physical check.
    with pytest.raises(CompiledError, match="^COMPILED_OPERATOR_TYPE$"):
        derive_compiled_semantics(root, ("1",))

    # A derivation forged past the law and the physical comparison check is
    # still refused by the independent verifier.
    with monkeypatch.context() as patch:
        unchecked = (
            ValueType(
                ResolvedType("Bool", TypeKind.BUILTIN), EffectiveNullability.UNKNOWN
            ),
            None,
        )
        patch.setattr(
            expressions, "resolved_comparison_value_type", lambda *_: unchecked
        )
        patch.setattr(
            physical,
            "resolved_comparison_realization",
            lambda family, tag, nullable, left, right, *, operator: (
                physical._bool(family, False),
                None,
            ),
        )
        forged = derive_compiled_semantics(root, ("1",))
    with pytest.raises(CompiledError, match="^COMPILED_SEMANTIC_TYPE$"):
        verify_compiled_semantics(forged)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_compiled_premises_preserve_original_admission(tmp_path, target):
    """A correct external test pin must not hide invalid semantic premises."""
    import copy
    import json
    from dataclasses import replace
    from pietto._project.project_compiled_schema import (
        Address,
        Record,
        encode,
        content_pin,
    )
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_sql_emission_contract import canonical

    source = build(
        tmp_path / "premise-source", target, "S_fixed_named", "imported_bind"
    ).artifact
    assert source is not None
    built = build_compiled(source)
    described = built.root.description
    original_contract = json.loads(source.request.accepted_bytes)
    original_premises = tuple(
        r for r in described.records if r.address.kind == "premise"
    )

    def load(contract, premises):
        target_record = built.root.records[Address("target", 0)]
        changed_target = Record(
            target_record.address,
            (
                *target_record.values[:2],
                canonical(contract).decode(),
                target_record.values[3],
            ),
        )
        changed_premises = tuple(
            Record(Address("premise", i), (i, *r.values[1:]))
            for i, r in enumerate(premises)
        )
        description = replace(
            described,
            members=tuple(
                (
                    name,
                    tuple(
                        changed_target if r.address.kind == "target" else r
                        for r in records
                        if r.address.kind != "premise"
                    )
                    + (changed_premises if name == "targets" else ()),
                )
                for name, records in described.members
            ),
        )
        raw = encode(description)
        return load_compiled(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )

    # Expected rejection comes from the original source emitter and its real roots.
    for key, value, code in (
        ("operator_environment", "unqualified_operators", "OPERATOR_PREMISE"),
        ("parameter_protocol", "interpolated_text", "OPERATOR_PREMISE"),
        ("identifier_case", "case_folded", "NAMING_PREMISE"),
        ("client_encoding", "LATIN1", "SOURCE_PREMISE"),
        ("row_domain_matches", False, "SOURCE_PREMISE"),
        ("read_only_object", False, "SOURCE_PREMISE"),
        ("row_domain_matches", 1, "PREMISE_VALUE"),
    ):
        contract = copy.deepcopy(original_contract)
        raw_premises = contract["environment"] + [
            p for s in contract["sources"] for p in s["premises"]
        ]
        assert any(p["key"] == key for p in raw_premises)
        for p in raw_premises:
            if p["key"] == key:
                p["value"] = value
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert outcome.status in ("INPUT_REJECTED", "BLOCKED"), key
        premises = tuple(
            Record(r.address, (*r.values[:3], canonical(value).decode()))
            if r.get("key") == key
            else r
            for r in original_premises
        )
        with pytest.raises(ValueError, match="^COMPILED_%s$" % code):
            load(contract, premises)

    for key, code in (
        ("operator_environment", "OPERATOR"),
        ("parameter_protocol", "OPERATOR"),
        ("client_encoding", "SOURCE"),
        ("row_domain_matches", "SOURCE"),
        ("read_only_object", "SOURCE"),
    ):
        contract = copy.deepcopy(original_contract)
        contract["environment"] = [
            p for p in contract["environment"] if p["key"] != key
        ]
        for s in contract["sources"]:
            s["premises"] = [p for p in s["premises"] if p["key"] != key]
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert outcome.status == "BLOCKED", key
        with pytest.raises(ValueError, match="^COMPILED_%s_PREMISE$" % code):
            load(contract, tuple(r for r in original_premises if r.get("key") != key))

    # Preserve the original distinction between equal repeats and conflicts.
    first = next(
        i
        for i, r in enumerate(original_premises)
        if r.get("key") == "operator_environment"
    )
    for value, accepted in (("builtin_only", True), ("unqualified_operators", False)):
        contract = copy.deepcopy(original_contract)
        index = next(
            i
            for i, p in enumerate(contract["environment"])
            if p["key"] == "operator_environment"
        )
        contract["environment"].insert(
            index + 1, dict(key="operator_environment", scope="statement", value=value)
        )
        extra = Record(
            original_premises[first].address,
            (*original_premises[first].values[:3], canonical(value).decode()),
        )
        premises = (
            *original_premises[: first + 1],
            extra,
            *original_premises[first + 1 :],
        )
        outcome = emit_project_sql(source.request.verification, canonical(contract))
        assert (outcome.status == "VERIFIED") is accepted
        if accepted:
            root = load(contract, premises)
            assert (
                emit_compiled(
                    root, tuple(v.value for v in source.fixed_values)
                ).rendered.sql
                == source.rendered.sql
            )
        else:
            with pytest.raises(ValueError, match="^COMPILED_PREMISE_CONFLICT$"):
                load(contract, premises)

    # The raw contract and resolved graph must agree independently and completely.
    for damage, code in (
        ("missing_record", "PREMISES"),
        ("extra_field", "SOURCE"),
        ("wrong_scan", "SOURCE"),
        ("bool_ordinal", "FIELD"),
        ("wrong_source_scope", "PREMISE_SCOPE"),
    ):
        contract = copy.deepcopy(original_contract)
        premises = original_premises
        if damage == "missing_record":
            premises = premises[:-1]
        elif damage == "extra_field":
            contract["sources"][0]["unexpected"] = True
        elif damage == "wrong_scan":
            contract["sources"][0]["scan"] = "raw_sql"
        elif damage == "bool_ordinal":
            contract["sources"][0]["fields"][0]["ordinal"] = False
        else:
            contract["sources"][0]["premises"][0]["scope"] = "statement"
        with pytest.raises(ValueError, match="^COMPILED_CONTRACT_%s$" % code):
            load(contract, premises)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "variant", ("limit", "global", "grouped", "window", "set", "ordered", "key")
)
def test_retained_unselected_request_does_not_require_execution_mapping(
    tmp_path, monkeypatch, target, variant
):
    from dataclasses import replace
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project import project_compiled_verification as verification
    from pietto._project.project_compiled_schema import (
        Address,
        Record,
        FIELDS,
        encode,
        content_pin,
    )

    outcome = retained_unmapped_source(
        tmp_path / "unselected-unmapped", target, variant, monkeypatch
    )
    assert outcome.status == "VERIFIED", tuple(
        (b.code, b.detail) for b in outcome.blockers
    )
    source = outcome.artifact
    assert source is not None
    assert len(source.request.verification.completed.single_match_requests) == 2
    assert len(source.request.sources) == 2
    # The actual source binding route retains this request without admitting or
    # evaluating the unrelated physical source.
    reference = prepare_template(source)
    accepted = bind_values(reference, tuple((slot, 2) for slot in reference.slots))
    captured = []
    checker = verification.verify_logical_export

    def capture(description, checked, correspondence):
        checker(description, checked, correspondence)
        captured.append((description, checked, correspondence.copy()))

    monkeypatch.setattr(verification, "verify_logical_export", capture)
    built = build_compiled(source)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    template = prepare_template(
        emit_compiled(loaded, tuple(v.value for v in source.fixed_values))
    )
    bound = bind_values(template, tuple((slot, 2) for slot in template.slots))
    assert bound.artifact.rendered.sql == accepted.artifact.rendered.sql
    assert len(bound.artifact.request.plan.all_single_matches) == 2
    assert len(bound.artifact.request.plan.single_matches) == 1
    assert len(bound.artifact.request.sources) == 2
    assert tuple(
        (
            a.request.owner.declaration_position,
            a.request.scope.value,
            a.assessment.state.value,
            tuple(p.kind.value for p in a.assessment.proofs),
        )
        for a in bound.artifact.request.plan.all_single_matches
    ) == tuple(
        (
            a.request.owner.declaration_position,
            a.request.scope.value,
            a.state.value,
            tuple(p.kind.value for p in a.proofs),
        )
        for a in accepted.artifact.request.verification.completed.single_matches.entries
    )
    logical_sources = tuple(
        r
        for r in loaded.description.records
        if r.address.kind == "source" and r.get("namespace") is None
    )
    assert len(logical_sources) == 1
    assert all(
        loaded.records[f].get("physical") is None
        for f in logical_sources[0].get("fields")
    )

    assert len(captured) == 1
    description, checked, correspondence = captured[0]

    def changed_record(record, **changes):
        values = list(record.values)
        for name, value in changes.items():
            values[FIELDS[record.address.kind].index(name)] = value
        return Record(record.address, tuple(values))

    field = next(r for r in description.records if r.address.kind == "field")
    use = next(r for r in description.records if r.address.kind == "use")
    request = next(r for r in description.records if r.address.kind == "request")
    damages = [
        changed_record(field, logical=("Bool", "non_null")),
        changed_record(use, ordinal=99),
        changed_record(
            request, pairs=tuple(pair[::-1] for pair in request.get("pairs"))
        ),
    ]
    codes = ("SOURCE_FIELD", "USE_INPUT", "REQUEST_INPUTS")
    for damage, code in zip(damages, codes, strict=True):
        candidate = replace(
            description,
            members=tuple(
                (
                    name,
                    tuple(
                        damage if r.address == damage.address else r for r in records
                    ),
                )
                for name, records in description.members
            ),
        )
        with pytest.raises(ValueError, match="^COMPILED_RETAINED_%s$" % code):
            checker(candidate, checked, correspondence)
    removed = {"site"}
    if variant == "key":
        removed.add("source_unique")
    for kind in removed:
        assert any(r.address.kind == kind for r in description.records), kind
        candidate = replace(
            description,
            members=tuple(
                (name, tuple(r for r in records if r.address.kind != kind))
                for name, records in description.members
            ),
        )
        code = {"site": "LITERAL", "source_unique": "KEY"}[kind]
        with pytest.raises(ValueError, match="^COMPILED_RETAINED_%s_INVENTORY$" % code):
            checker(candidate, checked, correspondence)

    # A retained logical source cannot become an executable source by changing
    # the selected entry, even with a correct independent test pin.
    entry = loaded.records[loaded.description.query]
    terminal = loaded.records[entry.get("retained")[0]]
    changed = changed_record(
        entry,
        declaration=terminal.get("owner"),
        terminal=terminal.address,
        exports=terminal.get("outputs"),
        retained=(entry.get("terminal"),),
    )
    selected_outputs = tuple(
        Record(
            Address("output", i),
            (
                i,
                loaded.records[port].get("label"),
                port,
                loaded.records[port].get("logical"),
                None,
            ),
        )
        for i, port in enumerate(terminal.get("outputs"))
    )
    candidate = replace(
        loaded.description,
        members=tuple(
            (
                name,
                selected_outputs
                if name == "outputs"
                else tuple(
                    changed if r.address == entry.address else r for r in records
                ),
            )
            for name, records in loaded.description.members
        ),
    )
    raw = encode(candidate)
    with pytest.raises(ValueError, match="^COMPILED_SOURCE$"):
        load_compiled(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )


# Phase70 S12: a JOIN reads a let with capture lines LATERAL; the let compiles
# inline at that JOIN's right input and each capture_use record names that
# right input's use, its capturing read.
LATERAL_LET = """    let {name}:
        capture lhs
        from rhs
        where rhs.{field} == lhs.{field}
        select:
            id
{tail}    from lhs
"""
TWO_LATERAL = (
    "table a:\n"
    + LATERAL_LET.format(name="m", field="key", tail="")
    + "    let m1 = m\n    cross join m1\n"
    + "    select:\n        id = lhs.id\n        t = m1.id\n"
    + "table b:\n"
    + LATERAL_LET.format(name="n", field="id", tail="")
    + "    let n1 = n\n    inner join n1 on True\n"
    + "    select:\n        id = lhs.id\n        t = n1.id\n"
    + "query result:\n    from a\n    let y = b\n    cross join y\n"
    + "    select:\n        x = a.t\n        z = y.t\n"
)
TOP_K_LATERAL = (
    "query result:\n"
    + LATERAL_LET.format(
        name="m",
        field="key",
        tail="            v = rhs.key\n        order by:\n            key desc\n"
        "            id\n        limit 2\n",
    )
    + "    let m1 = m\n    {kind} join m1{on}\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n"
)


def _compiled_lateral(directory, target, source):
    """The verified source artifact, its compiled build and the loaded replay."""
    from pietto._project.project_compiled_schema import encode

    item = emission.join_witness(target, source, policy="bind_safe_literals")
    checked, original = emission.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    assert checked.verified and original.status == "VERIFIED"
    artifact = original.artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert encode(loaded.description) == built.payload
    candidate = emit_compiled(loaded, tuple(v.value for v in artifact.fixed_values))
    assert candidate.rendered.sql == artifact.rendered.sql
    return artifact, built, candidate


def _replaced(description, targets):
    """``description`` with the values of the records in ``targets`` replaced."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import Record

    return replace(
        description,
        members=tuple(
            (
                name,
                tuple(
                    Record(r.address, targets[r.address]) if r.address in targets else r
                    for r in records
                ),
            )
            for name, records in description.members
        ),
    )


def _load(raw, built):
    from pietto._project.project_compiled_schema import content_pin

    return load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )


def _captured_references(query):
    """Every captured reference of a lowered statement, by its scope alias."""
    import dataclasses
    from pietto._project import project_sql_emission_rows as rows

    found, pending, seen = {}, list(query.bodies), set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is rows.SQLCapturedReference:
            found.setdefault(value.scope.name, []).append(value)
        if type(value) is tuple:
            pending.extend(value)
        elif dataclasses.is_dataclass(value) and type(value).__module__.startswith(
            "pietto._project.project_sql_emission"
        ):
            pending.extend(getattr(value, f.name) for f in dataclasses.fields(value))
    return found


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_two_lateral_lets_capturing_one_source_replay_by_their_reads(tmp_path, target):
    from pietto._project.project_compiled_schema import CompiledError, encode
    from pietto._project.project_compiled_verification import (
        verify_compiled_emission,
        verify_description,
    )

    # Two tables each join their own let LATERAL over the same source lhs: the
    # two capture records name the same source ports through distinct reads.
    artifact, built, candidate = _compiled_lateral(tmp_path, target, TWO_LATERAL)
    description = built.root.description
    records = {r.address: r for r in description.records}
    first, second = (r for r in description.records if r.address.kind == "capture_use")
    assert first.get("ports") == second.get("ports")
    assert first.get("read") != second.get("read")
    for record in (first, second):
        right = records[record.get("read")]
        assert (right.address.kind, right.get("ordinal"), record.get("ordinal")) == (
            "use",
            1,
            0,
        )
        assert records[right.get("consumer")].address.kind == "join"
    # Each captured reference names the record of its own JOIN's read.
    captured = _captured_references(candidate.ast)
    assert {
        alias: [r.capture.ref.position for r in found]
        for alias, found in captured.items()
    } == {"m0": [0], "m2": [1]}
    # Swapped between the two reads, a valid record of the same port is refused
    # by the compiled emission verifier.
    (left,), (right,) = captured["m0"], captured["m2"]
    original = left.capture, right.capture
    object.__setattr__(left, "capture", original[1])
    object.__setattr__(right, "capture", original[0])
    try:
        with pytest.raises(CompiledError, match="^COMPILED_EMISSION_CAPTURE$"):
            verify_compiled_emission(candidate, candidate.request)
    finally:
        object.__setattr__(left, "capture", original[0])
        object.__setattr__(right, "capture", original[1])
    verify_compiled_emission(candidate, candidate.request)
    # Both records naming one read leave the other read without its let.
    with pytest.raises(CompiledError, match="^COMPILED_INLINE_INVENTORY$"):
        verify_description(
            _replaced(
                description, {second.address: (first.get("read"), *second.values[1:])}
            )
        )
    # The two records swapped whole are the same captures renumbered: each
    # read still finds its own record, and the replay is the same statement.
    swapped = _replaced(
        description, {first.address: second.values, second.address: first.values}
    )
    verify_description(swapped)
    replay = emit_compiled(
        _load(encode(swapped), built), tuple(v.value for v in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    assert {
        alias: [r.capture.ref.position for r in found]
        for alias, found in _captured_references(replay.ast).items()
    } == {"m0": [1], "m2": [0]}


def test_a_lateral_lets_inline_units_name_no_input_of_its_join(tmp_path):
    # Its correlated references name the JOIN's left input: no unit of the
    # let, its ORDER BY and LIMIT included, takes a JOIN input's alias, and no
    # two of its units share one. Another unit's scope may repeat an alias.
    from pietto._project.project_compiled_schema import FIELDS, CompiledError, encode
    from pietto._project.project_compiled_verification import verify_description

    source = TOP_K_LATERAL.format(kind="cross", on="")
    _, built, _ = _compiled_lateral(tmp_path, "postgres", source)
    description = built.root.description
    (join,) = (r for r in description.records if r.address.kind == "join")
    inline = [
        r
        for r in description.records
        if "layout" in FIELDS[r.address.kind] and r.get("layout")[-1] is None
    ]
    assert [r.address.kind for r in inline] == ["row", "row", "result"]
    names = [r.get("layout")[2] for r in inline]
    assert join.get("layout")[2] == ("m0", "m1")

    def aliased(record, alias):
        values = list(record.values)
        at = FIELDS[record.address.kind].index("layout")
        layout = values[at]
        values[at] = (*layout[:2], alias, *layout[3:])
        return _replaced(description, {record.address: tuple(values)})

    forgeries = [aliased(unit, "m0") for unit in inline]
    forgeries += [aliased(join, ("m0", name)) for name in names]
    forgeries.append(aliased(inline[2], names[0]))
    for forged in forgeries:
        with pytest.raises(CompiledError, match="^COMPILED_ALIASES$"):
            verify_description(forged)
        with pytest.raises(CompiledError, match="^COMPILED_ALIASES$"):
            _load(encode(forged), built)


@pytest.mark.parametrize("kind", ("right", "full", "semi", "anti"))
def test_a_compiled_lateral_join_keeps_a_kind_that_extends_each_left_row(
    tmp_path, kind
):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        encode,
    )
    from pietto._project.project_compiled_verification import verify_description

    source = TOP_K_LATERAL.format(kind="left", on=" on m1.id > 3")
    _, built, _ = _compiled_lateral(tmp_path, "postgres", source)
    description = built.root.description
    (join,) = (r for r in description.records if r.address.kind == "join")
    assert join.get("kind") == "left"
    # Otherwise valid: a SEMI or ANTI JOIN outputs only its left input.
    names = FIELDS["join"]
    values = list(join.values)
    values[names.index("kind")] = kind
    if kind in ("semi", "anti"):
        left = next(
            r for r in description.records if r.address == join.get("inputs")[0]
        )
        values[names.index("outputs")] = join.get("outputs")[: len(left.get("ports"))]
    forged = _replaced(description, {join.address: tuple(values)})
    with pytest.raises(CompiledError, match="^COMPILED_LATERAL_JOIN_KIND$"):
        verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_LATERAL_JOIN_KIND$"):
        _load(encode(forged), built)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("cross", "inner", "left"))
def test_a_lateral_top_k_replays_from_compiled_input(tmp_path, target, kind):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Scalar,
    )
    from pietto._project.project_compiled_verification import (
        verify_description,
        verify_export,
    )

    on = {"cross": "", "inner": " on True", "left": " on m1.id > 3"}
    artifact, built, candidate = _compiled_lateral(
        tmp_path, target, TOP_K_LATERAL.format(kind=kind, on=on[kind])
    )
    assert b" LIMIT 2) AS " in candidate.rendered.sql
    # The let's ORDER BY and LIMIT are one inline result unit, read by the
    # JOIN's right input: no unit position, no CTE name, not final.
    description = built.root.description
    records = {r.address: r for r in description.records}
    (capture,) = (r for r in description.records if r.address.kind == "capture_use")
    result = records[records[capture.get("read")].get("producer")]
    assert result.address.kind == "result"
    assert result.get("layout") == (None, (), "t0", False, None)
    assert (result.get("distinct"), result.get("limit")) == (False, 2)
    assert [d for _, d in result.get("ordering")] == ["desc", "asc"]
    projection = records[result.get("input")]
    assert projection.address.kind == "row" and projection.get("layout")[-1] is None
    names = FIELDS["result"]

    def changed(**fields):
        values = list(result.values)
        for name, value in fields.items():
            values[names.index(name)] = value
        return _replaced(description, {result.address: tuple(values)})

    layout = result.get("layout")
    # Claiming a unit position or a CTE name makes it no inline unit.
    with pytest.raises(CompiledError, match="^COMPILED_CAPTURE_USE$"):
        verify_description(changed(layout=(*layout[:-1], 0)))
    with pytest.raises(CompiledError, match="^COMPILED_INLINE_LAYOUT$"):
        verify_description(changed(layout=("p9", *layout[1:])))
    # Another valid LIMIT with its literal is a coherent description; the
    # export verifier re-derives it from the live statement and refuses it.
    literal = records[result.get("limit_literal")]
    values = list(literal.values)
    values[FIELDS["literal"].index("value")] = Scalar("Int", 3)
    limit = list(result.values)
    limit[names.index("limit")] = 3
    forged = _replaced(
        description, {result.address: tuple(limit), literal.address: tuple(values)}
    )
    verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_EXPORT_STATIC_LITERAL$"):
        verify_export(forged, artifact)


# Owner decision 2026-10-15 (D70.05): a correlated NOT IN and a scalar read of
# two lets ending in ORDER BY and LIMIT compile on PostgreSQL with no new
# record kind: each let's ORDER BY and LIMIT are one inline result unit, the
# outermost of its chain, read by the expression block use of its read.
ORDERED_BLOCK_READS = (
    "query result:\n    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "        order by:\n            id desc\n        limit 2\n"
    "    let n:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            key\n"
    "        order by:\n            id\n        limit 1\n"
    "    from lhs\n    where lhs.id not in m\n"
    "    select:\n        a = lhs.id\n        k = scalar n.key\n"
)


def test_ordered_scalar_and_in_reads_replay_from_compiled_input(tmp_path):
    from pietto._project.project_compiled_schema import (
        FIELDS,
        CompiledError,
        Scalar,
    )
    from pietto._project.project_compiled_verification import (
        verify_description,
        verify_export,
    )

    artifact, built, candidate = _compiled_lateral(
        tmp_path, "postgres", ORDERED_BLOCK_READS
    )
    sql = candidate.rendered.sql
    assert (sql.count(b" LIMIT 2) AS "), sql.count(b" LIMIT 1) AS ")) == (1, 1)
    description = built.root.description
    records = {r.address: r for r in description.records}
    captures = [r for r in description.records if r.address.kind == "capture_use"]
    reads = [records[c.get("read")] for c in captures]
    assert [r.address.kind for r in reads] == ["expression_block_use"] * 2
    results = [records[r.get("producer")] for r in reads]
    assert sorted(
        (r.address.kind, r.get("layout")[:2], r.get("layout")[3:], r.get("limit"))
        for r in results
    ) == [
        ("result", (None, ()), (False, None), 1),
        ("result", (None, ()), (False, None), 2),
    ]
    result = results[0]
    names = FIELDS["result"]
    layout = result.get("layout")
    # A unit position makes it no inline unit of the read.
    values = list(result.values)
    values[names.index("layout")] = (*layout[:-1], 0)
    with pytest.raises(CompiledError, match="^COMPILED_CAPTURE_USE$"):
        verify_description(_replaced(description, {result.address: tuple(values)}))
    # Another valid LIMIT with its literal is a coherent description that the
    # export verifier refuses against the live statement.
    literal = records[result.get("limit_literal")]
    literal_values = list(literal.values)
    literal_values[FIELDS["literal"].index("value")] = Scalar("Int", 3)
    values = list(result.values)
    values[names.index("limit")] = 3
    forged = _replaced(
        description,
        {result.address: tuple(values), literal.address: tuple(literal_values)},
    )
    verify_description(forged)
    with pytest.raises(CompiledError, match="^COMPILED_EXPORT_STATIC_LITERAL$"):
        verify_export(forged, artifact)


def test_a_mysql_description_of_an_ordered_block_read_is_refused(tmp_path, monkeypatch):
    # MySQL reads a let's ORDER BY and LIMIT only LATERAL. A MySQL artifact
    # forged past the emission's own refusal and its verifiers describes a
    # scalar or IN read of an inline result unit; the emission verifier and
    # the compiled description (a repinned bundle) each refuse it on their own.
    from types import SimpleNamespace

    from pietto._project import project_sql_emission as emitting
    from pietto._project import project_sql_emission_ast as sql_ast
    from pietto._project import project_sql_emission_inspection as inspection
    from pietto._project.project_compiled_build import _Export
    from pietto._project.project_compiled_schema import CompiledError, encode
    from pietto._project.project_compiled_verification import verify_description
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    verified = SimpleNamespace(verified=True, issues=())
    monkeypatch.setattr(
        sql_ast, "ORDERED_INLINE_READ_TARGETS", frozenset({"postgres", "mysql"})
    )
    monkeypatch.setattr(emitting, "verify_row_query", lambda *_: True)
    for module in (emitting, inspection):
        monkeypatch.setattr(module, "verify_project_sql_emission", lambda *_: verified)
    item = emission.join_witness("mysql", ORDERED_BLOCK_READS)
    _, outcome = emission.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    artifact = outcome.artifact
    assert artifact is not None and b" LIMIT 1) AS " in artifact.rendered.sql
    description = _Export(artifact, None, None).run()
    monkeypatch.undo()
    assert not verify_project_sql_emission(artifact, artifact.request).verified
    with pytest.raises(CompiledError, match="^COMPILED_MYSQL_CORRELATED_ORDER$"):
        verify_description(description)
    built = SimpleNamespace(
        producer=description.producer, compatibility=description.compatibility
    )
    with pytest.raises(CompiledError, match="^COMPILED_MYSQL_CORRELATED_ORDER$"):
        _load(encode(description), built)
