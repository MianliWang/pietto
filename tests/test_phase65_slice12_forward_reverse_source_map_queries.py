"""Exact retained source ownership, original graph endpoints and query behavior."""

from dataclasses import replace, FrozenInstanceError
from types import MappingProxyType
from typing import cast
from pathlib import Path
import sys
import traceback

import pytest

from pietto import ast_nodes as ast
from pietto.errors import SourceLocation
from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_source_maps as maps
from pietto._project import project_sql_plan_requirements as requirements
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
    verify_project_sql_bindings,
)
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from test_phase65_slice11_complete_demand_obligation_report import _cases
from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
    _roots,
    _source as join_source,
)
from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
    _chain,
    _repeated_sets,
)
from test_phase65_slice7_windows_named_window_qualify_staging import _family_source
from test_phase65_slice4_row_scalar_let_where_stage_value_planning import (
    _source as row_source,
)
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _graft

P = literals.ProjectSQLLiteralPolicy
K = maps.ProjectSQLSourceAssociationKind
R = sql.ProjectSQLOriginRole
V = sql.ProjectSQLOriginProvenance


def _mapped(roots, policy=P.BIND_SAFE_LITERALS):
    assert roots[0].ok, roots[0].diagnostics
    plan = sql.build_project_sql_plan(*roots, literal_policy=policy)
    assert isinstance(plan, sql.ProjectSQLPlan), getattr(plan, "blockers", ())
    source = verify_project_sql_plan(plan, *roots, literal_policy=policy)
    assert source.verified, source.issues
    product = maps.build_project_sql_source_map(source)
    checked = maps.verify_project_sql_source_map(product, source)
    assert checked.verified, checked.issues
    view = maps.inspect_project_sql_source_map(checked)
    return roots, plan, source, product, checked, view


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    cases = {
        name: value
        for name, value in _cases().items()
        if name
        in (
            "minimal",
            "literal_tags",
            "hidden_order",
            "set_membership",
            "path",
            "aggregate",
            "hidden_group",
            "hidden_window",
        )
    }
    cases["renamed"] = (_chain(), None)
    shared = _family_source(
        "first_value(value)",
        "rows between 2 preceding and current row",
        True,
        "query",
        "postgres",
    )
    shared = shared.replace(
        "        w = first_value(value) window composed\n",
        "        w = first_value(value) window composed\n        again = last_value(value) window composed\n",
    )
    cases["shared_window"] = (shared, None)
    result = {}
    for name, (source, requests) in cases.items():
        roots = _roots(tmp_path_factory.mktemp("source-maps"), source, requests)
        for policy in P:
            result[name, policy] = _mapped(roots, policy)
    return result


def test_all_original_roles_have_closed_real_mapping_rules(corpus):
    assert not set(maps.SYNTAX_ROLES) & set(maps.GENERATED_ROLES)
    assert set(maps.SYNTAX_ROLES) | set(maps.GENERATED_ROLES) == set(R)
    assert {
        entry.original.role
        for product in corpus.values()
        for entry in product[3].entries
    } == set(R)


@pytest.mark.parametrize("policy", tuple(P))
def test_flat_original_inventory_and_exact_forward_reverse_relations(corpus, policy):
    for name in {key[0] for key in corpus}:
        roots, plan, source, product, _, view = corpus[name, policy]
        assert product.plan is plan and product.source_verification is source
        assert (
            product.literal_policy is policy and product.envelope is plan.fixed_envelope
        )
        assert product.diagnostics is roots[0].diagnostics
        assert len(product.entries) == len(plan.origins)
        for i, (entry, original) in enumerate(
            zip(product.entries, plan.origins, strict=True)
        ):
            assert entry.position == i and entry.original is original
            assert view.origin(original.ref) is entry
            assert entry in view.subject(original.subject).origins
            expected = tuple(a for a in product.associations if a.entry is entry)
            assert view.associations(entry.ref) == expected
            causes = tuple(a for a in expected if a.kind is K.CAUSE)
            assert causes and all(
                a.site.occurrence is original.cause and a.observed is original.cause
                for a in causes
            )
            for association in expected:
                assert association in view.reverse(
                    association.site.source, association.site.occurrence
                )
                assert (
                    association.site.location.original
                    is association.site.occurrence.span
                )
        for site in product.sites:
            assert product.sites[site.position] is site
            assert site.source.module.parsed_input is site.source.parsed
            assert (
                tuple(a for a in product.associations if a.site is site)
                == product.indexes.by_site[site]
            )
        assert len({id(site) for site in product.sites}) == len(product.sites)


def test_metadata_subjects_multiple_origins_and_root_generated_reasons(corpus):
    _, plan, source, product, _, view = corpus["minimal", P.PRESERVE_LITERALS]
    source_subject = view.subject(plan.sources[0].ref)
    assert [entry.original.role for entry in source_subject.origins] == [
        R.DEFINITION,
        R.SOURCE_DESCRIPTOR,
    ]
    (root,) = view.subject(plan.scope).origins
    assert root.original.role is root.generated_reason is R.SELECTED_OWNER
    assert root.original.antecedents == ()
    for value in (*plan.symbols, *plan.boundaries, *plan.demands):
        subject = view.subject(value.ref)
        assert subject.origins
        assert all(entry.subject is value.ref for entry in subject.origins)
    symbol = view.subject(plan.symbols[0].ref).origins[0]
    assert symbol.nature is maps.ProjectSQLSourceNature.GENERATED
    assert symbol.generated_reason is R.SYMBOL
    assert not hasattr(symbol, "span")  # Authored cause is explanatory context.
    with pytest.raises(ValueError):
        view.subject(root.ref)
    with pytest.raises(ValueError):
        view.origin(plan.symbols[0].ref)
    original_view = inspect_project_sql_plan(source)
    before = original_view.expressions
    convenience = original_view.source_map()
    assert convenience.source_map.plan is plan and original_view.expressions is before
    assert tuple(e.original for e in convenience.source_map.entries) == plan.origins


def test_antecedent_endpoint_roles_and_all_subject_origins_are_preserved(corpus):
    for _, plan, _, product, _, view in corpus.values():
        cursor = 0
        for entry in product.entries:
            actual = view.antecedents(entry.ref)
            assert len(actual) == len(entry.original.antecedents)
            for ordinal, (link, original) in enumerate(
                zip(actual, entry.original.antecedents, strict=True)
            ):
                assert (
                    link is product.links[cursor]
                    and link.position == cursor
                    and link.ordinal == ordinal
                )
                assert link.target.ref is original and link.origin is entry
                if original.kind is sql.ProjectSQLPlanRefKind.ORIGIN:
                    assert link.kind is maps.ProjectSQLSourceEndpointKind.ORIGIN
                    assert link.target is view.origin(original)
                else:
                    assert link.kind is maps.ProjectSQLSourceEndpointKind.SUBJECT
                    assert link.target is view.subject(original)
                    assert tuple(e.original for e in link.target.origins) == tuple(
                        o for o in plan.origins if o.subject is original
                    )
                assert link in view.dependents(original)
                cursor += 1
        assert cursor == len(product.links)


def _reachable(plan, ref):
    # Small test oracle over the raw ledger, independent of map endpoint indexes.
    found = {o.ref for o in plan.origins if o.ref is ref or o.subject is ref}
    while True:
        previous = set(found)
        for origin in plan.origins:
            if origin.ref not in found:
                continue
            for target in origin.antecedents:
                found.update(
                    o.ref
                    for o in plan.origins
                    if o.ref is target
                    if target.kind is sql.ProjectSQLPlanRefKind.ORIGIN
                )
                if target.kind is not sql.ProjectSQLPlanRefKind.ORIGIN:
                    found.update(o.ref for o in plan.origins if o.subject is target)
        if found == previous:
            return tuple(o for o in plan.origins if o.ref in found)


@pytest.mark.parametrize(
    "case", ("renamed", "hidden_order", "set_membership", "path", "literal_tags")
)
def test_transitive_explanations_preserve_roles_through_intermediate_records(
    corpus, case
):
    _, plan, _, product, _, view = corpus[case, P.BIND_SAFE_LITERALS]
    for ref in (plan.exports[-1].ref, plan.demands[-1].ref):
        trace = view.explain(ref, transitive=True)
        assert tuple(entry.original for entry in trace.visited) == _reachable(plan, ref)
        assert len({entry.ref for entry in trace.visited}) == len(trace.visited)
        assert trace.origins == trace.visited
        for provenance in V:
            filtered = view.explain(ref, transitive=True, provenance=provenance)
            assert filtered.visited == trace.visited and filtered.links == trace.links
            assert filtered.origins == tuple(
                e for e in trace.origins if e.original.provenance is provenance
            )
            assert all(
                a.entry.original.provenance is provenance for a in filtered.associations
            )
    assert len(product.links) == sum(len(o.antecedents) for o in plan.origins)


def test_renamed_fields_keep_original_field_and_type_declarations(corpus):
    _, plan, _, product, _, view = corpus["renamed", P.PRESERVE_LITERALS]
    source_field = next(
        port.field.evidence.field_def
        for port in plan.source_ports
        if port.identity.name == "name"
    )
    assert source_field is not None
    sites = [site for site in product.sites if site.occurrence is source_field]
    assert len(sites) == 1 and sites[0].declaration.definition.name == "Row"
    result = view.explain(plan.exports[-1].ref, transitive=True)
    assert any(
        a.site is sites[0] and a.kind is K.FIELD_DECLARATION
        for a in result.associations
    )
    assert any(a.site.occurrence is source_field.type_expr for a in result.associations)


def test_shared_named_window_has_one_original_site_and_distinct_effective_links(corpus):
    _, plan, _, product, _, view = corpus["shared_window", P.BIND_SAFE_LITERALS]
    first, second = plan.windows
    assert (
        first.authored is not first.effective
        and second.authored is not second.effective
    )
    assert first.effective.spec.order_by[0] is second.effective.spec.order_by[0]
    component = first.effective.spec.order_by[0]
    sites = [site for site in product.sites if site.occurrence is component]
    assert len(sites) == 1
    assert type(sites[0].container) is ast.NamedWindowDeclaration
    mappings = view.reverse(sites[0].source, component)
    assert {a.evidence.window for a in mappings if a.kind is K.WINDOW_COMPONENT} == {
        first.ref,
        second.ref,
    }
    for window in plan.windows:
        pairs = [
            a for a in view.associations(window.ref) if a.kind is K.EFFECTIVE_WINDOW
        ]
        assert len(pairs) == 1 and pairs[0].observed is window.effective
        assert (
            pairs[0].site.occurrence is window.authored and pairs[0].evidence is window
        )
        with pytest.raises(ValueError):
            view.reverse(pairs[0].site.source, window.effective)


def _imported(tmp_path: Path):
    (tmp_path / "a.pietto").write_text(
        'type Money = Decimal(12, 2)\nshape Row:\n    amount: Money nullable\nsource rows: Row is mysql.table("rows")\ntable first:\n    from rows\n    select:\n        amount\nexport:\n    table first\n'
    )
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    text = 'import "b.pietto":\n    table Public as Alias\nquery result:\n    from Alias\n    select:\n        renamed = amount\n'
    return _mapped(_roots(tmp_path, text))


def test_import_reexport_and_external_type_source_ownership(tmp_path: Path):
    roots, plan, _, product, _, view = _imported(tmp_path)
    use = next(u for u in plan.input_uses if u.dependency.consumer is roots[2])
    entry = next(
        e
        for e in product.entries
        if e.subject is use.ref and e.original.role is R.INPUT_USE
    )
    associations = view.associations(entry.ref)
    trail = [
        a
        for a in associations
        if a.kind in (K.IMPORT, K.EXPORT) and a.path is use.origin_path
    ]
    assert [(a.kind, a.site.source.display_path) for a in trail] == [
        (K.IMPORT, "main.pietto"),
        (K.EXPORT, "b.pietto"),
        (K.IMPORT, "b.pietto"),
        (K.EXPORT, "a.pietto"),
    ]
    for position, hop in enumerate(use.origin_path.hops):
        assert trail[2 * position].hop is trail[2 * position + 1].hop is hop
    typed = [
        entry
        for entry in product.entries
        if entry.original.role is R.LITERAL_SITE
        and entry.original.owner.definition.name == "Money"
    ]
    assert typed and all(e.consuming_definition is plan.sources[0].ref for e in typed)
    for entry in typed:
        causes = [a for a in view.associations(entry.ref) if a.kind is K.CAUSE]
        assert all(
            a.site.declaration is entry.original.owner
            and a.site.source.display_path == "a.pietto"
            for a in causes
        )
    declaration = typed[0].original.owner.definition
    assert type(declaration) is ast.TypeDef
    assert any(site.occurrence is declaration.base for site in product.sites)


@pytest.mark.parametrize("change", ("missing", "hop", "path_order", "foreign_ast"))
def test_import_hops_are_exact_ordered_source_correspondences(tmp_path, change):
    product = _imported(tmp_path)
    value = product[3]
    original = next(
        a
        for a in value.associations
        if a.kind is K.IMPORT and a.path is not None and len(a.path.hops) == 2
    )
    if change == "missing":
        associations = tuple(a for a in value.associations if a is not original)
    else:
        assert original.path is not None
        changes = {
            "hop": {"hop": original.path.hops[1]},
            "path_order": {
                "path": _graft(original.path, hops=tuple(reversed(original.path.hops)))
            },
            "foreign_ast": {
                "site": _graft(
                    original.site, occurrence=replace(original.site.occurrence)
                )
            },
        }
        bad = _graft(original, **changes[change])
        associations = _changed(value.associations, original, bad)
    _reject(product, _graft(value, associations=associations))


def test_relationship_source_container_is_not_the_consuming_query(corpus):
    _, plan, _, value, _, view = corpus["path", P.PRESERVE_LITERALS]
    entry = next(e for e in value.entries if e.original.role is R.RELATIONSHIP_MATCH)
    (cause,) = tuple(a for a in view.associations(entry.ref) if a.kind is K.CAUSE)
    assert type(cause.site.container) is ast.RelationshipMetadata
    assert cause.site.declaration is None
    assert entry.original.owner is plan.scope.selected_owner


@pytest.mark.parametrize(
    "case", ("set_membership", "hidden_order", "hidden_group", "hidden_window", "path")
)
def test_hidden_values_membership_and_pending_proofs_remain_explainable(corpus, case):
    _, plan, _, product, _, view = corpus[case, P.BIND_SAFE_LITERALS]
    assert product.diagnostics is plan.diagnostics
    if case == "set_membership":
        right = plan.set_inputs[1]
        demand = next(d for d in plan.demands if d.subject is right.ref)
        trace = view.explain(demand.ref, transitive=True)
        assert any(e.original.provenance is V.TYPE_PROOF for e in trace.visited)
        assert any(
            e.subject is right.ref and e.original.provenance is V.MEMBERSHIP
            for e in trace.visited
        )
        assert plan.single_matches[0].downstream_enforcement_required
    if case == "hidden_order":
        pending = plan.hidden_order_requirements[0]
        assert view.associations(pending.ref)
        assert all(port.ref is not pending.ref for port in plan.result_ports)
    if case == "hidden_group":
        assert plan.group_keys and view.associations(plan.group_keys[0].ref)
        assert all(port.identity.name != "id" for port in plan.exports)
    if case == "hidden_window":
        assert any(window.selected is None for window in plan.windows)
        assert all(view.associations(window.ref) for window in plan.windows)
    if case == "path":
        for proof in plan.single_match_proofs:
            assert view.associations(proof.ref)
            assert view.explain(proof.ref, transitive=True).visited


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_matching_only_right_inputs_remain_sources_without_becoming_exports(
    tmp_path, kind
):
    _, plan, _, product, _, view = _mapped(_roots(tmp_path, join_source(kind, "true")))
    right = plan.join_inputs[1]
    assert view.associations(right.ref)
    assert all(p.identity.name != "right_id" for p in plan.exports)
    assert any(
        e.original.provenance is V.MEMBERSHIP
        for e in view.explain(right.ref, transitive=True).visited
    )
    assert len(product.sources) == 1


@pytest.mark.parametrize("policy", tuple(P))
def test_literal_transport_reverse_identity_and_exact_coordinates(corpus, policy):
    _, plan, _, product, _, view = corpus["literal_tags", policy]
    text = next(
        site
        for site in product.sites
        if type(site.occurrence) is ast.LiteralExpr and site.occurrence.value == "é\n😀"
    )
    position = text.location
    assert position.end_column - position.column == len('"é\\n😀"')
    associations = view.reverse(text.source, text.occurrence)
    assert associations
    assert all(
        a in view.at(text.source, position.line, position.column) for a in associations
    )
    assert all(
        a not in view.at(text.source, position.end_line, position.end_column)
        for a in associations
    )
    assert (
        view.overlapping(
            text.source,
            (position.line, position.column),
            (position.line, position.column),
        )
        == ()
    )
    assert all(
        a
        in view.overlapping(
            text.source,
            (position.line, position.column),
            (position.end_line, position.end_column),
        )
        for a in associations
    )
    multiline = next(
        site for site in product.sites if site.location.line < site.location.end_line
    )
    assert any(
        a.site is multiline
        for a in view.at(multiline.source, multiline.location.line + 1, 1)
    )
    assert view.at(text.source, 10000, 1) == ()
    assert view.reverse(text.source, text.source.parsed.script) == ()
    if policy is P.BIND_SAFE_LITERALS:
        fixed = next(
            value for value in plan.fixed_envelope.values if value.value == "é\n😀"
        )
        relevant = {a.entry.original.subject for a in associations}
        assert {fixed.ref, fixed.slot.ref, fixed.slot.site.ref} <= relevant
        use = next(use for use in plan.bind_uses if use.slot is fixed.slot)
        assert use.ref in relevant
    else:
        assert plan.literal_slots == plan.bind_uses == ()


def test_equal_spans_do_not_merge_authored_occurrences(tmp_path):
    text = row_source("    select:\n        value = id + 1 + 2\n")
    _, _, _, product, _, view = _mapped(_roots(tmp_path, text))
    pair = next(
        (a, b)
        for i, a in enumerate(product.sites)
        for b in product.sites[i + 1 :]
        if a.occurrence is not b.occurrence and a.occurrence.span == b.occurrence.span
    )
    first, second = pair
    assert first is not second
    assert first.location.line is not None and first.location.column is not None
    matches = view.at(first.source, first.location.line, first.location.column)
    assert any(a.site is first for a in matches) and any(
        a.site is second for a in matches
    )


def test_real_legacy_absence_is_distinct_from_malformed_or_missing_authored_sites(
    corpus,
):
    _, _, _, product, _, _ = corpus["renamed", P.PRESERVE_LITERALS]
    missing = [
        record
        for record in product.legacy_positions
        if record.location.availability
        is maps.ProjectSQLPositionAvailability.UNAVAILABLE
    ]
    assert missing and all(
        record.location.original is None and record.location.line is None
        for record in missing
    )
    assert all(
        any(a.entry is record.entry and a.kind is K.CAUSE for a in product.associations)
        for record in missing
    )
    partial = SourceLocation(path=None, line=2, column=3, end_line=4)
    observed = maps.allocate_position(partial)
    assert observed.original is partial and observed.end_column is None
    assert observed.availability is maps.ProjectSQLPositionAvailability.PARTIAL
    # The compatibility utility does not certify an authored site or AST membership.
    with pytest.raises(ValueError):
        maps.allocate_position(
            _graft(
                ast.Span(path=None, line=2, column=3, end_line=2, end_column=4),
                end_line=None,
                end_column=None,
            )
        )


def test_partial_legacy_position_cannot_reverse_a_known_end_line():
    with pytest.raises(ValueError):
        maps.allocate_position(SourceLocation(path=None, line=4, column=2, end_line=3))


def test_depth12_shared_set_explanation_is_not_a_path_expansion(tmp_path):
    source = _repeated_sets(12).replace("        id\n", "        id = 17\n", 1)
    _, plan, _, product, _, view = _mapped(_roots(tmp_path, source))
    assert len(plan.bindings.definitions) == 15 and len(plan.input_uses) == 26
    assert len(product.entries) == len(plan.origins)
    assert len(product.links) == sum(len(origin.antecedents) for origin in plan.origins)
    assert len(plan.literal_slots) == 1
    trace = view.explain(plan.exports[0].ref, transitive=True)
    assert len(trace.visited) <= len(product.entries)
    assert tuple(e.original for e in trace.visited) == _reachable(
        plan, plan.exports[0].ref
    )
    assert len({e.ref for e in trace.visited}) == len(trace.visited)


def _changed(values, original, replacement):
    return tuple(replacement if value is original else value for value in values)


def _reject(product, candidate):
    _, _, source, _, checked, _ = product
    assert not maps.verify_project_sql_source_map(candidate, source).verified
    with pytest.raises(ValueError, match="VERIFIED"):
        maps.inspect_project_sql_source_map(_graft(checked, source_map=candidate))


@pytest.mark.parametrize(
    "section",
    ("entries", "sites", "subjects", "associations", "links", "legacy_positions"),
)
@pytest.mark.parametrize("change", ("empty", "missing", "extra", "reorder", "mutable"))
def test_every_original_mapping_inventory_is_complete(corpus, section, change):
    product = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    value = product[3]
    original = getattr(value, section)
    assert len(original) > 1
    mutated = {
        "empty": (),
        "missing": original[:-1],
        "extra": (*original, original[0]),
        "reorder": tuple(reversed(original)),
        "mutable": list(original),
    }[change]
    _reject(product, _graft(value, **{section: mutated}))


@pytest.mark.parametrize(
    "change", ("ordinal", "role", "provenance", "cause", "nature", "reason", "consumer")
)
def test_origin_identity_and_generated_authored_distinction(corpus, change):
    product = corpus["minimal", P.PRESERVE_LITERALS]
    value = product[3]
    original = next(e for e in value.entries if e.original.role is R.SYMBOL)
    changes = {
        "ordinal": {"position": True},
        "role": {"original": _graft(original.original, role=R.EXPRESSION)},
        "provenance": {"original": _graft(original.original, provenance=V.VALUE)},
        "cause": {
            "original": _graft(
                original.original, cause=replace(original.original.cause)
            )
        },
        "nature": {"nature": maps.ProjectSQLSourceNature.SYNTAX_CORRESPONDENCE},
        "reason": {"generated_reason": None},
        "consumer": {"consuming_definition": value.plan.exports[0].ref},
    }
    bad = _graft(original, **changes[change])
    _reject(product, _graft(value, entries=_changed(value.entries, original, bad)))


@pytest.mark.parametrize(
    "change",
    (
        "source",
        "ast",
        "container",
        "owner",
        "span",
        "coordinate",
        "bool_coordinate",
        "path",
    ),
)
def test_source_site_membership_and_position_snapshots_are_exact(corpus, change):
    product = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    value = product[3]
    site = value.sites[0]
    foreign = corpus["minimal", P.PRESERVE_LITERALS][3]
    changes = {
        "source": {"source": foreign.sources[0]},
        "ast": {"occurrence": replace(site.occurrence)},
        "container": {"container": replace(site.container)},
        "owner": {"declaration": None},
        "span": {
            "location": _graft(site.location, original=replace(site.occurrence.span))
        },
        "coordinate": {"location": _graft(site.location, line=999)},
        "bool_coordinate": {"location": _graft(site.location, line=True)},
        "path": {"location": _graft(site.location, path="elsewhere.pietto")},
    }
    bad = _graft(site, **changes[change])
    _reject(product, _graft(value, sites=_changed(value.sites, site, bad)))


@pytest.mark.parametrize(
    "change",
    ("kind", "observed", "effective_as_authored", "evidence", "entry", "ordinal"),
)
def test_effective_window_correspondence_cannot_use_copied_spans(corpus, change):
    product = corpus["shared_window", P.BIND_SAFE_LITERALS]
    value = product[3]
    original = next(a for a in value.associations if a.kind is K.EFFECTIVE_WINDOW)
    changes = {
        "kind": {"kind": K.CAUSE},
        "observed": {"observed": replace(original.observed)},
        "effective_as_authored": {
            "site": _graft(original.site, occurrence=original.observed)
        },
        "evidence": {"evidence": None},
        "entry": {"entry": value.entries[0]},
        "ordinal": {"position": False},
    }
    bad = _graft(original, **changes[change])
    _reject(
        product, _graft(value, associations=_changed(value.associations, original, bad))
    )


@pytest.mark.parametrize("change", ("kind", "target", "ordinal", "position", "source"))
def test_origin_and_subject_endpoint_roles_cannot_be_interchanged(corpus, change):
    product = corpus["hidden_order", P.PRESERVE_LITERALS]
    value = product[3]
    origin = next(
        link
        for link in value.links
        if link.kind is maps.ProjectSQLSourceEndpointKind.ORIGIN
    )
    subject = next(
        link
        for link in value.links
        if link.kind is maps.ProjectSQLSourceEndpointKind.SUBJECT
    )
    changes = {
        "kind": {"kind": maps.ProjectSQLSourceEndpointKind.SUBJECT},
        "target": {"target": subject.target},
        "ordinal": {"ordinal": True},
        "position": {"position": False},
        "source": {"origin": origin.target},
    }
    bad = _graft(origin, **changes[change])
    _reject(product, _graft(value, links=_changed(value.links, origin, bad)))


@pytest.mark.parametrize(
    "name", tuple(maps.ProjectSQLSourceMapIndexes.__dataclass_fields__)
)
@pytest.mark.parametrize("change", ("empty", "mutable", "wrong_member"))
def test_forward_reverse_indexes_are_exact_immutable_relations(corpus, name, change):
    product = corpus["renamed", P.PRESERVE_LITERALS]
    value = product[3]
    original = getattr(value.indexes, name)
    mutated = {} if change == "empty" else dict(original)
    if change == "wrong_member":
        key = next(key for key, members in mutated.items() if members)
        mutated[key] = None if name in ("origins", "subjects") else ()
    replacement = mutated if change == "mutable" else MappingProxyType(mutated)
    _reject(
        product, _graft(value, indexes=_graft(value.indexes, **{name: replacement}))
    )


def test_missing_all_origins_fails_layer1_and_empty_map_fails_layer2(corpus):
    product = corpus["minimal", P.PRESERVE_LITERALS]
    _, plan, source, value, _, _ = product
    with pytest.raises(ValueError):
        maps.build_project_sql_source_map(_graft(source, plan=_graft(plan, origins=())))
    _reject(
        product,
        _graft(
            value,
            entries=(),
            associations=(),
            sites=(),
            subjects=(),
            links=(),
            legacy_positions=(),
        ),
    )


@pytest.mark.parametrize(
    "field",
    ("source_verification", "plan", "literal_policy", "envelope", "diagnostics"),
)
def test_exact_root_and_captured_request_invalidation(corpus, field):
    product = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    value = product[3]
    foreign = corpus["set_membership", P.PRESERVE_LITERALS][3]
    replacement = getattr(foreign, field)
    assert replacement is not getattr(value, field)
    _reject(product, _graft(value, **{field: replacement}))


def test_same_content_envelope_wrapper_requires_fresh_map(corpus):
    roots, plan, source, value, checked, _ = corpus[
        "literal_tags", P.BIND_SAFE_LITERALS
    ]
    changed = _graft(plan, fixed_envelope=replace(plan.fixed_envelope))
    stale = _graft(source, plan=changed)
    with pytest.raises(ValueError):
        maps.build_project_sql_source_map(stale)
    fresh = verify_project_sql_plan(
        changed, *roots, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert fresh.verified
    assert not maps.verify_project_sql_source_map(value, fresh).verified
    new = maps.build_project_sql_source_map(fresh)
    assert maps.verify_project_sql_source_map(new, fresh).verified
    with pytest.raises(ValueError):
        maps.inspect_project_sql_source_map(_graft(checked, source_verification=fresh))


def test_closed_query_domains_and_immutable_records(corpus):
    _, plan, _, value, _, view = corpus["literal_tags", P.BIND_SAFE_LITERALS]
    source = value.sources[0]
    foreign = corpus["minimal", P.PRESERVE_LITERALS][3]
    with pytest.raises(ValueError):
        view.at(foreign.sources[0], 1, 1)
    with pytest.raises(ValueError):
        view.reverse(source, replace(value.sites[0].occurrence))
    with pytest.raises(ValueError):
        view.origin(plan.exports[0].ref)
    for point in ((True, 1), (1, False), (0, 1), (-1, 2), (1, 1.5)):
        with pytest.raises(ValueError):
            view.at(source, *point)
    for start, end in (((2, 1), (1, 1)), ((True, 1), (2, 1)), ((1, 1), (2, False))):
        with pytest.raises(ValueError):
            view.overlapping(source, start, end)
    with pytest.raises(ValueError):
        view.explain(plan.scope, transitive=1)
    with pytest.raises(ValueError):
        view.explain(plan.scope, provenance="value")
    for name in maps.ProjectSQLSourceMapIndexes.__dataclass_fields__:
        with pytest.raises(TypeError):
            getattr(value.indexes, name)[None] = ()
    for item in (
        value,
        *value.entries,
        *value.sites,
        *value.associations,
        *value.links,
    ):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(item, "position", 0)


def test_no_reconstruction_source_reads_or_map_builders_in_independent_checks(
    corpus, monkeypatch
):
    products = [
        corpus[name, P.BIND_SAFE_LITERALS]
        for name in (
            "literal_tags",
            "shared_window",
            "path",
            "hidden_order",
            "set_membership",
        )
    ]

    def forbidden(*args, **kwargs):
        pytest.fail("Source-map consumer crossed a reconstruction or I/O boundary")

    names = (
        "infer_row_expression",
        "resolve_named_window_namespace",
        "build_project_completed_semantic_result",
        "build_project_query_block_ir",
        "build_project_sql_plan",
        "build_project_sql_bindings",
        "lookup_capability",
        "parse_source",
        "resolve_project_joined_namespace_reference",
    )
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pietto.") and module is not None:
            for member in names:
                if hasattr(module, member):
                    monkeypatch.setattr(module, member, forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    for _, _, source, _, _, _ in products:
        current = maps.build_project_sql_source_map(source)
        assert maps.verify_project_sql_source_map(current, source).verified
    for member in (
        "build_project_sql_source_map",
        "_build_map",
        "classify_origin",
        "allocate_position",
    ):
        monkeypatch.setattr(maps, member, forbidden)
    for _, plan, source, value, checked, _ in products:
        assert maps.verify_project_sql_source_map(value, source).verified
        assert (
            maps.inspect_project_sql_source_map(checked)
            .explain(plan.exports[0].ref, transitive=True)
            .origins
        )


def test_plan_and_report_remain_independent_optional_consumers(corpus, monkeypatch):
    roots, plan, source, _, _, _ = corpus["literal_tags", P.BIND_SAFE_LITERALS]

    def forbidden(*args, **kwargs):
        pytest.fail("Optional products became recursive prerequisites")

    for name in (
        "build_project_sql_source_map",
        "verify_project_sql_source_map",
        "membership",
        "classify_origin",
    ):
        monkeypatch.setattr(maps, name, forbidden)
    assert verify_project_sql_plan(
        plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
    ).verified
    value = requirements.build_project_sql_requirement_report(source)
    assert requirements.verify_project_sql_requirement_report(value, source).verified


def test_unavailable_bindings_only_and_uninitialized_inputs_are_controlled(
    corpus, tmp_path
):
    roots = corpus["minimal", P.PRESERVE_LITERALS][0]
    bindings = sql.build_project_sql_bindings(*roots)
    assert isinstance(bindings, sql.ProjectSQLBindings)
    binding_verification = verify_project_sql_bindings(bindings, *roots)
    with pytest.raises(ValueError):
        maps.build_project_sql_source_map(
            cast(ProjectSQLPlanVerification, binding_verification)
        )
    invalid = _roots(tmp_path, row_source("    select:\n        value = null\n"))
    failed = verify_project_sql_plan(sql.build_project_sql_plan(*invalid), *invalid)
    with pytest.raises(ValueError):
        maps.build_project_sql_source_map(failed)
    with pytest.raises(ValueError):
        maps.inspect_project_sql_source_map(
            object.__new__(maps.ProjectSQLSourceMapVerification)
        )


@pytest.mark.parametrize("failure", (ValueError, KeyError))
def test_rejections_do_not_dump_payload_or_chained_exception_repr(
    corpus, monkeypatch, failure
):
    source = corpus["minimal", P.PRESERVE_LITERALS][2]
    marker = "private-source-map-payload"

    def fail(*args, **kwargs):
        raise failure(marker)

    monkeypatch.setattr(maps, "_build_map", fail)
    with pytest.raises(ValueError) as raised:
        maps.build_project_sql_source_map(source)
    assert marker not in "".join(traceback.format_exception(raised.value))
