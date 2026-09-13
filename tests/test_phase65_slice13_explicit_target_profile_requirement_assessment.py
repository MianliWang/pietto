"""Real neutral plans, declared profiles, exact compiler facts and hostile products."""

from dataclasses import replace
from types import MappingProxyType
from typing import cast
from pathlib import Path
import sys
import traceback

import pytest

from pietto._project import project_sql_plan_target_assessment as target
from pietto._project import project_sql_plan_target_mapping as mapping
from pietto._project import project_sql_plan_requirements as reports
from pietto._project import project_sql_plan_source_maps as maps
from pietto._project import project_sql_plan_literals as literals
from pietto.ast_nodes import TypeDef, LiteralExpr
from pietto.semantic.capability_facts import CapabilityKey
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto.semantic import capability_inventory as inventory
from pietto.semantic import capability_signatures as signatures
from pietto.semantic import capability_aggregates as aggregates
from pietto.semantic import capability_windows as windows
from pietto.semantic import capability_providers as providers
from pietto.semantic.capability_composition import CapabilityProfileCompositionSuccess
from pietto.semantic.capability_facts import (
    CapabilityDomain as D,
    CapabilitySupport,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import (
    Found,
    Absent,
    Unknown,
    Conflict,
    lookup_capability,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
    CapabilityProfileIdentity,
    CapabilityProfileReference,
    CapabilityProfileKind,
    CapabilityProfileSchemaVersion,
    StaticCapabilityProfile,
    CapabilityProfileFactOccurrence,
    CapabilityProfileBaseOccurrence,
)
from test_phase65_slice11_complete_demand_obligation_report import (
    corpus as corpus,
    _cases,
    _reported,
    _roots,
    P,
    F,
)
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _graft
from test_phase65_slice4_row_scalar_let_where_stage_value_planning import (
    _source as row_source,
    ROW_BODY,
)
from test_phase65_slice7_windows_named_window_qualify_staging import _family_source
from test_phase65_slice6_grouped_global_satisfying_block_boundaries import _ordinary
from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
    _repeated_sets,
)

S = target.AspectOutcome


def _database(family="postgresql", release="18"):
    return CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE, family, release
    )


def _profile(
    database,
    facts=(),
    *,
    name="declared",
    base=None,
    extension="test.extension",
    extension_release="1",
):
    """Explicit test declarations about real compiler facts, not observed DB support."""
    reference = CapabilityProfileReference(
        CapabilityProfileIdentity("slice13", name), "profile-release-7"
    )
    profile_target = (
        database
        if base is None
        else CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            database.family,
            database.release,
            extension,
            extension_release,
        )
    )
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        reference,
        profile_target,
        CapabilityProfileKind.BASE if base is None else CapabilityProfileKind.OVERLAY,
        ()
        if base is None
        else (CapabilityProfileBaseOccurrence(reference, 0, base.profile),),
        tuple(
            CapabilityProfileFactOccurrence(reference, i, fact)
            for i, fact in enumerate(facts)
        ),
    )


REAL_FACTS = (
    *inventory._LOGICAL_TYPE_FACTS,
    *inventory._LITERAL_FACTS,
    *signatures._CAPABILITY_SIGNATURE_FACTS,
    *aggregates._AGGREGATE_SIGNATURE_FACTS,
    *windows._WINDOW_SIGNATURE_FACTS,
)


def _request(family="postgresql", release="18", facts=REAL_FACTS):
    database = _database(family, release)
    return target.prepare_project_sql_target_request(
        database, base=_profile(database, facts)
    )


def _assessed(record, request=None):
    _, plan, source, report, checked, _ = record
    request = _request() if request is None else request
    product = target.build_project_sql_target_assessment(
        source, request, report_verification=checked
    )
    verification = target.verify_project_sql_target_assessment(product, source, request)
    assert verification.verified, verification.issues
    view = target.inspect_project_sql_target_assessment(verification)
    assert product.report is report and product.report_verification is checked
    assert product.source_verification is source and product.report.plan is plan
    return product, verification, view


@pytest.mark.parametrize("policy", tuple(P))
@pytest.mark.parametrize("name", tuple(_cases()))
def test_complete_real_inventory_exact_roots_queries_and_nonpositive_full_result(
    corpus, name, policy
):
    record = corpus[name, policy]
    product, _, view = _assessed(record)
    report = record[3]
    assert len(product.demands) == len(report.entries)
    assert view.summary.posture is target.AssessmentPosture.INCOMPLETE
    assert view.summary.original_obligations is report.summary
    assert report.summary.target is reports.ProjectSQLReportTargetPosture.NOT_ASSESSED
    assert product.summary.pending_realizations
    assert view.for_outcome(S.UNMAPPED)
    assert [a for d in product.demands for a in d.aspects] == list(product.aspects)
    for entry, demand in zip(report.entries, view.demands, strict=True):
        assert demand.entry is entry
        assert view.demand(entry.ref) is demand
        assert demand.posture is target.AssessmentPosture.INCOMPLETE
        for ordinal, aspect in enumerate(demand.aspects):
            assert view.aspect(entry.ref, ordinal) is aspect
            assert aspect.entry is entry and aspect.proposition.witness is entry.demand
            assert view.lookup(aspect) is aspect.lookup
            if aspect.lookup is not None:
                assert aspect in view.uses(aspect.lookup)
    for outcome in S:
        assert view.for_outcome(outcome) == tuple(
            a for a in product.aspects if outcome in a.outcomes
        )
    for query in view.lookups:
        assert query.request is product.request
        assert query.inputs.key is query.key
        assert query.key.dialect is query.key.extension is None
        assert query.key.domain is not D.PARAMETER
    for name in ("ready", "executable", "installed", "fulfilled"):
        assert not hasattr(view.summary, name)


@pytest.mark.parametrize("policy", tuple(P))
def test_omission_complete_denominator_zero_provider_calls(corpus, monkeypatch, policy):
    def forbidden(*args, **kwargs):
        raise AssertionError("omission must not acquire providers")

    monkeypatch.setattr(providers, "canonical_capability_provider_inputs", forbidden)
    request = target.prepare_project_sql_target_request()
    product, _, view = _assessed(corpus["literal_tags", policy], request)
    assert not product.lookups
    assert all(a.outcomes == (S.NOT_ASSESSED,) for a in product.aspects)
    assert all(
        d.posture is target.AssessmentPosture.NOT_ASSESSED for d in product.demands
    )
    assert view.summary.posture is target.AssessmentPosture.NOT_ASSESSED
    assert view.summary.demand_count == len(product.report.entries)


@pytest.mark.parametrize("family,release", [("postgresql", "18"), ("mysql", "8.4")])
def test_explicit_releases_profile_overlay_roots_and_sharing(
    corpus, family, release, monkeypatch
):
    database = _database(family, release)
    base = _profile(database, REAL_FACTS[:3])
    overlay = _profile(
        database,
        REAL_FACTS[3:],
        name="overlay",
        base=base,
        extension_release="ext-release-2",
    )
    request = target.prepare_project_sql_target_request(
        database, base=base, overlays=(overlay,)
    )
    assert type(request.composition) is CapabilityProfileCompositionSuccess
    assert request.composition.base is base and request.composition.overlays == (
        overlay,
    )
    calls = []
    provider = providers.canonical_capability_provider_inputs

    def counted(key):
        calls.append(key)
        return provider(key)

    monkeypatch.setattr(providers, "canonical_capability_provider_inputs", counted)
    product, _, view = _assessed(corpus["row", P.BIND_SAFE_LITERALS], request)
    assert len(calls) == len(product.lookups)
    assert any(len(view.uses(q)) > 1 for q in product.lookups)
    assert all(
        q.profile_occurrences is request.composition.effective_occurrences
        for q in product.lookups
    )
    assert view.target is database
    assert database.release != base.profile.release != overlay.target.extension_release
    assert (
        product.report.plan.scope.completed.semantic_result.compilation_mode.value
        == "explicit_modules"
    )


def test_real_compiler_positive_subpropositions_do_not_certify_composites(corpus):
    seen = set()
    satisfied = set()
    for name in (
        "row",
        "literal_tags",
        "aggregate",
        "hidden_window",
        "window_arguments",
    ):
        product, _, _ = _assessed(corpus[name, P.BIND_SAFE_LITERALS])
        for aspect in product.aspects:
            query = aspect.lookup
            if (
                query is not None
                and type(query.provider_result) is Found
                and query.provider_result.fact.support is CapabilitySupport.SUPPORTED
            ):
                seen.add(query.key.domain)
                if S.SATISFIED in aspect.outcomes:
                    satisfied.add(query.key.domain)
        for demand in product.demands:
            assert demand.posture is target.AssessmentPosture.INCOMPLETE
        for demand in product.demands:
            if demand.entry.family is F.LITERAL:
                assert isinstance(demand.entry.demand, literals.ProjectSQLLiteralDemand)
                assert (
                    tuple(
                        a.proposition.gap
                        for a in demand.aspects
                        if a.proposition.kind is mapping.K.RESIDUAL
                    )
                    == demand.entry.demand.requirements
                )
                assert demand.entry.demand.contexts
    expected = {
        D.LOGICAL_TYPE,
        D.LITERAL,
        D.BINARY_OPERATOR,
        D.COMPARISON,
        D.AGGREGATE,
        D.WINDOW_FUNCTION,
    }
    assert expected <= seen
    assert expected <= satisfied


@pytest.mark.parametrize(
    "call,frame",
    [
        ("row_number()", None),
        ("rank()", None),
        ("dense_rank()", None),
        ("percent_rank()", None),
        ("cume_dist()", None),
        ("ntile(3)", None),
        ("lag(value, 2, 0)", None),
        ("lead(value)", None),
        ("first_value(value)", "rows between unbounded preceding and current row"),
        ("last_value(value)", "rows between unbounded preceding and current row"),
        ("nth_value(value, 2)", "rows between unbounded preceding and current row"),
    ],
)
def test_real_window_signature_scope_is_separate_from_frame_and_qualify(
    tmp_path, call, frame
):
    source = _family_source(call, frame, True, "query", "postgres")
    record = _reported(_roots(tmp_path, source), P.PRESERVE_LITERALS)
    product, _, _ = _assessed(record)
    queries = [q for q in product.lookups if q.key.domain is D.WINDOW_FUNCTION]
    assert queries and all(type(q.provider_result) is Found for q in queries)
    assert all(
        q.key.operation == "signature" and q.key.context == "window_signature"
        for q in queries
    )
    windows = [d for d in product.demands if d.entry.family is F.WINDOW]
    assert all(d.posture is target.AssessmentPosture.INCOMPLETE for d in windows)


@pytest.mark.parametrize("family", ["postgresql", "mysql"])
def test_source_family_bridge_known_mismatch_mixed_and_connection_residual(
    tmp_path, family
):
    source = row_source(ROW_BODY)
    source = source.replace("query result:", "table first:")
    source += 'source other: Row is mysql.table("other")\nquery result:\n    union all:\n        from first\n        from other\n'
    # Align positional outputs while preserving both real source descriptors.
    source = (
        source[: source.index("table first:")]
        + "table first:\n    from rows\n    select:\n        id\n        key\n        flag\n"
        + source[source.index("source other") :]
    )
    record = _reported(_roots(tmp_path, source), P.PRESERVE_LITERALS)
    product, _, view = _assessed(
        record, _request(family, "18" if family == "postgresql" else "8.4")
    )
    aspects = [
        a for a in product.aspects if a.proposition.kind is mapping.K.SOURCE_FAMILY
    ]
    assert len(aspects) == 2
    assert sum(a.outcomes == (S.NEGATIVE,) for a in aspects) == 1
    assert sum(a.outcomes == (S.SATISFIED,) for a in aspects) == 1
    assert view.summary.posture is target.AssessmentPosture.INCOMPLETE
    assert (
        len(
            [a for a in view.summary.pending_realizations if a.entry.family is F.SOURCE]
        )
        == 2
    )


def _declaration(
    fact,
    support=CapabilitySupport.SUPPORTED,
    *,
    dialect=None,
    label="synthetic-declaration",
):
    return replace(
        fact,
        support=support,
        evidence=(
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST, __file__, label, dialect=dialect
            ),
        ),
    )


def test_partial_negative_conflicting_profiles_keep_both_raw_channels(corpus):
    fact = next(f for f in inventory._LOGICAL_TYPE_FACTS if f.key.subject == "Int")
    database = _database()
    positive, negative = (
        _declaration(fact),
        _declaration(
            fact, CapabilitySupport.EXPLICITLY_UNSUPPORTED, label="synthetic-negative"
        ),
    )
    for facts, expected in (
        ((), Unknown),
        ((negative,), Found),
        ((positive, negative), Conflict),
    ):
        request = target.prepare_project_sql_target_request(
            database, base=_profile(database, facts)
        )
        product, _, view = _assessed(corpus["row", P.BIND_SAFE_LITERALS], request)
        lookups = [q for q in view.lookups if q.key == fact.key]
        assert lookups
        for query in lookups:
            assert type(query.profile_result) is expected
            assert (
                type(query.provider_result) is Found
                and query.provider_result.fact is fact
            )
            if expected is Conflict:
                assert isinstance(query.profile_result, Conflict)
                assert query.profile_result.evidence == (positive, negative)
                assert all(a.outcomes == (S.CONFLICT,) for a in view.uses(query))
            elif facts:
                assert all(a.outcomes == (S.NEGATIVE,) for a in view.uses(query))
        assert view.for_outcome(S.UNKNOWN)
        assert view.for_outcome(S.UNMAPPED)
        assert product.summary.posture is target.AssessmentPosture.INCOMPLETE


def test_missing_mismatched_and_blocked_profile_are_explicit_inputs(corpus):
    database = _database()
    foreign = _profile(_database("postgresql", "17"), REAL_FACTS)
    good = _profile(database)
    overlay = _profile(_database("mysql", "8.4"), name="wrong", base=good)
    requests = [
        target.prepare_project_sql_target_request(database),
        target.prepare_project_sql_target_request(database, base=foreign),
        target.prepare_project_sql_target_request(
            database, base=good, overlays=(overlay,)
        ),
    ]
    for request in requests:
        product, _, view = _assessed(corpus["minimal", P.PRESERVE_LITERALS], request)
        assert request.issues and product.lookups
        assert view.summary.posture is target.AssessmentPosture.INCOMPLETE
        assert view.for_outcome(S.INPUT_UNRESOLVED)
        if isinstance(request.composition, CapabilityProfileCompositionSuccess):
            assert all(type(q.profile_result) is Found for q in view.lookups)
            assert all(
                q.profile_occurrences is request.composition.effective_occurrences
                for q in view.lookups
            )
        else:
            assert all(type(q.profile_result) is Unknown for q in view.lookups)
        assert all(q.profile_applicable is False for q in view.lookups)
    assert target.TargetInputIssue.PROFILE_MISSING in requests[0].issues
    assert target.TargetInputIssue.TARGET_MISMATCH in requests[1].issues
    assert target.TargetInputIssue.COMPOSITION_BLOCKED in requests[2].issues


def test_new_equal_content_targets_releases_and_profiles_never_share_queries(corpus):
    record = corpus["row", P.BIND_SAFE_LITERALS]
    first, _, _ = _assessed(record, _request())
    for request in (_request(), _request(release="17"), _request("mysql", "8.4")):
        second, _, _ = _assessed(record, request)
        assert first.report.plan is second.report.plan
        common = [
            (q, r) for q in first.lookups for r in second.lookups if q.key == r.key
        ]
        assert common and all(q is not r for q, r in common)
        assert not target.verify_project_sql_target_assessment(
            first, record[2], request
        ).verified
    assert not target.verify_project_sql_target_assessment(
        first, _graft(record[2]), first.request
    ).verified


@pytest.mark.parametrize(
    "name",
    ["join", "path", "partial_path", "aggregate", "hidden_order", "set_membership"],
)
def test_original_proofs_warning_risks_and_membership_remain_unfulfilled(corpus, name):
    product, _, view = _assessed(corpus[name, P.BIND_SAFE_LITERALS])
    report = product.report
    assert view.summary.original_obligations is report.summary
    assert report.links is product.report.links
    assert (
        report.summary.original_proved
        or report.summary.enforcement_required
        or report.summary.aggregate_evidence
        or report.summary.pending_realizations
    )
    for demand in product.demands:
        assert demand.entry is report.entries[demand.position]
    if name == "set_membership":
        assert report.summary.enforcement_required
        assert product.report.plan.result_limits[0].value == 0


def test_depth12_shared_definition_control_keeps_defining_occurrences(tmp_path):
    record = _reported(_roots(tmp_path, _repeated_sets(12)), P.BIND_SAFE_LITERALS)
    product, _, view = _assessed(record)
    assert len(product.report.plan.bindings.definitions) == 15
    assert len(product.report.plan.input_uses) == 26
    assert len(product.demands) == len(product.report.plan.demands)
    assert len({d.entry.ref for d in product.demands}) == len(product.demands)
    assert any(len(view.uses(q)) > 1 for q in product.lookups)


def test_optional_inspection_report_map_interoperability(corpus):
    record = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    view = inspect_project_sql_plan(record[2]).target_assessment(
        _request(), report_verification=record[4]
    )
    source_map = maps.build_project_sql_source_map(record[2])
    map_view = maps.inspect_project_sql_source_map(
        maps.verify_project_sql_source_map(source_map, record[2])
    )
    for demand in view.demands:
        entry = demand.entry
        assert record[5].entry(entry.ref) is entry
        assert map_view.origin(entry.origin.ref).original is entry.origin
        assert map_view.subject(entry.ref).origins
    assert view.for_outcome(S.ABSENT) == ()
    assert (
        view.lookup(
            next(
                a
                for a in view.assessment.aspects
                if a.proposition.kind is mapping.K.RESIDUAL
            )
        )
        is None
    )


def test_independent_verification_and_ordinary_products_need_no_acquisition(
    corpus, monkeypatch
):
    record = corpus["aggregate", P.BIND_SAFE_LITERALS]
    product, _, _ = _assessed(record)

    def forbidden(*args, **kwargs):
        raise AssertionError("verification must consume retained evidence")

    for module, names in (
        (
            target,
            (
                "build_project_sql_target_assessment",
                "prepare_project_sql_target_request",
                "compose_capability_profiles",
                "_outcomes",
                "_posture",
                "_applicable",
            ),
        ),
        (
            mapping,
            (
                "build_propositions",
                "_type_key",
                "_scalar_key",
                "_aggregate_key",
                "_window_key",
                "_literal_key",
                "aggregate_inputs",
            ),
        ),
        (
            providers,
            (
                "canonical_capability_provider_inputs",
                "inventory_lookup_inputs",
                "signature_lookup_inputs",
                "aggregate_lookup_inputs",
                "window_lookup_inputs",
            ),
        ),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    checked = target.verify_project_sql_target_assessment(
        product, record[2], product.request
    )
    assert checked.verified, checked.issues
    assert (
        target.inspect_project_sql_target_assessment(checked).summary is product.summary
    )
    assert verify_project_sql_plan(
        record[1], *record[0], literal_policy=P.BIND_SAFE_LITERALS
    ).verified
    assert reports.verify_project_sql_requirement_report(record[3], record[2]).verified
    source_map = maps.build_project_sql_source_map(record[2])
    assert maps.verify_project_sql_source_map(source_map, record[2]).verified


def _reject(value, source, request):
    checked = target.verify_project_sql_target_assessment(value, source, request)
    assert not checked.verified
    with pytest.raises(ValueError, match="exact current VERIFIED"):
        target.inspect_project_sql_target_assessment(checked)
    forged = _graft(checked, issues=())
    with pytest.raises(ValueError, match="exact current VERIFIED"):
        target.inspect_project_sql_target_assessment(forged)


def test_complete_product_deletion_and_false_summary_mutations(corpus):
    record = corpus["set_membership", P.BIND_SAFE_LITERALS]
    product, _, _ = _assessed(record)
    changes = [
        {"demands": ()},
        {"aspects": ()},
        {"lookups": ()},
        {"uses": MappingProxyType({})},
        {"by_demand": MappingProxyType({})},
        {"request_roots": tuple(list(product.request_roots))},
        {"demands": tuple(d for d in product.demands if d.entry.family is not F.SET)},
        {
            "summary": _graft(
                product.summary, posture=target.AssessmentPosture.SATISFIED
            )
        },
        {"summary": _graft(product.summary, demand_count=True)},
        {"summary": _graft(product.summary, aspect_count=0)},
        {"summary": _graft(product.summary, query_count=True)},
        {"summary": _graft(product.summary, pending_realizations=())},
        {"summary": _graft(product.summary, categories=MappingProxyType({}))},
        {
            "summary": _graft(
                product.summary,
                original_obligations=_graft(
                    product.report.summary, enforcement_required=()
                ),
            )
        },
        {"report": _graft(product.report, links=())},
        {
            "report_verification": _graft(
                product.report_verification, source_verification=_graft(record[2])
            )
        },
    ]
    for fields in changes:
        _reject(_graft(product, **fields), record[2], product.request)


def test_aspect_query_evidence_and_bool_mutations(corpus):
    record = corpus["row", P.BIND_SAFE_LITERALS]
    product, _, _ = _assessed(record)
    demand = next(d for d in product.demands if any(a.lookup for a in d.aspects))
    aspect = next(a for a in demand.aspects if a.lookup is not None)
    query = cast(target.ProjectSQLTargetLookup, aspect.lookup)
    modifications = [
        _graft(aspect, ordinal=True),
        _graft(aspect, position=True),
        _graft(aspect, entry=_graft(aspect.entry)),
        _graft(aspect, lookup=None),
        _graft(aspect, outcomes=(S.SATISFIED,)),
        _graft(
            aspect,
            proposition=_graft(
                aspect.proposition, witness=product.demands[-1].entry.demand
            ),
        ),
        _graft(
            aspect,
            proposition=_graft(
                aspect.proposition, key=replace(query.key, dialect="mysql")
            ),
        ),
    ]
    # Select an unresolved aspect for a meaningful false-positive transition.
    residual = demand.aspects[-1]
    modifications.append(_graft(residual, outcomes=(S.SATISFIED,)))
    for changed in modifications:
        local = tuple(
            changed if a.position == changed.position else a for a in demand.aspects
        )
        broken_demand = _graft(demand, aspects=local)
        broken = _graft(
            product,
            demands=tuple(broken_demand if d is demand else d for d in product.demands),
        )
        _reject(broken, record[2], product.request)
    assert type(query.provider_result) is Found
    foreign_fact = _declaration(query.provider_result.fact)
    inputs = query.inputs
    wrong_queries = [
        _graft(query, position=True),
        _graft(query, request=_request()),
        _graft(
            query, inputs=replace(inputs, domain_complete=not inputs.domain_complete)
        ),
        _graft(query, inputs=replace(inputs, facts=())),
        _graft(query, provider_result=Found(foreign_fact)),
        _graft(query, profile_occurrences=()),
        _graft(query, profile_result=Unknown(CapabilityReasonCode.NOT_EVIDENCED)),
    ]
    for wrong in wrong_queries:
        _reject(
            _graft(
                product,
                lookups=tuple(wrong if q is query else q for q in product.lookups),
            ),
            record[2],
            product.request,
        )


def test_stale_envelope_roots_and_foreign_queries_reject(corpus):
    record = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    product, checked, view = _assessed(record)
    fresh = verify_project_sql_plan(
        record[1],
        *record[0],
        literal_policy=P.BIND_SAFE_LITERALS,
        envelope=_graft(record[1].fixed_envelope),
    )
    _reject(product, fresh, product.request)
    for ref in (
        record[1].bindings.definitions[0].ref,
        record[3].entries[0].origin.ref,
        _graft(record[3].entries[0].ref),
    ):
        with pytest.raises(ValueError, match="owned demand"):
            view.demand(ref)
    for ordinal in (True, -1, 999):
        with pytest.raises(ValueError, match="owned aspect ordinal"):
            view.aspect(record[3].entries[0].ref, ordinal)
    with pytest.raises(ValueError, match="owned lookup"):
        view.uses(_graft(product.lookups[0]))
    with pytest.raises(ValueError, match="owned aspect"):
        view.lookup(_graft(product.aspects[0]))
    with pytest.raises(ValueError, match="exact outcome"):
        view.for_outcome(cast(target.AspectOutcome, "not_assessed"))
    _reject(
        _graft(product, request=_graft(product.request)),
        checked.source_verification,
        product.request,
    )


def test_synthetic_lookup_state_mechanics_preserve_simultaneous_categories(corpus):
    """Synthetic raw inputs exercise algebra only; never a verified plan positive."""
    product, _, _ = _assessed(corpus["row", P.BIND_SAFE_LITERALS])
    aspect = next(a for a in product.aspects if a.lookup is not None)
    query = cast(target.ProjectSQLTargetLookup, aspect.lookup)
    assert type(query.provider_result) is Found
    positive = _declaration(query.provider_result.fact)
    negative = _declaration(
        positive, CapabilitySupport.EXPLICITLY_UNSUPPORTED, label="synthetic-negative"
    )
    conflict = lookup_capability(query.key, (positive, negative), domain_complete=False)
    assert type(conflict) is Conflict
    absent = lookup_capability(query.key, (), domain_complete=True)
    unknown = lookup_capability(query.key, (), domain_complete=False)
    assert type(absent) is Absent and type(unknown) is Unknown
    for provider, profile, expected in (
        (absent, conflict, {S.ABSENT, S.CONFLICT}),
        (unknown, Found(negative), {S.UNKNOWN, S.NEGATIVE}),
        (Found(negative), conflict, {S.NEGATIVE, S.CONFLICT}),
    ):
        synthetic = _graft(query, provider_result=provider, profile_result=profile)
        assert (
            set(target._outcomes(aspect.proposition, synthetic, product.request))
            == expected
        )
    assert (
        target._posture(product.request.target, ())
        is target.AssessmentPosture.INCOMPLETE
    )
    # Aggregation mechanics on a positive subset never certify the full product.
    positive_aspect = next(a for a in product.aspects if a.outcomes == (S.SATISFIED,))
    assert (
        target._posture(product.request.target, (positive_aspect,))
        is target.AssessmentPosture.SATISFIED
    )
    assert product.summary.posture is target.AssessmentPosture.INCOMPLETE


def test_actual_taxonomy_and_precise_scalar_and_type_propositions(corpus):
    assert set(mapping.SUPPORTED_VARIANTS) == set(reports.DEMAND_FAMILIES)
    actual = {}
    for record in corpus.values():
        for entry in record[3].entries:
            actual.setdefault(entry.family.value, set()).add(
                None if entry.subkind is None else entry.subkind.value
            )
    assert actual == {f: set(kinds) for f, kinds in mapping.SUPPORTED_SUBKINDS.items()}
    product, _, _ = _assessed(corpus["row", P.BIND_SAFE_LITERALS])
    keys = {q.key for q in product.lookups}
    assert (
        CapabilityKey(
            D.BINARY_OPERATOR, "Int", "+", ("Int", "Int", "unknown"), "expression"
        )
        in keys
    )
    assert (
        CapabilityKey(
            D.LOGICAL_TYPE, "Int", "catalog_membership", context="builtin_registry"
        )
        in keys
    )
    entry = product.report.entries[0]
    assert not mapping.check_propositions(
        _graft(entry, family="source_realization"), (), {}
    )


@pytest.mark.parametrize(
    "call,operators",
    [
        ("count(len(label))", {"len"}),
        ("count_distinct(lower(trim(label)))", {"lower", "trim"}),
    ],
)
def test_real_scalar_transform_signatures_leave_composite_aggregate_unmapped(
    tmp_path, call, operators
):
    text = _ordinary(f"    select:\n        total = {call}\n").replace(
        "    value: Int nullable\n",
        "    value: Int nullable\n    label: Text nullable\n",
    )
    record = _reported(_roots(tmp_path, text), P.BIND_SAFE_LITERALS)
    product, _, view = _assessed(record)
    queries = [q for q in product.lookups if q.key.domain is D.SCALAR_FUNCTION]
    assert {q.key.operation for q in queries} == operators
    assert all(type(q.provider_result) is Found for q in queries)
    assert all(a.outcomes == (S.SATISFIED,) for q in queries for a in view.uses(q))
    assert any(
        a.proposition.gap is mapping.MappingGap.AGGREGATE_UNMODELED
        for a in product.aspects
    )


def test_original_alias_decimal_provenance_is_not_a_builtin_rewrite(tmp_path):
    text = 'type Money = Decimal(12, 2)\nshape Row:\n    amount: Money nullable\nsource rows: Row is postgres.table("rows")\nquery result:\n    from rows\n    select:\n        amount\n'
    record = _reported(_roots(tmp_path, text), P.PRESERVE_LITERALS)
    product, _, _ = _assessed(record)
    keys = {q.key for q in product.lookups}
    assert (
        CapabilityKey(
            D.LOGICAL_TYPE, "Decimal", "catalog_membership", context="builtin_registry"
        )
        in keys
    )
    # Upstream has already resolved Money to Decimal. Assessment consumes that
    # exact result and retains the original alias and precision/scale witnesses.
    declarations = [
        origin.owner.definition
        for origin in record[1].origins
        if isinstance(origin.owner.definition, TypeDef)
    ]
    assert declarations and all(
        declaration is declarations[0] for declaration in declarations
    )
    declaration = declarations[0]
    assert declaration.name == "Money" and declaration.base.name == "Decimal"
    arguments = declaration.base.arguments
    assert all(isinstance(argument.value, LiteralExpr) for argument in arguments)
    assert len(arguments) == 2
    assert cast(LiteralExpr, arguments[0].value).value == 12
    assert cast(LiteralExpr, arguments[1].value).value == 2
    assert product.report.plan.origins is record[1].origins
    for demand in product.demands:
        assert demand.entry.demand is record[1].demands[demand.position]
    assert product.summary.posture is target.AssessmentPosture.INCOMPLETE


@pytest.mark.parametrize(
    "release,selected", [("18", False), ("18", True), ("17", True)]
)
def test_supplied_catalog_context_is_retained_unmapped_not_selection_or_installation(
    corpus, monkeypatch, release, selected
):
    import test_phase57_slice8_extension_signature_provider_checking_integration as ext
    from pietto.semantic.extension_catalog import (
        ExtensionCatalogLookupScope,
        ExtensionCatalogEntryFamily,
        PostgreSQLCallableIdentity,
    )
    from pietto._project import extension_signature_provider

    requested = ext._target(
        database_release=release, extension_release="extension-release-9"
    )
    selection = (
        ext._selection(ext._catalog(target=requested))
        if selected
        else ext._undeclared_selection(requested)
    )
    scope = ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity("missing", (ext.slice5._builtin(),)),
    )
    context = ext._context(
        ext._requirements(ext._key("missing")), (0, scope, selection)
    )
    database = _database()
    request = target.prepare_project_sql_target_request(
        database, base=_profile(database, REAL_FACTS), catalog_context=context
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No plan demand supplies this extension selector")

    monkeypatch.setattr(
        extension_signature_provider,
        "extension_signature_provider_authority",
        forbidden,
    )
    monkeypatch.setattr(
        extension_signature_provider, "extension_signature_provider_inputs", forbidden
    )
    product, _, view = _assessed(corpus["row", P.BIND_SAFE_LITERALS], request)
    (residual,) = view.summary.catalog_residuals
    assert (
        residual.context is context
        and residual.selector is context.selectors.occurrences[0]
    )
    assert residual.selection is context.selections[0]
    assert target.TargetInputIssue.CATALOG_UNMAPPED in residual.issues
    assert (target.TargetInputIssue.CATALOG_TARGET_MISMATCH in residual.issues) is (
        release != "18"
    )
    assert all(q.key.domain is not D.EXTENSION_SIGNATURE for q in product.lookups)
    assert view.for_outcome(S.SATISFIED)
    assert not view.for_outcome(S.INPUT_UNRESOLVED)
    assert view.summary.posture is target.AssessmentPosture.INCOMPLETE
    second, _, _ = _assessed(corpus["row", P.BIND_SAFE_LITERALS], _request())
    assert all(q is not r for q in product.lookups for r in second.lookups)


def test_verification_and_inspection_do_not_infer_prove_render_or_read(
    corpus, monkeypatch
):
    record = corpus["partial_path", P.BIND_SAFE_LITERALS]
    product, checked, _ = _assessed(record)

    def forbidden(*args, **kwargs):
        raise AssertionError("Assessment crossed an upstream or runtime boundary")

    names = (
        "infer_row_expression",
        "resolve_named_window_namespace",
        "build_project_completed_semantic_result",
        "build_project_query_block_ir",
        "build_project_sql_plan",
        "build_project_sql_bindings",
        "analyze_window_expression",
        "resolve_project_joined_namespace_reference",
        "parse_source",
        "canonical_capability_provider_inputs",
        "build_project_sql_target_assessment",
        "_build_assessment",
        "compose_capability_profiles",
    )
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pietto.") and module is not None:
            for member in names:
                if hasattr(module, member):
                    monkeypatch.setattr(module, member, forbidden)
            if name.startswith("pietto.sql."):
                for member in tuple(vars(module)):
                    if member.startswith("render") and callable(
                        getattr(module, member)
                    ):
                        monkeypatch.setattr(module, member, forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert target.verify_project_sql_target_assessment(
        product, record[2], product.request
    ).verified
    assert (
        target.inspect_project_sql_target_assessment(checked).summary is product.summary
    )


def _rewire_query(product, original, changed):
    """Keep indexes consistent so mutations reach the actual evidence checker."""
    aspects = tuple(
        _graft(a, lookup=changed) if a.lookup is original else a
        for a in product.aspects
    )
    demands = tuple(
        _graft(d, aspects=tuple(aspects[a.position] for a in d.aspects))
        for d in product.demands
    )
    queries = tuple(changed if q is original else q for q in product.lookups)
    summary = _graft(
        product.summary,
        categories=MappingProxyType(
            {s: tuple(a for a in aspects if s in a.outcomes) for s in S}
        ),
        pending_realizations=tuple(
            a for a in aspects if a.proposition.kind is mapping.K.RESIDUAL
        ),
    )
    return _graft(
        product,
        demands=demands,
        aspects=aspects,
        lookups=queries,
        by_demand=MappingProxyType({d.entry.ref: d for d in demands}),
        uses=MappingProxyType(
            {q: tuple(a for a in aspects if a.lookup is q) for q in queries}
        ),
        summary=summary,
    )


def test_coherent_foreign_facts_false_completeness_and_lookup_substitution(corpus):
    record = corpus["row", P.BIND_SAFE_LITERALS]
    product, _, _ = _assessed(record)
    query = next(q for q in product.lookups if type(q.provider_result) is Found)
    assert isinstance(query.provider_result, Found)
    fact = query.provider_result.fact
    replacement = _declaration(fact)
    inputs = _graft(
        query.inputs,
        facts=tuple(replacement if f is fact else f for f in query.inputs.facts),
    )
    changes = (
        _graft(query, inputs=inputs, provider_result=Found(replacement)),
        _graft(
            query,
            inputs=_graft(
                query.inputs, domain_complete=not query.inputs.domain_complete
            ),
        ),
        _graft(query, inputs=_graft(query.inputs, facts=query.inputs.facts[::-1])),
        _graft(query, profile_occurrences=()),
        _graft(query, provider_result=Unknown(CapabilityReasonCode.NOT_EVIDENCED)),
    )
    for changed in changes:
        broken = _rewire_query(product, query, changed)
        verification = target.verify_project_sql_target_assessment(
            broken, record[2], product.request
        )
        assert verification.issues == (target.TargetAssessmentIssue.EVIDENCE,)


@pytest.mark.parametrize("failure", (KeyError, ValueError))
def test_errors_are_closed_without_payload_or_exception_chain(
    corpus, monkeypatch, failure
):
    record = corpus["minimal", P.PRESERVE_LITERALS]
    request = _request()

    def fail(*args, **kwargs):
        raise failure("private-source-payload-marker")

    monkeypatch.setattr(target, "_build_assessment", fail)
    with pytest.raises(ValueError) as raised:
        target.build_project_sql_target_assessment(record[2], request)
    assert "private-source-payload-marker" not in "".join(
        traceback.format_exception(raised.value)
    )
    missing = object.__new__(target.ProjectSQLTargetAssessmentVerification)
    with pytest.raises(ValueError, match="VERIFIED"):
        target.inspect_project_sql_target_assessment(missing)


def test_wrong_release_retains_raw_conflict_separate_from_applicability(corpus):
    fact = next(f for f in inventory._LOGICAL_TYPE_FACTS if f.key.subject == "Int")
    positive = _declaration(fact)
    negative = _declaration(
        fact,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        label="synthetic-other-release-negative",
    )
    declared = _profile(_database(release="17"), (positive, negative))
    request = target.prepare_project_sql_target_request(
        _database(release="18"), base=declared
    )
    product, _, view = _assessed(corpus["row", P.BIND_SAFE_LITERALS], request)
    assert isinstance(request.composition, CapabilityProfileCompositionSuccess)
    queries = [q for q in product.lookups if q.key == fact.key]
    assert queries
    for query in queries:
        assert query.profile_occurrences is request.composition.effective_occurrences
        assert isinstance(query.profile_result, Conflict)
        assert query.profile_result.evidence[0] is positive
        assert query.profile_result.evidence[1] is negative
        assert query.profile_applicable is False
        assert all(
            set(a.outcomes) == {S.CONFLICT, S.INAPPLICABLE, S.INPUT_UNRESOLVED}
            for a in view.uses(query)
        )
        wrong = _graft(query, profile_applicable=True)
        _reject(
            _rewire_query(product, query, wrong), product.source_verification, request
        )
    assert view.summary.posture is target.AssessmentPosture.INCOMPLETE


def test_new_consumers_remain_private_without_dynamic_or_renderer_access():
    from _pietto_repository_facts import REPOSITORY_FACTS

    for module in (target, mapping):
        assert module.__all__ == ()
        path = module.__file__
        assert type(path) is str
        facts = REPOSITORY_FACTS.python(Path(path))
        assert not any(name.startswith("pietto.sql") for name in facts.imported_modules)
        assert (
            not {"__import__", "import_module", "entry_points", "eval", "exec", "open"}
            & facts.identifiers
        )
