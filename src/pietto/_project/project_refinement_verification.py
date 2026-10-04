"""Independent correspondence of private native syntax to original live facts.

No refinement constructor or renderer is called here. Closed rule checks consume
all native CTEs, and a separate byte recognizer checks actual submitted syntax.
"""

from dataclasses import dataclass, fields, replace
import re

from pietto._project.project_execution_source import requirement_state
from pietto._project.project_refinement import (
    RefinedQuery,
    TieRefinement,
    UnitRefinement,
    verify_sources,
)
from pietto._project.project_refinement_order import Coordinate, before, equality
from pietto._project.project_refinement_rendering import (
    CTE,
    Expr,
    Join,
    Order,
    Relation,
    Select,
    SetQuery,
    Statement,
    NativeStatement,
    conjunction,
    disjunction,
    integer,
    ref,
)
from pietto._project.project_result_output import verify_output, source_read_columns
from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLLiteralColumn,
    SQLScan,
    SQLNamedUse,
    RowScan,
    RowNamedUse,
    RowValueColumn,
)
from pietto._project.project_sql_emission_aggregation import AggregateValueColumn
from pietto._project.project_sql_emission_joins import JoinBody
from pietto._project.project_sql_emission_results import RowResultBody
from pietto._project.project_sql_emission_sets import SetBody
from pietto._project.project_sql_emission_windows import WindowColumn

__all__: tuple[str, ...] = ()

_SYNTAX = (CTE, Expr, Join, Order, Relation, Select, SetQuery, Statement, Coordinate)


def _same(actual, expected):
    """Exact primitive types, closed syntax values, and original object identity."""
    if type(actual) is not type(expected):
        return False
    if type(expected) in _SYNTAX:
        return all(
            _same(getattr(actual, f.name), getattr(expected, f.name))
            for f in fields(expected)
        )
    if type(expected) is tuple:
        return len(actual) == len(expected) and all(
            _same(a, b) for a, b in zip(actual, expected, strict=True)
        )
    if type(expected) in (str, int, bool, bytes, type(None)):
        return actual == expected
    if type(expected) is float:
        return actual.hex() == expected.hex()
    return actual is expected


def _need(condition, reason):
    if not condition:
        raise ValueError("REFINEMENT_" + reason)


def _int(address, low=-(1 << 63), high=(1 << 63) - 1):
    return Coordinate(
        address,
        "Int",
        False,
        (("kind", "int_range"), ("max", str(high)), ("min", str(low))),
    )


def _scalar(address, realization):
    _need(realization.tag in ("Int", "Bool", "Text", "Decimal"), "KEY_TYPE")
    return Coordinate(
        address,
        realization.tag,
        realization.nullable is not False,
        tuple(sorted(realization.domain.items())),
        tuple(sorted(realization.storage.items())),
    )


def _shift(coordinates, offset, enclosing=()):
    return tuple(
        replace(
            c,
            active=enclosing
            + tuple((offset + index, value) for index, value in c.active),
        )
        for c in coordinates
    )


@dataclass(frozen=True)
class _Input:
    relation: str
    fields: tuple
    keys: tuple
    coordinates: tuple
    order_names: tuple = ()
    order_coordinates: tuple = ()
    directions: tuple = ()
    dependency: int = -1


class _Rules:
    def __init__(self, value):
        self.value = value
        self.output = value.output
        self.request = value.original.request
        self.family = self.request.family
        self.prefix = value.prefix
        self.actual = value.statement.ctes
        self.cursor = 0
        self.inputs = {}
        self.recursive = False
        self.select_names = {}
        if type(value.original.ast) is SQLSelect:
            self.select_names = {
                c.body: tuple(s.name for s in c.columns)
                for c in value.original.ast.ctes
            }

    def names(self, kind, count):
        return tuple(self.prefix + kind + str(i) for i in range(count))

    @staticmethod
    def reads(alias, names):
        return tuple(ref(alias, name) for name in names)

    def cte(self, name, columns, query):
        _need(self.cursor < len(self.actual), "MISSING_NATIVE_UNIT")
        actual = self.actual[self.cursor]
        _need(
            _same(actual, CTE(name, tuple(columns), query)),
            "NATIVE_RULE_CORRESPONDENCE",
        )
        self.cursor += 1
        return actual

    def select(self, name, columns, source, **clauses):
        return self.cte(
            name,
            tuple(n for n, _ in columns),
            Select(tuple(columns), source, **clauses),
        )

    def sources(self):
        columns = source_read_columns(self.output)
        for index, (source, capability, names) in enumerate(
            zip(self.request.sources, self.value.sources, columns, strict=True)
        ):
            alias = self.prefix + "base"
            keys = self.names("k", len(capability.token_columns) + 1)
            selected = tuple((n, ref(alias, n)) for n in names)
            selected += ((keys[0], Expr("cast_integer", (integer(index),))),)
            selected += tuple(
                (name, Expr("cast_integer", (ref(alias, physical),)))
                for name, physical in zip(
                    keys[1:], capability.token_columns, strict=True
                )
            )
            relation = self.prefix + "source" + str(index)
            self.select(
                relation, selected, Relation((source.namespace, source.name), alias)
            )
            coordinates = (_int(("source", index), index, index),) + tuple(
                _int(("source", index, "token", i))
                for i in range(len(capability.token_columns))
            )
            self.inputs[source] = _Input(
                relation, names, keys, coordinates, dependency=-index - 1
            )

    def input(self, scan):
        if type(scan) in (SQLScan, RowScan):
            owner = scan.realization
        elif type(scan) is SQLNamedUse:
            owner = scan.cte.body
        else:
            owner = scan.body
        _need(owner in self.inputs, "DEPENDENCY_ORDER")
        return self.inputs[owner]

    def rows(self, unit, address, terminal, public):
        source = self.input(unit.scan)
        alias = unit.scan.symbol.name
        keys = self.reads(alias, source.keys)
        coordinates = source.coordinates
        if type(unit.scan) in (RowNamedUse, SQLNamedUse):
            keys = (Expr("cast_integer", (integer(address),)),) + keys
            coordinates = (_int((address, "use"), address, address),) + _shift(
                coordinates, 1
            )
        orders = self.reads(alias, source.order_names)
        order_types, directions = source.order_coordinates, source.directions
        predicate = getattr(unit, "predicate", None)
        predicate = (
            None
            if predicate is None
            else Expr("original_scalar", (predicate.value, alias))
        )
        relation = source.relation
        if getattr(unit, "window", None) is not None and predicate is not None:
            relation = terminal + "filtered"
            self.select(
                relation,
                tuple(
                    (n, ref(alias, n))
                    for n in source.fields + source.keys + source.order_names
                ),
                Relation((source.relation,), alias),
                where=predicate,
            )
            predicate = None
        grouping = getattr(unit, "aggregation", None)
        groups = ()
        rule, capacity = "projection", "structural_keys"
        if grouping is not None:
            rule = "global" if not grouping.keys else "grouped"
            groups = tuple(ref(alias, c.read.name) for c in grouping.keys)
            keys = (Expr("cast_integer", (integer(0),)),) + groups
            coordinates = (_int((address, "group"), 0, 0),) + tuple(
                _scalar((address, "group", i), c.read.realization)
                for i, c in enumerate(grouping.keys)
            )
            orders, order_types, directions = (), (), ()
        if type(unit) is RowResultBody:
            rule = "result"
            if unit.distinct is not None:
                relation = terminal + "quotient"
                self.select(
                    relation,
                    tuple((c.read.name, ref(alias, c.read.name)) for c in unit.columns),
                    Relation((source.relation,), alias),
                    distinct=True,
                )
                keys = (Expr("cast_integer", (integer(0),)),) + tuple(
                    ref(alias, c.read.name) for c in unit.columns
                )
                coordinates = (_int((address, "class"), 0, 0),) + tuple(
                    _scalar((address, "class", i), c.column.realization)
                    for i, c in enumerate(unit.columns)
                )
                orders, order_types, directions = (), (), ()
            if unit.order is not None:
                orders = tuple(ref(alias, item.read.name) for item in unit.order.items)
                order_types = tuple(
                    _scalar((address, "order", i), item.read.realization)
                    for i, item in enumerate(unit.order.items)
                )
                directions = tuple(item.direction for item in unit.order.items)
        selected = []
        for i, original in enumerate(unit.columns):
            if type(unit) is SQLSelect:
                value = (
                    Expr("original_scalar", (original.value, alias))
                    if type(original) is SQLLiteralColumn and original.value is not None
                    else ref(alias, original.symbol.name)
                )
            elif type(original) is AggregateValueColumn:
                value = Expr("original_aggregate", (original, alias))
            elif type(original) is WindowColumn:
                value = self.window(
                    original, relation, alias, source.keys, terminal + "w" + str(i)
                )
                rule, capacity = (
                    "window",
                    "original_native_call_range_structural_frame_endpoints",
                )
            elif hasattr(original, "read"):
                value = ref(alias, original.read.name)
            else:
                if type(original) is not RowValueColumn:
                    raise ValueError("REFINEMENT_ORIGINAL_COLUMN")
                value = Expr("original_scalar", (original.value, alias))
            selected.append((public[i], value))
        key_names, order_names = (
            self.names("k", len(keys)),
            self.names("o", len(orders)),
        )
        selected.extend(zip(key_names, keys, strict=True))
        selected.extend(zip(order_names, orders, strict=True))
        ordering, limit = (), None
        if type(unit) is RowResultBody:
            ordering = tuple(
                Order(v, d) for v, d in zip(orders, directions, strict=True)
            ) + tuple(Order(v) for v in keys)
            limit = None if unit.limit is None else unit.limit.value
        self.select(
            terminal,
            selected,
            Relation((relation,), alias),
            where=predicate,
            groups=groups,
            orders=ordering,
            limit=limit,
        )
        return (
            rule,
            (source.dependency,),
            _Input(
                terminal,
                public,
                key_names,
                coordinates,
                order_names,
                order_types,
                directions,
                address,
            ),
            capacity,
        )

    def joins(self, unit, address, terminal, public):
        left, right = unit.inputs
        left_input, right_input = (
            self.inputs[left.producer],
            self.inputs[right.producer],
        )
        a, b = left.symbol.name, right.symbol.name
        if self.family == "mysql" and unit.join.kind.value in ("left", "right"):
            side = int(unit.join.kind.value == "left")
            nullable = right_input if side else left_input
            _need(bool(nullable.keys), "NULLABLE_INPUT_IDENTITY")
            fields = nullable.fields + nullable.order_names + nullable.keys
            relation = terminal + "nullable" + str(side)
            self.select(
                relation,
                tuple((name, ref("s", name)) for name in fields),
                Relation((nullable.relation,), "s"),
                distinct=True,
            )
            if side == 1:
                right_input = replace(nullable, relation=relation)
            else:
                left_input = replace(nullable, relation=relation)
        predicates = tuple(
            Expr(
                "=",
                (
                    ref(e.left_scope.name, e.left.name),
                    ref(e.right_scope.name, e.right.name),
                ),
            )
            for e in unit.equalities
        )
        if unit.predicate is not None:
            predicates += (Expr("original_scalar", (unit.predicate, "")),)
        condition = conjunction(*predicates)
        selected = [
            (n, ref(c.scope.name, c.read.name))
            for n, c in zip(public, unit.columns, strict=True)
        ]
        where = None
        if unit.membership is not None:
            source = Relation((left_input.relation,), a)
            where = self.exists(right_input.relation, b, condition)
            if unit.membership == "not_exists":
                where = Expr("not", (where,))
            coordinates, keys = left_input.coordinates, self.reads(a, left_input.keys)
        else:
            kind = unit.join.kind.value.upper()
            _need(kind in ("INNER", "CROSS", "LEFT", "RIGHT", "FULL"), "JOIN_KIND")
            source = Join(
                Relation((left_input.relation,), a),
                Relation((right_input.relation,), b),
                kind,
                condition,
            )
            coordinates, keys = [], []
            for side, inp, alias in ((0, left_input, a), (1, right_input, b)):
                presence = len(coordinates)
                coordinates.append(_int((address, "presence", side), 0, 1))
                for c in inp.coordinates:
                    coordinates.append(
                        replace(
                            c,
                            active=((presence, 1),)
                            + tuple((i + presence + 1, v) for i, v in c.active),
                        )
                    )
                keys.append(
                    Expr(
                        "cast_integer",
                        (
                            Expr(
                                "case",
                                (
                                    Expr("is_null", (ref(alias, inp.keys[0]),)),
                                    integer(0),
                                    integer(1),
                                ),
                            ),
                        ),
                    )
                )
                keys.extend(self.reads(alias, inp.keys))
            coordinates, keys = tuple(coordinates), tuple(keys)
        key_names = self.names("k", len(keys))
        selected.extend(zip(key_names, keys, strict=True))
        self.select(terminal, selected, source, where=where)
        return (
            "join_" + unit.join.kind.value,
            (left_input.dependency, right_input.dependency),
            _Input(terminal, public, key_names, coordinates, dependency=address),
            "structural_keys",
        )

    def exists(self, relation, alias, predicate):
        return Expr(
            "exists",
            (
                Select(
                    ((self.prefix + "one", integer(1)),),
                    Relation((relation,), alias),
                    predicate,
                ),
            ),
        )

    def window(self, original, relation, outer, keys, stem):
        specification = original.specification
        partitions = tuple(read.name for _, read in specification.partitions)
        peer_names = tuple(order.read.name for order in specification.orders)
        peer_directions = tuple(order.direction for order in specification.orders)

        def ordered(alias, chosen=False):
            names = peer_names + (keys if chosen else ())
            directions = peer_directions + (("asc",) * len(keys) if chosen else ())
            return tuple(
                Order(ref(alias, n), d) for n, d in zip(names, directions, strict=True)
            )

        if original.function in (
            "row_number",
            "ntile",
            "lag",
            "lead",
            "rank",
            "dense_rank",
            "percent_rank",
            "cume_dist",
        ):
            choice = original.function in ("row_number", "ntile", "lag", "lead")
            return Expr(
                "window",
                (
                    original,
                    outer,
                    self.reads(outer, partitions),
                    ordered(outer, choice),
                    False,
                ),
            )
        _need(
            original.function in ("first_value", "last_value", "nth_value"),
            "WINDOW_FUNCTION",
        )
        from pietto._project.project_sql_emission_contract import (
            CompiledPreparedEmission,
        )

        if type(self.request) is CompiledPreparedEmission:
            from pietto._project.project_compiled_schema import Address

            records = self.request.verification.completed.root.records
            window = records[
                Address(original.window.ref.kind, original.window.ref.position)
            ]
            described = records[window.get("specification")].get("frame")
            unit, start, end, exclusion = (
                ("range", ("unbounded_preceding", None), ("current_row", None), None)
                if described is None
                else (
                    described[0],
                    (
                        described[1][0],
                        None
                        if described[1][1] is None
                        else records[described[1][1]].get("value").value,
                    ),
                    (
                        described[2][0],
                        None
                        if described[2][1] is None
                        else records[described[2][1]].get("value").value,
                    ),
                    described[3],
                )
            )
        else:
            policies = tuple(
                p
                for p in self.request.plan.window_policies
                if p.window is original.window.ref
            )
            _need(len(policies) == 1, "WINDOW_POLICY")
            resolved = getattr(policies[0].specification.frame, "resolved", None)
            unit, start, end, exclusion = (
                "range",
                ("unbounded_preceding", None),
                ("current_row", None),
                None,
            )
            if resolved is not None and resolved.unit is not None:
                unit = resolved.unit.value
                start = (
                    resolved.start.kind.value,
                    getattr(resolved.start.offset, "value", None),
                )
                end = (
                    resolved.end.kind.value,
                    getattr(resolved.end.offset, "value", None),
                )
                exclusion = (
                    None if resolved.exclusion is None else resolved.exclusion.value
                )
        member, candidate = stem + "member", stem + "endpoint"
        endpoint_relation = relation
        if unit == "groups":
            endpoint_relation = stem + "peers"
            names = tuple(dict.fromkeys(partitions + peer_names))
            _need(bool(names), "GROUPS_ORDER")
            self.select(
                endpoint_relation,
                tuple((n, ref(candidate, n)) for n in names),
                Relation((relation,), candidate),
                distinct=True,
            )
        names = peer_names + (keys if unit == "rows" else ())
        directions = peer_directions + (("asc",) * len(keys) if unit == "rows" else ())

        def inclusive(lower, upper):
            if not names:
                return conjunction()
            return disjunction(
                before(upper, lower, directions, self.family), equality(lower, upper)
            )

        def boundary(bound, is_start):
            kind, distance = bound
            if kind in ("unbounded_preceding", "unbounded_following"):
                return conjunction()
            if kind == "current_row" or distance == 0:
                m, x = self.reads(member, names), self.reads(outer, names)
                return inclusive(m, x) if is_start else inclusive(x, m)
            _need(
                kind in ("offset_preceding", "offset_following")
                and type(distance) is int
                and 0 < distance < 2**63,
                "FRAME_CAPACITY",
            )
            preceding = kind == "offset_preceding"
            if unit == "range":
                _need(len(peer_names) == 1, "RANGE_KEY")
                ascending = peer_directions[0] == "asc"
                threshold = Expr(
                    "+" if preceding != ascending else "-",
                    (
                        Expr("cast_integer", (ref(outer, peer_names[0]),)),
                        integer(distance),
                    ),
                )
                return Expr(
                    ">=" if is_start == ascending else "<=",
                    (ref(member, peer_names[0]), threshold),
                )
            near = self.reads(candidate, names)
            anchor = self.reads(outer, names)
            side = (
                before(near, anchor, directions, self.family)
                if preceding
                else before(anchor, near, directions, self.family)
            )
            eligible = conjunction(
                equality(
                    self.reads(candidate, partitions), self.reads(outer, partitions)
                ),
                side,
            )
            native_order = tuple(
                Order(v, ("desc" if d == "asc" else "asc") if preceding else d)
                for v, d in zip(near, directions, strict=True)
            )

            def endpoint(value):
                return Select(
                    ((stem + "value", value),),
                    Relation((endpoint_relation,), candidate),
                    eligible,
                    orders=native_order,
                    limit=1,
                    offset=distance - 1,
                )

            exists = Expr(
                "is_not_null", (Expr("scalar_query", (endpoint(integer(1)),)),)
            )
            point = tuple(Expr("scalar_query", (endpoint(value),)) for value in near)
            row = self.reads(member, names)
            inside = inclusive(row, point) if is_start else inclusive(point, row)
            # A missing lower predecessor means before-start; a missing upper
            # predecessor means an empty prefix. Following has the dual law.
            return (
                disjunction(Expr("not", (exists,)), inside)
                if is_start == preceding
                else conjunction(exists, inside)
            )

        predicate = conjunction(
            equality(self.reads(member, partitions), self.reads(outer, partitions)),
            boundary(start, True),
            boundary(end, False),
        )
        same_peer = equality(
            self.reads(member, peer_names), self.reads(outer, peer_names)
        )
        same_row = equality(self.reads(member, keys), self.reads(outer, keys))
        if exclusion == "current_row":
            predicate = conjunction(predicate, Expr("not", (same_row,)))
        elif exclusion == "group":
            predicate = conjunction(predicate, Expr("not", (same_peer,)))
        elif exclusion == "ties":
            predicate = conjunction(
                predicate, disjunction(Expr("not", (same_peer,)), same_row)
            )
        else:
            _need(exclusion in (None, "no_others"), "EXCLUSION")
        function = Expr("window", (original, member, (), ordered(member, True), True))
        return Expr(
            "scalar_query",
            (
                Select(
                    ((stem + "value", function),),
                    Relation((relation,), member),
                    predicate,
                    orders=ordered(member, True),
                    limit=1,
                ),
            ),
        )

    def paired_copies(self, left, right, public, operation, stem):
        a, b, between, p = (stem + suffix for suffix in ("a", "b", "m", "p"))
        successor_names = []
        for side, inp in enumerate((left, right)):
            now, later, middle = (
                self.reads(scope, inp.keys) for scope in (a, b, between)
            )
            directions = ("asc",) * len(now)
            predicate = Expr(
                "not",
                (
                    self.exists(
                        inp.relation,
                        between,
                        conjunction(
                            equality(
                                self.reads(a, public), self.reads(between, public)
                            ),
                            before(now, middle, directions, self.family),
                            before(middle, later, directions, self.family),
                        ),
                    ),
                ),
            )
            source = Join(
                Relation((inp.relation,), a),
                Relation((inp.relation,), b),
                "INNER",
                conjunction(
                    equality(self.reads(a, public), self.reads(b, public)),
                    before(now, later, directions, self.family),
                ),
            )
            successor = stem + "successor" + str(side)
            self.select(
                successor,
                tuple(zip(self.names("c", len(now)), now, strict=True))
                + tuple(zip(self.names("n", len(now)), later, strict=True)),
                source,
                where=predicate,
            )
            successor_names.append(successor)
        lnames, rnames = (
            self.names("l", len(left.keys)),
            self.names("r", len(right.keys)),
        )
        initial = equality(self.reads(a, public), self.reads(b, public))
        for inp, alias in ((left, a), (right, b)):
            first = Expr(
                "not",
                (
                    self.exists(
                        inp.relation,
                        between,
                        conjunction(
                            equality(
                                self.reads(between, public), self.reads(alias, public)
                            ),
                            before(
                                self.reads(between, inp.keys),
                                self.reads(alias, inp.keys),
                                ("asc",) * len(inp.keys),
                                self.family,
                            ),
                        ),
                    ),
                ),
            )
            initial = conjunction(initial, first)
        anchor = Select(
            tuple(
                zip(
                    lnames + rnames,
                    self.reads(a, left.keys) + self.reads(b, right.keys),
                    strict=True,
                )
            ),
            Join(
                Relation((left.relation,), a),
                Relation((right.relation,), b),
                "INNER",
                initial,
            ),
        )
        name = stem + "pairs"
        source = Join(
            Relation((name,), p),
            Relation((successor_names[0],), a),
            "INNER",
            equality(
                self.reads(p, lnames), self.reads(a, self.names("c", len(lnames)))
            ),
        )
        source = Join(
            source,
            Relation((successor_names[1],), b),
            "INNER",
            equality(
                self.reads(p, rnames), self.reads(b, self.names("c", len(rnames)))
            ),
        )
        next_pair = Select(
            tuple(
                zip(
                    lnames + rnames,
                    self.reads(a, self.names("n", len(lnames)))
                    + self.reads(b, self.names("n", len(rnames))),
                    strict=True,
                )
            ),
            source,
        )
        self.cte(name, lnames + rnames, SetQuery(anchor, next_pair, "UNION", "ALL"))
        quotient = stem + "classes"
        self.select(
            quotient,
            tuple(zip(public, self.reads(a, public), strict=True)),
            Relation((left.relation,), a),
            distinct=True,
        )
        matched = self.exists(
            name, p, equality(self.reads(p, lnames), self.reads(a, left.keys))
        )
        where = matched if operation == "INTERSECT" else Expr("not", (matched,))
        source = Join(
            Relation((left.relation,), a),
            Relation((quotient,), b),
            "INNER",
            equality(self.reads(a, public), self.reads(b, public)),
        )
        self.select(
            stem,
            tuple(zip(public, self.reads(b, public), strict=True))
            + tuple(zip(left.keys, self.reads(a, left.keys), strict=True)),
            source,
            where=where,
        )
        return _Input(stem, public, left.keys, left.coordinates)

    def sets(self, unit, address, terminal, public):
        operands = []
        for i, operand in enumerate(unit.operands):
            _need(operand.producer in self.inputs, "SET_DEPENDENCY")
            inp = self.inputs[operand.producer]
            alias = operand.symbol.name
            name = terminal + "operand" + str(i)
            self.select(
                name,
                tuple(
                    (n, ref(alias, c.name))
                    for n, c in zip(public, operand.columns, strict=True)
                )
                + tuple(zip(inp.keys, self.reads(alias, inp.keys), strict=True)),
                Relation((inp.relation,), alias),
            )
            operands.append(replace(inp, relation=name, fields=public))
        dependencies = tuple(inp.dependency for inp in operands)
        operation, quantifier = unit.kind.value.upper(), unit.quantifier.value.upper()
        capacity = "structural_keys"
        if (operation, quantifier) == ("UNION", "ALL"):
            coordinates = [_int((address, "branch"), 0, len(operands) - 1)]
            for branch, inp in enumerate(operands):
                offset = len(coordinates)
                coordinates.extend(_shift(inp.coordinates, offset, ((0, branch),)))
            coordinates = tuple(coordinates)
            key_names = self.names("k", len(coordinates))
            terms = []
            for branch, inp in enumerate(operands):
                alias = terminal + "union"
                keys = [Expr("cast_integer", (integer(branch),))]
                for other, part in enumerate(operands):
                    keys.extend(
                        self.reads(alias, part.keys)
                        if other == branch
                        else (Expr("null", ()),) * len(part.keys)
                    )
                terms.append(
                    Select(
                        tuple(zip(public, self.reads(alias, public), strict=True))
                        + tuple(zip(key_names, keys, strict=True)),
                        Relation((inp.relation,), alias),
                    )
                )
            fold = terms[0]
            for term in terms[1:]:
                fold = SetQuery(fold, term, "UNION", "ALL")
            self.cte(terminal, public + key_names, fold)
        elif quantifier == "DISTINCT":
            terms = [
                Select(
                    tuple(zip(public, self.reads("s", public), strict=True)),
                    Relation((inp.relation,), "s"),
                )
                for inp in operands
            ]
            fold = terms[0]
            for term in terms[1:]:
                fold = SetQuery(fold, term, operation, "DISTINCT")
            name = terminal + "quotient"
            self.cte(name, public, fold)
            coordinates = (_int((address, "class"), 0, 0),) + tuple(
                _scalar((address, "class", i), c.realization)
                for i, c in enumerate(unit.columns)
            )
            key_names = self.names("k", len(coordinates))
            keys = (Expr("cast_integer", (integer(0),)),) + self.reads("s", public)
            self.select(
                terminal,
                tuple(zip(public, self.reads("s", public), strict=True))
                + tuple(zip(key_names, keys, strict=True)),
                Relation((name,), "s"),
            )
        else:
            _need(
                operation in ("INTERSECT", "EXCEPT") and quantifier == "ALL", "SET_FORM"
            )
            self.recursive = True
            capacity = "structural_successor_pairing_native_resource_terminal"
            accumulated = operands[0]
            for i, operand in enumerate(operands[1:]):
                accumulated = self.paired_copies(
                    accumulated, operand, public, operation, terminal + "fold" + str(i)
                )
            coordinates, key_names = accumulated.coordinates, accumulated.keys
            self.select(
                terminal,
                tuple((n, ref("s", n)) for n in public + key_names),
                Relation((accumulated.relation,), "s"),
            )
        return (
            "set_" + unit.kind.value + "_" + unit.quantifier.value,
            dependencies,
            _Input(terminal, public, key_names, coordinates, dependency=address),
            capacity,
        )

    def run(self):
        self.sources()
        _need(len(self.value.units) == len(self.output.units), "UNIT_DENOMINATOR")
        for address, (original, supplied) in enumerate(
            zip(self.output.units, self.value.units, strict=True)
        ):
            _need(
                type(supplied) is UnitRefinement
                and supplied.original is original
                and type(supplied.address) is int
                and supplied.address == address,
                "UNIT_IDENTITY",
            )
            first = self.cursor
            terminal = self.prefix + "unit" + str(address)
            public = self.select_names.get(
                original, tuple(s.name for s in getattr(original, "cte_columns", ()))
            )
            if not public:
                public = tuple(c.label for c in original.columns)
            if self.family == "mysql" and len({n.casefold() for n in public}) != len(
                public
            ):
                public = self.names("v", len(public))
            if type(original) is SetBody:
                rule, dependencies, result, capacity = self.sets(
                    original, address, terminal, public
                )
            elif type(original) is JoinBody:
                rule, dependencies, result, capacity = self.joins(
                    original, address, terminal, public
                )
            else:
                rule, dependencies, result, capacity = self.rows(
                    original, address, terminal, public
                )
            for actual, expected in (
                (supplied.rule, rule),
                (supplied.dependencies, dependencies),
                (supplied.terminal, terminal),
                (supplied.public_names, public),
                (supplied.key_names, result.keys),
                (supplied.coordinates, result.coordinates),
                (supplied.order_names, result.order_names),
                (supplied.order_coordinates, result.order_coordinates),
                (supplied.directions, result.directions),
                (supplied.capacity, capacity),
            ):
                _need(_same(actual, expected), "FACT_CORRESPONDENCE")
            expected_ctes = self.actual[first : self.cursor]
            _need(
                type(supplied.ctes) is tuple
                and len(supplied.ctes) == len(expected_ctes)
                and all(
                    a is b for a, b in zip(supplied.ctes, expected_ctes, strict=True)
                ),
                "UNIT_NATIVE_INVENTORY",
            )
            self.inputs[original] = result
        _need(self.cursor == len(self.actual), "EXTRA_NATIVE_UNIT")
        last = self.value.units[-1]
        alias = self.prefix + "result"
        columns = tuple(
            (c.label, ref(alias, n))
            for c, n in zip(self.output.columns, last.public_names, strict=True)
        )
        columns += tuple((n, ref(alias, n)) for n in last.order_names + last.key_names)
        directions = last.directions + ("asc",) * len(last.key_names)
        order = tuple(
            Order(ref(alias, n), d)
            for n, d in zip(last.order_names + last.key_names, directions, strict=True)
        )
        _need(
            _same(
                self.value.statement.query,
                Select(columns, Relation((last.terminal,), alias), orders=order),
            ),
            "FINAL_ERASURE_ORDER",
        )
        _need(
            type(self.value.statement.recursive) is bool
            and self.value.statement.recursive is self.recursive,
            "RECURSION_SCOPE",
        )


def _syntax_resources(statement, request):
    from pietto._project.project_sql_emission_ast import resource_limits

    limits = resource_limits(request)
    stack = [statement]
    nodes = 0
    while stack:
        value = stack.pop()
        if type(value) in _SYNTAX:
            nodes += 1
            _need(nodes <= limits["nodes"], "RESOURCE_LIMIT")
            if type(value) in (Select, CTE):
                _need(len(value.columns) <= limits["columns"], "RESOURCE_LIMIT")
            stack.extend(getattr(value, f.name) for f in fields(value))
        elif type(value) is tuple:
            _need(
                len(value) <= limits["nodes"]
                and len(stack) + len(value) <= limits["nodes"] * 4,
                "RESOURCE_LIMIT",
            )
            stack.extend(value)
    return limits


def verify_refinement(value):
    _need(type(value) is RefinedQuery and type(value.policy) is TieRefinement, "ROOT")
    _need(
        type(value.policy.choice) is str
        and value.policy.choice == "structural_occurrence_ascending",
        "POLICY",
    )
    output = value.output
    _need(output.artifact is value.original, "ORIGINAL_ROOT")
    verify_output(output, value.original, output.contract, binding=output.binding)
    verify_sources(
        value.sources,
        value.original.request.sources,
        family=value.original.request.family,
    )
    expected = tuple(requirement_state(s) for s in value.sources)
    _need(_same(value.source_states, expected), "SOURCE_STATE")
    _need(
        type(value.prefix) is str
        and re.fullmatch(r"__pietto_r2_(?:[1-9][0-9]*_)?", value.prefix) is not None,
        "NAMESPACE",
    )
    reserved = tuple(
        f.column for s in value.original.request.sources for f in s.fields
    ) + tuple(c.label for u in output.units for c in u.columns)
    if value.original.request.family == "mysql":
        reserved = tuple(n.casefold() for n in reserved)
    _need(not any(n.startswith(value.prefix) for n in reserved), "NAMESPACE_COLLISION")
    _need(
        type(value.statement) is Statement
        and type(value.statement.ctes) is tuple
        and type(value.units) is tuple
        and bool(value.units),
        "STATEMENT",
    )
    _syntax_resources(value.statement, value.original.request)
    _need(
        all(type(c) is CTE and type(c.name) is str for c in value.statement.ctes),
        "NATIVE_UNIT",
    )
    names = []
    for cte in value.statement.ctes:
        if type(cte) is not CTE:
            raise ValueError("REFINEMENT_NATIVE_UNIT")
        names.append(cte.name)
    _need(len(set(names)) == len(names), "DUPLICATE_NATIVE_UNIT")
    _need(
        type(value.erasure) is tuple and len(value.erasure) == len(output.columns),
        "ERASURE_DENOMINATOR",
    )
    for index, (item, column) in enumerate(
        zip(value.erasure, output.columns, strict=True)
    ):
        _need(
            type(item) is tuple
            and len(item) == 2
            and type(item[0]) is int
            and item[0] == index
            and item[1] is column,
            "ERASURE_IDENTITY",
        )
    _Rules(value).run()
    return value.units[-1]


class _Bytes:
    """Recognize the one checked closed syntax, never parse caller SQL into authority."""

    def __init__(self, native, artifact, controls):
        self.native = native
        self.artifact = artifact
        self.family = artifact.request.family
        self.controls = controls
        self.text = native.sql.decode("utf-8")
        self.position = 0
        self.uses = []
        self.base = max((u.server_index for u in artifact.parameter_uses), default=0)

    def take(self, text):
        _need(self.text.startswith(text, self.position), "NATIVE_SQL")
        self.position += len(text)

    def identifier(self, expected):
        _need(type(expected) is str and "\0" not in expected, "IDENTIFIER")
        quote = '"' if self.family == "postgres" else "`"
        self.take(quote)
        decoded = []
        while self.position < len(self.text):
            char = self.text[self.position]
            self.position += 1
            if char == quote:
                if self.position < len(self.text) and self.text[self.position] == quote:
                    decoded.append(quote)
                    self.position += 1
                    continue
                _need("".join(decoded) == expected, "NATIVE_IDENTIFIER")
                return
            decoded.append(char)
        raise ValueError("REFINEMENT_NATIVE_IDENTIFIER")

    def list(self, items, consume, separator=", "):
        for i, item in enumerate(items):
            if i:
                self.take(separator)
            consume(item)

    def parameter(self, domain, owner, index, value, original=None):
        from pietto._project.project_sql_emission_parameters import same_value

        expected_index = index if self.family == "postgres" else len(self.uses) + 1
        self.take("$" + str(expected_index) if self.family == "postgres" else "?")
        ordinal = len(self.uses)
        _need(ordinal < len(self.native.uses), "PARAMETER_DENOMINATOR")
        actual = self.native.uses[ordinal]
        from pietto._project.project_refinement_rendering import ParameterUse

        _need(
            type(actual) is ParameterUse
            and _same(actual.domain, domain)
            and type(actual.index) is int
            and actual.index == expected_index,
            "PARAMETER_USE",
        )
        _need(
            actual.owner is owner
            if domain == "original"
            else type(actual.owner) is int and actual.owner == owner,
            "PARAMETER_OWNER",
        )
        _need(actual.original is original, "PARAMETER_OCCURRENCE")
        _need(
            same_value(actual.value, value)
            if type(value) in (bool, int, float, str)
            else actual.value is value,
            "PARAMETER_VALUE",
        )
        self.uses.append((domain, owner, expected_index, value))

    def scalar(self, value, alias):
        from pietto._project import project_sql_emission_parameters as p
        from pietto._project.project_sql_emission_rows import (
            SQLStageReference,
            SQLOperation,
        )

        if type(value) is SQLStageReference:
            self.identifier(alias if value.scope is None else value.scope.name)
            self.take(".")
            self.identifier(value.column.name)
        elif type(value) is SQLOperation:
            self.take("(")
            if value.kind == "sign":
                self.take(value.original.expression.operator)
                self.scalar(value.operands[0], alias)
            elif value.kind == "null_test":
                self.scalar(value.operands[0], alias)
                self.take(
                    " IS NOT NULL" if value.original.expression.negated else " IS NULL"
                )
            else:
                self.scalar(value.operands[0], alias)
                operator = value.original.expression.operator
                if type(operator) is not str:
                    raise ValueError("REFINEMENT_SCALAR_OPERATOR")
                operator = {"==": "=", "!=": "<>"}.get(operator, operator)
                self.take(
                    " "
                    + (operator.upper() if value.kind == "logical" else operator)
                    + " "
                )
                self.scalar(value.operands[1], alias)
            self.take(")")
        elif type(value) is p.SQLUnary:
            self.take("(" + value.original.expression.operator)
            self.scalar(value.operand, alias)
            self.take(")")
        elif type(value) is p.SQLAnchor:
            self.take("CAST(")
            self.scalar(value.operand, alias)
            self.take(p.anchor_suffix(value.physical_type))
        elif type(value) is p.SQLParameter:
            slot = value.use.slot
            native_value = slot.site.position.literal.value
            if self.family == "mysql" and slot.tag.value == "Bool":
                native_value = int(native_value)
            self.parameter(
                "original", slot, value.use.server_index, native_value, value.use
            )
        else:
            _need(type(value) is p.SQLLiteral, "SCALAR")
            self.take(p.literal_token(value, self.family))

    def expression(self, value):
        _need(type(value) is Expr and type(value.args) is tuple, "EXPRESSION")
        kind, args = value.kind, value.args
        if kind == "ref":
            self.identifier(args[0])
            self.take(".")
            self.identifier(args[1])
        elif kind == "integer":
            _need(type(args[0]) is int and -(1 << 63) <= args[0] < (1 << 63), "INTEGER")
            self.take(str(args[0]))
        elif kind == "null":
            self.take("NULL")
        elif kind in ("and", "or"):
            self.take("(")
            if not args:
                self.take("TRUE" if kind == "and" else "FALSE")
            else:
                self.list(args, self.expression, " AND " if kind == "and" else " OR ")
            self.take(")")
        elif kind in ("=", "<>", "<", ">", "<=", ">=", "+", "-"):
            self.take("(")
            self.expression(args[0])
            self.take(" " + kind + " ")
            self.expression(args[1])
            self.take(")")
        elif kind in ("is_null", "is_not_null", "not"):
            self.take("(")
            if kind == "not":
                self.take("NOT ")
            self.expression(args[0])
            if kind != "not":
                self.take(" IS NULL" if kind == "is_null" else " IS NOT NULL")
            self.take(")")
        elif kind == "cast_integer":
            self.take("CAST(")
            self.expression(args[0])
            self.take(" AS BIGINT)" if self.family == "postgres" else " AS SIGNED)")
        elif kind == "case":
            self.take("CASE WHEN ")
            self.expression(args[0])
            self.take(" THEN ")
            self.expression(args[1])
            self.take(" ELSE ")
            self.expression(args[2])
            self.take(" END")
        elif kind in ("scalar_query", "exists"):
            self.take("(" if kind == "scalar_query" else "EXISTS (")
            self.query(args[0])
            self.take(")")
        elif kind == "original_scalar":
            self.scalar(args[0], args[1])
        elif kind == "original_aggregate":
            original, alias = args
            self.take(original.spelling + "(")
            if original.argument is None:
                self.take("*")
            else:
                if original.distinct:
                    self.take("DISTINCT ")
                self.scalar(original.argument, alias)
            self.take(")")
        elif kind == "window":
            original, alias, partitions, orders, full = args
            self.take(original.function.upper() + "(")
            for i, item in enumerate(original.arguments):
                if i:
                    self.take(", ")
                if item.read is None:
                    self.take(item.literal)
                else:
                    self.identifier(alias)
                    self.take(".")
                    self.identifier(item.read.name)
            self.take(") OVER (")
            if partitions:
                self.take("PARTITION BY ")
                self.list(partitions, self.expression)
            if orders:
                if partitions:
                    self.take(" ")
                self.take("ORDER BY ")
                self.list(orders, self.order)
            if full:
                self.take(" ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING")
            self.take(")")
        elif kind in ("page", "page_limit"):
            index, tag, precision, scale = args
            _need(
                type(index) is int and 0 <= index < len(self.controls), "PAGE_PARAMETER"
            )
            raw = self.controls[index]
            wire = (
                str(raw)
                if tag == "Decimal" and raw is not None
                else int(raw)
                if self.family == "mysql" and tag == "Bool" and raw is not None
                else raw
            )
            if self.family == "mysql" and kind == "page_limit":
                self.parameter("page", index, self.base + index + 1, wire)
                return
            if self.family == "postgres":
                cast = {
                    "Int": "BIGINT",
                    "Bool": "BOOLEAN",
                    "Text": "TEXT",
                    "Decimal": "NUMERIC",
                }[tag]
            elif tag == "Decimal":
                _need(
                    type(precision) is int
                    and type(scale) is int
                    and 1 <= precision <= 65
                    and 0 <= scale <= min(precision, 30),
                    "PAGE_TYPE",
                )
                cast = f"DECIMAL({precision},{scale})"
            else:
                cast = {
                    "Int": "SIGNED",
                    "Bool": "SIGNED",
                    "Text": "CHAR CHARACTER SET utf8mb4",
                }[tag]
            self.take("CAST(")
            self.parameter("page", index, self.base + index + 1, wire)
            self.take(" AS " + cast + ")")
        else:
            raise ValueError("REFINEMENT_EXPRESSION_KIND")

    def order(self, value):
        _need(type(value) is Order and value.direction in ("asc", "desc"), "ORDER")
        self.expression(value.value)
        self.take(" ASC" if value.direction == "asc" else " DESC")

    def source(self, value):
        if type(value) is Relation:
            self.list(value.name, self.identifier, ".")
            self.take(" AS ")
            self.identifier(value.alias)
        else:
            _need(
                type(value) is Join
                and value.kind in ("INNER", "CROSS", "LEFT", "RIGHT", "FULL"),
                "JOIN",
            )
            self.take("(")
            self.source(value.left)
            self.take(" " + value.kind + " JOIN ")
            self.source(value.right)
            if value.kind != "CROSS":
                self.take(" ON ")
                self.expression(value.condition)
            self.take(")")

    def query(self, value):
        if type(value) is SetQuery:
            _need(
                value.kind in ("UNION", "INTERSECT", "EXCEPT")
                and value.quantifier in ("ALL", "DISTINCT"),
                "SET",
            )
            self.take("(")
            self.query(value.left)
            self.take(") " + value.kind + " " + value.quantifier + " (")
            self.query(value.right)
            self.take(")")
            return
        _need(type(value) is Select, "SELECT")
        self.take("SELECT DISTINCT " if value.distinct else "SELECT ")
        for i, (name, expression) in enumerate(value.columns):
            if i:
                self.take(", ")
            self.expression(expression)
            self.take(" AS ")
            self.identifier(name)
        self.take(" FROM ")
        self.source(value.source)
        if value.where is not None:
            self.take(" WHERE ")
            self.expression(value.where)
        if value.groups:
            self.take(" GROUP BY ")
            self.list(value.groups, self.expression)
        if value.orders:
            self.take(" ORDER BY ")
            self.list(value.orders, self.order)
        if value.limit is not None:
            self.take(" LIMIT ")
            self.expression(
                value.limit if type(value.limit) is Expr else integer(value.limit)
            )
        if value.offset:
            self.take(" OFFSET ")
            self.expression(integer(value.offset))

    def run(self):
        statement = self.native.statement
        if statement.ctes:
            self.take("WITH RECURSIVE " if statement.recursive else "WITH ")
            for i, cte in enumerate(statement.ctes):
                if i:
                    self.take(", ")
                self.identifier(cte.name)
                self.take(" (")
                self.list(cte.columns, self.identifier)
                self.take(") AS (")
                self.query(cte.query)
                self.take(")")
            self.take(" ")
        self.query(statement.query)
        _need(
            self.position == len(self.text) and len(self.uses) == len(self.native.uses),
            "NATIVE_COVERAGE",
        )
        if self.family == "mysql":
            expected = tuple(item[3] for item in self.uses)
        else:
            seen = {}
            for domain, owner, index, value in self.uses:
                if index in seen:
                    old_domain, old_owner, old_value = seen[index]
                    _need(
                        domain == old_domain
                        and (
                            owner is old_owner
                            if domain == "original"
                            else owner == old_owner
                        )
                        and _same(value, old_value),
                        "PARAMETER_REUSE",
                    )
                else:
                    seen[index] = (domain, owner, value)
            _need(sorted(seen) == list(range(1, len(seen) + 1)), "PARAMETER_GAP")
            expected = tuple(seen[i][2] for i in range(1, len(seen) + 1))
        _need(_same(self.native.arguments, expected), "NATIVE_ARGUMENTS")


def page_syntax(value, frontier, size):
    """A checked segment expression is not authority for completed progress."""
    from pietto._project.project_refinement_order import check_coordinates

    unit = value.units[-1]
    _need(type(size) is int and 0 < size < 2**63, "PAGE_SIZE")
    coordinates = unit.order_coordinates + _shift(
        unit.coordinates, len(unit.order_coordinates)
    )
    controls = ()
    predicate = None
    if frontier is not None:
        controls = check_coordinates(frontier, coordinates)
        arguments = []
        for index, coordinate in enumerate(coordinates):
            domain = dict(coordinate.domain)
            arguments.append(
                Expr(
                    "page",
                    (
                        index,
                        coordinate.tag,
                        domain.get("precision"),
                        domain.get("scale"),
                    ),
                )
            )
        orders = value.statement.query.orders
        predicate = before(
            tuple(arguments),
            tuple(o.value for o in orders),
            tuple(o.direction for o in orders),
            value.original.request.family,
        )
    limit = Expr("page_limit", (len(controls), "Int", None, None))
    query = replace(value.statement.query, where=predicate, limit=limit)
    return replace(value.statement, query=query), controls + (size,)


def verify_native(native, value, *, frontier=None, size=None):
    verify_refinement(value)
    _need(
        type(native) is NativeStatement
        and type(native.sql) is bytes
        and type(native.uses) is tuple
        and type(native.arguments) is tuple,
        "NATIVE_ROOT",
    )
    if size is None:
        _need(frontier is None, "PAGE_CONTEXT")
        expected, controls = value.statement, ()
    else:
        expected, controls = page_syntax(value, frontier, size)
    _need(_same(native.statement, expected), "PAGE_STATEMENT")
    limits = _syntax_resources(native.statement, value.original.request)
    _need(
        len(native.sql) <= limits["sql_bytes"]
        and len(native.uses) <= limits["parameters"],
        "RESOURCE_LIMIT",
    )
    _Bytes(native, value.original, controls).run()
    return controls
