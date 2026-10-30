"""Emission of nested relations: a checked Collect read or Unnest is refused
per target."""

from __future__ import annotations

import json

import pytest

import pietto.execution as execution
from pietto.cli import main as cli_main

from _pietto_plan_nested import (
    HEAD,
    SHAPES,
    UNNEST_PARENT,
    UNNEST_SHAPES,
    emission_contract,
    imported_sources,
    imported_unnest_sources,
    project,
    sources,
)

pytestmark = pytest.mark.ci_workload("general-runtime")

# Each shape's Collect reads, where `collect` is written, in source order.
READS = {
    "closed": [("main.pietto", 20, 18)],
    "top_k": [("main.pietto", 24, 25)],
    "joined_capture": [("main.pietto", 25, 26)],
    "joined_parent": [("main.pietto", 21, 18)],
    "parallel": [("main.pietto", 23, 14), ("main.pietto", 24, 14)],
    "ordered_parent": [("main.pietto", 19, 18)],
    "windowed": [("main.pietto", 22, 18)],
    "staged_capture": [("main.pietto", 24, 25)],
    "distinct_producer": [("main.pietto", 20, 18)],
    "qualify_producer": [("main.pietto", 23, 18)],
    "reader": [("main.pietto", 19, 18)],
    "exists_reader": [("main.pietto", 19, 18)],
    "scalar_reader": [("main.pietto", 19, 18)],
    "imported": [("parent.pietto", 19, 18)],
}
SENTINELS = ("nested_relation", "<nested relation>")


def _project(tmp_path, shape, dialect):
    target = "postgres" if dialect == "postgres" else "mysql"
    files = (
        imported_sources(target)
        if shape == "imported"
        else imported_unnest_sources(target)
        if shape == "unnest_imported"
        else sources(shape, target)
    )
    root = project(tmp_path / f"{shape}-{dialect}", files)
    module = "parent.pietto" if shape.endswith("imported") else "main.pietto"
    (root / "contract.json").write_text(
        emission_contract(target, module), encoding="utf-8"
    )
    return root


def _emit(root, dialect, capsys, *extra):
    code = cli_main(
        [
            "emit-sql",
            "--project",
            str(root),
            "--module",
            "main.pietto",
            "--kind",
            "query",
            "--name",
            "result",
            "--dialect",
            dialect,
            "--emission-contract",
            "contract.json",
            *extra,
        ]
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", (*SHAPES, "imported"))
def test_a_checked_collect_program_is_blocked_at_each_read(
    tmp_path, capsys, shape, dialect, monkeypatch
):
    root = _project(tmp_path, shape, dialect)
    monkeypatch.chdir(root)
    assert cli_main(["check", "--project", ".", "--format", "json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is True and checked["diagnostics"] == []

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1
    assert document["status"] == "BLOCKED"
    assert document["artifact"] is None
    assert document["cli_errors"] == [] and document["diagnostics"] == []
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (
                item["location"]["path"],
                item["location"]["line"],
                item["location"]["column"],
            ),
        )
        for item in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "collect_not_admitted_on_target",
            {"kind": "collect", "position": position},
            location,
        )
        for position, location in enumerate(READS[shape])
    ]
    assert not any(sentinel in out for sentinel in SENTINELS)

    code, out, text = _emit(root, dialect, capsys, "--format", "text")
    assert code == 1 and out == ""
    assert text.splitlines()[0] == "pietto.sql-emission.v1 BLOCKED"
    assert [line for line in text.splitlines() if line.startswith("blocker")] == [
        "blocker PIE-B1003 UNSUPPORTED_RULE: collect_not_admitted_on_target "
        f"({path}:{line}:{column})"
        for path, line, column in READS[shape]
    ]
    assert not any(sentinel in text for sentinel in SENTINELS)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_compile_query_refuses_a_collect_program_with_the_command_document(
    tmp_path, capsys, dialect
):
    root = _project(tmp_path, "top_k", dialect)
    _, out, _ = _emit(root, dialect, capsys, "--format", "json")

    with pytest.raises(execution.CompileRejected) as error:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
    assert error.value.status == "BLOCKED"
    assert json.loads(error.value.emission) == json.loads(out)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_a_table_function_refusal_precedes_the_collect_refusal(
    tmp_path, capsys, dialect
):
    target = "postgres" if dialect == "postgres" else "mysql"
    files = sources("closed", target)
    files["main.pietto"] = files["main.pietto"].replace(
        "    from rows\n    select:\n        id\n        nested",
        "    from rows\n    where exists series\n    select:\n        id\n        nested",
    ) + (
        "query series:\n    from generate_series(1, 3, 1) as n\n    select:\n        n\n"
    )
    root = project(tmp_path / dialect, files)
    (root / "contract.json").write_text(emission_contract(target), encoding="utf-8")

    _, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    details = [item["subject"]["detail"] for item in document["blockers"]]
    assert details == (
        ["collect_not_admitted_on_target"]
        if dialect == "postgres"
        else ["table_function_not_admitted_on_target", "collect_not_admitted_on_target"]
    )


_COLLECT = ("collect_not_admitted_on_target", "collect", "main.pietto", 21, 18)
# Each Unnest shape's refusals, in source order: the parent's Collect read,
# then each Unnest let.
REFUSALS = {
    **{
        shape: [
            _COLLECT,
            ("unnest_not_admitted_on_target", "unnest", "main.pietto", line, 5),
        ]
        for shape, line in (
            ("unnest_cross", 24),
            ("unnest_inner", 24),
            ("unnest_left", 24),
            ("unnest_left_where", 24),
            ("unnest_left_on_parent", 24),
            ("unnest_left_on_match", 24),
            ("unnest_ordered", 24),
            ("unnest_alias", 25),
            ("unnest_left_joined_parent", 26),
            ("unnest_join_binding", 26),
            ("unnest_cross_joined_parent", 26),
            ("unnest_beside_series", 25),
            ("unnest_captured_exists", 30),
        )
    },
    "unnest_two_bodies": [
        _COLLECT,
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 24, 5),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 30, 5),
    ],
    "unnest_imported": [
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 6, 5),
        ("collect_not_admitted_on_target", "collect", "parent.pietto", 21, 18),
    ],
    "unnest_language": [
        ("collect_not_admitted_on_target", "collect", "main.pietto", 20, 25),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 23, 5),
    ],
    "unnest_inner_nullable": [
        ("collect_not_admitted_on_target", "collect", "main.pietto", 19, 18),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 22, 5),
    ],
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", REFUSALS)
def test_a_checked_unnest_program_is_blocked_at_each_let(
    tmp_path, capsys, shape, dialect, monkeypatch
):
    assert set(REFUSALS) == {*UNNEST_SHAPES, "unnest_imported"}
    root = _project(tmp_path, shape, dialect)
    monkeypatch.chdir(root)
    assert cli_main(["check", "--project", ".", "--format", "json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is True and checked["diagnostics"] == []

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1
    assert (document["status"], document["artifact"]) == ("BLOCKED", None)
    assert document["cli_errors"] == [] and document["diagnostics"] == []
    expected = REFUSALS[shape]
    if shape == "unnest_beside_series" and dialect == "mysql":
        # The table-function refusal precedes every nested one (D70.05).
        assert document["blockers"][0]["subject"]["detail"] == (
            "table_function_not_admitted_on_target"
        )
        document["blockers"] = document["blockers"][1:]
    # Each kind's references count in source order within a module.
    counts = {"collect": 0, "unnest": 0}
    references = []
    for _, kind, _, _, _ in expected:
        references.append({"kind": kind, "position": counts[kind]})
        counts[kind] += 1
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (
                item["location"]["path"],
                item["location"]["line"],
                item["location"]["column"],
            ),
        )
        for item in document["blockers"]
    ] == [
        ("PIE-B1003", detail, reference, (path, line, column))
        for (detail, _, path, line, column), reference in zip(
            expected, references, strict=True
        )
    ]
    assert not any(sentinel in out for sentinel in SENTINELS)

    code, out, text = _emit(root, dialect, capsys, "--format", "text")
    assert code == 1 and out == ""
    assert text.splitlines()[0] == "pietto.sql-emission.v1 BLOCKED"
    assert [
        line
        for line in text.splitlines()
        if line.startswith("blocker") and "table_function" not in line
    ] == [
        f"blocker PIE-B1003 UNSUPPORTED_RULE: {detail} ({path}:{line}:{column})"
        for detail, _, path, line, column in expected
    ]
    assert not any(sentinel in text for sentinel in SENTINELS)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_compile_query_refuses_an_unnest_program_with_the_command_document(
    tmp_path, capsys, dialect
):
    root = _project(tmp_path, "unnest_left", dialect)
    _, out, _ = _emit(root, dialect, capsys, "--format", "json")

    with pytest.raises(execution.CompileRejected) as error:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
    assert error.value.status == "BLOCKED"
    assert json.loads(error.value.emission) == json.loads(out)
    assert "unnest_not_admitted_on_target" in out


# A Timestamp JOIN port beside a CROSS JOIN fails the scalar meaning admission;
# the nested refusals still come first, each at its own read or let.
TIMESTAMP_CROSS = {
    "unnest": (
        UNNEST_PARENT.replace(
            "            total\n", "            total\n            created_at\n"
        )
        + "query result:\n    from parent\n    let o = unnest(parent.nested)\n"
        + "    cross join o\n    select:\n        id = parent.id\n"
        + "        total = o.total\n",
        [
            ("collect_not_admitted_on_target", "collect", 22, 18),
            ("unnest_not_admitted_on_target", "unnest", 25, 5),
        ],
    ),
    "collect": (
        "query result:\n    let children:\n        from rows\n        select id\n"
        + "        order by id\n    from rows\n    cross join orders\n    select:\n"
        + "        id = rows.id\n        at = orders.created_at\n"
        + "        nested = collect children\n",
        [("collect_not_admitted_on_target", "collect", 21, 18)],
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", TIMESTAMP_CROSS)
def test_a_timestamp_beside_a_cross_join_keeps_the_nested_refusals(
    tmp_path, capsys, shape, dialect
):
    target = "postgres" if dialect == "postgres" else "mysql"
    body, expected = TIMESTAMP_CROSS[shape]
    head = HEAD.format(target=target).replace(
        "    created_at: Int\n", "    created_at: Timestamp\n"
    )
    root = project(tmp_path / dialect, {"main.pietto": head + body})
    contract = json.loads(emission_contract(target))
    for item in contract["sources"][1]["fields"]:
        if item["name"] == "created_at":
            item["representation"] = {
                "storage": {
                    "kind": "pg_timestamp" if target == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                },
                "nullable": False,
                "domain": {"kind": "timestamp"},
            }
    (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1 and document["status"] == "BLOCKED"
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (item["location"]["line"], item["location"]["column"]),
        )
        for item in document["blockers"]
    ] == [
        ("PIE-B1003", detail, {"kind": kind, "position": 0}, (line, column))
        for detail, kind, line, column in expected
    ]
