from __future__ import annotations

from dataclasses import dataclass, fields, replace
import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto._project import project_joined_aggregation as joined_aggregation
from pietto._project import project_joined_qualify as joined_qualify
from pietto._project import project_joined_row_filter as joined_row_filter
from pietto._project import project_joined_windows as joined_windows
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_completed_semantics as completed_semantics
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectNoJoinScalarExpression,
    ProjectNonConcreteRelationLimit,
    ProjectNonConcreteRelationOrdering,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_completed_semantics.py"
CLI = REPO_ROOT / "src/pietto/cli.py"
JSON_V2 = REPO_ROOT / "src/pietto/_project/json_v2.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice13-completed-project-semantic-result-public-check-boundaries-v1.md"
)
PROJECT_JSON_KEYS = (
    "schema_version",
    "command",
    "mode",
    "ok",
    "project",
    "inputs",
    "diagnostics",
    "cli_errors",
    "result",
)

POSITIVE_SOURCE = """shape AccountRow:
    id: Int not null
    metric: Int nullable
    unique account_key on id
shape EventRow:
    id: Int not null
    account_id: Int not null
    metric: Int nullable
    unique event_key on id
source accounts: AccountRow is postgres.table("accounts")
source events: EventRow is postgres.table("events")
relationship account_events:
    endpoint account: accounts
    endpoint event: events
    on account.id == event.account_id
query plain:
    from accounts
    select:
        id
query joined:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
        event_id = event.id
query downstream:
    from joined
    select:
        event_id
query grouped:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(event.metric)
query global:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
query qualified:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3
"""

PRECISE_FAILURE_SOURCE = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
query bad:
    from rows
    select:
        missing
"""

FALLBACK_FAILURE_SOURCE = """query bad:
    from missing
    select:
        id
query downstream:
    from bad
    select:
        id
"""

SOURCE_FAILURE_SOURCE = """source rows: MissingShape is postgres.table("rows")
"""

NESTED_WINDOW_FAILURE_SOURCE = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        mystery = mystery_window() window:
            order by:
                id
"""

DIAGNOSTIC_MATRIX_SOURCE = (
    POSITIVE_SOURCE
    + """query where_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where not_a_builtin(event.metric) > 0
    select:
        event_id = event.id
query downstream_where_bad:
    from joined
    where not_a_builtin(event_id) > 0
    select:
        event_id
query qualify_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        missing > 0
query order_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        id = row_number() window:
            order by:
                event.id
    order by:
        id
query order_precise:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
    order by:
        metric
query limit_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit -1
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    parse_result: ProjectParseCheckResult
    semantic_result: ProjectSemanticResult
    completed: completed_semantics.ProjectConcreteCompletedSemanticResult


def _project(root: Path, source: str, *, schema_version: int = 2) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")
    return root


def _build(root: Path, source: str) -> _Built:
    parse_result = check_project_parse_only(_project(root, source))
    assert parse_result.ok, parse_result.diagnostics
    semantic_result = build_empty_project_semantic_result(parse_result)
    completed = completed_semantics.build_project_completed_semantic_result(
        semantic_result
    )
    assert type(completed) is completed_semantics.ProjectConcreteCompletedSemanticResult
    return _Built(parse_result, semantic_result, completed)


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s13-positive"), POSITIVE_SOURCE)


@pytest.fixture(scope="module")
def foreign(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s13-foreign"), POSITIVE_SOURCE)


@pytest.fixture(scope="module")
def diagnostic_matrix(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(
        tmp_path_factory.mktemp("p63s13-diagnostic-matrix"),
        DIAGNOSTIC_MATRIX_SOURCE,
    )


def _entry(
    built: _Built,
    name: str,
) -> ProjectExistingEffectiveOutput | ProjectCompletedEffectiveOutput:
    matches = tuple(
        entry
        for entry in built.completed.effective_outputs.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    entry = matches[0]
    assert type(entry) in {
        ProjectExistingEffectiveOutput,
        ProjectCompletedEffectiveOutput,
    }
    return cast(ProjectExistingEffectiveOutput | ProjectCompletedEffectiveOutput, entry)


def _terminal_entry(
    built: _Built,
    name: str,
) -> ProjectEffectiveOutputCompletionTerminal:
    matches = tuple(
        entry
        for entry in built.completed.effective_outputs.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    entry = matches[0]
    assert type(entry) is ProjectEffectiveOutputCompletionTerminal
    return entry


def test_concrete_result_closes_exact_existing_chain_and_all_positive_families(
    positive: _Built,
) -> None:
    result = positive.completed
    roots = result.roots
    assert not positive.semantic_result.ok
    assert result.ok
    assert result.diagnostics == ()
    assert result.semantic_result is roots.semantic_result is positive.semantic_result
    assert result.verification is roots.verification
    assert result.completion is roots.completion
    assert result.effective_outputs is roots.effective_outputs
    assert result.completion.verification is result.verification
    assert result.effective_outputs.base is result.completion
    assert (
        result.effective_outputs.joined_qualifies.window_set.aggregation_set.filter_set.completion
        is result.completion
    )
    assert tuple(
        entry.owner.identity.declared_name for entry in result.effective_outputs.entries
    ) == (
        "accounts",
        "events",
        "plain",
        "joined",
        "downstream",
        "grouped",
        "global",
        "qualified",
    )
    assert all(
        type(entry) in {ProjectExistingEffectiveOutput, ProjectCompletedEffectiveOutput}
        for entry in result.effective_outputs.entries
    )
    joined = cast(ProjectCompletedEffectiveOutput, _entry(positive, "joined"))
    downstream = cast(ProjectCompletedEffectiveOutput, _entry(positive, "downstream"))
    grouped = cast(ProjectCompletedEffectiveOutput, _entry(positive, "grouped"))
    global_ = cast(ProjectCompletedEffectiveOutput, _entry(positive, "global"))
    qualified = cast(ProjectCompletedEffectiveOutput, _entry(positive, "qualified"))
    downstream_root = cast(ProjectConcreteNoJoinReplay, downstream.root)
    assert downstream_root.upstream_entry is joined
    assert grouped.row_domain.kind.value == "grouped"
    assert global_.row_domain.kind.value == "global"
    assert tuple(field.output_name for field in qualified.fields) == (
        "event_id",
        "ranked",
    )
    assert qualified.root is next(
        item
        for item in result.effective_outputs.joined_qualifies.results
        if item.window_stage.input_aggregation.input_filter.entry.owner
        is qualified.owner
    )


@pytest.mark.parametrize(
    ("mode", "reason"),
    (
        (
            ProjectCompilationMode.LEGACY_FLAT,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE,
        ),
        (
            ProjectCompilationMode.PACKAGE_ROOT,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.PACKAGE_ROOT_MODE,
        ),
    ),
)
def test_direct_builder_is_typed_fail_closed_for_non_positive_modes(
    mode: ProjectCompilationMode,
    reason: completed_semantics.ProjectCompletedSemanticNonConcreteReason,
) -> None:
    semantic = ProjectSemanticResult(
        root=None,
        config_path=None,
        model=None,
        compilation_mode=mode,
    )
    result = completed_semantics.build_project_completed_semantic_result(semantic)
    assert type(result) is completed_semantics.ProjectNonConcreteCompletedSemanticResult
    assert result.semantic_result is semantic
    assert result.reason is reason
    assert result.diagnostics is semantic.diagnostics
    assert result.verification is result.completion is result.effective_outputs is None
    assert not result.ok


def test_completed_roots_reject_equal_looking_foreign_grafts(
    positive: _Built,
    foreign: _Built,
) -> None:
    local = positive.completed
    other = foreign.completed
    assert local.semantic_result is not other.semantic_result
    assert local.verification is not other.verification
    assert local.completion is not other.completion
    assert local.effective_outputs is not other.effective_outputs

    same_completion_foreign_overlay = replace(local.effective_outputs)
    assert same_completion_foreign_overlay is not local.effective_outputs
    with pytest.raises((TypeError, ValueError), match="exact|continuity|init=False"):
        replace(local.roots, effective_outputs=same_completion_foreign_overlay)

    for change in (
        {"verification": other.verification},
        {"completion": other.completion},
        {"effective_outputs": other.effective_outputs},
    ):
        with pytest.raises(
            (TypeError, ValueError), match="exact|continuity|init=False"
        ):
            replace(local.roots, **change)

    with pytest.raises(ValueError, match="Slice-7|exact"):
        replace(
            local.effective_outputs,
            joined_qualifies=other.effective_outputs.joined_qualifies,
        )
    with pytest.raises(ValueError, match="exact|owner-local"):
        replace(
            local.effective_outputs,
            entries=other.effective_outputs.entries,
        )
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(local, semantic_result=other.semantic_result)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(local, diagnostics=other.diagnostics)

    exact = replace(local)
    assert exact.roots is local.roots
    assert exact.semantic_result is local.semantic_result
    assert exact.verification is local.verification
    assert exact.completion is local.completion
    assert exact.effective_outputs is local.effective_outputs


def test_final_diagnostics_preserve_precise_errors_without_content_dedup(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "precise", PRECISE_FAILURE_SOURCE)
    result = built.completed
    terminal = next(
        entry
        for entry in result.effective_outputs.entries
        if entry.owner.identity.declared_name == "bad"
    )
    assert type(terminal) is ProjectEffectiveOutputTerminal
    helper_error = terminal.fragment.semantic_facts.helper_diagnostics[0]
    assert not result.ok
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        "PIE-S2102",
        "PIE-S2102",
    )
    assert result.diagnostics[0] is built.semantic_result.diagnostics[0]
    assert result.diagnostics[1] is helper_error
    assert result.diagnostics[0] is not result.diagnostics[1]
    assert not any(diagnostic.code == "PIE-S2333" for diagnostic in result.diagnostics)


def test_missing_terminal_errors_receive_one_ordered_public_fallback_each(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "fallback", FALLBACK_FAILURE_SOURCE)
    result = built.completed
    assert not result.ok
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (
        "PIE-S2301",
        "PIE-S2333",
        "PIE-S2333",
    )
    assert tuple(diagnostic.message for diagnostic in result.diagnostics[1:]) == (
        "Project relation semantic completion is unavailable: bad",
        "Project relation semantic completion is unavailable: downstream",
    )
    assert tuple(
        (diagnostic.location.path, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics[1:]
    ) == (("main.pietto", 1, 1), ("main.pietto", 5, 1))
    rendered = " ".join(diagnostic.message for diagnostic in result.diagnostics)
    for private in (
        "HISTORICAL_NON_CONCRETE",
        "UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE",
        "ProjectEffectiveOutputTerminal",
        "ProjectIR",
        "object id",
    ):
        assert private not in rendered


def test_non_concrete_source_relation_receives_public_fallback_without_traceback(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "source-failure", SOURCE_FAILURE_SOURCE)
    result = built.completed
    assert not result.ok
    fallbacks = tuple(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "PIE-S2333"
    )
    assert len(fallbacks) == 1
    assert fallbacks[0].message == (
        "Project relation semantic completion is unavailable: rows"
    )
    assert (
        fallbacks[0].location.path,
        fallbacks[0].location.line,
        fallbacks[0].location.column,
    ) == ("main.pietto", 1, 1)


def test_nested_window_error_is_retained_by_identity_instead_of_fallback(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "nested-window", NESTED_WINDOW_FAILURE_SOURCE)
    entry = next(
        item
        for item in built.completed.effective_outputs.entries
        if item.owner.identity.declared_name == "result"
    )
    assert type(entry) is ProjectEffectiveOutputTerminal
    retained = entry.fragment.semantic_facts.window_outputs[0].diagnostics[0]
    assert retained.code == "PIE-S2103"
    assert any(diagnostic is retained for diagnostic in built.completed.diagnostics)
    assert not any(
        diagnostic.code == "PIE-S2333" for diagnostic in built.completed.diagnostics
    )


def test_nested_where_scalar_error_is_retained_by_identity(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "where_bad")
    qualify = entry.joined_qualify
    assert type(qualify) is joined_qualify.ProjectNonConcreteJoinedQualify
    stage = qualify.window_stage
    assert type(stage) is joined_windows.ProjectNonConcreteJoinedWindowStage
    aggregation = stage.input_aggregation
    assert type(aggregation) is joined_aggregation.ProjectNonConcreteJoinedAggregation
    row_filter = aggregation.input_filter
    assert type(row_filter) is joined_row_filter.ProjectNonConcreteJoinedRowFilter
    retained = row_filter.diagnostics[0]
    assert retained.code == "PIE-S2103"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("where_bad")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )

    replay = _terminal_entry(diagnostic_matrix, "downstream_where_bad")
    replay_blocker = replay.blocker
    assert type(replay_blocker) is ProjectNoJoinScalarExpression
    assert replay.replay_root is not None
    assert replay.replay_root.blocker is replay_blocker
    replay_error = replay_blocker.diagnostics[0]
    assert replay_error.code == "PIE-S2103"
    assert any(
        diagnostic is replay_error
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert (
        sum(
            diagnostic is replay_error
            for diagnostic in completed_semantics._entry_error_diagnostics(replay)
        )
        == 1
    )


def test_qualify_error_is_retained_by_identity_without_fallback(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "qualify_bad")
    blocker = entry.blocker
    assert type(blocker) is joined_qualify.ProjectNonConcreteJoinedQualify
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2332"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("qualify_bad")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )


def test_order_terminal_projects_exact_blocker_error_before_fallback(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "order_precise")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationOrdering
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2321"
    assert any(
        diagnostic is retained for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert not any(
        diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("order_precise")
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )


def test_superseded_base_diagnostic_is_not_a_current_terminal_error(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "order_bad")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationOrdering
    assert (
        type(blocker.blocker)
        is scalar_namespaces.ProjectNonConcreteJoinedNamespaceExpression
    )
    current = entry.joined_qualify
    assert type(current) is joined_qualify.ProjectConcreteJoinedQualify
    assert type(current.window_stage) is joined_windows.ProjectConcreteJoinedWindowStage
    superseded = entry.base_entry.fragment.semantic_facts.window_outputs[0].diagnostics[
        0
    ]
    assert superseded.code == "PIE-S2103"
    assert not any(
        diagnostic is superseded
        for diagnostic in diagnostic_matrix.completed.diagnostics
    )
    assert (
        sum(
            diagnostic.code == "PIE-S2333" and diagnostic.message.endswith("order_bad")
            for diagnostic in diagnostic_matrix.completed.diagnostics
        )
        == 1
    )


def test_limit_error_identity_dedup_and_equal_value_multiplicity_are_exact(
    diagnostic_matrix: _Built,
) -> None:
    entry = _terminal_entry(diagnostic_matrix, "limit_bad")
    blocker = entry.blocker
    assert type(blocker) is ProjectNonConcreteRelationLimit
    retained = blocker.diagnostics[0]
    assert retained.code == "PIE-S2307"
    assert entry.diagnostics[0] is retained
    raw = completed_semantics._diagnostics_from_carrier(entry)
    assert sum(diagnostic is retained for diagnostic in raw) == 2
    projected = completed_semantics._entry_error_diagnostics(entry)
    assert tuple(diagnostic for diagnostic in projected if diagnostic is retained) == (
        retained,
    )

    equal_but_distinct = replace(retained)
    assert equal_but_distinct == retained and equal_but_distinct is not retained
    foreign_blocker = replace(blocker, diagnostics=(equal_but_distinct,))
    grafted = replace(entry, blocker=foreign_blocker)
    distinct_projection = completed_semantics._entry_error_diagnostics(grafted)
    assert distinct_projection[:2] == (retained, equal_but_distinct)
    assert distinct_projection[0] is retained
    assert distinct_projection[1] is equal_but_distinct


def test_explicit_project_cli_uses_completed_success_with_unchanged_text_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "cli-success", POSITIVE_SOURCE)
    semantic_builder = cli.build_empty_project_semantic_result
    completed_builder = cli.build_project_completed_semantic_result
    semantic_results: list[ProjectSemanticResult] = []
    completed_results: list[completed_semantics.ProjectCompletedSemanticResult] = []

    def build_semantic(parse_result: ProjectParseCheckResult) -> ProjectSemanticResult:
        result = semantic_builder(parse_result)
        semantic_results.append(result)
        return result

    def build_completed(
        semantic_result: ProjectSemanticResult,
    ) -> completed_semantics.ProjectCompletedSemanticResult:
        result = completed_builder(semantic_result)
        completed_results.append(result)
        return result

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", build_semantic)
    monkeypatch.setattr(cli, "build_project_completed_semantic_result", build_completed)

    assert cli.main(["check", "--project", str(root)]) == 0
    text = capsys.readouterr()
    assert text.out == "Project check OK: .\nFiles checked: 1\n"
    assert text.err == ""
    assert not semantic_results[-1].ok
    assert completed_results[-1].ok

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["schema_version"] == 2
    assert document["ok"] is completed_results[-1].ok is True
    assert document["diagnostics"] == []
    serialized = json.dumps(document)
    for private in (
        "completion",
        "effective_outputs",
        "field identities",
        "ProjectIR",
        "terminal reason",
    ):
        assert private not in serialized


def test_explicit_project_cli_renders_completed_failure_in_text_and_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "cli-failure", FALLBACK_FAILURE_SOURCE)

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err.count("PIE-S2333") == 2
    assert "Project relation semantic completion is unavailable: bad" in text.err
    assert "Project relation semantic completion is unavailable: downstream" in text.err
    assert "Project check OK" not in text.out

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["ok"] is False
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert tuple(item["code"] for item in diagnostics) == (
        "PIE-S2301",
        "PIE-S2333",
        "PIE-S2333",
    )
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }


def test_parse_failure_runs_neither_semantic_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path / "parse-failure", "shape Broken\n    id: Int\n")

    def unexpected(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("semantic builders must not run after parse failure")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected)
    monkeypatch.setattr(cli, "build_project_completed_semantic_result", unexpected)
    assert cli.main(["check", "--project", str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1000" in captured.err


def test_legacy_project_and_single_file_checks_never_enter_completed_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    legacy = _project(
        tmp_path / "legacy",
        'shape Row:\n    id: Int not null\nsource rows: Row is postgres.table("rows")\n',
        schema_version=1,
    )
    single = tmp_path / "single.pietto"
    single.write_text("shape Row:\n    id: Int not null\n", encoding="utf-8")

    def unexpected(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("non-explicit checks must not enter completed semantics")

    monkeypatch.setattr(cli, "build_project_completed_semantic_result", unexpected)
    assert cli.main(["check", "--project", str(legacy)]) == 0
    legacy_text = capsys.readouterr()
    assert legacy_text.out == "Project check OK: .\nFiles checked: 1\n"
    assert legacy_text.err == ""

    assert cli.main(["check", str(single)]) == 0
    single_text = capsys.readouterr()
    assert single_text.out == f"OK: {single}\n"
    assert single_text.err == ""

    assert cli.main(["check", str(single), "--format", "json"]) == 0
    single_json = _read_json(capsys)
    assert single_json["schema_version"] == 1
    assert single_json["command"] == "check"
    assert "mode" not in single_json


def test_json_v2_and_public_private_boundaries_remain_exact(positive: _Built) -> None:
    direct = project_check_result_to_json_dict(
        positive.parse_result,
        semantic_diagnostics=positive.completed.diagnostics,
    )
    assert tuple(direct) == PROJECT_JSON_KEYS
    assert direct["schema_version"] == 2
    assert direct["ok"] is True

    production = PRODUCTION.read_text(encoding="utf-8")
    cli_source = CLI.read_text(encoding="utf-8")
    json_source = JSON_V2.read_text(encoding="utf-8")
    assert completed_semantics.__all__ == ()
    assert "ProjectConcreteCompletedSemanticResult" not in (
        REPO_ROOT / "src/pietto/__init__.py"
    ).read_text(encoding="utf-8")
    assert "build_project_completed_semantic_result" not in json_source
    assert "ProjectCompletedSemanticResult" not in json_source
    assert "_run_check" in cli_source
    single_file_body = cli_source.split("def _run_check(", 1)[1].split(
        "def _run_emit_sql(", 1
    )[0]
    assert "build_project_completed_semantic_result" not in single_file_body
    project_explain_body = cli_source.split("def _run_project_explain(", 1)[1]
    assert "build_project_completed_semantic_result" not in project_explain_body
    assert "build_project_ir_project_plan(" in production
    projection = production.split("def _diagnostics_from_carrier(", 1)[1].split(
        "def _fallback_diagnostic(", 1
    )[0]
    for forbidden in (
        "vars(",
        "__dict__",
        "fields(",
        "is_dataclass(",
        "serialize",
        "analyze_",
        "build_",
        "sorted(",
        ".sort(",
    ):
        assert forbidden not in projection
    for forbidden in (
        "ProjectIRUnary",
        "unary_tail",
        "emit_postgres_sql",
        "emit_mysql_sql",
        "pyarrow",
        "executor",
        "optimizer",
        "serialize_project_ir",
    ):
        assert forbidden not in production
    exposed_fields = {item.name for item in fields(positive.completed)}
    assert exposed_fields == {
        "roots",
        "semantic_result",
        "verification",
        "completion",
        "effective_outputs",
        "diagnostics",
        "ok",
    }
    assert not exposed_fields.intersection(
        {"plan", "node", "use", "slot", "coordinate", "canonical_bytes"}
    )


def test_spec_records_exact_contract_and_frozen_closure() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "ProjectConcreteCompletedSemanticResult",
        "ProjectNonConcreteCompletedSemanticResult",
        "ProjectPhase62VerificationResult",
        "ProjectEffectiveOutputCompletion",
        "PIE-S2333",
        "Project JSON v2",
        "EXPLICIT_MODULES",
        "LEGACY_FLAT",
        "PACKAGE_ROOT",
        "A3/M7/D0",
        "A3/M14/D0",
        "7/10",
        "mechanical expansion",
        "closed typed visitor",
        "test_phase55_slice2_explicit_package_activation_compatibility_and_immutable_package_carrier.py",
        "174 -> 175",
        "417 -> 418",
        "Slice 14",
    ):
        assert phrase in text


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))
