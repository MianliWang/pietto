"""Compositional private lowering over the complete verified emission DAG."""

from dataclasses import dataclass, replace

from pietto._project.project_refinement import UnitRefinement
from pietto._project.project_refinement_order import (
    before,
    equality,
    integer_coordinate,
    scalar_coordinate,
)
from pietto._project.project_refinement_rendering import (
    CTE,
    Expr,
    Join,
    Order,
    Relation,
    Select,
    SetQuery,
    Statement,
    conjunction,
    integer,
    ref,
)
from pietto._project.project_refinement_windows import lower_window
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
from pietto._project.project_sql_emission_contract import BoundSource
from pietto._project.project_sql_emission_joins import JoinBody, NATIVE_KINDS
from pietto._project.project_sql_emission_results import RowResultBody
from pietto._project.project_sql_emission_sets import SetBody
from pietto._project.project_sql_emission_windows import WindowColumn

__all__: tuple[str, ...] = ()


@dataclass(frozen=True)
class Input:
    name: str
    fields: tuple[str, ...]
    key_names: tuple[str, ...]
    coordinates: tuple
    order_names: tuple[str, ...] = ()
    order_coordinates: tuple = ()
    directions: tuple[str, ...] = ()
    dependency: int = -1


def relocated(coordinates, offset, active=()):
    return tuple(
        replace(c, active=active + tuple((i + offset, v) for i, v in c.active))
        for c in coordinates
    )


def lower(output, sources):
    original = output.artifact
    request = original.request
    family = request.family
    from pietto._project.project_sql_emission_ast import resource_limits

    limits = resource_limits(request)
    reserved = {f.column for s in request.sources for f in s.fields}
    reserved.update(c.label for u in output.units for c in u.columns)
    if family == "mysql":
        reserved = {n.casefold() for n in reserved}
    prefix = "__pietto_r2_"
    suffix = 0
    while any(n.startswith(prefix) for n in reserved):
        suffix += 1
        prefix = "__pietto_r2_" + str(suffix) + "_"
    ctes: list[CTE] = []
    from pietto._project.project_refinement_rendering import syntax_work

    charged_nodes = 0
    units = []
    inputs = {}

    def names(kind, count):
        if count > limits["columns"]:
            raise ValueError("REFINEMENT_RESOURCE_LIMIT")
        return tuple(prefix + kind + str(i) for i in range(count))

    def values(alias, fields):
        return tuple(ref(alias, n) for n in fields)

    def publish(name, columns, source, **options):
        nonlocal charged_nodes
        if len(columns) > limits["columns"]:
            raise ValueError("REFINEMENT_RESOURCE_LIMIT")
        query = Select(tuple(columns), source, **options)
        cte = CTE(name, tuple(n for n, _ in columns), query)
        charged_nodes += syntax_work(cte, limits["nodes"] - charged_nodes)
        ctes.append(cte)
        return query

    def exists(source, alias, condition):
        return Expr(
            "exists",
            (
                Select(
                    ((prefix + "one", integer(1)),),
                    Relation((source,), alias),
                    condition,
                ),
            ),
        )

    def source_input(source):
        return inputs[source]

    def input_of(producer):
        return (
            source_input(producer)
            if type(producer) is BoundSource
            else inputs[producer]
        )

    from pietto._project.project_result_output import source_read_columns

    source_reads = source_read_columns(output)
    for position, requirement in enumerate(sources):
        source = requirement.source
        name = prefix + "source" + str(position)
        alias = prefix + "base"
        fields = source_reads[position]
        key_names = names("k", 1 + len(requirement.token_columns))
        coordinates = (
            integer_coordinate(("source", position), position, position),
        ) + tuple(
            integer_coordinate(("source", position, "token", j))
            for j in range(len(requirement.token_columns))
        )
        columns = [(n, ref(alias, n)) for n in fields]
        columns += [(key_names[0], Expr("cast_integer", (integer(position),)))]
        columns += [
            (n, Expr("cast_integer", (ref(alias, physical),)))
            for n, physical in zip(
                key_names[1:], requirement.token_columns, strict=True
            )
        ]
        publish(name, columns, Relation((source.namespace, source.name), alias))
        inputs[source] = Input(
            name, fields, key_names, coordinates, dependency=-position - 1
        )

    select_names = {}
    if type(original.ast) is SQLSelect:
        select_names = {
            c.body: tuple(s.name for s in c.columns) for c in original.ast.ctes
        }

    def named_input(scan):
        if type(scan) in (SQLScan, RowScan):
            return source_input(scan.realization)
        if type(scan) is SQLNamedUse:
            return inputs[scan.cte.body]
        return inputs[scan.body]

    def set_all_step(left, right, labels, kind, name):
        """Pair equal-class successors; no count, rank, or copy ordinal.

        The recursive native operation is resource bounded by the attempt, and
        normal completion is required. A recursion/deadline refusal is never
        EOF. Keys only label copies; public values come from the exact quotient.
        """
        a, b, middle, p = (name + suffix for suffix in ("a", "b", "m", "p"))
        all_keys = (left, right)
        if any(
            len(inp.key_names) * (len(inp.key_names) + 1) // 2 > limits["nodes"]
            for inp in all_keys
        ):
            raise ValueError("REFINEMENT_RESOURCE_LIMIT")
        successor_names = []
        for side, operand in enumerate(all_keys):
            current = values(a, operand.key_names)
            following = values(b, operand.key_names)
            inside = values(middle, operand.key_names)
            ds = ("asc",) * len(current)
            no_between = Expr(
                "not",
                (
                    exists(
                        operand.name,
                        middle,
                        conjunction(
                            equality(values(a, labels), values(middle, labels)),
                            before(current, inside, ds, family),
                            before(inside, following, ds, family),
                        ),
                    ),
                ),
            )
            relation = Join(
                Relation((operand.name,), a),
                Relation((operand.name,), b),
                "INNER",
                conjunction(
                    equality(values(a, labels), values(b, labels)),
                    before(current, following, ds, family),
                ),
            )
            sn = name + "successor" + str(side)
            successor_names.append(sn)
            publish(
                sn,
                tuple(zip(names("c", len(current)), current, strict=True))
                + tuple(zip(names("n", len(current)), following, strict=True)),
                relation,
                where=no_between,
            )

        left_keys, right_keys = values(a, left.key_names), values(b, right.key_names)
        pair_left, pair_right = names("l", len(left_keys)), names("r", len(right_keys))
        initial = equality(values(a, labels), values(b, labels))
        for operand, scope, keys in ((left, a, left_keys), (right, b, right_keys)):
            initial = conjunction(
                initial,
                Expr(
                    "not",
                    (
                        exists(
                            operand.name,
                            middle,
                            conjunction(
                                equality(values(middle, labels), values(scope, labels)),
                                before(
                                    values(middle, operand.key_names),
                                    keys,
                                    ("asc",) * len(keys),
                                    family,
                                ),
                            ),
                        ),
                    ),
                ),
            )
        anchor = Select(
            tuple(zip(pair_left + pair_right, left_keys + right_keys, strict=True)),
            Join(
                Relation((left.name,), a), Relation((right.name,), b), "INNER", initial
            ),
        )
        pair_name = name + "pairs"
        advance = Join(
            Relation((pair_name,), p),
            Relation((successor_names[0],), a),
            "INNER",
            equality(values(p, pair_left), values(a, names("c", len(pair_left)))),
        )
        advance = Join(
            advance,
            Relation((successor_names[1],), b),
            "INNER",
            equality(values(p, pair_right), values(b, names("c", len(pair_right)))),
        )
        step = Select(
            tuple(
                zip(
                    pair_left + pair_right,
                    values(a, names("n", len(pair_left)))
                    + values(b, names("n", len(pair_right))),
                    strict=True,
                )
            ),
            advance,
        )
        ctes.append(
            CTE(
                pair_name,
                pair_left + pair_right,
                SetQuery(anchor, step, "UNION", "ALL"),
            )
        )
        quotient = name + "classes"
        publish(
            quotient,
            tuple(zip(labels, values(a, labels), strict=True)),
            Relation((left.name,), a),
            distinct=True,
        )
        paired = exists(pair_name, p, equality(values(p, pair_left), left_keys))
        selected = paired if kind == "INTERSECT" else Expr("not", (paired,))
        public = tuple(zip(labels, values(b, labels), strict=True))
        keys = tuple(zip(left.key_names, left_keys, strict=True))
        publish(
            name,
            public + keys,
            Join(
                Relation((left.name,), a),
                Relation((quotient,), b),
                "INNER",
                equality(values(a, labels), values(b, labels)),
            ),
            where=selected,
        )
        return Input(name, labels, left.key_names, left.coordinates)

    recursive = False
    for address, unit in enumerate(output.units):
        first = len(ctes)
        terminal = prefix + "unit" + str(address)
        public_names = select_names.get(
            unit, tuple(s.name for s in getattr(unit, "cte_columns", ()))
        )
        if not public_names:
            public_names = tuple(c.label for c in unit.columns)
        if family == "mysql" and len({n.casefold() for n in public_names}) != len(
            public_names
        ):
            public_names = names("v", len(public_names))
        order_exprs, order_coordinates, directions = (), (), ()
        capacity = "structural_keys"
        dependencies = ()
        if type(unit) is SetBody:
            widths = tuple(len(input_of(o.producer).coordinates) for o in unit.operands)
            if (unit.kind.value, unit.quantifier.value) == ("union", "all") and 1 + sum(
                widths
            ) + len(public_names) > limits["columns"]:
                raise ValueError("REFINEMENT_RESOURCE_LIMIT")
            if (
                unit.quantifier.value == "all"
                and unit.kind.value != "union"
                and 2 * max(widths) > limits["columns"]
            ):
                raise ValueError("REFINEMENT_RESOURCE_LIMIT")
            rule = "set_" + unit.kind.value + "_" + unit.quantifier.value
            operands = []
            for j, operand in enumerate(unit.operands):
                inp = input_of(operand.producer)
                alias = operand.symbol.name
                name = terminal + "operand" + str(j)
                columns = tuple(
                    (n, ref(alias, c.name))
                    for n, c in zip(public_names, operand.columns, strict=True)
                )
                columns += tuple(
                    zip(inp.key_names, values(alias, inp.key_names), strict=True)
                )
                publish(name, columns, Relation((inp.name,), alias))
                operands.append(replace(inp, name=name, fields=public_names))
            dependencies = tuple(o.dependency for o in operands)
            kind, quantifier = unit.kind.value.upper(), unit.quantifier.value.upper()
            if (kind, quantifier) == ("UNION", "ALL"):
                coordinates = [
                    integer_coordinate((address, "branch"), 0, len(operands) - 1)
                ]
                for j, inp in enumerate(operands):
                    coordinates.extend(
                        relocated(inp.coordinates, len(coordinates), ((0, j),))
                    )
                coordinates = tuple(coordinates)
                key_names = names("k", len(coordinates))
                queries = []
                for j, inp in enumerate(operands):
                    alias = terminal + "union"
                    key_exprs = [Expr("cast_integer", (integer(j),))]
                    for k, other in enumerate(operands):
                        key_exprs.extend(
                            values(alias, other.key_names)
                            if k == j
                            else (Expr("null", ()),) * len(other.key_names)
                        )
                    queries.append(
                        Select(
                            tuple(
                                zip(
                                    public_names,
                                    values(alias, public_names),
                                    strict=True,
                                )
                            )
                            + tuple(zip(key_names, key_exprs, strict=True)),
                            Relation((inp.name,), alias),
                        )
                    )
                combined = queries[0]
                for query in queries[1:]:
                    combined = SetQuery(combined, query, "UNION", "ALL")
                ctes.append(CTE(terminal, public_names + key_names, combined))
            elif quantifier == "DISTINCT":
                queries = [
                    Select(
                        tuple(
                            zip(public_names, values("s", public_names), strict=True)
                        ),
                        Relation((inp.name,), "s"),
                    )
                    for inp in operands
                ]
                combined = queries[0]
                for query in queries[1:]:
                    combined = SetQuery(combined, query, kind, "DISTINCT")
                quotient = terminal + "quotient"
                ctes.append(CTE(quotient, public_names, combined))
                coordinates = (integer_coordinate((address, "class"), 0, 0),) + tuple(
                    scalar_coordinate((address, "class", i), c.realization)
                    for i, c in enumerate(unit.columns)
                )
                key_names = names("k", len(coordinates))
                key_exprs = (Expr("cast_integer", (integer(0),)),) + values(
                    "s", public_names
                )
                publish(
                    terminal,
                    tuple(zip(public_names, values("s", public_names), strict=True))
                    + tuple(zip(key_names, key_exprs, strict=True)),
                    Relation((quotient,), "s"),
                )
            else:
                recursive = True
                capacity = "structural_successor_pairing_native_resource_terminal"
                current = operands[0]
                for j, operand in enumerate(operands[1:]):
                    current = set_all_step(
                        current, operand, public_names, kind, terminal + "fold" + str(j)
                    )
                coordinates, key_names = current.coordinates, current.key_names
                publish(
                    terminal,
                    tuple((n, ref("s", n)) for n in public_names + key_names),
                    Relation((current.name,), "s"),
                )
        elif type(unit) is JoinBody:
            rule = "join_" + unit.join.kind.value
            left, right = unit.inputs
            li, ri = input_of(left.producer), input_of(right.producer)
            dependencies = (li.dependency, ri.dependency)
            la, ra = left.symbol.name, right.symbol.name
            if family == "mysql" and unit.join.kind.value in ("left", "right"):
                side = 1 if unit.join.kind.value == "left" else 0
                inp = ri if side else li
                materialized = terminal + "nullable" + str(side)
                # Including the complete injective key makes DISTINCT a bijection.
                # It prevents MySQL merging/folding nullable derived constants.
                fields = inp.fields + inp.order_names + inp.key_names
                publish(
                    materialized,
                    tuple((n, ref("s", n)) for n in fields),
                    Relation((inp.name,), "s"),
                    distinct=True,
                )
                if side:
                    ri = replace(inp, name=materialized)
                else:
                    li = replace(inp, name=materialized)
            condition = conjunction(
                *(
                    Expr(
                        "=",
                        (
                            ref(e.left_scope.name, e.left.name),
                            ref(e.right_scope.name, e.right.name),
                        ),
                    )
                    for e in unit.equalities
                ),
                None
                if unit.predicate is None
                else Expr("original_scalar", (unit.predicate, "")),
            )
            columns = [
                (n, ref(c.scope.name, c.read.name))
                for n, c in zip(public_names, unit.columns, strict=True)
            ]
            predicate = None
            if unit.membership is not None:
                relation = Relation((li.name,), la)
                predicate = exists(ri.name, ra, condition)
                if unit.membership == "not_exists":
                    predicate = Expr("not", (predicate,))
                coordinates, key_exprs = li.coordinates, values(la, li.key_names)
            else:
                native_kind = NATIVE_KINDS[unit.join.kind].split()[0]
                relation = Join(
                    Relation((li.name,), la),
                    Relation((ri.name,), ra),
                    native_kind,
                    condition,
                )
                coordinates, key_exprs = [], []
                for side, inp, scope in ((0, li, la), (1, ri, ra)):
                    presence = len(coordinates)
                    coordinates.append(
                        integer_coordinate((address, "presence", side), 0, 1)
                    )
                    coordinates.extend(
                        relocated(inp.coordinates, presence + 1, ((presence, 1),))
                    )
                    key_exprs.append(
                        Expr(
                            "cast_integer",
                            (
                                Expr(
                                    "case",
                                    (
                                        Expr(
                                            "is_null", (ref(scope, inp.key_names[0]),)
                                        ),
                                        integer(0),
                                        integer(1),
                                    ),
                                ),
                            ),
                        )
                    )
                    key_exprs.extend(values(scope, inp.key_names))
                coordinates, key_exprs = tuple(coordinates), tuple(key_exprs)
            key_names = names("k", len(coordinates))
            columns.extend(zip(key_names, key_exprs, strict=True))
            publish(terminal, columns, relation, where=predicate)
        else:
            scan = unit.scan
            inp = named_input(scan)
            dependencies = (inp.dependency,)
            alias = scan.symbol.name
            relation_name = inp.name
            key_exprs, coordinates = values(alias, inp.key_names), inp.coordinates
            if type(scan) in (RowNamedUse, SQLNamedUse):
                key_exprs = (Expr("cast_integer", (integer(address),)),) + key_exprs
                coordinates = (
                    integer_coordinate((address, "use"), address, address),
                ) + relocated(coordinates, 1)
            order_exprs = values(alias, inp.order_names)
            order_coordinates, directions = inp.order_coordinates, inp.directions
            aggregation = getattr(unit, "aggregation", None)
            predicate = getattr(unit, "predicate", None)
            predicate = (
                None
                if predicate is None
                else Expr("original_scalar", (predicate.value, alias))
            )
            if getattr(unit, "window", None) is not None and predicate is not None:
                # WHERE belongs before the original window's input relation.
                # Materialize that boundary once, without duplicating or
                # rebinding its retained scalar expression inside member scans.
                relation_name = terminal + "filtered"
                publish(
                    relation_name,
                    tuple(
                        (name, ref(alias, name))
                        for name in inp.fields + inp.key_names + inp.order_names
                    ),
                    Relation((inp.name,), alias),
                    where=predicate,
                )
                predicate = None
            columns = []
            groups = ()
            rule = "projection"
            if aggregation is not None:
                rule = "global" if not aggregation.keys else "grouped"
                groups = tuple(ref(alias, c.read.name) for c in aggregation.keys)
                key_exprs = (Expr("cast_integer", (integer(0),)),) + groups
                coordinates = (integer_coordinate((address, "group"), 0, 0),) + tuple(
                    scalar_coordinate((address, "group", i), c.read.realization)
                    for i, c in enumerate(aggregation.keys)
                )
                order_exprs, order_coordinates, directions = (), (), ()
            if type(unit) is RowResultBody:
                rule = "result"
                if unit.distinct is not None:
                    quotient = terminal + "quotient"
                    publish(
                        quotient,
                        tuple(
                            (c.read.name, ref(alias, c.read.name)) for c in unit.columns
                        ),
                        Relation((inp.name,), alias),
                        distinct=True,
                    )
                    relation_name = quotient
                    key_exprs = (Expr("cast_integer", (integer(0),)),) + tuple(
                        ref(alias, c.read.name) for c in unit.columns
                    )
                    coordinates = (
                        integer_coordinate((address, "class"), 0, 0),
                    ) + tuple(
                        scalar_coordinate((address, "class", i), c.column.realization)
                        for i, c in enumerate(unit.columns)
                    )
                    order_exprs, order_coordinates, directions = (), (), ()
                if unit.order is not None:
                    order_exprs = tuple(
                        ref(alias, item.read.name) for item in unit.order.items
                    )
                    order_coordinates = tuple(
                        scalar_coordinate((address, "order", i), item.read.realization)
                        for i, item in enumerate(unit.order.items)
                    )
                    directions = tuple(item.direction for item in unit.order.items)
            for position, column in enumerate(unit.columns):
                if type(unit) is SQLSelect:
                    value = (
                        Expr("original_scalar", (column.value, alias))
                        if type(column) is SQLLiteralColumn and column.value is not None
                        else ref(alias, column.symbol.name)
                    )
                elif type(column) is AggregateValueColumn:
                    value = Expr("original_aggregate", (column, alias))
                elif type(column) is WindowColumn:
                    width = len(inp.key_names) + len(column.specification.orders)
                    if width * (width + 1) // 2 > limits["nodes"]:
                        raise ValueError("REFINEMENT_RESOURCE_LIMIT")
                    rule = "window"
                    capacity = "original_native_call_range_structural_frame_endpoints"
                    extra, value = lower_window(
                        column,
                        request,
                        relation_name,
                        alias,
                        inp.key_names,
                        terminal + "w" + str(position),
                    )
                    ctes.extend(extra)
                elif hasattr(column, "read"):
                    value = ref(alias, column.read.name)
                else:
                    if type(column) is not RowValueColumn:
                        raise ValueError("REFINEMENT_ORIGINAL_COLUMN")
                    value = Expr("original_scalar", (column.value, alias))
                columns.append((public_names[position], value))
            key_names = names("k", len(coordinates))
            order_names = names("o", len(order_exprs))
            columns.extend(zip(key_names, key_exprs, strict=True))
            columns.extend(zip(order_names, order_exprs, strict=True))
            ordering = ()
            limit = None
            if type(unit) is RowResultBody:
                ordering = tuple(
                    Order(v, d) for v, d in zip(order_exprs, directions, strict=True)
                )
                ordering += tuple(Order(v) for v in key_exprs)
                limit = None if unit.limit is None else unit.limit.value
            publish(
                terminal,
                columns,
                Relation((relation_name,), alias),
                where=predicate,
                groups=groups,
                orders=ordering,
                limit=limit,
            )
        order_names = names("o", len(order_exprs))
        result = UnitRefinement(
            unit,
            address,
            rule,
            dependencies,
            tuple(ctes[first:]),
            terminal,
            public_names,
            key_names,
            tuple(coordinates),
            order_names,
            tuple(order_coordinates),
            directions,
            capacity,
        )
        units.append(result)
        inputs[unit] = Input(
            terminal,
            public_names,
            key_names,
            tuple(coordinates),
            order_names,
            tuple(order_coordinates),
            directions,
            address,
        )
    final = units[-1]
    alias = prefix + "result"
    final_columns = tuple(
        (column.label, ref(alias, name))
        for column, name in zip(output.columns, final.public_names, strict=True)
    )
    final_columns += tuple(
        (n, ref(alias, n)) for n in final.order_names + final.key_names
    )
    final_orders = tuple(
        Order(ref(alias, n), d)
        for n, d in zip(
            final.order_names + final.key_names,
            final.directions + ("asc",) * len(final.key_names),
            strict=True,
        )
    )
    statement = Statement(
        tuple(ctes),
        Select(final_columns, Relation((final.terminal,), alias), orders=final_orders),
        recursive,
    )
    syntax_work(statement, limits["nodes"])
    return tuple(units), statement, prefix
