"""Independent closed-graph checks before compiled authority construction."""

from collections import Counter
from typing import Any, cast

from pietto._project.project_verification_scope import once
from pietto._project.project_compiled_schema import (
    BLOCK_READ_OPERATORS,
    captured_logical,
    captured_reads,
    executed_operations,
    scalar_read_port,
    Address,
    CompiledError,
    Description,
    FIELDS,
    MAX_EDGES,
    MAX_RECORDS,
    MAX_FIELDS,
    MAX_EXPRESSION_DEPTH,
    MEMBERS,
    Record,
    Scalar,
    VERSIONS,
    declaration_values,
    row_bindings,
    scalar_wire,
    selected_relations,
    unit_captured_reads,
    unit_position,
)

__all__: tuple[str, ...] = ()

MEMBER_KINDS = {
    "structure": frozenset(FIELDS)
    - {
        "slot",
        "native_use",
        "parameter",
        "target",
        "premise",
        "policy",
        "request",
        "provider",
        "requirement_origin",
        "requirement",
        "requirement_link",
        "output",
    },
    "parameters": frozenset({"slot", "native_use", "parameter"}),
    "targets": frozenset({"target", "premise"}),
    "obligations": frozenset(
        {
            "policy",
            "request",
            "provider",
            "requirement_origin",
            "requirement",
            "requirement_link",
        }
    ),
    "outputs": frozenset({"output"}),
}
RELATIONS = frozenset(
    {"source", "scan", "row", "join", "aggregate", "window", "result", "set", "values"}
)
VALUES_LOGICAL = tuple(
    (tag, nullability)
    for tag in ("Int", "Bool", "Float", "Text")
    for nullability in ("non_null", "nullable")
)
VALUES = frozenset(
    {
        "literal",
        "null_literal",
        "parameter_read",
        "read",
        "operation",
        "aggregate_value",
        "window_value",
        "set_value",
        "join_value",
    }
)
ROLES = frozenset(
    {
        "select",
        "let",
        "where",
        "on",
        "aggregate_argument",
        "satisfying",
        "qualify",
        "window_argument",
        "window_partition",
        "window_order",
        "frame",
        "relation_order",
        "limit",
        "connector",
        "type_argument",
        "unknown",
    }
)


def _physical_fields(fields):
    """A premise's expression context reads physical source fields only; a
    VALUES column has no source premise."""
    return all(
        type(f.get("source")) is Address and f.get("source").kind == "source"
        for f in fields
    )


def need(condition, category):
    if not condition:
        raise CompiledError("COMPILED_" + category)


def _references(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is Address:
            yield item
        elif type(item) is tuple:
            pending.extend(reversed(item))
        elif type(item) is Scalar:
            scalar_wire(item)
        else:
            need(type(item) in (type(None), bool, int, str), "VALUE")


def verify_description(value: Description) -> None:
    need(type(value) is Description, "DESCRIPTION")
    need(
        type(value.compatibility) is tuple and len(value.compatibility) == 5,
        "COMPATIBILITY",
    )
    need(
        value.compatibility[:4] == VERSIONS
        and all(type(v) is int for v in value.compatibility[:4]),
        "COMPATIBILITY",
    )
    need(
        type(value.compatibility[4]) is str and len(value.compatibility[4]) == 64,
        "COMPATIBILITY",
    )
    need(
        type(value.producer) is str and bool(value.producer),
        "PRODUCER",
    )
    need(type(value.members) is tuple and len(value.members) == len(MEMBERS), "MEMBERS")
    records: dict[Address, Record] = {}
    counts: Counter[str] = Counter()
    edges = 0
    for expected, member in zip(MEMBERS, value.members, strict=True):
        need(
            type(member) is tuple
            and len(member) == 2
            and member[0] == expected
            and type(member[1]) is tuple,
            "MEMBERS",
        )
        for record in member[1]:
            need(type(record) is Record and type(record.address) is Address, "RECORD")
            address = record.address
            need(
                address.kind in MEMBER_KINDS[expected]
                and type(address.position) is int
                and address.position == counts[address.kind],
                "RECORD_ORDER",
            )
            need(
                address not in records and len(records) < MAX_RECORDS,
                "RECORD_INVENTORY",
            )
            need(
                type(record.values) is tuple
                and len(record.values) == len(FIELDS[address.kind]),
                "FIELDS",
            )
            records[address] = record
            counts[address.kind] += 1
            for _ in _references(record.values):
                edges += 1
                need(edges <= MAX_EDGES, "EDGE_LIMIT")
    need(
        type(value.query) is Address
        and value.query.kind == "entry"
        and counts["entry"] == 1
        and value.query in records,
        "QUERY",
    )
    need(
        counts["target"] == counts["policy"] == 1 and counts["output"] > 0,
        "REQUIRED_MEMBER",
    )

    def ref(item, kinds) -> Record:
        if type(item) is not Address or item.kind not in kinds or item not in records:
            raise CompiledError("COMPILED_REFERENCE")
        return records[item]

    def refs(items, kinds):
        need(type(items) is tuple, "REFERENCES")
        return tuple(ref(item, kinds) for item in items)

    for record in records.values():
        for address in _references(record.values):
            need(address in records, "MISSING_REFERENCE")
    target = records[Address("target", 0)]
    family, release, contract, profile = target.values
    from pietto._project.project_sql_emission_contract import RELEASES

    need(
        family in ("postgres", "mysql")
        and type(release) is str
        and type(contract) is str
        and RELEASES.get(family) == release,
        "TARGET",
    )
    need(
        profile == ("finite_pg_v1" if family == "postgres" else "finite_mysql_v1"),
        "PROFILE",
    )
    from pietto._project.project_compiled_schema import json_value

    contract_data = json_value(contract.encode("utf-8"))
    need(
        type(contract_data) is dict
        and set(contract_data) == {"format", "target", "sources", "environment"}
        and contract_data["format"] == "pietto.emission-contract.v1"
        and contract_data["target"] == {"family": family, "release": release}
        and type(contract_data["sources"]) is list
        and type(contract_data["environment"]) is list,
        "TARGET_CONTRACT",
    )
    entry = records[value.query]
    selected = ref(entry.get("declaration"), {"declaration"})
    # `compile_query` selects one module-level table or query, never a let.
    need(
        selected.get("let") is None
        and (selected.get("namespace"), selected.get("kind"))
        in (("relation", "table"), ("relation", "query")),
        "QUERY",
    )
    ref(entry.get("terminal"), RELATIONS)
    exports = refs(entry.get("exports"), {"port"})
    refs(entry.get("requests"), {"request"})
    refs(entry.get("retained"), RELATIONS - {"source"})
    need(len(exports) == counts["output"], "OUTPUT_INVENTORY")
    need(
        set(entry.get("requests")) == {a for a in records if a.kind == "request"},
        "REQUEST_INVENTORY",
    )
    execution = selected_relations(records, entry)
    slot_literals, slot_sites, parameter_labels = set(), set(), set()
    for record in records.values():
        kind, get = record.address.kind, record.get
        if kind in RELATIONS:
            field_refs = get("fields") if kind == "source" else get("outputs")
            need(
                type(field_refs) is tuple and len(field_refs) <= MAX_FIELDS,
                "FIELD_LIMIT",
            )
        if kind == "declaration":
            need(
                type(get("module")) is str
                and type(get("module_position")) is int
                and get("module_position") >= 0
                and get("namespace") in ("type", "relation", "callable")
                and type(get("position")) is int
                and get("position") >= 0,
                "DECLARATION",
            )
            need(
                get("kind")
                in (
                    "type",
                    "enum",
                    "shape",
                    "source",
                    "table",
                    "query",
                    "constraint",
                    "derive",
                )
                and type(get("label")) is str
                and bool(get("label")),
                "DECLARATION",
            )
            need(
                get("let") is None
                or (
                    type(get("let")) is int
                    and get("let") >= 0
                    and (get("namespace"), get("kind")) == ("relation", "query")
                ),
                "DECLARATION",
            )
        elif kind == "source":
            ref(get("declaration"), {"declaration"})
            need(
                get("family") in ("postgres", "mysql")
                and (record.address not in execution or get("family") == family),
                "SOURCE_FAMILY",
            )
            fields = refs(get("fields"), {"field"})
            need(
                bool(fields)
                and all(
                    f.get("source") == record.address and f.get("ordinal") == i
                    for i, f in enumerate(fields)
                ),
                "SOURCE_FIELDS",
            )
            need(
                (
                    get("namespace") is None
                    and get("name") is None
                    and record.address not in execution
                )
                or all(type(get(n)) is str and get(n) for n in ("namespace", "name")),
                "SOURCE",
            )
        elif kind == "expression_context":
            ref(get("owner"), {"declaration"})
            need(
                type(get("kind")) is str
                and type(get("block_kind")) is str
                and all(
                    type(get(n)) is int and get(n) >= 0
                    for n in ("position", "block_position")
                )
                and _physical_fields(refs(get("fields"), {"field"})),
                "EXPRESSION_CONTEXT",
            )
        elif kind == "premise":
            need(type(get("value")) is str, "PREMISE_VALUE")
            json_value(get("value").encode("utf-8"))
            from pietto._project.project_sql_emission_contract import (
                LOCAL_KEYS,
                STATEMENT_KEYS,
            )

            need(
                type(get("position")) is int
                and get("position") == record.address.position
                and get("key") in LOCAL_KEYS | STATEMENT_KEYS
                and type(get("value")) is str,
                "PREMISE",
            )
            scope = get("scope")
            if scope != "statement":
                if type(scope) is tuple:
                    need(len(scope) == 2, "PREMISE_SCOPE")
                    source = ref(scope[0], {"declaration"})
                    context = ref(scope[1], {"expression_context"})
                    fields = refs(context.get("fields"), {"field"})
                    need(
                        _physical_fields(fields)
                        and any(
                            records[f.get("source")].get("declaration")
                            == source.address
                            for f in fields
                        ),
                        "PREMISE_EXPRESSION_SOURCE",
                    )
                else:
                    source = ref(scope, {"declaration"})
                need(source.get("kind") == "source", "PREMISE_SOURCE")
            need(
                (get("key") in STATEMENT_KEYS) is (scope == "statement"),
                "PREMISE_DOMAIN",
            )
        elif kind == "source_unique":
            source = ref(get("source"), {"source"})
            shape = ref(get("shape"), {"declaration"})
            fields = refs(get("fields"), {"port"})
            need(
                shape.get("kind") == "shape"
                and type(get("position")) is int
                and get("position") >= 0
                and bool(fields)
                and len({f.address for f in fields}) == len(fields)
                and all(f.get("owner") == source.address for f in fields)
                and get("null_policy") == "nulls_distinct"
                and get("origin") == "authored_contract"
                and get("trust") == "trusted"
                and get("enforcement") == "model_contract",
                "SOURCE_UNIQUE",
            )
        elif kind == "field":
            holder = ref(get("source"), {"source", "values"})
            need(type(get("ordinal")) is int and get("ordinal") >= 0, "FIELD")
            need(type(get("label")) is str, "FIELD")
            physical_mapping = get("physical") is not None
            need(
                all(type(get(n)) is str for n in ("column", "physical"))
                if physical_mapping
                else get("column") is None and get("source") not in execution,
                "FIELD",
            )
            from pietto._project.project_sql_emission_contract import (
                _representation,
            )
            from pietto._project.project_sql_emission_ast import (
                resolved_representation_problem,
            )

            logical = get("logical")
            need(
                type(logical) is tuple
                and len(logical) == 2
                and logical[0]
                in ("Int", "Bool", "Float", "Text", "Decimal", "Timestamp", "UUID")
                and logical[1] in ("non_null", "nullable", "unknown"),
                "FIELD_LOGICAL",
            )
            decimal = get("decimal")
            if logical[0] == "Decimal":
                need(
                    type(decimal) is tuple
                    and len(decimal) == 2
                    and all(type(v) is int for v in decimal),
                    "FIELD_DECIMAL",
                )
            else:
                need(decimal is None, "FIELD_DECIMAL")
            need(
                get("meaning")
                == (logical[0] if logical[0] in ("Timestamp", "UUID") else None),
                "FIELD_MEANING",
            )

            if holder.address.kind == "values":
                # A VALUES column is no contract source field: its values record
                # re-derives its whole representation from the fixed cells.
                columns = holder.get("fields")
                need(
                    type(columns) is tuple and record.address in columns,
                    "VALUES_COLUMNS",
                )
                continue
            if not physical_mapping:
                continue
            physical = json_value(get("physical").encode("utf-8"))
            need(
                _representation(physical, "compiled/field", []), "FIELD_REPRESENTATION"
            )
            need(
                resolved_representation_problem(
                    logical[0],
                    {"non_null": False, "nullable": True, "unknown": "unknown"}[
                        cast(str, logical[1])
                    ],
                    physical,
                    family,
                    decimal,
                )
                is None,
                "FIELD_REPRESENTATION",
            )
        elif kind == "port":
            ref(get("owner"), RELATIONS)
            need(
                type(get("ordinal")) is int
                and get("ordinal") >= 0
                and type(get("label")) is str,
                "PORT",
            )
            ref(get("source"), VALUES | {"field", "port"})
        elif kind == "use":
            ref(get("consumer"), RELATIONS)
            ref(get("producer"), RELATIONS)
            need(type(get("ordinal")) is int and get("ordinal") >= 0, "USE")
            refs(get("ports"), {"port"})
        elif kind == "expression_block_use":
            operation = ref(get("operation"), {"operation"})
            consumer = ref(get("consumer"), RELATIONS - {"source"})
            producer = ref(get("producer"), RELATIONS)
            # An existence read has no column, a scalar read names one output
            # port of its producer, and a membership read compares with column
            # 0 of its single-column producer.
            need(
                operation.get("operator") in BLOCK_READ_OPERATORS
                and (
                    get("column") is None
                    if operation.get("operator") == ("exists", "exists")
                    else scalar_read_port(records, operation.address) is not None
                    if operation.get("operator") == ("scalar", "scalar")
                    else type(get("column")) is int
                    and get("column") == 0
                    and sum(
                        r.address.kind == "port" and r.get("owner") == producer.address
                        for r in records.values()
                    )
                    == 1
                )
                and get("producer") != consumer.address
                and operation.address in executed_operations(records, consumer.address),
                "EXPRESSION_BLOCK_USE",
            )
        elif kind == "capture_use":
            block = ref(get("read"), {"expression_block_use", "use"})
            ports = refs(get("ports"), {"port"})
            uses = tuple(
                r
                for r in records.values()
                if r.address.kind == "use"
                and r.get("consumer") == block.get("consumer")
            )
            if block.address.kind == "use":
                # LATERAL: the JOIN's right input executes the let and its
                # captured fields read the same JOIN's left input.
                need(
                    records[block.get("consumer")].address.kind == "join"
                    and block.get("ordinal") == 1,
                    "CAPTURE_USE",
                )
                # Only a CROSS, INNER or LEFT JOIN reads a let LATERAL, as at
                # the source (PIE-S2372): each pair extends a left row.
                need(
                    records[block.get("consumer")].get("kind")
                    in ("cross", "inner", "left"),
                    "LATERAL_JOIN_KIND",
                )
                uses = tuple(u for u in uses if u.get("ordinal") == 0)
            inner = records[block.get("producer")]
            need(
                type(get("ordinal")) is int
                and get("ordinal") >= 0
                and len(uses) == 1
                and len({p.address for p in ports}) == len(ports)
                and all(p.address in uses[0].get("ports") for p in ports)
                # The let's ORDER BY and LIMIT end it in a result unit.
                and inner.address.kind in ("row", "result")
                and unit_position(inner) is None,
                "CAPTURE_USE",
            )
            # MySQL reads a let's ORDER BY and LIMIT only LATERAL, never in a
            # scalar or IN read, as at emission (D70.05).
            need(
                family == "postgres"
                or block.address.kind == "use"
                or inner.address.kind == "row",
                "MYSQL_CORRELATED_ORDER",
            )
        elif kind == "literal":
            need(
                type(get("value")) is Scalar and get("value").tag == get("tag"),
                "LITERAL",
            )
            ref(get("site"), {"site"})
        elif kind == "null_literal":
            site = ref(get("site"), {"site"})
            need(site.get("disposition") == "preserved_with_reason", "STATIC_NULL")
        elif kind == "parameter":
            from pietto._project.query_parameters import MAX_QUERY_PARAMETERS

            # Only the entry query declares parameters, in header order, each
            # under its own source name: a binding by name never picks a winner.
            label = get("label")
            need(
                get("declaration") == entry.get("declaration")
                and type(get("ordinal")) is int
                and get("ordinal") == record.address.position < MAX_QUERY_PARAMETERS
                and type(label) is str
                and label.isascii()
                and label.isidentifier()
                and label not in parameter_labels
                and get("tag") in ("Bool", "Int", "Float", "Text")
                and type(get("nullable")) is bool,
                "PARAMETER",
            )
            parameter_labels.add(label)
        elif kind == "parameter_read":
            ref(get("parameter"), {"parameter"})
        elif kind == "read":
            port = ref(get("port"), {"port"})
            use = ref(get("use"), {"use"})
            need(
                port is not None
                and use is not None
                and port.address in use.get("ports"),
                "READ_USE",
            )
            need(port.get("owner") == use.get("producer"), "READ_PRODUCER")
            need(get("role") in ("value", "capture"), "READ_ROLE")
        elif kind == "site":
            ref(get("owner"), {"declaration"})
            need(
                get("role") in ROLES
                and type(get("ordinal")) is int
                and get("ordinal") >= 0,
                "SITE",
            )
            need(
                type(get("ancestry")) is tuple
                and get("disposition") in ("bound", "preserved_with_reason"),
                "SITE",
            )
        elif kind == "slot":
            site = ref(get("site"), {"site"})
            literal = ref(get("literal"), {"literal"})
            need(
                site is not None
                and literal is not None
                and literal.get("site") == site.address,
                "SLOT_SITE",
            )
            need(
                site.get("disposition") == "bound"
                and site.get("role") in ("select", "let", "where", "on")
                and site.get("reason") is None,
                "SLOT_ELIGIBILITY",
            )
            need(
                get("tag") == literal.get("tag")
                and get("tag") in ("Bool", "Int", "Float", "Text"),
                "SLOT_TAG",
            )
            need(
                site.address not in slot_sites and literal.address not in slot_literals,
                "SLOT_ALIAS",
            )
            slot_sites.add(site.address)
            slot_literals.add(literal.address)
        elif kind == "row":
            ref(get("owner"), {"declaration"})
            producer = ref(get("input"), RELATIONS)
            use = ref(get("use"), {"use"})
            values = refs(
                get("values"),
                {"literal", "null_literal", "parameter_read", "read", "operation"},
            )
            outputs = refs(get("outputs"), {"port"})
            need(
                get("stage") in ("let", "where", "satisfying", "qualify", "projection")
                and use.get("consumer") == record.address
                and use.get("producer") == producer.address
                and len(values) == len(outputs)
                and tuple(p.get("source") for p in outputs) == get("values"),
                "ROW_SHAPE",
            )
            if get("predicate") is not None:
                ref(
                    get("predicate"),
                    {"literal", "null_literal", "parameter_read", "read", "operation"},
                )
            need(
                (get("predicate") is not None)
                is (get("stage") in ("where", "satisfying", "qualify")),
                "ROW_PREDICATE",
            )
        elif kind == "result":
            from pietto.semantic.relation_limits import valid_resolved_limit

            ref(get("owner"), {"declaration"})
            producer = ref(get("input"), {"row"})
            need(
                producer.get("stage") == "projection"
                and producer.get("owner") == get("owner"),
                "RESULT_PROJECTION",
            )
            refs(get("projection"), {"read"})
            outputs = refs(get("outputs"), {"port"})
            need(
                tuple(p.get("source") for p in outputs) == get("projection")
                and type(get("distinct")) is bool
                and type(get("ordering")) is tuple,
                "RESULT_COLUMNS",
            )
            for item in get("ordering"):
                if (
                    type(item) is not tuple
                    or len(item) != 2
                    or item[1] not in ("asc", "desc")
                ):
                    raise CompiledError("COMPILED_RESULT_ORDER")
                ref(item[0], {"read"})
            limit = get("limit")
            if limit is None:
                need(get("limit_literal") is None, "RESULT_LIMIT")
            else:
                literal = ref(get("limit_literal"), {"literal"})
                site = records[literal.get("site")]
                need(
                    valid_resolved_limit(limit)
                    and literal.get("tag") == "Int"
                    and literal.get("value").value == limit
                    and site.get("role") == "limit"
                    and site.get("owner") == get("owner")
                    and site.get("disposition") == "preserved_with_reason",
                    "RESULT_LIMIT",
                )
            need(
                get("distinct") or bool(get("ordering")) or limit is not None,
                "RESULT_BOUNDARIES",
            )
        elif kind == "aggregate":
            need(
                get("risk_law") in (None, "current", "relationship"),
                "AGGREGATE_RISK_LAW",
            )
            joins_here = tuple(
                r
                for r in records.values()
                if r.address.kind == "join" and r.get("owner") == get("owner")
            )
            need(
                (get("risk_law") is None) is (not joins_here), "AGGREGATE_RISK_CLOSURE"
            )
            n = len(get("values"))
            need(
                n * (n - 1) // 2 + 3 * n + len(get("keys")) <= MAX_RECORDS,
                "AGGREGATE_EVIDENCE_EXPANSION",
            )
            ref(get("owner"), {"declaration"})
            producer = ref(get("input"), RELATIONS)
            use = ref(get("use"), {"use"})
            keys = refs(get("keys"), {"read"})
            values = refs(get("values"), {"aggregate_value"})
            outputs = refs(get("outputs"), {"port"})
            need(
                get("mode") in ("grouped", "global")
                and bool(keys) is (get("mode") == "grouped"),
                "AGGREGATE_MODE",
            )
            need(
                use.get("consumer") == record.address
                and use.get("producer") == producer.address,
                "AGGREGATE_INPUT",
            )
            need(
                tuple(p.get("source") for p in outputs) == get("keys") + get("values"),
                "AGGREGATE_OUTPUTS",
            )
            need(
                all(
                    p.get("owner") == record.address and p.get("ordinal") == i
                    for i, p in enumerate(outputs)
                ),
                "AGGREGATE_PORTS",
            )
            reads = (*keys, *(records[a] for v in values for a in v.get("arguments")))
            need(all(r.get("use") == use.address for r in reads), "AGGREGATE_SCOPE")
        elif kind == "aggregate_value":
            arguments = refs(get("arguments"), {"read"})
            need(
                get("function")
                in ("count", "count_distinct", "sum", "avg", "min", "max")
                and len(arguments) <= 1
                and (bool(arguments) or get("function") == "count"),
                "AGGREGATE_SIGNATURE",
            )
        elif kind == "join":
            ref(get("owner"), {"declaration"})
            need(
                get("kind")
                in ("cross", "inner", "left", "right", "full", "semi", "anti"),
                "JOIN_KIND",
            )
            uses = refs(get("inputs"), {"use"})
            need(
                get("law") in ("relationship", "current")
                and type(get("source_positions")) is tuple,
                "JOIN_LAW",
            )
            need(
                len(uses) == 2
                and all(
                    u.get("consumer") == record.address and u.get("ordinal") == i
                    for i, u in enumerate(uses)
                ),
                "JOIN_INPUTS",
            )
            positions = get("source_positions")
            need(
                all(
                    type(i) is int and 0 <= i < len(uses[0].get("ports"))
                    for i in positions
                )
                and tuple(sorted(set(positions))) == positions,
                "JOIN_SOURCE_POSITIONS",
            )
            equalities = refs(get("equalities"), {"join_equality"})
            need(
                get("law") != "relationship"
                or (
                    get("kind") in ("inner", "left")
                    and bool(positions)
                    and bool(equalities)
                ),
                "JOIN_RELATIONSHIP_LAW",
            )
            for equality in equalities:
                need(
                    equality.get("owner") == record.address
                    and records[equality.get("left")].get("use") == uses[0].address
                    and records[equality.get("right")].get("use") == uses[1].address,
                    "JOIN_EQUALITY_SCOPE",
                )
            predicate = get("predicate")
            if predicate is not None:
                ref(
                    predicate,
                    {"read", "operation", "literal", "null_literal", "parameter_read"},
                )
            need(
                (get("kind") == "cross") is (not equalities and predicate is None),
                "JOIN_CONDITION",
            )
            outputs = refs(get("outputs"), {"port"})
            expected = tuple(
                (u.address, a)
                for u in (uses[:1] if get("kind") in ("semi", "anti") else uses)
                for a in u.get("ports")
            )
            need(len(outputs) == len(expected), "JOIN_OUTPUTS")
            for index, (port, pair) in enumerate(zip(outputs, expected, strict=True)):
                column_value = ref(port.get("source"), {"join_value"})
                read = ref(column_value.get("input"), {"read"})
                need(
                    port.get("owner") == record.address
                    and port.get("ordinal") == index
                    and column_value.get("owner") == record.address
                    and (read.get("use"), read.get("port")) == pair,
                    "JOIN_OUTPUT_PORT",
                )
        elif kind == "join_value":
            ref(get("owner"), {"join"})
            ref(get("input"), {"read"})
        elif kind == "join_equality":
            ref(get("owner"), {"join"})
            ref(get("left"), {"read"})
            ref(get("right"), {"read"})
        elif kind == "set":
            ref(get("owner"), {"declaration"})
            need(
                get("kind") in ("union", "intersect", "except")
                and get("quantifier") in ("all", "distinct"),
                "SET_KIND",
            )
            uses = refs(get("operands"), {"use"})
            outputs = refs(get("outputs"), {"port"})
            need(
                len(uses) >= 2
                and bool(outputs)
                and all(
                    u.get("consumer") == record.address
                    and u.get("ordinal") == i
                    and len(u.get("ports")) == len(outputs)
                    for i, u in enumerate(uses)
                ),
                "SET_OPERANDS",
            )
            for index, port in enumerate(outputs):
                column_value = ref(port.get("source"), {"set_value"})
                reads = refs(column_value.get("inputs"), {"read"})
                need(
                    port.get("owner") == record.address
                    and port.get("ordinal") == index
                    and column_value.get("owner") == record.address
                    and len(reads) == len(uses)
                    and all(
                        r.get("use") == u.address
                        and r.get("port") == u.get("ports")[index]
                        for r, u in zip(reads, uses, strict=True)
                    ),
                    "SET_POSITIONAL_INPUTS",
                )
        elif kind == "set_value":
            ref(get("owner"), {"set"})
            need(len(refs(get("inputs"), {"read"})) >= 2, "SET_INPUTS")
        elif kind == "values":
            ref(get("owner"), {"declaration"})
            fields = refs(get("fields"), {"field"})
            outputs = refs(get("outputs"), {"port"})
            rows = get("rows")
            need(
                bool(fields)
                and len(fields) == len(outputs) <= 64
                and all(
                    f.get("source") == record.address
                    and f.get("ordinal") == i
                    and f.get("column") == f"c{i}"
                    and type(f.get("physical")) is str
                    and f.get("decimal") is None
                    and f.get("meaning") is None
                    and f.get("logical") in VALUES_LOGICAL
                    and p.get("owner") == record.address
                    and p.get("ordinal") == i
                    and p.get("source") == f.address
                    and p.get("logical") == f.get("logical")
                    for i, (f, p) in enumerate(zip(fields, outputs, strict=True))
                ),
                "VALUES_COLUMNS",
            )
            need(
                type(rows) is tuple
                and len(rows) <= 1000
                and all(
                    type(row) is tuple
                    and len(row) == len(fields)
                    and all(
                        (cell is None and f.get("logical")[1] == "nullable")
                        or (type(cell) is Scalar and cell.tag == f.get("logical")[0])
                        for cell, f in zip(row, fields, strict=True)
                    )
                    for row in rows
                ),
                "VALUES_ROWS",
            )
            from pietto._project.project_sql_emission_contract import canonical
            from pietto._project.project_sql_emission_verification import (
                _values_column_realization,
            )

            # Each column's carrier, nullability and domain are what its cells
            # give on this target, never the producer's claim.
            for i, f in enumerate(fields):
                tag, nullability = f.get("logical")
                try:
                    _, derived = _values_column_realization(
                        tag,
                        nullability == "nullable",
                        tuple(None if row[i] is None else row[i].value for row in rows),
                        family,
                    )
                except ValueError:
                    derived = None
                need(
                    derived is not None
                    and f.get("physical")
                    == canonical(
                        {
                            "storage": derived.storage,
                            "nullable": derived.nullable,
                            "domain": derived.domain,
                        }
                    ).decode("utf-8"),
                    "VALUES_REPRESENTATION",
                )
            layout = get("layout")
            need(
                type(layout) is tuple
                and len(layout) == 5
                and (layout[0] is None or type(layout[0]) is str)
                and type(layout[1]) is tuple
                and all(type(name) is str for name in layout[1])
                and type(layout[2]) is str
                and type(layout[3]) is bool
                and type(layout[4]) is int,
                "VALUES_LAYOUT",
            )
        elif kind == "window":
            ref(get("owner"), {"declaration"})
            ref(get("input"), RELATIONS)
            use = ref(get("use"), {"use"})
            need(
                use.get("consumer") == record.address
                and use.get("producer") == get("input"),
                "WINDOW_INPUT",
            )
            definitions = refs(get("definitions"), {"window_definition"})
            values = refs(get("values"), {"read", "window_value"})
            outputs = refs(get("outputs"), {"port"})
            need(
                tuple(p.get("source") for p in outputs) == get("values")
                and tuple(d.get("ordinal") for d in definitions)
                == tuple(range(len(definitions))),
                "WINDOW_INVENTORY",
            )
            for window_value in values:
                if window_value.address.kind == "read":
                    need(window_value.get("use") == use.address, "WINDOW_CARRY")
                else:
                    need(
                        window_value.get("inputs") == use.get("ports"), "WINDOW_INPUTS"
                    )
                    spec = records[window_value.get("specification")]
                    reads = (
                        *spec.get("partition"),
                        *(a for a, _, _ in spec.get("ordering")),
                        *(
                            a
                            for role, a in window_value.get("arguments")
                            if role == "value" and a.kind == "read"
                        ),
                    )
                    need(
                        all(records[a].get("use") == use.address for a in reads),
                        "WINDOW_SCOPE",
                    )
        elif kind == "window_value":
            from pietto._project.project_sql_emission_windows import resolved_arguments

            refs(get("inputs"), {"port"})
            ref(get("specification"), {"window_spec"})
            need(
                type(get("selected")) is bool and type(get("arguments")) is tuple,
                "WINDOW_VALUE",
            )
            for argument in get("arguments"):
                need(type(argument) is tuple and len(argument) == 2, "WINDOW_ARGUMENT")
                ref(argument[1], {"read", "literal", "null_literal", "parameter_read"})
            resolved_arguments(get("function"), get("arguments"), records, family)
        elif kind == "window_spec":
            refs(get("partition"), {"read"})
            need(
                type(get("ordering")) is tuple and bool(get("ordering")), "WINDOW_ORDER"
            )
            for item in get("ordering"):
                need(
                    type(item) is tuple
                    and len(item) == 3
                    and item[1] in ("asc", "desc")
                    and item[2] is None,
                    "WINDOW_ORDER_ITEM",
                )
                ref(item[0], {"read"})
            if get("named") is not None:
                ref(get("named"), {"window_definition"})
            frame = get("frame")
            if frame is not None:
                need(type(frame) is tuple and len(frame) == 4, "WINDOW_FRAME")
                for bound in frame[1:3]:
                    if type(bound) is not tuple or len(bound) != 2:
                        raise CompiledError("COMPILED_WINDOW_FRAME_BOUND")
                    if bound[1] is not None:
                        ref(bound[1], {"literal"})
        elif kind == "window_definition":
            spec = ref(get("specification"), {"window_spec"})
            need(
                type(get("ordinal")) is int
                and get("ordinal") >= 0
                and type(get("label")) is str
                and bool(get("label"))
                and spec.get("named") is None,
                "WINDOW_DEFINITION",
            )
        elif kind == "native_use":
            ref(get("slot"), {"slot", "parameter_read"})
            need(
                type(get("ordinal")) is int
                and get("ordinal") == record.address.position
                and type(get("index")) is int
                and get("index") > 0,
                "NATIVE_USE",
            )
        elif kind == "match_step":
            need(
                type(get("module")) is str
                and all(
                    type(get(n)) is int and get(n) >= 0
                    for n in ("ordinal", "module_position", "position")
                )
                and type(get("source")) is int
                and type(get("target")) is int
                and {get("source"), get("target")} == {0, 1},
                "MATCH_STEP",
            )
        elif kind == "match_path":
            steps = refs(get("steps"), {"match_step"})
            need(
                bool(steps)
                and len({s.address for s in steps}) == len(steps)
                and tuple(s.get("ordinal") for s in steps) == tuple(range(len(steps))),
                "MATCH_PATH",
            )
        elif kind == "match_use":
            owner = ref(get("owner"), {"declaration"})
            boundaries = refs(get("boundaries"), {"join"})
            need(
                bool(boundaries)
                and type(get("position")) is int
                and get("position") >= 0
                and all(b.get("owner") == owner.address for b in boundaries),
                "MATCH_USE",
            )
            if get("path") is not None:
                path = ref(get("path"), {"match_path"})
                need(len(path.get("steps")) == len(boundaries), "MATCH_PATH_BOUNDARIES")
        elif kind == "request":
            owner = ref(get("owner"), {"declaration"})
            use = ref(get("use"), {"match_use"})
            need(
                use.get("owner") == owner.address
                and get("scope") in ("direct_binary", "whole_path", "path_hop")
                and get("unit") == "actual_matched_bag_occurrence",
                "REQUEST_KIND",
            )
            boundaries = use.get("boundaries")
            if get("scope") == "direct_binary":
                need(
                    len(boundaries) == 1 and get("path") is None and get("hop") is None,
                    "REQUEST_DIRECT",
                )
            elif get("scope") == "whole_path":
                need(
                    get("path") is not None
                    and get("path") == use.get("path")
                    and get("hop") is None,
                    "REQUEST_PATH",
                )
            else:
                hop = get("hop")
                if (
                    type(hop) is not tuple
                    or len(hop) != 2
                    or type(hop[1]) is not int
                    or not 0 <= hop[1] < len(boundaries)
                ):
                    raise CompiledError("COMPILED_REQUEST_HOP")
                need(
                    hop[0] in ("path_step", "traversal_step")
                    and (get("path") is None or get("path") == use.get("path"))
                    and (hop[0] != "path_step" or get("path") is not None),
                    "REQUEST_HOP",
                )
                boundaries = (boundaries[hop[1]],)
            need(
                all(records[a].get("kind") != "cross" for a in boundaries),
                "REQUEST_CROSS",
            )
            need(
                get("pairs") == tuple(records[a].get("inputs") for a in boundaries),
                "REQUEST_PAIRS",
            )
        elif kind == "provider":
            ref(get("source"), {"source"})
            need(
                all(
                    type(get(key)) is str and bool(get(key)) and "\0" not in get(key)
                    for key in (
                        "provider",
                        "version",
                        "revision",
                        "definition",
                        "role",
                        "guarantee",
                    )
                ),
                "PROVIDER_TEXT",
            )
            registry, tokens = get("registry"), get("tokens")
            need(
                type(registry) is tuple
                and len(registry) == 2
                and type(tokens) is tuple
                and 0 < len(tokens) <= 16
                and len(set(tokens)) == len(tokens),
                "PROVIDER_FIELDS",
            )
            from pietto._project.project_execution_source import identifier

            for label in (*registry, *tokens):
                if type(label) is not str:
                    raise CompiledError("COMPILED_PROVIDER_IDENTIFIER")
                identifier(label, family=target.get("family"))
        elif kind == "output":
            need(
                type(get("ordinal")) is int
                and get("ordinal") == record.address.position,
                "OUTPUT",
            )
            port = ref(get("port"), {"port"})
            need(
                port is exports[record.address.position]
                and get("label") == port.get("label"),
                "OUTPUT_PORT",
            )
    need(
        slot_sites
        == {
            r.address
            for r in records.values()
            if r.address.kind == "site" and r.get("disposition") == "bound"
        },
        "SLOT_INVENTORY",
    )
    for record in records.values():
        if record.address.kind == "operation":
            operator = record.get("operator")
            need(type(operator) is tuple and len(operator) == 2, "OPERATOR")
            role, token = operator
            if type(role) is not str or type(token) is not str:
                raise CompiledError("COMPILED_OPERATOR")
            allowed = {
                "unary": ({"+", "-"}, 1),
                "not": ({"not"}, 1),
                "binary": ({"+", "-", "*", "and", "or"}, 2),
                "comparison": (
                    {"==", "!=", "<", "<=", ">", ">=", "like", "not like"},
                    2,
                ),
                "null_test": ({"is_null", "is_not_null"}, 1),
                "between": ({"between"}, 3),
                "conditional": ({"if_else"}, 3),
                "membership": ({"in", "not_in"}, None),
                "cast": ({"int_to_float"}, 1),
                "exists": ({"exists"}, 0),
                "scalar": ({"scalar"}, 0),
                "relation_membership": ({"in", "not_in"}, 1),
                "scalar_call": (
                    {
                        "lower",
                        "upper",
                        "trim",
                        "len",
                        "substr",
                        "replace",
                        "contains",
                        "starts_with",
                        "ends_with",
                        "coalesce",
                        "nullif",
                        "abs",
                        "sign",
                        "date_of",
                        "year",
                        "month",
                        "day",
                        "hour",
                        "minute",
                    },
                    None,
                ),
            }
            need(
                type(role) is str
                and role in allowed
                and type(token) is str
                and token in allowed[role][0],
                "OPERATOR",
            )
            expected_arity = allowed[role][1]
            operands = record.get("operands")
            need(
                type(operands) is tuple
                and (expected_arity is None or len(operands) == expected_arity)
                and (role != "membership" or len(operands) >= 1)
                and (role != "scalar_call" or len(operands) >= 1),
                "OPERATOR_ARITY",
            )
            refs(
                operands,
                {"literal", "null_literal", "parameter_read", "read", "operation"},
            )
            if (role, token) in BLOCK_READ_OPERATORS:
                # Exactly one expression block use names each block read.
                need(
                    sum(
                        r.address.kind == "expression_block_use"
                        and r.get("operation") == record.address
                        for r in records.values()
                    )
                    == 1,
                    "EXPRESSION_BLOCK_USE_INVENTORY",
                )
    bound_literals = {
        r.get("literal"): records[r.get("site")]
        for r in records.values()
        if r.address.kind == "slot"
    }
    located_slots = set()
    execution_relations = selected_relations(records, entry)
    for relation in records.values():
        if relation.address not in execution_relations:
            continue
        roots = []
        if relation.address.kind == "row":
            role = (
                "select"
                if relation.get("stage") == "projection"
                else relation.get("stage")
            )
            roots.extend((a, role) for a in relation.get("values"))
            if relation.get("predicate") is not None:
                roots.append((relation.get("predicate"), relation.get("stage")))
        elif relation.address.kind == "join" and relation.get("predicate") is not None:
            roots.append((relation.get("predicate"), "on"))
        for root, role in roots:
            pending: list[tuple[Address, tuple[tuple[str, int], ...]]] = [(root, ())]
            visits = 0
            while pending:
                address, ancestry = pending.pop()
                visits += 1
                need(visits <= MAX_RECORDS, "LITERAL_ANCESTRY_EXPANSION")
                current = records[address]
                if address.kind == "operation":
                    parent = current.get("operator")[0]
                    pending.extend(
                        (a, (*ancestry, (parent, i)))
                        for i, a in reversed(tuple(enumerate(current.get("operands"))))
                    )
                elif address in bound_literals:
                    site = bound_literals[address]
                    need(
                        site.get("owner") == relation.get("owner")
                        and site.get("role") == role
                        and site.get("ancestry") == ancestry,
                        "SLOT_ANCESTRY",
                    )
                    located_slots.add(address)
    need(located_slots == set(bound_literals), "SLOT_EXECUTION_CLOSURE")

    # Ref depth and repeated scalar expansion are bounded before constructing
    # dialect trees; a compact DAG cannot allocate an exponential tree.
    costs, depths, active_values = {}, {}, set()
    for address in records:
        if address.kind not in (
            "literal",
            "null_literal",
            "parameter_read",
            "read",
            "operation",
        ):
            continue
        stack = [(address, False)]
        while stack:
            current, returning = stack.pop()
            if current in costs:
                continue
            record = records[current]
            children = record.get("operands") if current.kind == "operation" else ()
            if not returning:
                need(current not in active_values, "EXPRESSION_CYCLE")
                active_values.add(current)
                stack.append((current, True))
                stack.extend((child, False) for child in reversed(children))
                continue
            active_values.remove(current)
            costs[current] = (
                2
                if current.kind in ("literal", "null_literal", "parameter_read")
                else 1
            ) + sum(costs[c] for c in children)
            depths[current] = 1 + max((depths[c] for c in children), default=0)
            need(
                costs[current] <= MAX_RECORDS
                and depths[current] <= MAX_EXPRESSION_DEPTH,
                "EXPRESSION_EXPANSION",
            )
    roots = []
    for record in records.values():
        kind = record.address.kind
        if kind == "row":
            roots.extend(record.get("values"))
        if kind in ("row", "join") and record.get("predicate") is not None:
            roots.append(record.get("predicate"))
        if kind == "aggregate_value":
            roots.extend(record.get("arguments"))
    need(sum(costs[a] for a in roots) <= MAX_RECORDS, "EXPRESSION_EXPANSION")
    policy = records[Address("policy", 0)]
    need(
        policy.get("literal_policy") in ("preserve_literals", "bind_safe_literals"),
        "LITERAL_POLICY",
    )
    need(type(policy.get("guarded")) is bool, "POLICY")
    need(
        policy.get("refinement") in (None, "structural_occurrence_ascending"), "POLICY"
    )
    providers = refs(policy.get("sources"), {"provider"})
    need(
        tuple(p.address for p in providers)
        == tuple(a for a in records if a.kind == "provider"),
        "PROVIDER_INVENTORY",
    )
    if policy.get("refinement") is None:
        need(not providers, "PROVIDER_MODE")
    else:
        need(
            tuple(p.get("source") for p in providers)
            == tuple(
                a
                for a in records
                if a.kind == "source" and a in selected_relations(records, entry)
            ),
            "PROVIDER_SOURCE_CLOSURE",
        )

    from pietto._project.project_sql_plan_requirements import (
        verify_compiled_requirement_inputs,
    )

    verify_compiled_requirement_inputs(records)

    # Ownership can point back to an enclosing record. Only actual producer
    # edges determine scheduling; caller-provided traversal order is not proof.
    incoming = {a: [] for a in records if a.kind in RELATIONS}
    for record in records.values():
        if record.address.kind == "use":
            incoming[record.get("consumer")].append(record.get("producer"))
    reads = {a: [] for a in incoming}
    for record in records.values():
        if record.address.kind == "expression_block_use":
            reads[record.get("consumer")].append(record.get("producer"))
    # Inline units are exactly the use chains of the capturing lets the
    # capture records name, each read once and never a unit position.
    inline = {
        a
        for a in incoming
        if "layout" in FIELDS[a.kind] and unit_position(records[a]) is None
    }
    chained: set[Address] = set()
    for read in {
        r.get("read") for r in records.values() if r.address.kind == "capture_use"
    }:
        current = records[read].get("producer")
        outermost = current
        while current in inline:
            need(current not in chained, "INLINE_CHAIN")
            chained.add(current)
            layout = records[current].get("layout")
            need(
                (
                    current.kind == "row"
                    # Only the outermost unit of a let is its result unit.
                    or (current.kind == "result" and current == outermost)
                )
                and layout[:2] == (None, ())
                and type(layout[2]) is str
                and layout[3] is False,
                "INLINE_LAYOUT",
            )
            producers = incoming[current]
            need(len(producers) == 1, "INLINE_CHAIN")
            current = producers[0]
    need(chained == inline, "INLINE_INVENTORY")
    # The records of one capturing read are its lines 0, 1, ... in record
    # order, each exactly the ports of one distinct row binding of the reading
    # body's input: the one input of an EXISTS read's row, or the left input of
    # the JOIN whose right input reads the let LATERAL. Every captured field
    # read lies in the inline units of one capturing read and reads, through
    # that reading use, a port of one of that read's records.
    capture_records: dict[Address, list[Record]] = {}
    for record in records.values():
        if record.address.kind == "capture_use":
            capture_records.setdefault(record.get("read"), []).append(record)
    reading_uses = {}
    for read, described in capture_records.items():
        consumer = records[read].get("consumer")
        lateral = read.kind == "use"
        consumer_uses = tuple(
            r.address
            for r in records.values()
            if r.address.kind == "use"
            and r.get("consumer") == consumer
            and (not lateral or r.get("ordinal") == 0)
        )
        need(
            consumer.kind == ("join" if lateral else "row") and len(consumer_uses) == 1,
            "CAPTURE_SCOPE",
        )
        bindings = row_bindings(records, consumer_uses[0])
        need(
            [r.get("ordinal") for r in described] == list(range(len(described))),
            "CAPTURE_ORDINALS",
        )
        need(
            all(r.get("ports") in bindings for r in described)
            and len({r.get("ports") for r in described}) == len(described),
            "CAPTURE_PORTS",
        )
        reading_uses[read] = consumer_uses[0]
    attributed = captured_reads(records)
    need(
        set(attributed)
        == {
            r.address
            for r in records.values()
            if r.address.kind == "read" and r.get("role") == "capture"
        }
        and all(
            len(pairs) == 1
            and pairs[0][1] is not None
            and records[read].get("use") == reading_uses[pairs[0][0]]
            for read, pairs in attributed.items()
        ),
        "READ_CAPTURE",
    )
    execution = selected_relations(records, entry)
    # A correlated reference names an alias of its reading unit from inside
    # the let's inline units, so no inline unit of a read is named like a
    # relation of that unit (its scan or JOIN inputs, or the e<n> of a block
    # read it makes) or like another unit of the same let; the inputs of one
    # JOIN or set have distinct aliases. The one exception is the ORDER BY and
    # LIMIT wrapper of a `scalar` or `in` read, holding no reference: it names
    # the derived table every reference lies inside, never in scope there, and
    # PostgreSQL's wrapper of a JOIN reader repeats the reader's alias. Any
    # other unit is another scope, where an alias may repeat, and a retained
    # unit is never rendered.
    for address in execution:
        if "layout" not in FIELDS[address.kind]:
            continue
        alias = records[address].get("layout")[2]
        if address.kind in ("join", "set"):
            inputs = records[address].get(
                "inputs" if address.kind == "join" else "operands"
            )
            need(
                type(alias) is tuple
                and all(type(a) is str for a in alias)
                and len(set(alias)) == len(alias) == len(inputs),
                "ALIASES",
            )
        else:
            need(type(alias) is str, "ALIASES")
    for read in {
        r.get("read") for r in records.values() if r.address.kind == "capture_use"
    }:
        consumer = records[read].get("consumer")
        if consumer not in execution:
            continue
        alias = records[consumer].get("layout")[2]
        need(
            type(alias) is str
            or type(alias) is tuple
            and all(type(a) is str for a in alias),
            "ALIASES",
        )
        visible = {alias} if type(alias) is str else set(alias)
        visible.update(
            f"e{r.address.position}"
            for r in records.values()
            if r.address.kind == "expression_block_use"
            and r.get("consumer") == consumer
        )
        chain, current = [], records[read].get("producer")
        while current in inline:
            chain.append(current)
            current = incoming[current][0]
        names = [records[unit].get("layout")[2] for unit in chain]
        wrapper = (
            read.kind == "expression_block_use"
            and bool(chain)
            and chain[0].kind == "result"
            and not unit_captured_reads(records, chain[0])
        )
        need(
            all(type(n) is str for n in names)
            and len(set(names)) == len(names)
            and not set(names[1:] if wrapper else names) & visible,
            "ALIASES",
        )
    retained = entry.get("retained")
    need(
        len(set(retained)) == len(retained) and entry.get("terminal") not in retained,
        "RETAINED_ROOTS",
    )
    execution_owners = {
        records[a].get("owner") for a in execution if a.kind != "source"
    }
    requested_owners = {
        records[a].get("owner") for a in entry.get("requests")
    } - execution_owners
    need(
        {records[a].get("owner") for a in retained} == requested_owners
        and len(retained) == len(requested_owners),
        "RETAINED_REQUEST_CLOSURE",
    )
    reached = set(execution)
    for terminal in retained:
        retained_pending = [terminal]
        while retained_pending:
            address = retained_pending.pop()
            if address in reached:
                continue
            reached.add(address)
            # Every described block read is executed by its consumer.
            retained_pending.extend((*incoming[address], *reads[address]))
    need(reached == set(incoming), "RELATION_INVENTORY_CLOSURE")

    # A let is a block of the table or query record at its coordinates. Only
    # its block and that block's other lets read it, any number of times and in
    # any written order, so a closure reaches a let only through its block,
    # and a block reaches every let: positions 0, 1, 2, .... The one other root
    # is a retained request owner that is a let of an unselected block; its
    # closure is that let and what it reads. An expression block use reads its
    # producer like a use does.
    def coordinates(record):
        return tuple(record.get(n) for n in ("module", "module_position", "position"))

    blocks: dict[tuple, list[Record]] = {}
    lets: dict[tuple, set[Address]] = {}
    for record in records.values():
        if record.address.kind == "declaration":
            if record.get("let") is None:
                blocks.setdefault(coordinates(record), []).append(record)
            else:
                lets.setdefault(coordinates(record), set()).add(record.address)
    for place, members in lets.items():
        positions = [records[a].get("let") for a in members]
        parents = blocks.get(place, [])
        need(
            len(set(positions)) == len(positions)
            and (
                not parents
                or (
                    len(parents) == 1
                    and parents[0].get("namespace") == "relation"
                    and parents[0].get("kind") in ("table", "query")
                    and sorted(positions) == list(range(len(positions)))
                )
            ),
            "DECLARATION",
        )
    read_owners = set()
    for terminal in (entry.get("terminal"), *retained):
        root = records[records[terminal].get("owner")]
        closure, closure_pending = set(), [terminal]
        while closure_pending:
            address = closure_pending.pop()
            if address not in closure:
                closure.add(address)
                closure_pending.extend((*incoming[address], *reads[address]))
        owners = {records[a].get("owner") for a in closure if a.kind != "source"}
        read_owners |= owners
        for owner in owners:
            record = records[owner]
            place = coordinates(record)
            if record.get("let") is None:
                need(lets.get(place, set()) <= owners, "DECLARATION")
            else:
                parents = blocks.get(place, [])
                need(
                    (bool(parents) and parents[0].address in owners)
                    or (root.get("let") is not None and coordinates(root) == place),
                    "DECLARATION",
                )
    need(
        all(
            members <= read_owners
            and all(p.address in read_owners for p in blocks.get(place, ()))
            for place, members in lets.items()
        ),
        "DECLARATION",
    )
    active, complete = set(), set()
    for relation in incoming:
        relation_pending = [(relation, False)]
        while relation_pending:
            current, returning = relation_pending.pop()
            if returning:
                active.remove(current)
                complete.add(current)
            elif current not in complete:
                need(current not in active, "RELATION_CYCLE")
                active.add(current)
                relation_pending.append((current, True))
                relation_pending.extend(
                    (item, False)
                    for item in reversed((*incoming[current], *reads[current]))
                )

    _verify_compiled_contract(records, entry, contract_data, family)


def _verify_compiled_contract(
    records: dict[Address, Record], entry: Record, document: Any, family: str
):
    """Check resolved contract inputs and original admission laws, without lookup."""
    from pietto._project.project_compiled_schema import json_value
    from pietto._project.project_sql_emission_contract import (
        Premise,
        canonical,
        validate_resolved_premise,
    )
    from pietto._project.project_sql_emission_ast import (
        field_premise_problems,
        identifier_valid,
        naming_premise_problems,
        operator_premise_problems,
        source_premise_problems,
    )

    def selector(address):
        owner = records[address]
        return {
            "module": owner.get("module"),
            "kind": "source",
            "name": owner.get("label"),
        }

    active = selected_relations(records, entry)
    sources = tuple(
        r
        for r in records.values()
        if r.address.kind == "source" and r.address in active
    )
    need(len(sources) == len(document["sources"]), "CONTRACT_SOURCES")
    inputs: list[tuple[Any, Address | None]] = [
        (raw, None) for raw in document["environment"]
    ]
    for source, raw in zip(sources, document["sources"], strict=True):
        need(
            type(raw) is dict
            and set(raw) == {"selector", "relation", "scan", "fields", "premises"},
            "CONTRACT_SOURCE",
        )
        raw = cast(dict[str, Any], raw)
        need(
            raw["selector"] == selector(source.get("declaration"))
            and raw["scan"] == "relation_rows",
            "CONTRACT_SOURCE",
        )
        need(
            raw["relation"]
            == {"namespace": source.get("namespace"), "name": source.get("name")},
            "CONTRACT_RELATION",
        )
        need(
            all(
                identifier_valid(source.get(k), family, relation=True)
                for k in ("namespace", "name")
            ),
            "CONTRACT_IDENTIFIER",
        )
        need(
            type(raw["fields"]) is list
            and len(raw["fields"]) == len(source.get("fields")),
            "CONTRACT_FIELDS",
        )
        columns = set()
        for address, described in zip(source.get("fields"), raw["fields"], strict=True):
            record = records[address]
            need(
                type(described) is dict
                and canonical(described)
                == canonical(
                    {
                        "ordinal": record.get("ordinal"),
                        "name": record.get("label"),
                        "column": record.get("column"),
                        "representation": json_value(record.get("physical").encode()),
                    }
                ),
                "CONTRACT_FIELD",
            )
            # Equality alone must not identify bool with an integer ordinal.
            need(type(described["ordinal"]) is int, "CONTRACT_FIELD")
            column = record.get("column")
            column_key = column if family == "postgres" else column.casefold()
            need(
                identifier_valid(column, family) and column_key not in columns,
                "CONTRACT_COLUMN",
            )
            columns.add(column_key)
        need(type(raw["premises"]) is list, "CONTRACT_PREMISES")
        inputs.extend((p, source.get("declaration")) for p in raw["premises"])

    described_premises = tuple(
        r for r in records.values() if r.address.kind == "premise"
    )
    need(len(inputs) == len(described_premises), "CONTRACT_PREMISES")
    premises = []
    prior = {}
    for record, (raw, enclosing) in zip(described_premises, inputs, strict=True):
        need(
            type(raw) is dict and set(raw) == {"key", "scope", "value"},
            "CONTRACT_PREMISE",
        )
        scope = record.get("scope")
        expected_scope: Any
        if scope == "statement":
            expected_scope = "statement"
        elif type(scope) is tuple:
            owner, context = scope
            site = records[context]
            expected_scope = {
                "kind": "expression",
                "source": selector(owner),
                "site": {"kind": site.get("kind"), "position": site.get("position")},
                "context": {
                    "kind": site.get("block_kind"),
                    "position": site.get("block_position"),
                },
            }
        else:
            expected_scope = (
                "source"
                if raw["scope"] == "source" and scope == enclosing
                else {"kind": "source", "selector": selector(scope)}
            )
        need(
            canonical(raw["scope"]) == canonical(expected_scope),
            "CONTRACT_PREMISE_SCOPE",
        )
        value = json_value(record.get("value").encode())
        errors = []
        validate_resolved_premise(
            record.get("key"),
            "statement"
            if scope == "statement"
            else "expression"
            if type(scope) is tuple
            else "source",
            value,
            "compiled/premise",
            errors,
        )
        need(not errors, "PREMISE_VALUE")
        need(
            raw["key"] == record.get("key")
            and canonical(raw["value"]) == canonical(value),
            "CONTRACT_PREMISE",
        )
        encoded = canonical(value)
        need(record.get("value").encode() == encoded, "PREMISE_CANONICAL")
        key = (scope, record.get("key"))
        need(key not in prior or prior[key] == encoded, "PREMISE_CONFLICT")
        prior[key] = encoded
        premises.append(
            Premise(record.address.position, record.get("key"), scope, encoded)
        )

    operators = any(
        a.kind in {"join", "aggregate", "window", "result", "set"}
        or a.kind == "row"
        and (
            records[a].get("predicate") is not None
            or any(v.kind != "read" for v in records[a].get("values"))
        )
        for a in active
    )
    if operators:
        need(
            not operator_premise_problems(
                premises, family, any(a.kind == "slot" for a in records)
            ),
            "OPERATOR_PREMISE",
        )
    if sum(a.kind not in {"source", "scan"} for a in active) > 1:
        need(not naming_premise_problems(premises, family), "NAMING_PREMISE")
    for source in sources:
        owner = source.get("declaration")
        used = tuple(p for p in premises if p.scope == "statement" or p.scope == owner)
        need(not source_premise_problems(used, family), "SOURCE_PREMISE")
        for address in source.get("fields"):
            field = records[address]
            scoped = tuple(
                p
                for p in premises
                if p in used
                or type(p.scope) is tuple
                and p.scope[0] == owner
                and address in records[p.scope[1]].get("fields")
            )
            need(
                not field_premise_problems(scoped, field.get("physical").encode()),
                "FIELD_PREMISE",
            )
    for address in entry.get("exports"):
        need(
            identifier_valid(records[address].get("label"), family, label=True),
            "OUTPUT_LABEL",
        )


def verify_export(description, artifact, *, guarded=None, refinement=None):
    """Read the original complete inventory, without calling the exporter."""
    from pietto._project.project_execution_binding_verification import inspect
    from pietto._project.project_sql_emission_contract import BoundSource
    from pietto._project import project_sql_emission_ast as sql
    from pietto._project import project_sql_emission_parameters as parameters
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project import project_sql_emission_results as results
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project import project_sql_emission_sets as setting
    from pietto._project import project_sql_emission_values as valuing
    from pietto._project import project_sql_emission_joins as joining

    view = inspect(artifact, guarded)
    verify_description(description)
    records = {r.address: r for r in description.records}
    original = artifact.request
    grouped = {
        kind: tuple(r for r in records.values() if r.address.kind == kind)
        for kind in FIELDS
    }
    target = grouped["target"][0]
    need(
        target.values[:3]
        == (original.family, original.release, original.accepted_bytes.decode()),
        "EXPORT_TARGET",
    )

    def _original_meaning_entry(field):
        from pietto._project.project_scalar_meaning import _source_entry, verify_law

        entry = _source_entry(field.scalar_meaning, field.field)
        if entry is not None:
            verify_law(entry.law, field.field.evidence.resolved_type.name)
        return entry

    source_map, unit_map = {}, {}
    need(len(grouped["source"]) == len(original.sources), "EXPORT_SOURCES")
    for record, source in zip(grouped["source"], original.sources, strict=True):
        source_map[id(source)] = record.address
        need(
            record.get("namespace") == source.namespace
            and record.get("name") == source.name,
            "EXPORT_SOURCE",
        )
        need(len(record.get("fields")) == len(source.fields), "EXPORT_FIELDS")
        for address, actual in zip(record.get("fields"), source.fields, strict=True):
            described = records[address]
            need(
                described.values
                == (
                    record.address,
                    actual.ordinal,
                    actual.name,
                    actual.column,
                    (
                        actual.field.evidence.resolved_type.name,
                        actual.field.effective_nullability.value,
                    ),
                    actual.representation.decode(),
                    None
                    if actual.decimal is None
                    else (actual.decimal.precision, actual.decimal.scale),
                    actual.field.evidence.resolved_type.name
                    if actual.scalar_meaning is not None
                    and _original_meaning_entry(actual) is not None
                    else None,
                ),
                "EXPORT_FIELD",
            )
    need(len(grouped["premise"]) == len(original.premises), "EXPORT_PREMISES")
    from pietto._project.project_sql_emission_scopes import reference_source_ports

    original_references = reference_source_ports(original.plan)
    for record, premise in zip(grouped["premise"], original.premises, strict=True):
        need(
            record.get("position") == premise.position
            and record.get("key") == premise.key
            and record.get("value").encode() == premise.value,
            "EXPORT_PREMISE",
        )
        scope = record.get("scope")
        if premise.scope == "statement":
            need(scope == "statement", "EXPORT_PREMISE_SCOPE")
        elif type(premise.scope) is tuple:
            owner, context = premise.scope
            need(type(scope) is tuple and len(scope) == 2, "EXPORT_PREMISE_SCOPE")
            described_owner, described_context = records[scope[0]], records[scope[1]]
            need(
                described_owner.values == declaration_values(owner),
                "EXPORT_PREMISE_OWNER",
            )
            need(
                described_context.values[1:5]
                == (
                    context.ref.kind.value,
                    context.ref.position,
                    context.block.kind.value,
                    context.block.position,
                ),
                "EXPORT_PREMISE_CONTEXT",
            )
            expected_fields = tuple(
                port.field
                for expression, port in original_references.values()
                if expression.site is context
            )
            need(
                len(described_context.get("fields")) == len(expected_fields),
                "EXPORT_CONTEXT_FIELDS",
            )
            for address, field in zip(
                described_context.get("fields"), expected_fields, strict=True
            ):
                described = records[address]
                source = original.sources[described.get("source").position]
                need(
                    source.fields[described.get("ordinal")].field is field,
                    "EXPORT_CONTEXT_FIELD",
                )
        else:
            described = records[scope]
            need(
                described.values == declaration_values(premise.scope),
                "EXPORT_PREMISE_OWNER",
            )
    need(len(grouped["site"]) == len(original.plan.literal_sites), "EXPORT_SITES")
    from pietto.ast_nodes import (
        UnaryExpr,
        BinaryExpr,
        CastExpr,
        ComparisonExpr,
        ConditionalExpr,
        IsNullExpr,
        MembershipExpr,
        BetweenExpr,
        CallExpr,
        RelationMembershipExpr,
    )

    parent_kinds = {
        UnaryExpr: "unary",
        BinaryExpr: "binary",
        ComparisonExpr: "comparison",
        IsNullExpr: "null_test",
        BetweenExpr: "between",
        CallExpr: "call",
        ConditionalExpr: "conditional",
        MembershipExpr: "membership",
        RelationMembershipExpr: "relation_membership",
        CastExpr: "cast",
    }
    expected_declarations = {}

    def check_declaration(address, owner):
        record = records[address]
        need(
            record.address.kind == "declaration"
            and record.values == declaration_values(owner),
            "EXPORT_DECLARATION",
        )
        previous = expected_declarations.setdefault(address, owner)
        need(previous is owner, "EXPORT_DECLARATION_ALIAS")

    for record, source in zip(grouped["source"], original.sources, strict=True):
        check_declaration(record.get("declaration"), source.owner)
    original_keys = []
    key_seen = set()
    for source in original.sources:
        definitions = tuple(
            d
            for d in original.plan.bindings.definitions
            if d.entry.owner is source.owner
        )
        need(len(definitions) == 1, "EXPORT_SOURCE_KEYS")
        for key in definitions[0].entry.active_properties.relational.keys:
            for fact in key.supports:
                for support in fact.supports:
                    if id(support) in key_seen:
                        continue
                    key_seen.add(id(support))
                    original_keys.append((source, support))
    need(
        len(grouped["source_unique"]) == len(original_keys),
        "EXPORT_SOURCE_KEY_INVENTORY",
    )
    for record, (source, support) in zip(
        grouped["source_unique"], original_keys, strict=True
    ):
        check_declaration(record.get("shape"), support.declaration.shape_occurrence)
        need(
            record.get("source") == source_map[id(source)]
            and record.get("position")
            == support.identity.declaration.shape_item_position
            and tuple(records[a].get("ordinal") for a in record.get("fields"))
            == tuple(
                d.source_field_identity.field_position for d in support.determinants
            )
            and record.values[-4:]
            == (
                support.null_policy.value,
                support.origin.value,
                support.trust.value,
                support.enforcement.value,
            ),
            "EXPORT_SOURCE_KEY",
        )
    all_literals = (*grouped["literal"], *grouped["null_literal"])
    need(len(all_literals) == len(original.plan.literal_sites), "EXPORT_LITERALS")
    for index, (record, site) in enumerate(
        zip(grouped["site"], original.plan.literal_sites, strict=True)
    ):
        position = site.position
        check_declaration(record.get("owner"), position.owner)
        ancestry = tuple(
            (parent_kinds[type(parent)], ordinal)
            for parent, ordinal in position.ancestry
        )
        need(
            record.values[1:]
            == (
                position.role.value,
                index,
                ancestry,
                site.disposition.value,
                None if site.reason is None else site.reason.value,
            ),
            "EXPORT_SITE",
        )
        literals = tuple(r for r in all_literals if r.get("site") == record.address)
        need(len(literals) == 1, "EXPORT_SITE_LITERAL")
        literal = literals[0]
        need(
            (literal.address.kind == "null_literal" and position.literal.value is None)
            or (
                literal.address.kind == "literal"
                and parameters.same_value(
                    literal.get("value").value, position.literal.value
                )
            ),
            "EXPORT_STATIC_LITERAL",
        )
    need(len(grouped["slot"]) == len(original.plan.literal_slots), "EXPORT_SLOTS")
    for index, (record, slot) in enumerate(
        zip(grouped["slot"], original.plan.literal_slots, strict=True)
    ):
        positions = tuple(
            i for i, site in enumerate(original.plan.literal_sites) if site is slot.site
        )
        need(
            len(positions) == 1
            and record.get("site") == Address("site", positions[0])
            and record.get("tag") == slot.tag.value,
            "EXPORT_SLOT",
        )
        literal = records[record.get("literal")]
        need(
            type(literal.get("value")) is Scalar
            and parameters.same_value(
                literal.get("value").value, slot.site.position.literal.value
            ),
            "EXPORT_LITERAL",
        )
    declared = original.plan.parameters
    need(len(grouped["parameter"]) == len(declared), "EXPORT_PARAMETERS")
    for record, parameter in zip(grouped["parameter"], declared, strict=True):
        check_declaration(record.get("declaration"), parameter.owner)
        need(
            record.values[1:]
            == (
                parameter.ordinal,
                parameter.declaration.name,
                parameter.tag,
                parameter.value_type.nullability.value == "nullable",
            ),
            "EXPORT_PARAMETER",
        )
    need(len(grouped["native_use"]) == len(artifact.parameter_uses), "EXPORT_USES")
    reads = iter(grouped["parameter_read"])
    for record, use in zip(grouped["native_use"], artifact.parameter_uses, strict=True):
        if use.parameter is not None:
            # Each read occurrence owns its record, in native occurrence order.
            read = next(reads, None)
            need(
                read is not None
                and read.get("parameter") == Address("parameter", use.parameter.ordinal)
                and record.values
                == (
                    read.address,
                    use.ordinal,
                    use.server_index,
                    use.physical_type,
                ),
                "EXPORT_USE",
            )
            continue
        slots = tuple(
            i for i, slot in enumerate(original.plan.literal_slots) if slot is use.slot
        )
        need(
            len(slots) == 1
            and record.values
            == (
                Address("slot", slots[0]),
                use.ordinal,
                use.server_index,
                use.physical_type,
            ),
            "EXPORT_USE",
        )
    need(next(reads, None) is None, "EXPORT_PARAMETER_READS")
    ast = artifact.ast
    units: tuple[Any, ...]
    if type(ast) is sql.SQLSelect:
        units = tuple(c.body for c in ast.ctes) + (ast,)
    elif type(ast) is sql.SQLRowQuery:
        units = ast.bodies
    elif type(ast) is sql.SQLJoinQuery:
        units = ast.units
    else:
        raise CompiledError("COMPILED_EXPORT_ROOT")
    # An inline let's units have no unit position: they are checked at the
    # live read that renders them.
    described_units = tuple(
        r
        for r in records.values()
        if r.address.kind in RELATIONS - {"source"} and r.get("layout")[-1] is not None
    )
    inline_units = {
        r.address
        for r in records.values()
        if r.address.kind in RELATIONS - {"source"} and r.get("layout")[-1] is None
    }
    inline_seen: set[Address] = set()
    capture_seen: set[Address] = set()
    current_units: list[Any] = []
    capture_context: list[tuple[Any, Any]] = []
    need(len(described_units) == len(units), "EXPORT_UNITS")
    index_of = {id(unit): index for index, unit in enumerate(units)}
    for index, (record, unit) in enumerate(zip(described_units, units, strict=True)):
        need(record.get("layout")[-1] == index, "EXPORT_UNIT_ORDER")
        unit_map[id(unit)] = record.address
        if type(unit) is joining.JoinBody:
            definitions = tuple(
                d
                for d in original.plan.bindings.definitions
                if d.ref is unit.join.definition
            )
            need(len(definitions) == 1, "EXPORT_JOIN_OWNER")
            owner = definitions[0].entry.owner
        else:
            owner = unit.definition.original.entry.owner
        check_declaration(record.get("owner"), owner)

    def expected_producer(scan):
        if type(scan) in (sql.SQLScan, sql.RowScan):
            return scan.realization
        if type(scan) is sql.SQLNamedUse:
            return scan.cte.body
        return scan.body

    def port_address(column, producer):
        source = source_map.get(id(producer))
        if source is not None:
            positions = tuple(
                i for i, f in enumerate(producer.fields) if column.field is f
            )
            owner = source
        else:
            positions = tuple(
                i
                for i, c in enumerate(producer.columns)
                if c.column.terminal is column.terminal
            )
            owner = unit_map.get(id(producer))
        need(len(positions) == 1, "EXPORT_CAPTURE_PORT")
        found = tuple(
            r.address
            for r in grouped["port"]
            if r.get("owner") == owner and r.get("ordinal") == positions[0]
        )
        need(len(found) == 1, "EXPORT_CAPTURE_PORT")
        return found[0]

    def check_inline_units(first, terminal, context):
        """A live inline let ending in ``terminal``, unit by unit from its
        innermost body, whatever reads it: ``first`` is the unit its read names,
        ``context`` the reading row (producer, use), and its ORDER BY and LIMIT
        end it in a result unit."""
        chain = sql.inline_chain(terminal)
        addresses = [first]
        while True:
            uses = tuple(
                r for r in grouped["use"] if r.get("consumer") == addresses[-1]
            )
            need(len(uses) == 1, "EXPORT_INLINE_USE")
            if uses[0].get("producer") not in inline_units:
                break
            addresses.append(uses[0].get("producer"))
        addresses.reverse()
        need(
            len(addresses) == len(chain)
            and all(sql.inline_body(body) for body in chain),
            "EXPORT_INLINE",
        )
        capture_context.append(context)
        try:
            for address, body in zip(addresses, chain, strict=True):
                record = records[address]
                need(
                    address in inline_units
                    and address not in inline_seen
                    and record.address.kind
                    == ("result" if type(body) is results.RowResultBody else "row")
                    and record.get("layout")
                    == (None, (), body.scan.symbol.name, False, None),
                    "EXPORT_INLINE_UNIT",
                )
                inline_seen.add(address)
                unit_map[id(body)] = address
                check_declaration(
                    record.get("owner"), body.definition.original.entry.owner
                )
                check_unit(record, body)
        finally:
            capture_context.pop()

    def check_inline(block_use, actual, producer, use):
        """A live inline let, unit by unit, and the capture records of its read."""
        outer = current_units[-1]
        need(type(outer) is sql.RowBody, "EXPORT_INLINE")
        check_inline_units(
            block_use.get("producer"), actual.target.producer, (producer, use)
        )
        captures = tuple(
            c for c in original.plan.captures if c.read is actual.original.ref
        )
        described = tuple(
            r for r in grouped["capture_use"] if r.get("read") == block_use.address
        )
        need(len(described) == len(captures) > 0, "EXPORT_CAPTURES")
        for record, capture in zip(described, captures, strict=True):
            ports = []
            for reference in capture.ports:
                position = outer.block.inputs.index(reference)
                column = sql._stage_read(original, outer.scan, position, reference)
                need(column is not None, "EXPORT_CAPTURE_PORT")
                ports.append(port_address(column, producer))
            need(
                record.values == (block_use.address, capture.use.ordinal, tuple(ports)),
                "EXPORT_CAPTURE",
            )
            capture_seen.add(record.address)

    def check_lateral(use_address, item, left, left_producer, left_use):
        """A live LATERAL right input's inline let, unit by unit over the
        JOIN's left input, and the capture records its use reads."""
        check_inline_units(
            records[use_address].get("producer"),
            item.producer,
            (left_producer, left_use),
        )
        captures = tuple(
            c for c in original.plan.captures if c.read is item.original.ref
        )
        described = tuple(
            r for r in grouped["capture_use"] if r.get("read") == use_address
        )
        need(len(described) == len(captures) > 0, "EXPORT_CAPTURES")
        for record, capture in zip(described, captures, strict=True):
            ports = []
            for reference in capture.ports:
                positions = tuple(i for i, p in enumerate(left.ports) if p is reference)
                need(len(positions) == 1, "EXPORT_CAPTURE_PORT")
                ports.append(port_address(left.columns[positions[0]], left_producer))
            need(
                record.values == (use_address, capture.use.ordinal, tuple(ports)),
                "EXPORT_CAPTURE",
            )
            capture_seen.add(record.address)

    def check_read(address, actual, producer, use, role="value"):
        record = records[address]
        need(
            record.address.kind == "read"
            and record.get("use") == use
            and record.get("role") == role,
            "EXPORT_READ",
        )
        port = records[record.get("port")]
        source = source_map.get(id(producer))
        if source is not None:
            positions = tuple(
                i for i, f in enumerate(producer.fields) if actual.field is f
            )
            need(
                len(positions) == 1
                and port.get("owner") == source
                and port.get("ordinal") == positions[0],
                "EXPORT_READ_SOURCE",
            )
        else:
            positions = tuple(
                i
                for i, c in enumerate(producer.columns)
                if c.column.terminal is actual.terminal
            )
            need(
                len(positions) == 1
                and port.get("owner") == unit_map[id(producer)]
                and port.get("ordinal") == positions[0],
                "EXPORT_READ_PORT",
            )

    def check_scalar(address, actual, producer, use, join_contexts=None):
        record = records[address]
        if type(actual) is rows.SQLCapturedReference:
            # A captured field reads the reading body's own input row.
            need(join_contexts is None and bool(capture_context), "EXPORT_CAPTURE")
            outer_producer, outer_use = capture_context[-1]
            check_read(address, actual.column, outer_producer, outer_use, "capture")
        elif type(actual) is rows.SQLStageReference:
            if join_contexts is not None:
                matches = tuple(
                    (p, u) for symbol, p, u in join_contexts if symbol is actual.scope
                )
                need(len(matches) == 1, "EXPORT_MATCH_SCOPE")
                producer, use = matches[0]
            check_read(address, actual.column, producer, use)
        elif type(actual) is parameters.SQLAnchor:
            check_scalar(address, actual.operand, producer, use, join_contexts)
        elif type(actual) is rows.SQLParameterRead:
            need(
                record.address.kind == "parameter_read"
                and record.get("parameter")
                == Address("parameter", actual.original.parameter.ordinal)
                and any(
                    u is actual.use and records[native].get("slot") == address
                    for u, native in zip(
                        artifact.parameter_uses,
                        (r.address for r in grouped["native_use"]),
                        strict=True,
                    )
                ),
                "EXPORT_PARAMETER_READ",
            )
        elif type(actual) in (parameters.SQLLiteral, parameters.SQLParameter):
            need(record.address.kind == "literal", "EXPORT_LITERAL")
            value = (
                actual.value
                if type(actual) is parameters.SQLLiteral
                else actual.fixed.value
            )
            need(
                type(record.get("value")) is Scalar
                and parameters.same_value(record.get("value").value, value),
                "EXPORT_LITERAL_VALUE",
            )
        elif type(actual) is parameters.SQLNull:
            need(
                record.address.kind == "null_literal"
                and parameters.typed_null(actual.original)
                and actual.site.position.literal.value is None
                and actual.site.disposition.value == "preserved_with_reason"
                and actual.site.reason.value == "contextual_typed_null",
                "EXPORT_NULL_LITERAL",
            )
        elif type(actual) in (parameters.SQLUnary, rows.SQLOperation):
            need(record.address.kind == "operation", "EXPORT_OPERATION")
            if type(actual) is parameters.SQLUnary:
                role, token, operands = (
                    "unary",
                    actual.original.expression.operator,
                    (actual.operand,),
                )
            else:
                role = {
                    "sign": "unary",
                    "not": "not",
                    "arithmetic": "binary",
                    "logical": "binary",
                    "comparison": "comparison",
                    "null_test": "null_test",
                    "between": "between",
                    "scalar_call": "scalar_call",
                    "conditional": "conditional",
                    "membership": "membership",
                    "cast": "cast",
                }.get(actual.kind)
                need(role is not None, "EXPORT_OPERATION")
                token = (
                    actual.original.callee_symbol.name
                    if role == "scalar_call"
                    else "not_in"
                    if role == "membership" and actual.original.expression.negated
                    else "in"
                    if role == "membership"
                    else "int_to_float"
                    if role == "cast"
                    else "if_else"
                    if role == "conditional"
                    else "between"
                    if role == "between"
                    else "not"
                    if role == "not"
                    else "is_not_null"
                    if role == "null_test" and actual.original.expression.negated
                    else "is_null"
                    if role == "null_test"
                    else actual.original.expression.operator
                )
                operands = actual.operands
            need(
                record.get("operator") == (role, token)
                and len(record.get("operands")) == len(operands),
                "EXPORT_OPERATION",
            )
            for child, expected in zip(record.get("operands"), operands, strict=True):
                check_scalar(child, expected, producer, use, join_contexts)
        elif type(actual) is rows.SQLBlockRead:
            # The block read operation and its one expression block use name
            # the live read's consumer, producer, occurrence, read or compared
            # column and generated alias.
            need(
                join_contexts is None
                and record.address.kind == "operation"
                and record.get("operator")
                == (
                    (actual.kind, actual.kind)
                    if actual.kind in ("exists", "scalar")
                    else ("relation_membership", actual.kind)
                )
                and record.get("operator") in BLOCK_READ_OPERATORS
                and len(record.get("operands")) == len(actual.operands)
                and len(actual.operands) == (actual.kind in ("in", "not_in")),
                "EXPORT_BLOCK_READ",
            )
            for child, expected in zip(
                record.get("operands"), actual.operands, strict=True
            ):
                check_scalar(child, expected, producer, use, join_contexts)
            matches = tuple(
                r
                for r in records.values()
                if r.address.kind == "expression_block_use"
                and r.get("operation") == address
            )
            need(len(matches) == 1, "EXPORT_BLOCK_READ")
            target = actual.target
            expected_producer = (
                source_map.get(id(target.producer))
                if target.source is not None
                else unit_map.get(id(target.producer))
            )
            if target.source is None and sql.inline_body(target.producer):
                check_inline(matches[0], actual, producer, use)
                expected_producer = unit_map.get(id(target.producer))
            need(
                expected_producer is not None
                and matches[0].address.position == target.use.ref.position
                and target.symbol.name == f"e{target.use.ref.position}"
                and matches[0].values
                == (
                    address,
                    records[use].get("consumer"),
                    expected_producer,
                    actual.column,
                ),
                "EXPORT_BLOCK_READ",
            )
        else:
            raise CompiledError("COMPILED_EXPORT_SCALAR")

    def check_window_spec(address, actual, policy, producer, use, definitions):
        described = records[address]
        need(
            address.kind == "window_spec"
            and len(described.get("partition")) == len(actual.partitions)
            and len(described.get("ordering")) == len(actual.orders),
            "EXPORT_WINDOW_SPEC",
        )
        for child, (_, read) in zip(
            described.get("partition"), actual.partitions, strict=True
        ):
            check_read(child, read, producer, use)
        for child, item in zip(described.get("ordering"), actual.orders, strict=True):
            need(child[1:] == (item.direction, item.nulls), "EXPORT_WINDOW_ORDER")
            check_read(child[0], item.read, producer, use)
        expected_named = (
            None if actual.symbol is None else definitions[id(actual.symbol)]
        )
        need(described.get("named") == expected_named, "EXPORT_WINDOW_NAMED")
        frame = described.get("frame")
        need((frame is None) == (actual.frame is None), "EXPORT_WINDOW_FRAME")
        if frame is not None:
            resolved = policy.specification.frame.resolved
            need(
                frame[0] == resolved.unit.value == actual.frame.unit
                and frame[3]
                == (None if resolved.exclusion is None else resolved.exclusion.value),
                "EXPORT_WINDOW_FRAME",
            )
            for bound, source in zip(
                frame[1:3], (resolved.start, resolved.end), strict=True
            ):
                need(
                    bound[0] == source.kind.value
                    and (bound[1] is None) == (source.offset is None),
                    "EXPORT_WINDOW_BOUND",
                )
                if source.offset is not None:
                    site_positions = tuple(
                        i
                        for i, site in enumerate(original.plan.literal_sites)
                        if site.position.literal is source.offset
                    )
                    need(
                        len(site_positions) == 1
                        and records[bound[1]].get("site")
                        == Address("site", site_positions[0]),
                        "EXPORT_WINDOW_BOUND_SITE",
                    )

    def check_unit(record, unit):
        """One live unit against its record; inline lets are checked at their read."""
        current_units.append(unit)
        try:
            check_unit_body(record, unit)
        finally:
            current_units.pop()

    def check_unit_body(record, unit):
        if record.address.kind == "join":
            need(
                type(unit) is joining.JoinBody
                and record.get("kind") == unit.join.kind.value
                and record.get("ordinal") == unit.join.position
                and len(record.get("inputs")) == len(unit.inputs)
                and len(record.get("outputs")) == len(unit.columns)
                and len(record.get("equalities")) == len(unit.equalities),
                "EXPORT_JOIN",
            )
            from pietto._project.project_ir_joins import (
                ProjectIRBinaryJoinOccurrence,
                _source_slice_fields,
            )
            from pietto._project.project_current_joins import ProjectCurrentBinaryJoin

            actual_join = unit.join.source.source
            if type(actual_join) is ProjectIRBinaryJoinOccurrence:
                expected_law = "relationship"
                positions = tuple(
                    f.field_position for f in _source_slice_fields(actual_join)
                )
            else:
                need(type(actual_join) is ProjectCurrentBinaryJoin, "EXPORT_JOIN_LAW")
                expected_law = "current"
                candidates = actual_join.condition.environment.source_candidates
                positions = tuple(
                    i
                    for i, (binding, _) in enumerate(actual_join.left_fields)
                    if len(candidates) == 1 and binding is candidates[0]
                )
            need(
                record.get("law") == expected_law
                and record.get("source_positions") == positions,
                "EXPORT_JOIN_LAW",
            )
            contexts = []
            for position, (a, item) in enumerate(
                zip(record.get("inputs"), unit.inputs, strict=True)
            ):
                use_record = records[a]
                producer = item.producer
                if position and sql.inline_body(producer):
                    check_lateral(a, item, unit.inputs[0], *contexts[0][1:])
                expected = source_map.get(id(producer), unit_map.get(id(producer)))
                need(
                    use_record.get("producer") == expected
                    and use_record.get("ordinal") == position
                    and record.get("layout")[2][position] == item.symbol.name,
                    "EXPORT_JOIN_INPUT",
                )
                contexts.append((item.symbol, producer, a))
            for a, equality in zip(
                record.get("equalities"), unit.equalities, strict=True
            ):
                described = records[a]
                check_read(
                    described.get("left"), equality.left, contexts[0][1], contexts[0][2]
                )
                check_read(
                    described.get("right"),
                    equality.right,
                    contexts[1][1],
                    contexts[1][2],
                )
            need(
                (record.get("predicate") is None) == (unit.predicate is None),
                "EXPORT_JOIN_PREDICATE",
            )
            if unit.predicate is not None:
                check_scalar(
                    record.get("predicate"), unit.predicate, None, None, tuple(contexts)
                )
            for a, column in zip(record.get("outputs"), unit.columns, strict=True):
                port = records[a]
                value = records[port.get("source")]
                matches = tuple(
                    (p, u) for symbol, p, u in contexts if symbol is column.scope
                )
                need(
                    len(matches) == 1 and port.get("label") == column.label,
                    "EXPORT_JOIN_COLUMN",
                )
                check_read(value.get("input"), column.read, *matches[0])
            return
        if record.address.kind == "set":
            need(
                type(unit) is setting.SetBody
                and record.get("kind") == unit.kind.value
                and record.get("quantifier") == unit.quantifier.value
                and len(record.get("operands")) == len(unit.operands)
                and len(record.get("outputs")) == len(unit.columns),
                "EXPORT_SET",
            )
            for position, (address, operand) in enumerate(
                zip(record.get("operands"), unit.operands, strict=True)
            ):
                use = records[address]
                producer = operand.producer
                expected = source_map.get(id(producer), unit_map.get(id(producer)))
                need(
                    use.get("consumer") == record.address
                    and use.get("ordinal") == position
                    and use.get("producer") == expected
                    and record.get("layout")[2][position] == operand.symbol.name,
                    "EXPORT_SET_OPERAND",
                )
                for index, port_address in enumerate(record.get("outputs")):
                    port = records[port_address]
                    value = records[port.get("source")]
                    need(
                        port.get("label") == unit.columns[index].label,
                        "EXPORT_SET_LABEL",
                    )
                    check_read(
                        value.get("inputs")[position],
                        operand.columns[index],
                        producer,
                        address,
                    )
            return
        if record.address.kind == "values":
            from pietto._project.project_sql_emission_contract import canonical

            fields = tuple(records[a] for a in record.get("fields"))
            need(
                type(unit) is valuing.ValuesBody
                and len(fields) == len(unit.columns) == len(record.get("outputs"))
                and not any(r.get("consumer") == record.address for r in grouped["use"])
                and record.get("layout")
                == (
                    None if unit.symbol is None else unit.symbol.name,
                    tuple(c.name for c in unit.cte_columns),
                    unit.scope.name,
                    unit.final,
                    index_of[id(unit)],
                )
                and len(record.get("rows")) == len(unit.rows),
                "EXPORT_VALUES",
            )
            for column, field, port_address in zip(
                unit.columns, fields, record.get("outputs"), strict=True
            ):
                realization = column.realization
                need(
                    field.get("label") == column.source.source.name
                    and field.get("logical")
                    == (
                        realization.tag,
                        "nullable" if realization.nullable is True else "non_null",
                    )
                    and field.get("physical")
                    == canonical(
                        {
                            "storage": realization.storage,
                            "nullable": realization.nullable,
                            "domain": realization.domain,
                        }
                    ).decode("utf-8")
                    and records[port_address].get("label") == column.label,
                    "EXPORT_VALUES_COLUMN",
                )
            for row, cells in zip(unit.rows, record.get("rows"), strict=True):
                need(
                    all(
                        cell is None
                        if value is None
                        else type(cell) is Scalar
                        and cell.tag == column.realization.tag
                        and parameters.same_value(cell.value, value)
                        for value, cell, column in zip(
                            row, cells, unit.columns, strict=True
                        )
                    ),
                    "EXPORT_VALUES_ROW",
                )
            return
        producer = expected_producer(unit.scan)
        producer_address = source_map.get(id(producer), unit_map.get(id(producer)))
        uses = tuple(r for r in grouped["use"] if r.get("consumer") == record.address)
        need(
            len(uses) == 1 and uses[0].get("producer") == producer_address,
            "EXPORT_INPUT",
        )
        use = uses[0].address
        definitions = {}
        if record.address.kind == "window":
            if type(unit) is not sql.RowBody:
                raise CompiledError("COMPILED_EXPORT_WINDOW_STAGE")
            stage = unit.window
            need(
                type(stage) is windowing.WindowStage
                and len(record.get("definitions")) == len(stage.definitions),
                "EXPORT_WINDOW_STAGE",
            )
            definitions = {
                id(d.symbol): a
                for a, d in zip(
                    record.get("definitions"), stage.definitions, strict=True
                )
            }
            for a, d in zip(record.get("definitions"), stage.definitions, strict=True):
                described = records[a]
                need(
                    (described.get("ordinal"), described.get("label"))
                    == (d.index, d.label),
                    "EXPORT_WINDOW_DEFINITION",
                )
                columns = tuple(
                    c for c in stage.columns if c.specification.symbol is d.symbol
                )
                need(bool(columns), "EXPORT_WINDOW_UNUSED_DEFINITION")
                policy = next(
                    p
                    for p in original.plan.window_policies
                    if p.ref is columns[0].window.policy
                )
                check_window_spec(
                    described.get("specification"),
                    d.specification,
                    policy,
                    producer,
                    use,
                    definitions,
                )
        # The original terminal remains positional even when labels repeat.
        need(len(record.get("outputs")) == len(unit.columns), "EXPORT_COLUMNS")
        for address, actual in zip(record.get("outputs"), unit.columns, strict=True):
            port = records[address]
            need(port.get("label") == actual.label, "EXPORT_COLUMN_LABEL")
            if isinstance(
                actual,
                (
                    sql.RowCarryColumn,
                    results.ResultColumn,
                    grouping.AggregateKeyColumn,
                    grouping.AggregateProjectionColumn,
                    windowing.WindowProjectionColumn,
                ),
            ):
                check_read(port.get("source"), actual.read, producer, use)
            elif type(actual) is windowing.WindowColumn:
                value = records[port.get("source")]
                need(
                    value.address.kind == "window_value"
                    and value.get("function") == actual.function
                    and value.get("selected") is actual.selected
                    and len(value.get("inputs")) == len(actual.inputs)
                    and len(value.get("arguments")) == len(actual.arguments),
                    "EXPORT_WINDOW_VALUE",
                )
                arguments = tuple(
                    a
                    for a in original.plan.window_arguments
                    if a.window is actual.window.ref
                )
                for (role, a), item, source in zip(
                    value.get("arguments"), actual.arguments, arguments, strict=True
                ):
                    need(
                        role == item.role == source.role.value,
                        "EXPORT_WINDOW_ARGUMENT_ROLE",
                    )
                    if item.parameter is not None:
                        # The read record of this argument's own native use.
                        leaf = item.parameter
                        need(
                            source.parameter is not None
                            and leaf.original is source
                            and leaf.use.original is source
                            and leaf.use.parameter is source.parameter
                            and records[a].address.kind == "parameter_read"
                            and records[a].get("parameter")
                            == Address("parameter", source.parameter.ordinal)
                            and any(
                                u is leaf.use and records[native].get("slot") == a
                                for u, native in zip(
                                    artifact.parameter_uses,
                                    (r.address for r in grouped["native_use"]),
                                    strict=True,
                                )
                            ),
                            "EXPORT_WINDOW_PARAMETER",
                        )
                    elif item.read is not None:
                        check_read(a, item.read, producer, use)
                    else:
                        site_positions = tuple(
                            i
                            for i, site in enumerate(original.plan.literal_sites)
                            if site.position.literal is source.expression
                        )
                        need(
                            len(site_positions) == 1
                            and records[a].get("site")
                            == Address("site", site_positions[0]),
                            "EXPORT_WINDOW_ARGUMENT_SITE",
                        )
                policy = next(
                    p
                    for p in original.plan.window_policies
                    if p.ref is actual.window.policy
                )
                check_window_spec(
                    value.get("specification"),
                    actual.specification,
                    policy,
                    producer,
                    use,
                    definitions,
                )
            elif type(actual) is grouping.AggregateValueColumn:
                value = records[port.get("source")]
                need(
                    value.address.kind == "aggregate_value"
                    and value.get("function") == actual.function
                    and len(value.get("arguments"))
                    == (0 if actual.argument is None else 1),
                    "EXPORT_AGGREGATE",
                )
                if actual.argument is not None:
                    check_scalar(
                        value.get("arguments")[0], actual.argument, producer, use
                    )
            elif type(actual) is sql.RowValueColumn:
                check_scalar(port.get("source"), actual.value, producer, use)
            elif type(actual) is sql.SQLLiteralColumn:
                if actual.value is None:
                    if isinstance(producer, BoundSource) or actual.producer is None:
                        raise CompiledError("COMPILED_EXPORT_LITERAL_CARRY")
                    read = records[port.get("source")]
                    pointed = records[read.get("port")]
                    positions = tuple(
                        i
                        for i, c in enumerate(producer.columns)
                        if c.export.ref is actual.producer.canonical.ref
                    )
                    need(
                        len(positions) == 1
                        and read.address.kind == "read"
                        and read.get("use") == use
                        and pointed.get("owner") == producer_address
                        and pointed.get("ordinal") == positions[0],
                        "EXPORT_LITERAL_CARRY",
                    )
                else:
                    check_scalar(port.get("source"), actual.value, producer, use)
            elif type(actual) is sql.SQLColumn:
                read = records[port.get("source")]
                pointed = records[read.get("port")]
                if isinstance(producer, BoundSource):
                    positions = tuple(
                        i
                        for i, f in enumerate(producer.fields)
                        if f is actual.source_field
                    )
                else:
                    positions = tuple(
                        i
                        for i, c in enumerate(producer.columns)
                        if c.export.ref is actual.input_port.producer_port
                    )
                need(
                    len(positions) == 1
                    and read.get("use") == use
                    and pointed.get("ordinal") == positions[0],
                    "EXPORT_PROJECTION",
                )
            else:
                raise CompiledError("COMPILED_EXPORT_COLUMN")
        if record.address.kind == "aggregate":
            if type(unit) is not sql.RowBody:
                raise CompiledError("COMPILED_EXPORT_AGGREGATE_STAGE")
            stage = unit.aggregation
            from pietto._project.project_joined_aggregation import (
                ProjectConcreteJoinedAggregation,
            )
            from pietto._project.project_multifact import (
                ProjectCurrentMultiFactRegion,
                ProjectMultiFactConcreteRegion,
            )

            authority = stage.aggregation.authority.source
            risk_law = None
            if type(authority) is ProjectConcreteJoinedAggregation:
                region = authority.input_filter.joined_semantics.multifact_region
                need(
                    type(region)
                    in (ProjectCurrentMultiFactRegion, ProjectMultiFactConcreteRegion),
                    "EXPORT_AGGREGATE_RISK_OWNER",
                )
                risk_law = (
                    "current"
                    if type(region) is ProjectCurrentMultiFactRegion
                    else "relationship"
                )
            need(record.get("risk_law") == risk_law, "EXPORT_AGGREGATE_RISK_LAW")
            need(
                type(stage) is grouping.AggregateStage
                and record.get("mode") == stage.mode
                and stage.empty_input
                == ("no_groups" if stage.mode == "grouped" else "one_global_row")
                and len(record.get("keys")) == len(stage.keys)
                and len(record.get("values")) == len(stage.values)
                and tuple(stage.keys) + tuple(stage.values) == unit.columns,
                "EXPORT_AGGREGATE_STAGE",
            )
        if record.address.kind == "result":
            if type(unit) is not results.RowResultBody:
                raise CompiledError("COMPILED_EXPORT_RESULT_BODY")
            need(
                record.get("distinct") is (unit.distinct is not None),
                "EXPORT_DISTINCT",
            )
            need(
                record.get("limit")
                == (None if unit.limit is None else unit.limit.value),
                "EXPORT_LIMIT",
            )
            if unit.limit is not None:
                literal = records[record.get("limit_literal")]
                site = original.plan.literal_sites[literal.get("site").position]
                need(
                    site.position.literal is unit.limit.limit.literal,
                    "EXPORT_LIMIT_SITE",
                )
            expected_order = () if unit.order is None else unit.order.items
            need(len(record.get("ordering")) == len(expected_order), "EXPORT_ORDER")
            for described, actual_order in zip(
                record.get("ordering"), expected_order, strict=True
            ):
                need(
                    described[1] == actual_order.direction
                    and actual_order.nulls is None,
                    "EXPORT_ORDER_ITEM",
                )
                check_read(described[0], actual_order.read, producer, use)
        predicate = getattr(unit, "predicate", None)
        if record.address.kind == "row":
            need(
                (record.get("predicate") is None) == (predicate is None),
                "EXPORT_PREDICATE",
            )
            if predicate is not None:
                check_scalar(record.get("predicate"), predicate.value, producer, use)

    for record, unit in zip(described_units, units, strict=True):
        check_unit(record, unit)
    need(
        inline_seen == inline_units
        and capture_seen == {r.address for r in grouped["capture_use"]},
        "EXPORT_INLINE_INVENTORY",
    )
    entry = records[description.query]
    reached_owners = tuple(d.entry.owner for d in original.plan.bindings.definitions)
    requests = tuple(
        r
        for r in original.verification.completed.single_match_requests
        if any(r.owner is owner for owner in reached_owners)
    )
    need(len(entry.get("requests")) == len(requests), "EXPORT_REQUESTS")
    request_ids, use_ids, path_ids = {}, {}, {}
    for address, request in zip(entry.get("requests"), requests, strict=True):
        record = records[address]
        previous = request_ids.setdefault(id(request), address)
        need(
            previous == address
            and all(
                id(other) == id(request) or a != address
                for a, other in zip(entry.get("requests"), requests, strict=True)
            ),
            "EXPORT_REQUEST_ALIAS",
        )
        check_declaration(record.get("owner"), request.owner)
        use = records[record.get("use")]
        previous_use = use_ids.setdefault(id(request.use), use.address)
        need(
            previous_use == use.address
            and record.get("scope") == request.scope.value
            and record.get("unit") == request.unit.value,
            "EXPORT_REQUEST_KIND",
        )
        originals = tuple(
            o for o in original.plan.single_matches if o.request is request
        )
        need(bool(originals), "EXPORT_RETAINED_REQUEST_SCOPE")
        obligation = originals[0]
        condition = obligation.assessment.condition
        need(condition is not None, "EXPORT_REQUEST_CONDITION")
        from pietto._project.project_single_match import _boundaries

        boundaries = _boundaries(
            original.verification.completed.effective_outputs, condition
        )
        expected_boundaries = []
        for boundary in boundaries:
            units_for_boundary = tuple(
                u
                for u in units
                if type(u) is joining.JoinBody
                and (u.join.source is boundary or u.join.source.source is boundary)
            )
            need(len(units_for_boundary) == 1, "EXPORT_REQUEST_BOUNDARY")
            expected_boundaries.append(unit_map[id(units_for_boundary[0])])
        need(
            use.get("boundaries") == tuple(expected_boundaries),
            "EXPORT_REQUEST_BOUNDARIES",
        )
        authority = (
            original.verification.completed.effective_outputs.operative_conditions
        )
        positions = tuple(i for i, c in enumerate(authority.entries) if c is condition)
        need(positions == (use.get("position"),), "EXPORT_REQUEST_ORDER")
        path = condition.effective_use.path
        need((use.get("path") is None) is (path is None), "EXPORT_REQUEST_PATH")
        if path is not None:
            previous_path = path_ids.setdefault(id(path), use.get("path"))
            need(previous_path == use.get("path"), "EXPORT_PATH_ALIAS")
            described_path = records[use.get("path")]
            need(
                len(described_path.get("steps")) == len(path.steps), "EXPORT_PATH_STEPS"
            )
            for step_address, step in zip(
                described_path.get("steps"), path.steps, strict=True
            ):
                direction = step.guarantee.direction
                declared = direction.declaration
                need(
                    records[step_address].values
                    == (
                        step.position,
                        declared.module.path,
                        declared.module_position,
                        declared.relationship_position,
                        direction.source.identity.endpoint_position,
                        direction.target.identity.endpoint_position,
                    ),
                    "EXPORT_PATH_STEP",
                )
        need(
            (record.get("path") is None) is (request.path is None),
            "EXPORT_REQUEST_PATH_PRESENCE",
        )
        if request.path is not None:
            need(
                record.get("path") == path_ids[id(request.path)],
                "EXPORT_REQUEST_PATH_IDENTITY",
            )
        if request.hop is None:
            need(record.get("hop") is None, "EXPORT_REQUEST_HOP")
        else:
            from pietto._project.project_relationship_paths import (
                ProjectRelationshipPathStep,
            )
            from pietto._project.project_relationship_uses import (
                ProjectTraversalStepUse,
            )

            if type(request.hop) is ProjectRelationshipPathStep:
                if request.path is None:
                    raise CompiledError("COMPILED_EXPORT_REQUEST_HOP")
                candidates = tuple(
                    i for i, s in enumerate(request.path.steps) if s is request.hop
                )
                tag = "path_step"
            else:
                need(type(request.hop) is ProjectTraversalStepUse, "EXPORT_REQUEST_HOP")
                candidates = tuple(
                    i for i, s in enumerate(condition.use.step_uses) if s is request.hop
                )
                tag = "traversal_step"
            need(
                len(candidates) == 1 and record.get("hop") == (tag, candidates[0]),
                "EXPORT_REQUEST_HOP",
            )
    policy = records[Address("policy", 0)]
    need(policy.get("guarded") is (guarded is not None), "EXPORT_GUARD_POLICY")
    if refinement is None:
        need(
            policy.get("refinement") is None and not policy.get("sources"),
            "EXPORT_REFINEMENT_POLICY",
        )
    else:
        from pietto._project.project_refinement_verification import verify_refinement

        verify_refinement(refinement)
        need(
            refinement.original is artifact
            and refinement.output.guarded is guarded
            and policy.get("refinement") == refinement.policy.choice
            and len(policy.get("sources")) == len(refinement.sources),
            "EXPORT_REFINEMENT_ROOT",
        )
        for address, requirement in zip(
            policy.get("sources"), refinement.sources, strict=True
        ):
            need(
                records[address].values
                == (
                    source_map[id(requirement.source)],
                    requirement.provider,
                    requirement.version,
                    requirement.revision,
                    (requirement.registry_namespace, requirement.registry_name),
                    requirement.definition,
                    requirement.token_columns,
                    requirement.role,
                    requirement.provider_guarantee,
                ),
                "EXPORT_PROVIDER_REQUIREMENT",
            )
    verify_requirement_export(records, artifact, check_declaration)
    check_declaration(entry.get("declaration"), original.verification.selected_owner)
    need(
        set(expected_declarations) == {r.address for r in grouped["declaration"]},
        "EXPORT_DECLARATION_INVENTORY",
    )
    need(entry.get("terminal") == unit_map[id(units[-1])], "EXPORT_TERMINAL")
    need(
        tuple(r.get("label") for r in grouped["output"])
        == tuple(c.label for c in view.columns),
        "EXPORT_OUTPUTS",
    )


def _verify_compiled_emission(artifact, request):
    """Original typed SQL carriers checked against the complete compiled plan."""
    import json
    from pietto._project.project_sql_emission import CompiledEmissionArtifact
    from pietto._project.project_guard_preparation import (
        CompiledGuardedArtifact,
        verify_scope,
    )
    from pietto._project.project_sql_emission_contract import (
        CompiledPreparedEmission,
        canonical,
    )
    from pietto._project.project_sql_plan_verification import verify_compiled_sql_plan
    from pietto._project import project_sql_emission_ast as ast
    from pietto._project import project_sql_emission_parameters as parameters
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project.project_query_block_ir import CompiledIRReference
    from pietto._project.project_sql_emission_verification import verify_row_bytes

    need(
        type(artifact) in (CompiledEmissionArtifact, CompiledGuardedArtifact)
        and type(request) is CompiledPreparedEmission
        and artifact.request is request,
        "EMISSION_ROOT",
    )
    plan = request.plan
    verify_compiled_sql_plan(plan)
    records = plan.ir.completed.root.records
    from pietto._project.project_compiled_schema import selected_relations

    active = selected_relations(
        records, records[plan.ir.completed.root.description.query]
    )
    guarded = records[Address("policy", 0)].get("guarded")
    need(
        type(artifact)
        is (CompiledGuardedArtifact if guarded else CompiledEmissionArtifact),
        "EMISSION_GUARD_POLICY",
    )
    if guarded:
        verify_scope(artifact.guard_scope, request)
    else:
        need(
            not any(o.downstream_enforcement_required for o in plan.single_matches),
            "EMISSION_PENDING_GUARD",
        )
    refs = plan.references
    facts = {f.address: f for f in plan.ir.completed.facts}
    target = records[Address("target", 0)]
    need(
        request.accepted_bytes == target.get("contract").encode()
        and (request.family, request.release) == target.values[:2],
        "EMISSION_TARGET",
    )
    document = json.loads(request.accepted_bytes)
    need(
        request.normalized_bytes == canonical(document)
        and document["target"]
        == {"family": request.family, "release": request.release},
        "EMISSION_CONTRACT",
    )
    source_records = tuple(
        r
        for r in records.values()
        if r.address.kind == "source" and r.address in active
    )
    need(
        len(request.sources) == len(source_records) == len(document["sources"]),
        "EMISSION_SOURCES",
    )
    from pietto._project.project_scalar_meaning import verify_scalar_meaning

    has_meaning = any(
        r.address.kind == "field" and r.get("meaning") is not None
        for r in records.values()
    )
    need((request.scalar_meaning is not None) is has_meaning, "EMISSION_MEANING")
    if has_meaning:
        verify_scalar_meaning(request.scalar_meaning, request.verification)
    sources = {}
    for position, (source, record, contract) in enumerate(
        zip(request.sources, source_records, document["sources"], strict=True)
    ):
        need(
            source.owner is plan.sources[position].source.owner
            and source.position == position
            and source.namespace
            == record.get("namespace")
            == contract["relation"]["namespace"]
            and source.name == record.get("name") == contract["relation"]["name"]
            and source.selector == canonical(contract["selector"]),
            "EMISSION_SOURCE",
        )
        fields = record.get("fields")
        ports = tuple(
            r
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == record.address
        )
        need(
            len(source.fields) == len(fields) == len(ports) == len(contract["fields"]),
            "EMISSION_FIELDS",
        )
        for ordinal, (field, address, port, configured) in enumerate(
            zip(source.fields, fields, ports, contract["fields"], strict=True)
        ):
            described = records[address]
            need(
                field.ordinal == ordinal == described.get("ordinal")
                and field.name == described.get("label") == configured["name"]
                and field.column == described.get("column") == configured["column"]
                and field.field is plan.ports[port.address].field
                and field.representation == described.get("physical").encode()
                and json.loads(field.representation) == configured["representation"]
                and field.scalar_meaning is request.scalar_meaning
                and (
                    None
                    if field.decimal is None
                    else (field.decimal.precision, field.decimal.scale)
                )
                == described.get("decimal"),
                "EMISSION_FIELD",
            )
        sources[record.address] = source
    premise_records = tuple(r for r in records.values() if r.address.kind == "premise")
    need(len(request.premises) == len(premise_records), "EMISSION_PREMISES")
    declarations = {d.address: d for d in plan.ir.completed.declarations}
    for actual, record in zip(request.premises, premise_records, strict=True):
        scope = record.get("scope")
        if scope == "statement":
            need(actual.scope == "statement", "EMISSION_PREMISE_SCOPE")
        elif type(scope) is tuple:
            need(
                type(actual.scope) is tuple
                and len(actual.scope) == 2
                and actual.scope[0] is declarations[scope[0]]
                and actual.scope[1] is refs[scope[1]],
                "EMISSION_PREMISE_SCOPE",
            )
        else:
            need(actual.scope is declarations[scope], "EMISSION_PREMISE_SCOPE")
        need(
            actual.position == record.get("position")
            and actual.key == record.get("key")
            and actual.value == record.get("value").encode(),
            "EMISSION_PREMISE",
        )
    from pietto._project.project_sql_emission_scopes import ScopeUse, TerminalBinding

    described_uses = tuple(
        r
        for r in records.values()
        if r.address.kind == "use" and r.get("consumer") in active
    )
    need(
        type(request.bindings) is tuple
        and len(request.bindings) == len(described_uses),
        "EMISSION_BINDING_INVENTORY",
    )
    bindings_by_ref = {}
    input_position = 0
    definitions = {d.ref: d for d in plan.definitions}
    for binding, record in zip(request.bindings, described_uses, strict=True):
        need(
            type(binding) is ScopeUse
            and binding.original.ref is refs[record.address]
            and binding.producer.original is definitions[refs[record.get("producer")]]
            and binding.consumer.original is definitions[refs[record.get("consumer")]],
            "EMISSION_BINDING_OWNER",
        )
        need(
            len(binding.bindings) == len(record.get("ports")), "EMISSION_BINDING_PORTS"
        )
        for pair, address in zip(binding.bindings, record.get("ports"), strict=True):
            need(
                type(pair) is TerminalBinding
                and pair.canonical is plan.ports[address]
                and pair.terminal is pair.canonical
                and pair.input_port is not pair.canonical
                and pair.input_port.owner is refs[record.address]
                and pair.input_port.producer_port is pair.canonical.ref
                and pair.input_port.ref.scope is plan.scope
                and pair.input_port.ref.kind == "input_port"
                and pair.input_port.ref.position == input_position,
                "EMISSION_INPUT_PORT",
            )
            input_position += 1
        bindings_by_ref[record.address] = binding

    expected_subjects = set(refs.values()) | {plan.scope}
    expected_subjects.update(
        pair.input_port.ref for use in request.bindings for pair in use.bindings
    )
    from pietto._project.project_compiled_schema import MAX_RECORDS

    extra_keys = set()
    for record in records.values():
        if record.address.kind != "result" or record.address not in active:
            continue
        base = record.address.position * MAX_RECORDS
        boundary_count = (
            int(record.get("distinct"))
            + int(bool(record.get("ordering")))
            + int(record.get("limit") is not None)
        )
        if record.get("distinct"):
            extra_keys.add(("result_distinct", base))
            extra_keys.update(
                ("result_quotient_field", base + i)
                for i in range(len(record.get("outputs")))
            )
        if record.get("ordering"):
            extra_keys.add(("result_order", base))
            extra_keys.update(
                (kind, base + i)
                for kind in (
                    "result_order_item",
                    "result_order_expression",
                    "result_order_use",
                )
                for i in range(len(record.get("ordering")))
            )
        if record.get("limit") is not None:
            extra_keys.add(("result_limit", base))
        extra_keys.update(
            ("result_stage_" + str(stage), base + i)
            for stage in range(boundary_count - 1)
            for i in range(len(record.get("outputs")))
        )
    extra_subjects = tuple(
        r for r in request.origin_subjects if r not in expected_subjects
    )
    need(
        len(extra_subjects) == len(extra_keys)
        and all(
            type(r) is CompiledIRReference and r.scope is plan.scope
            for r in extra_subjects
        ),
        "EMISSION_ORIGIN_INVENTORY",
    )
    need(
        {(r.kind, r.position) for r in extra_subjects} == extra_keys,
        "EMISSION_ORIGIN_INVENTORY",
    )
    extra_by_key = {(r.kind, r.position): r for r in extra_subjects}

    def local_port(use, port):
        record = records[use]
        positions = tuple(
            i for i, candidate in enumerate(record.get("ports")) if candidate == port
        )
        need(len(positions) == 1, "EMISSION_INPUT_PORT")
        return bindings_by_ref[use].bindings[positions[0]].input_port.ref

    query = artifact.ast
    if type(query) is not ast.CompiledSQLQuery or query.request is not request:
        raise CompiledError("COMPILED_EMISSION_QUERY")
    positions = {
        r.address: unit_position(r)
        for r in records.values()
        if "layout" in FIELDS[r.address.kind]
    }
    units = tuple(
        records[a] for a, i in positions.items() if a in active and i is not None
    )
    # An inline let's units have no unit position: they are checked at the
    # read that renders them, over the reading body's input row.
    inline_units = {a for a, i in positions.items() if i is None}
    need(len(query.bodies) == len(units), "EMISSION_UNITS")
    observed_bodies = {}
    used_parameters = []
    current_bodies: list[Any] = []
    capture_scopes: list[tuple[Any, Any, Any, Any]] = []
    captured = captured_reads(records)

    def column_name(body, index):
        # A CTE column is read by its generated name, an inline column by label.
        if body.cte_columns:
            return body.cte_columns[index].name
        return body.columns[index].label

    def check_capture_read(actual, address):
        record = records[address]
        need(bool(capture_scopes), "EMISSION_CAPTURE_SCOPE")
        outer_use, outer_producer, outer_symbol, block_use = capture_scopes[-1]
        port = records[record.get("port")]
        # The read names the record its inline let and line attribute it to.
        attribution = captured.get(address, ())
        need(
            len(attribution) == 1
            and attribution[0][0] == block_use
            and attribution[0][1] is not None
            and type(actual) is rows.SQLCapturedReference
            and actual.original is plan.expressions[address]
            and actual.capture.ref is refs[attribution[0][1]]
            and actual.scope is outer_symbol
            and record.get("use") == outer_use
            and port.get("owner") == outer_producer
            and actual.column.terminal is refs[record.get("port")]
            and actual.realization is facts[address].realization,
            "EMISSION_CAPTURE",
        )
        if outer_producer in sources:
            field = sources[outer_producer].fields[port.get("ordinal")]
            need(
                actual.column.field is field and actual.column.name == field.column,
                "EMISSION_CAPTURE_SOURCE",
            )
        else:
            index = port.get("ordinal")
            need(
                actual.column.name
                == column_name(observed_bodies[outer_producer], index),
                "EMISSION_CAPTURE_STAGE",
            )

    def verify_inline_units(first, terminal, scope, category):
        """An inline let ending in ``terminal``, unit by unit from its innermost
        body, whatever reads it: ``first`` is the unit its read names and
        ``scope`` the reading row; its ORDER BY and LIMIT end it in a result
        unit."""
        addresses = [first]
        while True:
            inputs = tuple(
                r.get("producer")
                for r in records.values()
                if r.address.kind == "use" and r.get("consumer") == addresses[-1]
            )
            need(len(inputs) == 1, "EMISSION_INLINE_USE")
            if inputs[0] not in inline_units:
                break
            addresses.append(inputs[0])
        addresses.reverse()
        chain = ast.inline_chain(terminal)
        need(
            len(chain) == len(addresses)
            and all(ast.inline_body(body) for body in chain)
            and all(a not in observed_bodies for a in addresses),
            category,
        )
        capture_scopes.append(scope)
        try:
            for index, (address, body) in enumerate(zip(addresses, chain, strict=True)):
                verify_unit(index, body, records[address], inline=True)
        finally:
            capture_scopes.pop()

    def check_inline(actual, block_use, use, producer):
        """The inline let a read renders, unit by unit, over its read's row."""
        verify_inline_units(
            block_use.get("producer"),
            actual.target.producer,
            (use, producer, current_bodies[-1].scan.symbol, block_use.address),
            "EMISSION_INLINE",
        )

    def scalar(actual, address, producer, use, join_contexts=None):
        record = records[address]
        expected_original = plan.expressions[address]
        if address.kind == "read" and record.get("role") == "capture":
            need(join_contexts is None, "EMISSION_CAPTURE_SCOPE")
            check_capture_read(actual, address)
        elif address.kind == "read":
            need(record.get("role") == "value", "EMISSION_READ_ROLE")
            if join_contexts is not None:
                use = record.get("use")
                need(use in join_contexts, "EMISSION_MATCH_USE")
                producer, scope = join_contexts[use]
                need(
                    actual.scope is scope and actual.column.scope is scope,
                    "EMISSION_MATCH_SCOPE",
                )
            need(
                type(actual) is rows.SQLStageReference
                and actual.original is expected_original
                and actual.port is local_port(use, record.get("port")),
                "EMISSION_READ",
            )
            port = records[record.get("port")]
            need(
                record.get("use") == use
                and port.get("owner") == producer
                and actual.column.terminal is refs[record.get("port")],
                "EMISSION_READ_OWNER",
            )
            if producer in sources:
                field = sources[producer].fields[port.get("ordinal")]
                need(
                    actual.column.field is field and actual.column.name == field.column,
                    "EMISSION_SOURCE_READ",
                )
            else:
                body = observed_bodies[producer]
                index = port.get("ordinal")
                need(
                    actual.column.realization is body.columns[index].column.realization
                    and actual.column.name == column_name(body, index),
                    "EMISSION_STAGE_READ",
                )
        elif address.kind == "literal":
            need(
                type(actual) is parameters.SQLAnchor
                and actual.original is expected_original
                and actual.physical_type
                == parameters.PHYSICAL[request.family][
                    facts[address].value_type.resolved_type.name
                ],
                "EMISSION_LITERAL",
            )
            leaf = actual.operand
            matches = tuple(
                s
                for s in plan.literal_sites
                if s.position.expression is expected_original.ref
            )
            need(
                len(matches) == 1
                and leaf.original is expected_original
                and leaf.site is matches[0],
                "EMISSION_LITERAL_SITE",
            )
            if type(leaf) is parameters.SQLParameter:
                need(
                    any(leaf.use is u for u in plan.parameter_uses)
                    and leaf.use.original is expected_original
                    and leaf.use.slot is leaf.fixed.slot
                    and any(leaf.fixed is f for f in plan.fixed_envelope.values),
                    "EMISSION_PARAMETER",
                )
                used_parameters.append(leaf.use)
            else:
                need(
                    type(leaf) is parameters.SQLLiteral
                    and parameters.same_value(leaf.value, facts[address].value),
                    "EMISSION_LITERAL_VALUE",
                )
        elif address.kind == "parameter_read":
            parameter = expected_original.parameter
            need(
                type(actual) is rows.SQLParameterRead
                and actual.original is expected_original
                and any(actual.use is u for u in plan.parameter_uses)
                and actual.use.original is expected_original
                and actual.use.slot is None
                and actual.use.parameter is parameter
                and any(parameter is p for p in plan.parameters)
                and actual.physical_type
                == actual.use.physical_type
                == parameters.PHYSICAL[request.family][parameter.tag]
                and actual.realization is facts[address].realization,
                "EMISSION_PARAMETER_READ",
            )
            used_parameters.append(actual.use)
        elif address.kind == "null_literal":
            matches = tuple(
                site
                for site in plan.literal_sites
                if site.position.expression is expected_original.ref
            )
            need(
                type(actual) is parameters.SQLNull
                and actual.original is expected_original
                and len(matches) == 1
                and actual.site is matches[0]
                and expected_original.expression.value is None
                and facts[address].value_type.resolved_type.name
                in {
                    "Bool",
                    "Int",
                    "Float",
                    "Text",
                    "Decimal",
                    "Date",
                    "Timestamp",
                    "UUID",
                }
                and facts[address].value_type.nullability.value == "nullable",
                "EMISSION_NULL_LITERAL",
            )
        else:
            role, token = record.get("operator")
            children = record.get("operands")
            if (role, token) in BLOCK_READ_OPERATORS:
                operand_free = role != "relation_membership"
                described = tuple(
                    r
                    for r in records.values()
                    if r.address.kind == "expression_block_use"
                    and r.get("operation") == address
                )
                need(
                    len(described) == 1 and len(children) == (0 if operand_free else 1),
                    "EMISSION_BLOCK_READ",
                )
                block_use = described[0]
                target = actual.target
                producer_address = block_use.get("producer")
                inline = producer_address in inline_units
                if inline:
                    need(
                        type(actual) is rows.SQLBlockRead
                        and type(target) is rows.SQLBlockTarget
                        and len(actual.operands) == len(children),
                        "EMISSION_BLOCK_READ",
                    )
                    # A membership read renders its left value before the let.
                    for operand, child in zip(actual.operands, children, strict=True):
                        scalar(operand, child, producer, use, join_contexts)
                    check_inline(actual, block_use, use, producer)
                need(
                    type(actual) is rows.SQLBlockRead
                    and actual.original is plan.expression_identities[address]
                    and actual.kind == token
                    and actual.column == block_use.get("column")
                    and len(actual.operands) == len(children)
                    and actual.realization is facts[address].realization
                    and records[use].get("consumer") == block_use.get("consumer")
                    and type(target) is rows.SQLBlockTarget
                    and target.use.ref is refs[block_use.address]
                    and target.symbol.binding is target.use.ref
                    and target.symbol.position == 0
                    and target.symbol.name == f"e{block_use.address.position}"
                    and (
                        target.producer is sources[producer_address]
                        and target.source is not None
                        and target.source.ref is refs[producer_address]
                        if producer_address in sources
                        else target.source is None
                        and target.producer is observed_bodies.get(producer_address)
                    ),
                    "EMISSION_BLOCK_READ",
                )
                if not inline:
                    for operand, child in zip(actual.operands, children, strict=True):
                        scalar(operand, child, producer, use, join_contexts)
                return
            if type(actual) is parameters.SQLUnary:
                need(
                    role == "unary"
                    and len(children) == 1
                    and actual.original is expected_original,
                    "EMISSION_SIGN",
                )
                scalar(actual.operand, children[0], producer, use, join_contexts)
            else:
                kind = {
                    "unary": "sign",
                    "not": "not",
                    "comparison": "comparison",
                    "null_test": "null_test",
                    "between": "between",
                    "scalar_call": "scalar_call",
                    "conditional": "conditional",
                    "membership": "membership",
                    "cast": "cast",
                }.get(role, "logical" if token in ("and", "or") else "arithmetic")
                need(
                    type(actual) is rows.SQLOperation
                    and actual.original is plan.expression_identities[address]
                    and actual.kind == kind
                    and len(actual.operands) == len(children)
                    and actual.realization is facts[address].realization,
                    "EMISSION_OPERATION",
                )
                for position in rows.rendered_operand_order(kind, len(children)):
                    scalar(
                        actual.operands[position],
                        children[position],
                        producer,
                        use,
                        join_contexts,
                    )

    def verify_unit(index, body, record, inline=False):
        current_bodies.append(body)
        try:
            verify_unit_body(index, body, record, inline)
        finally:
            current_bodies.pop()

    def check_lateral(body, record):
        """A LATERAL right input's inline let, unit by unit, over the JOIN's
        left input row (alias and use)."""
        from pietto._project import project_sql_emission_joins as joining

        need(type(body) is joining.JoinBody, "JOIN_UNIT")
        left_use, right_use = record.get("inputs")
        producer = records[right_use].get("producer")
        if producer not in inline_units:
            return
        verify_inline_units(
            producer,
            body.inputs[1].producer,
            (
                left_use,
                records[left_use].get("producer"),
                body.inputs[0].symbol,
                right_use,
            ),
            "EMISSION_LATERAL",
        )

    def verify_unit_body(index, body, record, inline):
        if record.address.kind == "join":
            check_lateral(body, record)
            verify_compiled_join_unit(
                body, record, request, observed_bodies, sources, bindings_by_ref
            )
            if record.get("predicate") is not None:
                contexts = {
                    a: (records[a].get("producer"), item.symbol)
                    for a, item in zip(record.get("inputs"), body.inputs, strict=True)
                }
                scalar(body.predicate, record.get("predicate"), None, None, contexts)
            observed_bodies[record.address] = body
            return
        if record.address.kind == "set":
            verify_compiled_set_unit(
                body, record, request, observed_bodies, sources, bindings_by_ref
            )
            observed_bodies[record.address] = body
            return
        if record.address.kind == "values":
            verify_compiled_values_unit(body, record, request)
            observed_bodies[record.address] = body
            return
        if record.address.kind == "result":
            need(
                (record.get("layout")[-1] is None) is inline
                and (inline or record.get("layout")[-1] == index),
                "EMISSION_UNIT",
            )
            verify_compiled_result_unit(
                body, record, request, observed_bodies, local_port, extra_by_key, index
            )
            observed_bodies[record.address] = body
            return
        need(
            record.address.kind in ("row", "aggregate", "window")
            and type(body) is ast.RowBody,
            "EMISSION_UNIT_KIND",
        )
        name, native_names, alias, final, position = record.get("layout")
        need(
            (position is None) is inline
            and (inline or position == index)
            and index == body.index
            and (not inline or record.address.kind == "row")
            and body.block.ref is refs[record.address]
            and body.block.kind.value
            == (
                record.get("stage")
                if record.address.kind == "row"
                else record.address.kind
            )
            and body.final is final
            and (None if body.symbol is None else body.symbol.name) == name
            and tuple(s.name for s in body.cte_columns) == native_names
            and body.scan.symbol.name == alias,
            "EMISSION_UNIT",
        )
        producer = record.get("input")
        use = record.get("use")
        if producer in sources:
            need(
                type(body.scan) is ast.RowScan
                and body.scan.realization is sources[producer]
                and body.scan.source.ref is refs[producer]
                and body.scan.use.ref is refs[use]
                and body.scan.binding is bindings_by_ref[use],
                "EMISSION_SCAN",
            )
        elif records[producer].get("owner") != record.get("owner"):
            need(
                type(body.scan) is ast.RowNamedUse
                and body.scan.body is observed_bodies[producer]
                and body.scan.use.ref is refs[use]
                and body.scan.binding is bindings_by_ref[use],
                "EMISSION_NAMED_USE",
            )
        else:
            need(
                (
                    (
                        type(body.scan) is ast.RowJoinUse
                        and producer.kind == "join"
                        and body.scan.tail.ref is refs[use]
                    )
                    or (
                        type(body.scan) is ast.RowStageUse
                        and producer.kind != "join"
                        and body.scan.block is body.block
                    )
                )
                and body.scan.body is observed_bodies[producer],
                "EMISSION_DEPENDENCY",
            )
        ports = record.get("outputs")
        need(len(body.columns) == len(ports), "EMISSION_COLUMNS")
        for position, (column, address) in enumerate(
            zip(body.columns, ports, strict=True)
        ):
            port = records[address]
            need(
                column.ordinal == position
                and column.export is plan.ports[address]
                and column.label == port.get("label")
                and column.column.terminal is refs[address]
                and column.column.realization is facts[address].realization,
                "EMISSION_COLUMN",
            )
            expression = port.get("source")
            if type(column) in (ast.RowCarryColumn, grouping.AggregateKeyColumn):
                read = records[expression]
                need(
                    read.address.kind == "read"
                    and column.input_port is local_port(use, read.get("port"))
                    and column.read.terminal is refs[read.get("port")],
                    "EMISSION_CARRY",
                )
                if producer in sources:
                    field = sources[producer].fields[
                        records[read.get("port")].get("ordinal")
                    ]
                    need(
                        column.read.field is field and column.read.name == field.column,
                        "EMISSION_CARRY_SOURCE",
                    )
                else:
                    i = records[read.get("port")].get("ordinal")
                    need(
                        column.read.name == column_name(observed_bodies[producer], i),
                        "EMISSION_CARRY_NAME",
                    )
                if type(column) is grouping.AggregateKeyColumn:
                    need(
                        record.address.kind == "aggregate"
                        and column.key.ref is refs[expression]
                        and grouping.grouping_problem(column.read.realization) is None,
                        "EMISSION_GROUP_KEY",
                    )
                    origin = column.column.aggregate
                    need(
                        type(origin) is grouping.AggregateOrigin
                        and origin.kind == "group_key"
                        and origin.aggregation is body.aggregation.aggregation
                        and origin.result is column.export.ref
                        and origin.inputs == (column.read.terminal,)
                        and origin.key is column.key,
                        "EMISSION_GROUP_ORIGIN",
                    )
            elif type(column) is windowing.WindowColumn:
                need(
                    record.address.kind == "window"
                    and expression.kind == "window_value"
                    and len(column.arguments)
                    == len(records[expression].get("arguments")),
                    "EMISSION_WINDOW_COLUMN",
                )
                # A header-parameter argument is a placeholder leaf in native
                # order; the window stage check covers every other argument.
                for argument, (_, address) in zip(
                    column.arguments, records[expression].get("arguments"), strict=True
                ):
                    if address.kind == "parameter_read":
                        scalar(argument.parameter, address, producer, use)
            elif type(column) is grouping.AggregateValueColumn:
                value = records[expression]
                function = value.get("function")
                need(
                    record.address.kind == "aggregate"
                    and expression.kind == "aggregate_value"
                    and column.aggregate.ref is refs[expression]
                    and column.function == function
                    and column.spelling == grouping.SPELLING[function]
                    and column.distinct is (function in grouping.DISTINCT_FUNCTIONS),
                    "EMISSION_AGGREGATE_VALUE",
                )
                arguments = value.get("arguments")
                need(
                    (column.argument is None) == (not arguments),
                    "EMISSION_AGGREGATE_ARGUMENT",
                )
                if arguments:
                    scalar(column.argument, arguments[0], producer, use)
                    need(
                        grouping.argument_problem(function, column.argument) is None,
                        "EMISSION_AGGREGATE_ARGUMENT",
                    )
                need(
                    column.argument_cast
                    == grouping.argument_cast(
                        request.family, function, column.argument
                    ),
                    "EMISSION_AGGREGATE_CAST",
                )
                origin = column.column.aggregate
                expected_inputs = (
                    (column.argument.column.terminal,)
                    if arguments
                    else tuple(refs[p] for p in records[use].get("ports"))
                )
                need(
                    type(origin) is grouping.AggregateOrigin
                    and origin.kind == "aggregate_result"
                    and origin.aggregation is body.aggregation.aggregation
                    and origin.result is column.export.ref
                    and origin.inputs == expected_inputs
                    and origin.aggregate is column.aggregate
                    and origin.function == function,
                    "EMISSION_AGGREGATE_ORIGIN",
                )
            else:
                need(type(column) is ast.RowValueColumn, "EMISSION_VALUE_COLUMN")
                scalar(column.value, expression, producer, use)
        if record.address.kind == "aggregate":
            stage = body.aggregation
            key_count = len(record.get("keys"))
            need(
                type(stage) is grouping.AggregateStage
                and stage.aggregation.ref is refs[record.address]
                and stage.keys == body.columns[:key_count]
                and stage.values == body.columns[key_count:]
                and stage.mode == record.get("mode")
                and stage.empty_input
                == ("no_groups" if stage.mode == "grouped" else "one_global_row"),
                "EMISSION_AGGREGATE_STAGE",
            )
        else:
            need(body.aggregation is None, "EMISSION_UNEXPECTED_AGGREGATE")
        if record.address.kind == "window":
            verify_compiled_window_stage(
                body, record, request, observed_bodies, sources
            )
        else:
            need(body.window is None, "EMISSION_UNEXPECTED_WINDOW")
        predicate = record.get("predicate") if record.address.kind == "row" else None
        need((body.predicate is None) == (predicate is None), "EMISSION_PREDICATE")
        if predicate is not None:
            if body.predicate is None:
                raise CompiledError("COMPILED_EMISSION_PREDICATE")
            need(
                body.predicate.original.ref is refs[predicate],
                "EMISSION_PREDICATE_ROOT",
            )
            scalar(body.predicate.value, predicate, producer, use)
        observed_bodies[record.address] = body

    for index, (body, record) in enumerate(zip(query.bodies, units, strict=True)):
        verify_unit(index, body, record)
    # Every parameter leaf is checked once; an inline let is checked inside
    # out, so the order is the rendered one.
    need(
        sorted(map(id, used_parameters)) == sorted(map(id, plan.parameter_uses))
        and tuple(leaf.use for leaf in ast.row_parameter_leaves(query))
        == plan.parameter_uses
        and artifact.parameter_uses is plan.parameter_uses
        and artifact.fixed_values is plan.fixed_envelope.values,
        "EMISSION_PARAMETER_INVENTORY",
    )
    from pietto._project.project_sql_plan_requirements import (
        verify_compiled_requirement_report,
        compiled_requirement_rule,
    )

    report = verify_compiled_requirement_report(request.report, request.verification)
    need(
        type(artifact.original_requirements) is tuple
        and len(artifact.original_requirements) == len(report.entries),
        "EMISSION_ORIGINAL_REQUIREMENTS",
    )
    for item, entry in zip(artifact.original_requirements, report.entries, strict=True):
        need(
            type(item) is ast.OriginalRequirement
            and item.entry is entry
            and item.rule
            == compiled_requirement_rule(
                plan, entry, generated_scopes=len(query.units) > 1
            ),
            "EMISSION_ORIGINAL_REQUIREMENT",
        )
    from pietto._project.project_sql_emission_verification import (
        verify_row_generated_requirements,
    )

    need(
        verify_row_generated_requirements(
            request, query, artifact.generated_requirements
        ),
        "EMISSION_GENERATED_REQUIREMENTS",
    )
    need(verify_row_bytes(query, artifact.rendered), "EMISSION_BYTES")
    return ()


def verify_compiled_emission(artifact, request):
    """The complete emission check; repeated checks of these exact objects inside one top-level call rely on the completed one."""
    once(_verify_compiled_emission, artifact, request)
    return ()


def verify_compiled_result_unit(
    body, record, request, produced, local_port, extras, unit_index
):
    """One result unit at ``unit_index``: its unit position, or the block count
    of the inline let whose unnamed projection it orders and limits."""
    from pietto._project.project_sql_emission_results import (
        RowResultBody,
        RowResultUse,
        ResultColumn,
        ResultDistinct,
        ResultOrder,
        ResultLimit,
        CompiledResultBoundary,
        CompiledResultPort,
    )
    from pietto.semantic.relation_limits import valid_resolved_limit

    need(type(body) is RowResultBody, "RESULT_BODY")
    plan, records = request.plan, request.verification.completed.root.records
    producer = record.get("input")
    need(
        producer in produced
        and type(body.scan) is RowResultUse
        and body.scan.body is produced[producer],
        "RESULT_INPUT",
    )
    original = produced[producer]

    def column_name(i):
        # A CTE column is read by its generated name, an inline one by label.
        if original.cte_columns:
            return original.cte_columns[i].name
        return original.columns[i].label

    name, names, alias, final, _ = record.get("layout")
    need(
        body.index == unit_index
        and body.final is final
        and body.scan.symbol.name == alias
        and (None if body.symbol is None else body.symbol.name) == name
        and tuple(c.name for c in body.cte_columns) == names,
        "RESULT_LAYOUT",
    )
    from pietto._project.project_compiled_schema import MAX_RECORDS

    base = record.address.position * MAX_RECORDS
    kinds = tuple(
        k
        for k, enabled in (
            ("result_distinct", record.get("distinct")),
            ("result_order", bool(record.get("ordering"))),
            ("result_limit", record.get("limit") is not None),
        )
        if enabled
    )
    need(len(body.boundaries) == len(kinds), "RESULT_BOUNDARIES")
    for boundary, kind in zip(body.boundaries, kinds, strict=True):
        need(
            type(boundary) is CompiledResultBoundary
            and boundary.ref is extras[kind, base],
            "RESULT_BOUNDARY",
        )
    need(body.scan.boundary is body.boundaries[0], "RESULT_SCAN")
    need((body.distinct is None) is (not record.get("distinct")), "RESULT_DISTINCT")
    if body.distinct is not None:
        need(
            type(body.distinct) is ResultDistinct
            and body.distinct.distinct.ref is extras["result_distinct", base]
            and len(body.distinct.fields) == len(record.get("outputs"))
            and all(
                type(field) is CompiledResultPort
                and field.ref is extras["result_quotient_field", base + i]
                and field.source is plan.ports[p]
                and field.ordinal == i
                for i, (field, p) in enumerate(
                    zip(body.distinct.fields, record.get("outputs"), strict=True)
                )
            ),
            "RESULT_DISTINCT_FIELDS",
        )
    if record.get("limit") is None:
        need(body.limit is None, "RESULT_LIMIT")
    else:
        need(
            valid_resolved_limit(record.get("limit"))
            and type(body.limit) is ResultLimit
            and body.limit.value == body.limit.limit.value == record.get("limit")
            and body.limit.limit.ref is extras["result_limit", base],
            "RESULT_LIMIT",
        )
    need(len(body.columns) == len(record.get("outputs")), "RESULT_COLUMNS")
    facts = {f.address: f for f in plan.ir.completed.facts}
    for position, (column, address) in enumerate(
        zip(body.columns, record.get("outputs"), strict=True)
    ):
        port = records[address]
        read = records[port.get("source")]
        input_port = plan.ports[read.get("port")]
        i = records[read.get("port")].get("ordinal")
        need(
            type(column) is ResultColumn
            and column.ordinal == position
            and column.export is plan.ports[address]
            and column.projection_port is input_port
            and column.output is column.export
            and column.read.terminal is input_port.ref
            and column.read.name == column_name(i)
            and column.column.realization is facts[address].realization,
            "RESULT_COLUMN",
        )
        need(
            len(column.stages) == len(body.boundaries)
            and all(
                stage.boundary is boundary
                and stage.input_port
                is (input_port if i == 0 else column.stages[i - 1].output_port)
                and (
                    stage.output_port is column.export
                    if i == len(body.boundaries) - 1
                    else type(stage.output_port) is CompiledResultPort
                    and stage.output_port.ref
                    is extras["result_stage_" + str(i), base + position]
                    and stage.output_port.source is stage.input_port
                    and stage.output_port.ordinal == position
                )
                and stage.quotient_field
                is (
                    body.distinct.fields[position]
                    if body.distinct is not None and boundary is body.distinct.boundary
                    else None
                )
                for i, (stage, boundary) in enumerate(
                    zip(column.stages, body.boundaries, strict=True)
                )
            ),
            "RESULT_STAGES",
        )
    ordering = record.get("ordering")
    if not ordering:
        need(body.order is None, "RESULT_ORDER")
    else:
        need(
            type(body.order) is ResultOrder
            and body.order.order.ref is extras["result_order", base]
            and len(body.order.items) == len(ordering),
            "RESULT_ORDER",
        )
        for position, (item, described) in enumerate(
            zip(body.order.items, ordering, strict=True)
        ):
            read = records[described[0]]
            port = plan.ports[read.get("port")]
            i = records[read.get("port")].get("ordinal")
            need(
                item.position == position
                and item.item.ref is extras["result_order_item", base + position]
                and item.expression.ref
                is extras["result_order_expression", base + position]
                and (
                    item.use is None
                    or item.use.ref is extras["result_order_use", base + position]
                )
                and item.port is port
                and item.read.terminal is port.ref
                and item.read.name == column_name(i)
                and item.direction == described[1]
                and item.nulls is None,
                "RESULT_ORDER_ITEM",
            )


def verify_compiled_window_stage(body, record, request, produced, sources):
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project.project_sql_emission_verification import (
        _window_result_realization,
    )
    from pietto.semantic.window_semantics import WindowFrameExclusion

    plan = request.plan
    records, refs = plan.ir.completed.root.records, plan.references
    facts = {f.address: f for f in plan.ir.completed.facts}
    stage = body.window
    need(
        type(stage) is windowing.WindowStage and stage.ref is refs[record.address],
        "WINDOW_STAGE",
    )
    producer, use = record.get("input"), record.get("use")
    need(len(stage.definitions) == len(record.get("definitions")), "WINDOW_DEFINITIONS")
    definitions = dict(zip(record.get("definitions"), stage.definitions, strict=True))

    def check_read(actual, address):
        described = records[address]
        port = records[described.get("port")]
        ordinal = port.get("ordinal")
        need(
            address.kind == "read"
            and described.get("use") == use
            and port.get("owner") == producer
            and actual.terminal is refs[port.address]
            and actual.realization is facts[address].realization,
            "WINDOW_READ",
        )
        if producer in sources:
            field = sources[producer].fields[ordinal]
            need(
                actual.field is field
                and actual.name == field.column
                and actual.aggregate is None
                and actual.window is None
                and actual.literal is None,
                "WINDOW_SOURCE_READ",
            )
        else:
            parent = produced[producer]
            expected = parent.columns[ordinal].column
            need(
                actual.name == parent.cte_columns[ordinal].name
                and actual.field is expected.field
                and actual.literal is expected.literal
                and actual.aggregate is expected.aggregate
                and actual.window is expected.window,
                "WINDOW_PRODUCER_READ",
            )

    def check_spec(actual, address):
        described = records[address]
        need(
            type(actual) is windowing.WindowSpecification
            and actual.parent is None
            and len(actual.partitions) == len(described.get("partition"))
            and len(actual.orders) == len(described.get("ordering")),
            "WINDOW_SPEC",
        )
        for (binding, read), a in zip(
            actual.partitions, described.get("partition"), strict=True
        ):
            need(binding.ref is refs[a], "WINDOW_PARTITION_BINDING")
            check_read(read, a)
            need(
                read.realization.tag in windowing.ORDER_TAGS, "WINDOW_PARTITION_DOMAIN"
            )
        for i, (item, (a, direction, nulls)) in enumerate(
            zip(actual.orders, described.get("ordering"), strict=True)
        ):
            need(
                type(item) is windowing.WindowOrderItem
                and item.position == i
                and item.binding.ref is refs[a]
                and item.direction == direction
                and item.nulls is nulls is None
                and item.read.realization.tag in windowing.ORDER_TAGS,
                "WINDOW_ORDER_ITEM",
            )
            check_read(item.read, a)
        frame = described.get("frame")
        need((actual.frame is None) == (frame is None), "WINDOW_FRAME")
        if frame is not None:
            bounds, offsets = [], []
            for kind, address in frame[1:3]:
                if address is None:
                    bounds.append((kind, windowing.BOUND_SPELLING[kind]))
                else:
                    number = records[address].get("value").value
                    need(
                        type(number) is int and 0 <= number <= windowing.I64_MAX,
                        "WINDOW_FRAME_OFFSET",
                    )
                    bounds.append(
                        (kind, str(number) + " " + windowing.OFFSET_BOUNDS[kind])
                    )
                    offsets.append((kind, number))
            need(
                type(actual.frame) is windowing.WindowFrameSpec
                and actual.frame.unit == frame[0]
                and (actual.frame.start, actual.frame.end) == tuple(bounds)
                and actual.frame.exclusion
                == (None if frame[3] is None else WindowFrameExclusion(frame[3]))
                and windowing.frame_problem(actual.frame, request.family) is None
                and windowing.offset_range_problem(actual.frame, actual.orders) is None
                and windowing.range_arithmetic_problem(
                    actual.frame, offsets, actual.orders
                )
                is None,
                "WINDOW_FRAME_DOMAIN",
            )
        named = described.get("named")
        need(
            actual.symbol is (None if named is None else definitions[named].symbol),
            "WINDOW_NAMED_REFERENCE",
        )
        if named is not None:
            need(
                windowing.same_specification(actual, definitions[named].specification),
                "WINDOW_NAMED_SPEC",
            )

    for address, definition in definitions.items():
        described = records[address]
        need(
            type(definition) is windowing.WindowDefinition
            and definition.index == described.get("ordinal")
            and definition.label == definition.symbol.name == described.get("label")
            and definition.symbol.binding is refs[address]
            and definition.named_use.ref is refs[address],
            "WINDOW_DEFINITION",
        )
        check_spec(definition.specification, described.get("specification"))
    expected_columns = tuple(
        c for c in body.columns if type(c) is windowing.WindowColumn
    )
    need(
        stage.columns == expected_columns
        and windowing.resource_problem(request.family, len(stage.columns)) is None,
        "WINDOW_COLUMN_INVENTORY",
    )
    for column in stage.columns:
        port = records[record.get("outputs")[column.ordinal]]
        value = records[port.get("source")]
        function = value.get("function")
        static = dict(
            windowing.resolved_arguments(
                function, value.get("arguments"), records, request.family
            )
        )
        need(
            column.window.ref is refs[value.address]
            and column.function == function
            and column.selected is value.get("selected")
            and len(column.arguments) == len(value.get("arguments"))
            and column.inputs == tuple(refs[a] for a in value.get("inputs")),
            "WINDOW_COLUMN",
        )
        for i, (argument, (role, address)) in enumerate(
            zip(column.arguments, value.get("arguments"), strict=True)
        ):
            need(
                type(argument) is windowing.WindowArgument
                and argument.position == i
                and argument.role == role,
                "WINDOW_ARGUMENT",
            )
            if address.kind == "parameter_read":
                # The leaf itself is checked with the unit's native uses.
                need(
                    argument.literal is None
                    and argument.read is None
                    and argument.parameter is not None
                    and (type(static.get(role)) is windowing.ParameterStatic)
                    == (role != "value"),
                    "WINDOW_PARAMETER_ARGUMENT",
                )
            elif role == "value":
                need(
                    argument.literal is None and argument.read is not None,
                    "WINDOW_VALUE_ARGUMENT",
                )
                check_read(argument.read, address)
            else:
                need(
                    argument.read is None
                    and argument.literal
                    == ("NULL" if static[role] is None else str(static[role])),
                    "WINDOW_STATIC_ARGUMENT",
                )
        check_spec(column.specification, value.get("specification"))
        need(
            (column.specification.frame is None)
            is (function in windowing.FRAME_INSENSITIVE),
            "WINDOW_FRAME_APPLICABILITY",
        )
        fact = facts[port.address]
        expected = _window_result_realization(
            request.family,
            function,
            column.arguments,
            (fact.realization.tag, fact.realization.nullable),
        )
        actual = column.column.realization
        need(
            (actual.tag, actual.storage, actual.nullable, actual.domain)
            == (expected.tag, expected.storage, expected.nullable, expected.domain),
            "WINDOW_REALIZATION",
        )
        origin = column.column.window
        need(
            type(origin) is windowing.WindowOrigin
            and origin.kind == "window_result"
            and origin.window is column.window
            and origin.result is column.export.ref
            and origin.inputs == column.inputs
            and origin.function == function
            and origin.selected is column.selected
            and origin.policy.ref is refs[value.get("specification")]
            and column.column.field is None
            and column.column.aggregate is None
            and column.column.literal is None,
            "WINDOW_ORIGIN",
        )


def verify_compiled_set_unit(body, record, request, produced, sources, bindings):
    from pietto._project import project_sql_emission_sets as setting
    from pietto._project.project_sql_emission_verification import (
        resolved_set_column_realization,
    )
    from pietto._project.project_row_equivalence import (
        resolved_builtin_equivalence_reason,
    )

    plan = request.plan
    records, refs = plan.ir.completed.root.records, plan.references
    facts = {f.address: f for f in plan.ir.completed.facts}
    name, labels, aliases, final, index = record.get("layout")
    need(
        type(body) is setting.SetBody
        and type(body.body) is setting.CompiledSetBodySubject
        and body.body.ref is refs[record.address]
        and body.body.kind is body.kind
        and body.body.quantifier is body.quantifier
        and body.body.requires_equivalence
        is (record.get("kind") != "union" or record.get("quantifier") == "distinct")
        and body.body.fold == "source_order_left_fold"
        and body.index == index
        and body.final is final
        and body.kind.value == record.get("kind")
        and body.quantifier.value == record.get("quantifier")
        and (None if body.symbol is None else body.symbol.name) == name
        and tuple(c.name for c in body.cte_columns) == labels
        and len(body.operands) == len(record.get("operands")),
        "SET_UNIT",
    )
    for ordinal, (operand, address) in enumerate(
        zip(body.operands, record.get("operands"), strict=True)
    ):
        use = records[address]
        producer = use.get("producer")
        expected_producer = sources.get(producer, produced.get(producer))
        need(
            type(operand) is setting.SetOperandBody
            and operand.position == ordinal
            and operand.operand.ref is refs[address]
            and operand.use is bindings[address]
            and operand.producer is expected_producer
            and operand.symbol.name == aliases[ordinal]
            and operand.symbol.binding is refs[address]
            and len(operand.columns) == len(use.get("ports")) == len(operand.inputs),
            "SET_OPERAND",
        )
        if producer in sources:
            need(operand.source.ref is refs[producer], "SET_SOURCE")
        else:
            need(operand.source is None, "SET_NAMED_SOURCE")
        for i, (column, a, input_port, binding) in enumerate(
            zip(
                operand.columns,
                use.get("ports"),
                operand.inputs,
                bindings[address].bindings,
                strict=True,
            )
        ):
            need(
                column.terminal is refs[a]
                and column.realization is facts[a].realization
                and input_port is binding.input_port,
                "SET_INPUT",
            )
            if producer in sources:
                field = sources[producer].fields[i]
                need(
                    column.field is field and column.name == field.column,
                    "SET_SOURCE_FIELD",
                )
            else:
                original = produced[producer].columns[i].column
                need(
                    column.name == produced[producer].cte_columns[i].name
                    and column.field is original.field
                    and column.literal is original.literal
                    and column.aggregate is original.aggregate
                    and column.window is original.window,
                    "SET_NAMED_FIELD",
                )
    need(
        len(body.columns) == len(record.get("outputs")) == len(body.terminals),
        "SET_COLUMNS",
    )
    for ordinal, (column, address, terminal) in enumerate(
        zip(body.columns, record.get("outputs"), body.terminals, strict=True)
    ):
        port = plan.ports[address]
        value = records[records[address].get("source")]
        expected_reads = tuple(operand.columns[ordinal] for operand in body.operands)
        fact = facts[address]
        need(
            type(column) is setting.SetColumn
            and column.ordinal == ordinal
            and column.source.ref is refs[value.address]
            and column.export is port
            and column.output is port
            and terminal is port
            and column.label == port.identity.name
            and column.column.terminal is port.ref
            and column.inputs == expected_reads
            and column.realization is column.column.realization is fact.realization,
            "SET_COLUMN",
        )
        expected = resolved_set_column_realization(
            body.kind,
            body.quantifier,
            fact.realization.nullable,
            expected_reads,
            tuple(
                resolved_builtin_equivalence_reason(r.realization.tag)
                for r in expected_reads
            ),
        )
        need(
            (expected.tag, expected.storage, expected.nullable, expected.domain)
            == (
                fact.realization.tag,
                fact.realization.storage,
                fact.realization.nullable,
                fact.realization.domain,
            ),
            "SET_COLUMN_REALIZATION",
        )


def verify_compiled_values_unit(body, record, request):
    """A compiled VALUES unit renders exactly its record's typed fixed rows."""
    from pietto._project import project_sql_emission_values as valuing

    plan = request.plan
    records, refs = plan.ir.completed.root.records, plan.references
    facts = {f.address: f for f in plan.ir.completed.facts}
    name, labels, alias, final, index = record.get("layout")
    rows_record = record.get("rows")
    need(
        type(body) is valuing.ValuesBody
        and type(body.body) is valuing.CompiledValuesSubject
        and body.body.ref is refs[record.address]
        and body.index == index
        and body.final is final
        and (None if body.symbol is None else body.symbol.name) == name
        and tuple(c.name for c in body.cte_columns) == labels
        and body.scope.name == alias
        and body.scope.binding is refs[record.address]
        and len(body.rows) == len(rows_record)
        and all(
            len(actual) == len(expected)
            and all(
                (value is None and cell is None)
                or (
                    type(cell) is Scalar
                    and value is not None
                    and parameters_same(cell.value, value)
                )
                for value, cell in zip(actual, expected, strict=True)
            )
            for actual, expected in zip(body.rows, rows_record, strict=True)
        )
        and len(body.columns)
        == len(record.get("outputs"))
        == len(record.get("fields"))
        == len(body.terminals),
        "VALUES_UNIT",
    )
    for ordinal, (column, field, address, terminal) in enumerate(
        zip(
            body.columns,
            record.get("fields"),
            record.get("outputs"),
            body.terminals,
            strict=True,
        )
    ):
        port = plan.ports[address]
        fact = facts[address]
        need(
            type(column) is valuing.ValuesOutputColumn
            and column.ordinal == ordinal
            and column.source.ref is refs[field]
            and column.source.name == records[field].get("label")
            and column.export is port
            and column.output is port
            and terminal is port
            and column.label == port.identity.name
            and column.symbol.name == column.label
            and column.symbol.binding is port.ref
            and column.column.terminal is port.ref
            and column.realization is column.column.realization is fact.realization
            and column.physical
            == {
                ("postgres", "Bool"): "pg_bool",
                ("postgres", "Int"): "pg_int8",
                ("postgres", "Float"): "pg_float8",
                ("postgres", "Text"): "pg_text",
                ("mysql", "Bool"): "my_signed_bool",
                ("mysql", "Int"): "my_signed_int",
                ("mysql", "Float"): "my_double",
                ("mysql", "Text"): "my_utf8mb4_text",
            }.get((request.family, fact.realization.tag))
            and column.physical == fact.realization.storage.get("kind"),
            "VALUES_COLUMN",
        )


def parameters_same(left, right):
    from pietto._project.project_sql_emission_parameters import same_value

    return same_value(left, right)


def verify_compiled_join_unit(body, record, request, produced, sources, bindings):
    from pietto._project import project_sql_emission_joins as joining
    from pietto.ast_nodes import AuthoredJoinKind

    plan = request.plan
    records, refs = plan.ir.completed.root.records, plan.references
    facts = {f.address: f for f in plan.ir.completed.facts}
    name, labels, aliases, final, index = record.get("layout")
    need(
        type(body) is joining.JoinBody
        and type(body.join) is joining.CompiledJoinSubject
        and body.join.ref is refs[record.address]
        and body.index == index
        and body.join.kind is AuthoredJoinKind(record.get("kind"))
        and final is False
        and body.symbol.name == name
        and body.symbol.binding is body.join.ref
        and tuple(s.name for s in body.cte_columns) == labels
        and len(body.inputs) == len(record.get("inputs")) == 2,
        "JOIN_UNIT",
    )
    by_use = {}
    for ordinal, (address, item) in enumerate(
        zip(record.get("inputs"), body.inputs, strict=True)
    ):
        use = records[address]
        producer = use.get("producer")
        need(
            type(item) is joining.JoinInput
            and type(item.original) is joining.CompiledJoinPart
            and item.original.ref is refs[address]
            and item.ordinal == ordinal
            and item.use is bindings[address]
            and item.producer is sources.get(producer, produced.get(producer))
            and item.symbol.name == aliases[ordinal]
            and item.symbol.binding is refs[address]
            and item.source is (refs[producer] if producer in sources else None)
            and item.ports
            == tuple(b.input_port.ref for b in bindings[address].bindings)
            and len(item.columns) == len(use.get("ports")),
            "JOIN_INPUT",
        )
        for i, (column, port) in enumerate(
            zip(item.columns, use.get("ports"), strict=True)
        ):
            need(
                column.terminal is refs[port]
                and column.realization is facts[port].realization
                and column.scope is item.symbol,
                "JOIN_INPUT_COLUMN",
            )
            if producer in sources:
                field = sources[producer].fields[i]
                need(
                    column.field is field and column.name == field.column,
                    "JOIN_SOURCE_COLUMN",
                )
            else:
                expected = produced[producer].columns[i].column
                # A LATERAL inline let publishes its columns by their labels.
                named = produced[producer].cte_columns
                need(
                    column.name
                    == (named[i].name if named else produced[producer].columns[i].label)
                    and column.field is expected.field
                    and column.literal is expected.literal
                    and column.aggregate is expected.aggregate
                    and column.window is expected.window,
                    "JOIN_PRODUCER_COLUMN",
                )
        by_use[address] = item

    def read(address):
        described = records[address]
        source = by_use[described.get("use")]
        ordinal = records[described.get("port")].get("ordinal")
        return source, source.columns[ordinal], source.use.bindings[ordinal].input_port

    need(len(body.equalities) == len(record.get("equalities")), "JOIN_EQUALITIES")
    for address, equality in zip(
        record.get("equalities"), body.equalities, strict=True
    ):
        described = records[address]
        left, left_column, left_port = read(described.get("left"))
        right, right_column, right_port = read(described.get("right"))
        need(
            type(equality) is joining.JoinEquality
            and equality.original.ref is refs[address]
            and equality.left is left_column
            and equality.right is right_column
            and equality.left_port is left_port.ref
            and equality.right_port is right_port.ref
            and equality.left_scope is left.symbol
            and equality.right_scope is right.symbol
            and left_column.realization.tag == right_column.realization.tag,
            "JOIN_EQUALITY",
        )
    predicate = record.get("predicate")
    need(
        (body.predicate is None) is (predicate is None)
        and body.join.on is (None if predicate is None else refs[predicate]),
        "JOIN_PREDICATE",
    )
    kind = body.join.kind
    need(
        (kind is AuthoredJoinKind.CROSS)
        is (body.predicate is None and not body.equalities),
        "JOIN_CONDITION",
    )
    if kind is AuthoredJoinKind.FULL:
        need(
            joining.full_admissible(
                body.join, body.equalities, body.predicate, request.family
            )
            is None,
            "JOIN_FULL_DOMAIN",
        )
    membership = joining.MEMBERSHIP.get(kind)
    need(
        body.membership == membership
        and body.sentinel is (None if membership is None else body.join.ref),
        "JOIN_MEMBERSHIP",
    )
    rejected = joining.null_rejected_ports(body.join, body.equalities, body.predicate)
    need(len(body.columns) == len(record.get("outputs")), "JOIN_COLUMNS")
    for position, (address, column) in enumerate(
        zip(record.get("outputs"), body.columns, strict=True)
    ):
        port = plan.ports[address]
        value = records[records[address].get("source")]
        source, expected_read, match = read(value.get("input"))
        fact = facts[address]
        expected, problem = joining.resolved_port_realization(
            fact.realization.tag,
            fact.realization.nullable,
            expected_read.realization,
            outer=True,
            proved=match.ref in rejected,
        )
        need(
            type(column) is joining.JoinColumn
            and column.position == position
            and column.port is port
            and column.match is match
            and column.scope is source.symbol
            and column.read is expected_read
            and column.label == port.identity.name
            and column.symbol.binding is port.ref
            and column.symbol.name == column.label
            and column.column.terminal is port.ref
            and column.column.scope is None
            and column.column.realization is fact.realization
            and column.column.field is expected_read.field
            and column.column.literal is expected_read.literal
            and column.column.aggregate is expected_read.aggregate
            and column.column.window is expected_read.window,
            "JOIN_COLUMN",
        )
        need(
            expected is not None
            and problem is None
            and (expected.tag, expected.storage, expected.nullable, expected.domain)
            == (
                fact.realization.tag,
                fact.realization.storage,
                fact.realization.nullable,
                fact.realization.domain,
            ),
            "JOIN_REALIZATION",
        )


def verify_requirement_export(records, artifact, check_declaration):
    """Read the complete original producer graph, independently of export maps."""
    from pietto._project import project_sql_emission_parameters as parameters

    plan, report = artifact.request.plan, artifact.request.report.report
    origins = tuple(
        r for r in records.values() if r.address.kind == "requirement_origin"
    )
    demands = tuple(r for r in records.values() if r.address.kind == "requirement")
    links = tuple(r for r in records.values() if r.address.kind == "requirement_link")
    need(
        len(origins) == len(plan.origins)
        and len(demands) == len(report.entries)
        and len(links) == len(report.links),
        "EXPORT_REQUIREMENT_INVENTORY",
    )

    def reference(value):
        return (
            ("scope", 0) if value is plan.scope else (value.kind.value, value.position)
        )

    for described, actual in zip(origins, plan.origins, strict=True):
        span = actual.cause.span
        check_declaration(described.get("owner"), actual.owner)
        need(
            described.address.position == actual.ref.position
            and described.get("subject") == reference(actual.subject)
            and described.get("role") == actual.role.value
            and described.get("provenance") == actual.provenance.value
            and described.get("location")
            == (span.path, span.line, span.column, span.end_line, span.end_column)
            and described.get("antecedents")
            == tuple(reference(a) for a in actual.antecedents),
            "EXPORT_REQUIREMENT_ORIGIN",
        )
    for described, actual in zip(demands, report.entries, strict=True):
        need(
            described.values[:7]
            == (
                actual.family.value,
                None if actual.subkind is None else actual.subkind.value,
                reference(actual.subject),
                reference(actual.scope.definition),
                tuple(reference(s) for s in actual.scope.stages),
                tuple(reference(u) for u in actual.scope.input_uses),
                Address("requirement_origin", actual.origin.ref.position),
            ),
            "EXPORT_REQUIREMENT_ENTRY",
        )
        if actual.family.value == "expression":
            expression = plan.expressions[actual.subject.position]
            logical = (
                expression.value_type.resolved_type.name,
                expression.value_type.nullability.value,
            )
            scalar_anchors = tuple(
                records[a]
                for a in described.get("anchors")
                if a.kind
                in ("literal", "null_literal", "parameter_read", "read", "operation")
            )
            if not scalar_anchors:
                need(
                    parameters.typed_null(expression),
                    "EXPORT_REQUIREMENT_EXPRESSION_ANCHOR",
                )
            for anchor in scalar_anchors:
                if anchor.address.kind == "literal":
                    expected = (anchor.get("tag"), "non_null")
                elif anchor.address.kind == "null_literal":
                    continue
                elif anchor.address.kind == "read":
                    expected = (
                        captured_logical(records, anchor.address)
                        if anchor.get("role") == "capture"
                        else records[anchor.get("port")].get("logical")
                    )
                elif anchor.address.kind == "parameter_read":
                    declared = records[anchor.get("parameter")]
                    expected = (
                        declared.get("tag"),
                        "nullable" if declared.get("nullable") else "non_null",
                    )
                else:
                    expected = anchor.get("logical")
                need(expected == logical, "EXPORT_REQUIREMENT_EXPRESSION_TYPE")
    for described, actual in zip(links, report.links, strict=True):
        need(
            described.values
            == (
                actual.kind.value,
                Address("requirement", actual.source.position),
                Address("requirement", actual.target.position),
            ),
            "EXPORT_REQUIREMENT_LINK",
        )


def verify_retained_export(description, selected, artifact, requests):
    """The checked selected graph remains exact; every source request survives."""
    from pietto._project.project_compiled_schema import selected_relations

    records = {r.address: r for r in description.records}
    for record in selected.records:
        actual = records.get(record.address)
        if actual is None:
            raise CompiledError("COMPILED_RETAINED_SELECTED_INVENTORY")
        if record.address.kind == "entry":
            need(actual.values[:3] == record.values[:3], "RETAINED_SELECTED_ENTRY")
        else:
            need(actual == record, "RETAINED_SELECTED_INPUT")
    entry = records[description.query]
    need(len(entry.get("requests")) == len(requests), "RETAINED_REQUEST_INVENTORY")
    identities = {}
    for address, request in zip(entry.get("requests"), requests, strict=True):
        record = records[address]
        owner = records[record.get("owner")]
        actual = request.owner
        need(
            owner.values == declaration_values(actual)
            and record.get("scope") == request.scope.value
            and record.get("unit") == request.unit.value,
            "RETAINED_REQUEST_OWNER",
        )
        if id(request) in identities:
            need(identities[id(request)] == address, "RETAINED_REQUEST_ALIAS")
        identities[id(request)] = address
    need(len(set(identities.values())) == len(identities), "RETAINED_REQUEST_MERGE")
    active = selected_relations(records, entry)
    original_records = {r.address: r for r in selected.records}
    need(
        active
        == selected_relations(original_records, original_records[selected.query]),
        "RETAINED_EXECUTION_SCOPE",
    )
    active_owners = {records[a].get("owner") for a in active if a.kind != "source"}
    expected_owners = tuple(
        dict.fromkeys(
            records[a].get("owner")
            for a in entry.get("requests")
            if records[a].get("owner") not in active_owners
        )
    )
    retained_owners = tuple(records[a].get("owner") for a in entry.get("retained"))
    need(
        set(retained_owners) == set(expected_owners)
        and len(retained_owners) == len(expected_owners),
        "RETAINED_OWNER_CLOSURE",
    )


def verify_logical_export(description, checked, references):
    """Compare retained inputs to the actual source plan, without its exporter."""
    from pietto._project.project_sql_plan import ProjectSQLPlan
    from pietto._project import project_sql_plan_expressions as scalar
    from pietto._project.project_sql_plan_aggregation import ProjectSQLResultReference
    from pietto._project.project_sql_plan_windows import ProjectSQLWindowReference
    from pietto._project.project_sql_emission_aggregation import function_name
    from pietto._project.project_sql_emission_contract import source_family
    from pietto._project.project_sql_emission_results import _same_order_expression
    from pietto._project.project_compiled_schema import scalar_wire

    plan = checked.plan
    need(type(plan) is ProjectSQLPlan and checked.verified, "RETAINED_PLAN")
    records = {r.address: r for r in description.records}
    need(len(records) == len(description.records), "RETAINED_RECORD_INVENTORY")
    expected_refs = (
        tuple(s.ref for s in plan.sources)
        + tuple(j.ref for j in plan.joins)
        + tuple(b.ref for b in plan.blocks)
        + tuple(b.ref for b in plan.set_bodies)
        + tuple(b.ref for b in plan.result_boundaries)
    )
    need(set(references) == set(expected_refs), "RETAINED_PLAN_INVENTORY")
    units = {a for a in records if a.kind in RELATIONS}
    result_owners = {b.definition for b in plan.result_boundaries}
    need(
        set(references.values()) == units
        and len(units)
        == len(plan.sources)
        + len(plan.joins)
        + len(plan.blocks)
        + len(plan.set_bodies)
        + len(result_owners),
        "RETAINED_UNIT_INVENTORY",
    )
    for ref in expected_refs:
        need(
            ref.scope is plan.scope and references[ref] in records,
            "RETAINED_PLAN_SCOPE",
        )

    def owner(address, original):
        need(
            records[address].values == declaration_values(original),
            "RETAINED_DECLARATION",
        )

    def logical(field):
        return (field.evidence.resolved_type.name, field.effective_nullability.value)

    sites = tuple(r for r in records.values() if r.address.kind == "site")
    literal_records = tuple(
        r for r in records.values() if r.address.kind in ("literal", "null_literal")
    )
    need(
        len(sites) == len(plan.literal_sites) == len(literal_records),
        "RETAINED_LITERAL_INVENTORY",
    )
    from pietto import ast_nodes as syntax

    ancestry_kinds = {
        syntax.UnaryExpr: "unary",
        syntax.BinaryExpr: "binary",
        syntax.ComparisonExpr: "comparison",
        syntax.IsNullExpr: "null_test",
        syntax.BetweenExpr: "between",
        syntax.CallExpr: "call",
        syntax.ConditionalExpr: "conditional",
        syntax.MembershipExpr: "membership",
        syntax.RelationMembershipExpr: "relation_membership",
        syntax.CastExpr: "cast",
    }
    literal_addresses = {}
    for ordinal, (site, literal, original) in enumerate(
        zip(sites, literal_records, plan.literal_sites, strict=True)
    ):
        position = original.position
        owner(site.get("owner"), position.owner)
        need(
            site.get("role") == position.role.value
            and site.get("ordinal") == ordinal
            and literal.get("site") == site.address
            and site.get("disposition") == original.disposition.value,
            "RETAINED_LITERAL_SITE",
        )
        need(
            site.get("ancestry")
            == tuple(
                (ancestry_kinds[type(parent)], ordinal)
                for parent, ordinal in position.ancestry
            )
            and site.get("reason")
            == (None if original.reason is None else original.reason.value),
            "RETAINED_LITERAL_ANCESTRY",
        )
        raw = position.literal.value
        if raw is None:
            need(literal.address.kind == "null_literal", "RETAINED_LITERAL_VALUE")
        else:
            expected = Scalar(
                {bool: "Bool", int: "Int", float: "Float", str: "Text"}[type(raw)], raw
            )
            need(
                literal.address.kind == "literal"
                and scalar_wire(literal.get("value")) == scalar_wire(expected),
                "RETAINED_LITERAL_VALUE",
            )
        literal_addresses[id(position.literal)] = literal.address

    ports = {}
    aliases = {
        p.ref: p.producer_port for p in plan.input_ports if p.producer_port is not None
    }
    aliases.update(
        {
            p.ref: p.source
            for p in (*plan.stage_ports, *plan.result_ports, *plan.join_ports)
        }
    )
    expressions = {e.ref: e for e in plan.expressions}
    block_uses = {u.ref: u for u in plan.expression_block_uses}
    read_edges = set()
    terminals = {}
    source_defs = {d.ref: d for d in plan.bindings.definitions}
    captures = {c.ref: c for c in plan.captures}
    captured_definitions = {c.inner for c in plan.captures}
    plan_blocks = {b.ref: b for b in plan.blocks}

    def port(reference):
        visited = set()
        while reference not in ports:
            need(
                reference not in visited and reference in aliases, "RETAINED_PORT_INPUT"
            )
            visited.add(reference)
            reference = aliases[reference]
        return ports[reference]

    def read(address, original, uses):
        record = records[address]
        need(
            record.address.kind == "read"
            and record.get("port") == port(original)
            and record.get("use") in uses
            and record.get("port") in records[record.get("use")].get("ports"),
            "RETAINED_READ_INPUT",
        )
        # Exact MATCH input occurrence matters when two uses share a producer.
        current = original
        join_ports = {p.ref: p for p in plan.join_ports}
        seen = set()
        while current in join_ports and current not in seen:
            seen.add(current)
            item = join_ports[current]
            if item.input is not None:
                original_input = next(
                    i for i in plan.join_inputs if i.ref is item.input
                )
                need(
                    records[record.get("use")].get("ordinal") == original_input.ordinal,
                    "RETAINED_READ_OCCURRENCE",
                )
                break
            current = item.source

    def expression(address, original_ref, uses):
        record, original = records[address], expressions[original_ref]
        need(
            type(original)
            in (
                scalar.ProjectSQLLiteral,
                scalar.ProjectSQLBoundLiteral,
                scalar.ProjectSQLReference,
                scalar.ProjectSQLJoinedReference,
                scalar.ProjectSQLMatchReference,
                ProjectSQLResultReference,
                ProjectSQLWindowReference,
                scalar.ProjectSQLUnary,
                scalar.ProjectSQLBinary,
                scalar.ProjectSQLComparison,
                scalar.ProjectSQLIsNull,
                scalar.ProjectSQLBetween,
                scalar.ProjectSQLScalarCall,
                scalar.ProjectSQLConditional,
                scalar.ProjectSQLMembership,
                scalar.ProjectSQLCast,
                scalar.ProjectSQLRelationExists,
                scalar.ProjectSQLRelationScalar,
                scalar.ProjectSQLRelationMembership,
                scalar.ProjectSQLCapturedField,
            ),
            "RETAINED_EXPRESSION_DOMAIN",
        )
        if type(original) is scalar.ProjectSQLCapturedField:
            # A captured field reads the reading body's input row through
            # that body's own use.
            capture = captures.get(original.capture)
            need(
                capture is not None and original.position in capture.edge.fields,
                "RETAINED_CAPTURE_READ",
            )
            assert capture is not None
            outer = plan_blocks[capture.block]
            reference = capture.ports[capture.edge.fields.index(original.position)]
            outer_uses = tuple(
                r
                for r in records.values()
                if r.address.kind == "use"
                and r.get("consumer") == references.get(capture.block)
            )
            need(
                len(outer_uses) == 1
                and reference in outer.inputs
                and record.address.kind == "read"
                and record.get("role") == "capture"
                and record.get("use") == outer_uses[0].address
                and record.get("port")
                == outer_uses[0].get("ports")[outer.inputs.index(reference)],
                "RETAINED_CAPTURE_READ",
            )
            return
        if isinstance(
            original, (scalar.ProjectSQLLiteral, scalar.ProjectSQLBoundLiteral)
        ):
            if original.expression.value is None:
                need(record.address.kind == "null_literal", "RETAINED_LITERAL")
            else:
                need(
                    record.address.kind == "literal"
                    and scalar_wire(record.get("value"))
                    == scalar_wire(
                        Scalar(
                            {bool: "Bool", int: "Int", float: "Float", str: "Text"}[
                                type(original.expression.value)
                            ],
                            original.expression.value,
                        )
                    ),
                    "RETAINED_LITERAL",
                )
            return
        if isinstance(
            original,
            (
                scalar.ProjectSQLReference,
                scalar.ProjectSQLJoinedReference,
                scalar.ProjectSQLMatchReference,
                ProjectSQLResultReference,
                ProjectSQLWindowReference,
            ),
        ):
            read(address, original.port, uses)
            return
        if type(original) is scalar.ProjectSQLUnary:
            expected, inputs = (
                (
                    ("not", "not")
                    if original.expression.operator == "not"
                    else ("unary", original.expression.operator)
                ),
                (original.operand,),
            )
        elif isinstance(
            original, (scalar.ProjectSQLBinary, scalar.ProjectSQLComparison)
        ):
            expected = (
                "binary" if type(original) is scalar.ProjectSQLBinary else "comparison",
                original.expression.operator,
            )
            inputs = (original.left, original.right)
        elif type(original) is scalar.ProjectSQLIsNull:
            expected = (
                "null_test",
                "is_not_null" if original.expression.negated else "is_null",
            )
            inputs = (original.value,)
        elif type(original) is scalar.ProjectSQLBetween:
            expected = ("between", "between")
            inputs = (original.value, original.lower, original.upper)
        elif type(original) is scalar.ProjectSQLScalarCall:
            expected = ("scalar_call", original.callee_symbol.name)
            inputs = original.arguments
        elif type(original) is scalar.ProjectSQLConditional:
            expected = ("conditional", "if_else")
            inputs = (original.when_true, original.condition, original.when_false)
        elif type(original) is scalar.ProjectSQLMembership:
            expected = ("membership", "not_in" if original.expression.negated else "in")
            inputs = (original.value, *original.options)
        elif type(original) is scalar.ProjectSQLCast:
            expected = ("cast", "int_to_float")
            inputs = (original.value,)
        elif type(original) is scalar.ProjectSQLRelationExists:
            expected, inputs = ("exists", "exists"), ()
        elif type(original) is scalar.ProjectSQLRelationScalar:
            expected, inputs = ("scalar", "scalar"), ()
        elif type(original) is scalar.ProjectSQLRelationMembership:
            expected = (
                "relation_membership",
                "not_in" if original.expression.negated else "in",
            )
            inputs = (original.value,)
        else:
            raise CompiledError("COMPILED_RETAINED_EXPRESSION_DOMAIN")
        need(
            record.address.kind == "operation"
            and record.get("operator") == expected
            and len(record.get("operands")) == len(inputs),
            "RETAINED_EXPRESSION",
        )
        if isinstance(
            original,
            (
                scalar.ProjectSQLRelationExists,
                scalar.ProjectSQLRelationScalar,
                scalar.ProjectSQLRelationMembership,
            ),
        ):
            # The one block use of this read names the actual plan edge's
            # consumer, producer terminal and read column.
            edge = block_uses.get(original.use)
            described = tuple(
                r
                for r in records.values()
                if r.address.kind == "expression_block_use"
                and r.get("operation") == address
            )
            need(
                edge is not None
                and original.use not in read_edges
                and len(described) == 1
                and {records[use].get("consumer") for use in uses}
                == {described[0].get("consumer")}
                and described[0].get("producer") == terminals.get(edge.producer)
                and described[0].get("column") == edge.edge.column,
                "RETAINED_BLOCK_READ",
            )
            # A capturing let's records name the reading body's ports of each
            # captured input, in line order.
            need(
                tuple(
                    r.values
                    for r in records.values()
                    if r.address.kind == "capture_use"
                    and r.get("read") == described[0].address
                )
                == tuple(
                    (
                        described[0].address,
                        c.use.ordinal,
                        tuple(port(reference) for reference in c.ports),
                    )
                    for c in plan.captures
                    if c.read is original_ref
                ),
                "RETAINED_CAPTURE",
            )
            read_edges.add(original.use)
        for child, ref in zip(record.get("operands"), inputs, strict=True):
            expression(child, ref, uses)

    def outputs(record):
        result = tuple(records[a] for a in record.get("outputs"))
        need(
            all(
                p.address.kind == "port"
                and p.get("owner") == record.address
                and p.get("ordinal") == i
                for i, p in enumerate(result)
            ),
            "RETAINED_OUTPUTS",
        )
        return result

    def uses(record, producers):
        actual = tuple(
            r
            for r in records.values()
            if r.address.kind == "use" and r.get("consumer") == record.address
        )
        need(len(actual) == len(producers), "RETAINED_USES")
        for i, (use, producer) in enumerate(zip(actual, producers, strict=True)):
            expected = tuple(
                r.address
                for r in records.values()
                if r.address.kind == "port" and r.get("owner") == producer
            )
            need(
                use.get("ordinal") == i
                and use.get("producer") == producer
                and use.get("ports") == expected,
                "RETAINED_USE_INPUT",
            )
        return tuple(r.address for r in actual)

    for source in plan.sources:
        record = records[references[source.ref]]
        need(
            record.address.kind == "source"
            and record.get("family") == source_family(source)
            and record.get("namespace") is None
            and record.get("name") is None,
            "RETAINED_SOURCE",
        )
        owner(record.get("declaration"), source.source.owner)
        fields = tuple(p for p in plan.source_ports if p.owner is source.ref)
        described_ports = tuple(
            r
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == record.address
        )
        need(
            len(fields) == len(record.get("fields")) == len(described_ports),
            "RETAINED_SOURCE_FIELDS",
        )
        for i, (original, address, described) in enumerate(
            zip(fields, record.get("fields"), described_ports, strict=True)
        ):
            field = records[address]
            need(
                field.address.kind == "field"
                and field.get("source") == record.address
                and field.get("ordinal") == i
                and field.get("label") == original.field.evidence.name
                and field.get("logical") == logical(original.field)
                and field.get("column") is None
                and field.get("physical") is None,
                "RETAINED_SOURCE_FIELD",
            )
            need(
                described.get("source") == address
                and described.get("logical") == logical(original.field),
                "RETAINED_SOURCE_PORT",
            )
            ports[original.ref] = described.address
        for original, described in zip(
            source_defs[source.ref].exports, described_ports, strict=True
        ):
            ports[original.ref] = described.address
        original_keys = []
        seen_supports = set()
        for key in source_defs[source.ref].entry.active_properties.relational.keys:
            for evidence in key.supports:
                from pietto._project.project_row_keys import ProjectCandidateKeyFact

                if type(evidence) is not ProjectCandidateKeyFact:
                    raise CompiledError("COMPILED_RETAINED_KEY_AUTHORITY")
                for support in evidence.supports:
                    if id(support) not in seen_supports:
                        seen_supports.add(id(support))
                        original_keys.append(support)
        actual_keys = tuple(
            r
            for r in records.values()
            if r.address.kind == "source_unique" and r.get("source") == record.address
        )
        need(len(actual_keys) == len(original_keys), "RETAINED_KEY_INVENTORY")
        for actual, original in zip(actual_keys, original_keys, strict=True):
            owner(actual.get("shape"), original.declaration.shape_occurrence)
            need(
                actual.get("position")
                == original.identity.declaration.shape_item_position
                and actual.get("fields")
                == tuple(
                    described_ports[d.source_field_identity.field_position].address
                    for d in original.determinants
                )
                and (
                    actual.get("null_policy"),
                    actual.get("origin"),
                    actual.get("trust"),
                    actual.get("enforcement"),
                )
                == (
                    original.null_policy.value,
                    original.origin.value,
                    original.trust.value,
                    original.enforcement.value,
                ),
                "RETAINED_KEY",
            )
        terminals[source.ref] = record.address

    for definition in plan.bindings.definitions:
        if definition.ref in terminals:
            continue
        # A capturing let is FROM, WHERE and SELECT rows only, all inline.
        inline = definition.ref in captured_definitions
        need(
            not inline
            or not any(
                item.definition is definition.ref
                for item in (*plan.set_bodies, *plan.joins, *plan.result_boundaries)
            )
            and all(
                b.kind.value not in ("aggregate", "window")
                for b in plan.blocks
                if b.definition is definition.ref
            ),
            "RETAINED_INLINE",
        )
        previous = None
        sets = tuple(v for v in plan.set_bodies if v.definition is definition.ref)
        if sets:
            original = sets[0]
            record = records[references[original.ref]]
            owner(record.get("owner"), definition.entry.owner)
            operands = tuple(
                next(o for o in plan.set_operands if o.ref is r)
                for r in original.operands
            )
            input_uses = uses(record, tuple(terminals[o.producer] for o in operands))
            need(
                record.address.kind == "set"
                and (record.get("kind"), record.get("quantifier"))
                == (original.kind.value, original.quantifier.value)
                and record.get("operands") == input_uses,
                "RETAINED_SET",
            )
            for original_port, described in zip(
                definition.exports, outputs(record), strict=True
            ):
                need(
                    described.get("logical") == logical(original_port.field),
                    "RETAINED_SET_OUTPUT",
                )
                value = records[described.get("source")]
                need(
                    value.address.kind == "set_value"
                    and value.get("owner") == record.address
                    and len(value.get("inputs")) == len(input_uses),
                    "RETAINED_SET_VALUE",
                )
                for address, use in zip(value.get("inputs"), input_uses, strict=True):
                    actual = records[address]
                    need(
                        actual.address.kind == "read"
                        and actual.get("use") == use
                        and actual.get("port")
                        == records[use].get("ports")[described.get("ordinal")],
                        "RETAINED_SET_INPUT",
                    )
                ports[original_port.ref] = described.address
            terminals[definition.ref] = record.address
            continue
        for join in (j for j in plan.joins if j.definition is definition.ref):
            record = records[references[join.ref]]
            owner(record.get("owner"), definition.entry.owner)
            originals = tuple(
                next(i for i in plan.join_inputs if i.ref is r) for r in join.inputs
            )
            parents = tuple(
                references[i.predecessor]
                if i.predecessor is not None
                else terminals[i.producer]
                for i in originals
            )
            input_uses = uses(record, parents)
            need(
                record.address.kind == "join"
                and record.get("kind") == join.kind.value
                and record.get("ordinal") == join.position
                and record.get("inputs") == input_uses,
                "RETAINED_JOIN",
            )
            for original, use in zip(originals, input_uses, strict=True):
                for ref, address in zip(
                    original.ports, records[use].get("ports"), strict=True
                ):
                    ports[ref] = address
            expected_equalities = tuple(
                e for e in plan.relationship_matches if e.join is join.ref
            )
            need(
                len(expected_equalities) == len(record.get("equalities")),
                "RETAINED_JOIN_EQUALITIES",
            )
            for original, address in zip(
                expected_equalities, record.get("equalities"), strict=True
            ):
                equality = records[address]
                read(equality.get("left"), original.left, input_uses)
                read(equality.get("right"), original.right, input_uses)
            need(
                (join.on is None) is (record.get("predicate") is None),
                "RETAINED_JOIN_PREDICATE",
            )
            if join.on is not None:
                expression(record.get("predicate"), join.on, input_uses)
            for ref, described in zip(join.outputs, outputs(record), strict=True):
                original = next(p for p in plan.join_ports if p.ref is ref)
                need(
                    described.get("logical") == logical(original.field),
                    "RETAINED_JOIN_OUTPUT",
                )
                value = records[described.get("source")]
                need(
                    value.address.kind == "join_value"
                    and value.get("owner") == record.address,
                    "RETAINED_JOIN_VALUE",
                )
                read(value.get("input"), original.source, input_uses)
                ports[ref] = described.address
            previous = record.address
        if previous is None:
            original_inputs = tuple(
                u for u in plan.input_uses if u.consumer is definition.ref
            )
            need(len(original_inputs) == 1, "RETAINED_INPUT")
            previous = terminals[original_inputs[0].producer]
        for block in (b for b in plan.blocks if b.definition is definition.ref):
            record = records[references[block.ref]]
            owner(record.get("owner"), definition.entry.owner)
            input_uses = uses(record, (previous,))
            need(record.get("input") == previous, "RETAINED_BLOCK_INPUT")
            for ref, address in zip(
                block.inputs, records[input_uses[0]].get("ports"), strict=True
            ):
                ports[ref] = address
            actual_outputs = outputs(record)
            need(len(actual_outputs) == len(block.exports), "RETAINED_BLOCK_OUTPUTS")
            if block.kind.value == "aggregate":
                original = next(a for a in plan.aggregations if a.block is block.ref)
                need(
                    record.address.kind == "aggregate"
                    and record.get("mode") == original.mode.value,
                    "RETAINED_AGGREGATE",
                )
                keys = tuple(
                    k for k in plan.group_keys if k.aggregation is original.ref
                )
                aggregates = tuple(
                    v for v in plan.aggregates if v.aggregation is original.ref
                )
                need(
                    len(record.get("keys")) == len(keys)
                    and len(record.get("values")) == len(aggregates),
                    "RETAINED_AGGREGATE_INVENTORY",
                )
                for key, address in zip(keys, record.get("keys"), strict=True):
                    read(address, key.input, input_uses)
                for item, address in zip(aggregates, record.get("values"), strict=True):
                    value = records[address]
                    need(
                        value.address.kind == "aggregate_value"
                        and value.get("function") == function_name(item.source)
                        and len(value.get("arguments")) == len(item.arguments),
                        "RETAINED_AGGREGATE_VALUE",
                    )
                    for address, ref in zip(
                        value.get("arguments"), item.arguments, strict=True
                    ):
                        expression(address, ref, input_uses)
            elif block.kind.value == "window":
                need(record.address.kind == "window", "RETAINED_WINDOW")
                windows = tuple(w for w in plan.windows if w.block is block.ref)
                need(
                    len(record.get("values")) == len(block.inputs) + len(windows),
                    "RETAINED_WINDOW_INVENTORY",
                )
                # Full policy/argument correspondence is checked below after the
                # same original pre-window inputs have been established.
                for original, address in zip(
                    windows, record.get("values")[len(block.inputs) :], strict=True
                ):
                    value = records[address]
                    need(
                        value.address.kind == "window_value"
                        and value.get("function") == original.function.name
                        and value.get("selected") == (original.selected is not None),
                        "RETAINED_WINDOW_VALUE",
                    )
                    policy = next(
                        p for p in plan.window_policies if p.ref is original.policy
                    )
                    specification = records[value.get("specification")]
                    original_uses = tuple(
                        u for u in plan.window_uses if u.window is original.ref
                    )
                    partition_uses = tuple(
                        u for u in original_uses if u.role.value == "window_partition"
                    )
                    order_uses = tuple(
                        u for u in original_uses if u.role.value == "window_order"
                    )
                    need(
                        len(specification.get("partition")) == len(partition_uses)
                        and len(specification.get("ordering")) == len(order_uses),
                        "RETAINED_WINDOW_INPUTS",
                    )
                    for address, item in zip(
                        specification.get("partition"), partition_uses, strict=True
                    ):
                        read(address, item.input, input_uses)
                    for (address, direction, nulls), item in zip(
                        specification.get("ordering"), order_uses, strict=True
                    ):
                        read(address, item.input, input_uses)
                        need(
                            direction
                            == policy.orders[item.role_position].effective_direction
                            and nulls is None,
                            "RETAINED_WINDOW_ORDER",
                        )
                    frame = None
                    if (
                        policy.specification.frame is not None
                        and policy.specification.frame.resolved.unit is not None
                    ):
                        resolved = policy.specification.frame.resolved
                        if (
                            resolved.unit is None
                            or resolved.start is None
                            or resolved.end is None
                        ):
                            raise CompiledError("COMPILED_RETAINED_WINDOW_FRAME")
                        frame = (
                            resolved.unit.value,
                            (
                                resolved.start.kind.value,
                                None
                                if resolved.start.offset is None
                                else literal_addresses[id(resolved.start.offset)],
                            ),
                            (
                                resolved.end.kind.value,
                                None
                                if resolved.end.offset is None
                                else literal_addresses[id(resolved.end.offset)],
                            ),
                            None
                            if resolved.exclusion is None
                            else resolved.exclusion.value,
                        )
                    need(specification.get("frame") == frame, "RETAINED_WINDOW_FRAME")
                    named = specification.get("named")
                    need(
                        (named is None) == (policy.named_use is None),
                        "RETAINED_WINDOW_NAMED",
                    )
                    if named is not None:
                        need(
                            named in record.get("definitions"), "RETAINED_WINDOW_NAMED"
                        )
                        definition_spec = records[records[named].get("specification")]
                        need(
                            definition_spec.get("named") is None
                            and definition_spec.get("frame") == frame
                            and tuple(
                                records[a].get("port")
                                for a in definition_spec.get("partition")
                            )
                            == tuple(
                                records[a].get("port")
                                for a in specification.get("partition")
                            )
                            and tuple(
                                (records[a].get("port"), d, n)
                                for a, d, n in definition_spec.get("ordering")
                            )
                            == tuple(
                                (records[a].get("port"), d, n)
                                for a, d, n in specification.get("ordering")
                            ),
                            "RETAINED_WINDOW_NAMED_INPUTS",
                        )
                    arguments = tuple(
                        a for a in plan.window_arguments if a.window is original.ref
                    )
                    need(
                        len(arguments) == len(value.get("arguments")),
                        "RETAINED_WINDOW_ARGUMENTS",
                    )
                    for argument, (role, address) in zip(
                        arguments, value.get("arguments"), strict=True
                    ):
                        need(
                            role == argument.role.value, "RETAINED_WINDOW_ARGUMENT_ROLE"
                        )
                        if argument.use is None:
                            need(
                                address == literal_addresses[id(argument.expression)],
                                "RETAINED_WINDOW_ARGUMENT_LITERAL",
                            )
                        else:
                            use = next(
                                u for u in original_uses if u.ref is argument.use
                            )
                            read(address, use.input, input_uses)

            else:
                need(
                    record.address.kind == "row"
                    and record.get("stage") == block.kind.value
                    and (unit_position(record) is None) is inline,
                    "RETAINED_ROW",
                )
                projections = {
                    v.export: v for v in plan.projections if v.block is block.ref
                }
                carried = {
                    v.export: v
                    for v in (*plan.aggregate_projections, *plan.window_projections)
                    if v.block is block.ref
                }
                lets = {v.port: v for v in plan.let_values if v.site.block is block.ref}
                for ref, described in zip(block.exports, actual_outputs, strict=True):
                    value = described.get("source")
                    if ref in projections:
                        expression(value, projections[ref].expression, input_uses)
                    elif ref in lets:
                        expression(value, lets[ref].expression, input_uses)
                    elif ref in carried:
                        read(value, carried[ref].input, input_uses)
                    else:
                        read(value, aliases[ref], input_uses)
                filters = tuple(f for f in plan.filters if f.site.block is block.ref)
                need(
                    len(filters) <= 1
                    and (not filters) == (record.get("predicate") is None),
                    "RETAINED_FILTER",
                )
                if filters:
                    expression(
                        record.get("predicate"), filters[0].predicate, input_uses
                    )
            for ref, described in zip(block.exports, actual_outputs, strict=True):
                ports[ref] = described.address
            previous = record.address
        boundaries = tuple(
            b for b in plan.result_boundaries if b.definition is definition.ref
        )
        if boundaries:
            record = records[references[boundaries[0].ref]]
            owner(record.get("owner"), definition.entry.owner)
            need(
                all(references[b.ref] == record.address for b in boundaries),
                "RETAINED_RESULT_BOUNDARIES",
            )
            input_uses = uses(record, (previous,))
            need(
                record.address.kind == "result"
                and record.get("input") == previous
                and record.get("distinct")
                == any(b.kind.value == "distinct" for b in boundaries),
                "RETAINED_RESULT",
            )
            for boundary in boundaries:
                for ref, address in zip(
                    boundary.inputs, records[input_uses[0]].get("ports"), strict=True
                ):
                    ports[ref] = address
                for ref, address in zip(
                    boundary.outputs, records[input_uses[0]].get("ports"), strict=True
                ):
                    ports[ref] = address
            order_items = tuple(
                next(i for i in plan.order_items if i.ref is ref)
                for order in plan.orders
                if any(order.boundary is b.ref for b in boundaries)
                for ref in order.items
            )
            need(
                len(record.get("ordering")) == len(order_items),
                "RETAINED_ORDER_INVENTORY",
            )
            for (address, direction), item in zip(
                record.get("ordering"), order_items, strict=True
            ):
                ordered_expression = next(
                    e for e in plan.order_expressions if e.ref is item.expression
                )
                order = next(
                    order for order in plan.orders if order.ref is item.ordering
                )
                if ordered_expression.use is not None:
                    original_use = next(
                        u for u in plan.order_uses if u.ref is ordered_expression.use
                    )
                    need(
                        len(original_use.ports) == 1
                        and original_use.requirement is None
                        and direction == item.source.direction.value,
                        "RETAINED_ORDER",
                    )
                    read(address, original_use.ports[0], input_uses)
                else:
                    matches = tuple(
                        projection
                        for projection in plan.projections
                        if _same_order_expression(
                            expressions[projection.expression].expression,
                            ordered_expression.expression,
                        )
                    )
                    boundary = tuple(
                        value
                        for value in plan.result_boundaries
                        if value.ref is order.boundary
                    )
                    result_ports = {port.ref: port for port in plan.result_ports}

                    def terminal_source(reference):
                        while reference in result_ports:
                            reference = result_ports[reference].source
                        return reference

                    inputs = (
                        ()
                        if len(boundary) != 1 or len(matches) != 1
                        else tuple(
                            value
                            for value in boundary[0].inputs
                            if terminal_source(value) is matches[0].ref
                        )
                    )
                    need(
                        bool(ordered_expression.operands)
                        and len(inputs) == 1
                        and direction == item.source.direction.value,
                        "RETAINED_ORDER",
                    )
                    assert inputs
                    read(address, inputs[0], input_uses)
            limits = tuple(
                v
                for v in plan.result_limits
                if any(v.boundary is b.ref for b in boundaries)
            )
            need(
                len(limits) <= 1
                and record.get("limit") == (limits[0].value if limits else None),
                "RETAINED_RESULT_LIMIT",
            )
            for i, described in enumerate(outputs(record)):
                value = records[described.get("source")]
                need(
                    value.address.kind == "read"
                    and value.get("use") == input_uses[0]
                    and value.get("port") == records[input_uses[0]].get("ports")[i],
                    "RETAINED_RESULT_PROJECTION",
                )
            previous = record.address
        terminals[definition.ref] = previous
        for original, described in zip(
            definition.exports, outputs(records[previous]), strict=True
        ):
            ports[original.ref] = described.address
    need(
        read_edges == set(block_uses)
        and sum(r.address.kind == "expression_block_use" for r in records.values())
        == len(block_uses),
        "RETAINED_BLOCK_READ_INVENTORY",
    )
    entry = records[description.query]
    selected = next(
        d for d in plan.bindings.definitions if d.entry.owner is checked.selected_owner
    )
    need(
        entry.get("terminal") == terminals[selected.ref]
        and entry.get("exports") == tuple(ports[p.ref] for p in selected.exports),
        "RETAINED_TERMINAL",
    )
    expected_requests = tuple(
        r
        for r in checked.completed.single_match_requests
        if any(r.owner is d.entry.owner for d in plan.bindings.definitions)
    )
    need(len(entry.get("requests")) == len(expected_requests), "RETAINED_REQUESTS")
    input_by_ref = {i.ref: i for i in plan.join_inputs}
    identities = {}
    for address, original in zip(entry.get("requests"), expected_requests, strict=True):
        record = records[address]
        owner(record.get("owner"), original.owner)
        obligations = tuple(o for o in plan.single_matches if o.request is original)
        need(bool(obligations), "RETAINED_REQUEST_PLAN")
        expected_pairs = []
        for pair in obligations[0].input_pairs:
            expected_pairs.append(
                tuple(
                    records[references[input_by_ref[r].join]].get("inputs")[
                        input_by_ref[r].ordinal
                    ]
                    for r in pair
                )
            )
        need(
            record.get("pairs") == tuple(expected_pairs)
            and record.get("scope") == original.scope.value
            and record.get("unit") == original.unit.value,
            "RETAINED_REQUEST_INPUTS",
        )
        if id(original) in identities:
            need(identities[id(original)] == address, "RETAINED_REQUEST_ALIAS")
        identities[id(original)] = address
    need(len(set(identities.values())) == len(identities), "RETAINED_REQUEST_MERGE")
