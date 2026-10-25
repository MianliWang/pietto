from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from _pietto_project_completion import POSITIVE_SOURCE

from pietto._project import project_completed_semantics as completed_semantics
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completion import (
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletionTerminal,
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

PRECISE_FAILURE_SOURCE = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
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

SOURCE_FAILURE_SOURCE = """source rows: MissingShape = postgres.table("rows")
"""

NESTED_WINDOW_FAILURE_SOURCE = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    select:
        mystery = mystery_window() window(order by id)
"""

DIAGNOSTIC_MATRIX_SOURCE = (
    POSITIVE_SOURCE
    + """query where_bad:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
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
    let event = events
    inner join event on account_events(accounts, event)
    select:
        ranked = row_number() window(order by event.id)
    qualify:
        missing > 0
query order_bad:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        id = row_number() window(order by event.id)
    order by:
        id
query order_precise:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
    order by:
        metric
query limit_bad:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
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
