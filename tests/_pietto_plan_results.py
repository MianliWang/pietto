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
    value: {type_name} nullable
    hidden: Float nullable
source rows: Row is {family}.table("rows")
{kind} result:
    from rows
"""
        + body
    )
