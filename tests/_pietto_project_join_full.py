"""Authored full-join source fixtures."""

from _pietto_project_join import _source


def _unique_source(kind: str, predicate: str | None, *, via: str = "") -> str:
    return _source(predicate, kind=kind, via=via).replace(
        "    allow_any: Bool nullable\n",
        "    allow_any: Bool nullable\n    unique row_key on id\n",
    )


def _two_current_globals_full(result_select: str) -> str:
    source = _source("lhs.id == r.id").split("query result:", 1)[0]
    return (
        source
        + f"""query left_global:
    from lhs
    inner join rhs as left_input:
        from lhs
        on true
    select:
        total = count()
query right_global:
    from rhs
    inner join lhs as right_input:
        from rhs
        on true
    select:
        total = count()
query result:
    from left_global
    full join right_global as r:
        from left_global
        on false
    select:
{result_select}"""
    )
