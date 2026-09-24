"""Window-stage SQL construction for the admitted Phase66 window emission.

The window stage reads its exact established pre-window input, computes every
selected and hidden occurrence as its own result column, and hands those columns
to an outer QUALIFY filter and to the final visible projection. Grouping is
acquisition topology: two declarations that spell the same window over the same
input stay two occurrences unless the retained authority says they are one.

This module owns the window-specific construction only. The renderer turns the
returned nodes into bytes, and the independent verifier re-derives them, so no
SQL text is authority here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_emission_rows as rows
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueTypeKind
from pietto.semantic.window_semantics import (
    WindowFrameExclusion,
    WindowNthDirection,
    WindowNullTreatment,
)

# R14 admits exactly these eleven function identities. The spelling map is the
# only place an identity becomes SQL, and it is keyed by the retained identity
# name rather than by an authored spelling.
SPELLING = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
    "first_value": "FIRST_VALUE",
    "last_value": "LAST_VALUE",
    "nth_value": "NTH_VALUE",
}
RANKING = frozenset({"row_number", "rank", "dense_rank"})
DISTRIBUTION = frozenset({"percent_rank", "cume_dist", "ntile"})
NAVIGATION = frozenset({"lag", "lead"})
# R15 owns these three: their result is determined by the effective frame, never
# by ORDER BY alone.
FRAME_VALUE = frozenset({"first_value", "last_value", "nth_value"})
FRAME_INSENSITIVE = RANKING | DISTRIBUTION | NAVIGATION
# The admitted argument arity of every promised identity. A ranking function
# with no scalar argument still depends on the whole input BAG, which the plan
# records as its own relation_input use rather than as an argument.
ARITY = {
    "row_number": (0, 0),
    "rank": (0, 0),
    "dense_rank": (0, 0),
    "percent_rank": (0, 0),
    "cume_dist": (0, 0),
    "ntile": (1, 1),
    "lag": (1, 3),
    "lead": (1, 3),
    "first_value": (1, 1),
    "last_value": (1, 1),
    "nth_value": (2, 2),
}

# One rule per retained window demand subject. R14 owns the computation and its
# inputs, R15 owns frames and named components, R17 owns the visible result.
# The retained window demands, keyed by the subject each one witnesses: R14 owns
# the occurrence, its input uses and its arguments, R15 owns the realized frame,
# modifiers and named components, and R17 owns the visible result projection.
DEMAND_RULES = {
    "window": "R14",
    "window_use": "R14",
    "window_argument": "R14",
    "window_policy": "R15",
    "window_projection": "R17",
}

# R15: GROUPS and EXCLUDE are PostgreSQL only for the Phase66 baseline. MySQL
# keeps a typed blocker and is never given an emulation.
FRAME_UNIT_TARGETS = {
    "rows": frozenset({"postgres", "mysql"}),
    "range": frozenset({"postgres", "mysql"}),
    "groups": frozenset({"postgres"}),
}
EXCLUSION_TARGETS = {
    WindowFrameExclusion.NO_OTHERS: frozenset({"postgres", "mysql"}),
    WindowFrameExclusion.CURRENT_ROW: frozenset({"postgres"}),
    WindowFrameExclusion.GROUP: frozenset({"postgres"}),
    WindowFrameExclusion.TIES: frozenset({"postgres"}),
}
BOUND_SPELLING = {
    "unbounded_preceding": "UNBOUNDED PRECEDING",
    "current_row": "CURRENT ROW",
    "unbounded_following": "UNBOUNDED FOLLOWING",
}
OFFSET_BOUNDS = {"offset_preceding": "PRECEDING", "offset_following": "FOLLOWING"}
UNIT_SPELLING = {"rows": "ROWS", "range": "RANGE", "groups": "GROUPS"}
EXCLUSION_SPELLING = {
    WindowFrameExclusion.CURRENT_ROW: "EXCLUDE CURRENT ROW",
    WindowFrameExclusion.GROUP: "EXCLUDE GROUP",
    WindowFrameExclusion.TIES: "EXCLUDE TIES",
}
# R15: MySQL refuses more than this many windows in one SELECT. The compiler
# counts its own generated computations and definitions rather than trusting
# documentation, and an excess is a typed resource blocker.
MYSQL_WINDOW_LIMIT = 127
# R14/R15 admit V01 signed Int order keys and arguments; ranking and
# distribution Float results travel only through the V06 boundary.
ORDER_TAGS = frozenset({"Int", "Bool", "Text", "Decimal"})
# A ranking result is the target's own signed64 integer; R14 declares that
# premise rather than deriving it from an input's value range. A bucket result is
# the width the target itself returns: PostgreSQL's ntile sends int4 and MySQL's
# sends a bigint, so each family publishes what it actually sends.
RANK_STORAGE = {"postgres": "pg_int8", "mysql": "my_bigint"}
RANK_MAX = (1 << 63) - 1
# R15-INT-OFFSET-V1: every finite frame offset is a signed64 count or distance,
# and every RANGE threshold an exact signed64 value, on both targets.
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1
BUCKET_REALIZATION = {
    "postgres": ("pg_int4", (1 << 31) - 1),
    "mysql": ("my_bigint", (1 << 63) - 1),
}
FLOAT_STORAGE = {"postgres": "pg_float8", "mysql": "my_double"}
# R14-PG-NAVIGATION-RESULT-V1: PostgreSQL's three-argument lag/lead take an
# anycompatible default, so an uncast integer default literal - int4, or int8
# beyond signed32 - joins the value in choosing the result's integer width.
PG_INT_ORDER = ("pg_int2", "pg_int4", "pg_int8")
I32_MIN = -(1 << 31)
I32_MAX = (1 << 31) - 1
# R15-MYSQL-WINDOW-RESULT-V1: MySQL materializes a signed integer window value
# as INT below ten display characters and as BIGINT from ten. Only a source
# column or an earlier window result has a reviewed display - its own field
# class's - and a non-negative LAG/LEAD default literal of d digits displays d+1.
MYSQL_DISPLAY = {"my_smallint": 6, "my_int": 11, "my_bigint": 20}
MYSQL_BIGINT_DISPLAY = 10
VALUE_NULLABILITY = {
    EffectiveNullability.NON_NULL: False,
    EffectiveNullability.NULLABLE: True,
    EffectiveNullability.UNKNOWN: "unknown",
}


def _scalar(value: Any) -> str:
    """One bounded scalar image for a debug repr; never a nested graph."""

    return value if type(value) in {int, str, bool, type(None)} else "..."


def _count(value: Any) -> int | str:
    return len(value) if type(value) is tuple else "?"


def _present(value: Any) -> str:
    return "None" if value is None else "..."


@dataclass(frozen=True, slots=True, eq=False)
class WindowOrigin:
    """One transported value's retained window-stage provenance.

    It rides on the stage column, so a window result stays distinguishable from a
    source field or an aggregate result after any number of carries, named uses or
    outer JOIN ports. Its debug image is bounded: the shared upstream graph stays
    opaque rather than being expanded and truncated afterwards.
    """

    kind: str
    window: Any
    result: Any
    inputs: tuple[Any, ...]
    function: str | None = None
    selected: bool = True
    definition: Any = None
    policy: Any = None

    def __repr__(self) -> str:
        return (
            f"WindowOrigin(kind={_scalar(self.kind)}, "
            f"function={_scalar(self.function)}, "
            f"selected={_scalar(self.selected)}, "
            f"inputs=<{_count(self.inputs)}>, window=..., result=..., "
            f"definition={_present(self.definition)}, "
            f"policy={_present(self.policy)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowArgument:
    """One realized window argument: a pre-window port or an exact literal."""

    position: int
    role: str
    read: Any = None
    literal: str | None = None

    def __repr__(self) -> str:
        return (
            f"WindowArgument(position={_scalar(self.position)}, "
            f"role={_scalar(self.role)}, literal={_scalar(self.literal)}, "
            f"read={_present(self.read)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowFrameSpec:
    """One realized frame: its unit, both bounds and its exclusion."""

    unit: str
    start: tuple[str, Any]
    end: tuple[str, Any]
    exclusion: Any = None

    def __repr__(self) -> str:
        return (
            f"WindowFrameSpec(unit={_scalar(self.unit)}, "
            f"start={_scalar(self.start[0])}, end={_scalar(self.end[0])}, "
            f"exclusion={_present(self.exclusion)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowOrderItem:
    """One window ORDER key with its retained direction and NULL posture."""

    position: int
    read: Any
    direction: str
    nulls: str | None
    binding: Any

    def __repr__(self) -> str:
        return (
            f"WindowOrderItem(position={_scalar(self.position)}, "
            f"direction={_scalar(self.direction)}, nulls={_scalar(self.nulls)}, "
            f"read=..., binding=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowSpecification:
    """One realized OVER specification, direct or named."""

    partitions: tuple[Any, ...]
    orders: tuple[WindowOrderItem, ...]
    frame: WindowFrameSpec | None
    symbol: Any = None
    parent: Any = None

    def __repr__(self) -> str:
        return (
            f"WindowSpecification(partitions=<{_count(self.partitions)}>, "
            f"orders=<{_count(self.orders)}>, "
            f"frame={_present(self.frame)}, symbol={_present(self.symbol)}, "
            f"parent={_present(self.parent)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowDefinition:
    """One generated WINDOW clause definition with a capture-safe symbol."""

    index: int
    symbol: Any
    label: str
    specification: WindowSpecification
    named_use: Any

    def __repr__(self) -> str:
        return (
            f"WindowDefinition(index={_scalar(self.index)}, "
            f"label={_scalar(self.label)}, specification=..., named_use=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowColumn:
    """One window occurrence and its own distinct stage result column."""

    ordinal: int
    export: Any
    window: Any
    function: str
    arguments: tuple[Any, ...]
    specification: WindowSpecification
    inputs: tuple[Any, ...]
    symbol: Any
    label: str
    column: Any
    selected: bool

    def __repr__(self) -> str:
        return (
            f"WindowColumn(ordinal={_scalar(self.ordinal)}, "
            f"function={_scalar(self.function)}, "
            f"selected={_scalar(self.selected)}, "
            f"arguments=<{_count(self.arguments)}>, "
            f"inputs=<{_count(self.inputs)}>, specification=..., window=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class WindowStage:
    """One realized window stage: its definitions and its occurrences."""

    ref: Any
    definitions: tuple[WindowDefinition, ...]
    columns: tuple[WindowColumn, ...]

    def __repr__(self) -> str:
        return (
            f"WindowStage(definitions=<{_count(self.definitions)}>, "
            f"columns=<{_count(self.columns)}>, ref=...)"
        )


def function_identity(window) -> str | None:
    """The retained identity name, never the authored spelling."""

    identity = getattr(windows.effective(window.source), "identity", None)
    name = getattr(identity, "name", None)
    return name if type(name) is str else None


def unsupported_function(function: str | None):
    """The exact typed blocker one non-promised window identity keeps."""

    return "PIE-B1003", "window_function_not_promised_in_phase66"


def unsupported_modifier(modifiers) -> tuple[str, str] | None:
    """R16: IGNORE NULLS and FROM LAST stay explicit non-support, never erased."""

    if modifiers is None:
        return None
    if modifiers.null_treatment is WindowNullTreatment.IGNORE_NULLS:
        return "PIE-B1003", "window_ignore_nulls_approved_non_support_in_phase66"
    if modifiers.nth_direction is WindowNthDirection.FROM_LAST:
        return "PIE-B1003", "window_from_last_approved_non_support_in_phase66"
    return None


def frame_problem(frame, target: str) -> tuple[str, str] | None:
    """R15: the exact target boundary for one realized frame unit and exclusion."""

    if frame is None:
        return None
    unit = frame.unit
    if unit not in FRAME_UNIT_TARGETS:
        return "PIE-B1003", "window_frame_unit_not_promised_in_phase66"
    if target not in FRAME_UNIT_TARGETS[unit]:
        return "PIE-B1003", f"window_frame_{unit}_approved_non_support_on_{target}"
    exclusion = frame.exclusion
    if exclusion is None or exclusion is WindowFrameExclusion.NO_OTHERS:
        return None
    if target not in EXCLUSION_TARGETS.get(exclusion, frozenset()):
        return "PIE-B1003", f"window_frame_exclusion_approved_non_support_on_{target}"
    return None


def offset_range_problem(frame, orders) -> tuple[str, str] | None:
    """R15: an offset RANGE frame needs its exact single-key arithmetic premise.

    The promise is one ORDER key that is a non-null signed Int, plus a static
    non-negative offset. A second key, a nullable key or a non-Int key changes
    what the frame means, so the combination is blocked rather than emitted.
    """

    if frame is None or frame.unit != "range":
        return None
    if not any(kind in OFFSET_BOUNDS for kind, _ in (frame.start, frame.end)):
        return None
    if len(orders) != 1:
        return "PIE-B1003", "offset_range_requires_exactly_one_order_key"
    realization = orders[0].read.realization
    if realization.tag != "Int":
        return "PIE-B1003", "offset_range_requires_a_signed_int_order_key"
    if realization.nullable is not False:
        return "PIE-B1003", "offset_range_requires_a_non_null_order_key"
    return None


def range_arithmetic_problem(frame, offsets, orders) -> tuple[str, str] | None:
    """R15-INT-OFFSET-V1: each finite RANGE threshold stays an exact signed64 value.

    The threshold is compared with the key, never stored in it, so an offset may
    be wider than the key's own storage. The key's retained domain must sit
    inside that storage, and each actual endpoint's direction-sensitive
    translation of the whole domain must stay inside signed64.
    """

    if frame is None or frame.unit != "range" or not offsets:
        return None
    key = orders[0]
    storage = rows.signed_range(key.read.realization.storage)
    domain = rows.int_bounds(key.read.realization)
    if storage is None or domain is None or domain[0] > domain[1]:
        return "PIE-B1004", "window_range_arithmetic_evidence_missing"
    low, high = domain
    if low < storage[0] or high > storage[1]:
        return "PIE-B1002", "window_range_key_domain_out_of_storage_range"
    for kind, offset in offsets:
        # ASC PRECEDING and DESC FOLLOWING look below the key; the other two above.
        sign = -1 if (kind == "offset_preceding") == (key.direction == "asc") else 1
        if low + sign * offset < I64_MIN or high + sign * offset > I64_MAX:
            return "PIE-B1002", "window_range_boundary_out_of_signed64_range"
    return None


def same_specification(left, right) -> bool:
    """Whether two realized specifications are one complete OVER clause.

    Partition and order reads are compared by identity, directions and NULL
    posture by value, and frames by their realized bound kinds, exact offsets and
    exclusion, so sharing a generated definition never rests on rendered text or
    on declaration identity alone.
    """

    return (
        len(left.partitions) == len(right.partitions)
        and all(a[1] is b[1] for a, b in zip(left.partitions, right.partitions))
        and len(left.orders) == len(right.orders)
        and all(
            a.read is b.read and a.direction == b.direction and a.nulls == b.nulls
            for a, b in zip(left.orders, right.orders)
        )
        and _frame_identity(left.frame) == _frame_identity(right.frame)
    )


def _frame_identity(frame):
    if frame is None:
        return None
    return frame.unit, frame.start, frame.end, frame.exclusion


def resource_problem(target: str, count: int) -> tuple[str, str] | None:
    """R15: MySQL refuses more than 127 windows in one SELECT."""

    if target == "mysql" and count > MYSQL_WINDOW_LIMIT:
        return "PIE-B1005", "mysql_window_count_exceeds_target_resource_limit"
    return None


def demand_rule(entry) -> str | None:
    """The published rule one retained window demand belongs to."""

    if entry.family.value != "window":
        return None
    return DEMAND_RULES.get(entry.subject.kind.value, "R14")


def column_nodes(column) -> int:
    """The node contribution of one window column.

    The builder and the independent verifier both call this, so their totals
    cannot drift apart over an arithmetic detail while each still derives the
    column's meaning from its own source.
    """

    specification = column.specification
    return (
        1
        + len(column.arguments)
        + len(specification.partitions)
        + len(specification.orders)
        + (0 if specification.frame is None else 1)
    )


def node_count(stage: WindowStage, value_nodes) -> int:
    """The bounded node contribution of one realized window stage."""

    return len(stage.definitions) + sum(column_nodes(c) for c in stage.columns)


def windowed_blocks(plan) -> dict[Any, list[Any]]:
    """Every window occurrence, grouped by the block whose stage computes it."""

    owners: dict[Any, list[Any]] = {}
    for window in plan.windows:
        owners.setdefault(window.block, []).append(window)
    return owners


def window_policies(plan) -> dict[Any, Any]:
    """Each window's single retained policy, keyed by the window ref."""

    result: dict[Any, Any] = {}
    for policy in plan.window_policies:
        if policy.window in result:
            return {}
        result[policy.window] = policy
    return result


def window_arguments(plan) -> dict[Any, list[Any]]:
    """Each window's ordered arguments, keyed by the window ref."""

    result: dict[Any, list[Any]] = {}
    for argument in plan.window_arguments:
        result.setdefault(argument.window, []).append(argument)
    for items in result.values():
        items.sort(key=lambda item: item.position)
    return result


def window_uses(plan) -> dict[Any, list[Any]]:
    """Each window's ordered input uses, keyed by the window ref."""

    result: dict[Any, list[Any]] = {}
    for use in plan.window_uses:
        result.setdefault(use.window, []).append(use)
    for items in result.values():
        items.sort(key=lambda item: item.position)
    return result


def _integer_literal(value) -> str | None:
    """One exact structural integer literal, or None when it is not one."""

    return str(value) if type(value) is int and not isinstance(value, bool) else None


def independent_arguments(policy, items, uses, available):
    """Realize this occurrence's arguments from their retained authority.

    A value argument is an established pre-window port. An offset, default,
    bucket or position is a structural static value the analyzer already froze,
    so it is emitted as an exact literal rather than re-extracted from source
    text or reclassified as a caller-bindable slot.
    """

    ports = {u.role_position: u for u in uses if u.role.value == "window_argument"}
    navigation = policy.navigation
    realized: list[WindowArgument] = []
    for item in items:
        role = item.role.value
        if role == "value":
            use = ports.get(0)
            read = None if use is None else available.get(use.input)
            if read is None:
                return None, ("PIE-B1001", "window_value_outside_pre_window_input")
            realized.append(WindowArgument(item.position, role, read=read))
            continue
        if role == "offset":
            fact = None if navigation is None else navigation.offset_fact
            literal = None if fact is None else _integer_literal(fact.effective_value)
            if fact is None or literal is None or fact.omitted or int(literal) < 0:
                return None, ("PIE-B1004", "window_offset_static_evidence_missing")
            realized.append(WindowArgument(item.position, role, literal=literal))
            continue
        if role == "default":
            fact = None if navigation is None else navigation.default_fact
            if fact is None or fact.omitted:
                return None, ("PIE-B1004", "window_default_static_evidence_missing")
            if fact.always_null:
                realized.append(WindowArgument(item.position, role, literal="NULL"))
                continue
            literal = _integer_literal(getattr(fact.expression, "value", None))
            if literal is None:
                return None, (
                    "PIE-B1003",
                    "window_default_literal_kind_not_realized_yet",
                )
            realized.append(WindowArgument(item.position, role, literal=literal))
            continue
        if role == "bucket":
            literal = _integer_literal(policy.bucket_count)
            if literal is None or policy.bucket_count <= 0:
                return None, ("PIE-B1004", "window_bucket_static_evidence_missing")
            realized.append(WindowArgument(item.position, role, literal=literal))
            continue
        if role == "position":
            fact = (
                None if policy.frame_value is None else policy.frame_value.position_fact
            )
            literal = None if fact is None else _integer_literal(fact.effective_value)
            if literal is None or int(literal) <= 0:
                return None, ("PIE-B1004", "window_position_static_evidence_missing")
            realized.append(WindowArgument(item.position, role, literal=literal))
            continue
        return None, ("PIE-B1003", "window_argument_role_not_realized_yet")
    return tuple(realized), None


def _specification(policy, reads, target: str):
    """One realized OVER specification from its exact retained policy."""

    partitions: list[Any] = []
    for binding, read in reads["partition"]:
        if read is None:
            return None, ("PIE-B1001", "window_partition_outside_pre_window_input")
        if read.realization.tag not in ORDER_TAGS:
            return None, ("PIE-B1002", "window_partition_comparison_domain_unsupported")
        partitions.append((binding, read))
    orders: list[WindowOrderItem] = []
    for position, (binding, read) in enumerate(reads["order"]):
        if read is None:
            return None, ("PIE-B1001", "window_order_outside_pre_window_input")
        if read.realization.tag not in ORDER_TAGS:
            return None, ("PIE-B1002", "window_order_comparison_domain_unsupported")
        direction = binding.effective_direction
        if direction not in {"asc", "desc"}:
            return None, ("PIE-B1004", "window_order_direction_evidence_missing")
        orders.append(WindowOrderItem(position, read, direction, None, binding))
    frame, offsets, problem = _frame(policy, target)
    if problem is not None:
        return None, problem
    problem = offset_range_problem(frame, orders) or range_arithmetic_problem(
        frame, offsets, orders
    )
    if problem is not None:
        return None, problem
    return (
        WindowSpecification(tuple(partitions), tuple(orders), frame),
        None,
    )


def _frame(policy, target: str):
    """One realized frame and its finite offsets, or None without a frame.

    A finite offset is an exact non-negative integer count (ROWS, GROUPS) or
    distance (RANGE) inside signed64; it is never bounded by the ORDER key.
    """

    validated = policy.specification.frame
    resolved = getattr(validated, "resolved", None)
    if resolved is None or resolved.unit is None:
        return None, (), None
    unit = resolved.unit.value
    start, end = resolved.start, resolved.end
    if start is None or end is None:
        return None, (), ("PIE-B1004", "window_frame_bound_evidence_missing")
    bounds = []
    offsets = []
    for bound in (start, end):
        kind = bound.kind.value
        if kind in BOUND_SPELLING:
            bounds.append((kind, BOUND_SPELLING[kind]))
            continue
        suffix = OFFSET_BOUNDS.get(kind)
        literal = _integer_literal(getattr(bound.offset, "value", None))
        if suffix is None or literal is None or int(literal) < 0:
            return None, (), ("PIE-B1004", "window_frame_offset_evidence_missing")
        bounds.append((kind, f"{literal} {suffix}"))
        offsets.append((kind, int(literal)))
    frame = WindowFrameSpec(unit, bounds[0], bounds[1], resolved.exclusion)
    problem = frame_problem(frame, target)
    if problem is None and any(offset > I64_MAX for _, offset in offsets):
        problem = "PIE-B1002", "window_frame_offset_out_of_signed64_range"
    return (None, (), problem) if problem is not None else (frame, tuple(offsets), None)


def build_stage(
    request,
    block,
    exports,
    available,
    occurrences,
    policies,
    arguments,
    uses,
    *,
    position_base,
    symbol,
):
    """Realize one window stage: every occurrence keeps its own result column.

    The carried pre-window inputs are already bound by the caller; this builds
    only the appended window results, so two declarations that spell the same
    window over the same input still occupy two distinct columns.
    """

    target = request.family
    columns: list[WindowColumn] = []
    definitions: list[WindowDefinition] = []
    # One generated definition per retained named declaration and complete
    # realized specification, in first-use order. Uses that agree on both share
    # a symbol; a use that extends or refines its declaration keeps its own
    # complete definition, and two distinct declarations never merge because
    # their effective specs look alike.
    declared: list[tuple[Any, WindowDefinition]] = []
    if len(occurrences) != len(exports):
        return None, None, ("PIE-B1001", "window_export_denominator", block.ref, None)
    count = len(occurrences)
    problem = resource_problem(target, count)
    if problem is not None:
        return None, None, (*problem, block.ref, None)
    for offset, window in enumerate(occurrences):
        export = exports[offset]
        if export.source is not window.ref:
            return (
                None,
                None,
                ("PIE-B1001", "window_result_port_drift", window.ref, None),
            )
        function = function_identity(window)
        location = getattr(getattr(window.source, "item", None), "span", None)
        if function is None or function not in SPELLING:
            return None, None, (*unsupported_function(function), window.ref, location)
        policy = policies.get(window.ref)
        if policy is None:
            return (
                None,
                None,
                ("PIE-B1004", "window_policy_evidence_missing", window.ref, location),
            )
        modifier = unsupported_modifier(policy.modifiers)
        if modifier is not None:
            return None, None, (*modifier, window.ref, location)
        reads = {"partition": [], "order": []}
        for use in uses.get(window.ref, ()):
            role = use.role.value
            if role == "window_partition":
                binding = policy.partitions[use.role_position]
                reads["partition"].append((binding, available.get(use.input)))
            elif role == "window_order":
                binding = policy.orders[use.role_position]
                reads["order"].append((binding, available.get(use.input)))
        specification, problem = _specification(policy, reads, target)
        if specification is None:
            assert problem is not None
            return None, None, (*problem, window.ref, location)
        named = policy.named_use
        if named is not None:
            declaration = named.composed.base.target_declaration
            if declaration is None:
                return (
                    None,
                    None,
                    (
                        "PIE-B1004",
                        "window_named_declaration_evidence_missing",
                        window.ref,
                        location,
                    ),
                )
            existing = next(
                (
                    item
                    for owner, item in declared
                    if owner is declaration
                    and same_specification(item.specification, specification)
                ),
                None,
            )
            if existing is None:
                index = len(definitions)
                label = f"w{index}"
                existing = WindowDefinition(
                    index,
                    symbol(index + 1, window.policy, label),
                    label,
                    specification,
                    named,
                )
                definitions.append(existing)
                declared.append((declaration, existing))
            specification = replace(specification, symbol=existing.symbol)
        items = arguments.get(window.ref, ())
        low, high = ARITY[function]
        if not low <= len(items) <= high or len(items) != len(window.arguments):
            return (
                None,
                None,
                (
                    "PIE-B1003",
                    "window_argument_signature_not_admitted",
                    window.ref,
                    location,
                ),
            )
        realized, problem = independent_arguments(
            policy, items, uses.get(window.ref, ()), available
        )
        if realized is None:
            assert problem is not None
            return None, None, (*problem, window.ref, location)
        position = position_base + offset
        label = f"c{position}"
        anchor = specification.orders[0].read if specification.orders else None
        if anchor is None:
            return (
                None,
                None,
                ("PIE-B1004", "window_result_anchor_missing", window.ref, location),
            )
        retained = result_value(window)
        if retained is None:
            return (
                None,
                None,
                (
                    "PIE-B1004",
                    "window_result_logical_type_evidence_missing",
                    window.ref,
                    location,
                ),
            )
        realization, problem = result_realization(target, function, realized, retained)
        if realization is None:
            assert problem is not None
            return None, None, (*problem, window.ref, location)
        origin = WindowOrigin(
            "window_result",
            window,
            export.ref,
            tuple(window.inputs),
            function=function,
            selected=window.selected is not None,
            policy=policy,
        )
        column = WindowColumn(
            position,
            export,
            window,
            function,
            realized,
            specification,
            tuple(window.inputs),
            symbol(position + 1, export.ref, label),
            label,
            stage_column(anchor, position, label, export, origin, realization),
            window.selected is not None,
        )
        columns.append(column)
    return columns, WindowStage(block.ref, tuple(definitions), tuple(columns)), None


def blocks_admitted(plan, *, single_input_use: bool = False) -> bool:
    """Whether every window block in this plan is inside the admitted domain."""

    if not plan.windows:
        return True
    projections = {projection.window for projection in plan.window_projections}
    for window in plan.windows:
        if function_identity(window) not in SPELLING:
            return False
        if window.selected is not None and window.ref not in projections:
            return False
    return True


def stage_column(read, index: int, label: str, export, origin, realization):
    """One window result column carrying its own realization and provenance."""

    return replace(
        read,
        position=index,
        name=label,
        terminal=export.ref,
        scope=None,
        window=origin,
        realization=realization,
        field=None,
        source_port=None,
        literal=None,
        aggregate=None,
    )


def result_value(window):
    """This window result's own retained logical tag and nullability."""

    value_type = windows.result_type(window.source)
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    nullable = VALUE_NULLABILITY.get(value_type.nullability)
    return None if nullable is None else (value_type.resolved_type.name, nullable)


def result_realization(family: str, function: str, arguments, retained):
    """One window result's independently established physical realization.

    A ranking result is the target's own non-null signed64 integer and a bucket
    result is the non-null integer width that target returns, both bounded by
    R14's declared premise rather than by any input's value range. A distribution
    result is the target's own double, travelling only through the V06 boundary.
    A navigation or frame-sensitive result carries its value argument's logical
    type and gains only the possibility of NULL; an Int result's width and
    interval follow its target's own rule over the value and any default.
    """

    tag, nullable = retained
    if function in RANKING or function == "ntile":
        if tag != "Int" or nullable is not False:
            return None, ("PIE-B1002", "window_rank_result_not_non_null_int")
        storage, bound = (
            BUCKET_REALIZATION[family]
            if function == "ntile"
            else (RANK_STORAGE[family], RANK_MAX)
        )
        return (
            rows.Realization(
                "Int",
                {"kind": storage},
                False,
                {"kind": "int_range", "min": "0", "max": str(bound)},
            ),
            None,
        )
    if function in DISTRIBUTION:
        if tag != "Float":
            return None, ("PIE-B1002", "window_distribution_result_not_float")
        return (
            rows.Realization(
                "Float",
                {"kind": FLOAT_STORAGE[family]},
                bool(nullable),
                {"kind": "float64"},
            ),
            None,
        )
    values = [item for item in arguments if item.read is not None]
    if len(values) != 1:
        return None, ("PIE-B1004", "window_value_argument_evidence_missing")
    read = values[0].read
    carrier = read.realization
    if tag != carrier.tag:
        return None, ("PIE-B1002", "window_result_logical_type_drift")
    if family == "mysql" and tag == "Bool":
        # B1: MySQL returns a Bool value's window result as an INT 0/1/NULL,
        # which no reviewed storage describes, so it stays a typed boundary.
        return None, (
            "PIE-B1002",
            "mysql_bool_window_result_representation_not_supported_in_phase66",
        )
    if tag != "Int":
        return (
            rows.Realization(tag, carrier.storage, bool(nullable), carrier.domain),
            None,
        )
    default = next((item.literal for item in arguments if item.role == "default"), None)
    representation, problem = integer_value_result(family, read, default)
    if representation is None:
        return None, problem
    storage, domain = representation
    return rows.Realization("Int", storage, bool(nullable), domain), None


def integer_value_result(family: str, read, default: str | None):
    """One Int navigation or frame-value result's storage and interval enclosure.

    A non-null integer default may be returned, so the interval is the least
    enclosure of the value's interval and that default - never the whole storage
    range, and never the input interval alone. An omitted or NULL default adds
    no value. The storage is the target's own documented choice for this value
    carrier and default literal, never a range read from the data.
    """

    bounds = rows.int_bounds(read.realization)
    kind = read.realization.storage.get("kind")
    number = None if default is None or default == "NULL" else int(default)
    if bounds is None:
        return None, ("PIE-B1004", "window_value_argument_evidence_missing")
    if number is not None and not I64_MIN <= number <= I64_MAX:
        return None, ("PIE-B1002", "window_default_integer_out_of_signed64_range")
    low, high = bounds
    if number is not None:
        low, high = min(low, number), max(high, number)
    if family == "postgres":
        if kind not in PG_INT_ORDER:
            return None, ("PIE-B1004", "window_value_argument_evidence_missing")
        rank = PG_INT_ORDER.index(kind)
        if number is not None:
            rank = max(rank, 1 if I32_MIN <= number <= I32_MAX else 2)
        storage = PG_INT_ORDER[rank]
    else:
        reviewed = (read.field is None) is not (read.window is None)
        display = MYSQL_DISPLAY.get(kind) if reviewed else None
        if display is None or read.aggregate is not None or read.literal is not None:
            return None, (
                "PIE-B1002",
                "mysql_window_integer_result_origin_not_supported_in_phase66",
            )
        if number is not None:
            if number < 0:
                return None, (
                    "PIE-B1003",
                    "window_default_literal_kind_not_realized_yet",
                )
            display = max(display, len(str(number)) + 1)
        storage = "my_int" if display < MYSQL_BIGINT_DISPLAY else "my_bigint"
    limits = rows.signed_range({"kind": storage})
    assert limits is not None
    if low < limits[0] or high > limits[1]:
        return None, ("PIE-B1002", "window_value_domain_out_of_storage_range")
    return (
        {"kind": storage},
        {"kind": "int_range", "min": str(low), "max": str(high)},
    ), None


def plan_projection_type():
    """The retained window projection type, for exact dispatch by identity."""

    return windows.ProjectSQLWindowProjection


@dataclass(frozen=True, slots=True, eq=False)
class WindowProjectionColumn:
    """One visible output that is an established window result port."""

    ordinal: int
    export: Any
    projection: Any
    input_port: Any
    read: Any
    symbol: Any
    label: str
    column: Any

    def __repr__(self) -> str:
        return (
            f"WindowProjectionColumn(ordinal={_scalar(self.ordinal)}, "
            f"label={_scalar(self.label)}, read=..., projection=...)"
        )


def build_projection(
    block, projection, export, terminal, available, position, label, *, symbol
):
    """Realize one visible output that reads an established window result."""

    if projection.block is not block.ref or projection.export is not export.ref:
        return None, ("PIE-B1001", "window_projection_drift", projection.ref, None)
    read = available.get(projection.input)
    if read is None:
        return None, (
            "PIE-B1001",
            "window_projection_outside_result_scope",
            projection.ref,
            None,
        )
    if read.window is None:
        return None, (
            "PIE-B1001",
            "window_projection_reads_non_window_port",
            projection.ref,
            None,
        )
    return (
        WindowProjectionColumn(
            position,
            export,
            projection,
            projection.input,
            read,
            symbol(position + 1, export.ref, label),
            label,
            replace(read, position=position, name=label, terminal=terminal.ref),
        ),
        None,
    )
