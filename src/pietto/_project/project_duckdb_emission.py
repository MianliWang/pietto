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
import json
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
from pietto._project.project_duckdb_sql import (
    OPERATORS,
    RELATION,
    DuckDBColumn,
    DuckDBComparison,
    DuckDBHaving,
    DuckDBSelect,
    Token,
    ast_rules_hold,
    node_count,
    render,
)
from pietto._project.project_sql_emission_contract import (
    CODES,
    MAX_ARTIFACT_BYTES,
    MAX_NODES,
    MAX_PARAMETERS,
    MAX_SQL_BYTES,
    Blocker,
    Premise,
    canonical,
)
from pietto._project.project_sql_emission_scopes import (
    reference_source_ports,
    stage_origins,
)
from pietto._project.project_sql_emission_suggestions import blocker_suggestion
from pietto._project.project_sql_plan_expressions import (
    ProjectSQLComparison,
    ProjectSQLParameterRead,
    ProjectSQLReference,
)
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

__all__: tuple[str, ...] = ()

FORMAT = "pietto.sql-emission.v1"
PARAMETERIZED_FORMAT = "pietto.sql-emission.v2"
COLUMNS = 4096
TYPES = ("Int", "Text", "Bool", "Float")
PREMISES = {
    "client_encoding": "UTF8",
    "operator_environment": "builtin_only",
    "parameter_protocol": "duckdb_prepared",
}
NOT_ADMITTED = ("identifier_case", "session_sql_mode", "session_time_zone")
# Every plan collection that an admitted statement leaves empty.
_EMPTY = (
    "let_values",
    "joins",
    "join_inputs",
    "relationship_matches",
    "single_matches",
    "windows",
    "window_arguments",
    "window_projections",
    "result_boundaries",
    "distincts",
    "orders",
    "result_limits",
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
_FILTERS = ("row_filter", "result_filter")
# The argument types of each admitted aggregate (rule 7a).
_AGGREGATES = {
    "count": ((), ("Int",), ("Text",), ("Bool",), ("Float",)),
    "sum": (("Int",),),
    "min": (("Int",), ("Float",)),
    "max": (("Int",), ("Float",)),
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
        "DuckDB emission admits one source read with where, group by, having,"
        " select, order by and limit; JOIN, windows, qualify, distinct, set"
        " operations, relation lets and derived sources are not available on"
        " DuckDB"
    ),
    "duckdb_source_count_not_admitted": (
        "read exactly one duckdb.arrow source; the DuckDB route runs one query"
        " over one Arrow table"
    ),
    "duckdb_projection_not_admitted": (
        "select source fields directly, or group by keys and aggregates of"
        " fields, such as select: customer, total = sum(amount); computed values"
        " are not available on DuckDB"
    ),
    "duckdb_aggregate_not_admitted": (
        "use count(), count(field), sum of an Int field, or min or max of an Int"
        " or Float field; other aggregates, sum or avg of a Float and aggregates"
        " of computed values are not available on DuckDB"
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
        "declare non-null Int, Text, Bool or Float parameters and read each one"
        " in a where or having comparison"
    ),
    "duckdb_field_type_not_admitted": "DuckDB emission reads Int, Text, Bool and Float fields",
    "source_identifier_unrepresentable": (
        'use the relation namespace "arrow"; the DuckDB route reads one'
        " registered Arrow table"
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


def _fits(name: str | None, representation: dict[str, Any]) -> bool:
    """The representation table of the route for one logical type."""
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


class _Values:
    """What the plan's values read: source ports, group keys and aggregates."""

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        self.refs = reference_source_ports(plan)
        self.origins = stage_origins(plan)
        self.sources = {port.ref: port for port in plan.source_ports}
        owners = {item.ref: item for item in (*plan.group_keys, *plan.aggregates)}
        # Each stage port that carries a group key's or aggregate's result
        # unmodified; a port's source precedes it, as for stage_origins.
        self.owners: dict[Any, Any] = {}
        for port in plan.stage_ports:
            owner = owners.get(port.source) or self.owners.get(port.source)
            if owner is not None:
                self.owners[port.ref] = owner

    def direct(self, expression: Any) -> Any:
        """The source port that `expression` reads directly, else None."""
        if type(expression) is not ProjectSQLReference:
            return None
        found = self.refs.get(expression.ref)
        return None if found is None else found[1]

    def key(self, key: Any) -> Any:
        """The source port that a group key reads directly, else None."""
        port = self.origins.get(key.input)
        return None if port is None else self.sources.get(port.producer_port)

    def aggregate(self, aggregate: Any) -> tuple[str, Any] | None:
        """(function, the source port it reads, None in count()) of an
        aggregate that rule 7a admits, else None."""
        source = aggregate.source
        if type(source) is not aggregation.ProjectAggregateExpressionAnalysis:
            return None
        call = aggregation.aggregate_call(source)
        function = aggregation.filtered_function(call) or source.fact.function
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
                if not plan.aggregations and projection.input_port is not None:
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

    def value(self, owner: Any) -> tuple[Any, str | None]:
        """(source port, aggregate function) of a group key or of an aggregate
        that rule 7a admits."""
        if type(owner) is aggregation.ProjectSQLGroupKey:
            return self.key(owner), None
        function, port = self.aggregate(owner) or (None, None)
        return port, function

    def nodes(self) -> int:
        """Rule 16: the nodes of the SQL AST that the plan admits."""
        plan = self.plan
        arguments = sum(
            len(owner.arguments)
            for _, _, owner in self.outputs()
            if type(owner) is aggregation.ProjectSQLAggregate
        )
        return node_count(
            len(plan.exports), arguments, len(plan.group_keys), len(plan.filters)
        )


class _Rules:
    """Rules 1-29, with 7a and 7b keyed 7.1 and 7.2: at most one blocker per
    rule, at its first failing site."""

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
        plan = self.plan
        named = tuple(
            d
            for d in plan.bindings.definitions
            if type(d.entry.owner.definition) is not SourceDef
        )
        operators = tuple(
            tuple(o.kind.value for o in block.operators) for block in plan.blocks
        )
        if not (
            len(named) == 1
            and len(plan.sources) == 1
            and len(plan.input_uses) == 1
            and operators in _SHAPES
            and len(plan.filters)
            == sum(o in _FILTERS for block in operators for o in block)
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
                        definition.order_by_clause,
                        definition.limit_clause,
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
                5, "PIE-B1003", "duckdb_relation_shape_not_admitted", location=site
            )
        self.ordered = tuple(
            sorted(plan.sources, key=lambda s: _key(s.declaration.span))
        )
        if not self.ordered:
            self.fail(6, "PIE-B1003", "duckdb_source_count_not_admitted", at=True)
        elif len(self.ordered) > 1:
            second = self.ordered[1]
            self.fail(
                6,
                "PIE-B1003",
                "duckdb_source_count_not_admitted",
                second.ref,
                second.declaration.span,
            )

    def projections(self) -> None:
        plan, values = self.plan, self.values
        outputs = values.outputs()
        for export, (projection, port, owner) in zip(
            plan.exports, outputs, strict=True
        ):
            if port is None and type(owner) is not aggregation.ProjectSQLAggregate:
                self.fail(
                    7,
                    "PIE-B1003",
                    "duckdb_projection_not_admitted",
                    export.ref if projection is None else projection.ref,
                    self.statement
                    if projection is None
                    else projection.site.occurrence.span
                    if type(projection) is plans.ProjectSQLProjection
                    else projection.semantic.item.span,
                )
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
            predicate = plan.expressions[filter_.predicate.position]
            if not (
                type(filter_.site) is aggregation.ProjectSQLAggregateSite
                and self.having(predicate, selected)
                if filter_.site.role.value == "satisfying"
                else not position and self.comparison(predicate)
            ):
                self.fail(
                    8,
                    "PIE-B1003",
                    "duckdb_filter_not_admitted",
                    filter_.ref,
                    filter_.site.occurrence.span,
                )

    def site(self, item: Any) -> Any:
        """The call of an aggregate, or the item of a group key."""
        node = getattr(item.source, "call", None) or getattr(item.source, "item", None)
        return getattr(node, "span", None) or self.statement

    def comparison(self, predicate: Any) -> bool:
        if (
            type(predicate) is not ProjectSQLComparison
            or predicate.expression.operator not in OPERATORS
        ):
            return False
        left = self.values.direct(self.plan.expressions[predicate.left.position])
        right = self.plan.expressions[predicate.right.position]
        return (
            left is not None
            and _type_name(left) == "Int"
            and type(right) is ProjectSQLParameterRead
        )

    def having(self, predicate: Any, selected: tuple[Any, ...]) -> bool:
        """One comparison of a direct read of an Int selected output, on the
        left, with a direct read of the parameter."""
        if (
            type(predicate) is not ProjectSQLComparison
            or predicate.expression.operator not in OPERATORS
        ):
            return False
        left = self.plan.expressions[predicate.left.position]
        right = self.plan.expressions[predicate.right.position]
        if type(left) is not aggregation.ProjectSQLResultReference:
            return False
        owner = self.values.owners.get(left.port)
        logical = _logical(left.value_type)
        return (
            owner is not None
            and any(owner is item for item in selected)
            and logical is not None
            and logical[0] == "Int"
            and type(right) is ProjectSQLParameterRead
        )

    def parameters(self) -> None:
        plan, header = self.plan, self.plan.parameters
        problem: tuple[object, object] | None = None
        if not plan.filters:
            if header:
                problem = (None, header[0].declaration.span)
        elif len(header) != 1:
            problem = (
                (None, header[1].declaration.span) if header else (None, self.statement)
            )
        elif header[0].tag != "Int" or header[0].value_type.nullability.value != (
            "non_null"
        ):
            problem = (None, header[0].declaration.span)
        else:
            predicates = tuple(
                plan.expressions[f.predicate.position] for f in plan.filters
            )
            if (
                len(self.reads) != 1
                or not any(
                    type(predicate) is ProjectSQLComparison
                    and any(
                        plan.expressions[side.position] is self.reads[0]
                        for side in (predicate.left, predicate.right)
                    )
                    for predicate in predicates
                )
                or any(a.parameter is not None for a in plan.window_arguments)
            ):
                problem = (None, self.statement)
        if problem is not None:
            self.fail(9, "PIE-B1003", "duckdb_parameter_not_admitted", *problem)
        for source in sorted(plan.sources, key=lambda s: _key(s.declaration.span)):
            for port in _ports(plan, source):
                if _type_name(port) is None:
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
            (13, "operator_environment", bool(plan.filters)),
            (14, "parameter_protocol", bool(self.reads)),
        ):
            found = [p for p in statement if p.key == key]
            if needed and not found:
                self.fail(rule, "PIE-B1004", key + "_declaration_missing", at=True)
            elif needed and json.loads(found[0].value) != PREMISES[key]:
                self.fail(rule, "PIE-B1005", key + "_declaration_mismatch", at=True)
        window_reads = sum(a.parameter is not None for a in plan.window_arguments)
        if len(self.reads) + window_reads > limits["parameters"]:
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
            if not _fits(_type_name(port), field.representation):
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
    """The statement the plan admits, read from the source ports, group keys
    and aggregates that its values read."""
    (source,) = plan.sources
    index = {port.ref: k for k, port in enumerate(_ports(plan, source))}
    values = _Values(plan)

    def field(port: Any) -> int | None:
        return None if port is None else index[port.ref]

    columns = []
    for export, (_, port, owner) in zip(plan.exports, values.outputs(), strict=True):
        function = None
        if type(owner) is aggregation.ProjectSQLAggregate:
            port, function = values.value(owner)
        columns.append(DuckDBColumn(field(port), export.identity.name, function))
    where = having = None
    for filter_ in plan.filters:
        predicate = plan.expressions[filter_.predicate.position]
        operator = OPERATORS[predicate.expression.operator]
        left = plan.expressions[predicate.left.position]
        if filter_.site.role.value == "where":
            where = DuckDBComparison(index[values.direct(left).ref], operator, 1)
        else:
            port, function = values.value(values.owners[left.port])
            having = DuckDBHaving(field(port), function, operator, 1)
    group_by = tuple(index[values.key(key).ref] for key in plan.group_keys)
    return DuckDBSelect(RELATION, tuple(columns), where, group_by, having)


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


def _subjects(
    plan: Any, outputs: tuple[tuple[Any, Any, Any], ...]
) -> dict[tuple[object, ...], Any]:
    """The plan owner of each symbolic token subject, given the plan's
    `_Values` outputs."""
    (source,) = plan.sources
    result: dict[tuple[object, ...], Any] = {
        ("statement",): plan.scope,
        ("source",): source.ref,
    }
    for position, (export, (projection, _, owner)) in enumerate(
        zip(plan.exports, outputs, strict=True)
    ):
        result["projection", position] = projection.ref
        result["export", position] = export.ref
        if type(owner) is aggregation.ProjectSQLAggregate:
            result["aggregate", position] = owner.ref
            if owner.arguments:
                result["argument", position] = owner.arguments[0]
    for aggregation_ in plan.aggregations:
        result["aggregation",] = aggregation_.ref
    for position, key in enumerate(plan.group_keys):
        result["group_key", position] = key.ref
    for filter_ in plan.filters:
        predicate = plan.expressions[filter_.predicate.position]
        names = (
            ("filter", "predicate", "left", "read")
            if filter_.site.role.value == "where"
            else ("having", "having_predicate", "having_left", "having_read")
        )
        refs = (filter_.ref, predicate.ref, predicate.left, predicate.right)
        for name, ref in zip(names, refs, strict=True):
            result[name,] = ref
    return result


def _document(artifact: DuckDBArtifact) -> bytes:
    checked, plan = artifact.checked, artifact.checked.plan
    semantic, owner = checked.completed.semantic_result, checked.selected_owner
    contract = json.loads(artifact.contract.normalized)
    (source,) = plan.sources
    ports = _ports(plan, source)
    (entry,) = (s for s in artifact.contract.sources if s.owner is source.source.owner)
    fields = {f.ordinal: f for f in entry.fields}
    outputs = _Values(plan).outputs()
    subjects = _subjects(plan, outputs)
    indexes = artifact.source_map.indexes
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
        read = None if column.field is None else ports[column.field]
        correspondence: dict[str, Any] = {
            "source": entry.selector,
            "field": column.field,
            "source_port": None if read is None else _ref(read.ref),
        }
        k, logical = column.field, None
        if column.function is not None:
            correspondence["aggregate"] = _ref(item.ref)
            correspondence["function"] = column.function
            logical = _logical(item.value_type)
        elif item is not None:
            correspondence["group_key"] = _ref(item.ref)
        if column.function in ("count", "sum") or k is None:
            # A count or a sum is a signed 64-bit Int, a count never negative.
            name, nullable = logical or (None, None)
            least = "0" if column.function == "count" else str(-(2**63))
            representation = {
                "storage": {"kind": "arrow_int64"},
                "domain": {"kind": "int_range", "min": least, "max": str(2**63 - 1)},
                "nullable": nullable,
            }
        else:
            # A read, or a min or max, which keeps its field's type and domain.
            representation = fields[k].representation
            name, nullable = _type_name(ports[k]), representation["nullable"]
            if column.function is not None:
                name, nullable = logical or (None, None)
                representation = representation | {"nullable": nullable}
        input_port = (
            projection.input_port
            if type(projection) is plans.ProjectSQLProjection
            else projection.input
        )
        columns.append(
            {
                "ordinal": position,
                "label": column.label,
                "logical_type": {"kind": "builtin", "name": name, "parameters": None},
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
                "owner": {"kind": "parameter", "parameter": 0},
                "server_index": 1,
                "physical_type": "duckdb_bigint",
                "range": {"start": token.start, "end": token.end},
            }
            for i, token in enumerate(placeholders)
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
                "reads": [_ref(subjects[t.subject]) for t in placeholders],
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
        (source,) = plan.sources
        if (
            type(plan) is not plans.ProjectSQLPlan
            or artifact.ast != _expected_ast(plan)
            or not ast_rules_hold(
                artifact.ast, len(_ports(plan, source)), _labels(plan)
            )
            or artifact.ast.nodes != _Values(plan).nodes()
            or render(artifact.ast) != (artifact.sql, artifact.tokens)
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
        not ast_rules_hold(ast, len(_ports(plan, plan.sources[0])), _labels(plan))
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
    `Int`, `max_characters` of a `Text`)."""

    column: str
    tag: str
    nullable: bool
    bounds: tuple[int, int] | None
    max_characters: int | None


@dataclass(frozen=True, slots=True)
class DuckDBExecutionFacts:
    """What the `duckdb_arrow` route reads of one verified artifact: the
    contract's `relation.name`, the rendered statement, the source fields,
    each result column's (label, logical type, nullable) in result order and
    the header parameters as (name, tag, nullable)."""

    key: str
    sql: str
    fields: tuple[DuckDBSourceField, ...]
    result: tuple[tuple[str, str, bool], ...]
    parameters: tuple[tuple[str, str, bool], ...]


def execution_facts(template: object) -> DuckDBExecutionFacts:
    """The facts of a live template whose artifact verifies afresh; any other
    value is BINDING_ARTIFACT. Each result column has the logical type and
    nullability of its verified document's column: a read's are its source
    field's, an aggregate's its result's (rules 7 and 7a)."""
    if type(template) is not DuckDBTemplate or not verify_artifact(template.emission):
        raise ValueError("BINDING_ARTIFACT")
    artifact = template.emission
    plan = artifact.checked.plan
    (source,) = plan.sources
    ports = _ports(plan, source)
    (entry,) = (s for s in artifact.contract.sources if s.owner is source.source.owner)
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
            )
        )
    result = tuple(
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in json.loads(artifact.document)["columns"]
    )
    if any(
        tag not in TYPES or type(nullable) is not bool for _, tag, nullable in result
    ):
        raise ValueError("BINDING_ARTIFACT")
    return DuckDBExecutionFacts(
        entry.name,
        artifact.sql.decode("utf-8"),
        tuple(fields),
        result,
        template.facts()[7],
    )
