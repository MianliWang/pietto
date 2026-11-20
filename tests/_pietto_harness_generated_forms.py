"""Bounded, seeded generation of opened forms with an independent oracle.

The generator writes, for one integer seed and profile, a shape ``Row`` with
an ``id`` key and up to four other fields, two sources ``t`` and ``u`` of it,
and one query ``q`` in one of three forms: a row form over ``t`` (``let``
values, ``where``, ``select``, ``order by``, ``limit``); an aggregate form
over ``t`` (``where``, ``group by``, ``select``, ``order by``, ``limit``); or
a JOIN form that joins ``u`` to ``t`` as ``r`` (INNER, LEFT, RIGHT, CROSS and,
in the broad profile, FULL on ``Int`` equalities) and reads qualified fields
(``where``, ``select``, ``order by``, ``limit``). Expressions are built by the
type they must have, from fields, literals, unary ``-``, ``+ - *``, ``abs``,
``coalesce``, ``lower``, ``upper``, comparisons, ``is None``, ``and`` and
``or``, with ``count``, ``min``, ``max``, ``sum`` and ``avg`` in the aggregate
form. ``BOUNDS`` bounds every size, and a seed always yields the same case.
Its ``depth`` is a recursion budget: under it an expression nests at most
three operators, and a ``where`` four.

Each case renders as a single file for PostgreSQL and for MySQL, and as an
explicit-module project with an emission contract. The broad profile uses
every production above; the forms it writes are opened in both single-file
targets and in PostgreSQL projects. The narrow profile keeps to field
reads, renaming lets, ``is None`` tests, comparisons of non-``Float`` field
reads in ``where`` and JOIN ``on``, ``and`` and ``or`` of those tests,
``count``, ``min`` and ``max`` of ``Int`` or ``Date`` fields, ``avg`` of
``Int`` fields and no FULL JOIN; its forms are also opened in MySQL projects
(docs/capabilities.md). In both, a WHERE after a JOIN holds no built-in call
(docs/language.md), and a JOIN ``on`` equality compares no ``Bool`` or
``Float`` pair; the broad profile compares ``Float`` values in an ``on`` only
inside an ``or`` operand, which PostgreSQL projects admit.

The oracle restates the result types and nullability of
docs/spec/nullability-propagation-contract-v1.md (Nullability v1: WHERE never
narrows) and of the JOIN rules of docs/language.md (Single-file JOINs). It
reads only the case and never imports pietto; the test owner compares the
product's public outputs with it.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
from typing import Any

PROFILES = ("broad", "narrow")
FORMS = ("row", "aggregate", "join")
TYPES = ("Int", "Float", "Text", "Bool", "Date")
# Campaign bounds: fields besides id, lets, select items, expression budget,
# GROUP BY keys, aggregates, JOIN `on` conjuncts and the largest LIMIT.
BOUNDS = {
    "fields": 4,
    "lets": 2,
    "items": 4,
    "depth": 2,
    "keys": 2,
    "aggregates": 3,
    "conjuncts": 2,
    "limit": 5,
}
NON_NULL, NULLABLE, UNKNOWN = "non_null", "nullable", "unknown"
_LITERALS = {"Int": ("0", "1", "7"), "Float": ("0.5", "2.0"), "Text": ('"a"', '"Zz"')}
_ORDERED = ("Int", "Float", "Text", "Date")
_MIN_MAX = {"broad": ("Int", "Float", "Date"), "narrow": ("Int", "Date")}
_AVERAGED = {"broad": ("Int", "Float"), "narrow": ("Int",)}
_KEY_TYPES = ("Int", "Text", "Bool", "Date")
_JOINS = {
    "broad": ("inner", "left", "right", "full", "cross"),
    "narrow": ("inner", "left", "right", "cross"),
}
# PostgreSQL and MySQL (storage, domain) per logical type (docs/project-package.md).
_TEXT_DOMAIN = {"kind": "text", "max_characters": 16, "padding": "NO PAD"}
_INT_DOMAIN = {"kind": "int_range", "min": "-1000", "max": "1000"}
_FLOAT_DOMAIN = {"kind": "finite_float", "format": "binary64"}
_REPRESENTATION = {
    "postgres": {
        "Int": ({"kind": "pg_int8"}, _INT_DOMAIN),
        "Float": ({"kind": "pg_float8"}, _FLOAT_DOMAIN),
        "Text": (
            {"kind": "pg_text"},
            {**_TEXT_DOMAIN, "encoding": "UTF8", "collation": "C"},
        ),
        "Bool": ({"kind": "pg_bool"}, {"kind": "bool01"}),
        "Date": ({"kind": "pg_date"}, {"kind": "date"}),
    },
    "mysql": {
        "Int": ({"kind": "my_bigint"}, _INT_DOMAIN),
        "Float": ({"kind": "my_double"}, _FLOAT_DOMAIN),
        "Text": (
            {"kind": "my_varchar", "length": 16},
            {**_TEXT_DOMAIN, "encoding": "utf8mb4", "collation": "utf8mb4_0900_bin"},
        ),
        "Bool": ({"kind": "my_bool01"}, {"kind": "bool01"}),
        "Date": ({"kind": "my_date"}, {"kind": "date"}),
    },
}
_ENVIRONMENT = {
    "postgres": (("client_encoding", "UTF8"), ("identifier_case", "quoted_exact")),
    "mysql": (
        ("client_encoding", "utf8mb4"),
        ("identifier_case", "lower_case_table_names=0"),
    ),
}
_RELEASE = {"postgres": "18.6", "mysql": "8.4.12"}


@dataclass(frozen=True, slots=True)
class Case:
    seed: int
    profile: str
    form: str
    fields: tuple[tuple[str, str, bool], ...]  # (name, type, nullable), id first
    join: tuple[str, tuple | None] | None  # (kind, on) of the JOIN form
    lets: tuple[tuple[str, tuple], ...]
    where: tuple | None
    keys: tuple[str, ...]  # GROUP BY fields
    items: tuple[tuple[str, tuple], ...]  # (output name, expression)
    order: tuple[tuple[str, bool], ...]  # (key, descending)
    limit: int | None


def generate(seed: int, profile: str) -> Case:
    """The case of ``seed`` in ``profile``: deterministic and bounded."""
    if profile not in PROFILES:
        raise ValueError(profile)
    rng = random.Random(f"{profile}:{seed}")
    fields = [("id", "Int", False)]
    for i in range(rng.randint(1, BOUNDS["fields"])):
        fields.append((f"f{i}", rng.choice(TYPES), rng.random() < 0.5))
    form = rng.choice(FORMS)
    bindings = ("t", "r") if form == "join" else ("",)
    columns = [
        (f"{b}.{name}" if b else name, kind)
        for b in bindings
        for name, kind, _ in fields
    ]
    gen = _Generator(rng, profile, columns)
    join = gen.join() if form == "join" else None
    gen.focus = _reads(join[1]) if join and join[1] else []
    limit = rng.randint(1, BOUNDS["limit"]) if rng.random() < 0.4 else None
    keys: tuple[str, ...] = ()
    lets: tuple[tuple[str, tuple], ...] = ()
    if form == "aggregate":
        candidates = [name for name, kind, _ in fields if kind in _KEY_TYPES]
        keys = tuple(
            rng.sample(candidates, rng.randint(0, min(BOUNDS["keys"], len(candidates))))
        )
        items = [(key, ("field", key)) for key in keys]
        items += [
            (f"a{i}", gen.aggregate())
            for i in range(rng.randint(1, BOUNDS["aggregates"]))
        ]
        order = tuple((key, rng.random() < 0.3) for key in keys if rng.random() < 0.7)
        limit = limit if keys else None
    else:
        if form == "row":
            lets = tuple(
                (f"l{i}", gen.value()) for i in range(rng.randint(0, BOUNDS["lets"]))
            )
            gen.lets = lets
        items, used = [], set()
        for i in range(rng.randint(1, BOUNDS["items"])):
            name, expression = gen.item(i, qualified=form == "join")
            if name not in used:
                used.add(name)
                items.append((name, expression))
        ordered = [
            name
            for name, kind in columns
            if kind in _ORDERED and not name.endswith("id")
        ]
        order = (
            ((rng.choice(ordered), rng.random() < 0.5),)
            if ordered and rng.random() < 0.5
            else ()
        )
        order += ((columns[0][0], rng.random() < 0.3),)
    # A WHERE after a JOIN admits no built-in call yet (docs/language.md).
    where = (
        gen.predicate(BOUNDS["depth"], plain=form == "join")
        if rng.random() < 0.6
        else None
    )
    read = [name for _, expression in items for name in _reads(expression)]
    # Bias toward the rule that WHERE never narrows: test a field the query reads.
    if read and rng.random() < 0.3:
        test = ("isnone", ("field", rng.choice(read)), True)
        where = test if where is None else ("bool", "and", test, where)
    return Case(
        seed,
        profile,
        form,
        tuple(fields),
        join,
        lets,
        where,
        keys,
        tuple(items),
        order,
        limit,
    )


def _reads(expression: tuple) -> list[str]:
    """The fields ``expression`` reads, with repeats, in reading order."""
    if expression[0] == "field":
        return [expression[1]]
    return [
        name
        for part in expression[1:]
        if isinstance(part, tuple)
        for name in _reads(part)
    ]


class _Generator:
    def __init__(
        self, rng: random.Random, profile: str, columns: list[tuple[str, str]]
    ) -> None:
        self.rng, self.profile, self.columns = rng, profile, columns
        self.lets: tuple[tuple[str, tuple], ...] = ()
        self.focus: list[str] = []  # fields a JOIN `on` reads, favoured by select items

    def _of(self, kind: str) -> list[str]:
        return [name for name, column_kind in self.columns if column_kind == kind]

    def _read(self) -> tuple:
        return ("field", self.rng.choice(self.columns)[0])

    def value(self) -> tuple:
        """A let value: any expression in broad, a field read in narrow."""
        if self.profile == "narrow":
            return self._read()
        return self.expression(self.rng.choice(TYPES), BOUNDS["depth"])

    def item(self, index: int, *, qualified: bool) -> tuple[str, tuple]:
        roll = self.rng.random()
        if self.lets and roll < 0.3:
            name = self.rng.choice(self.lets)[0]
            return name, ("let", name)
        if roll < 0.6 or self.profile == "narrow" and roll < 0.85:
            read = (
                ("field", self.rng.choice(self.focus))
                if self.focus and roll < 0.45
                else self._read()
            )
            return (f"o{index}" if qualified else read[1]), read
        if self.profile == "narrow":
            return f"o{index}", ("isnone", self._read(), self.rng.random() < 0.5)
        return f"o{index}", self.expression(self.rng.choice(TYPES), BOUNDS["depth"])

    def expression(self, kind: str, depth: int) -> tuple:
        """A broad expression of type ``kind`` within a recursion budget ``depth``."""
        rng = self.rng
        leaves = [("field", name) for name in self._of(kind)]
        leaves += [("lit", kind, text) for text in _LITERALS.get(kind, ())]
        if kind == "Bool":
            leaves += [("lit", "Bool", "True"), ("lit", "Bool", "False")]
        if kind == "Date" and not leaves:
            kind = "Int"  # no Date field and no Date literal: an Int instead
        if depth == 0 or rng.random() < 0.35 or kind == "Date":
            if leaves:
                return rng.choice(leaves)
            return ("field", self.columns[0][0])
        sub = depth - 1
        if kind in ("Int", "Float"):
            choice = rng.choice(("neg", "arith", "abs", "coalesce"))
            if choice == "neg":
                return ("neg", self.expression(kind, sub))
            if choice == "arith":
                return (
                    "arith",
                    rng.choice("+-*"),
                    self.expression(kind, sub),
                    self.expression(kind, sub),
                )
            if choice == "abs":
                return ("call", "abs", self.expression(kind, sub))
            return (
                "call",
                "coalesce",
                self.expression(kind, sub),
                self.expression(kind, sub),
            )
        if kind == "Text":
            choice = rng.choice(("lower", "upper", "coalesce"))
            if choice == "coalesce":
                return (
                    "call",
                    "coalesce",
                    self.expression("Text", sub),
                    self.expression("Text", sub),
                )
            return ("call", choice, self.expression("Text", sub))
        return self.predicate(depth)

    def predicate(self, depth: int, *, plain: bool = False) -> tuple:
        """A Bool expression; narrow, or ``plain``, compares field reads only."""
        rng = self.rng
        roll = rng.random()
        if depth > 0 and roll < 0.25:
            operands = (
                self.predicate(depth - 1, plain=plain),
                self.predicate(depth - 1, plain=plain),
            )
            return ("bool", rng.choice(("and", "or")), *operands)
        if roll < 0.5:
            return ("isnone", self._read(), rng.random() < 0.5)
        kinds = [kind for kind in _ORDERED if self._of(kind)]
        if self.profile == "narrow":
            kinds = [kind for kind in kinds if kind != "Float"]
        kind = rng.choice(kinds)
        left = ("field", rng.choice(self._of(kind)))
        if self.profile == "narrow" or plain:
            right = ("field", rng.choice(self._of(kind)))
        else:
            right = self.expression(kind, max(depth - 1, 0))
        return ("cmp", rng.choice(("==", "!=", "<", "<=", ">", ">=")), left, right)

    def join(self) -> tuple[str, tuple | None]:
        """A JOIN of ``r``: its kind and its ``on`` (None for CROSS)."""
        rng = self.rng
        kind = rng.choice(_JOINS[self.profile])
        if kind == "cross":
            return kind, None
        fields = [
            name.partition(".")[2] for name, _ in self.columns if name.startswith("t.")
        ]
        types = {name.partition(".")[2]: kind for name, kind in self.columns}
        # Project ON equalities: no Bool (docs/language.md) and no Float pair;
        # a FULL JOIN on Int keys only (docs/capabilities.md).
        keyed = ("Int",) if kind == "full" else ("Int", "Text", "Date")
        equal = [name for name in fields[1:] if types[name] in keyed] or ["id"]
        conjuncts = []
        # shortcut: no `is not None` conjunct in an INNER JOIN `on`, which projects
        # BLOCK with PIE-B1002 `join_output_nullability_drift` while docs/language.md
        # states that only for a Bool field; add it once the two agree.
        tests = kind != "inner"
        for _ in range(rng.randint(1, BOUNDS["conjuncts"])):
            roll = rng.random()
            if kind == "full" or roll < 0.6 or not tests and self.profile == "narrow":
                name = rng.choice(equal)
                conjuncts.append(
                    ("cmp", "==", ("field", f"t.{name}"), ("field", f"r.{name}"))
                )
            elif tests and (roll < 0.8 or self.profile == "narrow"):
                conjuncts.append(
                    ("isnone", ("field", f"r.{rng.choice(fields[1:] or fields)}"), True)
                )
            else:
                conjuncts.append(("bool", "or", self.predicate(0), self.predicate(0)))
        on = conjuncts[0]
        for conjunct in conjuncts[1:]:
            on = ("bool", "and", on, conjunct)
        return kind, on

    def aggregate(self) -> tuple:
        names = {kind: self._of(kind) for kind in TYPES}
        options: list[tuple] = [("agg", "count", None)]
        options += [("agg", "count", ("field", name)) for name, _ in self.columns]
        for function in ("min", "max"):
            options += [
                ("agg", function, ("field", n))
                for k in _MIN_MAX[self.profile]
                for n in names[k]
            ]
        options += [
            ("agg", "avg", ("field", n))
            for k in _AVERAGED[self.profile]
            for n in names[k]
        ]
        if self.profile == "broad":
            options += [
                ("agg", "sum", ("field", n)) for k in ("Int", "Float") for n in names[k]
            ]
        return self.rng.choice(options)


# ---- the oracle: types and nullability from the case alone ----


def _proved(on: tuple | None) -> set[str]:
    """Fields an INNER JOIN's ``on`` proves non-null: the direct field leaves
    of its top-level ``and`` operands (a Bool field, a comparison's field
    operand, ``field is not None``); ``or`` proves nothing."""
    if on is None:
        return set()
    if on[0] == "bool":
        return _proved(on[2]) | _proved(on[3]) if on[1] == "and" else set()
    if on[0] == "field":
        return {on[1]}
    if on[0] == "cmp":
        return {operand[1] for operand in on[2:] if operand[0] == "field"}
    if on[0] == "isnone" and on[2] and on[1][0] == "field":
        return {on[1][1]}
    return set()


def _column(case: Case, name: str) -> tuple[str, str]:
    binding, _, field = name.rpartition(".")
    _, kind, nullable = next(f for f in case.fields if f[0] == field)
    state = NULLABLE if nullable else NON_NULL
    if case.join is not None:
        join, on = case.join
        extended = {"left": ("r",), "right": ("t",), "full": ("t", "r")}.get(join, ())
        if binding in extended:
            state = NULLABLE
        elif join == "inner" and name in _proved(on):
            state = NON_NULL
    return kind, state


def typed(case: Case, expression: tuple) -> tuple[str, str]:
    """(type, nullability) of ``expression`` under Nullability v1."""
    tag = expression[0]
    if tag == "field":
        return _column(case, expression[1])
    if tag == "let":
        return typed(case, dict(case.lets)[expression[1]])
    if tag == "lit":
        return expression[1], NON_NULL
    if tag == "neg":
        return typed(case, expression[1])
    if tag == "arith":
        return typed(case, expression[2])[0], UNKNOWN
    if tag == "call":
        arguments = [typed(case, argument) for argument in expression[2:]]
        states = {state for _, state in arguments}
        if expression[1] == "coalesce":
            order = (NON_NULL, UNKNOWN, NULLABLE)
        else:
            order = (NULLABLE, UNKNOWN, NON_NULL)
        return arguments[0][0], next(state for state in order if state in states)
    if tag in ("cmp", "bool"):
        return "Bool", UNKNOWN
    if tag == "isnone":
        return "Bool", NON_NULL
    if tag == "agg":
        if expression[1] == "count":
            return "Int", NON_NULL
        kind = typed(case, expression[2])[0]
        return ("Float" if expression[1] == "avg" else kind), NULLABLE
    raise ValueError(tag)


def expected_columns(case: Case) -> tuple[tuple[str, str, str], ...]:
    """The query's (name, type, nullability) columns in select order."""
    return tuple((name, *typed(case, expression)) for name, expression in case.items)


# ---- rendering ----


def _text(expression: tuple) -> str:
    tag = expression[0]
    if tag in ("field", "let"):
        return expression[1]
    if tag == "lit":
        return expression[2]
    if tag == "neg":
        return f"-({_text(expression[1])})"
    if tag in ("arith", "cmp", "bool"):
        return f"({_text(expression[2])} {expression[1]} {_text(expression[3])})"
    if tag == "call":
        return f"{expression[1]}({', '.join(_text(a) for a in expression[2:])})"
    if tag == "isnone":
        return f"({_text(expression[1])} is {'not ' if expression[2] else ''}None)"
    if tag == "agg":
        return f"{expression[1]}({_text(expression[2]) if expression[2] else ''})"
    raise ValueError(tag)


def module_text(case: Case, target: str) -> str:
    """The case's module; ``t`` and ``u`` read ``target``'s ``app.t`` and ``app.u``."""
    lines = ["shape Row:"]
    lines += [
        f"    {name}: {kind}{' | None' if nullable else ''}"
        for name, kind, nullable in case.fields
    ]
    lines += [
        "",
        f'source t: Row = {target}.table("app.t")',
        f'source u: Row = {target}.table("app.u")',
    ]
    lines += ["", "query q:", "    from t"]
    if case.join is not None:
        kind, on = case.join
        lines += [
            "    let r = u",
            f"    {kind} join r" + (f" on {_text(on)}" if on else ""),
        ]
    lines += [f"    let {name} = {_text(expression)}" for name, expression in case.lets]
    if case.where is not None:
        lines.append(f"    where {_text(case.where)}")
    if case.keys:
        lines += ["    group by:"] + [f"        {key}" for key in case.keys]
    lines.append("    select:")
    for name, expression in case.items:
        bare = expression[0] in ("field", "let") and expression[1] == name
        lines.append(
            f"        {name}" if bare else f"        {name} = {_text(expression)}"
        )
    if case.order:
        lines += ["    order by:"] + [
            f"        {key}{' desc' if desc else ''}" for key, desc in case.order
        ]
    if case.limit is not None:
        lines.append(f"    limit {case.limit}")
    return "\n".join(lines) + "\n"


def contract(case: Case, target: str) -> str:
    """The project's emission contract for ``target`` (canonical JSON)."""
    fields = []
    for ordinal, (name, kind, nullable) in enumerate(case.fields):
        storage, domain = _REPRESENTATION[target][kind]
        representation = {"storage": storage, "domain": domain, "nullable": nullable}
        fields.append(
            {
                "ordinal": ordinal,
                "name": name,
                "column": name,
                "representation": representation,
            }
        )
    environment = (("operator_environment", "builtin_only"),) + _ENVIRONMENT[target]
    document: dict[str, Any] = {
        "format": "pietto.emission-contract.v1",
        "target": {"family": target, "release": _RELEASE[target]},
        "sources": [
            {
                "selector": {"module": "main.pietto", "kind": "source", "name": source},
                "relation": {"namespace": "app", "name": source},
                "scan": "relation_rows",
                "fields": fields,
                "premises": [
                    {"key": key, "scope": "source", "value": True}
                    for key in ("row_domain_matches", "read_only_object")
                ],
            }
            for source in ("t", "u")
        ],
        "environment": [
            {"key": k, "scope": "statement", "value": v} for k, v in environment
        ],
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def project_files(case: Case, target: str) -> dict[str, str]:
    """An explicit-module project's files: configuration, module and contract."""
    return {
        "pietto.toml": 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        "main.pietto": module_text(case, target),
        "contract.json": contract(case, target),
    }
