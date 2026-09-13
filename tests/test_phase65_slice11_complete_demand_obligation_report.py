"""Complete typed requirement reports through real plans and hostile witnesses."""

from dataclasses import replace, FrozenInstanceError
from types import MappingProxyType
from typing import get_args, cast
import sys
import traceback

import pytest

from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_joins as joins
from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_requirements as report
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
    verify_project_sql_bindings,
)
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_single_match import (
    ProjectSingleMatchScope,
    ProjectSingleMatchState,
)
from pietto.errors import Severity
from pietto.ast_nodes import DottedNameExpr
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
    _source as minimal_source,
    _graft,
)
from test_phase65_slice4_row_scalar_let_where_stage_value_planning import (
    _source as row_source,
    ROW_BODY,
)
from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
    _roots,
    _requests,
    _path_source,
    _path_requests,
    _source as join_source,
)
from test_phase65_slice6_grouped_global_satisfying_block_boundaries import (
    _joined_aggregates,
    _group_source,
)
from test_phase65_slice7_windows_named_window_qualify_staging import (
    SOURCES,
    _family_source,
)
from test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries import (
    _source as result_source,
)
from test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout import BODY
from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
    _repeated_sets,
)

P = literals.ProjectSQLLiteralPolicy
F = report.ProjectSQLDemandFamily


def _cases():
    hidden_order = result_source(
        "    select distinct:\n        value\n    order by:\n        hidden\n    limit 0\n"
    ).replace(
        "value: Int nullable", "value: Int not null\n    unique by_value on value"
    )
    right = join_source(
        "inner", "true", tail="    select:\n        id = lhs.id\n"
    ).replace("query result:", "table right_side:")
    right += "table left_side:\n    from lhs\n    select:\n        id\n    limit 0\nquery result:\n    except distinct:\n        from left_side\n        from right_side\n"
    return {
        "minimal": (minimal_source(), None),
        "row": (row_source(ROW_BODY), None),
        "literal_tags": (row_source(BODY), None),
        "join": (join_source("left", "true"), _requests),
        "path": (_path_source(all_unique=True), _path_requests),
        "partial_path": (_path_source(), _path_requests),
        "aggregate": (_joined_aggregates(), None),
        "hidden_group": (_group_source(), None),
        "hidden_window": (SOURCES["selected_and_hidden"], None),
        "window_arguments": (
            _family_source("lag(value, 2, 0)", None, True, "query", "postgres"),
            None,
        ),
        "hidden_order": (hidden_order, None),
        "set_membership": (right, _requests),
    }


def _reported(roots, policy):
    assert roots[0].ok, roots[0].diagnostics
    plan = sql.build_project_sql_plan(*roots, literal_policy=policy)
    assert isinstance(plan, sql.ProjectSQLPlan), getattr(plan, "blockers", ())
    source = verify_project_sql_plan(plan, *roots, literal_policy=policy)
    assert source.verified, source.issues
    value = report.build_project_sql_requirement_report(source)
    checked = report.verify_project_sql_requirement_report(value, source)
    assert checked.verified, checked.issues
    view = report.inspect_project_sql_requirement_report(checked)
    return roots, plan, source, value, checked, view


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    values = {}
    for name, (source, requests) in _cases().items():
        roots = _roots(tmp_path_factory.mktemp("requirements"), source, requests)
        for policy in P:
            values[name, policy] = _reported(roots, policy)
    return values


def test_every_current_variant_and_meaningful_subkind_has_real_coverage(corpus):
    current_variants = set(get_args(sql.ProjectSQLDemand.__value__))
    assert set(report.DEMAND_FAMILIES) == current_variants
    actual = set()
    kinds = {family: set() for family in F}
    for _, plan, _, value, _, _ in corpus.values():
        assert len(value.entries) == len(plan.demands)
        for entry in value.entries:
            actual.add(type(entry.demand))
            kinds[entry.family].add(entry.subkind)
    assert actual == current_variants
    assert kinds == {family: set(values) for family, values in report.SUBKINDS.items()}
    for family, enumeration in (
        (F.JOIN, joins.ProjectSQLJoinDemandKind),
        (F.AGGREGATE, aggregation.ProjectSQLAggregateDemandKind),
        (F.WINDOW, windows.ProjectSQLWindowDemandKind),
        (F.RESULT, results.ProjectSQLResultDemandKind),
        (F.SET, sets.ProjectSQLSetDemandKind),
        (F.SCOPE, row.ProjectSQLStageKind),
        (F.EXPRESSION, row.ProjectSQLExpressionRole),
        (F.STAGE_VALUE, row.ProjectSQLStagePortKind),
        (F.LITERAL, literals.ProjectSQLLiteralTag),
    ):
        assert set(report.SUBKINDS[family]) == set(enumeration)


@pytest.mark.parametrize("policy", tuple(P))
def test_roots_flat_order_and_useful_exact_indexes(corpus, policy):
    for name in _cases():
        roots, plan, source, value, _, view = corpus[name, policy]
        assert value.source_verification is source and value.plan is plan
        assert value.completed is roots[0] and value.analysis_bundle is roots[1]
        assert value.selected_owner is roots[2] and value.literal_policy is policy
        assert value.envelope is source.envelope is plan.fixed_envelope
        assert (
            value.diagnostics
            is view.diagnostics
            is plan.diagnostics
            is roots[0].diagnostics
        )
        assert value.input_uses is plan.input_uses
        assert [entry.position for entry in value.entries] == list(
            range(len(plan.demands))
        )
        assert len({entry.ref for entry in value.entries}) == len(value.entries)
        origins = {origin.ref: origin for origin in plan.origins}
        definitions = {d.ref: d for d in plan.bindings.definitions}
        for original, entry in zip(plan.demands, view.entries, strict=True):
            assert (
                entry.demand is original
                and entry.ref is original.ref
                and entry.subject is original.subject
            )
            assert view.entry(original.ref) is entry
            assert entry.origin is origins[original.origin]
            assert entry.origin_owner is entry.origin.owner
            assert entry.scope.definition in definitions
            assert entry in view.for_subject(entry.subject)
            assert entry in view.for_family(entry.family)
            assert entry in view.for_definition(entry.scope.definition)
            for stage in entry.scope.stages:
                assert entry in view.for_stage(stage)
            for use in entry.scope.input_uses:
                assert entry in view.for_input_use(use)
        for group in view.summary.families:
            assert group.entries is value.indexes.by_family[group.family]
            assert group.entries == tuple(
                e for e in value.entries if e.family is group.family
            )
        assert view.summary.demand_count == len(value.entries)
        assert view.summary.target is report.ProjectSQLReportTargetPosture.NOT_ASSESSED


def test_minimal_demands_are_not_runtime_obligations_or_ready_flags(corpus):
    _, plan, source, value, _, view = corpus["minimal", P.PRESERVE_LITERALS]
    assert value.entries and view.for_family(F.SOURCE) and view.for_family(F.EXPORT)
    assert (
        value.single_matches
        == view.summary.original_proved
        == view.summary.enforcement_required
        == ()
    )
    assert value.hidden_realizations == ()
    assert view.summary.target is report.ProjectSQLReportTargetPosture.NOT_ASSESSED
    assert not hasattr(view.summary, "ready") and not hasattr(
        view.summary, "executable"
    )
    # An owned source port has no direct demand; a role-correct empty query is legal.
    assert view.for_subject(plan.source_ports[0].ref) == ()
    planned = inspect_project_sql_plan(source)
    before = planned.expressions
    convenience = planned.requirements()
    assert convenience.report.plan is plan
    assert tuple(e.demand for e in convenience.entries) == plan.demands
    assert planned.expressions is before


@pytest.mark.parametrize("case", ("path", "partial_path", "join"))
def test_original_single_match_scope_proofs_and_posture(corpus, case):
    _, plan, _, value, _, view = corpus[case, P.BIND_SAFE_LITERALS]
    assert len(value.single_matches) == len(plan.single_matches)
    by_subject = {
        entry.subject: entry for entry in value.entries if entry.family is F.JOIN
    }
    for original, record in zip(plan.single_matches, value.single_matches, strict=True):
        assert record.original is original and record.entry is by_subject[original.ref]
        assert record.state is original.assessment.state
        assert record.enforcement_required is original.downstream_enforcement_required
        assert record.diagnostic is original.diagnostic
        expected = tuple(
            by_subject[p.ref]
            for p in plan.single_match_proofs
            if p.obligation is original.ref
        )
        assert record.proof_entries == expected
        assert view.for_requirement(original.request) == tuple(
            e for e in value.entries if e is record.entry or e in expected
        )
        assert view.for_requirement(original.assessment) == view.for_requirement(
            original.request
        )
        for proof in expected:
            assert isinstance(proof.demand, joins.ProjectSQLJoinDemand)
            image = proof.demand.witness
            assert isinstance(image, joins.ProjectSQLSingleMatchProof)
            assert proof in view.for_requirement(image.source.source)
            assert image.parent is None or view.referring(proof.ref)
        if record.state is ProjectSingleMatchState.LEGAL_UNPROVED:
            assert record in view.summary.enforcement_required
            assert (
                record.diagnostic is not None
                and record.diagnostic.severity is Severity.WARNING
            )
        else:
            assert (
                record in view.summary.original_proved
                and not record.enforcement_required
            )
    if case != "join":
        assert [m.original.request.scope for m in value.single_matches] == [
            ProjectSingleMatchScope.PATH_HOP
        ] * 2 + [ProjectSingleMatchScope.WHOLE_PATH]
        assert len(value.single_matches[-1].original.input_pairs) == 2
    if case == "path":
        assert any(
            link.kind is report.ProjectSQLDemandLinkKind.PROOF_CHILD
            for link in value.links
        )


def test_aggregate_evidence_is_not_a_synthesized_enforcement_verdict(corpus):
    _, plan, _, value, _, view = corpus["aggregate", P.BIND_SAFE_LITERALS]
    assert {record.kind for record in value.aggregate_evidence} == set(
        report.ProjectSQLAggregateEvidenceKind
    )
    assert len(value.aggregate_evidence) == len(plan.aggregate_risks)
    assert not value.single_matches and not view.summary.enforcement_required
    for original, record in zip(
        plan.aggregate_risks, value.aggregate_evidence, strict=True
    ):
        assert record.original is original and record.entry.demand.witness is original
        assert view.for_requirement(original.source) == (record.entry,)
        assert not hasattr(record, "enforcement_required") and not hasattr(
            record, "failed"
        )
        if isinstance(original.source, aggregation.ProjectJoinedAggregatePairLinkage):
            assert record.original.source.structural is original.source.structural
            assert record.original.source.common_grain is original.source.common_grain
    _, hidden, _, hidden_report, _, _ = corpus["hidden_group", P.PRESERVE_LITERALS]
    assert hidden.group_keys and all(p.identity.name != "id" for p in hidden.exports)
    assert any(
        e.subkind is aggregation.ProjectSQLAggregateDemandKind.GROUP_COMPARISON
        for e in hidden_report.entries
    )


def test_hidden_order_is_pending_realization_and_never_an_available_value(corpus):
    _, plan, _, value, _, view = corpus["hidden_order", P.PRESERVE_LITERALS]
    (record,) = value.hidden_realizations
    (original,) = plan.hidden_order_requirements
    assert record.original is original
    assert record.posture is report.ProjectSQLRealizationPosture.PENDING
    assert record.entry.subkind is results.ProjectSQLResultDemandKind.HIDDEN
    assert record.entry.demand.witness is original
    assert (
        view.for_requirement(original)
        == view.for_requirement(original.proof)
        == (record.entry,)
    )
    assert original.determinants and original.requested and original.input_images
    assert all(port.ref is not original.ref for port in plan.result_ports)
    assert view.summary.pending_realizations == (record,)
    assert not view.summary.enforcement_required


@pytest.mark.parametrize("policy", tuple(P))
def test_literal_composite_propositions_and_bidirectional_context_links(corpus, policy):
    _, plan, _, value, _, view = corpus["literal_tags", policy]
    entries = view.for_family(F.LITERAL)
    assert len(entries) == len(plan.bind_uses)
    if policy is P.BIND_SAFE_LITERALS:
        assert {entry.subkind for entry in entries} == set(
            literals.ProjectSQLLiteralTag
        )
    for entry in entries:
        demand = entry.demand
        assert type(demand) is literals.ProjectSQLLiteralDemand
        assert entry.literal_requirements is demand.requirements
        assert entry.literal_requirements == tuple(
            literals.ProjectSQLLiteralRequirement
        )
        edges = view.related(entry.ref)
        assert len(edges) == len(demand.contexts)
        assert all(
            edge.kind is report.ProjectSQLDemandLinkKind.LITERAL_CONTEXT
            for edge in edges
        )
        for edge, context in zip(edges, demand.contexts, strict=True):
            assert edge.source is entry and edge.target is view.entry(context.ref)
            assert edge.target.demand is context and edge in view.referring(context.ref)
        assert view.for_requirement(demand.use.slot) == (entry,)
        assert view.for_requirement(demand.value) == (entry,)
    if entries:
        equal = [
            e
            for e in entries
            if e.subkind is literals.ProjectSQLLiteralTag.INT
            and e.demand.value.value == 1
        ]
        assert len(equal) >= 2 and len({e.ref for e in equal}) == len(equal)


def test_except_membership_and_limit_zero_retain_original_warning(corpus):
    _, plan, _, value, _, view = corpus["set_membership", P.BIND_SAFE_LITERALS]
    assert plan.result_limits[0].value == 0
    assert (
        len(plan.set_columns[0].value_inputs) == 1
        and len(plan.set_columns[0].inputs) == 2
    )
    right = plan.set_inputs[1]
    (entry,) = view.for_subject(right.ref)
    assert entry.subkind is sets.ProjectSQLSetDemandKind.INPUT
    assert entry.origin.provenance is sql.ProjectSQLOriginProvenance.TYPE_PROOF
    origins = {origin.ref: origin for origin in plan.origins}
    (input_origin,) = tuple(origins[ref] for ref in entry.origin.antecedents)
    assert input_origin.subject is right.ref
    assert input_origin.provenance is sql.ProjectSQLOriginProvenance.MEMBERSHIP
    assert entry.scope.input_uses == (plan.set_operands[1].use.ref,)
    assert value.single_matches[0].enforcement_required
    assert value.single_matches[0].entry in view.for_definition(
        plan.set_operands[1].producer
    )


@pytest.mark.parametrize("reuse_identity", (False, True))
def test_repeated_original_requests_and_unrelated_project_warnings(
    tmp_path, reuse_identity
):
    source = join_source("semi", "true")
    source += (
        "query unused:" + join_source("inner", "true").split("query result:", 1)[1]
    )

    def requests(completed):
        first, second = _requests(completed)
        return first, first if reuse_identity else replace(first), second

    roots, plan, _, value, _, view = _reported(
        _roots(tmp_path, source, requests), P.PRESERVE_LITERALS
    )
    assert len(value.single_matches) == 2 and value.diagnostics is roots[0].diagnostics
    a, b = value.single_matches
    assert (a.original.request is b.original.request) is reuse_identity
    assert a.entry is not b.entry and (a.diagnostic is b.diagnostic) is reuse_identity
    expected = (a.entry, b.entry) if reuse_identity else (a.entry,)
    assert view.for_requirement(a.original.request) == expected
    assert len(roots[0].single_matches.entries) == 3
    with pytest.raises(ValueError):
        view.for_requirement(roots[0].single_matches.entries[-1].request)
    assert plan.diagnostics is value.diagnostics


@pytest.mark.parametrize("proof", ("limit", "global"))
def test_right_producer_bound_proofs_remain_scoped(tmp_path, proof):
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _limited_source,
    )
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
        _tail_source,
    )

    if proof == "limit":
        roots = _roots(tmp_path, _limited_source(right_limit=1), _requests)
    else:
        source, _ = _tail_source("global")
        source += "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
        roots = _roots(tmp_path, source, lambda completed: (_requests(completed)[-1],))
    _, plan, _, value, _, view = _reported(roots, P.BIND_SAFE_LITERALS)
    assert value.single_matches[0].state is ProjectSingleMatchState.PROVED
    assert not value.single_matches[0].enforcement_required
    matching = [
        p
        for p in plan.single_match_proofs
        if p.source.source.kind.value == "right_" + proof
    ]
    assert matching and all(p.producers for p in matching)
    for image in matching:
        demand = view.for_requirement(image.source)[0].demand
        assert type(demand) is joins.ProjectSQLJoinDemand
        assert demand.witness is image


def test_depth12_sharing_and_overlapping_use_facets_are_not_transitive_copies(tmp_path):
    roots = _roots(
        tmp_path, _repeated_sets(12).replace("        id\n", "        id = 17\n", 1)
    )
    _, plan, _, value, _, view = _reported(roots, P.BIND_SAFE_LITERALS)
    assert len(plan.bindings.definitions) == 15 and len(plan.input_uses) == 26
    assert (
        len(value.entries) == len(plan.demands) and len(view.for_family(F.LITERAL)) == 1
    )
    operand0, operand1 = plan.set_operands[:2]
    assert operand0.producer is operand1.producer
    shared = view.for_definition(operand0.producer)
    assert all(e in value.entries for e in shared)
    a, b = view.for_input_use(operand0.use.ref), view.for_input_use(operand1.use.ref)
    assert set(a) & set(b)  # Body/column context facets overlap.
    assert len(set(a) | set(b)) < len(a) + len(b)
    assert view.for_subject(operand0.ref)[0] is not view.for_subject(operand1.ref)[0]
    assert not any(e in shared for e in (*a, *b))


def test_imported_authored_owners_and_consuming_scopes_remain_distinct(tmp_path):
    (tmp_path / "a.pietto").write_text(
        'type Money = Decimal(12, 2)\nshape Row:\n    id: Int not null\n    amount: Money nullable\nsource rows: Row is mysql.table("rows")\ntable first:\n    from rows\n    select:\n        id\n        amount\nexport:\n    table first\n'
    )
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    source = 'import "b.pietto":\n    table Public as Alias\nquery result:\n    from Alias\n    select:\n        id\n        amount\n'
    roots, plan, _, value, _, view = _reported(
        _roots(tmp_path, source), P.BIND_SAFE_LITERALS
    )
    use = next(u for u in plan.input_uses if u.dependency.consumer is roots[2])
    assert len(use.origin_path.hops) == 2 and value.input_uses is plan.input_uses
    source_entry = view.for_family(F.SOURCE)[0]
    assert source_entry.origin_owner.identity.module_path == "a.pietto"
    assert source_entry.origin_owner is not value.selected_owner
    assert all(e.scope.definition is use.consumer for e in view.for_input_use(use.ref))
    types = [
        site
        for site in value.plan.literal_sites
        if site.position.role is literals.ProjectSQLLiteralRole.TYPE
    ]
    assert [s.position.literal.value for s in types] == [12, 2]
    assert all(
        s.position.owner.definition.name == "Money"
        and s.position.definition is source_entry.scope.definition
        for s in types
    )


def _changed(values, original, replacement):
    return tuple(replacement if value is original else value for value in values)


def _reject(product, candidate, issue=None):
    _, _, source, _, checked, _ = product
    result = report.verify_project_sql_requirement_report(candidate, source)
    assert not result.verified
    if issue is not None:
        assert result.issues == (issue,)
    with pytest.raises(ValueError, match="VERIFIED"):
        report.inspect_project_sql_requirement_report(_graft(checked, report=candidate))


@pytest.mark.parametrize(
    "change",
    (
        "empty",
        "missing",
        "duplicate",
        "extra",
        "reverse",
        "foreign",
        "family",
        "mutable",
        "adjusted_count",
    ),
)
def test_exact_flat_inventory_cannot_be_replaced_by_totals(corpus, change):
    product = corpus["aggregate", P.BIND_SAFE_LITERALS]
    value = product[3]
    entries = value.entries
    cases = {
        "empty": (),
        "missing": entries[:-1],
        "duplicate": (entries[0], *entries[:-1]),
        "extra": (*entries, entries[0]),
        "reverse": tuple(reversed(entries)),
        "foreign": corpus["row", P.BIND_SAFE_LITERALS][3].entries,
        "family": tuple(e for e in entries if e.family is not F.AGGREGATE),
        "mutable": list(entries),
        "adjusted_count": (),
    }
    candidate = _graft(value, entries=cases[change])
    if change == "adjusted_count":
        candidate = _graft(
            candidate, summary=_graft(value.summary, demand_count=0, families=())
        )
    _reject(product, candidate, report.ProjectSQLRequirementIssue.ENTRIES)


@pytest.mark.parametrize(
    "change",
    (
        "position_bool",
        "ref",
        "demand",
        "subject",
        "family",
        "subkind",
        "origin",
        "definition",
        "stage",
        "input_use",
        "type_context",
    ),
)
def test_entry_scope_and_evidence_are_exact_not_equal_looking(corpus, change):
    product = corpus["row", P.BIND_SAFE_LITERALS]
    value = product[3]
    entry = next(
        e
        for e in value.entries
        if e.family is F.EXPRESSION and e.subkind is row.ProjectSQLExpressionRole.SELECT
    )
    other = next(
        e
        for e in value.entries
        if e is not entry and e.family is entry.family and e.subkind is entry.subkind
    )
    scope = entry.scope
    changes = {
        "position_bool": {"position": True},
        "ref": {"ref": other.ref},
        "demand": {"demand": other.demand},
        "subject": {"subject": other.subject},
        "family": {"family": F.LITERAL},
        "subkind": {"subkind": "select"},
        "origin": {"origin": other.origin},
        "definition": {"scope": _graft(scope, definition=product[1].sources[0].ref)},
        "stage": {"scope": _graft(scope, stages=(entry.ref,))},
        "input_use": {"scope": _graft(scope, input_uses=())},
        "type_context": {
            "demand": _graft(entry.demand, value_type=replace(entry.demand.value_type))
        },
    }
    bad = _graft(entry, **changes[change])
    _reject(
        product,
        _graft(value, entries=_changed(value.entries, entry, bad)),
        report.ProjectSQLRequirementIssue.ENTRIES,
    )


@pytest.mark.parametrize("case", ("path", "literal_tags"))
@pytest.mark.parametrize(
    "change",
    ("empty", "missing", "duplicate", "reverse", "kind", "source", "target", "ordinal"),
)
def test_bidirectional_related_demand_edges(corpus, case, change):
    product = corpus[case, P.BIND_SAFE_LITERALS]
    value = product[3]
    links = value.links
    mutations = {
        "empty": (),
        "missing": links[:-1],
        "duplicate": (links[0], *links[:-1]),
        "reverse": tuple(reversed(links)),
        "kind": (_graft(links[0], kind="single_match_root_proof"), *links[1:]),
        "source": (_graft(links[0], source=links[0].target), *links[1:]),
        "target": (_graft(links[0], target=links[0].source), *links[1:]),
        "ordinal": (_graft(links[0], position=False), *links[1:]),
    }
    _reject(
        product,
        _graft(value, links=mutations[change]),
        report.ProjectSQLRequirementIssue.LINKS,
    )


@pytest.mark.parametrize(
    "change",
    ("empty", "request", "state", "enforcement", "diagnostic", "proofs", "reverse"),
)
def test_original_obligations_proof_links_and_warnings_cannot_be_laundered(
    corpus, change
):
    product = corpus["partial_path", P.BIND_SAFE_LITERALS]
    value = product[3]
    index = next(
        i
        for i, r in enumerate(value.single_matches)
        if r.state is ProjectSingleMatchState.LEGAL_UNPROVED
    )
    original = value.single_matches[index]
    altered = {
        "request": _graft(
            original,
            original=_graft(
                original.original, request=value.single_matches[0].original.request
            ),
        ),
        "state": _graft(original, state=ProjectSingleMatchState.PROVED),
        "enforcement": _graft(original, enforcement_required=False),
        "diagnostic": _graft(original, diagnostic=replace(original.diagnostic)),
        "proofs": _graft(original, proof_entries=value.single_matches[0].proof_entries),
    }
    values = (
        ()
        if change == "empty"
        else tuple(reversed(value.single_matches))
        if change == "reverse"
        else _changed(value.single_matches, original, altered[change])
    )
    _reject(
        product,
        _graft(value, single_matches=values),
        report.ProjectSQLRequirementIssue.OBLIGATIONS,
    )


@pytest.mark.parametrize(
    "section,change",
    (
        ("hidden_realizations", "empty"),
        ("hidden_realizations", "available"),
        ("hidden_realizations", "entry"),
        ("aggregate_evidence", "empty"),
        ("aggregate_evidence", "foreign"),
        ("aggregate_evidence", "verdict"),
    ),
)
def test_realization_and_risk_categories_preserve_exact_typed_evidence(
    corpus, section, change
):
    product = corpus[
        "hidden_order" if section == "hidden_realizations" else "aggregate",
        P.BIND_SAFE_LITERALS,
    ]
    value = product[3]
    records = getattr(value, section)
    if change == "empty":
        changed = ()
    elif change == "available":
        changed = (_graft(records[0], posture="ordinary_available_value"),)
    elif change == "entry":
        changed = (_graft(records[0], entry=value.entries[0]),)
    elif change == "foreign":
        changed = (_graft(records[0], original=records[1].original), *records[1:])
    else:
        changed = (_graft(records[0], kind="enforcement_required"), *records[1:])
    _reject(product, _graft(value, **{section: changed}))


@pytest.mark.parametrize(
    "index", tuple(report.ProjectSQLRequirementIndexes.__dataclass_fields__)
)
@pytest.mark.parametrize("change", ("missing", "mutable", "wrong_member"))
def test_indexes_are_complete_immutable_exact_views(corpus, index, change):
    product = corpus["path", P.BIND_SAFE_LITERALS]
    value = product[3]
    original = getattr(value.indexes, index)
    assert original
    changed = {} if change == "missing" else dict(original)
    if change == "wrong_member":
        key = next(key for key, members in changed.items() if members)
        changed[key] = () if index != "by_ref" else value.entries[-1]
    replacement = changed if change == "mutable" else MappingProxyType(changed)
    _reject(
        product,
        _graft(value, indexes=_graft(value.indexes, **{index: replacement})),
        report.ProjectSQLRequirementIssue.INDEXES,
    )


@pytest.mark.parametrize(
    "change",
    (
        "count",
        "bool_count",
        "family",
        "family_members",
        "target",
        "proof",
        "enforcement",
        "pending",
        "risks",
    ),
)
def test_summary_is_inspectable_membership_not_an_adjustable_success_count(
    corpus, change
):
    case = (
        "hidden_order"
        if change == "pending"
        else "aggregate"
        if change == "risks"
        else "partial_path"
    )
    product = corpus[case, P.BIND_SAFE_LITERALS]
    value = product[3]
    summary = value.summary
    changes = {
        "count": {"demand_count": 0},
        "bool_count": {"demand_count": True},
        "family": {"families": ()},
        "family_members": {
            "families": (_graft(summary.families[0], entries=()), *summary.families[1:])
        },
        "target": {"target": "supported"},
        "proof": {"original_proved": ()},
        "enforcement": {"enforcement_required": ()},
        "pending": {"pending_realizations": ()},
        "risks": {"aggregate_evidence": ()},
    }
    _reject(
        product,
        _graft(value, summary=_graft(summary, **changes[change])),
        report.ProjectSQLRequirementIssue.SUMMARY,
    )


@pytest.mark.parametrize(
    "field",
    (
        "source_verification",
        "plan",
        "completed",
        "analysis_bundle",
        "selected_owner",
        "literal_policy",
        "envelope",
        "diagnostics",
        "input_uses",
    ),
)
def test_report_roots_and_captured_literal_request_are_exact(corpus, field):
    product = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    value = product[3]
    foreign = corpus["row", P.PRESERVE_LITERALS][3]
    replacement = getattr(foreign, field)
    if field == "diagnostics":
        replacement = corpus["join", P.PRESERVE_LITERALS][3].diagnostics
    assert replacement is not getattr(value, field)
    _reject(
        product,
        _graft(value, **{field: replacement}),
        report.ProjectSQLRequirementIssue.ROOTS,
    )


def test_same_content_envelope_replacement_requires_a_new_report(corpus):
    roots, plan, source, value, checked, _ = corpus[
        "literal_tags", P.BIND_SAFE_LITERALS
    ]
    envelope = replace(plan.fixed_envelope)
    new_plan = _graft(plan, fixed_envelope=envelope)
    stale = _graft(source, plan=new_plan)
    with pytest.raises(ValueError):
        report.build_project_sql_requirement_report(stale)
    assert not report.verify_project_sql_requirement_report(value, stale).verified
    fresh = verify_project_sql_plan(
        new_plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert fresh.verified
    assert not report.verify_project_sql_requirement_report(value, fresh).verified
    new = report.build_project_sql_requirement_report(fresh)
    assert report.verify_project_sql_requirement_report(new, fresh).verified
    with pytest.raises(ValueError):
        report.inspect_project_sql_requirement_report(
            _graft(checked, source_verification=fresh)
        )


def test_layer1_rejects_missing_demands_and_literal_constituents(corpus):
    _, plan, source, _, _, _ = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    demand = next(
        d for d in plan.demands if type(d) is literals.ProjectSQLLiteralDemand
    )
    for bad in (
        _graft(plan, demands=()),
        _graft(
            plan,
            demands=_changed(
                plan.demands,
                demand,
                _graft(demand, requirements=demand.requirements[:-1]),
            ),
        ),
        _graft(
            plan, demands=_changed(plan.demands, demand, _graft(demand, contexts=()))
        ),
    ):
        stale = _graft(source, plan=bad)
        with pytest.raises(ValueError):
            report.build_project_sql_requirement_report(stale)


def test_bindings_only_unavailable_and_invalid_assessments_are_nonpositive(
    tmp_path, corpus
):
    roots = corpus["minimal", P.PRESERVE_LITERALS][0]
    bindings = sql.build_project_sql_bindings(*roots)
    assert isinstance(bindings, sql.ProjectSQLBindings)
    checked = verify_project_sql_bindings(bindings, *roots)
    assert checked.verified
    with pytest.raises(ValueError):
        report.build_project_sql_requirement_report(
            cast(ProjectSQLPlanVerification, checked)
        )
    invalid_roots = _roots(tmp_path, join_source("cross"), _requests)
    assert not invalid_roots[0].ok
    bad = sql.build_project_sql_plan(*invalid_roots)
    assert isinstance(bad, sql.ProjectSQLPlanUnavailable)
    with pytest.raises(ValueError):
        report.build_project_sql_requirement_report(
            verify_project_sql_plan(bad, *invalid_roots)
        )


def test_owned_refs_empty_queries_and_immutable_products(corpus):
    _, plan, _, value, _, view = corpus["row", P.BIND_SAFE_LITERALS]
    foreign = corpus["literal_tags", P.BIND_SAFE_LITERALS][1]
    for query, ref in (
        (view.entry, plan.exports[0].ref),
        (view.for_subject, value.entries[0].ref),
        (view.for_definition, plan.blocks[0].ref),
        (view.for_stage, plan.sources[0].ref),
        (view.for_input_use, plan.exports[0].ref),
        (view.for_subject, foreign.source_ports[0].ref),
        (view.related, plan.exports[0].ref),
    ):
        with pytest.raises(ValueError):
            query(ref)
    with pytest.raises(ValueError):
        view.for_family("source_realization")
    with pytest.raises(ValueError):
        view.for_requirement(replace(value.entries[0].demand.source))
    for name in report.ProjectSQLRequirementIndexes.__dataclass_fields__:
        index = getattr(value.indexes, name)
        with pytest.raises(TypeError):
            index[None] = ()
    for original in (value, *value.entries, *value.links, value.summary, value.indexes):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(original, "position", 0)


def test_no_downstream_construction_classification_or_provider_access(
    corpus, monkeypatch
):
    products = [
        corpus[name, P.BIND_SAFE_LITERALS]
        for name in (
            "literal_tags",
            "aggregate",
            "path",
            "hidden_order",
            "set_membership",
        )
    ]

    def forbidden(*args, **kwargs):
        pytest.fail("Report crossed a producer/provider boundary")

    names = (
        "infer_row_expression",
        "resolve_named_window_namespace",
        "build_project_completed_semantic_result",
        "build_project_query_block_ir",
        "build_project_sql_plan",
        "build_project_sql_bindings",
        "lookup_capability",
        "analyze_window_expression",
        "resolve_project_joined_namespace_reference",
    )
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pietto.") and module is not None:
            for member in names:
                if hasattr(module, member):
                    monkeypatch.setattr(module, member, forbidden)
    for member in ("build", "classify"):
        monkeypatch.setattr(literals, member, forbidden)
    for _, _, source, _, _, _ in products:
        rebuilt = report.build_project_sql_requirement_report(source)
        assert report.verify_project_sql_requirement_report(rebuilt, source).verified
    for member in ("build_project_sql_requirement_report", "classify", "build_summary"):
        monkeypatch.setattr(report, member, forbidden)
    for _, _, source, value, checked, _ in products:
        assert report.verify_project_sql_requirement_report(value, source).verified
        assert (
            report.inspect_project_sql_requirement_report(checked).entries
            is value.entries
        )


def test_plan_verification_does_not_require_a_report(corpus, monkeypatch):
    roots, plan, _, _, _, _ = corpus["row", P.BIND_SAFE_LITERALS]

    def forbidden(*args, **kwargs):
        pytest.fail("Plan verification depends on its optional report")

    for name in (
        "build_project_sql_requirement_report",
        "verify_project_sql_requirement_report",
        "classify",
        "context_index",
        "index_members",
        "build_summary",
    ):
        monkeypatch.setattr(report, name, forbidden)
    assert verify_project_sql_plan(
        plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
    ).verified


def test_uninitialized_report_verification_has_a_controlled_rejection():
    missing = object.__new__(report.ProjectSQLRequirementVerification)
    with pytest.raises(ValueError, match="VERIFIED"):
        report.inspect_project_sql_requirement_report(missing)


@pytest.mark.parametrize("failure", (KeyError, ValueError))
def test_report_errors_do_not_dump_source_payloads(corpus, monkeypatch, failure):
    source = corpus["literal_tags", P.BIND_SAFE_LITERALS][2]
    marker = "private-authored-payload-marker"

    def fail(*args, **kwargs):
        raise failure(marker)

    monkeypatch.setattr(report, "_build_report", fail)
    with pytest.raises(ValueError) as raised:
        report.build_project_sql_requirement_report(source)
    assert marker not in "".join(traceback.format_exception(raised.value))


def test_mixed_source_descriptors_remain_unassessed(tmp_path):
    text = join_source("inner", "true").replace(
        'source rhs: Row is postgres.table("rhs")',
        'source rhs: Row is mysql.table("rhs")',
    )
    _, plan, _, value, _, view = _reported(_roots(tmp_path, text), P.PRESERVE_LITERALS)
    demands = view.for_family(F.SOURCE)
    assert len(demands) == len(plan.sources) == 2
    families = []
    for entry in demands:
        demand = entry.demand
        assert type(demand) is sql.ProjectSQLSourceRealizationDemand
        callee = demand.source.connector.callee
        assert type(callee) is DottedNameExpr
        families.append(callee.parts[0])
    assert families == ["postgres", "mysql"]
    assert value.summary.target is report.ProjectSQLReportTargetPosture.NOT_ASSESSED


def test_unhandled_report_taxonomy_is_closed(corpus):
    with pytest.raises(ValueError, match="variant"):
        report.classify(object(), {})
    plan = corpus["join", P.BIND_SAFE_LITERALS][1]
    demand = next(d for d in plan.demands if type(d) is joins.ProjectSQLJoinDemand)
    nodes, _, _ = report.context_index(plan)
    with pytest.raises(ValueError, match="subkind"):
        report.classify(_graft(demand, kind="join_rows"), nodes)
