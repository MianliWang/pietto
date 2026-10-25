"""Authored project-join source and completed-semantic fixtures."""

from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)


BASE = """shape Row:
    id: Int
    key: Int | None
    allow_any: Bool | None
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
relationship Link(l: Row, r: Row):
    l.id == r.id
"""


def _source(predicate: str | None, *, kind: str = "inner") -> str:
    on = "" if predicate is None else f" on {predicate}"
    return (
        BASE
        + f"""query result:
    from lhs
    let r = rhs
    {kind} join r{on}
    select:
        id = lhs.id
"""
    )


def _prefix_existence_source(predicate: str, kind: str) -> str:
    """`_source` with a JOIN-prefix `[not] any` of `r`, a hidden SEMI/ANTI JOIN
    (a `semi`/`anti` JOIN before S6), then a later inner JOIN of `rhs`."""
    negation = "not " if kind == "anti" else ""
    return (
        BASE
        + f"""query result:
    from lhs
    let r = rhs
    where {negation}any({predicate} for r in r)
    let n = rhs
    inner join n on lhs.id == n.id
    select:
        id = lhs.id
"""
    )


def _parsed(root: Path, source: str) -> ProjectParseCheckResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(source)
    return check_project_parse_only(root)


def _completed(root: Path, source: str) -> ProjectConcreteCompletedSemanticResult:
    parsed = _parsed(root, source)
    assert parsed.ok, parsed.diagnostics
    result = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    return result
