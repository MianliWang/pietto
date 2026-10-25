"""Small authored SQL-window source fixtures."""


def select_body(call, *, frame="", order="id", partition=None, alias="w"):
    lines = [
        "table result:",
        "    from rows",
        "    select:",
        "        id",
        f"        {alias} = {call} window(",
    ]
    if partition is not None:
        lines += [f"            partition by {partition}"]
    lines += [f"            order by {order}"]
    if frame:
        lines += [f"            {frame}"]
    lines += ["        )"]
    return "\n".join(lines) + "\n"
