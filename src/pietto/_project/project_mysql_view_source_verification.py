"""Independent native-view derivation/closure checking; no live execution grants."""

from dataclasses import dataclass, field

from pietto._project.project_mysql_view_source import (
    Node,
    Token,
    ViewDefinition,
    ViewLimits,
    ViewSourceError,
    lex,
)

__all__: tuple[str, ...] = ()


def need(condition, category="MYSQL_VIEW_DERIVATION"):
    if not condition:
        raise ViewSourceError(category)


def _word(token, value):
    return (
        type(token) is Token
        and token.kind in ("word", "symbol")
        and token.value.upper() == value
    )


def _names(tokens):
    need(len(tokens) in (1, 3, 5))
    need(all(t.kind in ("id", "word") for t in tokens[::2]))
    need(all(_word(t, ".") for t in tokens[1::2]))
    return tuple(t.value for t in tokens[::2])


def _rule(value, *rules):
    return type(value) is Node and value.rule in rules


def verify_view(view, *, limits=ViewLimits()):
    """Check the proposed derivation against all bytes; never invoke its parser."""
    need(
        type(view) is ViewDefinition and type(view.key) is tuple and len(view.key) == 2
    )
    need(all(type(x) is str and x and "\0" not in x for x in view.key))
    need(
        view.charset == "utf8mb4" and view.collation == "utf8mb4_0900_bin",
        "MYSQL_VIEW_LEXICAL_CONTEXT",
    )
    need(
        view.sql_mode == "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION"
        and type(view.quote_show_create) is int
        and view.quote_show_create == 1,
        "MYSQL_VIEW_LEXICAL_CONTEXT",
    )
    tokens = lex(view.sql, limits)
    seen = set()
    names = {}
    references = []
    expressions = {
        "name",
        "star",
        "literal",
        "introduced",
        "unary",
        "binary",
        "group",
        "subquery",
        "cast",
        "call",
        "is_null",
    }
    queries = {"select", "union", "query_group"}

    def reference(node):
        return node.rule == "name" and all(
            t.kind == "id" for t in tokens[node.start : node.end : 2]
        )

    def expression(node):
        return (
            node.rule in expressions
            and node.rule != "star"
            and (node.rule != "name" or reference(node))
        )

    def check(node, depth=0):
        need(
            depth <= limits.depth and len(seen) <= limits.tokens,
            "MYSQL_VIEW_RESOURCE_LIMIT",
        )
        need(type(node) is Node and id(node) not in seen, "MYSQL_VIEW_NODE_IDENTITY")
        seen.add(id(node))
        need(
            type(node.start) is int
            and type(node.end) is int
            and 0 <= node.start < node.end <= len(tokens)
        )
        need(type(node.children) is tuple)
        surface = []
        position = node.start
        for child in node.children:
            need(
                type(child) is Node and position <= child.start < child.end <= node.end,
                "MYSQL_VIEW_COVERAGE",
            )
            surface.extend(tokens[position : child.start])
            check(child, depth + 1)
            surface.append(child)
            position = child.end
        surface.extend(tokens[position : node.end])
        c = node.children
        words = [
            t.value.upper() if type(t) is Token and t.kind in ("word", "symbol") else t
            for t in surface
        ]
        rule = node.rule
        if rule == "name":
            need(not c)
            names[id(node)] = _names(tokens[node.start : node.end])
        elif rule == "star":
            need(not c)
            part = tokens[node.start : node.end]
            need(
                _word(part[-1], "*")
                and (len(part) == 1 or len(part) >= 3 and _word(part[-2], "."))
            )
            if len(part) > 1:
                _names(part[:-2])
        elif rule == "literal":
            need(
                not c
                and len(surface) == 1
                and (
                    tokens[node.start].kind in ("number", "string")
                    or words[0] in ("NULL", "TRUE", "FALSE")
                )
            )
        elif rule == "introduced":
            need(
                not c
                and len(surface) == 2
                and words[0]
                in ("_UTF8MB4", "_UTF8MB3", "_UTF8", "_BINARY", "_LATIN1", "N")
                and type(surface[1]) is Token
                and surface[1].kind == "string"
            )
        elif rule == "unary":
            need(
                len(c) == 1
                and expression(c[0])
                and len(words) == 2
                and words[0] in ("+", "-", "NOT")
                and words[1] is c[0]
            )
        elif rule == "binary":
            need(len(c) == 2 and all(expression(x) for x in c))
            need(
                len(words) == 3
                and words[0] is c[0]
                and words[2] is c[1]
                and words[1]
                in (
                    "OR",
                    "AND",
                    "=",
                    "<>",
                    "!=",
                    "<",
                    ">",
                    "<=",
                    ">=",
                    "<=>",
                    "+",
                    "-",
                    "*",
                    "/",
                    "%",
                    "DIV",
                    "MOD",
                )
            )
        elif rule == "is_null":
            need(
                len(c) == 1
                and expression(c[0])
                and words in ([c[0], "IS", "NULL"], [c[0], "IS", "NOT", "NULL"])
            )
        elif rule in ("group", "subquery", "query_group"):
            need(
                len(c) == 1
                and (expression(c[0]) if rule == "group" else c[0].rule in queries)
                and words == ["(", c[0], ")"]
            )
        elif rule == "cast":
            need(
                len(c) == 1
                and expression(c[0])
                and words
                in (
                    ["CAST", "(", c[0], "AS", "SIGNED", ")"],
                    ["CAST", "(", c[0], "AS", "SIGNED", "INTEGER", ")"],
                )
            )
        elif rule == "call":
            need(len(c) == 1 and c[0].rule == "name", "MYSQL_VIEW_UNQUALIFIED_CALL")
            need(
                c[0].end == c[0].start + 1
                and _word(tokens[c[0].start], "CURRENT_USER"),
                "MYSQL_VIEW_UNQUALIFIED_CALL",
            )
            need(words == [c[0], "(", ")"], "MYSQL_VIEW_UNQUALIFIED_CALL")
        elif rule in ("projection", "relation"):
            need(1 <= len(c) <= 2)
            need(
                (expression(c[0]) or c[0].rule == "star")
                if rule == "projection"
                else reference(c[0])
            )
            need(
                words == [c[0]]
                or len(c) == 2
                and reference(c[1])
                and len(names[id(c[1])]) == 1
                and words in ([c[0], c[1]], [c[0], "AS", c[1]])
            )
            if rule == "relation":
                path = names[id(c[0])]
                need(len(path) <= 2)
                references.append(
                    (node.start, view.key[0] if len(path) == 1 else path[0], path[-1])
                )
        elif rule == "derived":
            need(
                len(c) == 2
                and c[0].rule in queries
                and reference(c[1])
                and len(names[id(c[1])]) == 1
            )
            need(words in (["(", c[0], ")", c[1]], ["(", c[0], ")", "AS", c[1]]))
        elif rule == "where":
            need(len(c) == 1 and expression(c[0]) and words == [c[0]])
        elif rule == "select":
            need(words and words[0] == "SELECT")
            i = 1
            projections = 0
            while i < len(words) and _rule(words[i], "projection"):
                projections += 1
                i += 1
                if i < len(words) and words[i] == ",":
                    i += 1
                    need(i < len(words) and _rule(words[i], "projection"))
                else:
                    break
            need(projections > 0)
            if i < len(words) and words[i] == "FROM":
                i += 1
                need(i < len(words) and _rule(words[i], "relation", "derived"))
                i += 1
            if i < len(words) and words[i] == "WHERE":
                i += 1
                need(i < len(words) and _rule(words[i], "where"))
                i += 1
            need(i == len(words), "MYSQL_VIEW_COMPLETE_SELECT")
        elif rule == "union":
            need(
                len(c) == 2
                and all(x.rule in queries for x in c)
                and words == [c[0], "UNION", "ALL", c[1]]
            )
        elif rule == "view":
            need(
                node is view.tree
                and len(c) == 2
                and reference(c[0])
                and c[1].rule in queries
            )
            # Header fields are data tokens; verify their exact positions without
            # treating a quoted keyword/account name as a syntactic keyword.
            need(len(surface) == 16)
            expected = {
                0: "CREATE",
                1: "ALGORITHM",
                2: "=",
                4: "DEFINER",
                5: "=",
                7: "@",
                9: "SQL",
                10: "SECURITY",
                12: "VIEW",
                14: "AS",
            }
            need(all(_word(surface[i], text) for i, text in expected.items()))
            need(
                words[3] in ("UNDEFINED", "MERGE", "TEMPTABLE")
                and words[11] in ("DEFINER", "INVOKER")
            )
            need(
                all(
                    type(surface[i]) is Token
                    and surface[i].kind in ("id", "word", "string")
                    for i in (6, 8)
                )
            )
            need(surface[13] is c[0] and surface[15] is c[1])
        else:
            raise ViewSourceError("MYSQL_VIEW_UNKNOWN_PRODUCTION")

    check(view.tree)
    need(
        view.tree.rule == "view"
        and view.tree.start == 0
        and view.tree.end == len(tokens)
    )
    root_name = names[id(view.tree.children[0])]
    need(
        root_name == (view.key[1],) or root_name == view.key,
        "MYSQL_VIEW_OBJECT_IDENTITY",
    )
    refs = tuple(sorted(references))
    need(
        type(view.references) is tuple
        and view.references == refs
        and len(refs) <= limits.edges,
        "MYSQL_VIEW_DEPENDENCY_COVERAGE",
    )
    return refs


@dataclass(frozen=True, slots=True, eq=False)
class SourceObject:
    key: tuple
    kind: str
    engine: str | None
    columns: tuple
    view: ViewDefinition | None = field(repr=False)
    context: tuple = field(repr=False)
    native_definition: str = field(default="", repr=False)


def _verify_columns(view, by_key):
    tokens = lex(view.sql)

    def name(node):
        return _names(tokens[node.start : node.end])

    def matches(a, b):
        return a == b or a.isascii() and b.isascii() and a.lower() == b.lower()

    def expression(node, frames):
        if node.rule == "name":
            path = name(node)
            for frame in frames:
                found = [
                    (prefixes, columns)
                    for prefixes, columns in frame
                    if len(path) == 1 or path[:-1] in prefixes
                ]
                candidates = [
                    c for _, columns in found for c in columns if matches(path[-1], c)
                ]
                if candidates:
                    need(len(candidates) == 1, "MYSQL_VIEW_COLUMN_AMBIGUITY")
                    return
            raise ViewSourceError("MYSQL_VIEW_UNRESOLVED_COLUMN")
        if node.rule in ("literal", "introduced", "call"):
            return
        if node.rule == "subquery":
            query(node.children[0], frames)
            return
        for child in node.children:
            expression(child, frames)

    def query(node, outer=()):
        if node.rule == "query_group":
            return query(node.children[0], outer)
        if node.rule == "union":
            left, right = (query(c, outer) for c in node.children)
            need(len(left) == len(right), "MYSQL_VIEW_UNION_WIDTH")
            return left
        need(node.rule == "select")
        frame = []
        for relation in node.children:
            if relation.rule == "relation":
                parts = name(relation.children[0])
                key = (view.key[0], parts[0]) if len(parts) == 1 else parts
                obj = by_key.get(key)
                need(obj is not None, "MYSQL_VIEW_MISSING_DEPENDENCY")
                if len(relation.children) == 2:
                    prefixes = (name(relation.children[1]),)
                else:
                    prefixes = ((key[-1],), key)
                frame.append((prefixes, tuple(c[0] for c in obj.columns)))
            elif relation.rule == "derived":
                columns = query(relation.children[0])
                frame.append(((name(relation.children[1]),), columns))
        frames = (tuple(frame),) + outer
        labels = []
        for child in node.children:
            if child.rule == "projection":
                expr = child.children[0]
                if expr.rule == "star":
                    part = tokens[expr.start : expr.end]
                    prefix = () if len(part) == 1 else _names(part[:-2])
                    chosen = [
                        cols
                        for prefixes, cols in frame
                        if not prefix or prefix in prefixes
                    ]
                    need(
                        len(chosen) == 1 and len(child.children) == 1,
                        "MYSQL_VIEW_STAR_SCOPE",
                    )
                    labels.extend(chosen[0])
                    continue
                expression(expr, frames)
                if len(child.children) == 2:
                    labels.append(name(child.children[1])[0])
                else:
                    need(expr.rule == "name", "MYSQL_VIEW_OUTPUT_LABEL")
                    labels.append(name(expr)[-1])
            elif child.rule == "where":
                expression(child.children[0], frames)
        return tuple(labels)

    labels = query(view.tree.children[1])
    need(
        labels == tuple(c[0] for c in by_key[view.key].columns),
        "MYSQL_VIEW_OUTPUT_SCHEMA",
    )


def verify_closure(
    roots: tuple,
    objects: tuple[SourceObject, ...],
    context: tuple,
    *,
    limits=ViewLimits(),
):
    """Pure structural closure only. It cannot create a live metadata-lock receipt."""
    need(
        type(roots) is tuple
        and type(objects) is tuple
        and 0 < len(objects) <= limits.objects,
        "MYSQL_VIEW_OBJECT_LIMIT",
    )
    by_key = {}
    for item in objects:
        if type(item) is not SourceObject:
            raise ViewSourceError("MYSQL_VIEW_OBJECT_IDENTITY")
        need(
            item.key not in by_key and item.context == context,
            "MYSQL_VIEW_OBJECT_IDENTITY",
        )
        need(
            type(item.columns) is tuple
            and item.columns
            and all(
                type(c) is tuple and len(c) == 3 and all(type(v) is str for v in c)
                for c in item.columns
            ),
            "MYSQL_VIEW_COLUMN_METADATA",
        )
        need(
            len({c[0].casefold() for c in item.columns}) == len(item.columns),
            "MYSQL_VIEW_COLUMN_AMBIGUITY",
        )
        by_key[item.key] = item
    active, visited, order, edges = set(), set(), [], []

    def visit(key, depth=0):
        need(depth <= limits.depth and key not in active, "MYSQL_VIEW_DEPENDENCY_CYCLE")
        need(key in by_key, "MYSQL_VIEW_MISSING_DEPENDENCY")
        if key in visited:
            return
        active.add(key)
        order.append(key)
        obj = by_key[key]
        if obj.kind == "BASE TABLE":
            need(obj.engine == "InnoDB" and obj.view is None, "MYSQL_SOURCE_ENGINE")
            need(
                not any("VIRTUAL GENERATED" in c[1].upper() for c in obj.columns),
                "MYSQL_SOURCE_READ_TIME_GENERATED",
            )
        elif obj.kind == "VIEW":
            need(
                obj.engine is None
                and type(obj.view) is ViewDefinition
                and obj.view.key == key,
                "MYSQL_VIEW_OBJECT_IDENTITY",
            )
            for site, schema, name in verify_view(obj.view, limits=limits):
                edges.append((key, site, (schema, name)))
                need(len(edges) <= limits.edges, "MYSQL_VIEW_EDGE_LIMIT")
                visit((schema, name), depth + 1)
            _verify_columns(obj.view, by_key)
        else:
            raise ViewSourceError("MYSQL_SOURCE_KIND")
        active.remove(key)
        visited.add(key)

    for root in roots:
        visit(root)
    need(
        tuple(order) == tuple(x.key for x in objects),
        "MYSQL_VIEW_COMPLETE_OBJECT_INVENTORY",
    )
    return tuple(edges)


def security_paths(roots, objects, account, roles, *, limits=ViewLimits()):
    """Effective CURRENT_USER for EVERY invocation path, including repeated views.

    INVOKER inherits its caller, which can itself be a definer. DEFINER changes
    the account and delegates applicable default-role privileges to the native
    authorizer. No caller SELECT on a definer's base rows is inferred here.
    """
    by_key = {obj.key: obj for obj in objects}
    paths = []

    def visit(key, inherited, role_basis, path):
        need(
            len(path) <= limits.depth and len(paths) < limits.edges,
            "MYSQL_VIEW_SECURITY_LIMIT",
        )
        obj = by_key[key]
        if obj.view is None:
            paths.append((path, key, "BASE", inherited, role_basis))
            return
        tokens = lex(obj.view.sql, limits)
        security = tokens[11].value.upper()
        definer = tokens[6].value + "@" + tokens[8].value
        effective = definer if security == "DEFINER" else inherited
        effective_roles = (
            "NATIVE_DEFINER_DEFAULT_ROLES" if security == "DEFINER" else role_basis
        )
        paths.append((path, key, security, effective, effective_roles))
        for site, schema, name in obj.view.references:
            visit((schema, name), effective, effective_roles, path + (site,))

    for position, key in enumerate(roots):
        visit(key, account, roles, (position,))
    return tuple(paths)
