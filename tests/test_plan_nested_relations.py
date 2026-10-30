"""CollectV1 and UnnestV1 in the SQL plan: records, closure, demands and
independent checks."""

from __future__ import annotations

from copy import copy
from dataclasses import replace

import pytest

from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_nested as nested
from pietto._project import project_sql_plan_portable as portable
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_source_maps as maps
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project import project_sql_plan_target_mapping as mapping
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.project_joined_row_filter import ProjectJoinedRowMultiplicity
from pietto._project.module_semantic_fact_preservation import _occurrence_identity
from pietto._project.project_sql_plan_results import terminal_index
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerificationIssue as Issue,
    verify_project_sql_plan,
)
from pietto.ast_nodes import AuthoredJoinKind, CollectRelationExpr, JoinClause
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
)

from _pietto_plan_nested import (
    HEAD,
    SHAPES,
    UNNEST_SHAPES,
    imported_sources,
    imported_unnest_sources,
    nested_plan,
    nested_roots,
    sources,
)

pytestmark = pytest.mark.ci_workload("general-runtime")

K = sql.ProjectSQLPlanRefKind
R = sql.ProjectSQLOriginRole
D = nested.ProjectSQLCollectionDemandKind
F = reports.ProjectSQLDemandFamily


def _graft(value, **changes):
    changed = copy(value)
    for name, item in changes.items():
        object.__setattr__(changed, name, item)
    return changed


def _files(shape):
    if shape == "imported":
        return imported_sources()
    return imported_unnest_sources() if shape == "unnest_imported" else sources(shape)


def _plan(tmp_path, shape):
    files = _files(shape)
    plan = nested_plan(tmp_path / shape, files).plan
    assert type(plan) is sql.ProjectSQLPlan
    return plan


def _definition(plan, ref):
    (value,) = (d for d in plan.bindings.definitions if d.ref is ref)
    return value


def _nested_port(port):
    return (
        port.field.evidence.resolved_type.kind
        is ProjectResolvedTypeKind.NESTED_RELATION
    )


@pytest.mark.parametrize("shape", (*SHAPES, "imported"))
def test_each_collect_read_is_one_record_projecting_its_nested_export(tmp_path, shape):
    plan = _plan(tmp_path, shape)

    uses = tuple(
        u
        for u in plan.expression_block_uses
        if type(u.expression) is CollectRelationExpr
    )
    assert len(plan.collects) == len(uses) == (2 if shape == "parallel" else 1)
    for position, (value, use) in enumerate(zip(plan.collects, uses, strict=True)):
        assert value.ref.kind is K.COLLECT and value.ref.position == position
        assert value.use is use.ref and value.producer is use.producer
        assert value.semantic.item.expression is use.expression
        assert value.fact.read is use.edge.use.evidence
        producer = _definition(plan, value.producer)
        parent = _definition(plan, use.consumer)
        export = parent.exports[value.semantic.selected_output_ordinal]
        assert value.export is export.ref
        assert export.field.evidence.resolved_type.nested is value.fact.nested_type
        assert export.field.effective_nullability is ProjectRowFieldNullability.NON_NULL
        # The children are the producer's own exports, in order: no hidden key.
        assert value.children == tuple(p.ref for p in producer.exports)
        assert value.fact.nested_type is not None
        elements = value.fact.nested_type.element_fields
        # DISTINCT and QUALIFY rebuild the producer's row at completion; its
        # exports then carry the rebuilt fields of the same outputs.
        rebuilt = shape in {"distinct_producer", "qualify_producer"}
        fields = (
            [f.field for f in getattr(producer.entry.semantic_entry, "fields")]
            if rebuilt
            else [item.field for item in elements]
        )
        assert all(
            p.field.evidence is f
            and (f is item.field) is not rebuilt
            and (f.name, f.resolved_type, f.nullability)
            == (item.field.name, item.field.resolved_type, item.field.nullability)
            for p, f, item in zip(producer.exports, fields, elements, strict=True)
        )
        assert value.fact.nested_type.element_relation == _occurrence_identity(
            producer.entry.owner
        )
        (block,) = (b for b in plan.blocks if b.ref is value.block)
        assert block.kind.value == "projection" and block.definition is parent.ref
        # A Collect read is no projection, row expression or export demand.
        assert not any(p.export is value.export for p in plan.projections)
        assert not any(getattr(e, "use", None) is value.use for e in plan.expressions)
        assert not any(
            type(d) is sql.ProjectSQLExportRepresentationDemand
            and d.subject is value.export
            for d in plan.demands
        )
    # Every nested port is a Collect export; every scalar export keeps its own
    # representation demand.
    assert {id(p.ref) for p in plan.all_exports if _nested_port(p)} == {
        id(value.export) for value in plan.collects
    }
    represented = {
        id(d.subject)
        for d in plan.demands
        if type(d) is sql.ProjectSQLExportRepresentationDemand
    }
    assert represented == {id(p.ref) for p in plan.all_exports if not _nested_port(p)}


def test_parallel_reads_are_independent_records_of_their_own_lets(tmp_path):
    plan = _plan(tmp_path, "parallel")

    first, second = plan.collects
    assert first.producer is not second.producer
    blocks = [
        _definition(plan, value.producer).entry.owner.authored_block
        for value in plan.collects
    ]
    assert [None if b is None else b.name for b in blocks] == ["a", "b"]
    assert [len(value.children) for value in plan.collects] == [1, 2]


@pytest.mark.parametrize(
    "shape", ("reader", "exists_reader", "scalar_reader", "imported")
)
def test_a_flat_reader_keeps_the_parent_collect_and_outputs_scalars(tmp_path, shape):
    plan = _plan(tmp_path, shape)

    (value,) = plan.collects
    assert not any(_nested_port(port) for port in plan.exports)
    # The closure holds the parent, its collected let and their source.
    (parent,) = (
        d
        for d in plan.bindings.definitions
        if d.entry.owner.definition.name == "parent"
        and d.entry.owner.let_position is None
    )
    assert any(p.ref is value.export for p in parent.exports)
    producer = _definition(plan, value.producer).entry.owner
    assert producer.authored_block is not None
    assert producer.authored_block.name == "children"
    assert producer.declaration_position == parent.entry.owner.declaration_position
    assert any(
        d.entry.owner.definition.name == "rows" for d in plan.bindings.definitions
    )


def test_the_imported_producer_stays_in_its_own_module(tmp_path):
    plan = _plan(tmp_path, "imported")

    (value,) = plan.collects
    producer = _definition(plan, value.producer).entry.owner
    assert producer.identity.module_path == "parent.pietto"
    assert producer.let_position == 0


def test_the_element_order_and_limit_are_the_producer_s_own(tmp_path):
    top_k = _plan(tmp_path, "top_k")
    (value,) = top_k.collects
    order = nested.collect_order(top_k, value)
    items = {i.ref: i for i in top_k.order_items}
    assert [
        (getattr(items[r].source.expression, "name"), items[r].source.direction.value)
        for r in order.items
    ] == [("created_at", "desc"), ("id", "asc")]
    limit = nested.collect_limit(top_k, value)
    assert limit is not None and limit.value == 2
    # `created_at` orders the elements but is no child field.
    assert [
        _definition(top_k, value.producer).exports[i].identity.name
        for i in range(len(value.children))
    ] == ["id", "total"]

    closed = _plan(tmp_path, "closed")
    (value,) = closed.collects
    assert nested.collect_limit(closed, value) is None
    assert len(nested.collect_order(closed, value).items) == 1


@pytest.mark.parametrize(
    ("shape", "count"), [("top_k", 1), ("staged_capture", 1), ("joined_capture", 2)]
)
def test_a_captured_read_completes_one_capture_per_line(tmp_path, shape, count):
    plan = _plan(tmp_path, shape)

    (value,) = plan.collects
    assert len(value.captures) == count == len(plan.captures)
    for ref, capture in zip(value.captures, plan.captures, strict=True):
        assert capture.ref is ref and capture.read is value.ref
        assert capture.block is value.block and capture.inner is value.producer
        assert capture.edge.checkpoint.read is _use(plan, value).edge
    closed = _plan(tmp_path, "closed")
    assert closed.collects[0].captures == () and closed.captures == ()


def test_a_joined_read_completes_each_capture_once_in_line_order(tmp_path):
    roots = nested_roots(tmp_path / "p", sources("joined_capture"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    (value,) = plan.collects
    first, second = value.captures
    for captures in (
        (first,),
        (second, first),
        (first, first),
        (*value.captures, first),
    ):
        changed = _graft(plan, collects=(_graft(value, captures=captures),))
        assert _check(roots, changed).issues == (Issue.STRUCTURE,), captures


def _use(plan, value):
    (use,) = (u for u in plan.expression_block_uses if u.ref is value.use)
    return use


def test_port_lineage_reaches_the_one_collect_or_fails(tmp_path):
    closed = _plan(tmp_path, "closed")
    (value,) = closed.collects
    assert nested.collect_of(closed, value.export) is value
    (scalar,) = (p for p in closed.exports if not _nested_port(p))
    with pytest.raises(ValueError, match="no one Collect"):
        nested.collect_of(closed, scalar.ref)

    reader = _plan(tmp_path, "reader")
    (value,) = reader.collects
    (port,) = (p for p in reader.input_ports if _nested_port(p))
    assert nested.collect_of(reader, port.ref) is value

    joined = _plan(tmp_path, "joined_parent")
    (value,) = joined.collects
    assert nested.collect_of(joined, value.export) is value
    with pytest.raises(ValueError, match="no one Collect"):
        nested.collect_of(joined, joined.join_ports[0].ref)


def test_collect_origins_and_demands_follow_values_and_precede_literals(tmp_path):
    plan = _plan(tmp_path, "top_k")
    (value,) = plan.collects

    positions = {o.ref: i for i, o in enumerate(plan.origins)}
    (original,) = (o for o in plan.origins if o.subject is value.ref)
    start = positions[original.ref]
    family = plan.origins[start : start + 5]
    assert [o.role for o in family] == [
        R.COLLECT,
        R.EXPORT,
        R.DEMAND,
        R.DEMAND,
        R.DEMAND,
    ]
    assert [o.subject for o in family[:2]] == [value.ref, value.export]
    assert original.antecedents == (
        value.block,
        value.use,
        value.producer,
        *value.captures,
    )
    assert all(o.cause is value.semantic.item for o in family)
    demands = tuple(
        d for d in plan.demands if type(d) is nested.ProjectSQLCollectionDemand
    )
    assert [(d.kind, d.subject) for d in demands] == [
        (D.COLLECT, value.ref),
        (D.COLLECT_ORDER, value.ref),
        (D.COLLECT_EXPORT, value.export),
    ]
    assert [positions[d.origin] for d in demands] == [start + 2, start + 3, start + 4]
    order = nested.collect_order(plan, value)
    limit = nested.collect_limit(plan, value)
    assert limit is not None
    by_subject = {o.subject: o.ref for o in plan.origins if o.role is not R.DEMAND}
    assert plan.origins[start + 3].antecedents == (
        original.ref,
        by_subject[order.ref],
        by_subject[limit.ref],
    )
    assert plan.origins[start + 4].antecedents == (family[1].ref,)
    # The values family ends before, and the literal family starts after.
    roles = [o.role for o in plan.origins]
    literal_roles = {R.LITERAL_SITE, R.LITERAL_SLOT, R.FIXED_LITERAL_VALUE, R.BIND_USE}
    assert all(role not in literal_roles for role in roles[:start])
    assert all(
        o.role in literal_roles or o.role is R.DEMAND for o in plan.origins[start + 5 :]
    )


@pytest.mark.parametrize(
    "shape", ("closed", "top_k", "joined_capture", "reader", "unnest_left")
)
def test_reports_maps_and_assessments_cover_the_collection_family(tmp_path, shape):
    verification = nested_plan(tmp_path / shape, sources(shape))
    plan = verification.plan
    assert type(plan) is sql.ProjectSQLPlan

    report = reports.build_project_sql_requirement_report(verification)
    checked = reports.verify_project_sql_requirement_report(report, verification)
    assert checked.verified, checked.issues
    collection = report.indexes.by_family[F.COLLECTION]
    assert len(collection) == 3 * len(plan.collects) + 2 * len(plan.unnests) > 0
    source_map = maps.build_project_sql_source_map(verification)
    assert maps.verify_project_sql_source_map(source_map, verification).verified
    for family, release in (("postgresql", "18.6"), ("mysql", "8.4.12")):
        request = targets.prepare_project_sql_target_request(
            CapabilityProfileTarget(
                CapabilityProfileTargetKind.DATABASE, family, release
            )
        )
        product = targets.build_project_sql_target_assessment(
            verification, request, report_verification=checked
        )
        assert targets.verify_project_sql_target_assessment(
            product, verification, request
        ).verified
        for demand in product.demands:
            evidence = mapping.type_evidence(demand.entry.demand)
            resolved = getattr(evidence, "resolved_type", evidence)
            nested_evidence = (
                getattr(resolved, "kind", None)
                is ProjectResolvedTypeKind.NESTED_RELATION
            )
            if demand.entry.family is F.COLLECTION:
                # A residual original requirement, never a capability key.
                assert [
                    (a.proposition.key, a.proposition.gap) for a in demand.aspects
                ] == [(None, mapping.MappingGap.COLLECTION)]
            elif nested_evidence:
                assert all(a.proposition.key is None for a in demand.aspects)


@pytest.mark.parametrize("shape", ("closed", "unnest_cross"))
def test_the_phase65_observation_refuses_a_nested_plan(tmp_path, shape):
    verification = nested_plan(tmp_path / "p", sources(shape))

    with pytest.raises(portable.TransportError) as raised:
        portable.build_project_sql_plan_portable(verification)
    assert raised.value.issue is portable.RuntimeIssue.UNSUPPORTED_VALUE


def test_a_flat_phase65_observation_encodes_no_collection_report(tmp_path):
    body = "query result:\n    from rows\n    select id\n"
    files = {"main.pietto": HEAD.format(target="postgres") + body}
    product = portable.build_project_sql_plan_portable(
        nested_plan(tmp_path / "p", files)
    )

    encoded = [
        value.family
        for _, value in product.bindings
        if type(value) is reports.ProjectSQLDemandFamilyReport
    ]
    assert encoded == [family for family in F if family is not F.COLLECTION]
    assert b"collection" not in product.canonical_bytes


def _check(roots, plan):
    return verify_project_sql_plan(plan, *roots)


def test_every_supplied_collect_record_is_checked_independently(tmp_path):
    roots = nested_roots(tmp_path / "parallel", sources("parallel"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    first, second = plan.collects
    foreign = _plan(tmp_path, "closed").collects[0]
    other = _definition(plan, second.producer)
    (scalar,) = (p for p in plan.exports if not _nested_port(p))
    collects = {
        "deleted": (first,),
        "duplicated": (first, first, second),
        "swapped": (second, first),
        "foreign": (foreign, second),
        "other-children": (
            _graft(first, children=tuple(p.ref for p in other.exports)),
            second,
        ),
        "truncated-children": (_graft(second, children=second.children[:1]), first),
        "swapped-children": (
            first,
            _graft(second, children=second.children[::-1]),
        ),
        "scalar-export": (_graft(first, export=scalar.ref), second),
        "other-use": (_graft(first, use=second.use), second),
        "other-fact": (_graft(first, fact=second.fact), second),
    }
    for name, values in collects.items():
        checked = _check(roots, _graft(plan, collects=values))
        assert checked.issues == (Issue.STRUCTURE,), name


def test_a_rebuilt_producer_field_is_its_element_by_identity_and_type(tmp_path):
    roots = nested_roots(tmp_path / "p", sources("distinct_producer"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    (value,) = plan.collects
    assert value.fact.nested_type is not None
    (element,) = value.fact.nested_type.element_fields
    (export,) = (p for p in plan.all_exports if p.ref is value.export)
    forged = (
        ("identity", replace(element.identity, name="other")),
        (
            "field",
            replace(element.field, nullability=ProjectRowFieldNullability.NULLABLE),
        ),
        (
            "field",
            replace(element.field, resolved_type=export.field.evidence.resolved_type),
        ),
    )
    for name, item in forged:
        original = getattr(element, name)
        object.__setattr__(element, name, item)
        try:
            assert _check(roots, plan).issues == (Issue.STRUCTURE,), name
        finally:
            object.__setattr__(element, name, original)
    assert _check(roots, plan).verified


def test_a_collect_reading_an_exists_block_use_is_refused(tmp_path):
    files = sources("closed")
    files["main.pietto"] = files["main.pietto"].replace(
        "    from rows\n    select:\n        id\n        nested",
        "    from rows\n    where exists children\n    select:\n        id\n        nested",
    )
    roots = nested_roots(tmp_path / "p", files)
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    (value,) = plan.collects
    (exists,) = (
        u
        for u in plan.expression_block_uses
        if type(u.expression) is not CollectRelationExpr
    )
    checked = _check(roots, _graft(plan, collects=(_graft(value, use=exists.ref),)))
    assert checked.issues == (Issue.STRUCTURE,)


def test_captures_projections_demands_and_origins_are_exclusive(tmp_path):
    roots = nested_roots(tmp_path / "top_k", sources("top_k"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    (value,) = plan.collects
    (capture,) = plan.captures
    for collect in (_graft(value, captures=()), _graft(value, captures=(value.ref,))):
        checked = _check(roots, _graft(plan, collects=(collect,)))
        assert checked.issues == (Issue.STRUCTURE,)
    # A capture completed by anything but its Collect read is refused.
    checked = _check(
        roots, _graft(plan, captures=(_graft(capture, read=plan.expressions[0].ref),))
    )
    assert not checked.verified

    # A ProjectSQLProjection of the nested export is refused.
    (projection,) = (
        p for p in plan.projections if any(p.export is e.ref for e in plan.exports)
    )
    extra = _graft(projection, export=value.export)
    checked = _check(roots, _graft(plan, projections=(*plan.projections, extra)))
    assert not checked.verified

    demands = list(plan.demands)
    positions = [
        i for i, d in enumerate(demands) if type(d) is nested.ProjectSQLCollectionDemand
    ]
    swapped = list(demands)
    swapped[positions[0]], swapped[positions[1]] = (
        swapped[positions[1]],
        swapped[positions[0]],
    )
    deleted = [d for i, d in enumerate(demands) if i != positions[2]]
    for changed in (swapped, deleted):
        checked = _check(roots, _graft(plan, demands=tuple(changed)))
        assert checked.issues == (Issue.DEMANDS,)

    origins = list(plan.origins)
    (position,) = (i for i, o in enumerate(origins) if o.subject is value.ref)
    origins[position] = _graft(origins[position], role=R.PROJECTION)
    checked = _check(roots, _graft(plan, origins=tuple(origins)))
    assert checked.issues == (Issue.ORIGINS,)


def test_an_export_representation_of_a_nested_port_is_refused(tmp_path):
    roots = nested_roots(tmp_path / "p", sources("closed"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan
    (value,) = plan.collects
    bindings = plan.bindings
    (port,) = (p for p in bindings.all_exports if p.ref is value.export)
    template = next(
        d
        for d in bindings.demands
        if type(d) is sql.ProjectSQLExportRepresentationDemand
    )
    extra = _graft(
        template,
        subject=port.ref,
        field=port.field,
        logical_type=port.field.evidence.resolved_type,
        nullability=port.field.effective_nullability,
    )
    changed = _graft(bindings, demands=(*bindings.demands, extra))
    checked = _check(roots, _graft(plan, bindings=changed))
    assert checked.issues and not checked.verified


def test_the_producer_order_is_the_one_its_own_boundary_owns(tmp_path):
    roots = nested_roots(tmp_path / "p", sources("parallel"))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan
    first, second = plan.orders
    checked = _check(roots, _graft(plan, orders=(second, first)))
    assert not checked.verified
    checked = _check(roots, _graft(plan, orders=(first,)))
    assert not checked.verified


# --- UnnestV1 (S06-U, U1-U6) ---

_ROWS = {
    AuthoredJoinKind.CROSS: "cartesian_pairs",
    AuthoredJoinKind.INNER: "matched_pairs",
    AuthoredJoinKind.LEFT: "left_preserved",
}
# Each shape's Unnest JOINs, in JOIN order: (kind, its JOIN's position in its
# body, the source binding's position).
_UNNEST_JOINS = {
    "unnest_cross": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_inner": [(AuthoredJoinKind.INNER, 0, 0)],
    "unnest_left": [(AuthoredJoinKind.LEFT, 0, 0)],
    "unnest_left_where": [(AuthoredJoinKind.LEFT, 0, 0)],
    "unnest_left_on_parent": [(AuthoredJoinKind.LEFT, 0, 0)],
    "unnest_left_on_match": [(AuthoredJoinKind.LEFT, 0, 0)],
    "unnest_ordered": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_alias": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_left_joined_parent": [(AuthoredJoinKind.LEFT, 1, 1)],
    "unnest_join_binding": [(AuthoredJoinKind.CROSS, 1, 1)],
    "unnest_cross_joined_parent": [(AuthoredJoinKind.CROSS, 1, 1)],
    "unnest_beside_series": [(AuthoredJoinKind.CROSS, 1, 1)],
    "unnest_captured_exists": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_two_bodies": [(AuthoredJoinKind.CROSS, 0, 0)] * 2,
    "unnest_imported": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_language": [(AuthoredJoinKind.CROSS, 0, 0)],
    "unnest_inner_nullable": [(AuthoredJoinKind.INNER, 0, 0)],
}


def _by_ref(values):
    return {value.ref: value for value in values}


@pytest.mark.parametrize("shape", _UNNEST_JOINS)
def test_each_unnest_is_the_right_input_of_one_join_in_join_order(tmp_path, shape):
    assert set(_UNNEST_JOINS) == {*UNNEST_SHAPES, "unnest_imported"}
    plan = _plan(tmp_path, shape)
    language = shape == "unnest_language"

    joins, inputs, ports = (
        _by_ref(plan.joins),
        _by_ref(plan.join_inputs),
        _by_ref(plan.join_ports),
    )
    expected = _UNNEST_JOINS[shape]
    assert len(plan.unnests) == len(expected)
    occurrences = [
        d for d in plan.bindings.definitions if d.entry.owner.unnest is not None
    ]
    assert len(occurrences) == len(expected)
    order = [j.ref for j in plan.joins]
    assert [order.index(u.join) for u in plan.unnests] == sorted(
        order.index(u.join) for u in plan.unnests
    )
    for position, (value, (kind, join_position, binding)) in enumerate(
        zip(plan.unnests, expected, strict=True)
    ):
        join = joins[value.join]
        left, right = (inputs[ref] for ref in join.inputs)
        definition = _definition(plan, value.definition)
        semantic = value.semantic
        assert value.ref.kind is K.UNNEST and value.ref.position == position
        # U1: the occurrence is the producer of the JOIN's right input.
        assert (join.kind, join.position) == (kind, join_position)
        assert join.rows.value == _ROWS[kind]
        assert value.input is right.ref and right.ordinal == 1
        assert right.producer is value.definition and definition in occurrences
        assert definition.entry.owner.unnest is semantic.query_let
        assert semantic.source_binding_position == binding
        # U2: the source port carries the nested field its Collect outputs.
        source = ports[value.source]
        assert source.input is left.ref
        assert source.field.evidence.name == ("recent_orders" if language else "nested")
        assert source.field.evidence.resolved_type.nested is semantic.nested_type
        (collect,) = (c for c in plan.collects if c.ref is value.collect)
        assert collect.fact is semantic.collect_read
        assert nested.collect_of(plan, value.source) is collect
        # U3, U4: the element fields, nulled by a LEFT JOIN only; an INNER
        # JOIN's own `on` narrows the nullable `other` it compares.
        assert semantic.nested_type is not None
        elements = semantic.nested_type.element_fields
        assert value.outputs == join.outputs[len(left.ports) :]
        outputs = [ports[ref] for ref in value.outputs]
        assert [p.field.evidence.name for p in outputs] == (
            ["id"]
            if language
            else ["id", "other"]
            if shape == "unnest_inner_nullable"
            else ["id", "total"]
        )
        left_join = kind is AuthoredJoinKind.LEFT
        for port, element in zip(outputs, elements, strict=True):
            assert port.field.evidence is element.field
            assert port.field.effective_nullability is (
                ProjectRowFieldNullability.NULLABLE
                if left_join
                else ProjectRowFieldNullability.NON_NULL
            )
            assert any(ref is join.source.node.ref for ref in port.nulling) is (
                left_join
            )
        # U5: a bag without keys, dependencies, order or bound; the JOIN
        # output has no key.
        properties = definition.entry.active_properties
        assert properties.multiplicity is ProjectJoinedRowMultiplicity.BAG
        assert properties.relational.keys == () == properties.relational.fds
        assert properties.ordering is None and properties.cardinality is None
        assert join.properties.keys == ()
        # Its rows are its JOIN's: no VALUES body, block, projection or
        # result port; its exports are their own terminals.
        assert not any(b.definition is definition.ref for b in plan.values_bodies)
        assert not any(b.definition is definition.ref for b in plan.blocks)
        assert not any(p.definition is definition.ref for p in plan.result_ports)
        terminals = terminal_index(plan)
        assert all(terminals[p.ref] is p for p in definition.exports)


def test_unnest_origins_and_demands_follow_the_collect_family(tmp_path):
    plan = _plan(tmp_path, "unnest_left")
    (collect,) = plan.collects
    (value,) = plan.unnests

    positions = {o.ref: i for i, o in enumerate(plan.origins)}
    (original,) = (o for o in plan.origins if o.subject is value.ref)
    start = positions[original.ref]
    (collected,) = (o for o in plan.origins if o.subject is collect.ref)
    # Every Collect family comes first: five origins per Collect read.
    assert start == positions[collected.ref] + 5
    family = plan.origins[start : start + 3]
    assert [o.role for o in family] == [R.UNNEST, R.DEMAND, R.DEMAND]
    (join,) = (j for j in plan.joins if j.ref is value.join)
    clause = join.source.condition.use.clause
    assert type(clause) is JoinClause and clause.target_binding_name == "o"
    assert all(o.cause is clause and o.evidence is value for o in family)
    assert original.antecedents == (
        value.join,
        value.input,
        value.definition,
        value.source,
        value.collect,
    )
    demands = [
        d
        for d in plan.demands
        if type(d) is nested.ProjectSQLCollectionDemand and d.witness is value
    ]
    assert [(d.kind, d.subject) for d in demands] == [
        (D.UNNEST_ROWS, value.ref),
        (D.UNNEST_SOURCE, value.ref),
    ]
    assert [positions[d.origin] for d in demands] == [start + 1, start + 2]
    assert [o.provenance.value for o in family] == [
        "membership",
        "membership",
        "type_proof",
    ]
    assert family[1].antecedents == (original.ref,)
    assert family[2].antecedents == (original.ref, collected.ref)
    literal_roles = {R.LITERAL_SITE, R.LITERAL_SLOT, R.FIXED_LITERAL_VALUE, R.BIND_USE}
    assert all(
        o.role in literal_roles or o.role is R.DEMAND for o in plan.origins[start + 3 :]
    )


def test_the_source_map_places_an_unnest_at_its_join_and_let(tmp_path):
    verification = nested_plan(tmp_path / "p", sources("unnest_cross"))
    plan = verification.plan
    assert type(plan) is sql.ProjectSQLPlan
    source_map = maps.build_project_sql_source_map(verification)
    assert maps.verify_project_sql_source_map(source_map, verification).verified
    (value,) = plan.unnests

    def located(subject, role):
        (entry,) = (
            e
            for e in source_map.entries
            if e.original.subject is subject and e.original.role is role
        )
        return [
            (a.kind.value, a.site.location.line, a.site.location.column)
            for a in source_map.indexes.associations[entry.ref]
        ]

    # The UNNEST is its JOIN's own syntax; the occurrence is its let's.
    assert located(value.ref, R.UNNEST) == [("authored_cause", 25, 5)]
    assert located(value.definition, R.DEFINITION) == [("authored_cause", 24, 5)]


@pytest.mark.parametrize(
    "shape", ("unnest_beside_series", "unnest_two_bodies", "unnest_captured_exists")
)
def test_an_unnest_occurrence_has_its_own_coordinates(tmp_path, shape):
    plan = _plan(tmp_path, shape)

    owners = [d.entry.owner for d in plan.bindings.definitions]
    keys = [sql._owner_key(owner) for owner in owners]
    assert len(set(keys)) == len(keys)
    for value in plan.unnests:
        occurrence = _definition(plan, value.definition).entry.owner
        (join,) = (j for j in plan.joins if j.ref is value.join)
        declaration = _definition(plan, join.definition).entry.owner
        # The occurrence shares its body's positions and only those.
        assert sql._owner_key(occurrence)[:3] == sql._owner_key(declaration)[:3]
        assert sql._owner_key(occurrence)[4] == occurrence.unnest_position == 0
        assert sql._owner_key(declaration)[4] == -1
    index = sql._origin_index(plan.scope)
    assert len(index) == len(set(index))
    local = [key for key in index if key[1] == -1]
    unnests = [key for key in local if key[5] != -1]
    assert len(unnests) == len(plan.unnests)
    assert {key[:5] for key in unnests} <= {key[:5] for key in local if key[5] == -1}


def _unnest_check(tmp_path, shape):
    roots = nested_roots(tmp_path / shape, sources(shape))
    plan = sql.build_project_sql_plan(*roots)
    assert type(plan) is sql.ProjectSQLPlan and _check(roots, plan).verified
    return roots, plan


def test_every_supplied_unnest_record_is_checked_independently(tmp_path):
    roots, plan = _unnest_check(tmp_path, "unnest_two_bodies")
    first, second = plan.unnests
    foreign = _plan(tmp_path, "unnest_cross").unnests[0]
    ports = _by_ref(plan.join_ports)
    (join,) = (j for j in plan.joins if j.ref is first.join)
    left = next(i for i in plan.join_inputs if i.ref is join.inputs[0])
    scalar = next(p for p in left.ports if p is not first.source)
    (other_collect,) = plan.collects
    changed = {
        "deleted": (first,),
        "duplicated": (first, first, second),
        "swapped": (second, first),
        "foreign": (foreign, second),
        "other-join": (_graft(first, join=second.join), second),
        "other-input": (_graft(first, input=join.inputs[0]), second),
        "other-definition": (_graft(first, definition=second.definition), second),
        "scalar-source": (_graft(first, source=scalar), second),
        "other-collect": (_graft(first, collect=first.ref), second),
        "truncated-outputs": (_graft(first, outputs=first.outputs[:1]), second),
        "swapped-outputs": (_graft(first, outputs=first.outputs[::-1]), second),
        "left-outputs": (
            _graft(first, outputs=join.outputs[: len(first.outputs)]),
            second,
        ),
        "other-semantic": (_graft(first, semantic=second.semantic), second),
    }
    assert ports[scalar].field.evidence.name == "id"
    assert other_collect.ref is first.collect is second.collect
    for name, values in changed.items():
        checked = _check(roots, _graft(plan, unnests=values))
        assert checked.issues == (Issue.STRUCTURE,), name


def test_an_inner_unnest_narrows_only_the_elements_its_on_proves(tmp_path):
    roots, plan = _unnest_check(tmp_path, "unnest_inner_nullable")
    (value,) = plan.unnests
    (join,) = (j for j in plan.joins if j.ref is value.join)
    ports = _by_ref(plan.join_ports)
    assert value.semantic.nested_type is not None
    (_, other) = value.semantic.nested_type.element_fields
    assert other.field.nullability is ProjectRowFieldNullability.NULLABLE
    assert ports[value.outputs[1]].field.effective_nullability is (
        ProjectRowFieldNullability.NON_NULL
    )
    # Without the `on` proof the narrowed element is no longer its own.
    condition = join.source.source.condition
    proofs = condition.null_rejections
    assert proofs
    object.__setattr__(condition, "null_rejections", ())
    try:
        assert _check(roots, plan).issues == (Issue.STRUCTURE,)
    finally:
        object.__setattr__(condition, "null_rejections", proofs)
    assert _check(roots, plan).verified


def test_an_unnest_demand_or_origin_out_of_place_is_refused(tmp_path):
    roots, plan = _unnest_check(tmp_path, "unnest_cross")
    (value,) = plan.unnests

    demands = list(plan.demands)
    positions = [
        i
        for i, d in enumerate(demands)
        if type(d) is nested.ProjectSQLCollectionDemand and d.witness is value
    ]
    swapped = list(demands)
    swapped[positions[0]], swapped[positions[1]] = (
        swapped[positions[1]],
        swapped[positions[0]],
    )
    deleted = [d for i, d in enumerate(demands) if i != positions[1]]
    for changed in (swapped, deleted):
        checked = _check(roots, _graft(plan, demands=tuple(changed)))
        assert checked.issues == (Issue.DEMANDS,)

    origins = list(plan.origins)
    (position,) = (i for i, o in enumerate(origins) if o.subject is value.ref)
    for role in (R.JOIN, R.COLLECT):
        changed = list(origins)
        changed[position] = _graft(origins[position], role=role)
        checked = _check(roots, _graft(plan, origins=tuple(changed)))
        assert checked.issues == (Issue.ORIGINS,), role


def test_an_unnest_read_by_another_input_use_is_refused(tmp_path):
    roots, plan = _unnest_check(tmp_path, "unnest_cross")
    (value,) = plan.unnests
    (join,) = (j for j in plan.joins if j.ref is value.join)
    right = next(i for i in plan.join_inputs if i.ref is value.input)
    # The JOIN's own binding is the only input use of an Unnest's rows.
    changed = _graft(right, binding_use=None)
    inputs = tuple(changed if i is right else i for i in plan.join_inputs)
    checked = _check(roots, _graft(plan, join_inputs=inputs))
    assert not checked.verified
    assert join.inputs[1] is right.ref
