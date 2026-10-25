"""Shared aggregate Project SQL-plan source fixtures."""


def _ordinary(body: str, *, family="postgres", kind="query"):
    return f"""shape Row:
    id: Int
    value: Int | None
source rows: Row = {family}.table("rows")
{kind} result:
    from rows
{body}"""


def _group_source(*, visible=(), keys=("lhs.id",), family="postgres", kind="query"):
    selected = "".join(
        f"        {name} = {expression}\n" for name, expression in visible
    )
    grouped = "".join(f"        {key}\n" for key in keys)
    return f"""shape Row:
    id: Int
    key: Int | None
source lhs: Row = {family}.table("lhs")
source rhs: Row = {family}.table("rhs")
{kind} result:
    from lhs
    let r = rhs
    left join r on lhs.id == r.id
    group by:
{grouped}    select:
{selected}        total = count()
"""


def _joined_aggregates(family="postgres", kind="query"):
    source = _group_source(family=family, kind=kind)
    source = source.replace(
        "    key: Int | None\n",
        "    key: Int | None\n    label: Text | None\n    row_key = unique(id)\n",
    )
    source = source.replace(
        "    group by:\n        lhs.id\n",
        """    let group_value = lhs.id
    let amount = r.key + 1
    where lhs.id > 0
    group by:
        group_value
""",
    )
    return source.replace(
        "        total = count()\n",
        """        row_count = count()
        field_count = count(r.id)
        distinct_labels = count_distinct(r.label)
        total = sum(amount)
        average = avg(amount)
        minimum = min(r.key)
        maximum = max(r.key)
        repeated_total = sum(amount)
    having:
        total > 0 and total > 1 and total < 10
""",
    )
