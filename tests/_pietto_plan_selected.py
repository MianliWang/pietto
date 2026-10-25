"""Selected SQL-plan source, root and graft fixtures."""

from copy import copy
from pathlib import Path

from _pietto_project_join import _completed
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)


def _source(kind: str = "query", family: str = "postgres") -> str:
    return f"""shape Row:
    id: Int
    name: Text | None
source rows: Row = {family}.table("public.users")
{kind} result:
    from rows
    select:
        label = name
        id
"""


def _roots(path: Path, source: str):
    completed = _completed(path, source)
    snapshot = build_project_query_block_ir(completed)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    bundle = build_project_query_block_ir_analysis_bundle(verification)
    owners = tuple(o for o in snapshot.owners if o.definition.name == "result")
    assert len(owners) == 1
    return completed, bundle, owners[0]


def _graft[T](value: T, /, **changes) -> T:
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result
