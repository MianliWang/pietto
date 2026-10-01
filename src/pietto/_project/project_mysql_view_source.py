"""Bounded native CREATE VIEW syntax. This data model grants no live authority."""

from dataclasses import dataclass, field
import re

__all__: tuple[str, ...] = ()


class ViewSourceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ViewLimits:
    bytes: int = 262144
    tokens: int = 32768
    depth: int = 48
    objects: int = 128
    edges: int = 1024


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


@dataclass(frozen=True, slots=True, eq=False)
class Node:
    rule: str
    start: int
    end: int
    children: tuple = field(default=(), repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ViewDefinition:
    key: tuple[str, str]
    sql: str = field(repr=False)
    charset: str
    collation: str
    tree: Node = field(repr=False)
    references: tuple
    sql_mode: str = "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION"
    quote_show_create: int = 1


def lex(sql, limits=ViewLimits()):
    """Trusted shared base: exact spans, quoting/escapes, resource limits, no comments.

    The native profile requires utf8mb4, quote-show-create on, and the selected
    SQL mode without ANSI_QUOTES or NO_BACKSLASH_ESCAPES. No SQL is emitted here.
    """
    if type(sql) is not str or not sql or len(sql.encode("utf-8")) > limits.bytes:
        raise ViewSourceError("MYSQL_VIEW_DEFINITION_SIZE")
    tokens = []
    i = depth = 0
    while i < len(sql):
        if sql[i].isspace():
            i += 1
            continue
        start = i
        c = sql[i]
        if (
            c == "\0"
            or c == "#"
            or sql.startswith("/*", i)
            or (sql.startswith("--", i) and (i + 2 == len(sql) or sql[i + 2].isspace()))
        ):
            raise ViewSourceError("MYSQL_VIEW_COMMENT_OR_CONTROL")
        if c in ("`", "'", '"'):
            quote = c
            value = []
            i += 1
            while i < len(sql):
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        value.append(quote)
                        i += 2
                        continue
                    i += 1
                    break
                if sql[i] == "\\" and quote != "`":
                    i += 1
                    if i == len(sql):
                        raise ViewSourceError("MYSQL_VIEW_QUOTE")
                    value.append(
                        {
                            "0": "\0",
                            "n": "\n",
                            "r": "\r",
                            "t": "\t",
                            "b": "\b",
                            "Z": "\x1a",
                        }.get(sql[i], sql[i])
                    )
                    i += 1
                else:
                    value.append(sql[i])
                    i += 1
            else:
                raise ViewSourceError("MYSQL_VIEW_QUOTE")
            kind, text = ("id" if quote == "`" else "string"), "".join(value)
            if kind == "id" and (not text or "\0" in text):
                raise ViewSourceError("MYSQL_VIEW_IDENTIFIER")
        elif c.isascii() and c.isdigit():
            match = re.match(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", sql[i:])
            assert match is not None
            text = match.group()
            i += len(text)
            if i < len(sql) and (sql[i].isalpha() or sql[i] in ("_", "$")):
                raise ViewSourceError("MYSQL_VIEW_NUMERIC_TOKEN")
            kind = "number"
        elif c.isalpha() or c in ("_", "$"):
            i += 1
            while i < len(sql) and (sql[i].isalnum() or sql[i] in ("_", "$")):
                i += 1
            kind, text = "word", sql[start:i]
        else:
            text = next(
                (x for x in ("<=>", "<=", ">=", "<>", "!=") if sql.startswith(x, i)), c
            )
            if text not in (
                "<=>",
                "<=",
                ">=",
                "<>",
                "!=",
                "=",
                "<",
                ">",
                "+",
                "-",
                "*",
                "/",
                "%",
                ".",
                ",",
                "(",
                ")",
                "@",
            ):
                raise ViewSourceError("MYSQL_VIEW_TOKEN")
            kind = "symbol"
            i += len(text)
            depth += (text == "(") - (text == ")")
            if depth < 0 or depth > limits.depth:
                raise ViewSourceError("MYSQL_VIEW_NESTING")
        tokens.append(Token(kind, text, start, i))
        if len(tokens) > limits.tokens:
            raise ViewSourceError("MYSQL_VIEW_TOKEN_LIMIT")
    if depth:
        raise ViewSourceError("MYSQL_VIEW_NESTING")
    return tuple(tokens)


class _Parser:
    def __init__(self, tokens, depth):
        self.tokens = tokens
        self.depth_limit = depth
        self.i = 0

    def at(self, value):
        return (
            self.i < len(self.tokens)
            and self.tokens[self.i].kind != "id"
            and self.tokens[self.i].value.upper() == value
        )

    def take(self, value):
        if not self.at(value):
            raise ViewSourceError("MYSQL_VIEW_SYNTAX")
        self.i += 1

    def name(self, maximum=3):
        start = self.i
        for n in range(maximum):
            if self.i >= len(self.tokens) or self.tokens[self.i].kind not in (
                "id",
                "word",
            ):
                raise ViewSourceError("MYSQL_VIEW_IDENTIFIER")
            self.i += 1
            if not self.at("."):
                return Node("name", start, self.i)
            self.i += 1
            if self.at("*"):
                self.i += 1
                return Node("star", start, self.i)
        raise ViewSourceError("MYSQL_VIEW_QUALIFICATION")

    def expression(self, minimum=0, depth=0):
        if depth > self.depth_limit:
            raise ViewSourceError("MYSQL_VIEW_NESTING")
        start = self.i
        if self.at("+") or self.at("-") or self.at("NOT"):
            self.i += 1
            node = Node("unary", start, 0, (self.expression(6, depth + 1),))
            node = Node(node.rule, start, self.i, node.children)
        elif self.at("("):
            self.i += 1
            query = self.at("SELECT")
            child = self.query() if query else self.expression(0, depth + 1)
            self.take(")")
            node = Node("subquery" if query else "group", start, self.i, (child,))
        elif self.at("CAST"):
            self.i += 1
            self.take("(")
            child = self.expression(0, depth + 1)
            self.take("AS")
            self.take("SIGNED")
            if self.at("INTEGER"):
                self.i += 1
            self.take(")")
            node = Node("cast", start, self.i, (child,))
        elif self.i < len(self.tokens) and (
            self.tokens[self.i].kind in ("number", "string")
            or any(self.at(x) for x in ("NULL", "TRUE", "FALSE"))
        ):
            self.i += 1
            node = Node("literal", start, self.i)
        elif (
            self.i + 1 < len(self.tokens)
            and self.tokens[self.i].kind == "word"
            and self.tokens[self.i].value.lower()
            in ("_utf8mb4", "_utf8mb3", "_utf8", "_binary", "_latin1", "n")
            and self.tokens[self.i + 1].kind == "string"
        ):
            self.i += 2
            node = Node("introduced", start, self.i)
        elif self.at("*"):
            self.i += 1
            node = Node("star", start, self.i)
        else:
            name = self.name()
            if self.at("("):
                self.i += 1
                children = [name]
                if not self.at(")"):
                    children.append(self.expression(0, depth + 1))
                    while self.at(","):
                        self.i += 1
                        children.append(self.expression(0, depth + 1))
                self.take(")")
                node = Node("call", start, self.i, tuple(children))
            else:
                node = name
        precedence = {
            "OR": 1,
            "AND": 2,
            "=": 3,
            "<>": 3,
            "!=": 3,
            "<": 3,
            ">": 3,
            "<=": 3,
            ">=": 3,
            "<=>": 3,
            "+": 4,
            "-": 4,
            "*": 5,
            "/": 5,
            "%": 5,
            "DIV": 5,
            "MOD": 5,
        }
        while self.i < len(self.tokens):
            if self.at("IS") and minimum <= 3:
                self.i += 1
                if self.at("NOT"):
                    self.i += 1
                self.take("NULL")
                node = Node("is_null", start, self.i, (node,))
                continue
            op = (
                self.tokens[self.i].value.upper()
                if self.tokens[self.i].kind != "id"
                else ""
            )
            priority = precedence.get(op, 0)
            if priority == 0 or priority < minimum:
                break
            self.i += 1
            right = self.expression(priority + 1, depth + 1)
            node = Node("binary", start, self.i, (node, right))
        return node

    def alias(self):
        if self.at("AS"):
            self.i += 1
            return self.name(1)
        if (
            self.i < len(self.tokens)
            and self.tokens[self.i].kind in ("id", "word")
            and not any(self.at(k) for k in ("FROM", "WHERE", "UNION"))
        ):
            return self.name(1)
        return None

    def select(self):
        start = self.i
        if self.at("("):
            self.i += 1
            q = self.query()
            self.take(")")
            return Node("query_group", start, self.i, (q,))
        self.take("SELECT")
        children = []
        while True:
            begin = self.i
            expression = self.expression()
            alias = self.alias()
            children.append(
                Node(
                    "projection",
                    begin,
                    self.i,
                    (expression,) + (() if alias is None else (alias,)),
                )
            )
            if not self.at(","):
                break
            self.i += 1
        if self.at("FROM"):
            self.i += 1
            begin = self.i
            if self.at("("):
                self.i += 1
                q = self.query()
                self.take(")")
                alias = self.alias()
                if alias is None:
                    raise ViewSourceError("MYSQL_VIEW_DERIVED_ALIAS")
                relation = Node("derived", begin, self.i, (q, alias))
            else:
                name = self.name(2)
                alias = self.alias()
                relation = Node(
                    "relation",
                    begin,
                    self.i,
                    (name,) + (() if alias is None else (alias,)),
                )
            children.append(relation)
        if self.at("WHERE"):
            self.i += 1
            children.append(Node("where", self.i, self.i, ()))
            expr = self.expression()
            children[-1] = Node("where", expr.start, expr.end, (expr,))
        return Node("select", start, self.i, tuple(children))

    def query(self):
        node = self.select()
        while self.at("UNION"):
            self.i += 1
            self.take("ALL")
            right = self.select()
            node = Node("union", node.start, self.i, (node, right))
        return node

    def view(self):
        self.take("CREATE")
        self.take("ALGORITHM")
        self.take("=")
        if not any(self.at(x) for x in ("UNDEFINED", "MERGE", "TEMPTABLE")):
            raise ViewSourceError("MYSQL_VIEW_ALGORITHM")
        self.i += 1
        self.take("DEFINER")
        self.take("=")
        for marker in ("@", "SQL"):
            if self.i >= len(self.tokens) or self.tokens[self.i].kind not in (
                "id",
                "word",
                "string",
            ):
                raise ViewSourceError("MYSQL_VIEW_DEFINER")
            self.i += 1
            self.take(marker)
        self.take("SECURITY")
        if not self.at("DEFINER") and not self.at("INVOKER"):
            raise ViewSourceError("MYSQL_VIEW_SECURITY")
        self.i += 1
        self.take("VIEW")
        name = self.name(2)
        self.take("AS")
        query = self.query()
        if self.i != len(self.tokens):
            raise ViewSourceError("MYSQL_VIEW_TRAILING_SYNTAX")
        return Node("view", 0, self.i, (name, query))


def recognize_view(
    key, sql, *, charset="utf8mb4", collation="utf8mb4_0900_bin", limits=ViewLimits()
):
    tokens = lex(sql, limits)
    tree = _Parser(tokens, limits.depth).view()
    refs = []

    pending = [tree]
    while pending:
        node = pending.pop()
        if node.rule == "relation":
            name = node.children[0]
            values = tuple(
                t.value
                for t in tokens[name.start : name.end]
                if t.kind in ("id", "word")
            )
            refs.append(
                (node.start, key[0] if len(values) == 1 else values[0], values[-1])
            )
        pending.extend(reversed(node.children))

    if len(refs) > limits.edges:
        raise ViewSourceError("MYSQL_VIEW_EDGE_LIMIT")
    return ViewDefinition(key, sql, charset, collation, tree, tuple(refs))
