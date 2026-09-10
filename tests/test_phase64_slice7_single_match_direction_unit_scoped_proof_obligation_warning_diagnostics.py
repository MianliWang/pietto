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
    ProjectSingleMatchRequest,
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
from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
    _unique_source,
)

from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)


def test_default_authored_compilation_has_no_implicit_single_match(
    tmp_path: Path,
) -> None:
    completed = _completed(tmp_path, _source("true", kind="semi"))
    assert completed.ok and not completed.diagnostics
    assert completed.single_matches.requests == ()
    assert completed.single_matches.obligations == ()


def _request(
    completed: ProjectConcreteCompletedSemanticResult, position: int = 0
) -> ProjectSingleMatchRequest:
    condition = completed.roots.join_conditions.entries[position]
    return ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
def test_unproved_actual_matches_warn_on_success_in_every_mode(
    tmp_path: Path, mode: CheckMode, kind: str
) -> None:
    original = _completed(tmp_path, f"mode {mode.value}\n" + _source("true", kind=kind))
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


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
@pytest.mark.parametrize("refinement", (False, True))
def test_exact_relationship_and_refinement_prove_same_direction(
    tmp_path: Path, kind: str, refinement: bool
) -> None:
    source = _unique_source(
        kind,
        "r.id > 0" if refinement else None,
        via="        via link: l -> r\n" if refinement else "",
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original),))
    assessment = checked.single_matches.entries[0]
    assert assessment.state is ProjectSingleMatchState.PROVED
    assert checked.ok and not checked.diagnostics
    condition = assessment.condition
    assert condition is not None and condition.base_guarantee is not None
    assert (
        condition.base_guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    )
    proof = assessment.proofs[0]
    expected = (
        condition.refinement_guarantee if refinement else condition.base_guarantee
    )
    assert proof.roots[-1] is expected
    assert proof.kind is (
        ProjectSingleMatchProofKind.REFINEMENT
        if refinement
        else ProjectSingleMatchProofKind.RELATIONSHIP
    )
    assert not assessment.downstream_enforcement_required


def _limited_source(
    *, right_limit: int | None, post_limit: bool = False, where: bool = False
) -> str:
    source = _source("true").split("query result:", 1)[0]
    source += "table right_named:\n    from rhs\n    select:\n        id\n"
    if right_limit is not None:
        source += f"    limit {right_limit}\n"
    source += "query result:\n    from lhs\n    inner join right_named as r:\n        from lhs\n        on true\n"
    if where:
        source += "    where lhs.id == 1\n"
    source += "    select:\n        id = lhs.id\n"
    if post_limit:
        source += "    limit 1\n"
    return source


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
    for kind in ("inner", "semi", "anti"):
        original = _completed(tmp_path / kind, _source("lhs.id == r.id", kind=kind))
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
        _source("true") + "query other:" + _source("true").split("query result:", 1)[1]
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
        _source("true")
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


def _asymmetric_source(*, target_unique: bool, source_unique: bool = False) -> str:
    return f"""shape LeftRow:
    id: Int not null
{("    unique key on id" + chr(10)) if source_unique else ""}shape RightRow:
    id: Int not null
{("    unique key on id" + chr(10)) if target_unique else ""}source lhs: LeftRow is postgres.table("lhs")
source rhs: RightRow is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
query result:
    from lhs
    inner join rhs as r:
        from lhs
    select:
        id = lhs.id
"""


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
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
    assert entry.condition is not None and entry.condition.base_guarantee is not None
    base = entry.condition.base_guarantee
    reverse = tuple(
        g
        for g in entry.condition.root.uses.index.directions
        if g.source_output is base.target_output
        and g.target_output is base.source_output
    )
    assert len(reverse) == 1
    assert (
        reverse[0].maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    ) is source_unique
    assert all(
        not any(root is reverse[0] for root in proof.roots) for proof in entry.proofs
    )


def test_hop_and_whole_path_keep_their_exact_units_and_complete_authority(
    tmp_path: Path,
) -> None:
    source = (
        _asymmetric_source(target_unique=True)
        .replace("inner join rhs as r:", "inner join lhs as r:")
        .replace(
            "        from lhs\n    select:",
            "        from lhs\n        via link: l -> r\n        via link: r -> l\n    select:",
        )
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    condition = original.roots.join_conditions.entries[0]
    path = condition.effective_use.path
    assert path is not None and len(path.steps) == 2
    request = _request(original)
    first = replace(
        request, scope=ProjectSingleMatchScope.PATH_HOP, path=path, hop=path.steps[0]
    )
    second = replace(first, hop=path.steps[1])
    whole = replace(request, scope=ProjectSingleMatchScope.WHOLE_PATH, path=path)
    checked = with_project_single_match_requests(
        original, (first, second, whole, request)
    )
    assert tuple(e.state for e in checked.single_matches.entries) == (
        ProjectSingleMatchState.PROVED,
        ProjectSingleMatchState.LEGAL_UNPROVED,
        ProjectSingleMatchState.LEGAL_UNPROVED,
        ProjectSingleMatchState.INVALID,
    )
    assert len(checked.single_matches.entries[2].input_pairs) == 2
    assert (
        checked.single_matches.entries[0].proofs[0].roots[-1] is path.steps[0].guarantee
    )
    assert not checked.single_matches.entries[2].proofs
    foreign = _completed(tmp_path / "foreign", source)
    other_path = foreign.roots.join_conditions.entries[0].effective_use.path
    assert other_path is not None
    invalid = with_project_single_match_requests(
        original, (replace(first, hop=other_path.steps[0]),)
    )
    assert invalid.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    keyed = _completed(
        tmp_path / "all_keyed",
        source.replace(
            "shape LeftRow:\n    id: Int not null\n",
            "shape LeftRow:\n    id: Int not null\n    unique key on id\n",
        ),
    )
    all_path = keyed.roots.join_conditions.entries[0].effective_use.path
    assert all_path is not None
    all_request = replace(
        _request(keyed), scope=ProjectSingleMatchScope.WHOLE_PATH, path=all_path
    )
    all_checked = with_project_single_match_requests(keyed, (all_request,))
    assert all_checked.single_matches.entries[0].state is ProjectSingleMatchState.PROVED
    assert all_checked.single_matches.entries[0].proofs[0].roots[0] is all_path


def test_request_roots_are_retained_and_cannot_graft_an_unrelated_snapshot(
    tmp_path: Path,
) -> None:
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        ProjectIRQueryBlockVerificationStatus,
    )

    original = _completed(tmp_path, _unique_source("inner", None))
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
    source = _source("true").replace("id = lhs.id", "total = sum(lhs.id)")
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
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
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
    source += "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
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
    from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
        _two_current_globals_full,
    )
    from pietto._project.project_grain import ProjectGrainBasisState

    source = _two_current_globals_full("        total = left_global.total\n").replace(
        "query result:", "table unknown_rows:"
    )
    if limited:
        source += "    limit 1\n"
    source += "query result:\n    from lhs\n    anti join unknown_rows as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
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


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("limited", (False, True))
def test_self_use_distinguishes_left_right_roles_even_with_same_producer(
    tmp_path: Path, kind: str, limited: bool
) -> None:
    source = (
        _limited_source(right_limit=1 if limited else 2)
        .replace(
            "    from lhs\n    inner join right_named as r:\n        from lhs\n",
            f"    from right_named\n    {kind} join right_named as r:\n        from right_named\n",
        )
        .replace("id = lhs.id", "id = right_named.id")
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    request = _request(original)
    checked = with_project_single_match_requests(original, (request,))
    entry = checked.single_matches.entries[0]
    assert entry.joins[0].left_input is entry.joins[0].right_input
    lhs, rhs = entry.input_pairs[0]
    assert lhs is not rhs and lhs.output is rhs.output
    assert entry.state is (
        ProjectSingleMatchState.PROVED
        if limited
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    swapped = with_project_single_match_requests(
        original, (replace(request, input_pairs=((rhs, lhs),)),)
    )
    assert swapped.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    assert not swapped.single_matches.entries[0].proofs


def test_import_reexport_replay_keep_exact_limited_right_entry(tmp_path: Path) -> None:
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
        _tail_source,
    )
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectConcreteNoJoinReplay,
    )

    source, _ = _tail_source("row")
    source = source.replace("    limit 2\n", "    limit 1\n")
    source += "table replay:\n    from upstream\n    select:\n        id\nexport:\n    table replay\n"
    (tmp_path / "a.pietto").write_text(source)
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table replay as Public\nexport:\n    table Public\n'
    )
    main = """import "b.pietto":
    table Public as Imported
shape Local:
    id: Int not null
source rows: Local is postgres.table("rows")
query result:
    from rows
    left join Imported as r:
        from rows
        on true
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

    _completed(tmp_path, f"mode {mode.value}\n" + _source("true", kind="anti"))
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


@pytest.mark.parametrize("kind", ("semi", "full"))
def test_invalid_multihop_new_kind_keeps_original_errors_without_obligation(
    tmp_path: Path, kind: str
) -> None:
    source = _source(
        None, kind=kind, via="        via link: l -> r\n        via link: r -> l\n"
    )
    original = _completed(tmp_path, source)
    assert not original.ok
    checked = with_project_single_match_requests(original, (_request(original),))
    assert not checked.ok and not checked.single_matches.obligations
    assert checked.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    assert all(
        a is b
        for a, b in zip(
            original.diagnostics,
            checked.diagnostics[: len(original.diagnostics)],
            strict=True,
        )
    )
    assert any(d.code == "PIE-S2336" for d in checked.diagnostics)
    assert not any(d.code == "PIE-S2337" for d in checked.diagnostics)


def test_explicit_authored_hop_keeps_refinement_and_rejects_replaced_refinement(
    tmp_path: Path,
) -> None:
    source = _unique_source("semi", "r.id > 0", via="        via link: l -> r\n")
    original = _completed(tmp_path / "original", source)
    condition = original.roots.join_conditions.entries[0]
    request = replace(
        _request(original),
        scope=ProjectSingleMatchScope.PATH_HOP,
        hop=condition.use.step_uses[0],
    )
    checked = with_project_single_match_requests(original, (request,))
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.PROVED
    assert entry.proofs[0].roots[-1] is condition.refinement_guarantee
    changed = _completed(tmp_path / "changed", source.replace("r.id > 0", "r.id < 0"))
    replacement = changed.roots.join_conditions.entries[0]
    invalid = with_project_single_match_requests(
        original, (replace(request, condition=replacement),)
    )
    assert invalid.single_matches.entries[0].state is ProjectSingleMatchState.INVALID
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(condition, refinement_guarantee=replacement.refinement_guarantee)


def test_unique_final_target_and_last_hop_proof_do_not_bound_whole_path(
    tmp_path: Path,
) -> None:
    source = (
        _asymmetric_source(target_unique=False, source_unique=True)
        .replace("inner join rhs as r:", "inner join lhs as r:")
        .replace(
            "        from lhs\n    select:",
            "        from lhs\n        via link: l -> r\n        via link: r -> l\n    select:",
        )
    )
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    path = original.roots.join_conditions.entries[0].effective_use.path
    assert path is not None
    whole = replace(
        _request(original), scope=ProjectSingleMatchScope.WHOLE_PATH, path=path
    )
    hop = replace(whole, scope=ProjectSingleMatchScope.PATH_HOP, hop=path.steps[1])
    checked = with_project_single_match_requests(original, (hop, whole))
    assert tuple(e.state for e in checked.single_matches.entries) == (
        ProjectSingleMatchState.PROVED,
        ProjectSingleMatchState.LEGAL_UNPROVED,
    )
    actual_paths = (("l0", "r0", "l0"), ("l0", "r1", "l0"))
    assert len(actual_paths) == 2
    assert actual_paths[0][-1] == actual_paths[1][-1]
    assert not checked.single_matches.entries[1].proofs


def test_existing_warning_and_request_warning_share_json_consumer_in_order(
    tmp_path: Path,
) -> None:
    from pietto.parser_api import parse_source
    from pietto.semantic import analyze

    parsed_warning = parse_source(
        "shape WarningRow:\n    value: Text\n", path="warning.pietto"
    )
    assert parsed_warning.ast is not None
    warnings = analyze(parsed_warning.ast).diagnostics
    assert len(warnings) == 1 and warnings[0].code == "PIE-S2005"
    assert warnings[0].severity is Severity.WARNING
    original = _completed(tmp_path, _source("true"))
    checked = with_project_single_match_requests(original, (_request(original),))
    diagnostics = (*warnings, *checked.diagnostics)
    document = project_check_result_to_json_dict(
        check_project_parse_only(tmp_path), semantic_diagnostics=diagnostics
    )
    wire = json.loads(json.dumps(document))
    assert wire["ok"]
    assert [item["code"] for item in wire["diagnostics"]] == ["PIE-S2005", "PIE-S2337"]
    assert all(item["severity"] == "warning" for item in wire["diagnostics"])
    assert diagnostics[0] is warnings[0]
    assert diagnostics[1] is checked.single_matches.entries[0].diagnostic


def test_cycle_branch_does_not_block_independent_requirement_and_allocates_nothing(
    tmp_path: Path,
) -> None:
    source = (
        _source("true")
        + """table a:
    from b
    inner join lhs as extra:
        from b
        on true
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
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
        _tail_source,
    )

    source, field_name = _tail_source(tail)
    source = (
        source.replace("    limit 2\n", "    limit 1\n")
        if tail == "row"
        else source + "    limit 1\n"
    )
    source += f"query result:\n    from upstream\n    full join rhs as r:\n        from upstream\n        on true\n    select:\n        value = upstream.{field_name}\n"
    original = _completed(tmp_path, source)
    assert original.ok, original.diagnostics
    checked = with_project_single_match_requests(original, (_request(original, -1),))
    entry = checked.single_matches.entries[0]
    assert entry.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert entry.joins[0].use.target_binding.relation_name == "rhs"
    assert not entry.proofs and checked.ok
