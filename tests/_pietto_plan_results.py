"""Shared result-boundary Project SQL-plan source fixture."""


def _source(
    body: str = "    select distinct:\n        value\n",
    *,
    type_name="Int",
    kind="query",
    family="postgres",
) -> str:
    return (
        f"""shape Row:
    value: {type_name} | None
    hidden: Float | None
source rows: Row = {family}.table("rows")
{kind} result:
    from rows
"""
        + body
    )
