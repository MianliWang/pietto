"""The independent DuckDB adapter (AD78.03): compile refusals, artifact,
artifact verifier, document and live template over `ProjectSQLPlan`.

The PostgreSQL/MySQL pipeline never receives the `duckdb` family: this
module reads its own contract (project_duckdb_contract), builds and renders
its own SQL AST (project_duckdb_sql) and serializes its own documents with
the `pietto.sql-emission.v1`/`v2` envelope. It shares only the
family-neutral plan views and the existing suggestion texts. It imports no
duckdb, pyarrow or sqlglot. The rules and their order are those of "Compile
refusals" in docs/spec/duckdb-arrow-route-v1.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import json
import re
from typing import Any

from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_duckdb_contract import (
    FAMILY,
    RELEASE,
    DuckDBContract,
    conflicts,
    read_duckdb_contract,
)
from pietto._project.project_joined_aggregation import (
    ProjectJoinedAggregateOccurrence,
)
from pietto._project.project_duckdb_sql import (
    OPERATORS,
    RELATION,
    DuckDBArithmetic,
    DuckDBColumn,
    DuckDBComparison,
    DuckDBJoin,
    DuckDBLiteral,
    DuckDBLogic,
    DuckDBNullTest,
    DuckDBOrderKey,
    DuckDBParameter,
    DuckDBRead,
    DuckDBSelect,
    Token,
    arithmetic_holds,
    ast_rules_hold,
    int_bounds,
    literal_decimal,
    literal_holds,
    node_count,
    render,
    written,
)
from pietto._project.project_sql_emission_contract import (
    CODES,
    MAX_ARTIFACT_BYTES,
    MAX_NODES,
    MAX_PARAMETERS,
    MAX_SQL_BYTES,
    Blocker,
    Premise,
    _logical_evidence,
    canonical,
)
from pietto._project.project_sql_emission_scopes import (
    reference_source_ports,
    stage_origins,
)
from pietto._project.project_sql_emission_suggestions import blocker_suggestion
from pietto._project.project_sql_plan_expressions import (
    ProjectSQLBinary,
    ProjectSQLBoundLiteral,
    ProjectSQLComparison,
    ProjectSQLIsNull,
    ProjectSQLJoinedReference,
    ProjectSQLLiteral,
    ProjectSQLMatchReference,
    ProjectSQLParameterRead,
    ProjectSQLReference,
    ProjectSQLUnary,
)
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto.semantic.constants import _temporal

__all__: tuple[str, ...] = ()

FORMAT = "pietto.sql-emission.v1"
PARAMETERIZED_FORMAT = "pietto.sql-emission.v2"
COLUMNS = 4096
# The digits of an Arrow decimal128 and of a DuckDB DECIMAL.
MAX_PRECISION = 38
TYPES = ("Int", "Text", "Bool", "Float", "Date", "Timestamp", "Decimal")
# A `having` compares outputs of these types only (the spec's predicates row).
HAVING_TYPES = TYPES[:4]
# The types of a JOIN key: a Decimal key stays refused (D79.28).
KEYS = tuple(name for name in TYPES if name != "Decimal")
# Each admitted JOIN: its kind's keyword and the rows the plan gives it.
_JOINS = {"inner": ("INNER", "matched_pairs"), "left": ("LEFT", "left_preserved")}
# The Python value type of each literal type that the source writes.
_VALUES = {"Int": int, "Text": str, "Bool": bool, "Float": float}
PHYSICAL = {
    "Int": "duckdb_bigint",
    "Float": "duckdb_double",
    "Text": "duckdb_varchar",
    "Bool": "duckdb_boolean",
    "Date": "duckdb_date",
    "Timestamp": "duckdb_timestamp",
    "Decimal": "duckdb_decimal",
}
PREMISES = {
    "client_encoding": "UTF8",
    "operator_environment": "builtin_only",
    "parameter_protocol": "duckdb_prepared",
}
NOT_ADMITTED = ("identifier_case", "session_sql_mode", "session_time_zone")
# Every plan collection that an admitted statement leaves empty.
_EMPTY = (
    "let_values",
    "relationship_matches",
    "single_matches",
    "windows",
    "window_arguments",
    "window_projections",
    "distincts",
    "set_bodies",
    "values_bodies",
    "collects",
    "unnests",
    "expression_block_uses",
    "captures",
    "literal_slots",
    "bind_uses",
)
_SHAPES = (
    (("relation_input", "final_projection"),),
    (("relation_input", "row_filter"), ("final_projection",)),
    (("relation_input", "group_aggregate"), ("final_projection",)),
    (("relation_input", "row_filter"), ("group_aggregate",), ("final_projection",)),
    (("relation_input", "group_aggregate"), ("result_filter",), ("final_projection",)),
    (
        ("relation_input", "row_filter"),
        ("group_aggregate",),
        ("result_filter",),
        ("final_projection",),
    ),
)
# After a JOIN the first block has no relation input of its own.
_JOINED_SHAPES = tuple(((*shape[0][1:],), *shape[1:]) for shape in _SHAPES)
_FILTERS = ("row_filter", "result_filter")
# A number literal as the grammar writes it: no sign and no exponent.
_NUMBER = re.compile(r"[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?")
# The result boundaries of at most one `order by`, then at most one `limit`.
_RESULTS = ((), ("relation_ordering",), ("limit",), ("relation_ordering", "limit"))
# The argument types of each admitted aggregate (rule 7a).
_AGGREGATES = {
    "count": ((), *((tag,) for tag in TYPES)),
    "sum": (("Int",),),
    "min": (("Int",), ("Float",), ("Date",), ("Timestamp",), ("Decimal",)),
    "max": (("Int",), ("Float",), ("Date",), ("Timestamp",), ("Decimal",)),
}

_SUGGESTIONS = {
    "target_release_not_reviewed": f'the reviewed duckdb release is "{RELEASE}"',
    "literal_policy_not_admitted_on_target": (
        "DuckDB emission takes --literal-policy preserve only"
    ),
    "premise_not_admitted_on_target": (
        "remove this premise; the DuckDB route does not use it"
    ),
    "duckdb_relation_shape_not_admitted": (
        "DuckDB emission admits duckdb.arrow source reads joined by inner or"
        " left joins on equalities of fields of one type, such as inner join"
        " customers on orders.customer_id == customers.id, then where, group"
        " by, having, select, order by and limit; right, full and cross joins,"
        " other on conditions, Decimal join keys, windows, qualify, distinct,"
        " set operations, relation lets and derived sources are not available"
        " on DuckDB"
    ),
    "duckdb_source_count_not_admitted": (
        "read one or more duckdb.arrow sources; the DuckDB route runs one query"
        " over the Arrow tables passed to execute()"
    ),
    "duckdb_projection_not_admitted": (
        "select source fields directly, or group by keys and aggregates of"
        " fields, such as select: customer, total = sum(amount), or add,"
        " subtract or multiply two Int or two Float values, one at least a"
        " field or key, such as net = price - discount; other computed values"
        " are not available on DuckDB"
    ),
    "duckdb_arithmetic_range_not_proved": (
        "narrow the int_range of each Int field this value reads so that"
        " every result fits a signed 64-bit integer; DuckDB emission proves"
        " Int arithmetic from those ranges and literals, and an Int parameter"
        " may hold any signed 64-bit value"
    ),
    "duckdb_aggregate_not_admitted": (
        "use count(), count(field), sum of an Int field, or min or max of an Int,"
        " Float, Decimal, Date or Timestamp field; other aggregates, sum or avg"
        " of a Float or a Decimal and aggregates of computed values are not"
        " available on DuckDB"
    ),
    "duckdb_grouping_not_admitted": (
        "group by source fields, such as group by customer; computed keys are"
        " not available on DuckDB"
    ),
    "duckdb_filter_not_admitted": (
        "compare fields or selected outputs with literals or query parameters of"
        " the same type, and join the tests with and, or and not, such as where"
        " amount >= min_amount and note is not None"
    ),
    "duckdb_order_not_admitted": (
        "order by source fields or selected outputs, such as order by total"
        " desc; computed keys are not available on DuckDB"
    ),
    "duckdb_text_literal_nul_not_admitted": (
        "remove NUL from the Text literal; DuckDB emission writes no NUL into SQL text"
    ),
    "duckdb_parameter_not_admitted": (
        "declare non-null Int, Text, Bool, Float, Date, Timestamp or Decimal(p, s)"
        " parameters, p at most 38, and read each one in a where or having"
        " comparison or in selected arithmetic"
    ),
    "duckdb_field_type_not_admitted": (
        "DuckDB emission reads Int, Text, Bool, Float, Date and Timestamp fields"
        " and Decimal(p, s) fields with p at most 38"
    ),
    "source_identifier_unrepresentable": (
        'use the relation namespace "arrow"; the DuckDB route reads registered'
        " Arrow tables"
    ),
    "duckdb_arrow_key_mismatch": (
        "make the contract relation name equal the duckdb.arrow key"
    ),
    "nullability_mismatch": (
        "set nullable to false for a non-null field and true for an optional one"
    ),
    "physical_storage_or_domain_mismatch": (
        "use the DuckDB storage and domain of the field's logical type"
    ),
}


def suggestion(code: str, detail: str) -> str:
    """The DuckDB text of the route's table, the premise rule with the DuckDB
    value, or the existing text the other targets give the same detail."""
    if detail in _SUGGESTIONS:
        return _SUGGESTIONS[detail]
    for key, value in PREMISES.items():
        premise = canonical({"key": key, "scope": "statement", "value": value})
        if detail == f"{key}_declaration_missing":
            return f'add {premise.decode()} to "environment"'
        if detail in {f"{key}_declaration_mismatch", f"{key}_mismatch"}:
            return f"the reviewed duckdb value is {premise.decode()}"
    return blocker_suggestion(code, detail, None)


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBArtifact:
    checked: Any
    contract: DuckDBContract
    policy: Any
    source_map: Any
    assessment: Any
    ast: DuckDBSelect
    sql: bytes
    tokens: tuple[Token, ...]
    document: bytes

    def __repr__(self) -> str:
        return "DuckDBArtifact(checked=..., ast=..., sql=..., document=...)"


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBEmission:
    """One DuckDB emission outcome; only `emit_duckdb_sql` makes a VERIFIED one."""

    status: str
    diagnostics: tuple[Any, ...]
    artifact: DuckDBArtifact | None = None
    blockers: tuple[Blocker, ...] = ()
    cli_errors: tuple[Any, ...] = ()
    family: str | None = FAMILY

    def __repr__(self) -> str:
        return (
            f"DuckDBEmission(status={self.status!r},"
            f" artifact={'present' if self.artifact is not None else 'none'})"
        )


def _key(span: Any) -> tuple[str, int, int]:
    return (span.path or "", span.line, span.column)


def _limits(premises: tuple[Premise, ...]) -> dict[str, int]:
    limits = {
        "sql_bytes": MAX_SQL_BYTES,
        "artifact_bytes": MAX_ARTIFACT_BYTES,
        "nodes": MAX_NODES,
        "parameters": MAX_PARAMETERS,
        "columns": COLUMNS,
    }
    for premise in premises:
        if premise.scope == "statement" and premise.key == "resource_limits":
            for key, value in json.loads(premise.value).items():
                limits[key] = min(limits[key], value)
    return limits


def _spelling(connector: Any) -> str:
    callee = connector.callee
    return getattr(callee, "name", None) or ".".join(callee.parts)


def _ports(plan: Any, source: Any) -> tuple[Any, ...]:
    return tuple(p for p in plan.source_ports if p.owner == source.ref)


def _type_name(port: Any) -> str | None:
    logical = port.field.evidence.resolved_type
    if logical is None or logical.kind is not ProjectResolvedTypeKind.BUILTIN:
        return None
    return logical.name if logical.name in TYPES else None


def _decimal(plan: Any, port: Any) -> tuple[int, int] | None:
    """The declared `Decimal(p, s)` of a source field, through its aliases,
    when `p` is at most MAX_PRECISION; else None (rule 10)."""
    types = plan.scope.completed.semantic_result.module_type_source_resolutions
    fact = _logical_evidence(port.field, types)[2]
    if fact is None or fact.precision > MAX_PRECISION:
        return None
    return fact.precision, fact.scale


def _admitted_decimal(parameter: Any) -> tuple[int, int] | None:
    """The declared (precision, scale) of a `Decimal` parameter whose
    precision is at most MAX_PRECISION, else None."""
    decimal = parameter.decimal
    return decimal if decimal is not None and decimal[0] <= MAX_PRECISION else None


def _fits(
    name: str | None,
    representation: dict[str, Any],
    decimal: tuple[int, int] | None = None,
) -> bool:
    """The representation table of the route for one logical type."""
    if name == "Decimal":
        if decimal is None:
            return False
        pair = dict(zip(("precision", "scale"), decimal, strict=True))
        return representation["storage"] == {"kind": "arrow_decimal128"} | pair and (
            representation["domain"] == {"kind": "decimal"} | pair
        )
    storage, domain = representation["storage"]["kind"], representation["domain"]
    if name == "Int":
        return (
            storage == "arrow_int64"
            and domain["kind"] == "int_range"
            and -(2**63) <= int(domain["min"])
            and int(domain["max"]) <= 2**63 - 1
        )
    if name == "Text":
        return (
            storage == "arrow_string"
            and domain["kind"] == "text"
            and (domain["encoding"], domain["collation"], domain["padding"])
            == ("UTF8", "C", "NO PAD")
        )
    expected = {
        "Bool": ("arrow_bool", "bool01"),
        "Float": ("arrow_float64", "finite_float"),
        "Date": ("arrow_date32", "date"),
        "Timestamp": ("arrow_timestamp_us", "timestamp"),
    }
    return name in expected and (storage, domain["kind"]) == expected[name]


def _logical(value_type: Any) -> tuple[str, bool] | None:
    """A known builtin value type's (name, nullable), else None."""
    resolved = value_type.resolved_type
    nullable = {"non_null": False, "nullable": True}.get(value_type.nullability.value)
    if (
        value_type.kind.value != "known"
        or resolved is None
        or resolved.kind.value != "builtin"
        or nullable is None
    ):
        return None
    return resolved.name, nullable


def _arithmetic(expression: Any) -> tuple[Any, ...]:
    """The operands of a `+`, `-` or `*`, or of a unary `-` or `+`; none for
    any other expression."""
    operator = getattr(expression.expression, "operator", None)
    if type(expression) is ProjectSQLBinary and operator in ("+", "-", "*"):
        return expression.left, expression.right
    if type(expression) is ProjectSQLUnary and operator in ("-", "+"):
        return (expression.operand,)
    return ()


def _bounds(contract: DuckDBContract, values: Any) -> dict[int, tuple[int, int]]:
    """The declared `int_range` of each read source field that has one, by
    its number across the source reads; the capture admits no value outside it."""
    entries = {entry.owner: entry for entry in contract.sources}
    result = {}
    for read, source, _ in values.chain or ():
        entry = entries.get(source.source.owner)
        for field in () if entry is None else entry.fields:
            domain = field.representation["domain"]
            if domain.get("kind") == "int_range":
                low, high = int(domain["min"]), int(domain["max"])
                # A range beyond signed 64 bits is rule 28's.
                if -(2**63) <= low and high <= 2**63 - 1:
                    result[values.starts[read.ref] + field.ordinal] = (low, high)
    return result


def _operands(expression: Any) -> tuple[Any, ...]:
    """The operands of a predicate node: `and`, `or` and `not`, a comparison
    or a null test; any other expression is a leaf, a signed literal too."""
    kind = type(expression)
    operator = getattr(expression.expression, "operator", None)
    if kind is ProjectSQLComparison or (
        kind is ProjectSQLBinary and operator in ("and", "or")
    ):
        return expression.left, expression.right
    if kind is ProjectSQLUnary and operator == "not":
        return (expression.operand,)
    return (expression.value,) if kind is ProjectSQLIsNull else ()


def _chain(plan: Any) -> tuple[tuple[Any, Any, tuple[Any, ...]], ...] | None:
    """Each source read in FROM and JOIN order as (read, source, ports): the
    first JOIN's two inputs, then each later JOIN's right input, which joins
    the rows so far, each a read with its own ports, one per field of its
    source in order, so that a source read twice, as through a row-input
    alias, is two reads; without JOINs, the source and its source ports.
    None when the JOINs do not chain source reads so, or a source is not
    read."""
    if not plan.joins:
        return tuple((source, source, _ports(plan, source)) for source in plan.sources)
    sources = {source.ref: source for source in plan.sources}
    inputs = {item.ref: item for item in plan.join_inputs}
    ports = {port.ref: port for port in plan.join_ports}
    reads: list[Any] = []
    previous = None
    for position, join in enumerate(plan.joins):
        left, right = (inputs.get(ref) for ref in join.inputs)
        if left is None or right is None or join.position != position:
            return None
        if previous is None:
            reads.append(left)
        elif left.producer is not None or left.predecessor is not previous.ref:
            return None
        reads.append(right)
        previous = join
    chain = []
    for read in reads:
        source = sources.get(read.producer)
        if source is None:
            return None
        own = tuple(ports.get(ref) for ref in read.ports)
        fields = _ports(plan, source)
        # Each own port carries its source field unmodified, so that
        # `_type_name` and `_decimal` read it as that field.
        if len(own) != len(fields) or not all(
            port is not None and port.source is field.ref and port.field is field.field
            for port, field in zip(own, fields, strict=True)
        ):
            return None
        chain.append((read, source, own))
    if len({id(source) for _, source, _ in chain}) != len(plan.sources):
        return None
    return tuple(chain)


class _Values:
    """What the plan's values read: the ports of source reads, group keys
    and aggregates. Source fields are numbered across the source reads in
    FROM and JOIN order, so a source read twice has two numbers per field;
    the port that a method gives for a field is its numbered port, the
    source port without JOINs, else the port of the JOIN input that reads
    it."""

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        self.refs = reference_source_ports(plan)
        self.origins = stage_origins(plan)
        self.chain = _chain(plan)
        self.starts: dict[Any, int] = {}
        self.index: dict[Any, int] = {}
        # Each numbered field's port: a source port, or the port of a JOIN
        # input that reads its source; numbered by source when the JOINs do
        # not chain source reads.
        self.ports: dict[Any, Any] = {}
        fallback = ((s, s, _ports(plan, s)) for s in plan.sources)
        for read, _, ports in fallback if self.chain is None else self.chain:
            self.starts[read.ref] = len(self.index)
            for port in ports:
                self.index[port.ref] = len(self.index)
                self.ports[port.ref] = port
        self.width = len(self.index)
        self.inputs = {item.ref: item for item in plan.join_inputs}
        # Each port's source port or the port it carries unmodified, through
        # stages and JOINs.
        self.carried = {
            port.ref: port.producer_port
            for port in plan.input_ports
            if port.producer_port is not None
        }
        self.carried.update(
            {port.ref: port.source for port in (*plan.stage_ports, *plan.join_ports)}
        )
        self.results = {port.ref: port for port in plan.result_ports}
        self.decimals = {
            port.ref: _decimal(plan, port)
            for port in (*plan.source_ports, *self.ports.values())
            if _type_name(port) == "Decimal"
        }
        self.roots = {e.ref: e for e in plan.order_expressions}
        self.uses = {u.ref: u for u in plan.order_uses}
        owners = {item.ref: item for item in (*plan.group_keys, *plan.aggregates)}
        # Each stage port that carries a group key's or aggregate's result
        # unmodified; a port's source precedes it, as for stage_origins.
        self.owners: dict[Any, Any] = {}
        for port in plan.stage_ports:
            owner = owners.get(port.source) or self.owners.get(port.source)
            if owner is not None:
                self.owners[port.ref] = owner

    def kind(self, port: Any) -> Any:
        """What a comparison matches of a source field: its type's name, or
        ("Decimal", p, s); None for a field that rule 10 refuses."""
        tag = _type_name(port)
        if tag != "Decimal":
            return tag
        decimal = self.decimals.get(port.ref)
        return None if decimal is None else ("Decimal", *decimal)

    def origin(self, ref: Any) -> Any:
        """The numbered port that a port carries unmodified, else None."""
        seen = set()
        while ref not in self.ports and ref in self.carried and ref not in seen:
            seen.add(ref)
            ref = self.carried[ref]
        return self.ports.get(ref)

    def direct(self, expression: Any) -> Any:
        """The source port that `expression` reads directly, else None."""
        if type(expression) is ProjectSQLJoinedReference:
            return self.origin(expression.port)
        if type(expression) is not ProjectSQLReference:
            return None
        found = self.refs.get(expression.ref)
        return None if found is None else self.ports.get(found[1].ref)

    def key(self, key: Any) -> Any:
        """The source port that a group key reads directly, else None."""
        return self.stage(key.input)

    def stage(self, ref: Any) -> Any:
        """The source port that a stage port carries unmodified, else None."""
        port = self.origins.get(ref)
        if port is None:
            return self.origin(ref) if self.plan.joins else None
        return self.ports.get(port.producer_port)

    def on(self, join: Any) -> tuple[tuple[Any, int, int], ...] | None:
        """Each `==` of an admitted JOIN's `on`, an `and` of them, as
        (comparison, left field, right field): both sides read fields of one
        key type, one of the joined source read and one of an earlier one;
        None for any other JOIN."""
        kind = _JOINS.get(join.kind.value)
        joined = self.inputs.get(join.inputs[1])
        if joined is None:
            return None
        start = self.starts.get(joined.ref)
        if (
            kind is None
            or kind[1] != join.rows.value
            or start is None
            or join.on is None
            or join.equalities
        ):
            return None
        plan = self.plan
        end = start + sum(port.owner == joined.producer for port in plan.source_ports)

        def equalities(ref: Any) -> tuple[tuple[Any, int, int], ...] | None:
            expression = plan.expressions[ref.position]
            operator = getattr(expression.expression, "operator", None)
            if type(expression) is ProjectSQLBinary and operator == "and":
                first = equalities(expression.left)
                second = equalities(expression.right)
                return None if first is None or second is None else first + second
            if type(expression) is not ProjectSQLComparison or operator != "==":
                return None
            ports = []
            for operand in (expression.left, expression.right):
                read = plan.expressions[operand.position]
                port = (
                    self.origin(read.port)
                    if type(read) is ProjectSQLMatchReference
                    else None
                )
                if port is None or _type_name(port) not in KEYS:
                    return None
                ports.append(port)
            left, right = (self.index[port.ref] for port in ports)
            if (
                _type_name(ports[0]) != _type_name(ports[1])
                or (start <= left < end) == (start <= right < end)
                or max(left, right) >= end
            ):
                return None
            return ((expression, left, right),)

        return equalities(join.on)

    def order(
        self, item: Any, outputs: tuple[tuple[Any, Any, Any], ...]
    ) -> tuple[Any, str | None] | None:
        """(source port, aggregate function) of an order key that reads a
        result field of `outputs` directly, or a source field when the
        statement neither groups nor aggregates; (None, None) when rule 7 or
        7a refuses that result field; None for any other key (rule 8a).
        Each port of the key's use is a copy of one value, which it reaches
        through the result ports."""
        root = self.roots.get(item.expression)
        use = None if root is None else self.uses.get(root.use)
        if (
            item.value is not item.expression
            or root is None
            or use is None
            or root.operands
            or use.requirement is not None
        ):
            return None
        ends = []
        for ref in use.ports:
            while ref in self.results:
                ref = self.results[ref].source
            ends.append(ref)
        if not ends or any(end is not ends[0] for end in ends):
            return None
        owner = self.owners.get(ends[0])
        for projection, port, selected in outputs:
            if projection is not None and projection.ref is ends[0]:
                return (port, None) if selected is None else self.value(selected)
            if selected is not None and selected is owner:
                return self.value(selected)
        port = None if self.plan.aggregations else self.stage(ends[0])
        return None if port is None else (port, None)

    def aggregate(self, aggregate: Any) -> tuple[str, Any] | None:
        """(function, the source port it reads, None in count()) of an
        aggregate that rule 7a admits, else None."""
        source = aggregate.source
        if type(source) is aggregation.ProjectAggregateExpressionAnalysis:
            call = aggregation.aggregate_call(source)
            function = aggregation.filtered_function(call) or source.fact.function
        elif type(source) is ProjectJoinedAggregateOccurrence:
            # An aggregate over JOIN rows.
            function = (
                aggregation.filtered_function(source.call) or source.function_name
            )
        else:
            return None
        reads = tuple(
            self.direct(self.plan.expressions[argument.position])
            for argument in aggregate.arguments
        )
        types = tuple(None if read is None else _type_name(read) for read in reads)
        if aggregate.order_by or types not in _AGGREGATES.get(function, ()):
            return None
        logical = _logical(aggregate.value_type)
        expected = types[0] if function in ("min", "max") else "Int"
        if logical is None or logical[0] != expected:
            return None
        return function, reads[0] if reads else None

    def outputs(self) -> tuple[tuple[Any, Any, Any], ...]:
        """Each result field's (projection, source port, group key or
        aggregate): a direct read of a source field, through a group key when
        the statement aggregates, has its port; an aggregate call has its
        aggregate; any other value has neither (rule 7)."""
        plan = self.plan
        projections = {
            p.export: p for p in (*plan.projections, *plan.aggregate_projections)
        }
        result = []
        for export in plan.exports:
            projection = projections.get(export.ref)
            port = owner = None
            if type(projection) is plans.ProjectSQLProjection:
                if not plan.aggregations and (
                    projection.input_port is not None or plan.joins
                ):
                    expression = plan.expressions[projection.expression.position]
                    port = self.direct(expression)
            elif (
                projection is not None
                and aggregation.composition_fact(projection.source) is None
            ):
                owner = self.owners.get(projection.input)
                if type(owner) is aggregation.ProjectSQLGroupKey:
                    port = self.key(owner)
            result.append((projection, port, owner))
        return tuple(result)

    def computed(
        self, projection: Any, numbers: dict[int, int]
    ) -> DuckDBArithmetic | None:
        """The arithmetic of a result field that rule 7 admits: `+`, `-` or
        `*` of two `Int` or two `Float` operands, or a `Float` sign of one,
        each a direct read of a source field (of a group key when the
        statement aggregates), a literal or a parameter, one at least a
        read; else None."""
        if type(projection) is not plans.ProjectSQLProjection:
            return None
        expression = self.plan.expressions[projection.expression.position]
        found = [self.operand(ref, numbers) for ref in _arithmetic(expression)]
        tags = {tag for _, tag in filter(None, found)}
        resolved = expression.value_type.resolved_type
        if (
            not found
            or None in found
            or len(tags) != 1
            or getattr(resolved, "name", None) not in tags
        ):
            return None
        node = DuckDBArithmetic(
            expression.expression.operator,
            tuple(operand for operand, _ in filter(None, found)),
            tags.pop(),
        )
        return node if arithmetic_holds(node) else None

    def operand(
        self, ref: Any, numbers: dict[int, int]
    ) -> tuple[DuckDBRead | DuckDBLiteral | DuckDBParameter, str] | None:
        """(node, type) of an arithmetic operand of type `Int` or `Float`."""
        expression = self.plan.expressions[ref.position]
        port = None
        if not self.plan.aggregations:
            port = self.direct(expression)
        elif type(expression) is aggregation.ProjectSQLResultReference:
            owner = self.owners.get(expression.port)
            if type(owner) is aggregation.ProjectSQLGroupKey:
                port = self.key(owner)
        node: DuckDBRead | DuckDBLiteral | DuckDBParameter
        if port is not None:
            node, tag = DuckDBRead(self.index[port.ref]), _type_name(port)
        elif (found := self.constant(ref, numbers, None)) is not None:
            node, tag = found
        else:
            return None
        return None if tag is None or tag not in ("Int", "Float") else (node, tag)

    def value(self, owner: Any) -> tuple[Any, str | None]:
        """(source port, aggregate function) of a group key or of an aggregate
        that rule 7a admits."""
        if type(owner) is aggregation.ProjectSQLGroupKey:
            return self.key(owner), None
        function, port = self.aggregate(owner) or (None, None)
        return port, function

    def predicate(
        self, ref: Any, selected: tuple[Any, ...] | None, numbers: dict[int, int]
    ) -> Any:
        """The SQL predicate of a `where` (`selected` None) or of a `having`
        over the `selected` group keys and aggregates, else None (rule 8).
        Each parameter's placeholder is numbered at its first read, in SQL
        order, into `numbers` (parameter ordinal to placeholder)."""
        expression = self.plan.expressions[ref.position]
        operands = _operands(expression)
        kind = type(expression)
        if kind is ProjectSQLComparison:
            if expression.expression.operator not in OPERATORS:
                return None
            reads = [self.read(operand, selected) for operand in operands]
            if sum(read is not None for read in reads) != 1:
                return None
            (against,) = (read[1] for read in reads if read is not None)
            # (node, kind) of each side, in SQL order.
            sides = [
                read or self.constant(operand, numbers, against)
                for operand, read in zip(operands, reads, strict=True)
            ]
            left, right = sides
            if left is None or right is None or left[1] != right[1]:
                return None
            return DuckDBComparison(
                left[0], OPERATORS[expression.expression.operator], right[0]
            )
        if kind is ProjectSQLIsNull:
            read = self.read(operands[0], selected)
            negated = expression.expression.negated
            return None if read is None else DuckDBNullTest(read[0], negated)
        if not operands:
            return None
        nodes = tuple(self.predicate(o, selected, numbers) for o in operands)
        if any(node is None for node in nodes):
            return None
        return DuckDBLogic(expression.expression.operator.upper(), nodes)

    def read(
        self, ref: Any, selected: tuple[Any, ...] | None
    ) -> tuple[DuckDBRead, Any] | None:
        """(read, kind) of a direct read of a source field in a `where`, or
        of a selected output of the tier 1 types in a `having`."""
        expression = self.plan.expressions[ref.position]
        if selected is None:
            port = self.direct(expression)
            if port is None or (tag := self.kind(port)) is None:
                return None
            return DuckDBRead(self.index[port.ref]), tag
        if type(expression) is not aggregation.ProjectSQLResultReference:
            return None
        owner = self.owners.get(expression.port)
        logical = _logical(expression.value_type)
        if (
            owner is None
            or not any(owner is item for item in selected)
            or logical is None
            or logical[0] not in HAVING_TYPES
        ):
            return None
        port, function = self.value(owner)
        field = None if port is None else self.index[port.ref]
        return DuckDBRead(field, function), logical[0]

    def constant(
        self, ref: Any, numbers: dict[int, int], against: Any
    ) -> tuple[DuckDBLiteral | DuckDBParameter, Any] | None:
        """(node, kind) of a literal, a signed number literal or a parameter
        read of an admitted type, compared with a read of kind `against`: a
        `Date` or `Timestamp` read takes a `Text` literal of its civil
        spelling, and a `Decimal` read a number literal, as the exact
        decimal it writes, whose cast fits with it in MAX_PRECISION digits."""
        expression = self.plan.expressions[ref.position]
        if type(expression) is ProjectSQLParameterRead:
            parameter = expression.parameter
            tag, decimal = parameter.tag, _admitted_decimal(parameter)
            if tag not in TYPES or (tag == "Decimal") is (decimal is None):
                return None
            number = numbers.setdefault(parameter.ordinal, len(numbers) + 1)
            node = DuckDBParameter(number, tag, decimal)
            return node, tag if decimal is None else ("Decimal", *decimal)
        logical = _logical(expression.value_type)
        signed = (
            type(expression) is ProjectSQLUnary
            and expression.expression.operator == "-"
        )
        if signed:
            expression = self.plan.expressions[expression.operand.position]
        if type(expression) is not ProjectSQLLiteral or logical is None:
            return None
        value: Any
        tag, value = logical[0], expression.expression.value
        if (
            logical[1]
            or tag not in TYPES
            or _logical(expression.value_type) != logical
            or type(value) is not _VALUES[tag]
            or (signed and tag not in ("Int", "Float"))
        ):
            return None
        if against in ("Date", "Timestamp") and tag == "Text":
            value = _temporal(against, value)
            return None if value is None else (DuckDBLiteral(value), against)
        if type(against) is tuple and tag in ("Int", "Float"):
            value = self.digits(expression)
            if value is None:
                return None
            # copy_negate is exact; `-` rounds to the context's 28 digits.
            value = value.copy_negate() if signed else value
            precision, scale = literal_decimal(value)
            whole = max(against[1] - against[2], precision - scale)
            if whole + max(against[2], scale) > MAX_PRECISION:
                return None
            return DuckDBLiteral(value), against
        value = -value if signed else value
        # A Text literal that holds NUL is rule 8b's alone.
        if tag != "Text" and not literal_holds(value):
            return None
        return DuckDBLiteral(value), tag

    def digits(self, literal: Any) -> Decimal | None:
        """The exact decimal number that a number literal writes: an `Int`
        literal's value, a `Float` literal's source text; None when its span
        does not hold exactly that number, as for an inlined def body, whose
        copy has the call's span."""
        if type(literal.expression.value) is int:
            return Decimal(literal.expression.value)
        span = literal.expression.span
        result = self.plan.scope.completed.semantic_result
        texts = [
            s.source_text
            for s in result.trusted_source_snapshots
            if s.path == span.path
        ]
        if len(texts) != 1 or span.line != span.end_line:
            return None
        lines = re.split(r"\r\n|\r|\n", texts[0].removeprefix("\ufeff"))
        if not 0 < span.line <= len(lines):
            return None
        text = lines[span.line - 1][span.column - 1 : span.end_column - 1]
        if _NUMBER.fullmatch(text) is None:
            return None
        number, value = Decimal(text.replace("_", "")), literal.expression.value
        return number if type(value) is float and float(number) == value else None

    def computations(self) -> tuple[DuckDBArithmetic, ...]:
        """The admitted arithmetic of each result field that has one."""
        found = (
            self.computed(projection, {})
            for projection, port, owner in self.outputs()
            if port is None and owner is None
        )
        return tuple(node for node in found if node is not None)

    def size(self, ref: Any) -> int:
        """Rule 16's nodes of a predicate, as `predicate` builds them."""
        expression = self.plan.expressions[ref.position]
        return 1 + sum(self.size(operand) for operand in _operands(expression))

    def nodes(self) -> int:
        """Rule 16: the nodes of the SQL AST that the plan admits."""
        plan = self.plan
        arguments = sum(
            len(owner.arguments)
            for _, _, owner in self.outputs()
            if type(owner) is aggregation.ProjectSQLAggregate
        ) + sum(len(node.operands) for node in self.computations())
        return node_count(
            len(plan.exports),
            arguments,
            len(plan.group_keys),
            sum(self.size(f.predicate) for f in plan.filters),
            len(plan.order_items),
            len(plan.result_limits),
            sum(2 + (0 if j.on is None else self.size(j.on)) for j in plan.joins),
        )


class _Rules:
    """Rules 1-29, with 7a, 7b, 7c, 8a and 8b keyed 7.1, 7.2, 7.3, 8.1 and
    8.2: at most one blocker per rule, at its first failing site."""

    def __init__(self, checked: Any, contract: DuckDBContract, policy: Any) -> None:
        self.found: dict[float, Blocker] = {}
        self.checked, self.contract = checked, contract
        self.statement = checked.selected_owner.definition.span
        premises = contract.premises
        for premise in conflicts(premises)[:1]:
            self.fail(1, "PIE-B1005", "inconsistent_declared_scope", premise)
        if contract.release != RELEASE:
            self.fail(2, "PIE-B1003", "target_release_not_reviewed")
        if policy.value != "preserve_literals":
            self.fail(3, "PIE-B1003", "literal_policy_not_admitted_on_target", at=True)
        for premise in premises:
            if premise.key in NOT_ADMITTED:
                self.fail(4, "PIE-B1003", "premise_not_admitted_on_target", premise)
        plan = checked.plan
        if type(plan) is not plans.ProjectSQLPlan:
            first = plan.blockers[0] if plan.blockers else None
            self.fail(
                5,
                "PIE-B1003",
                "duckdb_relation_shape_not_admitted",
                location=self.statement
                if first is None
                else getattr(first.site, "span", None) or first.owner.definition.span,
            )
            return
        self.plan = plan
        self.values = _Values(plan)
        self.reads = tuple(
            e for e in plan.expressions if type(e) is ProjectSQLParameterRead
        )
        self.shape()
        self.projections()
        self.parameters()
        limits = _limits(premises)
        self.environment(limits)
        self.evidence()
        for source in self.ordered:
            self.source(source)

    def fail(
        self,
        rule: float,
        code: str,
        detail: str,
        subject: object = None,
        location: object = None,
        related: tuple[object, ...] = (),
        *,
        at: bool = False,
    ) -> None:
        self.found.setdefault(
            rule,
            Blocker(code, detail, subject, self.statement if at else location, related),
        )

    def blockers(self) -> tuple[Blocker, ...]:
        return tuple(self.found[rule] for rule in sorted(self.found))

    def shape(self) -> None:
        plan, values = self.plan, self.values
        named = tuple(
            d
            for d in plan.bindings.definitions
            if type(d.entry.owner.definition) is not SourceDef
        )
        operators = tuple(
            tuple(o.kind.value for o in block.operators) for block in plan.blocks
        )
        results = ("relation_ordering",) * len(plan.orders) + ("limit",) * len(
            plan.result_limits
        )
        refused = [values.on(join) is None for join in plan.joins]
        if not (
            len(named) == 1
            and values.chain is not None
            and len(plan.input_uses) == len(values.chain)
            and operators in (_JOINED_SHAPES if plan.joins else _SHAPES)
            and len(plan.filters)
            == sum(o in _FILTERS for block in operators for o in block)
            and results in _RESULTS
            and tuple(b.kind.value for b in plan.result_boundaries) == results
            and not any(refused)
            and not any(getattr(plan, name) for name in _EMPTY)
        ):
            definition = self.checked.selected_owner.definition
            clauses = ()
            if type(definition) in (QueryDef, TableDef):
                joins = definition.join_clauses
                # A JOIN that the plan admits is no site; the plan's JOINs
                # are the authored ones, in order.
                if len(joins) == len(refused) and values.chain is not None:
                    joins = tuple(j for j, no in zip(joins, refused) if no)
                clauses = tuple(
                    clause
                    for clause in (
                        definition.let_clause,
                        definition.qualify_clause,
                        definition.distinct_clause,
                        *joins,
                        *definition.join_filters,
                        *definition.named_windows,
                        *definition.naming_declarations,
                    )
                    if clause is not None
                )
            site = (
                min((c.span for c in clauses), key=_key)
                if clauses
                else definition.from_clause.span
                if type(definition) in (QueryDef, TableDef) and len(named) != 1
                else self.statement
            )
            self.fail(
                5, "PIE-B1003", "duckdb_relation_shape_not_admitted", location=site
            )
        self.ordered = tuple(
            sorted(plan.sources, key=lambda s: _key(s.declaration.span))
        )
        if not self.ordered:
            self.fail(6, "PIE-B1003", "duckdb_source_count_not_admitted", at=True)

    def projections(self) -> None:
        plan, values = self.plan, self.values
        outputs = values.outputs()
        bounds = _bounds(self.contract, values)
        for export, (projection, port, owner) in zip(
            plan.exports, outputs, strict=True
        ):
            node = None if port or owner else values.computed(projection, {})
            site = (
                export.ref if projection is None else projection.ref,
                self.statement
                if projection is None
                else projection.site.occurrence.span
                if type(projection) is plans.ProjectSQLProjection
                else projection.semantic.item.span,
            )
            if (
                port is None
                and type(owner) is not aggregation.ProjectSQLAggregate
                and node is None
            ):
                self.fail(7, "PIE-B1003", "duckdb_projection_not_admitted", *site)
            elif (
                node is not None
                and node.tag == "Int"
                # An unmapped field or another domain is rule 20's or 28's.
                and all(
                    type(o) is not DuckDBRead or o.field in bounds
                    for o in node.operands
                )
                and int_bounds(node, bounds) is None
            ):
                self.fail(7.3, "PIE-B1003", "duckdb_arithmetic_range_not_proved", *site)
        for aggregate in sorted(plan.aggregates, key=lambda a: _key(self.site(a))):
            if values.aggregate(aggregate) is None:
                self.fail(
                    7.1,
                    "PIE-B1003",
                    "duckdb_aggregate_not_admitted",
                    aggregate.ref,
                    self.site(aggregate),
                )
        for key in sorted(plan.group_keys, key=lambda k: _key(self.site(k))):
            if values.key(key) is None:
                self.fail(
                    7.2,
                    "PIE-B1003",
                    "duckdb_grouping_not_admitted",
                    key.ref,
                    self.site(key),
                )
        selected = tuple(owner for _, _, owner in outputs if owner is not None)
        for position, filter_ in enumerate(plan.filters):
            having = filter_.site.role.value == "satisfying"
            if not (
                type(filter_.site) is aggregation.ProjectSQLAggregateSite
                and values.predicate(filter_.predicate, selected, {}) is not None
                if having
                else not position
                and values.predicate(filter_.predicate, None, {}) is not None
            ):
                self.fail(
                    8,
                    "PIE-B1003",
                    "duckdb_filter_not_admitted",
                    filter_.ref,
                    filter_.site.occurrence.span,
                )
        for item in plan.order_items:
            if values.order(item, outputs) is None:
                self.fail(
                    8.1,
                    "PIE-B1003",
                    "duckdb_order_not_admitted",
                    item.ref,
                    item.source.item.span,
                )
        literals: list[Any] = [
            e
            for e in plan.expressions
            if type(e) in (ProjectSQLLiteral, ProjectSQLBoundLiteral)
        ]
        nul = [
            e
            for e in literals
            if type(e.expression.value) is str and "\0" in e.expression.value
        ]
        for literal in sorted(nul, key=lambda e: _key(e.expression.span))[:1]:
            self.fail(
                8.2,
                "PIE-B1003",
                "duckdb_text_literal_nul_not_admitted",
                literal.ref,
                literal.expression.span,
            )

    def site(self, item: Any) -> Any:
        """The call of an aggregate, or the item of a group key."""
        node = getattr(item.source, "call", None) or getattr(item.source, "item", None)
        return getattr(node, "span", None) or self.statement

    def parameters(self) -> None:
        """Rule 9 at the declaration of the first parameter, in header order,
        that is optional, of another type or read nowhere; else at the
        statement when a read is no side of a `where` or `having`
        comparison and no operand of admitted arithmetic."""
        plan = self.plan
        placed = []
        stack = [plan.expressions[f.predicate.position] for f in plan.filters]
        while stack:
            expression = stack.pop()
            operands = [plan.expressions[o.position] for o in _operands(expression)]
            if type(expression) is ProjectSQLComparison:
                placed.extend(operands)
            else:
                stack.extend(operands)
        for projection, port, owner in self.values.outputs():
            if not (port or owner) and self.values.computed(projection, {}):
                root = plan.expressions[projection.expression.position]
                placed.extend(plan.expressions[o.position] for o in _arithmetic(root))
        ordinals = {read.parameter.ordinal for read in self.reads}
        problem: tuple[object, object] | None = next(
            (
                (None, parameter.declaration.span)
                for parameter in plan.parameters
                if parameter.tag not in TYPES
                or (parameter.tag == "Decimal" and _admitted_decimal(parameter) is None)
                or parameter.value_type.nullability.value != "non_null"
                or parameter.ordinal not in ordinals
            ),
            None,
        )
        if problem is None and (
            any(all(read is not p for p in placed) for read in self.reads)
            or any(a.parameter is not None for a in plan.window_arguments)
        ):
            problem = (None, self.statement)
        if problem is not None:
            self.fail(9, "PIE-B1003", "duckdb_parameter_not_admitted", *problem)
        for source in sorted(plan.sources, key=lambda s: _key(s.declaration.span)):
            for port in _ports(plan, source):
                if self.values.kind(port) is None:
                    definition = port.field.evidence.field_def
                    self.fail(
                        10,
                        "PIE-B1003",
                        "duckdb_field_type_not_admitted",
                        port.ref,
                        None if definition is None else definition.span,
                    )

    def environment(self, limits: dict[str, int]) -> None:
        plan = self.plan
        statement = [p for p in self.contract.premises if p.scope == "statement"]
        for rule, key, needed in (
            (
                13,
                "operator_environment",
                bool(plan.filters or self.values.computations()),
            ),
            (14, "parameter_protocol", bool(self.reads)),
        ):
            found = [p for p in statement if p.key == key]
            if needed and not found:
                self.fail(rule, "PIE-B1004", key + "_declaration_missing", at=True)
            elif needed and json.loads(found[0].value) != PREMISES[key]:
                self.fail(rule, "PIE-B1005", key + "_declaration_mismatch", at=True)
        window_reads = sum(a.parameter is not None for a in plan.window_arguments)
        # The placeholders the SQL writes: the checks of `Float` arithmetic
        # repeat its parameter operands.
        repeated = sum(
            (written(node) - 1) * sum(type(o) is DuckDBParameter for o in node.operands)
            for node in self.values.computations()
        )
        if len(self.reads) + window_reads + repeated > limits["parameters"]:
            self.fail(15, "PIE-B1007", "parameter_occurrence_limit", at=True)
        if (
            any(len(_ports(plan, s)) > limits["columns"] for s in plan.sources)
            or len(plan.exports) > limits["columns"]
            or self.values.nodes() > limits["nodes"]
        ):
            self.fail(16, "PIE-B1007", "generated_structure_limit", at=True)
        self.limits = limits

    def evidence(self) -> None:
        view = inspect_project_sql_plan(self.checked)
        report = view.requirements().verification
        request = targets.prepare_database_target_request(FAMILY, RELEASE)
        # As on the other targets; the command passes no profile, so only
        # `explicit_target_profile_missing` arises there.
        for issue in request.issues:
            if issue.value == "profile_target_family_or_release_mismatch":
                self.fail(11, "PIE-B1005", "target_evidence_scope_conflict", request)
            elif issue.value == "profile_composition_blocked":
                self.fail(
                    12, "PIE-B1006", "original_profile_composition_unresolved", request
                )
        self.source_map = view.source_map().verification.source_map
        self.assessment = view.target_assessment(
            request, report_verification=report
        ).verification
        for aspect in self.assessment.assessment.aspects:
            if any(
                state.value in {"exact_negative", "conflicting_facts"}
                for state in aspect.outcomes
            ):
                self.fail(
                    17,
                    "PIE-B1006",
                    "negative_original_target_evidence",
                    aspect.entry.subject,
                )
        for obligation in report.report.summary.enforcement_required:
            self.fail(
                18,
                "PIE-B1006",
                "original_enforcement_not_fulfilled",
                obligation.entry.subject,
            )

    def source(self, source: Any) -> None:
        plan, at = self.plan, source.declaration.span
        if _spelling(source.connector) != "duckdb.arrow":
            self.fail(19, "PIE-B1001", "source_family_mismatch", source.ref, at)
        entries = [s for s in self.contract.sources if s.owner is source.source.owner]
        if len(entries) != 1:
            self.fail(20, "PIE-B1001", "source_mapping_missing", source.ref, at)
            return
        entry, ports = entries[0], _ports(plan, source)
        if tuple(f.ordinal for f in entry.fields) != tuple(range(len(ports))):
            related = tuple(
                port.field.evidence.field_def.span
                for position, port in enumerate(ports)
                if (
                    position >= len(entry.fields)
                    or entry.fields[position].ordinal != position
                )
                and port.field.evidence.field_def is not None
            )
            self.fail(
                21,
                "PIE-B1001",
                "complete_ordered_source_schema_required",
                source.ref,
                at,
                related,
            )
        if entry.namespace != "arrow":
            self.fail(
                22, "PIE-B1001", "source_identifier_unrepresentable", source.ref, at
            )
        if entry.name != source.connector.arguments[0].value:
            self.fail(23, "PIE-B1001", "duckdb_arrow_key_mismatch", source.ref, at)
        owned = [p for p in self.contract.premises if p.scope is entry.owner]
        for rule, key in ((24, "row_domain_matches"), (25, "read_only_object")):
            values = [p for p in owned if p.key == key]
            if not values or any(p.value != b"true" for p in values):
                self.fail(
                    rule, "PIE-B1001", key + "_declaration_required", source.ref, at
                )
        clients = [
            p
            for p in self.contract.premises
            if p.scope == "statement" and p.key == "client_encoding"
        ]
        if not clients:
            self.fail(
                26, "PIE-B1004", "client_encoding_declaration_missing", source.ref, at
            )
        elif any(json.loads(p.value) != PREMISES["client_encoding"] for p in clients):
            self.fail(26, "PIE-B1005", "client_encoding_mismatch", source.ref, at)
        for field in sorted(entry.fields, key=lambda f: f.ordinal):
            port = ports[field.ordinal]
            definition = port.field.evidence.field_def
            place = (port.ref, None if definition is None else definition.span)
            nullable = {"non_null": False, "nullable": True}.get(
                port.field.effective_nullability.value
            )
            if nullable is None or field.representation["nullable"] is not nullable:
                self.fail(27, "PIE-B1002", "nullability_mismatch", *place)
            decimal = self.values.decimals.get(port.ref)
            if not _fits(_type_name(port), field.representation, decimal):
                self.fail(
                    28, "PIE-B1002", "physical_storage_or_domain_mismatch", *place
                )
            sites = tuple(
                expression.site
                for expression, read in self.values.refs.values()
                if read is port
            )
            domain = field.representation["domain"]
            for premise in self.contract.premises:
                if not (
                    premise.scope is entry.owner
                    or (
                        type(premise.scope) is tuple
                        and premise.scope[0] is entry.owner
                        and any(premise.scope[1] is site for site in sites)
                    )
                ):
                    continue
                expected = (
                    domain if premise.key == "value_domain" else domain.get(premise.key)
                )
                if expected is not None and json.loads(premise.value) != expected:
                    self.fail(29, "PIE-B1005", "field_domain_premise_mismatch", *place)


def _expected_ast(plan: Any) -> DuckDBSelect:
    """The statement the plan admits, read from the JOINs, source ports,
    group keys and aggregates that its values read."""
    values = _Values(plan)
    index = values.index

    def field(port: Any) -> int | None:
        return None if port is None else index[port.ref]

    # Placeholders are numbered in SQL order: the projection's, then the
    # `where`'s, then the `having`'s.
    numbers: dict[int, int] = {}
    columns = []
    for export, (projection, port, owner) in zip(
        plan.exports, values.outputs(), strict=True
    ):
        function = value = None
        if type(owner) is aggregation.ProjectSQLAggregate:
            port, function = values.value(owner)
        elif port is None and owner is None:
            value = values.computed(projection, numbers)
        columns.append(DuckDBColumn(field(port), export.identity.name, function, value))
    where = having = None
    outputs = values.outputs()
    selected = tuple(owner for _, _, owner in outputs if owner is not None)
    for filter_ in sorted(plan.filters, key=lambda f: f.site.role.value != "where"):
        if filter_.site.role.value == "where":
            where = values.predicate(filter_.predicate, None, numbers)
        else:
            having = values.predicate(filter_.predicate, selected, numbers)
    group_by = tuple(index[values.key(key).ref] for key in plan.group_keys)
    order_by = []
    for item in plan.order_items:
        port, function = values.order(item, outputs) or (None, None)
        descending = item.source.direction.value == "desc"
        order_by.append(DuckDBOrderKey(field(port), function, descending))
    limit = plan.result_limits[0].value if plan.result_limits else None
    joins = []
    for join in plan.joins:
        equalities = values.on(join)
        if equalities is None:
            raise ValueError("Every JOIN of the statement must be admitted.")
        joins.append(
            DuckDBJoin(
                _JOINS[join.kind.value][0],
                values.starts[join.inputs[1]],
                tuple((left, right) for _, left, right in equalities),
            )
        )
    return DuckDBSelect(
        RELATION,
        tuple(columns),
        where,
        group_by,
        having,
        tuple(order_by),
        limit,
        tuple(joins),
    )


def _labels(plan: Any) -> tuple[str, ...]:
    return tuple(export.identity.name for export in plan.exports)


def _ref(value: Any) -> dict[str, Any]:
    if type(value) is Premise:
        return {"kind": "premise", "position": value.position}
    if hasattr(value, "kind") and hasattr(value, "position"):
        return {"kind": value.kind.value, "position": value.position}
    return {"kind": "selected_plan", "position": 0}


def _location(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        key: getattr(value, key, None)
        for key in ("path", "line", "column", "end_line", "end_column")
    }


def _subjects(plan: Any, values: _Values) -> dict[tuple[object, ...], Any]:
    """The plan owner of each symbolic token subject."""
    outputs = values.outputs()
    chain: tuple[Any, ...] = values.chain or ()
    result: dict[tuple[object, ...], Any] = {
        ("statement",): plan.scope,
        ("source",): chain[0][1].ref,
    }
    for position, join in enumerate(plan.joins):
        result["join", position] = join.ref
        result["join_source", position] = chain[position + 1][1].ref
        for pair, (equality, _, _) in enumerate(values.on(join) or ()):
            result["join_on", position, pair] = equality.ref
            for side, operand in enumerate((equality.left, equality.right)):
                operand = plan.expressions[operand.position]
                result["join_on", position, pair, side] = operand.ref
    for position, (export, (projection, _, owner)) in enumerate(
        zip(plan.exports, outputs, strict=True)
    ):
        result["projection", position] = projection.ref
        result["export", position] = export.ref
        if type(projection) is plans.ProjectSQLProjection:
            root = plan.expressions[projection.expression.position]
            result["computed", position] = root.ref
            for k, operand in enumerate(_arithmetic(root)):
                result["computed", position, k] = plan.expressions[operand.position].ref
        if type(owner) is aggregation.ProjectSQLAggregate:
            result["aggregate", position] = owner.ref
            if owner.arguments:
                result["argument", position] = owner.arguments[0]
    for aggregation_ in plan.aggregations:
        result["aggregation",] = aggregation_.ref
    for position, key in enumerate(plan.group_keys):
        result["group_key", position] = key.ref
    for order in plan.orders:
        result["order",] = order.ref
    for position, item in enumerate(plan.order_items):
        result["order_key", position] = item.ref
    for limit in plan.result_limits:
        result["limit",] = limit.ref
    for filter_ in plan.filters:
        where = filter_.site.role.value == "where"
        result["filter" if where else "having",] = filter_.ref
        # Each predicate node at its path of operand positions.
        stack: list[tuple[tuple[object, ...], Any]] = [
            (("predicate" if where else "having_predicate",), filter_.predicate)
        ]
        while stack:
            path, ref = stack.pop()
            expression = plan.expressions[ref.position]
            result[path] = expression.ref
            stack.extend(
                ((*path, k), operand) for k, operand in enumerate(_operands(expression))
            )
    return result


def _left_joined(joins: tuple[DuckDBJoin, ...], field: int) -> bool:
    """Whether source field `field` lies in an input that a LEFT JOIN
    joins, which makes it nullable."""
    position = sum(join.start <= field for join in joins)
    return position > 0 and joins[position - 1].kind == "LEFT"


def _entry(contract: DuckDBContract, source: Any) -> Any:
    (entry,) = (s for s in contract.sources if s.owner is source.source.owner)
    return entry


def _document(artifact: DuckDBArtifact) -> bytes:
    checked, plan = artifact.checked, artifact.checked.plan
    semantic, owner = checked.completed.semantic_result, checked.selected_owner
    contract = json.loads(artifact.contract.normalized)
    values = _Values(plan)
    # Each source field's (source port, contract entry, its field) by number.
    fields: list[tuple[Any, Any, Any]] = []
    for _, source, _ in values.chain or ():
        entry = _entry(artifact.contract, source)
        described = {f.ordinal: f for f in entry.fields}
        for k, port in enumerate(_ports(plan, source)):
            fields.append((port, entry, described[k]))
    outputs = values.outputs()
    subjects = _subjects(plan, values)
    indexes = artifact.source_map.indexes
    bounds = _bounds(artifact.contract, values)
    ranges = []
    for token in artifact.tokens:
        subject = subjects[token.subject]
        ranges.append(
            {
                "start": token.start,
                "end": token.end,
                "kind": token.kind,
                "role": token.role,
                "subject": _ref(subject),
                "origins": [
                    {
                        "position": origin.position,
                        "role": origin.original.role.value,
                        "sources": [
                            {
                                "path": a.site.source.display_path,
                                "kind": a.kind.value,
                                "location": _location(a.site.location),
                            }
                            for a in indexes.associations[origin.ref]
                        ],
                    }
                    for origin in getattr(indexes.subjects.get(subject), "origins", ())
                ],
            }
        )
    columns = []
    for position, (column, export, (projection, _, item)) in enumerate(
        zip(artifact.ast.columns, plan.exports, outputs, strict=True)
    ):
        k, logical, node = column.field, None, column.value
        read = entry = described = None
        if k is not None:
            read, entry, described = fields[k]
        elif not plan.joins:
            entry = fields[0][1]
        correspondence: dict[str, Any] = {
            "source": None if entry is None else entry.selector,
            # A field's ordinal in its own source.
            "field": None if described is None else described.ordinal,
            "source_port": None if read is None else _ref(read.ref),
        }
        if column.function is not None:
            correspondence["aggregate"] = _ref(item.ref)
            correspondence["function"] = column.function
            logical = _logical(item.value_type)
        elif item is not None:
            correspondence["group_key"] = _ref(item.ref)
        if node is not None:
            # Arithmetic: NULL when an operand is, of its operands' type, an
            # Int over the range that its operands' capture-checked bounds
            # prove.
            correspondence["computed"] = _ref(subjects["computed", position])
            name, nullable = (
                node.tag,
                any(
                    type(o) is DuckDBRead
                    and o.field is not None
                    and (
                        fields[o.field][2].representation["nullable"]
                        or _left_joined(artifact.ast.joins, o.field)
                    )
                    for o in node.operands
                ),
            )
            domain: dict[str, str] = {"kind": "finite_float", "format": "binary64"}
            if name == "Int":
                proved = int_bounds(node, bounds)
                if proved is None:
                    raise ValueError("arithmetic range")
                domain = {
                    "kind": "int_range",
                    "min": str(proved[0]),
                    "max": str(proved[1]),
                }
            storage = "arrow_int64" if name == "Int" else "arrow_float64"
            representation = {
                "storage": {"kind": storage},
                "domain": domain,
                "nullable": nullable,
            }
        elif column.function in ("count", "sum") or k is None:
            # A count or a sum is a signed 64-bit Int, a count never negative.
            name, nullable = logical or (None, None)
            least = "0" if column.function == "count" else str(-(2**63))
            representation: dict[str, Any] = {
                "storage": {"kind": "arrow_int64"},
                "domain": {"kind": "int_range", "min": least, "max": str(2**63 - 1)},
                "nullable": nullable,
            }
        else:
            # A read, or a min or max, which keeps its field's type and domain.
            representation = fields[k][2].representation
            name, nullable = _type_name(read), representation["nullable"]
            if column.function is not None:
                name, nullable = logical or (None, None)
                representation = representation | {"nullable": nullable}
            elif plan.joins:
                # A LEFT JOIN makes the fields of its joined side nullable.
                nullable = export.field.effective_nullability.value == "nullable"
                representation = representation | {"nullable": nullable}
        input_port = (
            projection.input_port
            if type(projection) is plans.ProjectSQLProjection
            else projection.input
        )
        domain = representation["domain"]
        if input_port is None and type(projection) is plans.ProjectSQLProjection:
            # A read of JOIN rows names the stage port it reads.
            read_value = plan.expressions[projection.expression.position]
            input_port = getattr(read_value, "port", None)
        columns.append(
            {
                "ordinal": position,
                "label": column.label,
                "logical_type": {
                    "kind": "builtin",
                    "name": name,
                    "parameters": {k: domain[k] for k in ("precision", "scale")}
                    if name == "Decimal"
                    else None,
                },
                "nullable": nullable,
                "representation": representation,
                "correspondence": correspondence
                | {
                    "input_port": _ref(input_port),
                    "export": _ref(export.ref),
                    "projection": _ref(projection.ref),
                    "sql_symbol": position,
                },
            }
        )
    requirements = [
        {
            "denominator": "original",
            "ordinal": i,
            "kind": demand.entry.family.value,
            "subject": _ref(demand.entry.subject),
            "rule": "duckdb_b1",
            "disposition": "checked_rule",
            "premises": [],
            "evidence": [
                [s.value for s in aspect.outcomes] for aspect in demand.aspects
            ],
        }
        for i, demand in enumerate(artifact.assessment.assessment.demands)
    ]
    placeholders = [t for t in artifact.tokens if t.kind == "parameter"]
    reads = [
        plan.expressions[subjects[t.subject].position].parameter for t in placeholders
    ]
    # Each parameter's placeholder, numbered at its first read in SQL order.
    numbers: dict[int, int] = {}
    for read in reads:
        numbers.setdefault(read.ordinal, len(numbers) + 1)
    document: dict[str, Any] = {
        "format": PARAMETERIZED_FORMAT if plan.parameters else FORMAT,
        "status": "VERIFIED",
        "target": {
            "family": FAMILY,
            "release": artifact.contract.release,
            "environment": contract["environment"],
        },
        "request": {
            "owner": {
                "module": semantic.modules[owner.module_position].path,
                "kind": owner.identity.declaration_kind.value,
                "name": owner.definition.name,
            },
            "sources": [
                {
                    "module": snapshot.identity.path,
                    "sha256": snapshot.sha256,
                    "byte_count": snapshot.byte_count,
                }
                for snapshot in semantic.trusted_source_snapshots
            ],
            "contract": contract,
            "literal_policy": checked.literal_policy.value,
        },
        "sql": artifact.sql.decode("utf-8"),
        "fixed_values": [],
        "parameter_uses": [
            {
                "use": i,
                "owner": {"kind": "parameter", "parameter": read.ordinal},
                "server_index": numbers[read.ordinal],
                "physical_type": PHYSICAL[read.tag],
                "range": {"start": token.start, "end": token.end},
            }
            for i, (token, read) in enumerate(zip(placeholders, reads, strict=True))
        ],
        "columns": columns,
        "ranges": ranges,
        "requirements": requirements,
        "diagnostics": [asdict(d) for d in checked.completed.diagnostics],
    }
    if plan.parameters:
        document["parameters"] = [
            {
                "parameter": p.ordinal,
                "name": p.declaration.name,
                "tag": p.tag,
                "nullable": p.value_type.nullability.value == "nullable",
                "reads": [
                    _ref(subjects[t.subject])
                    for t, read in zip(placeholders, reads, strict=True)
                    if read.ordinal == p.ordinal
                ],
            }
            for p in plan.parameters
        ]
        document["binding_obligations"] = []
    return canonical(document) + b"\n"


def verify_artifact(artifact: object) -> bool:
    """The adapter's artifact verifier: the artifact is exactly what the
    current plan and contract build, render and document."""
    try:
        if type(artifact) is not DuckDBArtifact:
            return False
        plan = artifact.checked.plan
        if type(plan) is not plans.ProjectSQLPlan:
            return False
        values = _Values(plan)
        if (
            values.chain is None
            or artifact.ast != (expected := _expected_ast(plan))
            or not ast_rules_hold(artifact.ast, values.width, _labels(plan))
            or artifact.ast.nodes != values.nodes()
            or render(artifact.ast) != (artifact.sql, artifact.tokens)
            # Literals compare by value, 1, 1.0 and True alike, -0.0 and 0.0
            # alike; their SQL does not.
            or render(expected) != (artifact.sql, artifact.tokens)
        ):
            return False
        return _document(artifact) == artifact.document
    except (AttributeError, KeyError, LookupError, TypeError, ValueError):
        return False


def emit_duckdb_sql(
    checked: Any, data: bytes, policy: Any, *, read_sources_only: bool = False
) -> DuckDBEmission:
    """Rules 1-33 over one verified plan and the contract bytes."""
    diagnostics = checked.completed.diagnostics
    contract = read_duckdb_contract(checked, data, read_sources_only=read_sources_only)
    if isinstance(contract, tuple):
        return DuckDBEmission(
            "INPUT_REJECTED", diagnostics, cli_errors=contract, family=None
        )
    rules = _Rules(checked, contract, policy)
    blockers = rules.blockers()
    if blockers:
        return DuckDBEmission("BLOCKED", diagnostics, blockers=blockers)

    def blocked(code: str, detail: str) -> DuckDBEmission:
        return DuckDBEmission("BLOCKED", diagnostics, blockers=(Blocker(code, detail),))

    plan = checked.plan
    ast = _expected_ast(plan)
    if (
        not ast_rules_hold(ast, rules.values.width, _labels(plan))
        or ast.nodes != rules.values.nodes()
    ):
        return blocked("PIE-B1008", "plan_ast_correspondence")
    sql, tokens = render(ast)
    if len(sql) > rules.limits["sql_bytes"]:
        return blocked("PIE-B1007", "sql_byte_limit")
    artifact = DuckDBArtifact(
        checked,
        contract,
        policy,
        rules.source_map,
        rules.assessment,
        ast,
        sql,
        tokens,
        b"",
    )
    artifact = DuckDBArtifact(
        checked,
        contract,
        policy,
        rules.source_map,
        rules.assessment,
        ast,
        sql,
        tokens,
        _document(artifact),
    )
    if not verify_artifact(artifact):
        return blocked("PIE-B1008", "artifact_correspondence")
    if len(artifact.document) > rules.limits["artifact_bytes"]:
        return blocked("PIE-B1007", "public_artifact_byte_limit")
    return DuckDBEmission("VERIFIED", diagnostics, artifact=artifact)


def serialize_duckdb_emission(outcome: Any) -> bytes:
    """A VERIFIED document whose artifact verifies afresh, else the failure
    document, with the DuckDB suggestions."""
    if outcome.status == "VERIFIED":
        artifact = outcome.artifact
        if (
            type(outcome) is DuckDBEmission
            and artifact is not None
            and not outcome.blockers
            and not outcome.cli_errors
            and outcome.diagnostics is artifact.checked.completed.diagnostics
            and verify_artifact(artifact)
        ):
            return artifact.document
        outcome = DuckDBEmission(
            "BLOCKED",
            outcome.diagnostics,
            blockers=(Blocker("PIE-B1008", "artifact_correspondence"),),
        )
    if (
        outcome.status not in {"INPUT_REJECTED", "BLOCKED"}
        or outcome.artifact is not None
        or (outcome.status == "INPUT_REJECTED") != bool(outcome.cli_errors)
        or (outcome.status == "BLOCKED" and not outcome.blockers)
        or any(b.code not in CODES for b in outcome.blockers)
    ):
        raise ValueError("Invalid emission failure branch.")
    blockers: dict[bytes, dict[str, Any]] = {}
    for blocker in outcome.blockers:
        item = {
            "code": blocker.code,
            "reason": CODES[blocker.code],
            "suggestion": suggestion(blocker.code, blocker.detail),
            "subject": {"reference": _ref(blocker.subject), "detail": blocker.detail},
            "location": _location(blocker.location),
            "related": [_location(location) for location in blocker.related],
        }
        blockers.setdefault(canonical(item), item)
    return (
        canonical(
            {
                "format": FORMAT,
                "status": outcome.status,
                "artifact": None,
                "blockers": list(blockers.values()),
                "diagnostics": [asdict(d) for d in outcome.diagnostics],
                "cli_errors": [asdict(error) for error in outcome.cli_errors],
            }
        )
        + b"\n"
    )


@dataclass(frozen=True, slots=True, eq=False)
class DuckDBTemplate:
    """The live query of a VERIFIED DuckDB document and the installed code
    identity it was compiled with; the `duckdb_arrow` route executes it."""

    emission: DuckDBArtifact
    compatibility: tuple[Any, ...]

    def __repr__(self) -> str:
        return "DuckDBTemplate(emission=...)"

    def facts(self) -> tuple[Any, ...]:
        """Module, kind, name, family, release, literal policy, slot tags and
        header parameters, as `query_facts` gives them on the other targets."""
        checked = self.emission.checked
        owner = checked.selected_owner
        return (
            checked.completed.semantic_result.modules[owner.module_position].path,
            owner.identity.declaration_kind.value,
            owner.definition.name,
            FAMILY,
            self.emission.contract.release,
            "preserve",
            (),
            tuple(
                (
                    p.declaration.name,
                    p.tag,
                    p.value_type.nullability.value == "nullable",
                )
                for p in checked.plan.parameters
            ),
        )


def prepare_duckdb_live_template(outcome: Any) -> DuckDBTemplate | None:
    """The live template of a VERIFIED outcome whose artifact verifies afresh;
    None for any other status (the command's failure document)."""
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        return None
    if type(outcome) is not DuckDBEmission or not verify_artifact(outcome.artifact):
        raise ValueError("BINDING_ARTIFACT")
    from pietto._project.project_compiled_loading import supported_compatibility

    return DuckDBTemplate(outcome.artifact, supported_compatibility())


@dataclass(frozen=True, slots=True)
class DuckDBSourceField:
    """One source field in shape order: its contract column, logical type,
    compiled nullability and declared domain bounds (`int_range` of an
    `Int`, `max_characters` of a `Text`, (precision, scale) of a
    `Decimal`)."""

    column: str
    tag: str
    nullable: bool
    bounds: tuple[int, int] | None
    max_characters: int | None
    decimal: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class DuckDBSource:
    """One source read in FROM and JOIN order: the contract's
    `relation.name`, its fields in shape order and, when the statement
    aggregates JOIN rows, the field positions of each `unique(...)` key that
    its shape declares (D79.24)."""

    key: str
    fields: tuple[DuckDBSourceField, ...]
    unique: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class DuckDBExecutionFacts:
    """What the `duckdb_arrow` route reads of one verified artifact: its
    read sources, the rendered statement, each result column's (label,
    logical type, nullable, decimal) in result order, the header parameters
    as (name, tag, nullable, decimal), where decimal is a `Decimal`'s
    (precision, scale) and None for every other type, and the header ordinal
    of the parameter that each placeholder `$1`, `$2`, ... binds."""

    sources: tuple[DuckDBSource, ...]
    sql: str
    result: tuple[tuple[str, str, bool, tuple[int, int] | None], ...]
    parameters: tuple[tuple[str, str, bool, tuple[int, int] | None], ...]
    placeholders: tuple[int, ...]


def execution_facts(template: object) -> DuckDBExecutionFacts:
    """The facts of a live template whose artifact verifies afresh; any other
    value is BINDING_ARTIFACT. Each result column has the logical type and
    nullability of its verified document's column: a read's are its source
    field's, an aggregate's its result's (rules 7 and 7a), an arithmetic
    value's its operands' type, NULL when an operand is. The declared keys
    are those that the verified plan gives each JOIN input."""
    if type(template) is not DuckDBTemplate or not verify_artifact(template.emission):
        raise ValueError("BINDING_ARTIFACT")
    artifact = template.emission
    plan = artifact.checked.plan
    values = _Values(plan)
    sources = []
    for read, source, _ in values.chain or ():
        ports = _ports(plan, source)
        entry = _entry(artifact.contract, source)
        fields = []
        for field in sorted(entry.fields, key=lambda f: f.ordinal):
            tag = _type_name(ports[field.ordinal])
            domain = field.representation["domain"]
            if tag is None or type(field.representation["nullable"]) is not bool:
                raise ValueError("BINDING_ARTIFACT")
            fields.append(
                DuckDBSourceField(
                    field.column,
                    tag,
                    field.representation["nullable"],
                    (int(domain["min"]), int(domain["max"])) if tag == "Int" else None,
                    domain["max_characters"] if tag == "Text" else None,
                    (domain["precision"], domain["scale"])
                    if tag == "Decimal"
                    else None,
                )
            )
        unique: set[tuple[int, ...]] = set()
        if plan.joins and plan.aggregates:
            # Every declared key, whichever one a proof used (D79.24).
            for key in read.source.source_properties.keys:
                unique.add(
                    tuple(
                        sorted(
                            min(member.field_position for member in item.members)
                            for item in key.determinants
                        )
                    )
                )
        sources.append(DuckDBSource(entry.name, tuple(fields), tuple(sorted(unique))))
    document = json.loads(artifact.document)
    result = tuple(
        (
            c["label"],
            c["logical_type"]["name"],
            c["nullable"],
            None
            if c["logical_type"]["parameters"] is None
            else (
                c["logical_type"]["parameters"]["precision"],
                c["logical_type"]["parameters"]["scale"],
            ),
        )
        for c in document["columns"]
    )
    bound = {
        u["server_index"]: u["owner"]["parameter"] for u in document["parameter_uses"]
    }
    if any(
        tag not in TYPES
        or type(nullable) is not bool
        or (tag == "Decimal") is (pair is None)
        for _, tag, nullable, pair in result
    ):
        raise ValueError("BINDING_ARTIFACT")
    return DuckDBExecutionFacts(
        tuple(sources),
        artifact.sql.decode("utf-8"),
        result,
        tuple(
            (*header, parameter.decimal)
            for header, parameter in zip(
                template.facts()[7], plan.parameters, strict=True
            )
        ),
        tuple(bound[k] for k in sorted(bound)),
    )
