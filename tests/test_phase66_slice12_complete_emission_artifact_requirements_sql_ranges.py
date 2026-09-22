"""Complete artifact, dual-denominator closure and SQL-range queries.

Every positive artifact below is produced by the installed emission path from an
ordinary authored project, mostly the very fixtures the target manifest submits.
Expected ranges, multiplicities and requirement inventories are never copied from
the production builders: they come from the data-only public decoder, from
independent prefix-byte arithmetic over the SQL text, or from brute-force scans
of the retained objects. Mutations graft real retained structures; the one
injected upstream fact (a single-match request) is labelled as such.
"""

from copy import copy
from dataclasses import FrozenInstanceError, replace
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission import (
    EmissionOutcome,
    realize_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import (
    GeneratedRequirement,
    OriginalRequirement,
    SQLJoinQuery,
    SQLRowQuery,
    SQLSelect,
)
from pietto._project.project_sql_emission_contract import (
    Premise,
    prepare_project_sql_emission,
)
from pietto._project.project_sql_emission_inspection import (
    EmissionInspection,
    SQLRange,
    inspect_project_sql_emission,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlanRef

TARGETS = ("postgres", "mysql")
Q = {"postgres": '"', "mysql": "`"}
CASES = (
    ("G_emission_table_bag", "bag"),
    ("M_named_chain", "table_bag"),
    ("N_imported_chain", "bag"),
    ("T_row_direct", "query_bind"),
    ("W_join_shapes", "inner"),
    ("S_set_literals", "preserve"),
    ("S_set_forms", "union_all"),
    ("S_set_membership", "semi_except"),
    ("S_set_boundaries", "limit_zero_operand"),
    ("Z_aggregate_joined", "inner_fanout"),
    ("A_window_frame", "rows"),
    ("O_result_order", "ordinary_desc"),
    ("R_fixed_direct", "table_bind"),
)


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


def build(item, directory=None):
    if directory is not None:
        return probe.build_case(
            directory, item["source"], item["contract"], item["policy"]
        )
    with tempfile.TemporaryDirectory() as scratch:
        return probe.build_case(
            Path(scratch) / "case", item["source"], item["contract"], item["policy"]
        )


def artifact_of(outcome) -> Any:
    assert outcome.artifact is not None, serialize_project_sql_emission(outcome)
    return outcome.artifact


def view_of(outcome) -> EmissionInspection:
    artifact = artifact_of(outcome)
    return inspect_project_sql_emission(artifact, artifact.request)


def public(outcome) -> dict[str, Any]:
    return probe.decode_public(serialize_project_sql_emission(outcome))


def refused(changed, request):
    """The complete verifier, the factory and the serializer all reject `changed`."""
    assert not verify_project_sql_emission(changed, request).verified
    with pytest.raises(ValueError):
        inspect_project_sql_emission(changed, request)
    document = public(
        EmissionOutcome("VERIFIED", request.verification.completed.diagnostics, changed)
    )
    assert document["status"] == "BLOCKED"
    assert document["blockers"][0]["code"] == "PIE-B1008"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    result = {}
    for target in TARGETS:
        for case, variant in CASES:
            item = probe.fixture(target, case, variant)
            checked, outcome = build(item, tmp_path_factory.mktemp("slice12"))
            result[target, case] = (item, checked, outcome)
    return result


# --- C23: one complete artifact on both routes -------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_both_emitter_routes_bind_one_complete_verified_artifact(built, target):
    routes = set()
    for case, _ in CASES:
        item, checked, outcome = built[target, case]
        assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
        artifact = artifact_of(outcome)
        routes.add(type(artifact.ast))
        view = inspect_project_sql_emission(artifact, artifact.request)
        assert view.verification.verified and view.artifact is artifact
        assert view.request is artifact.request
        assert view.request.verification is checked
        # The installed consumer's own check passes over the same runtime view.
        assert probe.inspect_case(outcome, serialize_project_sql_emission(outcome))
        document = public(outcome)
        assert view.sql == document["sql"].encode("utf-8")
        assert [(r.start, r.end, r.kind, r.role) for r in view.ranges] == [
            (r["start"], r["end"], r["kind"], r["role"]) for r in document["ranges"]
        ]
        assert [c.label for c in view.columns] == [
            c["label"] for c in document["columns"]
        ]
        assert [u.server_index for u, _ in view.parameter_uses] == [
            u["server_index"] for u in document["parameter_uses"]
        ]
        # Tokens partition the exact bytes; overlays follow in retained order.
        tokens = [r for r in view.ranges if r.kind != "expression_range"]
        assert tokens[0].start == 0 and tokens[-1].end == len(view.sql)
        assert all(a.end == b.start for a, b in zip(tokens, tokens[1:]))
        assert [r.position for r in view.ranges] == list(range(len(view.ranges)))
        overlays = [r for r in view.ranges if r.kind == "expression_range"]
        assert view.ranges[len(tokens) :] == tuple(overlays)
    assert routes == {SQLSelect, SQLRowQuery, SQLJoinQuery}


@pytest.mark.parametrize("target", TARGETS)
def test_fresh_explicit_preparation_reuses_the_neutral_plan_only(built, target):
    item, checked, outcome = built[target, "G_emission_table_bag"]
    old = artifact_of(outcome)
    fresh = prepare_project_sql_emission(checked, item["contract"].encode())
    assert fresh is not old.request and fresh.verification is checked
    renewed = realize_project_sql(fresh)
    assert renewed.status == "VERIFIED"
    new = artifact_of(renewed)
    assert new.rendered.sql == old.rendered.sql
    # Each artifact is inspectable only with the request it was produced from.
    inspect_project_sql_emission(new, fresh)
    inspect_project_sql_emission(old, old.request)
    for artifact, request in ((old, fresh), (new, old.request)):
        with pytest.raises(ValueError):
            inspect_project_sql_emission(artifact, request)
        assert not verify_project_sql_emission(artifact, request).verified
    # A target-only change is a new request; the old artifact does not follow it.
    document = json.loads(item["contract"])
    document["environment"].append(
        {"key": "session_time_zone", "scope": "statement", "value": "UTC"}
    )
    changed = prepare_project_sql_emission(checked, probe.encoded(document))
    assert realize_project_sql(changed).status == "VERIFIED"
    with pytest.raises(ValueError):
        inspect_project_sql_emission(old, changed)


@pytest.mark.parametrize(
    "mutation",
    (
        "foreign_request",
        "foreign_artifact_request",
        "foreign_verification_root",
        "target_binding",
        "premise_root",
        "stale_bytes",
        "decoded_document",
        "outcome_as_artifact",
    ),
)
def test_grafted_stale_and_decoded_roots_are_refused(built, mutation):
    _, g_checked, g_outcome = built["postgres", "G_emission_table_bag"]
    _, h_checked, h_outcome = built["postgres", "M_named_chain"]
    artifact = artifact_of(g_outcome)
    request = artifact.request
    foreign = artifact_of(h_outcome)
    if mutation == "foreign_request":
        changed, bound = artifact, foreign.request
    elif mutation == "foreign_artifact_request":
        changed, bound = graft(artifact, request=foreign.request), foreign.request
    elif mutation == "foreign_verification_root":
        bound = graft(request, verification=h_checked)
        changed = graft(artifact, request=bound)
    elif mutation == "target_binding":
        document = json.loads(request.normalized_bytes)
        document["target"]["release"] = "17.0"
        bound = graft(request, normalized_bytes=probe.encoded(document))
        changed = graft(artifact, request=bound)
    elif mutation == "premise_root":
        bound = graft(request, premises=tuple(copy(p) for p in request.premises))
        changed = graft(artifact, request=bound)
    elif mutation == "stale_bytes":
        bound = request
        changed = replace(
            artifact,
            rendered=replace(
                artifact.rendered,
                sql=artifact.rendered.sql.replace(b"SELECT", b"select", 1),
            ),
        )
    elif mutation == "decoded_document":
        changed, bound = public(g_outcome), request
    else:
        changed, bound = g_outcome, request
    with pytest.raises(ValueError):
        inspect_project_sql_emission(changed, bound)
    if mutation not in {"decoded_document", "outcome_as_artifact"}:
        assert not verify_project_sql_emission(changed, bound).verified


# --- C20: two independently enumerated denominators --------------------------


@pytest.mark.parametrize(
    "case",
    ("G_emission_table_bag", "M_named_chain", "T_row_direct", "S_set_membership"),
)
@pytest.mark.parametrize(
    "mutation",
    (
        "drop_original",
        "drop_generated",
        "drop_matching_pair",
        "duplicate_original",
        "duplicate_generated",
        "reorder_generated",
        "foreign_original_entry",
        "foreign_generated_subject",
        "foreign_generated_kind",
        "empty_both",
    ),
)
def test_completeness_of_both_denominators_is_enforced(built, case, mutation):
    _, _, outcome = built["postgres", case]
    artifact = artifact_of(outcome)
    original, generated = (
        artifact.original_requirements,
        artifact.generated_requirements,
    )
    assert original and generated
    other = artifact_of(built["mysql", case][2])
    same_kind = next(
        g for g in other.generated_requirements if g.kind == generated[-1].kind
    )
    if mutation == "drop_original":
        changed = replace(artifact, original_requirements=original[1:])
    elif mutation == "drop_generated":
        changed = replace(artifact, generated_requirements=generated[:-1])
    elif mutation == "drop_matching_pair":
        changed = replace(
            artifact,
            original_requirements=original[:-1],
            generated_requirements=generated[:-1],
        )
    elif mutation == "duplicate_original":
        changed = replace(artifact, original_requirements=original + original[:1])
    elif mutation == "duplicate_generated":
        changed = replace(artifact, generated_requirements=generated + generated[-1:])
    elif mutation == "reorder_generated":
        changed = replace(artifact, generated_requirements=tuple(reversed(generated)))
    elif mutation == "foreign_original_entry":
        changed = replace(
            artifact,
            original_requirements=(
                OriginalRequirement(
                    other.original_requirements[0].entry, original[0].rule
                ),
                *original[1:],
            ),
        )
    elif mutation == "foreign_generated_subject":
        last = generated[-1]
        changed = replace(
            artifact,
            generated_requirements=(
                *generated[:-1],
                GeneratedRequirement(
                    last.kind, same_kind.subject, last.rule, last.premises
                ),
            ),
        )
    elif mutation == "foreign_generated_kind":
        last = generated[-1]
        changed = replace(
            artifact,
            generated_requirements=(
                *generated[:-1],
                GeneratedRequirement(
                    "checked_rule", last.subject, last.rule, last.premises
                ),
            ),
        )
    else:
        changed = replace(artifact, original_requirements=(), generated_requirements=())
    refused(changed, artifact.request)


# --- C21/C22: grounded justification and coherent scopes ---------------------


@pytest.mark.parametrize("target", TARGETS)
def test_shared_premise_roots_keep_separate_uses_and_refuse_substitutes(built, target):
    _, _, outcome = built[target, "M_named_chain"]
    artifact = artifact_of(outcome)
    request = artifact.request
    generated = artifact.generated_requirements
    users = {
        p.position: [g for g in generated if any(x is p for x in g.premises)]
        for p in request.premises
    }
    shared = max(users.values(), key=len)
    assert len(shared) >= 2
    for requirement in shared:
        assert all(any(p is x for x in request.premises) for p in requirement.premises)
    # Every requirement's premises are retained declaration roots and nothing else.
    for requirement in generated:
        assert all(type(p) is Premise for p in requirement.premises)
    index = generated.index(shared[0])
    root = shared[0].premises[0]
    for label, premises in (
        ("copied_root", (Premise(root.position, root.key, root.scope, root.value),)),
        ("rule_to_rule", (shared[1],)),
        ("original_as_root", (artifact.original_requirements[0],)),
        ("emptied", ()),
        ("extra_declared", (*shared[0].premises, *request.premises)),
    ):
        changed = replace(
            artifact,
            generated_requirements=(
                *generated[:index],
                replace(shared[0], premises=premises),
                *generated[index + 1 :],
            ),
        )
        refused(changed, request)


def two_source(target, body, *, second_text=None, extra_environment=()):
    item = probe.fixture(target, "S_set_forms", "union_all")
    contract = json.loads(item["contract"])
    if second_text is not None:
        contract["sources"][1]["fields"][3]["representation"]["domain"].update(
            second_text
        )
    contract["environment"].extend(extra_environment)
    header = item["source"].split("query result:", 1)[0]
    return {
        "source": header + body,
        "contract": probe.encoded(contract).decode(),
        "policy": "preserve_literals",
    }


JOIN_LABELS = (
    "query result:\n    from sa\n    inner join sb as r:\n        from sa\n"
    "        on sa.key == r.key\n    select:\n        a = sa.label\n        b = r.label\n"
)
JOIN_TEXT = (
    "query result:\n    from sa\n    inner join sb as r:\n        from sa\n"
    "        on sa.label == r.label\n    select:\n        a = sa.key\n"
)


@pytest.mark.parametrize("target", TARGETS)
def test_statement_scope_conflicts_and_source_local_differences(target):
    # Two declarations of one statement-scoped setting with different values.
    _, outcome = build(
        two_source(
            target,
            JOIN_LABELS,
            extra_environment=(
                {"key": "client_encoding", "scope": "statement", "value": "LATIN1"},
            ),
        )
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert ("PIE-B1005", "inconsistent_declared_scope") in [
        (b.code, b.detail) for b in outcome.blockers
    ]
    # Two sources with different but individually valid Text premises: not a
    # global conflict, each source keeps its own premise on its own requirements.
    _, outcome = build(
        two_source(target, JOIN_LABELS, second_text={"max_characters": 16})
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    view = view_of(outcome)
    owners = {
        id(p.scope)
        for g in view.generated_requirements
        if g.kind == "source_representation"
        for p in g.premises
        if p.scope != "statement"
    }
    assert len(owners) >= 2
    # A cross-source Text comparison satisfies its own compatibility rule.
    _, outcome = build(
        two_source(target, JOIN_TEXT, second_text={"max_characters": 16})
    )
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    collation = "und-x-icu" if target == "postgres" else "utf8mb4_general_ci"
    _, outcome = build(
        two_source(target, JOIN_TEXT, second_text={"collation": collation})
    )
    assert outcome.status == "BLOCKED"
    codes = {(b.code, b.detail) for b in outcome.blockers}
    assert ("PIE-B1005", "text_comparison_domain_conflict") in codes
    # Individually valid SET operands whose pair breaks the SET's own rule.
    _, outcome = build(probe.fixture(target, "V_set_blocked", "physical_mismatch"))
    assert outcome.status == "BLOCKED"
    assert ("PIE-B1002", "set_column_physical_representation_mismatch") in {
        (b.code, b.detail) for b in outcome.blockers
    }


# --- C31: membership, enforcement and ordinary risk --------------------------


def single_match_build(item):
    """Ordinary authored input plus one upstream single-match request.

    The request is registered through the upstream product API
    (`with_project_single_match_requests`), not fabricated into a plan; it is the
    only injected fact in this module and it produces a LEGAL_UNPROVED proof.
    """
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        ProjectConcreteCompletedSemanticResult,
        build_project_completed_semantic_result,
        with_project_single_match_requests,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        build_project_query_block_ir_analysis_bundle,
        verify_project_query_block_ir,
    )
    from pietto._project.project_single_match import ProjectSingleMatchRequest
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch) / "case"
        directory.mkdir(parents=True)
        (directory / "pietto.toml").write_text(probe.CONFIG)
        for name, content in probe.source_files(item["source"]).items():
            (directory / name).write_text(content, encoding="utf-8")
        parsed = check_project_parse_only(directory)
        completed = build_project_completed_semantic_result(
            build_empty_project_semantic_result(parsed)
        )
        assert type(completed) is ProjectConcreteCompletedSemanticResult
        requests = tuple(
            ProjectSingleMatchRequest(owner=c.use.owner, use=c.use)
            for c in completed.roots.join_conditions.entries
        )
        assert len(requests) == 1
        completed = with_project_single_match_requests(completed, requests)
        ir = build_project_query_block_ir(completed)
        bundle = build_project_query_block_ir_analysis_bundle(
            verify_project_query_block_ir(ir)
        )
        (selected,) = tuple(o for o in ir.owners if o.definition.name == "result")
        policy = ProjectSQLLiteralPolicy(item["policy"])
        plan = build_project_sql_plan(
            completed, bundle, selected, literal_policy=policy
        )
        checked = verify_project_sql_plan(
            plan, completed, bundle, selected, literal_policy=policy
        )
        return emit_project_sql(checked, item["contract"].encode())


@pytest.mark.parametrize("target", TARGETS)
def test_membership_enforcement_and_ordinary_risk_keep_their_meanings(built, target):
    # EXCEPT-right membership: the complete right terminal is an obligation.
    _, _, outcome = built[target, "S_set_membership"]
    artifact = artifact_of(outcome)
    generated = artifact.generated_requirements
    right = [g for g in generated if g.kind == "complete_right_terminal"]
    assert len(right) == 1 and right[0].rule == "R11"
    assert [g.kind for g in generated if g.kind == "set_row_equivalence"] == [
        "set_row_equivalence"
    ]
    refused(
        replace(
            artifact,
            generated_requirements=tuple(g for g in generated if g not in right),
        ),
        artifact.request,
    )
    # LIMIT 0 inside an operand waives no original demand and no static limit.
    _, _, outcome = built[target, "S_set_boundaries"]
    artifact = artifact_of(outcome)
    assert [g.kind for g in artifact.generated_requirements if g.kind == "static_limit"]
    assert len(artifact.original_requirements) == len(artifact.request.plan.demands) > 0
    refused(
        replace(artifact, original_requirements=artifact.original_requirements[:-1]),
        artifact.request,
    )
    # LEGAL_UNPROVED enforcement blocks usable SQL while its warning is retained.
    body = (
        "query result:\n    from lhs\n    semi join rhs as r:\n        from lhs\n"
        "        on true\n    select:\n        a = lhs.id\n"
    )
    unproved = single_match_build(probe.join_witness(target, body))
    assert unproved.status == "BLOCKED" and unproved.artifact is None
    assert [(b.code, b.detail) for b in unproved.blockers] == [
        ("PIE-B1006", "original_enforcement_not_fulfilled")
    ]
    document = public(unproved)
    assert document["status"] == "BLOCKED"
    assert [(d["code"], d["severity"]) for d in document["diagnostics"]] == [
        ("PIE-S2337", "warning")
    ]
    # Ordinary aggregate risk records are inspectable, not blockers.
    _, _, outcome = built[target, "Z_aggregate_joined"]
    artifact = artifact_of(outcome)
    summary = artifact.request.report.report.summary
    assert summary.aggregate_evidence and not summary.enforcement_required
    assert outcome.status == "VERIFIED"
    # A published VERIFIED outcome carries the project's retained diagnostics
    # by identity; a substituted tuple, even one holding a real retained
    # warning from another project, is refused.
    assert outcome.diagnostics is artifact.request.verification.completed.diagnostics
    lost = public(replace(outcome, diagnostics=unproved.diagnostics))
    assert lost["status"] == "BLOCKED"
    assert lost["blockers"][0]["subject"]["detail"] == "artifact_correspondence"


# --- C24: final bytes ---------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    (
        "set_quantifier",
        "equality_operator",
        "grouping",
        "separator",
        "identifier",
        "comment",
        "direct_keyword",
        "parameter",
    ),
)
def test_byte_mutations_with_correct_sidecars_are_refused(built, target, mutation):
    if mutation == "direct_keyword":
        artifact = artifact_of(built[target, "G_emission_table_bag"][2])
        old, new = b" FROM ", b" JOIN "
    elif mutation == "parameter":
        artifact = artifact_of(built[target, "T_row_direct"][2])
        old, new = (b"$1", b"$2") if target == "postgres" else (b"?", b"1")
    else:
        artifact = artifact_of(built[target, "S_set_membership"][2])
        quote = Q[target].encode()
        first = next(e for e in artifact.rendered.events if e.kind == "identifier")
        spelled = artifact.rendered.sql[first.start : first.end]
        old, new = {
            "set_quantifier": (b" EXCEPT DISTINCT ", b" EXCEPT ALL      "),
            "equality_operator": (b" = ", b" < "),
            "grouping": (b"(SELECT ", b" SELECT "),
            "separator": (b", ", b"; "),
            "identifier": (spelled, quote + b"z" + spelled[2:]),
            "comment": (b" AS ", b"--AS"),
        }[mutation]
    sql = artifact.rendered.sql
    assert old in sql and len(old) == len(new)
    changed = replace(
        artifact, rendered=replace(artifact.rendered, sql=sql.replace(old, new, 1))
    )
    refused(changed, artifact.request)


# --- C25: coordinates ---------------------------------------------------------


def unicode_item(target):
    item = probe.fixture(target)
    contract = json.loads(item["contract"])
    quote = Q[target]
    relation = f"ph{quote}ase\n" + ("𝒳é" if target == "postgres" else "é")
    column = f"te{quote}xt\n" + ("𝒳" if target == "postgres" else "é")
    contract["sources"][0]["relation"]["name"] = relation
    contract["sources"][0]["fields"][2]["column"] = column
    return {**item, "contract": probe.encoded(contract).decode()}, relation, column


@pytest.mark.parametrize("target", TARGETS)
def test_ranges_are_utf8_byte_offsets_into_the_exact_sql(target):
    item, relation, column = unicode_item(target)
    _, outcome = build(item)
    assert outcome.status == "VERIFIED", serialize_project_sql_emission(outcome)
    view = view_of(outcome)
    quote = Q[target]
    text = view.sql.decode("utf-8")
    encoded = json.dumps(text, ensure_ascii=False)
    for role, spelled in (("relation", relation), ("column", column)):
        token = quote + spelled.replace(quote, quote * 2) + quote
        (item_range,) = [
            r
            for r in view.ranges
            if r.kind == "identifier"
            and r.role == role
            and view.sql[r.start : r.end] == token.encode("utf-8")
        ]
        # Independent oracle: the byte offset is the UTF-8 length of the prefix.
        character_index = text.index(token)
        assert item_range.start == len(text[:character_index].encode("utf-8"))
        assert item_range.end == item_range.start + len(token.encode("utf-8"))
        if role == "relation":
            assert character_index != item_range.start
        # JSON escaping moves the text; its offsets are never SQL byte offsets.
        escaped = json.dumps(token, ensure_ascii=False)[1:-1]
        assert encoded.find(escaped) not in {-1, item_range.start}
        # An interior byte of a multi-byte character hits its containing range.
        marker = ("𝒳" if target == "postgres" else "é").encode("utf-8")
        interior = item_range.start + view.sql[item_range.start :].index(marker) + 1
        assert item_range in view.at(interior)
        # A mid-codepoint emitted endpoint is refused by the byte verifier.
        events = list(view.artifact.rendered.events)
        index = events.index(item_range.event)
        events[index] = replace(item_range.event, end=interior)
        refused(
            replace(
                view.artifact,
                rendered=replace(view.artifact.rendered, events=tuple(events)),
            ),
            view.request,
        )
        # Parser coordinates of the authored origin are character positions in
        # the authored module, not SQL byte offsets.
        lines = probe.source_files(item["source"])["main.pietto"].splitlines()
        located = [
            a
            for _, associations in item_range.origins
            for a in associations
            if a.site.location.availability.value == "complete"
        ]
        assert located
        for association in located:
            location = association.site.location
            assert str(location.path).endswith(".pietto")
            assert location.line >= 1 and location.column >= 1
            line = lines[location.line - 1]
            assert line[location.column - 1 :].strip()
    assert view.at(len(view.sql)) == ()
    assert view.overlapping(4, 4) == ()
    for bad in (True, -1, len(view.sql) + 1, 1.5, "3", (1, 2)):
        with pytest.raises(ValueError):
            view.at(bad)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            view.overlapping(0, bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        view.overlapping(5, 2)


# --- Query identity and completeness -----------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_forward_and_reverse_queries_preserve_every_occurrence(built, target):
    _, _, outcome = built[target, "T_row_direct"]
    view = view_of(outcome)
    # Equal spellings are distinct hits; forward lookup returns exactly the
    # subject's own occurrences and nothing that merely shares a spelling.
    spellings: dict[bytes, list[SQLRange]] = {}
    for item in view.ranges:
        if item.kind == "identifier":
            spellings.setdefault(view.sql[item.start : item.end], []).append(item)
    repeated = max(spellings.values(), key=len)
    assert len(repeated) > 1 and len({r.position for r in repeated}) == len(repeated)
    for item in repeated:
        hits = view.ranges_of(item.subject)
        assert hits == tuple(r for r in view.ranges if r.subject is item.subject)
        assert item in hits
    # Nested overlays: a byte inside the innermost span hits its token and every
    # enclosing overlay, in retained order, tokens before overlays.
    overlays = [r for r in view.ranges if r.kind == "expression_range"]
    inner = next(
        o
        for o in overlays
        if any(x is not o and x.start <= o.start and o.end <= x.end for x in overlays)
    )
    hits = view.at(inner.start)
    assert inner in hits and len([h for h in hits if h.kind == "expression_range"]) >= 2
    assert [h.position for h in hits] == sorted(h.position for h in hits)
    assert [h.kind == "expression_range" for h in hits] == sorted(
        h.kind == "expression_range" for h in hits
    )
    assert hits == tuple(r for r in view.ranges if r.start <= inner.start < r.end)
    window = view.overlapping(inner.start, inner.end)
    assert window == tuple(
        r for r in view.ranges if r.start < inner.end and inner.start < r.end
    )
    # A forged reference with equal kind and ordinal is foreign, not a no-hit.
    subject = next(
        r.subject for r in view.ranges if type(r.subject) is ProjectSQLPlanRef
    )
    forged = ProjectSQLPlanRef(
        scope=subject.scope, kind=subject.kind, position=subject.position
    )
    for foreign in (forged, object(), "s0", 0, [], {"kind": "symbol"}):
        with pytest.raises(ValueError):
            view.ranges_of(foreign)
    # A valid current subject that emitted nothing is an honest empty result.
    subjects = view.request.source_map.source_map.indexes.subjects
    silent = next(s for s in subjects if not any(r.subject is s for r in view.ranges))
    assert view.ranges_of(silent) == ()
    # Origins: lookup by the retained entry and by its ORIGIN-kind reference;
    # a foreign entry with the same ordinal is refused.
    item = next(r for r in view.ranges if r.origins)
    entry, associations = item.origins[0]
    by_entry = view.ranges_of(entry)
    assert item in by_entry and by_entry == view.ranges_of(entry.ref)
    assert by_entry == tuple(
        r for r in view.ranges if any(e is entry for e in r.event.origins)
    )
    other = view_of(built[target, "G_emission_table_bag"][2])
    foreign_entry = other.request.source_map.source_map.entries[entry.position]
    with pytest.raises(ValueError):
        view.ranges_of(foreign_entry)
    # Imported/re-exported producers keep their retained access route.
    imported = view_of(built[target, "N_imported_chain"][2])
    assert any(
        a.path is not None or a.hop is not None
        for r in imported.ranges
        for _, associations in r.origins
        for a in associations
    )
    # Generated scaffolding keeps its causal association without an authored
    # span of its own: the SELECT keyword's subject is the selected plan.
    scaffold = next(r for r in view.ranges if r.role == "select")
    assert scaffold.kind == "syntax"
    assert all(
        entry.original.provenance.value == "generated_structure"
        or entry.generated_reason is not None
        or entry.original.role.value == "selected_owner"
        for entry, _ in scaffold.origins
    )


@pytest.mark.parametrize("target", TARGETS)
def test_parameter_and_result_chains_through_the_view(built, target):
    _, _, outcome = built[target, "R_fixed_direct"]
    view = view_of(outcome)
    document = public(outcome)
    slots = {value.slot for value in view.artifact.fixed_values}
    sites = view.request.plan.literal_sites
    assert len(view.parameter_uses) == 18
    for ordinal, (use, token) in enumerate(view.parameter_uses):
        assert use.ordinal == ordinal and use.slot in slots
        # The token belongs to the original literal site of this exact use.
        (site,) = [s for s in sites if s.position.expression is use.original.ref]
        assert token.kind == "parameter" and token.subject is site.ref
        spelled = view.sql[token.start : token.end]
        if target == "mysql":
            assert spelled == b"?" and use.server_index == ordinal + 1
        else:
            assert spelled == b"$" + str(use.server_index).encode()
    assert [u.server_index for u, _ in view.parameter_uses] == [
        u["server_index"] for u in document["parameter_uses"]
    ]
    artifact = view.artifact
    uses = artifact.parameter_uses
    swapped = (uses[1], uses[0], *uses[2:])
    refused(replace(artifact, parameter_uses=swapped), artifact.request)
    wrong = replace(uses[0], server_index=uses[0].server_index + 1)
    refused(replace(artifact, parameter_uses=(wrong, *uses[1:])), artifact.request)
    # One shared producer keeps one literal token, one slot and one server
    # index across two operand uses.
    shared = view_of(built[target, "S_set_literals"][2])
    assert [g.kind for g in shared.generated_requirements].count("set_operand") == 2
    literals = [r for r in shared.ranges if r.kind == "literal"]
    assert len(literals) == 1
    # Positional result columns equal the published visible tuple everywhere.
    for case, _ in CASES:
        item_view = view_of(built[target, case][2])
        columns = public(built[target, case][2])["columns"]
        assert [(c.ordinal, c.label) for c in item_view.columns] == [
            (c["ordinal"], c["label"]) for c in columns
        ]


# --- Refusal to reconstruct and installed consumer ---------------------------


def test_inspection_never_reconstructs_or_reopens(built, monkeypatch):
    from pietto._project import check as checking
    from pietto._project import project_completed_semantics as completing
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_emission_ast as ast
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_rendering as rendering
    from pietto._project import project_sql_plan as planning

    def forbidden(*args, **kwargs):
        raise AssertionError("construction, rendering or reopening during inspection")

    for module, name in (
        (emission, "emit_project_sql"),
        (emission, "realize_project_sql"),
        (emission, "serialize_project_sql_emission"),
        (emission, "build_sql_ast"),
        (emission, "build_requirements"),
        (emission, "build_row_requirements"),
        (emission, "render_sql"),
        (emission, "render_row_sql"),
        (emission, "render_join_sql"),
        (emission, "prepare_project_sql_emission"),
        (contract, "prepare_project_sql_emission"),
        (contract, "_decimal_precision_scale_fact"),
        (ast, "build_sql_ast"),
        (ast, "build_requirements"),
        (ast, "build_row_requirements"),
        (rendering, "render_sql"),
        (rendering, "render_row_sql"),
        (rendering, "render_join_sql"),
        (planning, "build_project_sql_plan"),
        (completing, "build_project_completed_semantic_result"),
        (checking, "check_project_parse_only"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    for case in ("G_emission_table_bag", "S_set_membership", "T_row_direct"):
        artifact = artifact_of(built["postgres", case][2])
        view = inspect_project_sql_emission(artifact, artifact.request)
        first = view.ranges[0]
        assert first in view.at(first.start)
        assert first in view.overlapping(0, len(view.sql))
        assert first in view.ranges_of(first.subject)


def test_probe_checks_the_view_in_the_child_and_fails_on_drift(built):
    _, _, outcome = built["postgres", "S_set_membership"]
    data = serialize_project_sql_emission(outcome)
    assert isinstance(probe.inspect_case(outcome, data), EmissionInspection)
    document = json.loads(data)
    document["ranges"][-1]["end"] -= 1
    with pytest.raises(ValueError):
        probe.inspect_case(outcome, probe.encoded(document))
    document = json.loads(data)
    document["columns"][0]["label"] = "renamed"
    with pytest.raises(ValueError):
        probe.inspect_case(outcome, probe.encoded(document))
    blocked = build(probe.fixture("postgres", "V_set_blocked", "physical_mismatch"))[1]
    assert probe.inspect_case(blocked, serialize_project_sql_emission(blocked)) is None


def test_view_is_immutable_with_bounded_repr(built):
    view = view_of(built["postgres", "M_named_chain"][2])
    text = repr(view)
    assert text == repr(view) and len(text) < 300
    assert text.startswith("EmissionInspection(artifact=..., request=...")
    assert f"ranges=<{len(view.ranges)}>" in text
    item = view.ranges[0]
    assert len(repr(item)) < 200 and repr(item).startswith("SQLRange(position=0")
    with pytest.raises(FrozenInstanceError):
        view.ranges = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        item.start = 1  # type: ignore[misc]
