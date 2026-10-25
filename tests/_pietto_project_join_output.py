"""Completed project-join output fixtures."""

from _pietto_project_join import _source
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput


def _output(
    completed: ProjectConcreteCompletedSemanticResult, name: str
) -> ProjectCompletedEffectiveOutput:
    entries = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == name
    )
    assert len(entries) == 1 and isinstance(entries[0], ProjectCompletedEffectiveOutput)
    return entries[0]


def _tail_source(tail: str) -> tuple[str, str]:
    source = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    field_name = "id"
    if tail == "row":
        source = source.replace(
            "    select:\n",
            "    let adjusted = lhs.id + 1\n    where adjusted > 0\n    select:\n",
        )
        source += "        adjusted_value = adjusted\n    order by:\n        lhs.id desc\n    limit 2\n"
        field_name = "adjusted_value"
    elif tail == "grouped":
        source = source.replace(
            "    select:\n", "    group by:\n        lhs.id\n    select:\n"
        )
        source += "        total = count()\n    having:\n        total > 0\n"
        field_name = "total"
    elif tail == "global":
        source = source.replace("id = lhs.id", "total = count()")
        field_name = "total"
    elif tail == "selected_window":
        source += "        rn = row_number() window(order by lhs.id)\n    qualify:\n        rn <= 2\n"
        field_name = "rn"
    elif tail == "hidden_window":
        source += "    qualify:\n        row_number() window(order by lhs.id) <= 2\n"
    else:
        raise AssertionError(tail)
    return source, field_name
