"""Complete original named families are the source-side differential reference."""

import pytest

from _pietto_phase68_slice5_cases import CASES, build
from _pietto_phase68_slice7_cases import manifest, case_preparation
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_execution_template import BindingError
from pietto._project.project_result_output import prepare_output


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


def _compare(artifact):
    assert artifact is not None
    reference = prepare_output(artifact)
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
    _compare_refinement(artifact)
    assert len(candidate.parameter_uses) == len(artifact.parameter_uses)
    assert all(
        new is not old
        for new, old in zip(
            candidate.request.sources, artifact.request.sources, strict=True
        )
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_original_maximum_static_limit_round_trip(tmp_path, target):
    import _pietto_phase66_sql_emission_probe as emission
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
    from _pietto_phase68_slice5_cases import seven_artifact

    original = seven_artifact(
        tmp_path / "seven-build", target, precision=precision, state=state
    )
    _compare(original)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("right_unique", (False, True))
def test_original_relationship_property_laws(tmp_path, target, right_unique):
    from _pietto_phase68_slice7_cases import planned, DIRECT
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
        from test_phase68_slice6_refinement import capabilities

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
    from _pietto_phase68_slice4_probe import template
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

        def protection(value, factors, uses):
            return (
                uses[value.introduction_use.ref],
                len(value.group_keys),
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
            protection(p, new_factors, new_uses) for p in observed.group_protections
        ) == tuple(
            protection(p, old_factors, old_uses) for p in expected.group_protections
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
    from test_phase68_slice6_refinement import capabilities
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
    from _pietto_phase68_slice6_cases import original

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


def test_retained_unselected_requests_rederive_without_execution_or_source(
    tmp_path, monkeypatch
):
    from test_phase68_slice4_binding import _proof_artifact
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project import project_execution_template

    source = _proof_artifact(tmp_path / "retained-source", retained=True).artifact
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


def test_embedded_json_depth_is_checked_before_decoder_recursion(tmp_path):
    from dataclasses import replace
    from _pietto_phase68_slice4_probe import template
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
    from _pietto_phase68_slice4_probe import template
    import _pietto_phase67_result_product_probe as product
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


def retained_unmapped_source(directory, target, variant, monkeypatch):
    from test_phase68_slice4_binding import _proof_artifact
    import _pietto_phase66_sql_emission_probe as probe

    original = probe.join_witness

    def with_unselected_source(_target, body, **options):
        selected, unused = body.split("query unused:", 1)
        relation = {
            "key": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n",
            "limit": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "global": "table unused_ranked:\n    from unused_rows\n    select:\n        id = count()\n",
            "grouped": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "window": "table unused_ranked:\n    from unused_rows\n    select:\n        id\n    limit 1\n",
            "set": "table unused_base:\n    from unused_rows\n    select:\n        id\ntable unused_union:\n    union all:\n        from unused_base\n        from unused_base\ntable unused_ranked:\n    from unused_union\n    select:\n        id\n    limit 1\n",
            "ordered": "table unused_ranked:\n    from unused_rows\n    select distinct:\n        id\n    order by:\n        id\n    limit 1\n",
        }[variant]
        unused = unused.replace("join ranked as", "join unused_ranked as")
        if variant == "grouped":
            unused = unused.replace(
                "    select:\n        value = lhs.id\n",
                "    group by:\n        lhs.id\n    select:\n        value = lhs.id\n        total = count()\n",
            )
        if variant == "window":
            unused += "    qualify:\n        row_number() window:\n            order by:\n                lhs.id\n        <= 0\n"
        body = (
            f'source unused_rows: Row is {target}.table("unused_rows")\n'
            + relation
            + selected
            + "query unused:"
            + unused
        )
        if variant == "key":
            body = body.replace(
                "source unused_rows: Row", "source unused_rows: UnusedRow"
            )
        fixture = original(target, body, **options)
        if variant == "key":
            fixture["source"] = fixture["source"].replace(
                "source lhs:",
                "shape UnusedRow:\n    id: Int not null\n    key: Int nullable\n    unique unused_id on id\nsource lhs:",
                1,
            )
        return fixture

    monkeypatch.setattr(probe, "join_witness", with_unselected_source)
    return _proof_artifact(directory, retained=True)


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
