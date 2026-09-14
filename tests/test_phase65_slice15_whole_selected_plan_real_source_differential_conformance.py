"""Whole-plan conformance witnesses retained at their first failing boundary."""

from copy import copy
from dataclasses import replace
import json
import sys

import pytest

from _pietto_phase65_sql_plan_differential_probe import (
    construction,
    assessment,
    CONTROL,
    _field,
    _record,
    _change,
)
from pietto.ast_nodes import BinaryExpr, LiteralExpr, TableDef
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_portable as portable
from pietto._project import project_sql_plan_portable_schema as schema
from pietto._project import project_sql_plan_pure_boundary as pure
from pietto._project import project_sql_plan_requirements as reports


LITERAL_ANCESTRY_SOURCE = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        value = id + 1
"""


@pytest.mark.parametrize("retain_leaf", (False, True), ids=("all-contexts", "ancestor"))
def test_literal_ancestry_cannot_disagree_with_retained_report_links(
    tmp_path, retain_leaf
):
    verified = construction(
        tmp_path / "project",
        LITERAL_ANCESTRY_SOURCE,
        literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    assert verified.completed.ok and verified.verified
    assert len(plan.literal_slots) == len(plan.bind_uses) == 1
    (demand,) = tuple(
        d for d in plan.demands if type(d) is literals.ProjectSQLLiteralDemand
    )
    ancestor, leaf = demand.contexts
    assert type(ancestor.expression) is BinaryExpr
    assert ancestor.expression.operator == "+"
    assert ancestor.expression.right is leaf.expression
    assert type(leaf.expression) is LiteralExpr
    assert type(leaf.expression.value) is int and leaf.expression.value == 1
    assert demand.use.slot.site.position.literal is leaf.expression

    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    original = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert original.status is pure.Status.OK
    assert original.document == product.document
    assert original.canonical_bytes == product.canonical_bytes
    report = product.context.report.report
    assert len(report.links) == 2
    assert tuple(link.kind.value for link in report.links) == (
        "literal_ancestor_context",
        "literal_ancestor_context",
    )
    assert all(link.source.demand is demand for link in report.links)
    assert tuple(link.target.demand for link in report.links) == (ancestor, leaf)

    (ref,) = tuple(ref for ref, value in product.bindings if value is demand)
    (record,) = tuple(r for r in product.document.records if r.ref == ref)
    assert record.kind == "project_sql_literal_demand"
    (field,) = tuple(f for f in record.fields if f.name == "contexts")
    assert field.value.tag is schema.Tag.SEQUENCE
    assert isinstance(field.value.data, tuple) and len(field.value.data) == 2
    expected_refs = tuple(
        schema.Value(schema.Tag.REF, ref)
        for context in (ancestor, leaf)
        for ref, value in product.bindings
        if value is context
    )
    assert field.value.data == expected_refs
    changed = replace(
        record,
        fields=tuple(
            replace(
                f,
                value=schema.Value(
                    schema.Tag.SEQUENCE, field.value.data[1:] if retain_leaf else ()
                ),
            )
            if f is field
            else f
            for f in record.fields
        ),
    )
    document = replace(
        product.document,
        records=tuple(changed if r is record else r for r in product.document.records),
    )
    assert changed != record and changed.ref == record.ref
    assert all(
        new is old if old is not record else new is changed
        for old, new in zip(product.document.records, document.records, strict=True)
    )
    # The expression, ancestry, demand and both report links remain declared.
    # This is an internal contradiction, independent of source authentication.
    outcome = pure.evaluate_project_sql_plan_document(document)
    graft = copy(product)
    object.__setattr__(graft, "document", document)
    assert not portable._corresponds(graft)
    assert portable.verify_project_sql_plan_portable(graft, verified).issues == (
        portable.RuntimeIssue.CORRESPONDENCE,
    )
    assert outcome.status is pure.Status.INVALID_RELATION, (
        "Literal context removal retained its authoritative report links, "
        f"but pure checking returned {outcome.status.value}."
    )
    assert outcome.canonical_bytes is None


def _relation_product(
    path, source, policy=literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
):
    verified = construction(path, source, policy)
    supplied = assessment(verified)
    report = reports.build_project_sql_requirement_report(verified)
    checked = reports.verify_project_sql_requirement_report(report, verified)
    assert checked.verified
    product = portable.build_project_sql_plan_portable(
        verified, report=checked, assessment=supplied
    )
    assert report is not supplied.assessment.report
    assert portable.verify_project_sql_plan_portable(
        product, verified, assessment=supplied
    ).verified
    return verified, product


@pytest.fixture(scope="module")
def nested_literals(tmp_path_factory):
    source = LITERAL_ANCESTRY_SOURCE.replace(
        "value = id + 1",
        "first = (id + 1) * (2 + 3)\n        second = (id + 1) * (2 + 3)",
    )
    verified, product = _relation_product(
        tmp_path_factory.mktemp("nested") / "project", source
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    demands = tuple(
        d for d in plan.demands if type(d) is literals.ProjectSQLLiteralDemand
    )
    assert len(demands) == len(plan.literal_slots) == len(plan.bind_uses) == 6
    assert [d.value.value for d in demands] == [1, 2, 3, 1, 2, 3]
    assert all(len(d.contexts) == 3 for d in demands)
    assert demands[0].contexts[0].site is not demands[3].contexts[0].site
    return verified, product, demands


def _reject_changed(product, record, name, replacement):
    assert _field(record, name) != replacement
    document = _change(product.document, record, name, replacement)
    changed = tuple(r for r in document.records if r.ref == record.ref)
    assert len(changed) == 1 and _field(changed[0], name) == replacement
    outcome = pure.evaluate_project_sql_plan_document(document)
    assert outcome.status is pure.Status.INVALID_RELATION
    assert outcome.canonical_bytes is None


@pytest.mark.parametrize(
    "mutation", ("empty", "missing_leaf", "reverse", "duplicate", "foreign_context")
)
def test_contexts_are_complete_ordered_and_local(nested_literals, mutation):
    _, product, demands = nested_literals
    record = _record(product, demands[0])
    contexts = _field(record, "contexts").data
    assert isinstance(contexts, tuple) and len(contexts) == 3
    foreign = _field(_record(product, demands[3]), "contexts").data
    assert isinstance(foreign, tuple) and len(foreign) == 3
    replacement = {
        "empty": (),
        "missing_leaf": contexts[:-1],
        "reverse": tuple(reversed(contexts)),
        "duplicate": (contexts[0], contexts[0], contexts[2]),
        "foreign_context": (foreign[0], *contexts[1:]),
    }[mutation]
    _reject_changed(
        product, record, "contexts", schema.Value(schema.Tag.SEQUENCE, replacement)
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "empty",
        "shortened",
        "reversed",
        "wrong_operand",
        "negative_operand",
        "foreign_parent",
        "malformed_step",
    ),
)
def test_ancestry_connects_its_actual_context_root_to_the_bound_leaf(
    nested_literals, mutation
):
    _, product, demands = nested_literals
    record = _record(product, demands[0].use.slot.site.position)
    ancestry = _field(record, "ancestry").data
    assert isinstance(ancestry, tuple) and len(ancestry) == 2
    first = ancestry[0].data
    assert isinstance(first, tuple) and len(first) == 2
    assert first[1] == schema.Value(schema.Tag.INTEGER, "0")
    foreign = _field(
        _record(product, demands[3].use.slot.site.position), "ancestry"
    ).data
    assert isinstance(foreign, tuple)
    replacement = {
        "empty": (),
        "shortened": ancestry[1:],
        "reversed": tuple(reversed(ancestry)),
        "wrong_operand": (
            schema.Value(
                schema.Tag.SEQUENCE, (first[0], schema.Value(schema.Tag.INTEGER, "1"))
            ),
            ancestry[1],
        ),
        "negative_operand": (
            schema.Value(
                schema.Tag.SEQUENCE, (first[0], schema.Value(schema.Tag.INTEGER, "-1"))
            ),
            ancestry[1],
        ),
        "foreign_parent": (foreign[0], ancestry[1]),
        "malformed_step": (schema.Value(schema.Tag.SEQUENCE, first[:1]), ancestry[1]),
    }[mutation]
    _reject_changed(
        product, record, "ancestry", schema.Value(schema.Tag.SEQUENCE, replacement)
    )


@pytest.mark.parametrize("report_number", (0, 1))
@pytest.mark.parametrize(
    "mutation",
    (
        "missing",
        "duplicate",
        "reverse",
        "wrong_position",
        "swapped_target",
        "foreign_target",
        "foreign_source",
        "wrong_kind",
    ),
)
def test_literal_links_use_each_reports_own_ordered_entries(
    nested_literals, report_number, mutation
):
    _, product, demands = nested_literals
    supplied = product.context.assessment
    assert supplied is not None
    report_pair = (product.context.report.report, supplied.assessment.report)
    report, other = report_pair[report_number], report_pair[1 - report_number]
    assert set(map(id, report.entries)).isdisjoint(map(id, other.entries))
    assert tuple(e.demand for e in report.entries) == tuple(
        e.demand for e in other.entries
    )
    links = tuple(link for link in report.links if link.source.demand is demands[0])
    assert len(links) == 3
    assert tuple(link.target.demand for link in links) == demands[0].contexts
    record = _record(product, report)
    values = _field(record, "links").data
    assert isinstance(values, tuple) and len(values) == 18
    if mutation in ("missing", "duplicate", "reverse"):
        replacement = {
            "missing": values[1:],
            "duplicate": (values[0], *values),
            "reverse": tuple(reversed(values)),
        }[mutation]
        _reject_changed(
            product, record, "links", schema.Value(schema.Tag.SEQUENCE, replacement)
        )
        return
    record = _record(product, links[0])
    (foreign_target,) = tuple(
        e for e in other.entries if e.demand is demands[0].contexts[0]
    )
    (foreign_source,) = tuple(e for e in other.entries if e.demand is demands[0])
    name, replacement = {
        "wrong_position": ("position", schema.Value(schema.Tag.INTEGER, "1")),
        "swapped_target": (
            "target",
            schema.Value(schema.Tag.REF, _record(product, links[1].target).ref),
        ),
        "foreign_target": (
            "target",
            schema.Value(schema.Tag.REF, _record(product, foreign_target).ref),
        ),
        "foreign_source": (
            "source",
            schema.Value(schema.Tag.REF, _record(product, foreign_source).ref),
        ),
        "wrong_kind": (
            "kind",
            schema.Value(schema.Tag.ENUM, "single_match_root_proof"),
        ),
    }[mutation]
    _reject_changed(product, record, name, replacement)


def test_removing_contexts_and_all_their_links_still_contradicts_ancestry(tmp_path):
    verified = construction(
        tmp_path / "project",
        LITERAL_ANCESTRY_SOURCE,
        literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
    )
    product = portable.build_project_sql_plan_portable(verified)
    (demand,) = tuple(
        d
        for d in product.context.report.report.entries
        if d.family is reports.ProjectSQLDemandFamily.LITERAL
    )
    original = demand.demand
    assert isinstance(original, literals.ProjectSQLLiteralDemand)
    assert (
        len(original.contexts) == 2
        and len(original.use.slot.site.position.ancestry) == 1
    )
    empty = schema.Value(schema.Tag.SEQUENCE, ())
    document = _change(product.document, _record(product, original), "contexts", empty)
    document = _change(
        document, _record(product, product.context.report.report), "links", empty
    )
    document = replace(
        document,
        records=tuple(
            r for r in document.records if r.kind != "project_sql_demand_link"
        ),
    )
    outcome = pure.evaluate_project_sql_plan_document(document)
    assert (
        outcome.status is pure.Status.INVALID_RELATION
        and outcome.canonical_bytes is None
    )


@pytest.mark.parametrize(
    "case,expected_contexts",
    (("direct", (1,)), ("shared", (1,)), ("preserve", ()), ("no_bound", ())),
)
def test_zero_ancestry_shared_producers_and_empty_bound_inventories(
    tmp_path, case, expected_contexts
):
    shared = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
table shared:
    from rows
    let:
        one = 1
    select:
        one
query result:
    union all:
        from shared
        from shared
"""
    source = {
        "direct": LITERAL_ANCESTRY_SOURCE.replace("id + 1", "1"),
        "shared": shared,
        "preserve": LITERAL_ANCESTRY_SOURCE,
        "no_bound": CONTROL,
    }[case]
    policy = (
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS
        if case == "preserve"
        else literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
    )
    verified, product = _relation_product(tmp_path / "project", source, policy)
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    demands = tuple(
        d for d in plan.demands if type(d) is literals.ProjectSQLLiteralDemand
    )
    assert tuple(len(d.contexts) for d in demands) == expected_contexts
    assert len(plan.literal_slots) == len(plan.bind_uses) == len(demands)
    if case == "shared":
        assert len(plan.bindings.definitions) == 3 and len(plan.input_uses) == 3
        assert len(demands[0].use.slot.site.position.ancestry) == 0
    outcome = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert outcome.status is pure.Status.OK and outcome.document == product.document


def test_pure_literal_repair_never_calls_runtime_helpers_or_encoding(
    nested_literals, monkeypatch
):
    _, product, _ = nested_literals

    def forbidden(*args, **kwargs):
        pytest.fail("Pure checking called a runtime producer or verifier")

    for module, name in (
        (literals, "demand_contexts"),
        (reports, "build_project_sql_requirement_report"),
        (reports, "verify_project_sql_requirement_report"),
        (portable, "_encode_context"),
        (portable, "verify_project_sql_plan_portable"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    outcome = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert (
        outcome.status is pure.Status.OK
        and outcome.canonical_bytes == product.canonical_bytes
    )


def test_literal_link_positions_include_original_root_and_child_proof_links(tmp_path):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots,
        _path_source,
        _path_requests,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    source = _path_source(all_unique=True)
    assert source.endswith("        id = lhs.id\n")
    roots = _roots(tmp_path, source + "        flag = 1\n", _path_requests)
    policy = literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
    plan = build_project_sql_plan(*roots, literal_policy=policy)
    assert isinstance(plan, ProjectSQLPlan)
    verified = verify_project_sql_plan(plan, *roots, literal_policy=policy)
    assert verified.verified
    product = portable.build_project_sql_plan_portable(verified)
    report = product.context.report.report
    kinds = tuple(link.kind.value for link in report.links)
    assert set(kinds) == {
        "literal_ancestor_context",
        "single_match_root_proof",
        "single_match_child_proof",
    }
    (link,) = tuple(
        link for link in report.links if link.kind.value == "literal_ancestor_context"
    )
    assert link.position == len(report.links) - 1 and link.position > 0
    assert (
        pure.evaluate_project_sql_plan_document(product.document).status
        is pure.Status.OK
    )
    _reject_changed(
        product,
        _record(product, link),
        "position",
        schema.Value(schema.Tag.INTEGER, "0"),
    )


def test_right_global_fixture_requires_the_existing_joined_producer(tmp_path):
    from _pietto_phase65_sql_plan_differential_probe import CORPUS, REQUEST_MODES

    ((_, source, policy),) = tuple(
        case for case in CORPUS if case[0] == "proof_right_global"
    )
    verified = construction(
        tmp_path / "project",
        source,
        policy,
        requests=REQUEST_MODES["proof_right_global"],
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    assert [join.kind.value for join in plan.joins] == ["inner", "semi"]
    (obligation,) = plan.single_matches
    assert obligation.assessment.state.value == "proved"
    assert obligation.request.owner is verified.selected_owner
    assert not obligation.downstream_enforcement_required
    (proof,) = plan.single_match_proofs
    assert proof.source.source.kind.value == "right_global"
    assert proof.source.premise_nodes and len(plan.aggregations) == 1
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    assert (
        pure.parse_project_sql_plan_document(product.canonical_bytes).status
        is pure.Status.OK
    )


@pytest.mark.parametrize("policy", tuple(literals.ProjectSQLLiteralPolicy))
def test_named_ordered_producer_has_complete_portable_property_evidence(
    tmp_path, policy
):
    from pietto._project.project_ir_properties import (
        ProjectIRPropertyStage,
        ProjectIRProvidedRelationOrdering,
    )
    from pietto._project import project_sql_plan_source_maps as maps

    source = (
        CONTROL.replace("query result:", "table ordered:")
        + """    order by:
        id
query result:
    from ordered
    select:
        id
"""
    )
    verified = construction(tmp_path / "project", source, policy)
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    assert verified.completed.ok and verified.verified
    assert [d.entry.owner.definition.name for d in plan.bindings.definitions] == [
        "rows",
        "ordered",
        "result",
    ]
    assert len(plan.input_uses) == 2 and not plan.literal_slots
    (boundary,) = tuple(
        b for b in plan.result_boundaries if b.kind.value == "relation_ordering"
    )
    assert isinstance(boundary.properties, ProjectIRPropertyStage)
    (ordering,) = tuple(
        p
        for p in boundary.properties.provided
        if type(p) is ProjectIRProvidedRelationOrdering
    )
    assert len(ordering.items) == 1
    definition = ordering.evidence.owner.definition
    assert isinstance(definition, TableDef)
    assert definition.name == "ordered" and definition.order_by_clause is not None
    assert ordering.items is definition.order_by_clause.items
    report = reports.build_project_sql_requirement_report(verified)
    report_check = reports.verify_project_sql_requirement_report(report, verified)
    source_map = maps.build_project_sql_source_map(verified)
    map_check = maps.verify_project_sql_source_map(source_map, verified)
    assert report_check.verified and map_check.verified
    # The original F65S15-02 positive witness stays on the normal encode path.
    product = portable.build_project_sql_plan_portable(
        verified, report=report_check, source_map=map_check
    )
    assert sum(value is ordering for _, value in product.bindings) == 1
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    outcome = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert outcome.status is pure.Status.OK and outcome.document == product.document
    record = _record(product, ordering)
    assert record.kind == "project_ir_provided_relation_ordering"
    assert tuple(f.name for f in record.fields) == ("output", "evidence", "items")
    assert _field(record, "output") == schema.Value(
        schema.Tag.REF, _record(product, ordering.output).ref
    )
    assert _field(record, "evidence") == schema.Value(
        schema.Tag.REF, _record(product, ordering.evidence).ref
    )
    assert _field(record, "items") == schema.Value(
        schema.Tag.SEQUENCE,
        tuple(
            schema.Value(schema.Tag.REF, _record(product, item).ref)
            for item in ordering.items
        ),
    )
    assert pure.Inspection(outcome).record(record.ref) == record


ORDERING_PAIR = """shape Row:
    id: Int not null
    other: Int nullable
source rows: Row is postgres.table("rows")
table first:
    from rows
    select:
        id
        other
    order by:
        id desc
        other
    limit 1
table second:
    from rows
    select:
        id
        other
    order by:
        other asc
        id desc
    limit 1
query result:
    from first
    cross join second as r:
        from first
    select:
        first_id = first.id
        second_id = r.id
"""


def _provided_at(plan, name, kind):
    from pietto._project.project_ir_properties import (
        ProjectIRPropertyStage,
        ProjectIRProvidedRelationOrdering,
    )

    (definition,) = tuple(
        d for d in plan.bindings.definitions if d.entry.owner.definition.name == name
    )
    (boundary,) = tuple(
        b
        for b in plan.result_boundaries
        if b.definition is definition.ref and b.kind.value == kind
    )
    assert isinstance(boundary.properties, ProjectIRPropertyStage)
    (provided,) = tuple(
        p
        for p in boundary.properties.provided
        if type(p) is ProjectIRProvidedRelationOrdering
        and p.output.occurrence.producer is boundary.operator.node
    )
    return boundary, provided


@pytest.fixture(scope="module")
def ordering_pair(tmp_path_factory):
    verified = construction(
        tmp_path_factory.mktemp("ordering-pair") / "project",
        ORDERING_PAIR,
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    first, first_order = _provided_at(plan, "first", "relation_ordering")
    first_limit, limited_order = _provided_at(plan, "first", "limit")
    second, second_order = _provided_at(plan, "second", "relation_ordering")
    assert (
        first.properties is first_limit.properties
        and first.properties is not second.properties
    )
    assert (
        first_order is not limited_order
        and first_order.output is not limited_order.output
    )
    assert first_order.items is limited_order.items
    assert tuple(item.direction for item in first_order.items) == ("desc", None)
    assert tuple(item.direction for item in second_order.items) == ("asc", "desc")
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    return (
        verified,
        product,
        first,
        first_order,
        first_limit,
        limited_order,
        second,
        second_order,
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_items",
        "duplicate_items",
        "reversed_items",
        "foreign_items",
        "foreign_output",
        "same_owner_output",
        "foreign_evidence",
    ),
)
def test_provided_ordering_fields_preserve_exact_output_evidence_and_items(
    ordering_pair, mutation
):
    _, product, _, first, _, limited, _, second = ordering_pair
    record = _record(product, first)
    items = _field(record, "items").data
    assert isinstance(items, tuple) and len(items) == 2
    field, replacement = {
        "missing_items": ("items", schema.Value(schema.Tag.SEQUENCE, ())),
        "duplicate_items": (
            "items",
            schema.Value(schema.Tag.SEQUENCE, (items[0], items[0])),
        ),
        "reversed_items": (
            "items",
            schema.Value(schema.Tag.SEQUENCE, tuple(reversed(items))),
        ),
        "foreign_items": ("items", _field(_record(product, second), "items")),
        "foreign_output": (
            "output",
            schema.Value(schema.Tag.REF, _record(product, second.output).ref),
        ),
        "same_owner_output": (
            "output",
            schema.Value(schema.Tag.REF, _record(product, limited.output).ref),
        ),
        "foreign_evidence": (
            "evidence",
            schema.Value(schema.Tag.REF, _record(product, second.evidence).ref),
        ),
    }[mutation]
    _reject_changed(product, record, field, replacement)


def test_provided_ordering_requires_its_authored_clause_and_property_inventory(
    ordering_pair,
):
    verified, product, first_boundary, first, _, _, second_boundary, second = (
        ordering_pair
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    (first_order,) = tuple(o for o in plan.orders if o.boundary is first_boundary.ref)
    (second_order,) = tuple(o for o in plan.orders if o.boundary is second_boundary.ref)
    assert first_order.source.owner is first.evidence.owner
    _reject_changed(
        product,
        _record(product, first_order.source),
        "clause",
        schema.Value(schema.Tag.REF, _record(product, second_order.source.clause).ref),
    )
    first_stage = _record(product, first_boundary.properties)
    second_stage = _record(product, second_boundary.properties)
    first_items = _field(first_stage, "provided").data
    second_items = _field(second_stage, "provided").data
    assert isinstance(first_items, tuple) and isinstance(second_items, tuple)
    first_ref = schema.Value(schema.Tag.REF, _record(product, first).ref)
    second_ref = schema.Value(schema.Tag.REF, _record(product, second).ref)
    assert first_items.count(first_ref) == second_items.count(second_ref) == 1
    document = _change(
        product.document,
        first_stage,
        "provided",
        schema.Value(
            schema.Tag.SEQUENCE,
            tuple(second_ref if v == first_ref else v for v in first_items),
        ),
    )
    document = _change(
        document,
        second_stage,
        "provided",
        schema.Value(
            schema.Tag.SEQUENCE,
            tuple(first_ref if v == second_ref else v for v in second_items),
        ),
    )
    assert len(document.records) == len(product.document.records)
    outcome = pure.evaluate_project_sql_plan_document(document)
    assert (
        outcome.status is pure.Status.INVALID_RELATION
        and outcome.canonical_bytes is None
    )


@pytest.mark.parametrize("field", ("output", "evidence", "items"))
def test_provided_ordering_schema_rejects_missing_and_wrong_kind_fields(
    ordering_pair, field
):
    _, product, _, first, _, _, _, _ = ordering_pair
    record = _record(product, first)
    missing = replace(record, fields=tuple(f for f in record.fields if f.name != field))
    document = replace(
        product.document,
        records=tuple(missing if r is record else r for r in product.document.records),
    )
    outcome = pure.evaluate_project_sql_plan_document(document)
    assert (
        outcome.status is pure.Status.INVALID_FIELD and outcome.canonical_bytes is None
    )
    # A valid record of a different domain is not an output, evidence or item.
    wrong = schema.Value(schema.Tag.REF, _record(product, first).ref)
    if field == "items":
        wrong = schema.Value(schema.Tag.SEQUENCE, (wrong,))
    document = _change(product.document, record, field, wrong)
    outcome = pure.evaluate_project_sql_plan_document(document)
    assert outcome.status is pure.Status.INVALID_REF and outcome.canonical_bytes is None
    assert outcome.record_position == product.document.records.index(record)
    assert outcome.field_position == ("output", "evidence", "items").index(field)


@pytest.mark.parametrize("member", ("carrier", "output", "evidence", "item"))
def test_provided_ordering_same_looking_runtime_grafts_are_not_document_authenticity(
    ordering_pair, member, monkeypatch
):
    verified, product, _, first, _, _, _, _ = ordering_pair
    original = {
        "carrier": first,
        "output": first.output,
        "evidence": first.evidence,
        "item": first.items[0],
    }[member]
    foreign = copy(original)
    assert foreign is not original and portable._fields(foreign) == portable._fields(
        original
    )
    graft = copy(product)
    object.__setattr__(
        graft,
        "bindings",
        tuple(
            (ref, foreign if value is original else value)
            for ref, value in product.bindings
        ),
    )
    assert (
        pure.evaluate_project_sql_plan_document(graft.document).status is pure.Status.OK
    )
    monkeypatch.setattr(
        portable,
        "_encode_context",
        lambda *_: pytest.fail("Correspondence called encoder"),
    )
    assert not portable._corresponds(graft)
    assert portable.verify_project_sql_plan_portable(graft, verified).issues == (
        portable.RuntimeIssue.CORRESPONDENCE,
    )


def test_provided_ordering_rebound_and_completed_ordering_keep_distinct_routes(
    tmp_path,
):
    from _pietto_phase65_sql_plan_differential_probe import MIXED_QUALIFY, join_source
    from pietto._project.project_query_block_ir import (
        ProjectIRReboundExistingOutput,
        ProjectIRQueryBlockResultProperties,
    )
    from pietto._project.project_ir_properties import ProjectIRProvidedRelationOrdering

    source = (
        MIXED_QUALIFY.replace("query result:", "table upstream:")
        + "query result:\n    from upstream\n    select:\n        id\n    order by:\n        id\n    limit 1\n"
    )
    verified = construction(
        tmp_path / "rebound", source, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    assert isinstance(
        plan.bindings.definitions[-1].entry, ProjectIRReboundExistingOutput
    )
    boundary, limited = plan.result_boundaries
    assert boundary.kind.value == "relation_ordering" and limited.kind.value == "limit"
    assert isinstance(boundary.properties, ProjectIRQueryBlockResultProperties)
    assert isinstance(limited.properties, ProjectIRQueryBlockResultProperties)
    ordering = boundary.properties.ordering
    preserved = limited.properties.ordering
    assert isinstance(ordering, ProjectIRProvidedRelationOrdering)
    assert isinstance(preserved, ProjectIRProvidedRelationOrdering)
    assert ordering is not preserved and ordering.items is preserved.items
    product = portable.build_project_sql_plan_portable(verified)
    assert _record(product, ordering).kind == "project_ir_provided_relation_ordering"
    assert (
        pure.parse_project_sql_plan_document(product.canonical_bytes).status
        is pure.Status.OK
    )
    _reject_changed(
        product,
        _record(product, ordering),
        "output",
        schema.Value(schema.Tag.REF, _record(product, preserved.output).ref),
    )

    completed_source = (
        join_source("cross").replace("query result:", "table upstream:")
        + "query result:\n    from upstream\n    select:\n        id\n    order by:\n        id\n"
    )
    other = construction(
        tmp_path / "completed",
        completed_source,
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    )
    completed_product = portable.build_project_sql_plan_portable(other)
    assert not pure.Inspection(
        pure.parse_project_sql_plan_document(completed_product.canonical_bytes)
    ).for_kind("project_ir_provided_relation_ordering")
    assert pure.Inspection(
        pure.parse_project_sql_plan_document(completed_product.canonical_bytes)
    ).for_kind("project_relation_ordering")


@pytest.mark.parametrize(
    "case", ("limit_before_filter", "filter_before_limit", "limit_only")
)
def test_original_limit_filter_barriers_complete_the_portable_vertical(tmp_path, case):
    from _pietto_phase65_sql_plan_differential_probe import (
        CORPUS,
        LIMIT_HEAD,
        LIMIT_CONSUMER,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    if case == "limit_only":
        source = LIMIT_HEAD.replace("    order by:\n        id\n", "") + LIMIT_CONSUMER
        policy = literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
    else:
        ((_, source, policy),) = tuple(c for c in CORPUS if c[0] == case)
    verified = construction(tmp_path / "project", source, policy)
    view = inspect_project_sql_plan(verified)
    stages = tuple(
        tuple(stage.kind.value for stage in view.result_stages(d.ref))
        for d in view.definitions[1:]
    )
    assert (
        stages
        == {
            "limit_before_filter": (
                ("projection", "relation_ordering", "limit"),
                ("where", "projection"),
            ),
            "filter_before_limit": (
                ("where", "projection", "relation_ordering", "limit"),
                ("projection",),
            ),
            "limit_only": (("projection", "limit"), ("where", "projection")),
        }[case]
    )
    assert view.definitions[-1].entry.active_properties.ordering is None
    product = portable.build_project_sql_plan_portable(verified)
    assert portable.verify_project_sql_plan_portable(product, verified).verified
    parsed = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert (
        parsed.status is pure.Status.OK
        and parsed.canonical_bytes == product.canonical_bytes
    )


def test_provided_ordering_pure_check_has_no_runtime_dependency(
    ordering_pair, monkeypatch
):
    from pietto._project.project_ir_properties import ProjectIRProvidedRelationOrdering
    from pietto._project import project_ir_construction

    _, product, _, _, _, _, _, _ = ordering_pair

    def forbidden(*args, **kwargs):
        pytest.fail("Pure ORDER check called runtime construction/correspondence")

    monkeypatch.setattr(ProjectIRProvidedRelationOrdering, "__post_init__", forbidden)
    monkeypatch.setattr(project_ir_construction, "_row_properties", forbidden)
    monkeypatch.setattr(portable, "_encode_context", forbidden)
    monkeypatch.setattr(portable, "_corresponds", forbidden)
    outcome = pure.parse_project_sql_plan_document(product.canonical_bytes)
    assert (
        outcome.status is pure.Status.OK
        and outcome.canonical_bytes == product.canonical_bytes
    )


# Independent authored-fixture expectations, not generated from the probe registry.
# exports, block stages, JOIN kinds, aggregate modes, windows/visibility, SET forms, slots
CASE_SHAPES = {
    "minimal": ("id", "projection", "", "", "", "", 0),
    "bound": (
        "added flag floating negative_zero text large",
        "let where projection",
        "",
        "",
        "",
        "",
        7,
    ),
    "shared_set": ("id", "projection", "", "", "", "union:all except:distinct", 0),
    "staged": (
        "total w",
        "aggregate satisfying window qualify projection",
        "",
        "grouped",
        "rank:1",
        "",
        0,
    ),
    "hidden_order": ("value", "projection", "", "", "", "", 0),
    "row_shared": (
        "n z f t flag huge first again",
        "let let let let where projection",
        "",
        "",
        "",
        "",
        17,
    ),
    "table_mysql": ("id", "projection", "", "", "", "", 0),
    "imported_reexport": (
        "first repeated second third",
        "projection projection projection",
        "cross cross cross",
        "",
        "",
        "",
        0,
    ),
    "join_cross": ("id", "projection", "cross", "", "", "", 0),
    "join_right": ("id", "projection", "right", "", "", "", 1),
    "join_semi": ("id", "projection", "semi", "", "", "", 1),
    "join_anti": ("id", "projection", "anti", "", "", "", 0),
    "join_refinement": ("id", "where projection", "inner", "", "", "", 2),
    "join_accumulated": ("id", "projection", "left full", "", "", "", 0),
    "proof_right_limit": ("id", "projection projection", "inner", "", "", "", 1),
    "proof_right_global": (
        "id",
        "aggregate projection projection",
        "inner semi",
        "global",
        "",
        "",
        0,
    ),
    "path_complete": ("id", "projection", "inner inner", "", "", "", 0),
    "path_partial": ("id", "projection", "inner inner", "", "", "", 0),
    "global_empty": (
        "rows fields total",
        "where aggregate projection",
        "",
        "global",
        "",
        "",
        0,
    ),
    "group_hidden": ("total", "aggregate projection", "left", "grouped", "", "", 0),
    "group_partial": (
        "left_id total",
        "aggregate projection",
        "left",
        "grouped",
        "",
        "",
        0,
    ),
    "grouped_satisfying": (
        "total",
        "let let where aggregate satisfying projection",
        "",
        "grouped",
        "",
        "",
        2,
    ),
    "aggregate_risks": (
        "row_count field_count distinct_labels total average minimum maximum repeated_total",
        "let let where aggregate satisfying projection",
        "left",
        "grouped",
        "",
        "",
        0,
    ),
    "window_rank_navigation": (
        "id numbered ranked dense percent distribution bucket previous following",
        "window projection",
        "",
        "",
        "row_number:1 rank:1 dense_rank:1 percent_rank:1 cume_dist:1 ntile:1 lag:1 lead:1",
        "",
        0,
    ),
    "window_value_named": (
        "id first again last nth",
        "window projection",
        "",
        "",
        "first_value:1 last_value:1 last_value:1 nth_value:1",
        "",
        0,
    ),
    "mixed_qualify": (
        "id w",
        "window qualify projection",
        "",
        "",
        "row_number:1 row_number:0",
        "",
        0,
    ),
    "hidden_distinct": (
        "constant",
        "window qualify projection",
        "",
        "",
        "lag:0",
        "",
        1,
    ),
    "set_forms": (
        "id",
        "",
        "",
        "",
        "",
        "union:distinct intersect:all intersect:distinct except:all except:distinct",
        0,
    ),
    "set_float": ("id", "", "", "", "", "union:all", 0),
    "sharing_depth12": (
        "id",
        "projection projection",
        "",
        "",
        "",
        " ".join(("union:all",) * 12),
        1,
    ),
    "limit_before_filter": ("id", "projection where projection", "", "", "", "", 1),
    "filter_before_limit": ("id", "where projection projection", "", "", "", "", 1),
    "target_omitted": ("id", "projection", "", "", "", "", 0),
    "target_applicable": ("id", "projection", "", "", "", "", 0),
    "target_mismatch": ("id", "projection", "", "", "", "", 0),
    "target_conflict": ("id", "projection", "", "", "", "", 0),
    "target_residual": ("id", "projection", "", "", "", "", 0),
}
BOUND_CASES = {
    "bound",
    "row_shared",
    "imported_reexport",
    "join_right",
    "join_semi",
    "join_refinement",
    "proof_right_limit",
    "path_partial",
    "group_partial",
    "grouped_satisfying",
    "window_rank_navigation",
    "mixed_qualify",
    "hidden_distinct",
    "set_float",
    "sharing_depth12",
    "limit_before_filter",
    "filter_before_limit",
}
MUTATION_CASES = {
    "minimal": (
        "terminal_export_missing",
        "external_producer_missing",
        "generated_marked_authored",
        "coherent_alternative",
    ),
    "bound": (
        "literal_contexts_missing",
        "literal_ancestry_shortened",
        "literal_report_target_swapped",
        "fixed_int_altered",
        "fixed_int_as_bool",
        "fixed_int_as_float",
        "stale_envelope",
    ),
    "row_shared": ("cross_report_literal_target",),
    "imported_reexport": ("same_looking_producer_graft",),
    "join_right": ("join_nulling_rows_changed",),
    "join_semi": ("right_match_membership_missing",),
    "join_anti": ("right_match_membership_missing",),
    "global_empty": ("global_empty_row_lost",),
    "group_hidden": ("hidden_group_export_leak",),
    "aggregate_risks": ("retained_aggregate_risks_missing",),
    "hidden_distinct": ("hidden_window_export_leak", "qualify_window_missing"),
    "shared_set": ("except_right_membership_missing", "visible_order_proof_missing"),
    "set_forms": ("decimal_parent_missing", "set_operands_swapped"),
    "hidden_order": ("hidden_order_proof_missing",),
    "proof_right_limit": ("producer_proof_premise_missing",),
    "proof_right_global": ("producer_proof_premise_missing",),
    "path_complete": ("whole_path_child_missing",),
    "sharing_depth12": ("repeated_use_missing",),
    "window_value_named": ("effective_window_marked_authored",),
    "limit_before_filter": ("provided_order_items_missing",),
    "target_omitted": ("false_target_completion",),
    "target_applicable": ("false_target_completion", "target_residuals_missing"),
    "target_mismatch": ("false_target_completion", "false_profile_applicability"),
    "target_conflict": ("false_target_completion", "conflicting_fact_missing"),
    "target_residual": ("false_target_completion", "catalog_residual_missing"),
}


@pytest.fixture(scope="module")
def acquired_observation(tmp_path_factory):
    import _pietto_differential_process_acquisition as process

    store = process.acquisition(tmp_path_factory)
    documents = store.documents("phase65")
    key = f"source:python{sys.version_info.major}.{sys.version_info.minor}:seed:0"
    assert key in documents
    baseline = documents[key]
    assert all(raw == baseline for raw in documents.values())
    observed = json.loads(baseline)
    assert observed["format"] == "pietto.phase65-sql-plan-differential.v1"
    return store, observed


def _document_tables(case):
    outcome = pure.parse_project_sql_plan_document(case["document"])
    assert outcome.status is pure.Status.OK and outcome.document is not None
    assert outcome.canonical_bytes == case["document"].encode()
    records = {record.ref: record for record in outcome.document.records}
    data = {
        ref: {f.name: pure._data(f.value) for f in record.fields}
        for ref, record in records.items()
    }
    (plan_ref,) = tuple(
        ref for ref, record in records.items() if record.kind == "project_sql_plan"
    )
    return records, data, data[plan_ref]


def test_registered_corpus_has_independent_field_identity_and_role_expectations(
    acquired_observation,
):
    _, observed = acquired_observation
    assert [c["case"] for c in observed["cases"]] == list(CASE_SHAPES)
    all_joins, all_windows, all_sets = set(), set(), set()
    for case in observed["cases"]:
        name = case["case"]
        exports, blocks, joins, aggregations, windows, sets, slots = CASE_SHAPES[name]
        records, data, plan = _document_tables(case)
        summary = case["summary"]
        owner = data[plan["scope"]]["selected_owner"]
        definition = data[owner]["definition"]
        assert data[definition]["name"] == "result"
        assert records[definition].kind == (
            "table_def"
            if name == "table_mysql"
            else "set_relation_def"
            if name in ("shared_set", "set_forms", "set_float")
            else "query_def"
        )
        assert (
            plan["literal_policy"]
            == ("bind_safe_literals" if name in BOUND_CASES else "preserve_literals")
            == summary["policy"]
        )
        identities = tuple(data[data[ref]["identity"]] for ref in plan["exports"])
        assert [i["name"] for i in identities] == exports.split() == summary["exports"]
        assert [int(i["field_position"]) for i in identities] == list(
            range(len(identities))
        )
        assert all(i["kind"] == "relation_output" for i in identities)
        assert all(
            (
                data[i["owner"]]["module_position"],
                data[i["owner"]]["declaration_position"],
            )
            == (data[owner]["module_position"], data[owner]["declaration_position"])
            for i in identities
        )
        assert (
            [data[r]["kind"] for r in plan["blocks"]]
            == blocks.split()
            == summary["blocks"]
        )
        assert (
            [data[r]["kind"] for r in plan["joins"]]
            == joins.split()
            == summary["joins"]
        )
        assert [data[r]["mode"] for r in plan["aggregations"]] == aggregations.split()
        assert (
            [
                [data[data[r]["function"]]["name"], data[r]["selected"] is not None]
                for r in plan["windows"]
            ]
            == [[word.split(":")[0], word.endswith(":1")] for word in windows.split()]
            == summary["windows"]
        )
        actual_sets = [
            (data[r]["kind"], data[r]["quantifier"]) for r in plan["set_bodies"]
        ]
        assert actual_sets == [tuple(word.split(":")) for word in sets.split()]
        assert (
            len(plan["literal_slots"])
            == len(plan["bind_uses"])
            == slots
            == len(summary["values"])
        )
        assert (
            case["rejection"] == "invalid_document"
            and case["cross_snapshot"] == "invalid_runtime_request"
        )
        bindings = data[plan["bindings"]]
        definitions = {data[r]["ref"]: data[r] for r in bindings["definitions"]}
        assert len(definitions) == len(bindings["definitions"])
        for ref in plan["input_uses"]:
            use = data[ref]
            producer = definitions[use["producer"]]
            assert use["consumer"] in definitions and use["consumer"] != use["producer"]
            assert tuple(data[p]["producer_port"] for p in use["ports"]) == tuple(
                data[p]["ref"] for p in producer["exports"]
            )
            assert all(data[p]["owner"] == use["ref"] for p in use["ports"])
        (root,) = tuple(
            data[r] for r, record in records.items() if record.kind == "observation"
        )
        report = data[root["report"]]
        assert tuple(data[r]["demand"] for r in report["entries"]) == plan["demands"]
        assert [data[r]["family"] for r in report["entries"]] == summary[
            "demand_families"
        ]
        assert (
            tuple(data[r]["original"] for r in data[root["source_map"]]["entries"])
            == plan["origins"]
        )
        all_joins.update(joins.split())
        all_windows.update(w.split(":")[0] for w in windows.split())
        all_sets.update(actual_sets)
    assert all_joins == {"inner", "left", "cross", "right", "full", "semi", "anti"}
    assert all_windows == {
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
    }
    assert all_sets == {
        (kind, quantifier)
        for kind in ("union", "intersect", "except")
        for quantifier in ("all", "distinct")
    }


def test_registered_corpus_retains_proofs_risks_targets_and_hidden_visibility(
    acquired_observation,
):
    _, observed = acquired_observation
    cases = {c["case"]: c for c in observed["cases"]}
    for name, states in {
        "join_right": ["legal_unproved"],
        "join_semi": ["legal_unproved"],
        "join_anti": ["legal_unproved"],
        "join_refinement": ["proved"],
        "proof_right_limit": ["proved"],
        "proof_right_global": ["proved"],
        "path_complete": ["proved", "proved", "proved"],
        "path_partial": ["proved", "legal_unproved", "legal_unproved"],
    }.items():
        matches = cases[name]["summary"]["matches"]
        assert [m[1] for m in matches] == states
        assert [m[2] for m in matches] == [s == "legal_unproved" for s in states]
    for name in ("path_complete", "path_partial"):
        matches = cases[name]["summary"]["matches"]
        assert [m[0] for m in matches] == ["path_hop", "path_hop", "whole_path"]
        assert [m[3] for m in matches] == [1, 1, 2]
    assert "right_limit" in cases["proof_right_limit"]["summary"]["proofs"]
    assert "right_global" in cases["proof_right_global"]["summary"]["proofs"]
    assert cases["hidden_order"]["summary"]["hidden_order"] == 1
    assert cases["aggregate_risks"]["summary"]["risks"]
    assert cases["global_empty"]["summary"]["aggregations"] == [
        ["global", "one_global_row", 0]
    ]
    assert cases["global_empty"]["summary"]["aggregates"] == [
        [0, "Int", "non_null"],
        [1, "Int", "non_null"],
        [1, "Int", "nullable"],
    ]
    for name in ("group_hidden", "group_partial"):
        assert cases[name]["summary"]["aggregations"] == [["grouped", "no_groups", 2]]
    assert cases["sharing_depth12"]["summary"]["definitions"] == [
        "rows",
        *(f"p{i}" for i in range(13)),
        "result",
    ]
    assert cases["sharing_depth12"]["summary"]["uses"] == 26
    assert cases["sharing_depth12"]["summary"]["values"] == [["Int", "17"]]
    assert cases["table_mysql"]["summary"]["sources"] == [
        ["rows", ["mysql", "table"], "rows"]
    ]
    imported = cases["imported_reexport"]["summary"]
    assert (
        imported["definitions"].count("shared") == 2
        and imported["definitions"].count("rows") == 2
    )
    assert {tuple(s[1]) for s in imported["sources"]} == {
        ("postgres", "table"),
        ("mysql", "table"),
    }
    for name in ("hidden_distinct", "shared_set", "hidden_order"):
        _, data, plan = _document_tables(cases[name])
        boundaries = {data[r]["ref"]: data[r] for r in plan["result_boundaries"]}
        definitions = {
            data[r]["ref"]: data[r] for r in data[plan["bindings"]]["definitions"]
        }
        quotients = {data[r]["ref"]: data[r] for r in plan["quotient_fields"]}
        for ref in plan["distincts"]:
            distinct = data[ref]
            definition = definitions[boundaries[distinct["boundary"]]["definition"]]
            assert (
                tuple(quotients[q]["canonical"] for q in distinct["fields"])
                == definition["exports"]
            )
    for name in (
        "target_omitted",
        "target_applicable",
        "target_mismatch",
        "target_conflict",
        "target_residual",
    ):
        target = cases[name]["summary"]["target"]
        assert target["posture"] == (
            "not_assessed"
            if name == "target_omitted"
            else "incomplete_requirement_assessment"
        )
        assert target["pending"] > 0
    assert cases["target_omitted"]["summary"]["target"]["applicability"] == []
    assert not any(cases["target_mismatch"]["summary"]["target"]["applicability"])
    assert (
        dict(cases["target_conflict"]["summary"]["target"]["categories"])[
            "conflicting_facts"
        ]
        > 0
    )
    assert (
        dict(cases["target_applicable"]["summary"]["target"]["categories"])[
            "satisfied_exact_subproposition"
        ]
        > 0
    )
    assert cases["target_residual"]["summary"]["target"]["catalog_residuals"] == 1


def test_registered_mutations_and_source_negatives_have_exact_distinct_outcomes(
    acquired_observation,
):
    _, observed = acquired_observation
    for case in observed["cases"]:
        assert tuple(m["name"] for m in case["mutations"]) == MUTATION_CASES.get(
            case["case"], ()
        )
        for mutation in case["mutations"]:
            expected = (
                ("runtime", "invalid_runtime_request")
                if mutation["name"] == "stale_envelope"
                else ("correspondence", "runtime_document_correspondence")
                if mutation["name"] == "coherent_alternative"
                else ("pure", "invalid_relation")
            )
            assert (mutation["boundary"], mutation["status"]) == expected
            assert mutation["canonical_bytes"] is None
            assert mutation["record_position"] is mutation["field_position"] is None
            if mutation["name"] == "coherent_alternative":
                assert mutation["pure_status"] == "ok"
    expected = {
        "connector": (
            "semantic",
            ["PIE-S2306"],
            ["semantic_result_unsuccessful", "static_source_unavailable"],
        ),
        "unrelated_error": (
            "semantic",
            ["PIE-S2306"],
            ["semantic_result_unsuccessful"],
        ),
        "general_call": ("planning", [], ["call_authority_unavailable"]),
        "order_evidence": ("planning", [], ["order"]),
        "float_distinct": (
            "semantic",
            ["PIE-S2339"],
            ["semantic_result_unsuccessful", "active_output_unavailable"],
        ),
        "float_set": (
            "semantic",
            ["PIE-S2344", "PIE-S2344", "PIE-S2334"],
            ["semantic_result_unsuccessful", "active_output_unavailable"],
        ),
        "set_group": (
            "semantic",
            ["PIE-S2333"],
            ["semantic_result_unsuccessful", "active_output_unavailable", "group"],
        ),
        "set_global": (
            "semantic",
            ["PIE-S2333"],
            ["semantic_result_unsuccessful", "active_output_unavailable"],
        ),
        "global_satisfying": (
            "semantic",
            ["PIE-S2333"],
            ["semantic_result_unsuccessful", "active_output_unavailable", "satisfying"],
        ),
        "qualify_without_window": (
            "semantic",
            ["PIE-S2331"],
            ["semantic_result_unsuccessful", "active_output_unavailable"],
        ),
        "global_window": (
            "semantic",
            ["PIE-S2333"],
            ["semantic_result_unsuccessful", "active_output_unavailable"],
        ),
    }
    assert [n["case"] for n in observed["source_negatives"]] == list(expected)
    for negative in observed["source_negatives"]:
        boundary, codes, blockers = expected[negative["case"]]
        assert negative["boundary"] == boundary and negative["blockers"] == blockers
        assert negative["diagnostics"] == [[code, "error"] for code in codes]
        assert negative["status"] == (
            "error" if boundary == "semantic" else "unavailable"
        )
        assert negative["canonical_bytes"] is None
    assert [(r["name"], r["status"]) for r in observed["raw_rejections"]] == [
        ("duplicate_key", "duplicate_key"),
        ("invalid_utf8", "invalid_utf8"),
        ("nonfinite_number", "invalid_value"),
        ("negative_zero_ref", "invalid_value"),
        ("unknown_format", "unknown_format"),
        ("unknown_record", "invalid_record"),
        ("unknown_envelope_field", "invalid_document"),
        ("unknown_record_field", "invalid_field"),
        ("wrong_ref_domain_coordinates", "invalid_ref"),
        ("input_bytes_limit", "resource_limit"),
        ("input_depth_limit", "resource_limit"),
    ]
    assert all(r["canonical_bytes"] is None for r in observed["raw_rejections"])
    for rejection in observed["raw_rejections"]:
        assert (rejection["record_position"], rejection["field_position"]) == (
            (0, 0)
            if rejection["name"] == "wrong_ref_domain_coordinates"
            else (None, None)
        )


def test_registered_portable_join_group_window_set_and_profile_relationships(
    acquired_observation,
):
    _, observed = acquired_observation
    cases = {c["case"]: c for c in observed["cases"]}
    records, data, plan = _document_tables(cases["row_shared"])
    (envelope,) = tuple(
        data[r]
        for r, record in records.items()
        if record.kind == "project_sql_fixed_envelope"
    )
    values = [data[r] for r in envelope["values"]]
    assert [(v["tag"], v["value"]) for v in values] == [
        ("Int", "1"),
        ("Float", "0x1.0000000000000p+0"),
        ("Bool", True),
        ("Text", "text"),
        ("Bool", True),
        ("Int", "1"),
        ("Int", "1"),
        ("Float", "0x1.0000000000000p+0"),
        ("Float", "0x0.0p+0"),
        ("Text", "x"),
        ("Text", "x"),
        ("Int", "3"),
        ("Float", "0x0.0p+0"),
        ("Float", "0x1.4000000000000p+0"),
        ("Text", "é\n😀"),
        ("Bool", False),
        ("Int", "123456789012345678901234567890123456789"),
    ]
    assert tuple(v["slot"] for v in values) == plan["literal_slots"]
    slots = [data[r] for r in plan["literal_slots"]]
    positions = [data[data[s["site"]]["position"]] for s in slots]
    equal_slots = [slots[i] for i in (0, 5, 6)]
    assert (
        len({s["ref"] for s in equal_slots})
        == len({s["site"] for s in equal_slots})
        == 3
    )
    assert len({positions[i]["literal"] for i in (0, 5, 6)}) == 3
    assert [positions[i]["role"] for i in (0, 5, 6)] == ["let", "where", "where"]
    assert tuple(data[r]["slot"] for r in plan["bind_uses"]) == plan["literal_slots"]
    assert len({data[r]["expression"] for r in plan["bind_uses"]}) == 17
    stage_ports = {data[r]["ref"]: data[r] for r in plan["stage_ports"]}
    let_a = data[plan["let_values"][0]]
    references = [
        data[r]
        for r, record in records.items()
        if record.kind == "project_sql_reference"
    ]
    assert len(references) == len({r["expression"] for r in references}) == 2
    assert references[0]["port"] == references[1]["port"]
    binding = stage_ports[let_a["port"]]["key"]
    for reference in references:
        assert data[reference["reference"]]["let_candidates"] == (binding,)
        port = reference["port"]
        while port != let_a["port"]:
            assert stage_ports[port]["key"] == binding
            port = stage_ports[port]["source"]
    assert let_a["expression"] == data[plan["bind_uses"][0]]["expression"]
    for index in (11, 12):
        ((parent, ordinal),) = positions[index]["ancestry"]
        assert ordinal == "0" and data[parent]["operator"] == "-"
        assert data[parent]["operand"] == positions[index]["literal"]
    unicode_span = data[data[positions[14]["literal"]]["span"]]
    assert unicode_span["line"] == unicode_span["end_line"]
    assert (
        int(unicode_span["end_column"]) - int(unicode_span["column"])
        == len('"é\\n😀"')
        == 6
    )

    records, data, plan = _document_tables(cases["imported_reexport"])
    definitions = {
        data[r]["ref"]: data[r] for r in data[plan["bindings"]]["definitions"]
    }
    (root,) = tuple(
        data[r] for r, record in records.items() if record.kind == "observation"
    )
    mapped = data[root["source_map"]]
    shared = tuple(
        (ref, d)
        for ref, d in definitions.items()
        if data[data[data[d["entry"]]["owner"]]["definition"]]["name"] == "shared"
    )
    assert len(shared) == 2 and shared[0][0] != shared[1][0]
    usage = {}
    for ref, definition in shared:
        owner = data[definition["entry"]]["owner"]
        (site,) = tuple(
            data[r]
            for r in mapped["sites"]
            if data[r]["occurrence"] == data[owner]["definition"]
        )
        assert site["declaration"] == owner
        module = data[data[site["source"]]["module"]]
        assert module["position"] == data[owner]["module_position"]
        uses = [data[r] for r in plan["input_uses"] if data[r]["producer"] == ref]
        assert len({u["ref"] for u in uses}) == len(uses)
        usage[module["path"]] = len(uses)
    assert usage == {"other.pietto": 1, "producer.pietto": 2}
    association_sources = {}
    for ref in mapped["associations"]:
        association = data[ref]
        site = data[association["site"]]
        path = data[data[site["source"]]["module"]]["path"]
        association_sources.setdefault(association["kind"], set()).add(path)
    assert association_sources["import_item"] >= {"main.pietto", "facade.pietto"}
    assert association_sources["export_item"] >= {"facade.pietto", "producer.pietto"}
    row_rules = {
        "inner": "matched_pairs",
        "left": "left_preserved",
        "cross": "cartesian_pairs",
        "right": "right_preserved",
        "full": "both_preserved",
        "semi": "left_exists",
        "anti": "left_not_exists",
    }
    for name in (
        "join_cross",
        "join_right",
        "join_semi",
        "join_anti",
        "join_refinement",
        "join_accumulated",
    ):
        _, data, plan = _document_tables(cases[name])
        ports = {data[r]["ref"]: data[r] for r in plan["join_ports"]}
        inputs = {data[r]["ref"]: data[r] for r in plan["join_inputs"]}
        for ref in plan["joins"]:
            join = data[ref]
            left, right = (inputs[r] for r in join["inputs"])
            assert [int(left["ordinal"]), int(right["ordinal"])] == [0, 1]
            assert join["rows"] == row_rules[join["kind"]]
            assert all(
                ports[p]["kind"] == "match" for p in (*left["ports"], *right["ports"])
            )
            assert len(join["outputs"]) == (
                len(left["ports"])
                if join["kind"] in ("semi", "anti")
                else len(left["ports"]) + len(right["ports"])
            )
            assert all(ports[p]["kind"] == "output" for p in join["outputs"])
            if join["kind"] in ("semi", "anti"):
                assert right["producer"] is not None and len(right["ports"]) == 3
                assert len(plan["input_uses"]) == 2
        if name == "join_right":
            (join,) = (data[r] for r in plan["joins"])
            assert [len(ports[p]["nulling"]) for p in join["outputs"]] == [
                1,
                1,
                1,
                0,
                0,
                0,
            ]
        if name == "join_accumulated":
            first, second = (data[r] for r in plan["joins"])
            left = inputs[second["inputs"][0]]
            assert left["predecessor"] == first["ref"] and left["producer"] is None
            assert [len(ports[p]["nulling"]) for p in left["ports"]] == [
                0,
                0,
                0,
                1,
                1,
                1,
            ]
            assert [len(ports[p]["nulling"]) for p in second["outputs"]] == [
                1,
                1,
                1,
                2,
                2,
                2,
                1,
                1,
                1,
            ]
        if name == "join_refinement":
            (join,) = (data[r] for r in plan["joins"])
            (filter_,) = (data[r] for r in plan["filters"])
            assert join["on"] != filter_["predicate"]
            assert len(plan["relationship_matches"]) == 1
            assert data[filter_["site"]]["role"] == "where"

    for name in ("group_hidden", "group_partial"):
        _, data, plan = _document_tables(cases[name])
        (aggregation,) = (data[r] for r in plan["aggregations"])
        keys = [data[r] for r in plan["group_keys"]]
        assert [int(k["position"]) for k in keys] == [0, 1]
        assert all(k["result"] in aggregation["results"] for k in keys)
        assert all(
            k["result"] not in [data[r]["ref"] for r in plan["exports"]] for k in keys
        )
        properties = data[data[aggregation["authority"]]["properties"]]
        assert properties["keys"] == properties["fds"] == ()
    records, data, plan = _document_tables(cases["grouped_satisfying"])
    blocks = [data[r] for r in plan["blocks"]]
    assert [b["kind"] for b in blocks] == [
        "let",
        "let",
        "where",
        "aggregate",
        "satisfying",
        "projection",
    ]
    assert [b["predecessor"] for b in blocks[1:]] == [b["ref"] for b in blocks[:-1]]
    stage_ports = {data[r]["ref"]: data[r] for r in plan["stage_ports"]}
    (aggregate,) = (data[r] for r in plan["aggregates"])
    references = [
        data[r]
        for r, record in records.items()
        if record.kind == "project_sql_result_reference"
    ]
    assert len(references) == len({r["expression"] for r in references}) == 3
    assert len({r["port"] for r in references}) == 1
    assert all(data[r["site"]]["role"] == "satisfying" for r in references)
    assert all(
        stage_ports[r["port"]]["source"] == aggregate["result"] for r in references
    )
    assert len({data[r["reference"]]["aggregate_result_fact"] for r in references}) == 1
    expressions = {data[r]["ref"]: data[r] for r in plan["expressions"]}
    (argument,) = aggregate["arguments"]
    reference = expressions[argument]
    assert data[reference["site"]]["role"] == "aggregate_argument"
    amount = data[plan["let_values"][1]]
    binding = stage_ports[amount["port"]]["key"]
    assert data[reference["reference"]]["let_candidates"] == (binding,)
    port = reference["port"]
    for block in reversed(blocks[2:4]):
        assert stage_ports[port]["block"] == block["ref"]
        if stage_ports[port]["kind"] == "export":
            port = stage_ports[port]["source"]
        assert (
            stage_ports[port]["kind"] == "input" and stage_ports[port]["key"] == binding
        )
        port = stage_ports[port]["source"]
    assert port == amount["port"]
    risks = cases["aggregate_risks"]["summary"]["risks"]
    assert risks.count("group_protection") == 1
    assert risks.count("grain_linkage") == 8
    assert risks.count("pair_linkage") == 8 * 7 // 2
    _, data, plan = _document_tables(cases["aggregate_risks"])
    (aggregation,) = (data[r] for r in plan["aggregations"])
    assert (
        tuple(data[r]["source"] for r in plan["aggregate_risks"])
        == data[aggregation["authority"]]["risks"]
    )

    _, data, plan = _document_tables(cases["hidden_distinct"])
    uses = [data[r] for r in plan["window_uses"]]
    assert [u["role"] for u in uses] == [
        "window_argument",
        "window_default",
        "window_partition",
        "window_order",
    ]
    assert [int(u["position"]) for u in uses] == [0, 1, 2, 3]
    assert all(u["binding"] is not None and u["input"] is not None for u in uses)
    assert uses[0]["input"] == uses[3]["input"] and uses[1]["input"] == uses[2]["input"]
    assert len({u["ref"] for u in uses}) == 4
    _, data, plan = _document_tables(cases["window_value_named"])
    policies = [data[r] for r in plan["window_policies"]]
    specs = [data[data[p["specification"]]["resolved"]] for p in policies]
    frames = [data[s["frame"]] for s in specs]
    assert [f["unit"] for f in frames] == ["rows", "rows", "range", "groups"]
    assert [s["ordering_origin"] for s in specs] == [
        "inherited",
        "inherited",
        "locally_authored",
        "locally_authored",
    ]
    assert specs[0]["order_by"] == specs[1]["order_by"]
    assert frames[0]["authored"] == frames[1]["authored"]
    assert [p["named_use"] is not None for p in policies] == [True, True, False, False]
    assert frames[-1]["exclusion"] == "current_row"
    assert data[policies[-1]["modifiers"]]["null_treatment"] == "ignore_nulls"
    assert data[policies[-1]["modifiers"]]["nth_direction"] == "from_last"

    for name in ("shared_set", "set_forms", "set_float", "sharing_depth12"):
        _, data, plan = _document_tables(cases[name])
        operands = {data[r]["ref"]: data[r] for r in plan["set_operands"]}
        columns = {data[r]["ref"]: data[r] for r in plan["set_columns"]}
        for body_ref in plan["set_bodies"]:
            body = data[body_ref]
            assert body["fold"] == "source_order_left_fold"
            assert body["requires_equivalence"] == (
                (body["kind"], body["quantifier"]) != ("union", "all")
            )
            owned = [operands[r] for r in body["operands"]]
            assert [int(o["position"]) for o in owned] == list(range(len(owned)))
            for index, column_ref in enumerate(body["columns"]):
                column = columns[column_ref]
                assert column["inputs"] == tuple(o["fields"][index] for o in owned)
                assert column["value_inputs"] == (
                    column["inputs"][:1]
                    if body["kind"] == "except"
                    else column["inputs"]
                )
        if name == "set_float":
            assert not any(
                data[r].get("kind") == "set_whole_row_equivalence"
                for r in plan["demands"]
            )
        if name == "sharing_depth12":
            definitions = {
                data[data[data[r]["entry"]]["owner"]]["definition"]: data[r]["ref"]
                for r in data[plan["bindings"]]["definitions"]
            }
            names = {data[d]["name"]: ref for d, ref in definitions.items()}
            for index in range(1, 13):
                (body,) = tuple(
                    data[r]
                    for r in plan["set_bodies"]
                    if data[r]["definition"] == names[f"p{index}"]
                )
                first, second = (operands[r] for r in body["operands"])
                assert first["producer"] == second["producer"] == names[f"p{index - 1}"]
                assert first["use"] != second["use"]
    records, data, plan = _document_tables(cases["target_conflict"])
    conflicts = [data[r] for r, record in records.items() if record.kind == "conflict"]
    assert conflicts
    for conflict in conflicts:
        assert [data[r]["support"] for r in conflict["evidence"]] == [
            "supported",
            "explicitly_unsupported",
        ]
        assert len({data[r]["key"] for r in conflict["evidence"]}) == 1


def test_available_matrix_compares_actual_records_bytes_and_rejections(
    acquired_observation, record_property
):
    import _pietto_differential_process_acquisition as process
    from test_phase65_slice14_portable_boundary_minimal_process_integration import (
        _available_request_manifest,
    )

    store, baseline = acquired_observation
    expected = _available_request_manifest(store.interpreters)
    actual = tuple(
        (r.family, r.key, r.cell.version, r.cell.seed, r.cell.mode, r.ambient)
        for r in process.all_requests(store.interpreters)
    )
    assert actual == expected
    expected_phase65 = tuple(row for row in expected if row[0] == "phase65")
    documents = store.documents("phase65")
    assert tuple(documents) == tuple(row[1] for row in expected_phase65)
    for key, raw in documents.items():
        observed = json.loads(raw)
        assert observed["source_negatives"] == baseline["source_negatives"]
        assert observed["raw_rejections"] == baseline["raw_rejections"]
        for actual_case, expected_case in zip(
            observed["cases"], baseline["cases"], strict=True
        ):
            assert (
                actual_case["document"].encode() == expected_case["document"].encode()
            )
            assert json.loads(actual_case["document"]) == json.loads(
                expected_case["document"]
            )
            assert actual_case["summary"] == expected_case["summary"]
            assert actual_case["mutations"] == expected_case["mutations"]
    record_property("phase65_actual_request_manifest", json.dumps(expected_phase65))
    record_property(
        "phase65_actual_cells",
        json.dumps(
            [
                (c.version, c.seed, c.mode)
                for c in store.plan
                if any(r.family == "phase65" for r in store.plan[c])
            ]
        ),
    )


def test_unrelated_valid_definitions_do_not_add_selected_uses_or_demands(tmp_path):
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
    from _pietto_phase65_sql_plan_differential_probe import source_negative

    policy = literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
    original = construction(tmp_path / "original", CONTROL, policy)
    extra = (
        CONTROL
        + 'source extras: Row is postgres.table("extras")\nquery unused:\n    from extras\n    select:\n        text = trim("hello")\n'
    )
    extended = construction(tmp_path / "extended", extra, policy)
    first, second = (
        inspect_project_sql_plan(original),
        inspect_project_sql_plan(extended),
    )
    assert [d.entry.owner.definition.name for d in first.definitions] == [
        "rows",
        "result",
    ]
    assert [d.entry.owner.definition.name for d in second.definitions] == [
        "rows",
        "result",
    ]
    assert len(first.input_uses) == len(second.input_uses) == 1
    assert tuple(e.family for e in first.requirements().entries) == tuple(
        e.family for e in second.requirements().entries
    )
    assert len(first.literal_slots) == len(second.literal_slots) == 0
    (unused,) = tuple(
        o for o in extended.analysis_bundle.root.owners if o.definition.name == "unused"
    )
    mapped = second.source_map()
    (source,) = mapped.source_map.sources
    assert mapped.reverse(source, unused.definition) == ()
    negative = source_negative(
        tmp_path / "error",
        CONTROL + "source broken: Row is postgres.table(1)\n",
        "PIE-S2306",
    )
    assert negative["boundary"] == "semantic" and negative["blockers"] == [
        "semantic_result_unsuccessful"
    ]


def test_literal_policy_rebuild_preserves_authored_ast_and_visible_semantic_fields(
    tmp_path,
):
    from _pietto_phase65_sql_plan_differential_probe import ROW_SHARED
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    preserve = construction(
        tmp_path / "project",
        ROW_SHARED,
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    )
    old = preserve.plan
    assert isinstance(old, ProjectSQLPlan)
    policy = literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS
    bound = build_project_sql_plan(
        preserve.completed,
        preserve.analysis_bundle,
        preserve.selected_owner,
        literal_policy=policy,
    )
    assert isinstance(bound, ProjectSQLPlan)
    checked = verify_project_sql_plan(
        bound,
        preserve.completed,
        preserve.analysis_bundle,
        preserve.selected_owner,
        literal_policy=policy,
    )
    assert checked.verified and checked.completed is preserve.completed
    assert tuple(s.position.literal for s in old.literal_sites) == tuple(
        s.position.literal for s in bound.literal_sites
    )
    assert tuple(p.identity for p in old.exports) == tuple(
        p.identity for p in bound.exports
    )
    assert not old.literal_slots and len(bound.literal_slots) == 17
    product = portable.build_project_sql_plan_portable(preserve)
    assert portable.verify_project_sql_plan_portable(product, checked).issues == (
        portable.RuntimeIssue.INVALID_REQUEST,
    )


def test_repeated_use_changes_occurrences_without_copying_defining_literals(tmp_path):
    source = (
        CONTROL.replace("query result:", "table shared:").replace(
            "        id\n", "        id = 17\n"
        )
        + "query result:\n    union all:\n        from shared\n        from shared\n"
    )
    products = tuple(
        construction(
            tmp_path / str(n),
            source + "        from shared\n" * n,
            literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
        )
        for n in (0, 1)
    )
    for index, verified in enumerate(products):
        plan = verified.plan
        assert isinstance(plan, ProjectSQLPlan)
        assert [d.entry.owner.definition.name for d in plan.bindings.definitions] == [
            "rows",
            "shared",
            "result",
        ]
        assert len(plan.input_uses) == 3 + index and len(plan.set_operands) == 2 + index
        assert len(plan.literal_slots) == len(plan.bind_uses) == 1
        assert plan.fixed_envelope.values[0].value == 17
        assert plan.literal_slots[0].site.position.owner.definition.name == "shared"
        product = portable.build_project_sql_plan_portable(verified)
        assert (
            pure.parse_project_sql_plan_document(product.canonical_bytes).status
            is pure.Status.OK
        )


def test_set_operand_order_and_nesting_are_authored_structural_differences(tmp_path):
    prefix = (
        CONTROL.split("query result:")[0]
        + 'source other: Row is postgres.table("other")\nsource third: Row is postgres.table("third")\n'
    )
    flat = (
        prefix
        + "query result:\n    except distinct:\n        from rows\n        from other\n        from third\n"
    )
    reordered = (
        prefix
        + "query result:\n    except distinct:\n        from other\n        from rows\n        from third\n"
    )
    nested = (
        prefix
        + "table nested_right:\n    except distinct:\n        from other\n        from third\nquery result:\n    except distinct:\n        from rows\n        from nested_right\n"
    )
    for name, source, expected in (
        ("flat", flat, ("rows", "other", "third")),
        ("reordered", reordered, ("other", "rows", "third")),
        ("nested", nested, ("rows", "nested_right")),
    ):
        verified = construction(
            tmp_path / name, source, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS
        )
        plan = verified.plan
        assert isinstance(plan, ProjectSQLPlan)
        (definition,) = tuple(
            d
            for d in plan.bindings.definitions
            if d.entry.owner is verified.selected_owner
        )
        (body,) = tuple(b for b in plan.set_bodies if b.definition is definition.ref)
        definitions = {d.ref: d for d in plan.bindings.definitions}
        operands = tuple(o for o in plan.set_operands if o.body is body.ref)
        assert (
            tuple(definitions[o.producer].entry.owner.definition.name for o in operands)
            == expected
        )
        assert body.fold == "source_order_left_fold"
        assert [o.position for o in operands] == list(range(len(expected)))
        assert len(plan.set_bodies) == (2 if name == "nested" else 1)
        (column,) = tuple(c for c in plan.set_columns if c.body is body.ref)
        assert (
            len(column.inputs) == len(expected)
            and column.value_inputs == column.inputs[:1]
        )
        assert portable.verify_project_sql_plan_portable(
            portable.build_project_sql_plan_portable(verified), verified
        ).verified


def test_target_only_reassessment_keeps_the_original_neutral_request(tmp_path):
    verified = construction(
        tmp_path / "project",
        CONTROL,
        literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
    )
    plan = verified.plan
    assert isinstance(plan, ProjectSQLPlan)
    envelope, scope = verified.envelope, plan.scope
    applicable = assessment(verified, "applicable")
    mismatched = assessment(verified, "mismatch")
    assert applicable.request is not mismatched.request
    assert applicable.source_verification is mismatched.source_verification is verified
    assert isinstance(verified.plan, ProjectSQLPlan)
    assert (
        verified.plan is plan
        and verified.envelope is envelope
        and verified.plan.scope is scope
    )
    assert any(q.profile_applicable for q in applicable.assessment.lookups)
    assert not any(q.profile_applicable for q in mismatched.assessment.lookups)
    assert (
        applicable.assessment.summary.posture.value
        == mismatched.assessment.summary.posture.value
        == "incomplete_requirement_assessment"
    )
    product = portable.build_project_sql_plan_portable(verified, assessment=applicable)
    assert not portable.verify_project_sql_plan_portable(
        product, verified, assessment=mismatched
    ).verified


def test_hidden_and_selected_windows_change_only_the_intended_visible_tuple(tmp_path):
    from _pietto_phase65_sql_plan_differential_probe import ORDINARY_PREFIX

    selected = (
        ORDINARY_PREFIX
        + "query result:\n    from rows\n    select distinct:\n        id\n        w = row_number() window:\n            order by:\n                id\n    qualify:\n        w <= 3\n"
    )
    hidden = (
        ORDINARY_PREFIX
        + "query result:\n    from rows\n    select distinct:\n        id\n    qualify:\n        row_number() window:\n            order by:\n                id\n        <= 3\n"
    )
    for label, source, names in (
        ("selected", selected, ("id", "w")),
        ("hidden", hidden, ("id",)),
    ):
        verified = construction(
            tmp_path / label, source, literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS
        )
        plan = verified.plan
        assert isinstance(plan, ProjectSQLPlan)
        (window,) = plan.windows
        assert window.function.name == "row_number"
        assert (window.selected is not None) == (label == "selected")
        assert tuple(p.identity.name for p in plan.exports) == names
        assert tuple(q.canonical.identity.name for q in plan.quotient_fields) == names
        assert (
            pure.parse_project_sql_plan_document(
                portable.build_project_sql_plan_portable(verified).canonical_bytes
            ).status
            is pure.Status.OK
        )


def test_unicode_coordinates_and_imported_defining_vs_consuming_identity(tmp_path):
    from _pietto_phase65_sql_plan_differential_probe import (
        ROW_SHARED,
        IMPORTED_REEXPORT,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    verified = construction(
        tmp_path / "unicode",
        ROW_SHARED,
        literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
    )
    view = inspect_project_sql_plan(verified)
    (value,) = tuple(
        v
        for v in view.fixed_envelope.values
        if v.tag is literals.ProjectSQLLiteralTag.TEXT and v.value == "é\n😀"
    )
    literal = value.slot.site.position.literal
    assert literal.span.end_line is not None and literal.span.end_column is not None
    assert literal.span.end_column - literal.span.column == len('"é\\n😀"') == 6
    mapped = view.source_map()
    (site,) = tuple(s for s in mapped.source_map.sites if s.occurrence is literal)
    associations = mapped.reverse(site.source, literal)
    assert associations
    for association in associations:
        assert association in mapped.at(
            site.source, literal.span.line, literal.span.column
        )
        assert association not in mapped.at(
            site.source, literal.span.end_line, literal.span.end_column
        )
    assert (
        mapped.overlapping(
            site.source,
            (literal.span.line, literal.span.column),
            (literal.span.line, literal.span.column),
        )
        == ()
    )

    imported = construction(
        tmp_path / "imports",
        IMPORTED_REEXPORT,
        literals.ProjectSQLLiteralPolicy.BIND_SAFE_LITERALS,
    )
    view = inspect_project_sql_plan(imported)
    shared = tuple(
        d for d in view.definitions if d.entry.owner.definition.name == "shared"
    )
    assert len(shared) == 2 and shared[0].entry.owner is not shared[1].entry.owner
    mapped = view.source_map()
    counts = {}
    for definition in shared:
        (site,) = tuple(
            s
            for s in mapped.source_map.sites
            if s.occurrence is definition.entry.owner.definition
        )
        counts[str(site.source.module.path)] = sum(
            u.producer is definition.ref for u in view.input_uses
        )
        assert site.declaration is definition.entry.owner
    assert counts == {"other.pietto": 1, "producer.pietto": 2}
    assert {a.kind.value for a in mapped.source_map.associations} >= {
        "import_item",
        "export_item",
        "referenced_declaration",
    }
