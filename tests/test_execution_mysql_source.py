"""Closed native-view structure and independent data-only closure; no DB startup."""

from dataclasses import replace

import pytest

from pietto._project import project_mysql_view_source as model
from pietto._project.project_mysql_view_source_verification import (
    SourceObject,
    verify_view,
    verify_closure,
)


def view(body, name="v", security="INVOKER"):
    return model.recognize_view(
        ("phase66", name),
        f"CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`%` SQL SECURITY {security} VIEW `{name}` AS "
        + body,
    )


@pytest.mark.parametrize(
    "body,expected",
    (
        (
            "select 10 AS `part`,`l`.`lid` AS `lid` from `l` where (`l`.`version_id` = 1) union all select 20 AS `part`,`r`.`lid` AS `lid` from `r` where (`r`.`version_id` = 1)",
            ("l", "r"),
        ),
        (
            "select `b`.`id` AS `id`,cast(((`b`.`p68_raw_id` - 1) % 2) as signed) AS `p68_part`,cast(((`b`.`p68_raw_id` - 1) DIV 2) as signed) AS `p68_lid` from `base` `b`",
            ("base",),
        ),
        (
            "select `b`.`order.id` AS `order.id` from `base` `b` where ((`b`.`source_version` = (select `registry`.`version_tag` from `registry`)) and ((current_user() <> 'pietto_subset@%') or (`b`.`order.id` <> 1)))",
            ("base", "registry"),
        ),
        ("select `n`.`id` AS `id` from `nested view é` `n`", ("nested view é",)),
        (
            "select `b`.`field.from(é)` AS `from.call()`,_utf8mb4'FROM fake; sleep(1)' AS `text` from `a.b`.`table with space` `b`",
            ("table with space",),
        ),
        ("select `x`.`id` AS `id` from (select `t`.`id` AS `id` from `t`) `x`", ("t",)),
        ("select `a``b`.`id` AS `id` from `a``b`", ("a`b",)),
    ),
)
def test_required_definition_mechanisms_keep_complete_ordered_refs(body, expected):
    prepared = view(body)
    assert tuple(name for _, _, name in verify_view(prepared)) == expected


@pytest.mark.parametrize(
    "body",
    (
        "select `hidden`.`read_value`() AS `id` from `t`",
        "select `t`.`id` AS `id` from `t` where (0 AND `hidden`.`read_value`())",
        "select `t`.`id` AS `id` from `t` where (`t`.`id` = (select load_file('/x') AS `x`))",
        "select `t`.`id` AS `id` from `t` union all select mysqlx_error(1) AS `id`",
        "select `CURRENT_USER`() AS `id`",
        "select `schema`.`CURRENT_USER`() AS `id`",
        "select current_timestamp AS `id`",
        "select @value AS `id`",
        "select `t`.`id` AS `id` from `t` LIMIT 0",
        "select `t`.`id` AS `id` from `t` /*!80000 WHERE false */",
        "select `t`.`id` AS `id` from `t`; SELECT 1",
        "select 0x10 AS `id`",
    ),
)
def test_unsupported_effects_and_unconsumed_syntax_fail_closed(body):
    with pytest.raises(model.ViewSourceError):
        verify_view(view(body))


def test_same_literal_is_not_a_call_and_lexer_spans_are_exact():
    prepared = view("select 'routine() FROM `other`' AS `x`")
    assert verify_view(prepared) == ()
    tokens = model.lex(prepared.sql)
    assert all(t.start < t.end and prepared.sql[t.start : t.end] for t in tokens)
    with pytest.raises(model.ViewSourceError):
        model.lex(prepared.sql + " /* ignored? */")
    with pytest.raises(model.ViewSourceError):
        model.lex("select 'unterminated")
    with pytest.raises(model.ViewSourceError):
        model.lex(prepared.sql, model.ViewLimits(tokens=3))
    with pytest.raises(model.ViewSourceError):
        view("select " + "NOT " * 70 + "1 AS `x`")


def objects():
    context = ("server", "account", "role", "database", "transaction")
    root = view(
        "select `a`.`id` AS `id` from `a` union all select `a`.`id` AS `id` from `a`"
    )
    nested = view("select `b`.`id` AS `id` from `b`", name="a", security="DEFINER")
    return context, (
        SourceObject(root.key, "VIEW", None, (("id", "", ""),), root, context),
        SourceObject(nested.key, "VIEW", None, (("id", "", ""),), nested, context),
        SourceObject(
            ("phase66", "b"),
            "BASE TABLE",
            "InnoDB",
            (("id", "auto_increment", ""),),
            None,
            context,
        ),
    )


def test_complete_closure_keeps_repeated_edges_and_independent_verification(
    monkeypatch,
):
    context, records = objects()
    monkeypatch.setattr(
        model,
        "recognize_view",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("constructor called")),
    )
    edges = verify_closure((("phase66", "v"),), records, context)
    assert [edge[2] for edge in edges] == [
        ("phase66", "a"),
        ("phase66", "b"),
        ("phase66", "a"),
    ]


@pytest.mark.parametrize(
    "damage",
    (
        "missing",
        "extra",
        "reordered",
        "foreign",
        "engine",
        "virtual",
        "column",
        "edge",
        "coverage",
        "cycle",
    ),
)
def test_complete_closure_discriminating_damages(damage):
    context, original = objects()
    records = list(original)
    root_view = records[0].view
    assert root_view is not None
    if damage == "missing":
        records.pop()
    elif damage == "extra":
        records.append(replace(records[-1], key=("phase66", "unused")))
    elif damage == "reordered":
        records.reverse()
    elif damage == "foreign":
        records[1] = replace(records[1], context=("foreign",))
    elif damage == "engine":
        records[-1] = replace(records[-1], engine="MyISAM")
    elif damage == "virtual":
        records[-1] = replace(
            records[-1], columns=(("id", "VIRTUAL GENERATED", "hidden()"),)
        )
    elif damage == "column":
        records[-1] = replace(records[-1], columns=(("other", "", ""),))
    elif damage == "edge":
        records[0] = replace(records[0], view=replace(root_view, references=()))
    elif damage == "coverage":
        records[0] = replace(
            records[0],
            view=replace(
                root_view,
                tree=replace(root_view.tree, end=root_view.tree.end - 1),
            ),
        )
    else:
        records[1] = replace(
            records[1], view=view("select `v`.`id` AS `id` from `v`", name="a")
        )
    with pytest.raises(model.ViewSourceError):
        verify_closure((("phase66", "v"),), tuple(records), context)


@pytest.mark.parametrize(
    "change",
    (
        {"sql_mode": "NO_BACKSLASH_ESCAPES"},
        {"sql_mode": "ANSI_QUOTES"},
        {"quote_show_create": 0},
        {"charset": "latin1"},
    ),
)
def test_native_lexical_context_cannot_be_relabelled(change):
    prepared = view("select 'safe' AS `x`")
    with pytest.raises(model.ViewSourceError, match="MYSQL_VIEW_LEXICAL_CONTEXT"):
        verify_view(replace(prepared, **change))


def test_missing_native_lifetime_never_submits_source_sql(monkeypatch):
    from types import SimpleNamespace
    from pietto._project import project_execution_mysql_context as context
    from pietto._project.project_execution import ExecutionError

    calls = []
    owner = SimpleNamespace(
        _checkpoint=lambda: calls.append("checkpoint"),
        request=SimpleNamespace(mysql_deployment=None),
    )
    monkeypatch.setattr(
        context,
        "read_control",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("unqualified SQL submitted")
        ),
    )
    with pytest.raises(ExecutionError, match="MYSQL_DEPLOYMENT_PREMISE_REQUIRED"):
        context.qualify_sources(owner)
    assert calls == ["checkpoint"]


def test_nested_security_preserves_each_inherited_path():
    from pietto._project.project_mysql_view_source_verification import security_paths

    context, records = objects()
    verify_closure((("phase66", "v"),), records, context)
    paths = security_paths((("phase66", "v"),), records, "reader@%", "NONE")
    assert [p[3] for p in paths] == ["reader@%", "root@%", "root@%", "root@%", "root@%"]
    assert paths[1][0] != paths[3][0]
    # An invoker view nested below a definer retains that definer, not reader.
    records = (
        replace(
            records[0],
            view=view("select `a`.`id` AS `id` from `a`", security="DEFINER"),
        ),
        replace(records[1], view=view("select `b`.`id` AS `id` from `b`", name="a")),
        records[2],
    )
    verify_closure((("phase66", "v"),), records, context)
    assert all(
        p[3] == "root@%"
        for p in security_paths((("phase66", "v"),), records, "reader@%", "NONE")
    )
