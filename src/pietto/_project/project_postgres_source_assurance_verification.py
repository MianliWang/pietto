"""Independent complete-source checking of S09 native catalog replies.

The PG18 token decoder is trusted framing. This module checks native structure,
implementation links and every security/reference path; it never acquires data.
"""

from typing import cast

from pietto._project.project_execution import ExecutionError
from pietto._project.project_postgres_source_assurance import (
    Node,
    CatalogReply,
    SQL,
    parse_native,
    MAX_OBJECTS,
    MAX_DEPTH,
)
from pietto._project.project_refinement_enumeration import atom

__all__: tuple[str, ...] = ()

# Exact PG18 read-node members, including fields with empty native values.
NODE_FIELDS = {
    "ALIAS": ("aliasname colnames",),
    "BOOLEXPR": ("boolop args location",),
    "CONST": (
        "consttype consttypmod constcollid constlen constbyval constisnull location constvalue",
    ),
    "FROMEXPR": ("fromlist quals",),
    "FUNCEXPR": (
        "funcid funcresulttype funcretset funcvariadic funcformat funccollid inputcollid args location",
    ),
    "OPEXPR": (
        "opno opfuncid opresulttype opretset opcollid inputcollid args location",
    ),
    "QUERY": (
        "commandType querySource canSetTag utilityStmt resultRelation hasAggs hasWindowFuncs hasTargetSRFs hasSubLinks hasDistinctOn hasRecursive hasModifyingCTE hasForUpdate hasRowSecurity hasGroupRTE isReturn cteList rtable rteperminfos jointree mergeActionList mergeTargetRelation mergeJoinCondition targetList override onConflict returningOldAlias returningNewAlias returningList groupClause groupDistinct groupingSets havingQual windowClause distinctClause sortClause limitOffset limitCount limitOption rowMarks setOperations constraintDeps withCheckOptions stmt_location stmt_len",
    ),
    "RANGETBLENTRY": (
        "alias eref rtekind relid inh relkind rellockmode perminfoindex tablesample lateral inFromCl securityQuals",
        "alias eref rtekind subquery security_barrier relid inh relkind rellockmode perminfoindex lateral inFromCl securityQuals",
    ),
    "RANGETBLREF": ("rtindex",),
    "RTEPERMISSIONINFO": (
        "relid inh requiredPerms checkAsUser selectedCols insertedCols updatedCols",
    ),
    "SETOPERATIONSTMT": (
        "op all larg rarg colTypes colTypmods colCollations groupClauses",
    ),
    "SQLVALUEFUNCTION": ("op type typmod location",),
    "SUBLINK": ("subLinkType subLinkId testexpr operName subselect location",),
    "TARGETENTRY": (
        "expr resno resname ressortgroupref resorigtbl resorigcol resjunk",
    ),
    "VAR": (
        "varno varattno vartype vartypmod varcollid varnullingrels varlevelsup varreturningtype varnosyn varattnosyn location",
    ),
    "RELABELTYPE": ("arg resulttype resulttypmod resultcollid relabelformat location",),
}

# These are finite implementation signatures, not a namespace/volatility gate.
# OIDs are checked as links; no OID threshold grants authority.
CORE = {
    ("texteq", "25 25", 16),
    ("textne", "25 25", 16),
    ("nameeq", "19 19", 16),
    ("namene", "19 19", 16),
    ("int8eq", "20 20", 16),
    ("int8ne", "20 20", 16),
    ("int84eq", "20 23", 16),
    ("int84ne", "20 23", 16),
    ("int4eq", "23 23", 16),
    ("int4ne", "23 23", 16),
    ("int8mi", "20 20", 20),
    ("int84mi", "20 23", 20),
    ("int8div", "20 20", 20),
    ("int84div", "20 23", 20),
    ("int8mod", "20 20", 20),
    ("int4mod", "23 23", 23),
    ("int48", "23", 20),
    ("int28", "21", 20),
    ("int84", "20", 23),
    ("int82", "20", 21),
    ("i2toi4", "21", 23),
    ("i4toi2", "23", 21),
    ("int8abs", "20", 20),
    ("int4abs", "23", 23),
    ("name_text", "19", 25),
    ("text_name", "25", 19),
}
TYPE_PROFILE = {
    16: ("bool", ("boolin", "boolout", "boolrecv", "boolsend")),
    19: ("name", ("namein", "nameout", "namerecv", "namesend")),
    20: ("int8", ("int8in", "int8out", "int8recv", "int8send")),
    21: ("int2", ("int2in", "int2out", "int2recv", "int2send")),
    23: ("int4", ("int4in", "int4out", "int4recv", "int4send")),
    25: ("text", ("textin", "textout", "textrecv", "textsend")),
    26: ("oid", ("oidin", "oidout", "oidrecv", "oidsend")),
    700: ("float4", ("float4in", "float4out", "float4recv", "float4send")),
    701: ("float8", ("float8in", "float8out", "float8recv", "float8send")),
    1042: ("bpchar", ("bpcharin", "bpcharout", "bpcharrecv", "bpcharsend")),
    1043: ("varchar", ("varcharin", "varcharout", "varcharrecv", "varcharsend")),
    1114: (
        "timestamp",
        ("timestamp_in", "timestamp_out", "timestamp_recv", "timestamp_send"),
    ),
    1184: (
        "timestamptz",
        ("timestamptz_in", "timestamptz_out", "timestamptz_recv", "timestamptz_send"),
    ),
    1700: ("numeric", ("numeric_in", "numeric_out", "numeric_recv", "numeric_send")),
    2950: ("uuid", ("uuid_in", "uuid_out", "uuid_recv", "uuid_send")),
}


def need(condition, code="POSTGRES_SOURCE_NOT_QUALIFIED"):
    if not condition:
        raise ExecutionError(code)


def values(rows):
    return tuple(tuple(atom(v) for v in row) for row in rows)


def verify_native_reply(reply, sql, arguments, rows):
    from pietto._project.project_execution_postgres import PostgresCatalogReply
    from pietto._project.project_execution_postgres_adbc_native import (
        NativeReply,
        CONTEXT_SQL,
    )

    need(
        type(reply) in (NativeReply, PostgresCatalogReply),
        "POSTGRES_SOURCE_NATIVE_REPLY",
    )
    need(
        type(reply.arguments) is tuple
        and type(reply.rows) is tuple
        and all(type(row) is tuple for row in reply.rows),
        "POSTGRES_SOURCE_NATIVE_REPLY",
    )
    need(
        reply.sql == sql.encode()
        and values((reply.arguments,)) == values((arguments,))
        and reply.terminal == "NORMAL"
        and values(reply.rows) == values(rows),
        "POSTGRES_SOURCE_NATIVE_REPLY",
    )
    if type(reply) is not PostgresCatalogReply:
        return
    expected_types = {
        "resolve": (20,),
        "relation": (20, 25, 25, 25, 25, 20, 16, 16, 25, 20, 25, 20, 16),
        "attributes": (23, 25, 20, 20, 25, 25),
        "children": (20, 23, 16),
        "rewrite": (20, 25, 25, 16, 25, 25),
        "function": (20, 25, 25, 25, 25, 25, 25, 20, 25, 16, 25, 16, 25, 20, 16),
        "type": (20, 25, 25, 25, 20, 20, 20, 20, 20, 20, 16),
        "operator": (20, 25, 25, 20, 20, 20, 20, 16),
        "collation": (20, 25, 25, 25, 16, 23, 16),
        "role": (20, 25, 16, 16, 16),
        "members": (20, 20, 20, 16, 16, 16),
    }
    expected = (
        (23, 25, 25, 25, 20, 20, 23, 25, 25, 25, 25, 25, 25, 25, 25, 23, 25)
        if sql == CONTEXT_SQL
        else next((expected_types[k] for k, v in SQL.items() if v == sql), None)
    )
    if expected is None:
        raise ExecutionError("POSTGRES_SOURCE_NATIVE_SCHEMA")
    need(
        type(reply.metadata) is tuple
        and all(
            type(m) is tuple
            and len(m) == 3
            and type(m[0]) is int
            and m[0] == i
            and type(m[1]) is str
            and type(m[2]) is int
            for i, m in enumerate(reply.metadata)
        )
        and tuple(m[2] for m in reply.metadata) == expected,
        "POSTGRES_SOURCE_NATIVE_SCHEMA",
    )
    need(
        type(reply.status) is bytes and reply.status.startswith(b"SELECT "),
        "POSTGRES_SOURCE_NATIVE_TERMINAL",
    )
    for row in reply.rows:
        need(
            type(row) is tuple and len(row) == len(expected),
            "POSTGRES_SOURCE_NATIVE_SCHEMA",
        )
        for value, oid in zip(row, expected, strict=True):
            need(
                value is None
                or type(value) is {16: bool, 20: int, 23: int, 25: str}[oid],
                "POSTGRES_SOURCE_NATIVE_TYPE",
            )


def verify_catalog(roots, root_oids, replies, context, schemas, context_native=None):
    """No acquisition call or constructor-derived safe verdict is consumed."""
    from pietto._project.project_execution_postgres_adbc_native import CONTEXT_SQL

    need(
        type(replies) is tuple and type(roots) is tuple and len(roots) == len(root_oids)
    )
    need(
        context_native is not None
        and context_native.sql == CONTEXT_SQL.encode()
        and context_native.arguments == ()
        and context_native.terminal == "NORMAL"
        and values(context_native.rows) == values((context,)),
        "POSTGRES_SOURCE_NATIVE_CONTEXT",
    )
    verify_native_reply(context_native, CONTEXT_SQL, (), (context,))
    need(
        len(context) == 17
        and context[0] == 180006
        and context[9:14] == ("on", "UTF8", "pg_catalog", "UTC", "on")
        and context[8] in ("repeatable read", "serializable"),
        "POSTGRES_SOURCE_NATIVE_CONTEXT",
    )
    index = {}
    for reply in replies:
        need(
            type(reply) is CatalogReply
            and reply.kind in SQL
            and type(reply.arguments) is tuple
        )
        reply = cast(CatalogReply, reply)
        key = reply.kind, reply.arguments
        need(key not in index, "POSTGRES_SOURCE_DUPLICATE_REPLY")
        native = reply.native
        need(
            native.sql == SQL[reply.kind].encode()
            and native.arguments == reply.arguments
            and native.terminal == "NORMAL"
            and values(native.rows) == values(reply.rows),
            "POSTGRES_SOURCE_NATIVE_REPLY",
        )
        verify_native_reply(native, SQL[reply.kind], reply.arguments, reply.rows)
        index[key] = reply.rows
    used, paths, stack = set(), [], set()

    def rows(kind, *arguments):
        key = kind, arguments
        need(key in index, "POSTGRES_SOURCE_MISSING_REPLY")
        used.add(key)
        return index[key]

    def one(kind, oid, width):
        record = rows(kind, oid)
        need(
            len(record) == 1
            and len(record[0]) == width
            and type(record[0][0]) is int
            and record[0][0] == oid,
            "POSTGRES_SOURCE_CATALOG_IDENTITY",
        )
        return record[0]

    checked_roles = set()

    def role(oid, depth=0):
        need(depth <= MAX_DEPTH, "POSTGRES_SOURCE_RESOURCE_LIMIT")
        if oid in checked_roles:
            return
        need(len(checked_roles) < MAX_OBJECTS, "POSTGRES_SOURCE_RESOURCE_LIMIT")
        checked_roles.add(oid)
        r = one("role", oid, 5)
        need(type(r[1]) is str and all(type(v) is bool for v in r[2:]))
        for membership in rows("members", oid):
            need(
                len(membership) == 6
                and membership[1] == oid
                and all(type(v) is int for v in membership[:3])
                and all(type(v) is bool for v in membership[3:])
            )
            role(membership[0], depth + 1)

    def proc(oid, *, profile=None, io=None):
        p = one("function", oid, 15)
        need("pg_catalog" in schemas, "POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")
        need(
            p[1] == "pg_catalog"
            and p[3] == "internal"
            and p[5] is None
            and p[9] is False
            and p[10] == "f"
            and p[11] is False
            and p[12] is None
            and p[13] == 0
            and p[14] is False,
            "POSTGRES_SOURCE_CALLABLE_NOT_QUALIFIED",
        )
        signature = (p[4], p[6], p[7])
        if io is not None:
            name, kind, tid = io
            args = tuple(map(int, p[6].split()))
            if kind == 0:
                valid = args in ((2275,), (2275, 26, 23)) and p[7] == tid
            elif kind == 1:
                valid = args == (tid,) and p[7] == 2275
            elif kind == 2:
                valid = args in ((2281,), (2281, 26, 23)) and p[7] == tid
            else:
                valid = args == (tid,) and p[7] == 17
            need(
                p[4] == name and p[2] == name and p[8] in ("i", "s") and valid,
                "POSTGRES_SOURCE_TYPE_IO_NOT_QUALIFIED",
            )
        elif profile == "heap":
            need(
                signature == ("heap_tableam_handler", "2281", 269)
                and p[2] == "heap_tableam_handler"
                and p[8] == "v"
            )
        else:
            need(
                signature in CORE and p[8] == "i",
                "POSTGRES_SOURCE_CALLABLE_NOT_QUALIFIED",
            )
        return p

    def typ(oid):
        t = one("type", oid, 11)
        need(oid in TYPE_PROFILE, "POSTGRES_SOURCE_TYPE_NOT_QUALIFIED")
        name, io = TYPE_PROFILE[oid]
        # name's char element is storage, not a callable array source.
        need(
            t[1:5] == ("pg_catalog", name, "b", 0)
            and t[5] in (0, 18)
            and t[10] is False
        )
        for kind, f in enumerate(t[6:10]):
            need(type(f) is int and f > 0)
            proc(f, io=(io[kind], kind, oid))

    def collation(oid):
        if not oid:
            return
        c = one("collation", oid, 7)
        need(
            c[1] == "pg_catalog"
            and c[2] in ("default", "C", "POSIX")
            and c[3] in ("d", "c")
            and c[4] is True
            and c[6] is False,
            "POSTGRES_SOURCE_COLLATION_NOT_QUALIFIED",
        )

    def walk(value, path, permission_role, query_stack=()):
        if type(value) is tuple:
            for i, child in enumerate(value):
                walk(child, path + (i,), permission_role, query_stack)
            return
        if type(value) is not Node:
            return
        n = value
        fields = dict(n.fields)
        need(
            n.tag in NODE_FIELDS and " ".join(fields) in NODE_FIELDS[n.tag],
            "POSTGRES_SOURCE_NODE_NOT_QUALIFIED",
        )
        if n.tag == "QUERY":
            need(
                fields["commandType"] == 1
                and fields["resultRelation"] == 0
                and fields["utilityStmt"] is None
            )
            for k in (
                "hasAggs",
                "hasWindowFuncs",
                "hasTargetSRFs",
                "hasRecursive",
                "hasModifyingCTE",
                "hasForUpdate",
                "hasRowSecurity",
                "hasGroupRTE",
                "isReturn",
                "hasDistinctOn",
                "groupDistinct",
            ):
                need(fields[k] is False)
            for k in (
                "cteList",
                "mergeActionList",
                "mergeJoinCondition",
                "onConflict",
                "returningList",
                "groupClause",
                "groupingSets",
                "havingQual",
                "windowClause",
                "distinctClause",
                "sortClause",
                "limitOffset",
                "limitCount",
                "rowMarks",
                "constraintDeps",
                "withCheckOptions",
            ):
                need(fields[k] is None)
            table = fields["rtable"] or ()
            perms = fields["rteperminfos"] or ()
            need(type(table) is tuple and type(perms) is tuple)
            query_stack = query_stack + (table,)
            for entry in table:
                need(type(entry) is Node and entry.tag == "RANGETBLENTRY")
                entry = cast(Node, entry)
                if entry.get("rtekind") == 0:
                    i = entry.get("perminfoindex")
                    need(type(i) is int and 1 <= i <= len(perms))
                    info = perms[i - 1]
                    need(
                        type(info) is Node
                        and info.tag == "RTEPERMISSIONINFO"
                        and info.get("relid") == entry.get("relid")
                        and info.get("inh") is entry.get("inh")
                        and info.get("requiredPerms") == 2
                        and info.get("checkAsUser") == 0
                    )
        elif n.tag == "RANGETBLENTRY":
            need(fields["lateral"] is False and fields["securityQuals"] is None)
            if fields["rtekind"] == 0:
                need(
                    fields["tablesample"] is None
                    and fields["rellockmode"] == 1
                    and type(fields["inh"]) is bool
                )
                visit(fields["relid"], fields["inh"], path, permission_role)
            else:
                need(
                    fields["rtekind"] == 1
                    and type(fields["subquery"]) is Node
                    and fields["subquery"].tag == "QUERY"
                )
        elif n.tag == "RANGETBLREF":
            need(
                query_stack
                and type(fields["rtindex"]) is int
                and 1 <= fields["rtindex"] <= len(query_stack[-1])
            )
        elif n.tag == "VAR":
            level = fields["varlevelsup"]
            need(type(level) is int and 0 <= level < len(query_stack))
            need(
                type(fields["varno"]) is int
                and 1 <= fields["varno"] <= len(query_stack[-1 - level])
            )
            need(type(fields["varattno"]) is int and fields["varattno"] > 0)
        elif n.tag == "OPEXPR":
            op = one("operator", fields["opno"], 8)
            need(
                op[1] == "pg_catalog"
                and op[7] is False
                and op[6] == fields["opfuncid"]
                and op[5] == fields["opresulttype"]
            )
            p = proc(op[6])
            need(p[6] == " ".join(str(v) for v in op[3:5] if v) and p[7] == op[5])
            need(fields["opretset"] is False)
        elif n.tag == "FUNCEXPR":
            p = proc(fields["funcid"])
            need(
                p[7] == fields["funcresulttype"]
                and fields["funcretset"] is False
                and fields["funcvariadic"] is False
            )
        elif n.tag == "SQLVALUEFUNCTION":
            need(fields["op"] in (10, 11) and fields["type"] == 19)
        elif n.tag == "SETOPERATIONSTMT":
            need(
                fields["op"] == 1
                and fields["all"] is True
                and fields["groupClauses"] is None
            )
            for tid in (fields["colTypes"] or ())[1:]:
                typ(tid)
            for cid in (fields["colCollations"] or ())[1:]:
                collation(cid)
        elif n.tag == "SUBLINK":
            need(
                fields["subLinkType"] == 4
                and fields["testexpr"] is None
                and fields["operName"] is None
            )
        elif n.tag == "BOOLEXPR":
            need(fields["boolop"] in ("and", "or", "not"))
        elif n.tag == "RTEPERMISSIONINFO":
            need(
                fields["requiredPerms"] == 2
                and fields["checkAsUser"] == 0
                and fields["insertedCols"] == ("b",)
                and fields["updatedCols"] == ("b",)
            )
        elif n.tag == "CONST":
            need(
                type(fields["constisnull"]) is bool
                and type(fields["constbyval"]) is bool
            )
            datum = fields["constvalue"]
            need(
                datum is None
                if fields["constisnull"]
                else type(datum) is tuple and len(datum) == 3 and datum[0] == "datum"
            )
        for key in (
            "vartype",
            "consttype",
            "funcresulttype",
            "opresulttype",
            "resulttype",
            "type",
            "paramtype",
        ):
            if fields.get(key):
                typ(fields[key])
        for key in (
            "varcollid",
            "constcollid",
            "funccollid",
            "opcollid",
            "inputcollid",
            "resultcollid",
            "collOid",
        ):
            if fields.get(key):
                collation(fields[key])
        for key, child in n.fields:
            walk(child, path + (key,), permission_role, query_stack)

    def visit(oid, inherit, path, permission_role):
        need(
            len(path) <= MAX_DEPTH * 4 and len(paths) < MAX_OBJECTS * 16,
            "POSTGRES_SOURCE_RESOURCE_LIMIT",
        )
        need(oid not in stack, "POSTGRES_SOURCE_CYCLE_OR_DEPTH")
        stack.add(oid)
        r = one("relation", oid, 13)
        need(r[1] in schemas, "POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")
        need(r[3] in ("r", "p", "v") and r[4] in ("p", "u") and r[12] is False)
        need(r[6] is False and r[7] is False, "POSTGRES_SOURCE_RLS_NOT_QUALIFIED")
        role(r[5])
        if r[3] == "r" or (r[3] == "p" and r[9]):
            need(r[10] == "heap")
            proc(r[11], profile="heap")
        elif r[3] == "p":
            need(r[9:12] == (0, None, None))
        else:
            need(r[9:12] == (0, None, None))
        if r[3] == "v":
            options = (
                ()
                if r[8] is None
                else tuple(r[8].removeprefix("{").removesuffix("}").split(","))
            )
            need(
                all(
                    v
                    in (
                        "security_invoker=true",
                        "security_invoker=false",
                        "security_barrier=true",
                        "security_barrier=false",
                        "check_option=local",
                        "check_option=cascaded",
                    )
                    for v in options
                )
            )
            child_role = context[4] if "security_invoker=true" in options else r[5]
        else:
            child_role = permission_role
        paths.append((path, oid, inherit, permission_role, child_role, context[4]))
        attributes = rows("attributes", oid)
        need(attributes and len({a[0] for a in attributes}) == len(attributes))
        for a in attributes:
            need(len(a) == 6 and a[4] in ("", "s", "v"))
            typ(a[2])
            collation(a[3])
            if a[4] == "v":
                need(type(a[5]) is str)
                # A virtual expression has a base-relation var context.
                dummy = Node("RANGETBLENTRY", (("relid", oid),))
                walk(
                    parse_native(a[5]),
                    path + ("generated", a[0]),
                    child_role,
                    ((dummy,),),
                )
            else:
                need(a[5] is None)
        children = rows("children", oid)
        need(all(len(c) == 3 and c[2] is False for c in children))
        if inherit:
            for i, c in enumerate(children):
                visit(c[0], True, path + ("inherit", i), child_role)
        rules = rows("rewrite", oid)
        if r[3] == "v":
            need(len(rules) == 1 and rules[0][1:5] == ("_RETURN", "1", True, "<>"))
            walk(parse_native(rules[0][5]), path + ("view",), child_role)
        else:
            need(not rules)
        stack.remove(oid)

    role(context[4])
    for i, (root, oid) in enumerate(zip(roots, root_oids, strict=True)):
        need(rows("resolve", *root) == ((oid,),), "POSTGRES_SOURCE_ROOT")
        r = one("relation", oid, 13)
        need(r[1:3] == root, "POSTGRES_SOURCE_ROOT")
        visit(oid, True, ("root", i), context[4])
    need(used == set(index), "POSTGRES_SOURCE_EXTRA_REPLY")
    return tuple(paths)
