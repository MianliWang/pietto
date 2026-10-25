"""Shared row-scalar Project SQL-plan fixtures."""


def _source(body: str, *, kind: str = "query", family: str = "postgres") -> str:
    return f"""shape Row:
    id: Int
    key: Int | None
    flag: Bool | None
source rows: Row = {family}.table("rows")
{kind} result:
    from rows
{body}"""


ROW_BODY = """    let a = rows.id + 1
    let b = a * 2
    where b > 0 and flag
    select:
        first = b + a
        again = b
        third = b
        literal = 5
"""
