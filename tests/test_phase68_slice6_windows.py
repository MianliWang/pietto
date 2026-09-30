"""Joint choices, original peers/frames and producer-use identity controls."""

from dataclasses import replace

import pytest

from _pietto_phase68_slice6_cases import original
from test_phase68_slice6_refinement import capabilities, rewrite_cte
from pietto._project.project_refinement import TieRefinement, prepare_refinement
from pietto._project.project_refinement_rendering import (
    Expr,
    Select,
    Order,
    ref,
    render,
)
from pietto._project.project_refinement_verification import (
    verify_native,
    verify_refinement,
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "case,variant", (("R2_mixed", "joint"), ("R2_repeated", "tied_limit"))
)
def test_joint_and_repeated_sources_have_complete_independent_rules(
    tmp_path, target, case, variant
):
    artifact = original(tmp_path, target, case, variant)
    query = prepare_refinement(
        artifact, capabilities(artifact, width=2), policy=TieRefinement()
    )
    native = render(query.statement, artifact)
    verify_native(native, query)
    windows = [
        c
        for u in query.output.units
        for c in u.columns
        if type(c).__name__ == "WindowColumn"
    ]
    if case == "R2_mixed":
        assert len(windows) == 9
        assert sum(c.selected is False for c in windows) == 1
    else:
        assert len(windows) == 2
        assert query.units[-1].dependencies[0] == query.units[-1].dependencies[1]
        assert query.units[-1].rule == "set_union_all"


@pytest.mark.parametrize("damage", ("rank_peer", "frame_members", "row_choice"))
def test_coordinated_window_syntax_damage_is_not_its_own_witness(tmp_path, damage):
    artifact = original(tmp_path, "postgres", "R2_mixed", "joint")
    query = prepare_refinement(artifact, capabilities(artifact), policy=TieRefinement())
    found = False
    for index, cte in enumerate(query.statement.ctes):
        if type(cte.query) is not Select:
            continue
        columns = list(cte.query.columns)
        for position, (name, value) in enumerate(columns):
            replacement = None
            if damage == "frame_members" and value.kind == "scalar_query":
                inner = value.args[0]
                replacement = Expr(
                    "scalar_query", (replace(inner, where=Expr("and", ())),)
                )
            elif value.kind == "window":
                original_column, alias, partitions, orders, full = value.args
                if damage == "rank_peer" and original_column.function == "rank":
                    replacement = Expr(
                        "window",
                        (
                            original_column,
                            alias,
                            partitions,
                            orders + (Order(ref(alias, query.prefix + "k0")),),
                            full,
                        ),
                    )
                elif (
                    damage == "row_choice" and original_column.function == "row_number"
                ):
                    replacement = Expr(
                        "window", (original_column, alias, partitions, orders[:1], full)
                    )
            if replacement is not None:
                columns[position] = (name, replacement)
                changed = replace(cte, query=replace(cte.query, columns=tuple(columns)))
                damaged = rewrite_cte(query, index, changed)
                render(damaged.statement, artifact)
                with pytest.raises(ValueError, match="NATIVE_RULE_CORRESPONDENCE"):
                    verify_refinement(damaged)
                found = True
                break
        if found:
            break
    assert found


def test_reopened_graph_addresses_are_structural_but_live_roots_stay_distinct(tmp_path):
    first = original(tmp_path / "first", "postgres", "R2_mixed", "joint")
    second = original(tmp_path / "second", "postgres", "R2_mixed", "joint")
    a = prepare_refinement(first, capabilities(first), policy=TieRefinement())
    b = prepare_refinement(second, capabilities(second), policy=TieRefinement())
    assert first is not second
    assert tuple(u.coordinates for u in a.units) == tuple(
        u.coordinates for u in b.units
    )
    assert render(a.statement, first).sql == render(b.statement, second).sql
    with pytest.raises(ValueError):
        prepare_refinement(second, a.sources, policy=TieRefinement())
