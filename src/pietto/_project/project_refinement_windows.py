"""Native frame values over original members and coherent structural choices.

Endpoints select a bounded predecessor/successor using the original finite
offset. No new global row number, group number, or partition count is needed.
"""

from pietto._project.project_refinement_order import before, equality
from pietto._project.project_refinement_rendering import (
    CTE,
    Expr,
    Order,
    Relation,
    Select,
    conjunction,
    disjunction,
    integer,
    ref,
)

__all__: tuple[str, ...] = ()

CHOICE = frozenset(("row_number", "ntile", "lag", "lead"))
PEERS = frozenset(("rank", "dense_rank", "percent_rank", "cume_dist"))


def lower_window(column, request, relation, alias, key_names, prefix):
    specification = column.specification
    partition_names = tuple(read.name for _, read in specification.partitions)
    order_names = tuple(item.read.name for item in specification.orders)
    directions = tuple(item.direction for item in specification.orders)

    def reads(scope, names):
        return tuple(ref(scope, name) for name in names)

    def orders(scope, *, choice=False):
        names = order_names + (key_names if choice else ())
        ds = directions + (("asc",) * len(key_names) if choice else ())
        return tuple(
            Order(value, d) for value, d in zip(reads(scope, names), ds, strict=True)
        )

    if column.function in CHOICE | PEERS:
        return (), Expr(
            "window",
            (
                column,
                alias,
                reads(alias, partition_names),
                orders(alias, choice=column.function in CHOICE),
                False,
            ),
        )
    if column.function not in ("first_value", "last_value", "nth_value"):
        raise ValueError("REFINEMENT_WINDOW_FUNCTION")
    policies = tuple(
        p for p in request.plan.window_policies if p.window is column.window.ref
    )
    if len(policies) != 1:
        raise ValueError("REFINEMENT_WINDOW_POLICY")
    resolved = getattr(policies[0].specification.frame, "resolved", None)
    unit = "range" if resolved is None or resolved.unit is None else resolved.unit.value
    bounds = (("unbounded_preceding", None), ("current_row", None))
    exclusion = None
    if resolved is not None and resolved.unit is not None:
        bounds = tuple(
            (b.kind.value, getattr(b.offset, "value", None))
            for b in (resolved.start, resolved.end)
        )
        exclusion = None if resolved.exclusion is None else resolved.exclusion.value

    z, b = prefix + "member", prefix + "endpoint"
    partition = equality(reads(z, partition_names), reads(alias, partition_names))
    peer_equal = equality(reads(z, order_names), reads(alias, order_names))
    occurrence_equal = equality(reads(z, key_names), reads(alias, key_names))
    ctes = []
    endpoint_relation = relation
    if unit == "groups":
        endpoint_relation = prefix + "peers"
        names = tuple(dict.fromkeys(partition_names + order_names))
        if not names:
            raise ValueError("REFINEMENT_GROUPS_ORDER")
        ctes.append(
            CTE(
                endpoint_relation,
                names,
                Select(
                    tuple((n, ref(b, n)) for n in names),
                    Relation((relation,), b),
                    distinct=True,
                ),
            )
        )

    coordinate_names = order_names + (key_names if unit == "rows" else ())
    coordinate_directions = directions + (
        ("asc",) * len(key_names) if unit == "rows" else ()
    )

    def at_or_after(left, right):
        return (
            disjunction(
                before(right, left, coordinate_directions, request.family),
                equality(left, right),
            )
            if coordinate_names
            else conjunction()
        )

    def membership_bound(kind, offset, lower):
        if kind in ("unbounded_preceding", "unbounded_following"):
            # Original frame verifier excludes the invalid start/end sides.
            return conjunction()
        if kind == "current_row" or offset == 0:
            left, right = reads(z, coordinate_names), reads(alias, coordinate_names)
            return at_or_after(left, right) if lower else at_or_after(right, left)
        if (
            kind not in ("offset_preceding", "offset_following")
            or type(offset) is not int
            or not 0 < offset < 1 << 63
        ):
            raise ValueError("REFINEMENT_FRAME_OFFSET")
        preceding = kind == "offset_preceding"
        if unit == "range":
            if len(order_names) != 1:
                raise ValueError("REFINEMENT_RANGE_ORDER")
            asc = directions[0] == "asc"
            add = preceding != asc
            endpoint = Expr(
                "+" if add else "-",
                (
                    Expr("cast_integer", (ref(alias, order_names[0]),)),
                    integer(offset),
                ),
            )
            # R15 already proves this signed64 threshold for the original
            # complete key domain. The cast prevents narrower SQL arithmetic.
            operator = ">=" if lower == asc else "<="
            return Expr(operator, (ref(z, order_names[0]), endpoint))
        candidates, anchor = reads(b, coordinate_names), reads(alias, coordinate_names)
        strict = (
            before(candidates, anchor, coordinate_directions, request.family)
            if preceding
            else before(anchor, candidates, coordinate_directions, request.family)
        )
        predicate = conjunction(
            equality(reads(b, partition_names), reads(alias, partition_names)),
            strict,
        )
        seek_directions = tuple(
            ("desc" if d == "asc" else "asc") if preceding else d
            for d in coordinate_directions
        )
        seek = tuple(
            Order(v, d) for v, d in zip(candidates, seek_directions, strict=True)
        )

        def select(expression):
            return Select(
                ((prefix + "value", expression),),
                Relation((endpoint_relation,), b),
                predicate,
                orders=seek,
                limit=1,
                offset=offset - 1,
            )

        present = Expr("is_not_null", (Expr("scalar_query", (select(integer(1)),)),))
        endpoint = tuple(Expr("scalar_query", (select(c),)) for c in candidates)
        member = reads(z, coordinate_names)
        included = (
            at_or_after(member, endpoint) if lower else at_or_after(endpoint, member)
        )
        # Before-start and after-end are structural sentinels, never nullable
        # key values or arithmetic positions that can wrap.
        if lower == preceding:
            return disjunction(Expr("not", (present,)), included)
        return conjunction(present, included)

    start, end = bounds
    members = conjunction(
        partition, membership_bound(*start, True), membership_bound(*end, False)
    )
    if exclusion == "current_row":
        members = conjunction(members, Expr("not", (occurrence_equal,)))
    elif exclusion == "group":
        members = conjunction(members, Expr("not", (peer_equal,)))
    elif exclusion == "ties":
        members = conjunction(
            members, disjunction(Expr("not", (peer_equal,)), occurrence_equal)
        )
    elif exclusion not in (None, "no_others"):
        raise ValueError("REFINEMENT_FRAME_EXCLUSION")
    value = Expr("window", (column, z, (), orders(z, choice=True), True))
    query = Select(
        ((prefix + "value", value),),
        Relation((relation,), z),
        members,
        orders=orders(z, choice=True),
        limit=1,
    )
    return tuple(ctes), Expr("scalar_query", (query,))
