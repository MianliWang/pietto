"""Explicit private single-match requests over real completed Project roots."""

from pathlib import Path
from dataclasses import replace
import json

import pytest

from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    with_project_single_match_requests,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchScope,
    ProjectSingleMatchState,
    ProjectSingleMatchProofKind,
)
from pietto._project.project_final_outputs import ProjectRelationLimit
from pietto._project.project_relationship_match_guarantees import (
    ProjectRelationshipMaximumBound,
)
from pietto.semantic.model import CheckMode
from pietto.errors import Severity
from pietto.ast_nodes import TableDef, QueryDef
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from _pietto_project_join_full import (
    _unique_source,
)

from _pietto_project_join import (
    BASE,
    _completed,
    _source,
)
from _pietto_project_single_match import _asymmetric_source, _limited_source, _request


def test_default_authored_compilation_has_no_implicit_single_match(
    tmp_path: Path,
) -> None:
    completed = _completed(
        tmp_path,
        BASE + "query result:\n    from lhs\n    let r = rhs\n"
        "    where any(True for r in r)\n    select:\n        id = lhs.id\n",
    )
    assert completed.ok and not completed.diagnostics
    assert completed.single_matches.requests == ()
    assert completed.single_matches.obligations == ()


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("kind", ("inner", "left", "right", "full"))
def test_unproved_actual_matches_warn_on_success_in_every_mode(
    tmp_path: Path, mode: CheckMode, kind: str
) -> None:
    original = _completed(tmp_path, f"mode {mode.value}\n" + _source("True", kind=kind))
    request = _request(original)
    checked = with_project_single_match_requests(original, (request,))
    assert (
        checked.roots is original.roots
        and checked.effective_outputs is original.effective_outputs
    )
    assert checked.ok and original.ok
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert entry.downstream_enforcement_required and not entry.proofs
    assert len(entry.input_pairs) == 1
    join = entry.joins[0]
    assert entry.input_pairs[0][0] is join.input_uses[0]
    assert entry.input_pairs[0][1] is join.input_uses[1]
    assert entry.diagnostic is not None
    assert (
        entry.diagnostic.code == "PIE-S2337"
        and entry.diagnostic.severity is Severity.WARNING
    )
    assert checked.diagnostics == (entry.diagnostic,)
    assert checked.diagnostics[0] is entry.diagnostic
    assert original.diagnostics == ()
    document = project_check_result_to_json_dict(
        check_project_parse_only(tmp_path), semantic_diagnostics=checked.diagnostics
    )
    assert document["ok"]
    assert set(document) == {
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    }
    assert json.loads(json.dumps(document))["diagnostics"][0]["severity"] == "warning"


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_cross_request_is_invalid_not_implicit_on_true(
    tmp_path: Path, mode: CheckMode
) -> None:
    original = _completed(
        tmp_path, f"mode {mode.value}\n" + _source(None, kind="cross")
    )
    checked = with_project_single_match_requests(original, (_request(original),))
    entry = checked.single_matches.entries[0]
    assert not checked.ok and original.ok
    assert entry.state is ProjectSingleMatchState.INVALID
    assert not checked.single_matches.obligations
    assert not entry.proofs and not entry.downstream_enforcement_required
    assert entry.diagnostic is not None and entry.diagnostic.code == "PIE-S2338"
    assert entry.diagnostic.severity is Severity.ERROR
    assert checked.diagnostics[0] is entry.diagnostic


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full"))
@pytest.mark.parametrize("refinement", (False, True))
def test_predicate_and_extra_filter_prove_same_target_key(
    tmp_path: Path, kind: str, refinement: bool
) -> None:
    predicate = "Link(lhs, r)" + (" and r.id > 0" if refinement else "")
    original = _completed(tmp_path, _unique_source(kind, predicate))
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is ProjectSingleMatchState.PROVED
    assert checked.ok and not checked.diagnostics
    condition = assessment.condition
    assert condition is not None and condition.base_guarantee is None
    assert condition.refinement_guarantee is None
    matches = tuple(
        m for m in condition.key_matches if m.binding is condition.use.target_binding
    )
    assert len(matches) == 1 and len(condition.mandatory_equalities) == 1
    assert matches[0].maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert matches[0].minimum.value == "zero_allowed"
    assert tuple(proof.kind for proof in assessment.proofs) == (
        ProjectSingleMatchProofKind.MATCHED_KEY,
    )
    assert assessment.proofs[0].roots[1] is matches[0]
    assert not assessment.downstream_enforcement_required


@pytest.mark.parametrize(
    "limit,post,where,proved",
    (
        (1, False, False, True),
        (0, False, False, True),
        (2, False, False, False),
        (None, True, False, False),
        (None, False, True, False),
    ),
)
def test_c06_pre_join_limit_is_cardinality_and_post_join_filters_are_not(
    tmp_path: Path, limit: int | None, post: bool, where: bool, proved: bool
) -> None:
    original = _completed(
        tmp_path, _limited_source(right_limit=limit, post_limit=post, where=where)
    )
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is (
        ProjectSingleMatchState.PROVED
        if proved
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    if proved:
        proofs = tuple(
            p
            for p in assessment.proofs
            if p.kind is ProjectSingleMatchProofKind.RIGHT_LIMIT
        )
        assert len(proofs) == 1
        bound = proofs[0].roots[-1]
        assert isinstance(bound, ProjectRelationLimit)
        assert bound.owner.definition.name == "right_named"
        assert bound.row_count_upper_bound == limit
        assert isinstance(bound.owner.definition, (TableDef, QueryDef))
        assert bound.clause is bound.owner.definition.limit_clause
    assert checked.ok


def test_identical_payloads_count_two_actual_matches_without_data_repair(
    tmp_path: Path,
) -> None:
    left = (("l0", 1),)
    right = (("r0", 1), ("r1", 1))
    matches = tuple(row for row in right if left[0][1] == row[1])
    assert matches == right and len(matches) == 2
    assert matches[0][0] != matches[1][0] and matches[0][1] == matches[1][1]
    payload_classes = (matches[0][1],)
    assert len(payload_classes) == 1
    original = _completed(tmp_path, _source("lhs.id == r.id", kind="inner"))
    checked = with_project_single_match_requests(original, (_request(original),))
    assert (
        checked.single_matches.entries[0].state
        is ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert checked.effective_outputs is original.effective_outputs


def test_warning_source_order_distinct_diagnostics_and_same_object_repetition(
    tmp_path: Path,
) -> None:
    source = (
        _source("True") + "query other:" + _source("True").split("query result:", 1)[1]
    )
    original = _completed(tmp_path, source)
    first, other = _request(original), _request(original, 1)
    distinct = replace(first)
    checked = with_project_single_match_requests(
        original, (other, first, first, distinct)
    )
    entries = checked.single_matches.entries
    assert tuple(e.request for e in entries) == (first, first, distinct, other)
    assert entries[0] is entries[1] and entries[0] is not entries[2]
    assert len(checked.diagnostics) == 3
    assert all(
        actual is entry.diagnostic
        for actual, entry in zip(
            checked.diagnostics, (entries[0], entries[2], entries[3]), strict=True
        )
    )
    assert checked.diagnostics[0] == checked.diagnostics[1]
    assert checked.diagnostics[0] is not checked.diagnostics[1]


def test_warning_plus_unrelated_error_preserves_objects_order_and_failure(
    tmp_path: Path,
) -> None:
    source = (
        _source("True")
        + "query broken:\n    from lhs\n    select:\n        bad = missing\n"
    )
    original = _completed(tmp_path, source)
    assert not original.ok and original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assert not checked.ok
    assert all(
        a is b
        for a, b in zip(
            original.diagnostics,
            checked.diagnostics[: len(original.diagnostics)],
            strict=True,
        )
    )
    assert checked.diagnostics[-1] is checked.single_matches.entries[0].diagnostic
    assert checked.diagnostics[-1].severity is Severity.WARNING
    assert any(d.severity is Severity.ERROR for d in checked.diagnostics)


def test_malformed_and_foreign_requests_are_errors_without_obligations(
    tmp_path: Path,
) -> None:
    local = _completed(tmp_path / "local", _limited_source(right_limit=1))
    foreign = _completed(tmp_path / "foreign", _limited_source(right_limit=1))
    request = _request(local)
    base = with_project_single_match_requests(local, (request,)).single_matches.entries[
        0
    ]
    foreign_entry = with_project_single_match_requests(
        foreign, (_request(foreign),)
    ).single_matches.entries[0]
    assert base.state is foreign_entry.state is ProjectSingleMatchState.PROVED
    assert base.condition is not None and foreign_entry.condition is not None
    invalids = (
        replace(request, owner=foreign_entry.request.owner),
        replace(request, use=foreign_entry.request.use),
        replace(request, condition=foreign_entry.condition),
        replace(request, input_pairs=foreign_entry.input_pairs),
        replace(
            request, input_pairs=((base.input_pairs[0][1], base.input_pairs[0][0]),)
        ),
        replace(request, unit="distinct_final_target"),
        replace(request, unit="distinct_payload"),
        replace(request, scope="reverse"),
        replace(request, input_pairs=(object(),)),
        replace(request, use=object()),
    )
    for invalid in invalids:
        checked = with_project_single_match_requests(local, (invalid,))
        assessment = checked.single_matches.entries[0]
        assert assessment.state is ProjectSingleMatchState.INVALID
        assert not checked.ok and not checked.single_matches.obligations
        assert not assessment.proofs
        assert (
            assessment.diagnostic is not None
            and assessment.diagnostic.code == "PIE-S2338"
        )
    with pytest.raises((ValueError, TypeError), match="init=False"):
        replace(base, proofs=foreign_entry.proofs)
    with pytest.raises((ValueError, TypeError), match="init=False"):
        replace(base, state=ProjectSingleMatchState.PROVED)


def test_stale_limit_and_condition_do_not_survive_changed_right_producer(
    tmp_path: Path,
) -> None:
    before = _completed(tmp_path, _limited_source(right_limit=1))
    request = _request(before)
    proved = with_project_single_match_requests(
        before, (request,)
    ).single_matches.entries[0]
    after = _completed(tmp_path, _limited_source(right_limit=2))
    fresh_request = _request(after)
    fresh = with_project_single_match_requests(after, (fresh_request,))
    assert (
        fresh.single_matches.entries[0].state is ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert (
        with_project_single_match_requests(after, (request,))
        .single_matches.entries[0]
        .state
        is ProjectSingleMatchState.INVALID
    )
    assert proved.condition is not None
    stolen = with_project_single_match_requests(
        after, (replace(fresh_request, condition=proved.condition),)
    )
    assert stolen.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    assert not stolen.single_matches.entries[0].proofs


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full"))
@pytest.mark.parametrize(
    "target_unique,source_unique,proved", ((True, False, True), (False, True, False))
)
def test_only_target_direction_proves_matching_count(
    tmp_path: Path, target_unique: bool, source_unique: bool, proved: bool, kind: str
) -> None:
    original = _completed(
        tmp_path,
        _asymmetric_source(
            target_unique=target_unique, source_unique=source_unique
        ).replace("inner join", f"{kind} join"),
    )
    checked = with_project_single_match_requests(original, (_request(original),))
    entry = checked.single_matches.entries[0]
    assert entry.state is (
        ProjectSingleMatchState.PROVED
        if proved
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    condition = entry.condition
    assert condition is not None and condition.base_guarantee is None
    forward = tuple(
        m for m in condition.key_matches if m.binding is condition.use.target_binding
    )
    reverse = tuple(
        m
        for m in condition.key_matches
        if m.binding is not condition.use.target_binding
    )
    assert bool(forward) is target_unique and bool(reverse) is source_unique
    assert all(
        not any(root is match for root in proof.roots)
        for proof in entry.proofs
        for match in reverse
    )
    assert all(
        proof.kind is ProjectSingleMatchProofKind.MATCHED_KEY for proof in entry.proofs
    )


@pytest.mark.parametrize("all_unique", (False, True))
def test_two_direct_boundaries_keep_exact_pairs_and_independent_authority(
    tmp_path: Path, all_unique: bool
) -> None:
    from _pietto_plan_joins import _path_source, _path_requests

    source = _path_source(all_unique=all_unique)
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    requests = _path_requests(original)
    checked = with_project_single_match_requests(original, requests)
    first, second = checked.single_matches.entries
    assert first.state is ProjectSingleMatchState.PROVED
    assert second.state is (
        ProjectSingleMatchState.PROVED
        if all_unique
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    for position, entry in enumerate((first, second)):
        assert entry.request.scope is ProjectSingleMatchScope.DIRECT_BINARY
        assert entry.request.path is entry.request.hop is None
        assert entry.condition is original.roots.join_conditions.entries[position]
        assert len(entry.joins) == len(entry.input_pairs) == 1
        assert all(
            actual is expected
            for actual, expected in zip(
                entry.input_pairs[0], entry.joins[0].input_uses, strict=True
            )
        )
        assert all(
            proof.kind is ProjectSingleMatchProofKind.MATCHED_KEY
            for proof in entry.proofs
        )
    assert first.input_pairs[0][1] is not second.input_pairs[0][1]
    foreign = _completed(tmp_path / "foreign", source)
    for invalid in (
        replace(requests[0], use=_request(foreign).use),
        replace(requests[0], condition=foreign.roots.join_conditions.entries[0]),
        replace(requests[0], input_pairs=second.input_pairs),
        replace(requests[0], scope=ProjectSingleMatchScope.PATH_HOP),
        replace(requests[0], scope=ProjectSingleMatchScope.WHOLE_PATH),
    ):
        rejected = with_project_single_match_requests(original, (invalid,))
        assert (
            rejected.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
        )
        assert not rejected.single_matches.obligations


def test_request_roots_are_retained_and_cannot_graft_an_unrelated_snapshot(
    tmp_path: Path,
) -> None:
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        ProjectIRQueryBlockVerificationStatus,
    )

    original = _completed(tmp_path, _unique_source("inner", "Link(lhs, r)"))
    snapshot = build_project_query_block_ir(original)
    assert (
        verify_project_query_block_ir(snapshot).status
        is ProjectIRQueryBlockVerificationStatus.VERIFIED
    )
    checked = with_project_single_match_requests(original, (_request(original),))
    assert checked.ok
    retained = build_project_query_block_ir(checked)
    assert verify_project_query_block_ir(retained).verified
    assert len(retained.requirements) == 1
    assert retained.requirements[0].assessment is checked.single_matches.entries[0]
    assert retained.requirements[0].boundaries
    with pytest.raises(ValueError, match="every exact request occurrence"):
        replace(snapshot, completed=checked)
    object.__setattr__(snapshot, "completed", checked)
    assert (
        verify_project_query_block_ir(snapshot).status
        is ProjectIRQueryBlockVerificationStatus.INVALID
    )


def test_attaching_requests_preserves_existing_fallback_diagnostic_identity(
    tmp_path: Path,
) -> None:
    source = _source("True").replace("id = lhs.id", "total = sum(lhs.id)")
    original = _completed(tmp_path, source)
    assert not original.ok
    assert any(d.code == "PIE-S2333" for d in original.diagnostics)
    checked = with_project_single_match_requests(original, (_request(original),))
    assert all(
        a is b
        for a, b in zip(
            original.diagnostics,
            checked.diagnostics[: len(original.diagnostics)],
            strict=True,
        )
    )
    assert checked.diagnostics[-1].severity is Severity.WARNING


@pytest.mark.parametrize(
    "tail", ("row", "grouped", "global", "selected_window", "hidden_window")
)
@pytest.mark.parametrize("limited", (False, True))
def test_effective_right_proofs_use_real_tail_producers(
    tmp_path: Path, tail: str, limited: bool
) -> None:
    from _pietto_project_join_output import (
        _tail_source,
    )
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput

    source, _ = _tail_source(tail)
    if limited:
        source = (
            source.replace("    limit 2\n", "    limit 1\n")
            if tail == "row"
            else source + "    limit 1\n"
        )
    source += "query result:\n    from lhs\n    let r = upstream\n    left join r on True\n    select:\n        id = lhs.id\n"
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original, -1),))
    entry = checked.single_matches.entries[0]
    proved = limited or tail == "global"
    assert entry.state is (
        ProjectSingleMatchState.PROVED
        if proved
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    upstream = next(
        e
        for e in original.effective_outputs.entries
        if e.owner.definition.name == "upstream"
    )
    assert isinstance(upstream, ProjectCompletedEffectiveOutput)
    for proof in entry.proofs:
        assert proof.roots[0] is upstream
        assert proof.roots[1] is entry.input_pairs[0][1]
    assert checked.ok


@pytest.mark.parametrize("limited", (False, True))
def test_real_unknown_right_grain_is_not_a_row_count_proof(
    tmp_path: Path, limited: bool
) -> None:
    from _pietto_project_join_full import (
        _two_current_globals_full,
    )
    from pietto._project.project_grain import ProjectGrainBasisState

    source = _two_current_globals_full("        total = left_global.total\n").replace(
        "query result:", "table unknown_rows:"
    )
    if limited:
        source += "    limit 1\n"
    source += "query result:\n    from lhs\n    let r = unknown_rows\n    left join r on True\n    select:\n        id = lhs.id\n"
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original, -1),))
    entry = checked.single_matches.entries[0]
    assert entry.joins[0].right_input.grain.state is ProjectGrainBasisState.UNKNOWN
    assert entry.state is (
        ProjectSingleMatchState.PROVED
        if limited
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert bool(entry.proofs) is limited
    if limited:
        assert entry.proofs[0].kind is ProjectSingleMatchProofKind.RIGHT_LIMIT


def test_import_reexport_replay_keep_exact_limited_right_entry(tmp_path: Path) -> None:
    from _pietto_project_join_output import (
        _tail_source,
    )
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectConcreteNoJoinReplay,
    )

    source, _ = _tail_source("row")
    source = source.replace("    limit 2\n", "    limit 1\n")
    source += "table replay:\n    from upstream\n    select:\n        id\nexport table replay\n"
    (tmp_path / "a.pietto").write_text(source)
    (tmp_path / "b.pietto").write_text(
        'from "a.pietto" import table replay as Public\nexport table Public\n'
    )
    main = """from "b.pietto" import table Public as Imported
shape Local:
    id: Int
source rows: Local = postgres.table("rows")
query result:
    from rows
    let r = Imported
    left join r on True
    select:
        id = rows.id
"""
    original = _completed(tmp_path, main)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original, -1),))
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.PROVED
    proof = entry.proofs[0]
    replay = proof.roots[0]
    assert (
        isinstance(replay, ProjectCompletedEffectiveOutput)
        and replay.owner.definition.name == "replay"
    )
    assert isinstance(replay.root, ProjectConcreteNoJoinReplay)
    assert any(root is replay.root for root in proof.roots)
    bound = proof.roots[-1]
    assert (
        isinstance(bound, ProjectRelationLimit)
        and bound.owner.definition.name == "upstream"
    )
    assert bound.row_count_upper_bound == 1


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("output_format", ("text", "json"))
def test_real_cli_diagnostic_consumer_renders_private_warning_without_new_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: CheckMode,
    output_format: str,
) -> None:
    from pietto import cli
    from pietto._project.model import ProjectSemanticResult

    _completed(tmp_path, f"mode {mode.value}\n" + _source("True", kind="left"))
    builder = cli.build_project_completed_semantic_result
    observed: list[ProjectConcreteCompletedSemanticResult] = []

    def requested(
        semantic: ProjectSemanticResult,
    ) -> ProjectConcreteCompletedSemanticResult:
        original = builder(semantic)
        assert isinstance(original, ProjectConcreteCompletedSemanticResult)
        checked = with_project_single_match_requests(original, (_request(original),))
        observed.append(checked)
        return checked

    monkeypatch.setattr(cli, "build_project_completed_semantic_result", requested)
    args = ["check", "--project", str(tmp_path)]
    if output_format == "json":
        args.extend(["--format", "json"])
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert len(observed) == 1 and observed[0].ok
    assert (
        observed[0].diagnostics[0] is observed[0].single_matches.entries[0].diagnostic
    )
    if output_format == "json":
        document = json.loads(captured.out)
        assert document["schema_version"] == 2 and document["ok"]
        assert document["diagnostics"][0]["severity"] == "warning"
        assert not captured.err
    else:
        assert "PIE-S2337" in captured.out + captured.err
        assert "warning" in (captured.out + captured.err).lower()


def test_predicate_filter_keeps_exact_condition_and_rejects_replaced_match(
    tmp_path: Path,
) -> None:
    source = _unique_source("inner", "Link(lhs, r) and r.id > 0")
    original = _completed(tmp_path / "original", source)
    condition = original.roots.join_conditions.entries[0]
    request = _request(original)
    checked = with_project_single_match_requests(original, (request,))
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.PROVED
    match = next(
        m for m in condition.key_matches if m.binding is condition.use.target_binding
    )
    assert entry.proofs[0].roots[1] is match
    changed = _completed(tmp_path / "changed", source.replace("r.id > 0", "r.id < 0"))
    replacement = changed.roots.join_conditions.entries[0]
    invalid = with_project_single_match_requests(
        original, (replace(request, condition=replacement),)
    )
    assert invalid.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(condition, key_matches=replacement.key_matches)


def test_unique_last_target_does_not_bound_an_earlier_fanout(tmp_path: Path) -> None:
    source = _asymmetric_source(target_unique=False, source_unique=True).replace(
        "    let r = rhs\n    inner join r on Link(lhs, r)\n",
        "    let mid = rhs\n    inner join mid on Link(lhs, mid)\n"
        "    let r = lhs\n    inner join r on Link(r, mid)\n",
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(
        original, (_request(original), _request(original, 1))
    )
    first, last = checked.single_matches.entries
    assert first.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert last.state is ProjectSingleMatchState.PROVED
    assert (
        not first.proofs
        and last.proofs[0].kind is ProjectSingleMatchProofKind.MATCHED_KEY
    )
    actual_paths = (("l0", "r0", "l0"), ("l0", "r1", "l0"))
    assert len(actual_paths) == 2
    assert actual_paths[0][-1] == actual_paths[1][-1]
    assert first.input_pairs != last.input_pairs


def test_existing_warning_and_request_warning_share_json_consumer_in_order(
    tmp_path: Path,
) -> None:
    from pietto.parser_api import parse_source
    from pietto.semantic import analyze

    parsed_warning = parse_source(
        'source raw = postgres.table("raw")\n', path="warning.pietto"
    )
    assert parsed_warning.ast is not None
    warnings = analyze(parsed_warning.ast).diagnostics
    assert len(warnings) == 1 and warnings[0].code == "PIE-S2303"
    assert warnings[0].severity is Severity.WARNING
    original = _completed(tmp_path, _source("True"))
    checked = with_project_single_match_requests(original, (_request(original),))
    diagnostics = (*warnings, *checked.diagnostics)
    document = project_check_result_to_json_dict(
        check_project_parse_only(tmp_path), semantic_diagnostics=diagnostics
    )
    wire = json.loads(json.dumps(document))
    assert wire["ok"]
    assert [item["code"] for item in wire["diagnostics"]] == ["PIE-S2303", "PIE-S2337"]
    assert all(item["severity"] == "warning" for item in wire["diagnostics"])
    assert diagnostics[0] is warnings[0]
    assert diagnostics[1] is checked.single_matches.entries[0].diagnostic


def test_cycle_branch_does_not_block_independent_requirement_and_allocates_nothing(
    tmp_path: Path,
) -> None:
    source = (
        _source("True")
        + """table a:
    from b
    let extra = lhs
    inner join extra on True
    select:
        id = b.id
table b:
    from a
    select:
        id
"""
    )
    original = _completed(tmp_path, source)
    assert not original.ok and original.completion.topology.blocked_owners
    checked = with_project_single_match_requests(
        original, (_request(original), _request(original, 1))
    )
    assert tuple(e.state for e in checked.single_matches.entries) == (
        ProjectSingleMatchState.LEGAL_UNPROVED,
        ProjectSingleMatchState.INVALID,
    )
    assert len(checked.single_matches.obligations) == 1 and not checked.ok
    assert checked.effective_outputs is original.effective_outputs
    assert checked.verification is original.verification
    assert all(
        a is b
        for a, b in zip(
            original.diagnostics,
            checked.diagnostics[: len(original.diagnostics)],
            strict=True,
        )
    )


@pytest.mark.parametrize(
    "tail", ("row", "grouped", "global", "selected_window", "hidden_window")
)
def test_completed_left_limit_or_global_does_not_bound_right_matches(
    tmp_path: Path, tail: str
) -> None:
    from _pietto_project_join_output import (
        _tail_source,
    )

    source, field_name = _tail_source(tail)
    source = (
        source.replace("    limit 2\n", "    limit 1\n")
        if tail == "row"
        else source + "    limit 1\n"
    )
    source += f"query result:\n    from upstream\n    let r = rhs\n    full join r on True\n    select:\n        value = upstream.{field_name}\n"
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original, -1),))
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert entry.joins[0].use.target_binding.relation_name == "rhs"
    assert not entry.proofs and checked.ok


def _modern_predicate_match_source(
    on: str, *, tail: str = "", templates: bool = True
) -> str:
    declarations = (
        """relationship ById(a: Row, b: Row):
    a.id == b.id
relationship ActiveTenant(a: Row, b: Row):
    a.tenant == b.tenant and b.status == "active"
"""
        if templates
        else ""
    )
    return (
        """shape Row:
    id: Int
    tenant: Int
    status: Text | None
    row_key = unique(id, tenant)
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
"""
        + declarations
        + f"""query result:
    from lhs
    let r = rhs
    left join r on {on}
{tail}    select:
        id = lhs.id
        matched = r.id
"""
    )


def test_modern_predicate_calls_jointly_prove_composite_target_key(
    tmp_path: Path,
) -> None:
    from pietto._project.model import ProjectRowFieldNullability
    from pietto._project.project_current_joins import current_forward_at_most_one
    from pietto._project.project_relationship_match_guarantees import (
        ProjectRelationshipMinimumBound,
    )

    source = _modern_predicate_match_source(
        "ById(lhs, r) and ActiveTenant(lhs, r) and ById(lhs, r)"
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is ProjectSingleMatchState.PROVED
    condition = assessment.condition
    assert condition is not None and condition.base_guarantee is None
    assert current_forward_at_most_one(condition)
    assert len(condition.mandatory_equalities) == 3
    predicate = condition.environment.predicate_expression
    assert predicate is not None and len(predicate.calls) == 3
    assert (
        tuple(equality.calls[0] for equality in condition.mandatory_equalities)
        == predicate.calls
    )
    matches = tuple(
        match
        for match in condition.key_matches
        if match.binding is condition.use.target_binding
    )
    assert len(matches) == 1 and len(matches[0].equalities) == 3
    match = matches[0]
    assert any(match.key is key for key in match.properties.keys)
    with pytest.raises(ValueError, match="complete exact input key"):
        replace(match, key=replace(match.key))
    assert match.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
    assert match.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert all(
        bindings[1] is condition.use.target_binding
        for bindings in predicate.argument_bindings
    )
    assert tuple(proof.kind for proof in assessment.proofs) == (
        ProjectSingleMatchProofKind.MATCHED_KEY,
    )
    join = assessment.joins[0]
    assert all(
        field.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for field in join.output.row_shape.fields[len(join.left_input.fields) :]
    )


@pytest.mark.parametrize("context", ("or", "not", "where", "select"))
def test_modern_predicate_value_context_never_proves_on_cardinality(
    tmp_path: Path, context: str
) -> None:
    predicate = "ById(lhs, r) and ActiveTenant(lhs, r)"
    on = (
        "ById(lhs, r) or ActiveTenant(lhs, r)"
        if context == "or"
        else f"not ({predicate})"
        if context == "not"
        else "True"
    )
    source = _modern_predicate_match_source(
        on, tail=f"    where {predicate}\n" if context == "where" else ""
    )
    if context == "select":
        source = source.replace(
            "        matched = r.id", f"        matched = {predicate}"
        )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert assessment.condition is not None
    assert (
        assessment.condition.mandatory_equalities
        == assessment.condition.key_matches
        == ()
    )
    assert not assessment.proofs


def test_handwritten_on_equality_does_not_gain_predicate_authority(
    tmp_path: Path,
) -> None:
    original = _completed(
        tmp_path,
        _modern_predicate_match_source(
            "lhs.id == r.id and lhs.tenant == r.tenant",
            templates=False,
        ),
    )
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert assessment.condition is not None
    assert (
        assessment.condition.mandatory_equalities
        == assessment.condition.key_matches
        == ()
    )
    from pietto._project.project_join_conditions import ProjectJoinConditionEquality

    with pytest.raises(ValueError, match="predicate-call origin"):
        ProjectJoinConditionEquality(
            condition=assessment.condition, conjunct_position=0
        )
