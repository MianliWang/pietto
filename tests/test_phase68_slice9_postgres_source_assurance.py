"""Native PG18 node framing and independent source-evidence boundaries."""

from dataclasses import replace
import json
from pathlib import Path
import pytest

from pietto._project.project_execution import ExecutionError
from pietto._project.project_postgres_source_assurance import (
    parse_native,
    nodes,
    CatalogReply,
    SQL,
)
from pietto._project.project_postgres_source_assurance_verification import (
    verify_catalog,
)
from pietto._project.project_execution_postgres_adbc_native import (
    NativeReply,
    CONTEXT_SQL,
)


@pytest.fixture(scope="module")
def actual_views():
    return json.loads(
        (
            Path(__file__).parent / "fixtures/phase68_postgres_source_nodes.json"
        ).read_text()
    )["views"]


def test_full_native_source_positions_survive_decoder(actual_views):
    parsed = {row[2]: parse_native(row[5]) for row in actual_views}
    refs = [
        n.get("relid")
        for _, n in nodes(parsed["p68s9_definer"])
        if n.tag == "RANGETBLENTRY" and n.get("rtekind") == 0
    ]
    assert len(refs) == 2 and refs[0] == refs[1]
    invoker = [n for _, n in nodes(parsed["p68s9_invoker"])]
    assert sum(n.tag == "SUBLINK" for n in invoker) == 1
    assert sum(n.tag == "SQLVALUEFUNCTION" for n in invoker) == 1
    assert sum(n.tag == "RANGETBLENTRY" for n in invoker) == 2
    wrapper = [n for _, n in nodes(parsed["phase66 source é"])]
    assert sum(n.tag == "OPEXPR" for n in wrapper) == 4
    assert any(n.tag == "VAR" and n.get("vartype") == 1700 for n in wrapper)


@pytest.mark.parametrize(
    "text",
    (
        "{VAR :varno 1 :varno 2}",
        "({VAR :varno 1}",
        "{VAR :varno 1} trailing",
        "{CONST :constvalue 1 [ 999 ]}",
        "{VAR :varno }",
    ),
)
def test_node_corruption_is_not_missing_empty_success(text):
    with pytest.raises(ExecutionError):
        parse_native(text)


def test_node_depth_bound_is_resource_failure():
    with pytest.raises(ExecutionError, match="RESOURCE_LIMIT"):
        parse_native("(" * 66 + "<>" + ")" * 66)


def catalog():
    # Independently authored minimal native reply layout; these are data-only
    # observations and cannot be given to PostgresADBCExecution as authority.
    context = (
        180006,
        "db",
        "reader",
        "reader",
        10,
        100,
        200,
        "42",
        "repeatable read",
        "on",
        "UTF8",
        "pg_catalog",
        "UTC",
        "on",
        "127.0.0.1",
        5432,
        "start",
    )
    raw_context = NativeReply(CONTEXT_SQL.encode(), (), (context,), "NORMAL")
    entries = [
        ("resolve", ("public", "items"), ((50000,),)),
        (
            "relation",
            (50000,),
            (
                (
                    50000,
                    "public",
                    "items",
                    "r",
                    "p",
                    10,
                    False,
                    False,
                    None,
                    2,
                    "heap",
                    3,
                    False,
                ),
            ),
        ),
        ("attributes", (50000,), ((1, "id", 20, 0, "", None),)),
        ("children", (50000,), ()),
        ("rewrite", (50000,), ()),
        ("role", (10,), ((10, "reader", False, True, False),)),
        ("members", (10,), ()),
        (
            "type",
            (20,),
            ((20, "pg_catalog", "int8", "b", 0, 0, 460, 461, 2408, 2409, False),),
        ),
    ]
    for oid, name, args, result, volatility in (
        (3, "heap_tableam_handler", "2281", 269, "v"),
        (460, "int8in", "2275", 20, "i"),
        (461, "int8out", "20", 2275, "i"),
        (2408, "int8recv", "2281", 20, "i"),
        (2409, "int8send", "20", 17, "i"),
    ):
        entries.append(
            (
                "function",
                (oid,),
                (
                    (
                        oid,
                        "pg_catalog",
                        name,
                        "internal",
                        name,
                        None,
                        args,
                        result,
                        volatility,
                        False,
                        "f",
                        False,
                        None,
                        0,
                        False,
                    ),
                ),
            )
        )
    replies = tuple(
        CatalogReply(k, a, r, NativeReply(SQL[k].encode(), a, r, "NORMAL"))
        for k, a, r in entries
    )
    return context, raw_context, replies


def verify(replies, context, raw):
    return verify_catalog(
        (("public", "items"),),
        (50000,),
        replies,
        context,
        ("public", "pg_catalog"),
        raw,
    )


def test_complete_source_checker_is_native_reply_bound():
    context, raw, replies = catalog()
    paths = verify(replies, context, raw)
    assert paths == ((("root", 0), 50000, True, 10, 10, 10),)
    for i in range(len(replies)):
        with pytest.raises(ExecutionError):
            verify(replies[:i] + replies[i + 1 :], context, raw)
    forged = context[:6] + (999,) + context[7:]
    with pytest.raises(ExecutionError, match="NATIVE_CONTEXT"):
        verify(replies, forged, raw)


@pytest.mark.parametrize(
    "change",
    (
        "extra",
        "native_reply",
        "foreign_root",
        "custom_io",
        "extension_io",
        "virtual",
        "rls",
        "scope",
    ),
)
def test_unqualified_read_paths_and_copied_native_forgeries(change):
    context, raw, source = catalog()
    replies = list(source)
    if change == "extra":
        replies.append(
            CatalogReply(
                "children",
                (999,),
                (),
                NativeReply(SQL["children"].encode(), (999,), (), "NORMAL"),
            )
        )
    elif change == "scope":
        with pytest.raises(ExecutionError):
            verify_catalog(
                (("public", "items"),),
                (50000,),
                tuple(replies),
                context,
                ("public",),
                raw,
            )
        return
    else:
        kind = (
            "function"
            if change in ("custom_io", "extension_io")
            else "attributes"
            if change == "virtual"
            else "relation"
        )
        i = next(
            i
            for i, r in enumerate(replies)
            if r.kind == kind and (kind != "function" or r.arguments == (460,))
        )
        old = replies[i]
        row = list(old.rows[0])
        if change == "native_reply":
            row[5] = 99
        elif change == "foreign_root":
            row[2] = "elsewhere"
        elif change == "custom_io":
            row[1] = "public"
        elif change == "extension_io":
            row[14] = True
        elif change == "virtual":
            row[4:] = ["v", "{FUNCEXPR :funcid 999}"]
        elif change == "rls":
            row[6] = True
        changed = (tuple(row),)
        native = (
            old.native
            if change == "native_reply"
            else replace(old.native, rows=changed)
        )
        replies[i] = replace(old, rows=changed, native=native)
    with pytest.raises(ExecutionError):
        verify(tuple(replies), context, raw)


def test_nested_pg_invoker_resets_to_original_query_role():
    from _pietto_phase68_slice9_check import tuples, native_reply

    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures/phase68_postgres_source_nodes.json"
        ).read_text()
    )["nested_security"]
    q = fixture["qualification"]
    context = tuple(q["context"])
    replies = tuple(
        CatalogReply(
            r["kind"],
            tuples(r["arguments"]),
            tuples(r["rows"]),
            native_reply(r["native"]),
        )
        for r in q["replies"]
    )
    roots = tuples(q["roots"])
    oids = tuple(
        next(
            r.rows[0][0] for r in replies if r.kind == "resolve" and r.arguments == root
        )
        for root in roots
    )
    paths = verify_catalog(
        roots,
        oids,
        replies,
        context,
        ("public", "pg_catalog"),
        native_reply(fixture["native_context"]),
    )
    relations = {r.rows[0][2]: r.rows[0] for r in replies if r.kind == "relation"}
    invoker = relations["p68s9_invoker"]
    base = relations["p68s9_original"]
    invoker_paths = [p for p in paths if p[1] == invoker[0]]
    base_paths = [p for p in paths if p[1] == base[0]]
    assert len(invoker_paths) == len(base_paths) == 2
    assert all(p[3] == invoker[5] and p[4] == context[4] for p in invoker_paths)
    assert all(p[3] == context[4] for p in base_paths)
    assert context[4] != invoker[5]


def test_role_depth_exhaustion_is_explicit_in_both_traversals(monkeypatch):
    from types import SimpleNamespace
    from pietto._project import project_postgres_source_assurance as source

    context, raw, old = catalog()
    replies = [r for r in old if r.kind not in ("role", "members")]
    for i in range(10, 76):
        for kind, rows in (
            ("role", ((i, "r" + str(i), False, True, False),)),
            ("members", ((i + 1, i, 10, False, True, False),) if i < 75 else ()),
        ):
            replies.append(
                CatalogReply(
                    kind,
                    (i,),
                    rows,
                    NativeReply(SQL[kind].encode(), (i,), rows, "NORMAL"),
                )
            )
    with pytest.raises(ExecutionError, match="RESOURCE_LIMIT"):
        verify(tuple(replies), context, raw)
    lookup = {(SQL[r.kind], r.arguments): r for r in replies}

    def read(sql, arguments):
        r = lookup[sql, arguments]
        return (), r.rows, r.native

    owner = SimpleNamespace(
        request=SimpleNamespace(
            artifact=SimpleNamespace(request=SimpleNamespace(sources=())),
            limits=SimpleNamespace(max_bytes=1024 * 1024),
        ),
        requirements=(),
        context=context,
        _checkpoint=lambda: None,
        _catalog_read=read,
    )
    monkeypatch.setattr(source, "verify_postgres_adbc_deployment", lambda request: None)
    with pytest.raises(ExecutionError, match="RESOURCE_LIMIT"):
        source.qualify_sources(owner)
