"""Shared PostgreSQL source-assurance fixture."""

from pietto._project.project_execution_postgres_adbc_native import (
    CONTEXT_SQL,
    NativeReply,
)
from pietto._project.project_postgres_source_assurance import CatalogReply, SQL


def catalog():
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
        CatalogReply(
            kind,
            arguments,
            rows,
            NativeReply(SQL[kind].encode(), arguments, rows, "NORMAL"),
        )
        for kind, arguments, rows in entries
    )
    return context, raw_context, replies
