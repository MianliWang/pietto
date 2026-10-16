from __future__ import annotations

from dataclasses import fields, replace
import json
from pathlib import Path
from typing import cast

import pytest

from _pietto_project_completion import POSITIVE_SOURCE

import pietto.cli as cli
from pietto._project import project_joined_aggregation as joined_aggregation
from pietto._project import project_joined_qualify as joined_qualify
from pietto._project import project_joined_row_filter as joined_row_filter
from pietto._project import project_joined_windows as joined_windows
from pietto._project import project_scalar_namespaces as scalar_namespaces
from pietto._project import project_completed_semantics as completed_semantics
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaStatus,
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
    ProjectNoJoinScalarExpression,
    ProjectNonConcreteRelationLimit,
    ProjectNonConcreteRelationOrdering,
)


from _pietto_project_completed_semantics import (
    REPO_ROOT,
    PRODUCTION,
    CLI,
    JSON_V2,
    SPEC,
    PROJECT_JSON_KEYS,
    PRECISE_FAILURE_SOURCE,
    FALLBACK_FAILURE_SOURCE,
    SOURCE_FAILURE_SOURCE,
    NESTED_WINDOW_FAILURE_SOURCE,
    _Built,
    _project,
    _build,
    positive as positive,
    foreign as foreign,
    diagnostic_matrix as diagnostic_matrix,
    _entry,
    _terminal_entry,
)


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


def test_module_import_cycles_are_a_typed_terminal_in_builder_check_and_emit_sql(
    tmp_path: Path,
    positive: _Built,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def module(name: str, target: str, target_name: str) -> str:
        return (
            f"shape {name}:\n    id: Int\nexport:\n    shape {name}\n"
            f'import "{target}":\n    shape {target_name}\n'
        )

    def public(items: object) -> tuple[tuple[object, ...], ...]:
        facts: list[tuple[object, ...]] = []
        for item in cast(list[dict[str, object]], items):
            location = cast(dict[str, object], item["location"])
            facts.append(
                (
                    item["code"],
                    item["message"],
                    location["path"],
                    location["line"],
                    location["column"],
                )
            )
        return tuple(facts)

    root = tmp_path / "import-cycles"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for path, source in {
        "a.pietto": module("A", "b.pietto", "B"),
        "b.pietto": module("B", "a.pietto", "A"),
        "c.pietto": module("C", "d.pietto", "D"),
        "d.pietto": module("D", "c.pietto", "C"),
        "e.pietto": (
            "shape E:\n    id: Int not null\n"
            'source rows: E is postgres.table("e")\n'
            "query bad:\n    from rows\n    select:\n        nope\n"
        ),
        # A source connector outside the cycles is still checked.
        "f.pietto": 'shape F:\n    id: Int not null\nsource bad: F is mysql.table("")\n',
        # Header parameter, WHERE typing and scalar read checks are made while
        # completing relations, so a cycle elsewhere holds them back.
        "g.pietto": (
            "shape G:\n    id: Int not null\n    k: Int\n"
            'source rows: G is postgres.table("g")\n'
            "query p(id: Int not null, k: Int not null):\n    from rows\n"
            "    where id > k\n    select:\n        x = rows.id\n"
            "query q:\n    from rows\n    where exists p\n    select:\n        id\n"
            'query n:\n    from rows\n    where 1 == "a"\n    select:\n'
            "        id\n        v = scalar rows.nope\n"
        ),
        "contract.json": "{}",
    }.items():
        (root / path).write_text(source, encoding="utf-8")
    expected = (
        (
            "PIE-S2703",
            "Module import cycle detected: a.pietto -> b.pietto -> a.pietto",
            "b.pietto",
            5,
            8,
        ),
        (
            "PIE-S2703",
            "Module import cycle detected: c.pietto -> d.pietto -> c.pietto",
            "d.pietto",
            5,
            8,
        ),
        ("PIE-S2102", "Unknown field: nope", "e.pietto", 7, 9),
        (
            "PIE-S2306",
            "Invalid source connector arguments for mysql.table",
            "f.pietto",
            3,
            18,
        ),
    )

    semantic = build_empty_project_semantic_result(check_project_parse_only(root))
    result = completed_semantics.build_project_completed_semantic_result(semantic)
    assert type(result) is completed_semantics.ProjectNonConcreteCompletedSemanticResult
    assert (
        result.reason
        is completed_semantics.ProjectCompletedSemanticNonConcreteReason.MODULE_IMPORT_CYCLE
    )
    assert result.diagnostics[: len(semantic.diagnostics)] == semantic.diagnostics
    assert result.verification is result.completion is result.effective_outputs is None
    assert not result.ok
    retained = tuple(
        (d.code, d.message, d.location.path, d.location.line, d.location.column)
        for d in result.diagnostics
    )
    assert retained == expected
    for semantic_root, reason in (
        (positive.semantic_result, result.reason),
        (
            semantic,
            completed_semantics.ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE,
        ),
    ):
        with pytest.raises(ValueError, match="exact reason"):
            completed_semantics.ProjectNonConcreteCompletedSemanticResult(
                semantic_result=semantic_root,
                reason=reason,
            )

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == "".join(
        f"{path}:{line}:{column} {code} error: {message}\n"
        for code, message, path, line, column in expected
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert tuple(document) == PROJECT_JSON_KEYS
    assert document["ok"] is False
    assert public(document["diagnostics"]) == expected

    emit = ["emit-sql", "--project", str(root), "--module", "e.pietto"]
    emit += ["--kind", "query", "--name", "bad", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json", "--format", "json"]
    assert cli.main(emit) == 1
    emitted = _read_json(capsys)
    assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
    assert public(emitted["diagnostics"]) == expected

    # With every cycle fixed, the completed chain reports its own diagnostics
    # after the semantic and source connector ones.
    for path, name in (("b.pietto", "B"), ("d.pietto", "D")):
        (root / path).write_text(
            f"shape {name}:\n    id: Int\nexport:\n    shape {name}\n",
            encoding="utf-8",
        )
    collision = (
        "PIE-S2354",
        "Query parameter name is also a field, let, relation, output or window name.",
        "g.pietto",
        5,
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    fixed = public(_read_json(capsys)["diagnostics"])
    parameters = (
        (*collision, 9),
        (*collision, 27),
        (
            "PIE-S2356",
            "A query with parameters cannot be the input of another relation.",
            "g.pietto",
            12,
            11,
        ),
    )
    assert fixed[-3:] == parameters
    assert tuple(item for item in fixed if item[2] == "g.pietto") == (
        ("PIE-S2102", "Unknown field: rows.nope", "g.pietto", 20, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            "g.pietto",
            17,
            11,
        ),
        *parameters,
    )
    assert expected[3] in fixed


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


def test_final_diagnostics_report_an_equal_restated_error_once(
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
    # The relation facts restate the semantic error for the same occurrence;
    # the entry keeps its own object, the public result reports the value once.
    assert helper_error is not built.semantic_result.diagnostics[0]
    assert helper_error == built.semantic_result.diagnostics[0]
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == ("PIE-S2102",)
    assert result.diagnostics[0] is built.semantic_result.diagnostics[0]
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


def test_explicit_project_cli_shares_the_comparison_family_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "cli-comparison",
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n"
        '    where id == "x"\n'
        "    select:\n"
        "        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == (
        "main.pietto:6:11 PIE-S2105 error: Invalid operands for operator ==: "
        "expected comparable operands\n"
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            '    where name like "a!"\n    select:\n        id\n',
            "main.pietto:7:11 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            '    let:\n        p = "a!"\n    where name like p\n'
            "    select:\n        id\n",
            "main.pietto:9:11 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            '    let:\n        p = "a!"\n    select:\n        id\n'
            "        m = name like p\n",
            "main.pietto:11:13 PIE-S2105 error: Invalid operands for operator like: "
            "expected a pattern that does not end in the escape character ! "
            "(write !! for a literal !)\n",
        ),
        (
            "    select:\n        id\n        c = cast(null as Float)\n",
            "main.pietto:9:13 PIE-S2105 error: Invalid cast: cast(null as Float) is "
            "not supported; expected cast(Int as Float), the only supported cast\n",
        ),
    ],
    ids=("like-literal", "like-let-where", "like-let-select", "cast-null"),
)
def test_explicit_project_check_refuses_like_escape_and_null_cast(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    root = _project(
        tmp_path / "q1",
        "shape Row:\n"
        "    id: Int not null\n"
        "    name: Text not null\n"
        'source rows: Row is postgres.table("app.rows")\n'
        "query result:\n"
        "    from rows\n" + body,
    )

    # Before: like "a!" through a let and cast(null) passed or gave PIE-S2333.
    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == expected


def test_project_and_single_file_checks_agree_on_alias_comparison_operands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "alias-comparison",
        "type Age = Int not null\n"
        "type Years = Age not null\n"
        "type Tag = Text not null\n"
        "shape Row:\n"
        "    id: Int not null\n"
        "    age: Age not null\n"
        "    years: Years not null\n"
        "    tag: Tag not null\n"
        'source rows: Row is postgres.table("app.rows")\n'
        "query by_where:\n"
        "    from rows\n"
        '    where years == "x"\n'
        "    select:\n"
        "        id\n"
        "query by_select:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        '        flag = age == "x"\n'
        "query by_let:\n"
        "    from rows\n"
        "    let:\n"
        "        bad = tag > 5\n"
        "    where bad\n"
        "    select:\n"
        "        id\n"
        "query same_family:\n"
        "    from rows\n"
        '    where years >= age and tag == "x"\n'
        "    select:\n"
        "        id\n",
    )

    def facts(document: dict[str, object]) -> list[tuple[object, ...]]:
        diagnostics = cast(list[dict[str, object]], document["diagnostics"])
        return [
            (
                item["code"],
                item["severity"],
                item["message"],
                cast(dict[str, object], item["location"])["line"],
                cast(dict[str, object], item["location"])["column"],
            )
            for item in diagnostics
        ]

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    project = facts(_read_json(capsys))
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    single_file = facts(_read_json(capsys))
    message = "Invalid operands for operator {}: expected comparable operands"
    expected = [
        ("PIE-S2105", "error", message.format("=="), 12, 11),
        ("PIE-S2105", "error", message.format("=="), 19, 16),
        ("PIE-S2105", "error", message.format(">"), 23, 15),
    ]
    assert project == expected
    assert single_file == expected


_NO_GROUP = "`satisfying` requires GROUP BY"
_COUNT_IN_SATISFYING = (
    "Aggregate count() is not allowed in satisfying clause; "
    "use it only as a direct aliased select projection"
)


def _public_facts(items: object) -> list[tuple[object, ...]]:
    return [
        (
            item["code"],
            item["severity"],
            item["message"],
            cast(dict[str, object], item["location"])["line"],
            cast(dict[str, object], item["location"])["column"],
        )
        for item in cast(list[dict[str, object]], items)
    ]


def test_project_and_single_file_checks_refuse_satisfying_without_group_by(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "no-group-satisfying",
        "shape Row:\n"
        "    id: Int not null\n"
        "    key: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "query plain:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query aggregate_call:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        count() > 0\n"
        "query global_total:\n"
        "    from rows\n"
        "    select:\n"
        "        n = count()\n"
        "    satisfying:\n"
        "        n > 0\n"
        "query windowed:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "        r = row_number() window:\n"
        "            order by:\n"
        "                rows.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query with_let:\n"
        "    from rows\n"
        "    let:\n"
        "        b = id + 1\n"
        "    select:\n"
        "        c = b\n"
        "    satisfying:\n"
        "        c > 0\n"
        "query qualified:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "    qualify:\n"
        "        row_number() window:\n"
        "            order by:\n"
        "                a\n"
        "        <= 3\n"
        "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        rows.key\n"
        "    select:\n"
        "        k = rows.key\n"
        "        n = count()\n"
        "    satisfying:\n"
        "        n > 0\n",
    )
    (root / "contract.json").write_text("{}", encoding="utf-8")
    expected = [
        ("PIE-S2323", "error", _NO_GROUP, 9, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 16, 9),
        ("PIE-S2323", "error", _NO_GROUP, 21, 5),
        ("PIE-S2323", "error", _NO_GROUP, 30, 5),
        ("PIE-S2323", "error", _NO_GROUP, 38, 5),
        ("PIE-S2323", "error", _NO_GROUP, 44, 5),
    ]

    assert cli.main(["check", "--project", str(root)]) == 1
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == "".join(
        f"main.pietto:{line}:{column} {code} error: {message}\n"
        for code, _, message, line, column in expected
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    assert cli.main(["check", str(root / "main.pietto"), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected

    emit = ["emit-sql", "--project", str(root), "--module", "main.pietto"]
    emit += ["--kind", "query", "--name", "plain", "--dialect", "postgres"]
    emit += ["--emission-contract", "contract.json", "--format", "json"]
    assert cli.main(emit) == 1
    emitted = _read_json(capsys)
    assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
    assert _public_facts(emitted["diagnostics"]) == expected

    # Each refusal is the relation's own semantic fact, retained once.
    built = _build(tmp_path / "builder", (root / "main.pietto").read_text())
    plain = next(
        entry
        for entry in built.completed.effective_outputs.entries
        if entry.owner.identity.declared_name == "plain"
    )
    assert type(plain) is ProjectEffectiveOutputTerminal
    facts = plain.fragment.semantic_facts
    assert facts.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    (refusal,) = facts.helper_diagnostics
    assert refusal is built.completed.diagnostics[0]
    assert type(_entry(built, "grouped")) is ProjectExistingEffectiveOutput


def test_project_refuses_satisfying_without_group_by_in_every_no_join_body(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(
        tmp_path / "no-group-satisfying-bodies",
        "shape Row:\n"
        "    id: Int not null\n"
        "    key: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        'source others: Row is postgres.table("others")\n'
        "query both:\n"
        "    union all:\n"
        "        from rows\n"
        "        from others\n"
        "query set_reader:\n"
        "    from both\n"
        "    select:\n"
        "        a = both.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query seed:\n"
        "    values(id: Int not null):\n"
        "        1\n"
        "query values_reader:\n"
        "    from seed\n"
        "    select:\n"
        "        a = seed.id\n"
        "    satisfying:\n"
        "        count() > 0\n"
        "query joined:\n"
        "    from rows\n"
        "    inner join others as o:\n"
        "        from rows\n"
        "        on rows.id == o.id\n"
        "    select:\n"
        "        a = rows.id\n"
        "query joined_reader:\n"
        "    from joined\n"
        "    select:\n"
        "        a = joined.a\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query let_body:\n"
        "    let w1:\n"
        "        from rows\n"
        "        select:\n"
        "            a = rows.id\n"
        "        satisfying:\n"
        "            a > 0\n"
        "    from w1\n"
        "    select:\n"
        "        a\n"
        "query let_reader:\n"
        "    let w2:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "    from w2\n"
        "    select:\n"
        "        a = w2.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query distinct_rows:\n"
        "    from rows\n"
        "    select distinct:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query ordered:\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        a > 0\n"
        "    order by:\n"
        "        a asc\n"
        "    limit 3\n"
        "query downstream:\n"
        "    from ordered\n"
        "    select:\n"
        "        a\n",
    )
    unavailable = "Project relation semantic completion is unavailable: {}"

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = _read_json(capsys)
    assert document["ok"] is False
    assert _public_facts(document["diagnostics"]) == [
        ("PIE-S2323", "error", _NO_GROUP, 14, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 24, 9),
        ("PIE-S2323", "error", _NO_GROUP, 36, 5),
        ("PIE-S2323", "error", _NO_GROUP, 43, 9),
        ("PIE-S2333", "error", unavailable.format("let_body"), 38, 1),
        ("PIE-S2323", "error", _NO_GROUP, 56, 5),
        ("PIE-S2323", "error", _NO_GROUP, 62, 5),
        ("PIE-S2323", "error", _NO_GROUP, 68, 5),
        ("PIE-S2333", "error", unavailable.format("downstream"), 73, 1),
    ]


def test_satisfying_without_group_by_beside_parameters_and_table_functions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Header parameters and generate_series inputs reach the same refusal."""
    root = _project(
        tmp_path / "no-group-satisfying-phase70",
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query param_plain(low: Int not null):\n"
        "    from rows\n"
        "    where id > low\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        a > low\n"
        "query param_count(low: Int not null):\n"
        "    from rows\n"
        "    select:\n"
        "        a = rows.id\n"
        "    satisfying:\n"
        "        count() > low\n"
        "query param_let(low: Int not null):\n"
        "    let w:\n"
        "        from rows\n"
        "        where id > low\n"
        "        select:\n"
        "            a = rows.id\n"
        "        satisfying:\n"
        "            a > low\n"
        "    from w\n"
        "    select:\n"
        "        a\n"
        "query series_plain:\n"
        "    from generate_series(1, 5, 1) as n\n"
        "    select:\n"
        "        a = n\n"
        "    satisfying:\n"
        "        a > 0\n"
        "query series_count:\n"
        "    from generate_series(1, 5, 1) as n\n"
        "    select:\n"
        "        a = n\n"
        "    satisfying:\n"
        "        count() > 0\n"
        "query series_let:\n"
        "    let s:\n"
        "        from generate_series(1, 5, 1) as n\n"
        "        select:\n"
        "            a = n\n"
        "        satisfying:\n"
        "            a > 0\n"
        "    from s\n"
        "    select:\n"
        "        a\n",
    )
    (root / "contract.json").write_text("{}", encoding="utf-8")
    unavailable = "Project relation semantic completion is unavailable: param_let"
    expected = [
        ("PIE-S2323", "error", _NO_GROUP, 9, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 16, 9),
        ("PIE-S2323", "error", _NO_GROUP, 23, 9),
        ("PIE-S2333", "error", unavailable, 17, 1),
        ("PIE-S2323", "error", _NO_GROUP, 32, 5),
        ("PIE-S2308", "error", _COUNT_IN_SATISFYING, 39, 9),
        ("PIE-S2323", "error", _NO_GROUP, 45, 9),
    ]
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    assert _public_facts(_read_json(capsys)["diagnostics"]) == expected
    for name in ("param_plain", "series_plain"):
        emit = ["emit-sql", "--project", str(root), "--module", "main.pietto"]
        emit += ["--kind", "query", "--name", name, "--dialect", "postgres"]
        emit += ["--emission-contract", "contract.json", "--format", "json"]
        assert cli.main(emit) == 1
        emitted = _read_json(capsys)
        assert (emitted["status"], emitted["artifact"]) == ("BLOCKED", None)
        assert _public_facts(emitted["diagnostics"]) == expected


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
    assert exposed_fields >= {
        "roots",
        "semantic_result",
        "verification",
        "completion",
        "effective_outputs",
        "diagnostics",
        "ok",
    }
    assert positive.completed.single_match_requests == ()
    assert positive.completed.single_matches.obligations == ()
    assert positive.completed.single_matches.diagnostics == ()
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
