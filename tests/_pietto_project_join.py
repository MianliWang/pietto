"""Authored project-join source and completed-semantic fixtures."""

from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)


BASE = """shape Row:
    id: Int not null
    key: Int nullable
    allow_any: Bool nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
"""


def _source(predicate: str | None, *, kind: str = "inner", via: str = "") -> str:
    on = "" if predicate is None else f"        on {predicate}\n"
    return (
        BASE
        + f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
{via}{on}    select:
        id = lhs.id
"""
    )


def _completed(root: Path, source: str) -> ProjectConcreteCompletedSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    parsed = check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    result = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    return result
