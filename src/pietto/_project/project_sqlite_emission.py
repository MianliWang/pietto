"""The independent SQLite project adapter (AD78.03, PL.47): compile refusals,
artifact, artifact verifier and document over `ProjectSQLPlan`.

The PostgreSQL/MySQL pipeline never receives the `sqlite` family: this
module reads its own contract (project_sqlite_contract), builds and renders
its own SQL AST (project_sqlite_sql) and serializes its own documents with
the `pietto.sql-emission.v1`/`v2` envelope. From the emission pipeline it
imports only the names the DuckDB adapter imports, and it asks
`blocker_suggestion` with no family. It imports no sqlite3 or sqlglot. The
rules and their order are those of "Compile refusals" in
docs/spec/sqlite-project-v1.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto._project import project_sql_plan as plans
from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_expressions as expressions
from pietto._project import project_sql_plan_target_assessment as targets
from pietto._project.aggregate_grouped_schema import ProjectGroupKeyFact
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_emission_contract import (
    CODES,
    MAX_ARTIFACT_BYTES,
    MAX_NODES,
    MAX_SQL_BYTES,
    Blocker,
    Premise,
    canonical,
)
from pietto._project.project_sql_emission_scopes import reference_source_ports
from pietto._project.project_sql_emission_suggestions import blocker_suggestion
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sqlite_contract import (
    FAMILY,
    RELEASE,
    SQLiteContract,
    conflicts,
    read_sqlite_contract,
)
from pietto._project.project_sqlite_sql import (
    FUNCTIONS,
    LOGICAL,
    MAX_INT,
    OPERATORS,
    SQLiteAggregate,
    SQLiteColumn,
    SQLiteComparison,
    SQLiteIsNull,
    SQLiteKey,
    SQLiteLimit,
    SQLiteLiteral,
    SQLiteLogical,
    SQLiteNot,
    SQLiteParameter,
    SQLiteResult,
    SQLiteSelect,
    Token,
    ast_rules_hold,
    literal_text,
    render,
    size,
)

__all__: tuple[str, ...] = ()

FORMAT = "pietto.sql-emission.v1"
PARAMETERIZED_FORMAT = "pietto.sql-emission.v2"
# The measured build's MAX_COLUMN and MAX_VARIABLE_NUMBER, and half its
# MAX_EXPR_DEPTH, a margin for the nodes SQLite adds itself.
COLUMNS = 2000
PARAMETERS = 32766
DEPTH = 500
TYPES = ("Int", "Text", "Bool", "Float")
STORAGES = {
    "Int": "sqlite_integer",
    "Bool": "sqlite_bool01",
    "Text": "sqlite_text",
    "Float": "sqlite_real",
}
PREMISES = {
    "client_encoding": "UTF-8",
    "operator_environment": "builtin_only",
    "parameter_protocol": "sqlite_prepared",
}
NOT_ADMITTED = ("identifier_case", "session_sql_mode", "session_time_zone")
# Every plan collection that a tier 1 statement leaves empty.
_EMPTY = (
    "let_values",
    "joins",
    "join_inputs",
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
)
# Rule 3 owns the literal policy, so a bind-safe literal is read as its value.
_LITERALS = (expressions.ProjectSQLLiteral, expressions.ProjectSQLBoundLiteral)
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
# The field types each aggregate reads (rule 10); `count` reads any.
_ARGUMENTS = {
    "count_distinct": {"Int", "Text", "Bool"},
    "min": {"Int", "Float"},
    "max": {"Int", "Float"},
    "avg": {"Int"},
    "sum": {"Int"},
}
_RESULTS = ((), ("relation_ordering",), ("limit",), ("relation_ordering", "limit"))
_FOLD = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
)  # ASCII only, as SQLite folds identifiers
_TEXT = {"encoding": "UTF-8", "collation": "BINARY", "padding": "NO PAD"}
_SUGGESTIONS = {
    "target_release_not_reviewed": f'the reviewed sqlite release is "{RELEASE}"',
    "literal_policy_not_admitted_on_target": (
        "SQLite emission takes --literal-policy preserve only"
    ),
    "premise_not_admitted_on_target": (
        "remove this premise; SQLite project SQL does not use it"
    ),
    "sqlite_relation_shape_not_admitted": (
        "SQLite emission admits one source read with where, group by, having,"
        " order by, limit and select; JOINs, windows, qualify, distinct, set"
        " operations, relation lets and reads of another table or query are not"
        " available on SQLite"
    ),
    "sqlite_source_count_not_admitted": "read exactly one sqlite.table source",
    "sqlite_field_type_not_admitted": (
        "SQLite emission reads Int, Text, Bool and Float fields"
    ),
    "sqlite_parameter_not_admitted": (
        "declare Int, Text, Bool or Float parameters, with or without None"
    ),
    "sqlite_expression_not_admitted": (
        "use fields, literals, parameters, comparisons of two values of one type,"
        " and, or, not and is None; arithmetic, signs, in, ranges, conditionals,"
        " casts and function calls are not available on SQLite"
    ),
    "sqlite_aggregate_not_admitted": (
        "use count, count_distinct of an Int, Text or Bool field, min or max of an"
        " Int or Float field, or avg or sum of an Int field, each over one field"
        " of the source"
    ),
    "sqlite_projection_not_admitted": (
        "in a relation with group by or an aggregate, select group by keys,"
        " aggregates and literals"
    ),
    "sqlite_group_key_not_admitted": "group by fields of the source",
    "sqlite_order_not_admitted": (
        "order by fields of the source, or, with group by or an aggregate, by"
        " selected keys and aggregates"
    ),
    "sqlite_limit_not_admitted": "write limit as an Int literal",
    "source_identifier_unrepresentable": (
        'use the relation namespace "main" and a bare table name with no dot or'
        " NUL that does not start with sqlite_"
    ),
    "sqlite_table_name_mismatch": (
        "make the contract relation name equal the sqlite.table name"
    ),
    "column_identifier_unrepresentable_or_colliding": (
        "map each field to its own column; SQLite matches column names without"
        ' ASCII case, so "A" and "a" are one column'
    ),
    "nullability_mismatch": (
        "set nullable to false for a non-null field and true for an optional one"
    ),
    "physical_storage_or_domain_mismatch": (
        "use the SQLite storage and domain of the field's logical type"
    ),
    "sum_int_aggregate_range_proof_missing": (
        "declare an int_range on one side of zero, or keep this sum in"
        " check/plan: SQLite can fail a sum over values of both signs whose"
        " result fits"
    ),
}


def suggestion(code: str, detail: str) -> str:
    """The SQLite text of the specification's table, the premise rule with the
    SQLite value, or the existing text the other targets give the same detail."""
    if detail in _SUGGESTIONS:
        return _SUGGESTIONS[detail]
    for key, value in PREMISES.items():
        premise = canonical({"key": key, "scope": "statement", "value": value})
        if detail == f"{key}_declaration_missing":
            return f'add {premise.decode()} to "environment"'
        if detail in {f"{key}_declaration_mismatch", f"{key}_mismatch"}:
            return f"the reviewed sqlite value is {premise.decode()}"
    return blocker_suggestion(code, detail, None)


@dataclass(frozen=True, slots=True, eq=False)
class SQLiteArtifact:
    checked: Any
    contract: SQLiteContract
    policy: Any
    source_map: Any
    assessment: Any
    ast: SQLiteSelect
    sql: bytes
    tokens: tuple[Token, ...]
    document: bytes

    def __repr__(self) -> str:
        return "SQLiteArtifact(checked=..., ast=..., sql=..., document=...)"


@dataclass(frozen=True, slots=True, eq=False)
class SQLiteEmission:
    """One SQLite emission outcome; only `emit_sqlite_sql` makes a VERIFIED one."""

    status: str
    diagnostics: tuple[Any, ...]
    artifact: SQLiteArtifact | None = None
    blockers: tuple[Blocker, ...] = ()
    cli_errors: tuple[Any, ...] = ()
    family: str | None = FAMILY

    def __repr__(self) -> str:
        return (
            f"SQLiteEmission(status={self.status!r},"
            f" artifact={'present' if self.artifact is not None else 'none'})"
        )


def _key(span: Any) -> tuple[str, int, int]:
    return (span.path or "", span.line, span.column)


def _fold(name: str) -> str:
    return name.translate(_FOLD)


def _limits(premises: tuple[Premise, ...]) -> dict[str, int]:
    limits = {
        "sql_bytes": MAX_SQL_BYTES,
        "artifact_bytes": MAX_ARTIFACT_BYTES,
        "nodes": MAX_NODES,
        "parameters": PARAMETERS,
        "columns": COLUMNS,
    }
    for premise in premises:
        if premise.scope == "statement" and premise.key == "resource_limits":
            for key, value in json.loads(premise.value).items():
                if key in limits:
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


def _tag(expression: Any) -> str | None:
    """The logical type of a plan expression, when it is a known builtin."""
    value_type = expression.value_type
    resolved = getattr(value_type, "resolved_type", None)
    if getattr(value_type.kind, "value", None) != "known" or resolved is None:
        return None
    return resolved.name if getattr(resolved.kind, "value", None) == "builtin" else None


def _function(aggregate: Any) -> str | None:
    source = aggregate.source
    if type(source) is not aggregation.ProjectAggregateExpressionAnalysis:
        return None
    return aggregation.filtered_function(source.call) or source.fact.function


def _fits(name: str | None, representation: dict[str, Any]) -> bool:
    """The representation table of the specification for one logical type."""
    storage, domain = representation["storage"]["kind"], representation["domain"]
    if name == "Int":
        return (
            storage == "sqlite_integer"
            and domain["kind"] == "int_range"
            and -(2**63) <= int(domain["min"])
            and int(domain["max"]) <= MAX_INT
        )
    if name == "Text":
        return (
            storage == "sqlite_text"
            and domain["kind"] == "text"
            and all(domain[key] == value for key, value in _TEXT.items())
        )
    expected = {
        "Bool": ("sqlite_bool01", "bool01"),
        "Float": ("sqlite_real", "finite_float"),
    }
    return name in expected and (storage, domain["kind"]) == expected[name]


class _View:
    """The plan seen as one SQLite statement: what each port carries, and the
    source field, group key or aggregate it ends at."""

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        self.refs = reference_source_ports(plan)
        self.carried: dict[Any, Any] = {
            p.ref: p.producer_port
            for p in plan.input_ports
            if p.producer_port is not None
        }
        self.carried.update(
            {p.ref: p.source for p in (*plan.stage_ports, *plan.result_ports)}
        )
        self.carried.update(
            {p.ref: p.source_port for p in plan.projections if p.source_port}
        )
        self.carried.update({p.ref: p.input for p in plan.aggregate_projections})
        source = plan.sources[0] if len(plan.sources) == 1 else None
        self.ports = () if source is None else _ports(plan, source)
        self.index = {port.ref: k for k, port in enumerate(self.ports)}
        self.projections = {p.export: p for p in plan.projections}
        self.grouped = {p.export: p for p in plan.aggregate_projections}
        self.group_keys = {k.ref: k for k in plan.group_keys}
        self.aggregates = {a.ref: a for a in plan.aggregates}
        self.order_uses = {u.ref: u for u in plan.order_uses}
        self.aggregated = bool(plan.aggregations)
        self.selected = {id(self.end(p.input)) for p in plan.aggregate_projections} - {
            id(None)
        }

    def filter(self, role: str) -> Any:
        """The predicate of the `where` or of the `having`, else None."""
        found = [
            f
            for f in self.plan.filters
            if getattr(getattr(f.site, "role", None), "value", None) == role
        ]
        return self.expression(found[0].predicate) if len(found) == 1 else None

    def end(self, ref: Any) -> Any:
        """The source port, group key or aggregate that `ref` carries, else None."""
        seen: set[int] = set()
        while ref in self.carried and id(ref) not in seen:
            seen.add(id(ref))
            ref = self.carried[ref]
        if ref in self.index:
            return ref
        return self.group_keys.get(ref) or self.aggregates.get(ref)

    def field(self, ref: Any) -> int | None:
        found = self.end(ref)
        return self.index.get(found) if found in self.index else None

    def direct(self, expression: Any) -> int | None:
        """The source field that `expression` reads directly, else None."""
        if type(expression) is not expressions.ProjectSQLReference:
            return None
        found = self.refs.get(expression.ref)
        return None if found is None else self.index.get(found[1].ref)

    def expression(self, ref: Any) -> Any:
        return self.plan.expressions[ref.position]

    def children(self, node: Any) -> tuple[Any, ...]:
        kind = type(node)
        if kind in (expressions.ProjectSQLComparison, expressions.ProjectSQLBinary):
            return (self.expression(node.left), self.expression(node.right))
        if kind is expressions.ProjectSQLUnary:
            return (self.expression(node.operand),)
        if kind is expressions.ProjectSQLIsNull:
            return (self.expression(node.value),)
        return ()

    def admitted(self, node: Any) -> bool:
        """Rule 9 at one node of a `select`, `where` or aggregate argument."""
        kind = type(node)
        if kind is expressions.ProjectSQLReference:
            return self.direct(node) is not None
        if kind is aggregation.ProjectSQLResultReference:
            # A `having` or composed output read of a group key or aggregate;
            # rules 10 and 11 own which aggregates and outputs.
            return type(self.end(node.port)) in (
                aggregation.ProjectSQLGroupKey,
                aggregation.ProjectSQLAggregate,
            )
        if kind in _LITERALS:
            return literal_text(node.expression.value) is not None
        if kind is expressions.ProjectSQLComparison:
            left, right = self.children(node)
            return (
                node.expression.operator in OPERATORS
                and _tag(left) is not None
                and _tag(left) == _tag(right)
            )
        if kind is expressions.ProjectSQLBinary:
            return node.expression.operator in LOGICAL
        if kind is expressions.ProjectSQLUnary:
            return node.expression.operator == "not"
        return kind in (
            expressions.ProjectSQLParameterRead,
            expressions.ProjectSQLIsNull,
        )

    def key(self, item: Any) -> Any:
        """The source port, group key or aggregate one `order by` item reads."""
        order = self.plan.order_expressions[item.expression.position]
        hidden = self.plan.hidden_order_requirements
        if (
            len(item.uses) != 1
            or order.operands
            or any(h.item is item.ref for h in hidden)
        ):
            return None
        use = self.order_uses.get(item.uses[0])
        if use is None or len(use.ports) != 1:
            return None
        found = self.end(use.ports[0])
        if not self.aggregated:
            return found if found in self.index else None
        return found if id(found) in self.selected else None

    def roots(self) -> list[Any]:
        """Each plan value the statement renders: the results, the `where` and
        `having` filters, then each `group by` and `order by` key."""
        plan = self.plan
        found: list[Any] = []
        for export in plan.exports:
            grouped = self.grouped.get(export.ref)
            if grouped is not None:
                found.append(self.end(grouped.input))
            elif export.ref in self.projections:
                found.append(self.expression(self.projections[export.ref].expression))
        found.extend(self.expression(f.predicate) for f in plan.filters)
        found.extend(plan.group_keys)
        found.extend(self.key(item) for item in plan.order_items)
        return found

    def planned(self) -> tuple[int, int]:
        """`size` of the statement the plan admits, counted from the plan."""
        plan = self.plan
        nodes = 2 + len(plan.exports) + len(plan.group_keys) + len(plan.order_items)
        nodes += bool(plan.result_limits)
        depth = 0
        pending = [(root, 1) for root in self.roots()]
        while pending:
            node, level = pending.pop()
            nodes += 1
            depth = max(depth, level)
            if type(node) is aggregation.ProjectSQLResultReference:
                node = self.end(node.port)  # rendered as the key or aggregate
            if type(node) is aggregation.ProjectSQLAggregate:
                children: tuple[Any, ...] = node.arguments[:1]
            else:
                children = self.children(node)
            pending.extend((child, level + 1) for child in children)
        return nodes, depth


class _Rules:
    """Rules 1-35: at most one blocker per rule, at its first failing site."""

    def __init__(self, checked: Any, contract: SQLiteContract, policy: Any) -> None:
        self.found: dict[int, Blocker] = {}
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
                "sqlite_relation_shape_not_admitted",
                location=self.statement
                if first is None
                else getattr(first.site, "span", None) or first.owner.definition.span,
            )
            return
        self.plan: Any = plan
        self.view = _View(plan)
        self.reads = tuple(
            e
            for e in plan.expressions
            if type(e) is expressions.ProjectSQLParameterRead
        )
        self.shape()
        self.fields()
        self.values()
        self.aggregates()
        self.projections()
        self.keys()
        self.environment(_limits(premises))
        self.evidence()
        for source in self.ordered:
            self.source(source)
        self.sums()

    def fail(
        self,
        rule: int,
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

    def first(
        self, rule: int, code: str, detail: str, sites: list[tuple[Any, Any]]
    ) -> None:
        """One blocker at the first of `sites`, (subject, span) pairs, in source
        order."""
        if sites:
            subject, span = min(sites, key=lambda site: _key(site[1]))
            self.fail(rule, code, detail, subject, span)

    def blockers(self) -> tuple[Blocker, ...]:
        return tuple(self.found[rule] for rule in sorted(self.found))

    def shape(self) -> None:
        plan = self.plan
        named = tuple(
            d
            for d in plan.bindings.definitions
            if type(d.entry.owner.definition) is not SourceDef
        )
        operators = tuple(
            tuple(o.kind.value for o in block.operators) for block in plan.blocks
        )
        flat = sum(operators, ())
        results = tuple(b.kind.value for b in plan.result_boundaries)
        if not (
            len(named) == 1
            and len(plan.sources) == 1
            and len(plan.input_uses) == 1
            and operators in _SHAPES
            and len(plan.filters) == ("row_filter" in flat) + ("result_filter" in flat)
            and len(plan.aggregations) == ("group_aggregate" in flat)
            and results in _RESULTS
            and len(plan.orders) == ("relation_ordering" in results)
            and len(plan.result_limits) == ("limit" in results)
            and not any(getattr(plan, name) for name in _EMPTY)
        ):
            definition = self.checked.selected_owner.definition
            clauses = ()
            if type(definition) in (QueryDef, TableDef):
                clauses = tuple(
                    clause
                    for clause in (
                        definition.let_clause,
                        definition.qualify_clause,
                        definition.distinct_clause,
                        *definition.join_clauses,
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
                5, "PIE-B1003", "sqlite_relation_shape_not_admitted", location=site
            )
        self.ordered = tuple(
            sorted(plan.sources, key=lambda s: _key(s.declaration.span))
        )
        if not self.ordered:
            self.fail(6, "PIE-B1003", "sqlite_source_count_not_admitted", at=True)
        elif len(self.ordered) > 1:
            second = self.ordered[1]
            self.fail(
                6,
                "PIE-B1003",
                "sqlite_source_count_not_admitted",
                second.ref,
                second.declaration.span,
            )

    def fields(self) -> None:
        plan = self.plan
        for source in self.ordered:
            for port in _ports(plan, source):
                if _type_name(port) is None:
                    definition = port.field.evidence.field_def
                    self.fail(
                        7,
                        "PIE-B1003",
                        "sqlite_field_type_not_admitted",
                        port.ref,
                        None if definition is None else definition.span,
                    )
        for parameter in plan.parameters:
            if parameter.tag not in TYPES:
                self.fail(
                    8,
                    "PIE-B1003",
                    "sqlite_parameter_not_admitted",
                    None,
                    parameter.declaration.span,
                )

    def values(self) -> None:
        view, sites = self.view, []
        for node in self.plan.expressions:
            if type(node.site) in (
                expressions.ProjectSQLExpressionSite,
                aggregation.ProjectSQLAggregateSite,
            ):
                admitted = view.admitted(node)
            else:  # a joined, match or qualify site, which rule 5 refuses
                admitted = type(node) not in _LITERALS or (
                    literal_text(node.expression.value) is not None
                )
            if not admitted:
                sites.append((node.ref, node.expression.span))
        self.first(9, "PIE-B1003", "sqlite_expression_not_admitted", sites)

    def aggregates(self) -> None:
        view, sites = self.view, []
        whole = view.selected | {id(view.key(item)) for item in self.plan.order_items}
        for aggregate in self.plan.aggregates:
            function = _function(aggregate)
            arguments = tuple(view.expression(a) for a in aggregate.arguments)
            fields = tuple(view.direct(a) for a in arguments)
            if not (
                function in FUNCTIONS
                and not aggregate.order_by
                and (
                    len(arguments) <= 1 if function == "count" else len(arguments) == 1
                )
                and None not in fields
                and (
                    function == "count"
                    or {_type_name(view.ports[f]) for f in fields if f is not None}
                    <= _ARGUMENTS[str(function)]
                )
                and id(aggregate) in whole
            ):
                call = getattr(aggregate.source, "call", None)
                sites.append(
                    (aggregate.ref, self.statement if call is None else call.span)
                )
        self.first(10, "PIE-B1003", "sqlite_aggregate_not_admitted", sites)

    def projections(self) -> None:
        if not self.view.aggregated:
            return
        view, sites = self.view, []
        for export in self.plan.exports:
            grouped = view.grouped.get(export.ref)
            if grouped is not None:
                if view.end(grouped.input) is None:
                    sites.append((grouped.ref, self.statement))
                continue
            projection = view.projections.get(export.ref)
            if projection is None:
                sites.append((export.ref, self.statement))
            elif type(view.expression(projection.expression)) not in _LITERALS:
                sites.append((projection.ref, projection.site.occurrence.span))
        self.first(11, "PIE-B1003", "sqlite_projection_not_admitted", sites)

    def keys(self) -> None:
        view, plan = self.view, self.plan
        self.first(
            12,
            "PIE-B1003",
            "sqlite_group_key_not_admitted",
            [
                (key.ref, getattr(getattr(key.source, "item", None), "span", None))
                for key in plan.group_keys
                if type(key.source) is not ProjectGroupKeyFact
                or view.field(key.input) is None
            ],
        )
        self.first(
            13,
            "PIE-B1003",
            "sqlite_order_not_admitted",
            [
                (
                    item.ref,
                    plan.order_expressions[item.expression.position].expression.span,
                )
                for item in plan.order_items
                if view.key(item) is None
            ],
        )
        for limit in plan.result_limits:
            if not (
                type(limit.literal.value) is int
                and type(limit.value) is int
                and 0 <= limit.value <= MAX_INT
            ):
                self.fail(
                    14,
                    "PIE-B1003",
                    "sqlite_limit_not_admitted",
                    limit.ref,
                    limit.clause.span,
                )

    def environment(self, limits: dict[str, int]) -> None:
        plan, view = self.plan, self.view
        computed = any(
            view.direct(view.expression(p.expression)) is None for p in plan.projections
        )
        statement = [p for p in self.contract.premises if p.scope == "statement"]
        for rule, key, needed in (
            (
                17,
                "operator_environment",
                bool(
                    plan.filters
                    or plan.aggregations
                    or plan.orders
                    or plan.result_limits
                    or computed
                ),
            ),
            (18, "parameter_protocol", bool(self.reads)),
        ):
            found = [p for p in statement if p.key == key]
            if needed and not found:
                self.fail(rule, "PIE-B1004", key + "_declaration_missing", at=True)
            elif needed and json.loads(found[0].value) != PREMISES[key]:
                self.fail(rule, "PIE-B1005", key + "_declaration_mismatch", at=True)
        if len(self.reads) > limits["parameters"]:
            self.fail(19, "PIE-B1007", "parameter_occurrence_limit", at=True)
        try:
            nodes, depth = view.planned()
        except (AttributeError, LookupError, TypeError):
            nodes, depth = 0, 0  # an unadmitted plan, which rules 5-14 refuse
        if (
            any(len(_ports(plan, s)) > limits["columns"] for s in plan.sources)
            or len(plan.exports) > limits["columns"]
            or nodes > limits["nodes"]
            or depth > DEPTH
        ):
            self.fail(20, "PIE-B1007", "generated_structure_limit", at=True)
        self.limits = limits

    def evidence(self) -> None:
        view = inspect_project_sql_plan(self.checked)
        report = view.requirements().verification
        request = targets.prepare_database_target_request(FAMILY, RELEASE)
        # As on the other targets; the command passes no profile, so only
        # `explicit_target_profile_missing` arises there.
        for issue in request.issues:
            if issue.value == "profile_target_family_or_release_mismatch":
                self.fail(15, "PIE-B1005", "target_evidence_scope_conflict", request)
            elif issue.value == "profile_composition_blocked":
                self.fail(
                    16, "PIE-B1006", "original_profile_composition_unresolved", request
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
                    21,
                    "PIE-B1006",
                    "negative_original_target_evidence",
                    aspect.entry.subject,
                )
        for obligation in report.report.summary.enforcement_required:
            self.fail(
                22,
                "PIE-B1006",
                "original_enforcement_not_fulfilled",
                obligation.entry.subject,
            )

    def source(self, source: Any) -> None:
        plan, at = self.plan, source.declaration.span
        if _spelling(source.connector) != "sqlite.table":
            self.fail(23, "PIE-B1001", "source_family_mismatch", source.ref, at)
        entries = [s for s in self.contract.sources if s.owner is source.source.owner]
        if len(entries) != 1:
            self.fail(24, "PIE-B1001", "source_mapping_missing", source.ref, at)
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
                25,
                "PIE-B1001",
                "complete_ordered_source_schema_required",
                source.ref,
                at,
                related,
            )
        name = entry.name
        if (
            entry.namespace != "main"
            or "." in name
            or "\x00" in name
            or _fold(name).startswith("sqlite_")
        ):
            self.fail(
                26, "PIE-B1001", "source_identifier_unrepresentable", source.ref, at
            )
        if name != source.connector.arguments[0].value:
            self.fail(27, "PIE-B1001", "sqlite_table_name_mismatch", source.ref, at)
        owned = [p for p in self.contract.premises if p.scope is entry.owner]
        for rule, key in ((28, "row_domain_matches"), (29, "read_only_object")):
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
                30, "PIE-B1004", "client_encoding_declaration_missing", source.ref, at
            )
        elif any(json.loads(p.value) != PREMISES["client_encoding"] for p in clients):
            self.fail(30, "PIE-B1005", "client_encoding_mismatch", source.ref, at)
        folded: set[str] = set()
        for field in sorted(entry.fields, key=lambda f: f.ordinal):
            port = ports[field.ordinal]
            definition = port.field.evidence.field_def
            place = (port.ref, None if definition is None else definition.span)
            if "\x00" in field.column or _fold(field.column) in folded:
                self.fail(
                    31,
                    "PIE-B1001",
                    "column_identifier_unrepresentable_or_colliding",
                    *place,
                )
            folded.add(_fold(field.column))
            nullable = {"non_null": False, "nullable": True}.get(
                port.field.effective_nullability.value
            )
            if nullable is None or field.representation["nullable"] is not nullable:
                self.fail(32, "PIE-B1002", "nullability_mismatch", *place)
            if not _fits(_type_name(port), field.representation):
                self.fail(
                    33, "PIE-B1002", "physical_storage_or_domain_mismatch", *place
                )
            sites = tuple(
                expression.site
                for expression, read in self.view.refs.values()
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
                    self.fail(34, "PIE-B1005", "field_domain_premise_mismatch", *place)

    def sums(self) -> None:
        """Rule 35: a `sum` reads an `Int` field whose `int_range` lies on one
        side of zero, so SQLite fails exactly where the exact sum leaves
        signed 64 bits, and never on a partial sum alone."""
        if len(self.plan.sources) != 1:
            return  # rule 6
        view, sites = self.view, []
        (source,) = self.plan.sources
        entries = [s for s in self.contract.sources if s.owner is source.source.owner]
        fields = {} if len(entries) != 1 else {f.ordinal: f for f in entries[0].fields}
        for aggregate in self.plan.aggregates:
            arguments = aggregate.arguments
            field = None
            if _function(aggregate) == "sum" and len(arguments) == 1:
                field = view.direct(view.expression(arguments[0]))
            if field not in fields:
                continue
            representation = fields[field].representation
            domain = representation["domain"]
            if (
                _type_name(view.ports[field]) == "Int"
                and _fits("Int", representation)  # rule 33 holds
                and int(domain["min"]) < 0 < int(domain["max"])
            ):
                call = getattr(aggregate.source, "call", None)
                sites.append(
                    (aggregate.ref, self.statement if call is None else call.span)
                )
        self.first(35, "PIE-B1004", "sum_int_aggregate_range_proof_missing", sites)


def _entry(artifact_contract: SQLiteContract, plan: Any) -> Any:
    (source,) = plan.sources
    (entry,) = (s for s in artifact_contract.sources if s.owner is source.source.owner)
    return entry


def _expected_ast(plan: Any, contract: SQLiteContract) -> SQLiteSelect:
    """The statement the plan admits; parameters are numbered by first read in
    rendering order, which is the order the AST is built in."""
    view, entry = _View(plan), _entry(contract, plan)
    numbers: dict[int, int] = {}

    def aggregate(found: Any, subject: Any) -> SQLiteAggregate:
        function, argument = str(_function(found)), None
        assert function in FUNCTIONS
        if found.arguments:
            read = view.expression(found.arguments[0])
            field = view.direct(read)
            assert field is not None
            argument = SQLiteColumn(field, read.ref)
        collate = function == "count_distinct" and text(argument)
        return SQLiteAggregate(function, argument, collate, subject)

    def value(node: Any) -> Any:
        kind = type(node)
        if kind is aggregation.ProjectSQLAggregate:
            return aggregate(node, node.ref)
        if kind is aggregation.ProjectSQLResultReference:
            # A `having` read of a selected key or aggregate, written as that
            # key or aggregate, never as its output alias.
            found = view.end(node.port)
            if type(found) is aggregation.ProjectSQLAggregate:
                return aggregate(found, node.ref)
            assert type(found) is aggregation.ProjectSQLGroupKey
            field = view.field(found.input)
            assert field is not None
            return SQLiteColumn(field, node.ref)
        if kind is aggregation.ProjectSQLGroupKey:
            field = view.field(node.input)
            assert field is not None
            return SQLiteColumn(field, node.ref)
        if kind is expressions.ProjectSQLReference:
            field = view.direct(node)
            assert field is not None
            return SQLiteColumn(field, node.ref)
        if kind is expressions.ProjectSQLLiteral:
            return SQLiteLiteral(node.expression.value, node.ref)
        if kind is expressions.ProjectSQLParameterRead:
            number = numbers.setdefault(node.parameter.ordinal, len(numbers) + 1)
            return SQLiteParameter(number, node.ref)
        children = view.children(node)
        if kind is expressions.ProjectSQLComparison:
            left, right = children
            return SQLiteComparison(
                OPERATORS[node.expression.operator],
                value(left),
                value(right),
                _tag(left) == "Text",
                node.ref,
            )
        if kind is expressions.ProjectSQLBinary:
            left, right = children
            operator = LOGICAL[node.expression.operator]
            return SQLiteLogical(operator, value(left), value(right), node.ref)
        (operand,) = children
        if kind is expressions.ProjectSQLUnary:
            return SQLiteNot(value(operand), node.ref)
        assert kind is expressions.ProjectSQLIsNull
        return SQLiteIsNull(value(operand), node.expression.negated, node.ref)

    def text(column: Any) -> bool:
        return type(column) is SQLiteColumn and (
            _type_name(view.ports[column.field]) == "Text"
        )

    results = []
    for export in plan.exports:
        grouped = view.grouped.get(export.ref)
        if grouped is not None:
            subject, node = grouped.ref, view.end(grouped.input)
        else:
            projection = view.projections[export.ref]
            subject, node = projection.ref, view.expression(projection.expression)
        results.append(
            SQLiteResult(value(node), export.identity.name, subject, export.ref)
        )
    where = view.filter("where")
    where = None if where is None else value(where)
    group_by = []
    for key in plan.group_keys:
        column = value(key)
        group_by.append(SQLiteKey(column, text(column), None, key.ref))
    having = view.filter("satisfying")
    having = None if having is None else value(having)
    order_by = []
    for item in plan.order_items:
        found = view.key(item)
        column = (
            SQLiteColumn(view.index[found], item.ref)
            if found in view.index
            else value(found)
        )
        descending = item.source.direction.value == "desc"
        order_by.append(SQLiteKey(column, text(column), descending, item.ref))
    limit = None
    if plan.result_limits:
        found = plan.result_limits[0]
        limit = SQLiteLimit(found.value, found.ref)
    (source,) = plan.sources
    return SQLiteSelect(
        entry.name,
        tuple(f.column for f in sorted(entry.fields, key=lambda f: f.ordinal)),
        tuple(results),
        where,
        tuple(group_by),
        having,
        tuple(order_by),
        limit,
        plan.scope,
        source.ref,
    )


def _labels(plan: Any) -> tuple[str, ...]:
    return tuple(export.identity.name for export in plan.exports)


def _holds(ast: SQLiteSelect, plan: Any) -> bool:
    """The AST's own SQL rules, over the plan's `Text` fields and parameters,
    and its size as counted from the plan."""
    view = _View(plan)
    fields = frozenset(
        k for k, port in enumerate(view.ports) if _type_name(port) == "Text"
    )
    reads = {e.ref: e for e in plan.expressions}
    texts = frozenset(
        node.number
        for node in _parameters(ast)
        if node.subject in reads and reads[node.subject].parameter.tag == "Text"
    )
    return (
        ast_rules_hold(ast, _labels(plan), fields, texts)
        and size(ast) == view.planned()
    )


def _parameters(ast: SQLiteSelect) -> list[SQLiteParameter]:
    """Each parameter node in rendering order."""
    found: list[SQLiteParameter] = []
    pending: list[Any] = [
        *(r.value for r in ast.results),
        *(() if ast.where is None else (ast.where,)),
        *(() if ast.having is None else (ast.having,)),
    ]
    pending.reverse()
    while pending:
        node = pending.pop()
        if type(node) is SQLiteParameter:
            found.append(node)
        for name in ("right", "left", "operand"):
            child = getattr(node, name, None)
            if child is not None:
                pending.append(child)
    return found


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


def _int_range(low: int, high: int) -> dict[str, Any]:
    return {"kind": "int_range", "min": str(low), "max": str(high)}


def _domain(tag: str, value: object = None, width: int | None = None) -> Any:
    """The domain of a computed `tag` value; an Int literal is its own range."""
    if tag == "Int":
        return (
            _int_range(-(2**63), MAX_INT)
            if value is None
            else _int_range(int(str(value)), int(str(value)))
        )
    if tag == "Text":
        return {"kind": "text", "max_characters": width} | _TEXT
    if tag == "Bool":
        return {"kind": "bool01"}
    return {"kind": "finite_float", "format": "binary64"}


def _columns(artifact: SQLiteArtifact) -> list[dict[str, Any]]:
    """Each result column: its type, representation and correspondence."""
    plan = artifact.checked.plan
    view, entry = _View(plan), _entry(artifact.contract, plan)
    fields = {f.ordinal: f for f in entry.fields}
    columns = []
    for position, (result, export) in enumerate(
        zip(artifact.ast.results, plan.exports, strict=True)
    ):
        value = result.value
        tag = _type_name(export)
        # A nullability that `check` leaves unknown, as a comparison's, may
        # be NULL, so the `sqlite_file` route's Arrow schema must allow it.
        nullable = export.field.effective_nullability.value != "non_null"
        correspondence: dict[str, Any] = {}
        if type(value) is SQLiteColumn:
            field = fields[value.field]
            representation = field.representation
            port = view.ports[value.field]
            correspondence = {
                "source": entry.selector,
                "field": value.field,
                "source_port": _ref(port.ref),
            }
            if view.aggregated:
                correspondence["group_key"] = _ref(value.subject)
            else:
                projection = view.projections[export.ref]
                correspondence["input_port"] = _ref(projection.input_port)
        elif type(value) is SQLiteAggregate:
            assert tag is not None
            if value.function in ("count", "count_distinct"):
                storage, domain = "sqlite_integer", _int_range(0, MAX_INT)
            elif value.function in ("min", "max"):
                assert value.argument is not None
                read = fields[value.argument.field].representation
                storage, domain = read["storage"]["kind"], read["domain"]
            else:  # avg is a Float and sum an Int over the widest domain
                storage, domain = STORAGES[tag], _domain(tag)
            representation = {
                "storage": {"kind": storage},
                "nullable": nullable,
                "domain": domain,
            }
            correspondence = {"aggregate": _ref(value.subject)}
        else:
            assert tag is not None
            literal = value.value if type(value) is SQLiteLiteral else None
            width = len(literal) if type(literal) is str else None
            representation = {
                "storage": {"kind": STORAGES[tag]},
                "nullable": nullable,
                "domain": _domain(tag, literal if tag == "Int" else None, width),
            }
            correspondence = {"expression": _ref(value.subject)}
        columns.append(
            {
                "ordinal": position,
                "label": result.label,
                "logical_type": {"kind": "builtin", "name": tag, "parameters": None},
                "nullable": representation["nullable"],
                "representation": representation,
                "correspondence": correspondence
                | {
                    "export": _ref(export.ref),
                    "projection": _ref(result.subject),
                    "sql_symbol": position,
                },
            }
        )
    return columns


def _document(artifact: SQLiteArtifact) -> bytes:
    checked, plan = artifact.checked, artifact.checked.plan
    semantic, owner = checked.completed.semantic_result, checked.selected_owner
    contract = json.loads(artifact.contract.normalized)
    indexes = artifact.source_map.indexes
    ranges = []
    for token in artifact.tokens:
        subject = token.subject
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
    reads = {e.ref: e for e in plan.expressions}
    placeholders = [t for t in artifact.tokens if t.kind == "parameter"]
    numbers = {node.subject: node.number for node in _parameters(artifact.ast)}
    requirements = [
        {
            "denominator": "original",
            "ordinal": i,
            "kind": demand.entry.family.value,
            "subject": _ref(demand.entry.subject),
            "rule": "sqlite_b2",
            "disposition": "checked_rule",
            "premises": [],
            "evidence": [
                [s.value for s in aspect.outcomes] for aspect in demand.aspects
            ],
        }
        for i, demand in enumerate(artifact.assessment.assessment.demands)
    ]
    requirements += [
        {
            "denominator": "generated",
            "ordinal": i,
            "kind": "query_parameter",
            "subject": _ref(token.subject),
            "rule": "R04",
            "disposition": "checked_rule",
            "premises": [],
            "evidence": [{"parameter": reads[token.subject].parameter.ordinal}],
        }
        for i, token in enumerate(placeholders)
    ]
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
                "owner": {
                    "kind": "parameter",
                    "parameter": reads[token.subject].parameter.ordinal,
                },
                "server_index": numbers[token.subject],
                "physical_type": STORAGES[reads[token.subject].parameter.tag],
                "range": {"start": token.start, "end": token.end},
            }
            for i, token in enumerate(placeholders)
        ],
        "columns": _columns(artifact),
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
                    _ref(e.ref)
                    for e in plan.expressions
                    if type(e) is expressions.ProjectSQLParameterRead
                    and e.parameter is p
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
        if type(artifact) is not SQLiteArtifact:
            return False
        plan = artifact.checked.plan
        if (
            type(plan) is not plans.ProjectSQLPlan
            or artifact.ast != _expected_ast(plan, artifact.contract)
            or not _holds(artifact.ast, plan)
            or render(artifact.ast) != (artifact.sql, artifact.tokens)
        ):
            return False
        return _document(artifact) == artifact.document
    except (AssertionError, AttributeError, LookupError, TypeError, ValueError):
        return False


def emit_sqlite_sql(
    checked: Any, data: bytes, policy: Any, *, read_sources_only: bool = False
) -> SQLiteEmission:
    """Rules 1-39 over one verified plan and the contract bytes."""
    diagnostics = checked.completed.diagnostics
    contract = read_sqlite_contract(checked, data, read_sources_only=read_sources_only)
    if isinstance(contract, tuple):
        return SQLiteEmission(
            "INPUT_REJECTED", diagnostics, cli_errors=contract, family=None
        )
    rules = _Rules(checked, contract, policy)
    blockers = rules.blockers()
    if blockers:
        return SQLiteEmission("BLOCKED", diagnostics, blockers=blockers)

    def blocked(code: str, detail: str) -> SQLiteEmission:
        return SQLiteEmission("BLOCKED", diagnostics, blockers=(Blocker(code, detail),))

    plan = checked.plan
    ast: SQLiteSelect | None = None
    try:
        ast = _expected_ast(plan, contract)
        holds = _holds(ast, plan)
    except (AssertionError, AttributeError, LookupError, TypeError, ValueError):
        holds = False
    if ast is None or not holds:
        return blocked("PIE-B1008", "plan_ast_correspondence")
    sql, tokens = render(ast)
    if len(sql) > rules.limits["sql_bytes"]:
        return blocked("PIE-B1007", "sql_byte_limit")
    parts = (checked, contract, policy, rules.source_map, rules.assessment, ast)
    artifact = SQLiteArtifact(*parts, sql, tokens, b"")
    artifact = SQLiteArtifact(*parts, sql, tokens, _document(artifact))
    if not verify_artifact(artifact):
        return blocked("PIE-B1008", "artifact_correspondence")
    if len(artifact.document) > rules.limits["artifact_bytes"]:
        return blocked("PIE-B1007", "public_artifact_byte_limit")
    return SQLiteEmission("VERIFIED", diagnostics, artifact=artifact)


def serialize_sqlite_emission(outcome: Any) -> bytes:
    """A VERIFIED document whose artifact verifies afresh, else the failure
    document, with the SQLite suggestions."""
    if outcome.status == "VERIFIED":
        artifact = outcome.artifact
        if (
            type(outcome) is SQLiteEmission
            and artifact is not None
            and not outcome.blockers
            and not outcome.cli_errors
            and outcome.diagnostics is artifact.checked.completed.diagnostics
            and verify_artifact(artifact)
        ):
            return artifact.document
        outcome = SQLiteEmission(
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
