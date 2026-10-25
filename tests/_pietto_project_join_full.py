"""Authored full-join source fixtures."""

from _pietto_project_join import _source


def _unique_source(kind: str, predicate: str | None) -> str:
    return _source(predicate, kind=kind).replace(
        "    allow_any: Bool | None\n",
        "    allow_any: Bool | None\n    row_key = unique(id)\n",
    )


def _two_current_globals_full(result_select: str) -> str:
    source = _source("lhs.id == r.id").split("query result:", 1)[0]
    return (
        source
        + f"""query left_global:
    from lhs
    let left_input = rhs
    inner join left_input on True
    select:
        total = count()
query right_global:
    from rhs
    let right_input = lhs
    inner join right_input on True
    select:
        total = count()
query result:
    from left_global
    let r = right_global
    full join r on False
    select:
{result_select}"""
    )
