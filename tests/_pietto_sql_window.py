"""Small authored SQL-window source fixtures."""


def select_body(call, *, frame="", order="id", partition=None, alias="w"):
    lines = [
        "table result:",
        "    from rows",
        "    select:",
        "        id",
        f"        {alias} = {call} window:",
    ]
    if partition is not None:
        lines += ["            partition by:", f"                {partition}"]
    lines += ["            order by:"]
    lines += [f"                {key}" for key in order.split(",")]
    if frame:
        lines += [f"            {frame}"]
    return "\n".join(lines) + "\n"
