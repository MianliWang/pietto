"""Closed direct SELECT structure, exact ports, and finite realization rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any
from pietto.ast_nodes import AuthoredJoinKind, SourceDef

from pietto._project import project_sql_plan_expressions as row
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_emission_scopes import (
    ScopeDefinition,
    ScopeUse,
    TerminalBinding,
    reference_source_ports,
)
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_joins as joining
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project import project_sql_emission_windows as windowing
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project.project_sql_emission_contract import (
    Blocker,
    BoundField,
    BoundSource,
    PreparedEmission,
    RELEASES,
    MAX_NODES,
    MAX_SQL_BYTES,
    MAX_ARTIFACT_BYTES,
    MAX_PARAMETERS,
    source_family,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class SQLSymbol:
    position: int
    binding: object
    name: str


@dataclass(frozen=True, slots=True, eq=False)
class SQLScan:
    source: Any
    realization: BoundSource
    use: Any
    symbol: SQLSymbol
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class SQLNamedUse:
    cte: SQLCTE
    use: Any
    symbol: SQLSymbol
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class SQLColumn:
    ordinal: int
    scan: SQLScan | SQLNamedUse
    source_field: BoundField
    source_port: Any
    input_port: Any
    export: Any
    projection: Any
    symbol: SQLSymbol
    label: str
    producer: TerminalBinding
    origin: SQLScan


@dataclass(frozen=True, slots=True, eq=False)
class SQLLiteralColumn:
    ordinal: int
    scan: SQLScan | SQLNamedUse
    export: Any
    projection: Any
    symbol: SQLSymbol
    label: str
    origin: parameters.LiteralOrigin
    value: parameters.SQLAnchor | parameters.SQLUnary | None
    producer: TerminalBinding | None


@dataclass(frozen=True, slots=True, eq=False)
class SQLSelect:
    request: PreparedEmission
    scan: SQLScan | SQLNamedUse
    columns: tuple[SQLColumn | SQLLiteralColumn, ...]
    definition: ScopeDefinition
    ctes: tuple[SQLCTE, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class SQLCTE:
    definition: ScopeDefinition
    symbol: SQLSymbol
    columns: tuple[SQLSymbol, ...]
    body: SQLSelect


@dataclass(frozen=True, slots=True, eq=False)
class OriginalRequirement:
    entry: Any
    rule: str


@dataclass(frozen=True, slots=True, eq=False)
class GeneratedRequirement:
    kind: str
    subject: object
    rule: str
    premises: tuple[Any, ...]


def identifier_valid(name, family, *, label=False, relation=False):
    if type(name) is not str or not name or "\0" in name:
        return False
    try:
        encoded = name.encode("utf-8")
    except UnicodeError:
        return False
    if family == "postgres":
        return len(encoded) <= 63
    if (
        family != "mysql"
        or len(name) > (256 if label else 64)
        or any(ord(c) > 0xFFFF for c in name)
    ):
        return False
    if not label and name.endswith(" "):
        return False
    return not relation or not any(c in name for c in (".", "/", "\\"))


def projection_chain_shape(plan):
    named = tuple(
        d
        for d in plan.bindings.definitions
        if type(d.entry.owner.definition) is not SourceDef
    )
    return (
        bool(named)
        and len(plan.sources) == 1
        and len(plan.blocks) == len(named) == len(plan.input_uses)
        and all(
            tuple(o.kind.value for o in block.operators)
            == ("relation_input", "final_projection")
            for block in plan.blocks
        )
        and all(
            sum(block.definition is d.ref for block in plan.blocks) == 1
            and sum(use.consumer is d.ref for use in plan.input_uses) == 1
            and bool(d.exports)
            for d in named
        )
        and len(plan.projections) == len(plan.all_exports) == len(plan.expression_sites)
        and all(
            type(e)
            in {
                row.ProjectSQLReference,
                row.ProjectSQLLiteral,
                row.ProjectSQLBoundLiteral,
                row.ProjectSQLUnary,
            }
            for e in plan.expressions
        )
        and all(
            type(plan.expressions[p.expression.position]) is row.ProjectSQLReference
            or parameters.original_chain(plan, p.expression) is not None
            for p in plan.projections
        )
        and not any(
            (
                plan.let_values,
                plan.filters,
                plan.joins,
                plan.aggregations,
                plan.windows,
                plan.distincts,
                plan.orders,
                plan.result_limits,
                plan.set_bodies,
            )
        )
    )


def applicable_premises(request, owner, field=None):
    plan = request.plan
    sites = (
        ()
        if field is None
        else tuple(
            expression.site
            for expression, source_port in reference_source_ports(plan).values()
            if source_port.field is field.field
        )
    )
    return tuple(
        p
        for p in request.premises
        if p.scope == "statement"
        or p.scope is owner
        or (
            type(p.scope) is tuple
            and p.scope[0] is owner
            and any(p.scope[1] is s for s in sites)
        )
    )


def resource_limits(request):
    limits = {
        "sql_bytes": MAX_SQL_BYTES,
        "artifact_bytes": MAX_ARTIFACT_BYTES,
        "nodes": MAX_NODES,
        "parameters": MAX_PARAMETERS,
        "columns": 1664 if request.family == "postgres" else 4096,
    }
    for premise in request.premises:
        if premise.scope == "statement" and premise.key == "resource_limits":
            for key, value in json.loads(premise.value).items():
                limits[key] = min(limits[key], value)
    return limits


def representation_problem(field: BoundField, family: str):
    value = json.loads(field.representation)
    storage, domain = value["storage"], value["domain"]
    evidence = field.field.evidence
    logical = evidence.resolved_type
    resolution = field.resolution
    if (
        resolution is None
        or resolution.reference.type_expr is not evidence.field_def.type_expr
        or resolution.canonical_kind is not logical.kind
        or resolution.canonical_name != logical.name
    ):
        return "PIE-B1004", "logical_type_evidence_missing"
    if logical.kind is not ProjectResolvedTypeKind.BUILTIN:
        return "PIE-B1003", "representation_not_in_initial_domain"
    if logical.name in {"Timestamp", "UUID"}:
        return "PIE-B1004", "logical_temporal_or_uuid_meaning_missing"
    nullability = {"non_null": False, "nullable": True, "unknown": "unknown"}[
        field.field.effective_nullability.value
    ]
    if value["nullable"] != nullability or type(value["nullable"]) is not type(
        nullability
    ):
        return "PIE-B1002", "nullability_mismatch"
    kind = storage["kind"]
    prefix = "pg_" if family == "postgres" else "my_"
    valid = kind.startswith(prefix)
    if logical.name == "Int":
        bits = {
            "pg_int2": 16,
            "pg_int4": 32,
            "pg_int8": 64,
            "my_smallint": 16,
            "my_int": 32,
            "my_bigint": 64,
        }.get(kind)
        valid = valid and bits is not None and domain["kind"] == "int_range"
        if valid and bits is not None:
            valid = (
                -(1 << (bits - 1))
                <= int(domain["min"])
                <= int(domain["max"])
                < 1 << (bits - 1)
            )
    elif logical.name == "Bool":
        valid = (
            valid and kind in {"pg_bool", "my_bool01"} and domain["kind"] == "bool01"
        )
    elif logical.name == "Text":
        valid = valid and kind in {"pg_text", "my_varchar"} and domain["kind"] == "text"
        if valid:
            expected = (
                ("UTF8", "C", "NO PAD")
                if family == "postgres"
                else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
            )
            valid = (
                tuple(domain[k] for k in ("encoding", "collation", "padding"))
                == expected
            )
            if kind == "my_varchar":
                valid = valid and domain["max_characters"] <= storage["length"] <= 16383
    elif logical.name == "Decimal":
        if field.decimal is None:
            return "PIE-B1004", "validated_decimal_parameters_missing"
        valid = (
            valid
            and kind in {"pg_numeric", "my_decimal"}
            and domain["kind"] == "decimal"
        )
        if valid:
            pair = (field.decimal.precision, field.decimal.scale)
            valid = (
                pair
                == (storage["precision"], storage["scale"])
                == (domain["precision"], domain["scale"])
                and 1 <= pair[0] <= 65
                and 0 <= pair[1] <= min(pair[0], 30)
            )
    elif logical.name == "Float":
        valid = (
            valid
            and kind in {"pg_float8", "my_double"}
            and domain["kind"] == "finite_float"
        )
    else:
        return "PIE-B1003", "representation_not_in_initial_domain"
    return None if valid else ("PIE-B1002", "physical_storage_or_domain_mismatch")


def emission_blockers(request: PreparedEmission):
    plan = request.plan
    result = list(request.input_blockers)

    def add(code, detail, subject=None, location=None):
        result.append(Blocker(code, detail, subject, location))

    if RELEASES.get(request.family) != request.release:
        add("PIE-B1003", "target_release_not_reviewed")
    admitted = projection_chain_shape(plan)
    realization = None
    if not admitted and (admitted_row_shape(plan) or joining.admitted_join_shape(plan)):
        realization = realize_rows(request)
        result.extend(realization.problems)
    elif not admitted:
        shape_start = len(result)
        for block in plan.blocks:
            for operator in block.operators:
                if operator.kind.value not in {
                    "relation_input",
                    "row_filter",
                    "final_projection",
                }:
                    add("PIE-B1003", "operator_not_implemented_in_slice6", block.ref)
        expressions = {e.ref: e for e in plan.expressions}
        for projection in plan.projections:
            if type(expressions.get(projection.expression)) not in ADMITTED_EXPRESSIONS:
                add(
                    "PIE-B1003",
                    "scalar_projection_requires_later_slice",
                    projection.ref,
                    projection.site.occurrence.span,
                )
        for body in plan.set_bodies:
            add("PIE-B1003", "set_lowering_requires_slice11", body.ref)
        # A retained MATCH exercises the same scalar domain; no JOIN SQL exists.
        for code, detail, subject, location in rows.match_applicability(request):
            add(code, detail, subject, location)
        for join in plan.joins:
            add("PIE-B1003", "join_shape_not_admitted_in_slice7", join.ref)
        if len(result) == shape_start:
            add("PIE-B1003", "non_field_projection_or_later_shape", plan.scope)
    for issue in request.target_request.issues:
        if issue.value == "profile_target_family_or_release_mismatch":
            add("PIE-B1005", "target_evidence_scope_conflict", request.target_request)
        elif issue.value == "profile_composition_blocked":
            add(
                "PIE-B1006",
                "original_profile_composition_unresolved",
                request.target_request,
            )
    limits = resource_limits(request)
    scalar_nodes = 0
    if admitted:
        for projection in plan.projections:
            expression = plan.expressions[projection.expression.position]
            if type(expression) is row.ProjectSQLReference:
                continue
            problem = parameters.chain_problem(
                plan, projection.expression, request.family
            )
            if problem is not None:
                add(*problem, projection.ref, projection.site.occurrence.span)
            else:
                chain = parameters.original_chain(plan, projection.expression)
                assert chain is not None
                scalar_nodes += 3 + len(chain[0])  # origin, anchor, leaf, every sign
    if scalar_nodes or realization is not None:
        keys = {"operator_environment": "builtin_only"}
        if plan.literal_slots:
            keys["parameter_protocol"] = (
                "postgres_extended"
                if request.family == "postgres"
                else "mysql_prepared"
            )
        for key, expected in keys.items():
            found = [
                p for p in request.premises if p.scope == "statement" and p.key == key
            ]
            if not found:
                add("PIE-B1004", key + "_declaration_missing", plan.scope)
            elif any(json.loads(p.value) != expected for p in found):
                add("PIE-B1005", key + "_declaration_mismatch", plan.scope)
    if len(plan.bind_uses) > limits["parameters"]:
        add("PIE-B1007", "parameter_occurrence_limit", plan.scope)
    bodies = tuple(
        d
        for d in request.layout.definitions
        if type(d.original.entry.owner.definition) is not SourceDef
    )
    intermediate = tuple(
        d for d in bodies if d.original.entry.owner is not plan.scope.selected_owner
    )
    nodes = (
        3 * len(bodies)
        + 2 * len(plan.projections)
        + sum(2 + len(d.terminals) for d in intermediate)
        + scalar_nodes
    )
    generated_scopes = bool(intermediate)
    if realization is not None and realization.query is not None:
        query = realization.query
        nodes = query.nodes
        generated_scopes = len(query.bodies) > 1
        units = getattr(query, "units", query.bodies)
        generated_scopes = len(units) > 1
        if any(len(unit.columns) > limits["columns"] for unit in units):
            add("PIE-B1007", "generated_structure_limit", plan.scope)
    if admitted and (
        any(len(d.terminals) > limits["columns"] for d in bodies)
        or nodes > limits["nodes"]
    ):
        add("PIE-B1007", "generated_structure_limit", plan.scope)
    if realization is not None and nodes > limits["nodes"]:
        add("PIE-B1007", "generated_structure_limit", plan.scope)
    if (admitted or realization is not None) and generated_scopes:
        names = [p for p in request.premises if p.key == "identifier_case"]
        expected = (
            "quoted_exact"
            if request.family == "postgres"
            else "lower_case_table_names=0"
        )
        if not names:
            add("PIE-B1004", "identifier_case_declaration_missing", plan.scope)
        elif any(json.loads(p.value) != expected for p in names):
            add("PIE-B1005", "identifier_case_declaration_mismatch", plan.scope)
    for aspect in request.assessment.assessment.aspects:
        if any(
            state.value in {"exact_negative", "conflicting_facts"}
            for state in aspect.outcomes
        ):
            add("PIE-B1006", "negative_original_target_evidence", aspect.entry.subject)
    for obligation in request.report.report.summary.enforcement_required:
        add("PIE-B1006", "original_enforcement_not_fulfilled", obligation.entry.subject)
    for source in plan.sources:
        if source_family(source) != request.family:
            add(
                "PIE-B1001",
                "source_family_mismatch",
                source.ref,
                source.declaration.span,
            )
        matches = tuple(s for s in request.sources if s.owner is source.source.owner)
        if len(matches) != 1:
            add(
                "PIE-B1001",
                "source_mapping_missing",
                source.ref,
                source.declaration.span,
            )
            continue
        bound = matches[0]
        original = tuple(p for p in plan.source_ports if p.owner is source.ref)
        if tuple(f.ordinal for f in bound.fields) != tuple(range(len(original))) or any(
            f.field is not p.field for f, p in zip(bound.fields, original)
        ):
            add("PIE-B1001", "complete_ordered_source_schema_required", source.ref)
        if not all(
            identifier_valid(n, request.family, relation=True)
            for n in (bound.namespace, bound.name)
        ):
            add("PIE-B1001", "source_identifier_unrepresentable", source.ref)
        used = applicable_premises(request, bound.owner)
        for key in ("row_domain_matches", "read_only_object"):
            values = [p for p in used if p.key == key]
            if not values or any(p.value != b"true" for p in values):
                add("PIE-B1001", key + "_declaration_required", source.ref)
        clients = [p for p in used if p.key == "client_encoding"]
        if not clients:
            add("PIE-B1004", "client_encoding_declaration_missing", source.ref)
        elif any(
            json.loads(p.value)
            != ("UTF8" if request.family == "postgres" else "utf8mb4")
            for p in clients
        ):
            add("PIE-B1005", "client_encoding_mismatch", source.ref)
        columns = set()
        for field in bound.fields:
            subject = original[field.ordinal].ref
            column_key = (
                field.column
                if request.family == "postgres"
                else field.column.casefold()
            )
            if (
                not identifier_valid(field.column, request.family)
                or column_key in columns
            ):
                add(
                    "PIE-B1001",
                    "column_identifier_unrepresentable_or_colliding",
                    subject,
                )
            columns.add(column_key)
            problem = representation_problem(field, request.family)
            if problem is not None:
                add(
                    *problem,
                    subject,
                    field.field.evidence.field_def.span
                    if field.field.evidence.field_def
                    else None,
                )
            domain = json.loads(field.representation)["domain"]
            for premise in applicable_premises(request, bound.owner, field):
                expected = (
                    domain if premise.key == "value_domain" else domain.get(premise.key)
                )
                if expected is not None and json.loads(premise.value) != expected:
                    add("PIE-B1005", "field_domain_premise_mismatch", subject)
    for port in plan.exports:
        if not identifier_valid(port.identity.name, request.family, label=True):
            add("PIE-B1002", "output_label_unrepresentable", port.ref)
    return tuple(result)


def build_sql_ast(request: PreparedEmission):
    plan = request.plan
    sources = {source.ref: source for source in plan.sources}
    bindings = {use.consumer.original.ref: use for use in request.layout.uses}
    blocks = {block.definition: block for block in plan.blocks}
    ordered = tuple(
        p
        for d in request.layout.definitions
        if d.original.ref not in sources
        for p in plan.projections
        if p.block is blocks[d.original.ref].ref
    )
    occurrences = []
    for projection in ordered:
        chain = parameters.original_chain(plan, projection.expression)
        if chain is not None and type(chain[1]) is row.ProjectSQLBoundLiteral:
            leaf = chain[1]
            tag = parameters.tag_of(leaf)
            assert tag is not None
            occurrences.append((leaf, parameters.PHYSICAL[request.family][tag]))
    allocated = parameters.allocate_uses(
        request.family, tuple(occurrences), resource_limits(request)["parameters"]
    )
    uses = {use.original.ref: use for use in allocated}
    ctes: dict[Any, SQLCTE] = {}
    selected = None
    for definition in request.layout.definitions:
        original = definition.original
        if original.ref in sources:
            continue
        binding = bindings[original.ref]
        use = binding.original
        alias = SQLSymbol(0, use.ref, f"s{use.ref.position}")
        scan: SQLScan | SQLNamedUse
        if use.producer in sources:
            source = sources[use.producer]
            (bound,) = tuple(
                s for s in request.sources if s.owner is source.source.owner
            )
            scan = SQLScan(source, bound, use, alias, binding)
        else:
            scan = SQLNamedUse(ctes[use.producer], use, alias, binding)
        projections = tuple(
            p for p in plan.projections if p.block is blocks[original.ref].ref
        )
        by_input = {b.input_port.ref: (i, b) for i, b in enumerate(binding.bindings)}
        columns = []
        final = original.entry.owner is plan.scope.selected_owner
        for position, (projection, export) in enumerate(
            zip(projections, original.exports, strict=True)
        ):
            label = export.identity.name if final else f"c{position}"
            if projection.input_port is None:
                value = parameters.build_value(
                    plan, projection.expression, request.family, uses
                )
                origin = parameters.LiteralOrigin(
                    value, export, definition.terminals[position]
                )
                columns.append(
                    SQLLiteralColumn(
                        position,
                        scan,
                        export,
                        projection,
                        SQLSymbol(position + 1, export.ref, label),
                        label,
                        origin,
                        value,
                        None,
                    )
                )
                continue
            port_position, producer = by_input[projection.input_port]
            if type(scan) is SQLScan:
                origin = scan
                source_port = producer.canonical
                (field,) = tuple(
                    f for f in scan.realization.fields if f.field is source_port.field
                )
                name = field.column
            else:
                assert type(scan) is SQLNamedUse
                previous = scan.cte.body.columns[port_position]
                if type(previous) is SQLLiteralColumn:
                    columns.append(
                        SQLLiteralColumn(
                            position,
                            scan,
                            export,
                            projection,
                            SQLSymbol(
                                position + 1,
                                producer.input_port.ref,
                                scan.cte.columns[port_position].name,
                            ),
                            label,
                            previous.origin,
                            None,
                            producer,
                        )
                    )
                    continue
                assert isinstance(previous, SQLColumn)
                origin, source_port, field = (
                    previous.origin,
                    previous.source_port,
                    previous.source_field,
                )
                name = scan.cte.columns[port_position].name
            columns.append(
                SQLColumn(
                    position,
                    scan,
                    field,
                    source_port,
                    producer.input_port,
                    export,
                    projection,
                    SQLSymbol(position + 1, producer.input_port.ref, name),
                    label,
                    producer,
                    origin,
                )
            )
        body = SQLSelect(request, scan, tuple(columns), definition)
        if final:
            selected = body
        else:
            ctes[original.ref] = SQLCTE(
                definition,
                SQLSymbol(len(ctes), original.ref, f"p{len(ctes)}"),
                tuple(
                    SQLSymbol(i, terminal.ref, f"c{i}")
                    for i, terminal in enumerate(definition.terminals)
                ),
                body,
            )
    assert selected is not None
    return replace(selected, ctes=tuple(ctes.values()))


def original_rule(plan, entry, *, generated_scopes):
    """One retained demand's rule: Slice6 operators first, then the prior mapping."""
    rule = rows.demand_rule(plan, entry)
    if rule is not None:
        return rule
    rule = joining.demand_rule(plan, entry)
    if rule is not None:
        return rule
    rule = grouping.demand_rule(entry)
    if rule is not None:
        return rule
    rule = windowing.demand_rule(entry)
    if rule is not None:
        return rule
    if entry.family.value == "fixed_literal_transport" or (
        entry.family.value == "expression"
        and type(plan.expressions[entry.subject.position])
        not in {
            row.ProjectSQLReference,
            row.ProjectSQLJoinedReference,
            row.ProjectSQLMatchReference,
            grouping.ProjectSQLResultReference,
            plan_windows.ProjectSQLWindowReference,
        }
    ):
        return "R04"
    if generated_scopes and entry.family.value == "scope":
        return "R03"
    if entry.family.value in {"source_realization", "expression", "scope"}:
        return "R01"
    return "R02"


def build_requirements(request, ast):
    original = tuple(
        OriginalRequirement(
            entry, original_rule(request.plan, entry, generated_scopes=bool(ast.ctes))
        )
        for entry in request.report.report.entries
    )
    generated = []
    naming = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "identifier_case"
    )
    for cte in ast.ctes:
        generated.append(
            GeneratedRequirement(
                "cte_definition", cte.definition.original.ref, "R03", naming
            )
        )
        generated.extend(
            GeneratedRequirement("terminal_column", terminal.ref, "R03", naming)
            for terminal in cte.definition.terminals
        )
    for body in (*[cte.body for cte in ast.ctes], ast):
        scan = body.scan
        if type(scan) is SQLScan:
            generated.append(
                GeneratedRequirement(
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            generated.extend(
                GeneratedRequirement(
                    "source_representation",
                    field,
                    "R02",
                    applicable_premises(request, scan.realization.owner, field),
                )
                for field in scan.realization.fields
            )
        else:
            generated.append(
                GeneratedRequirement("named_use", scan.use.ref, "R03", naming)
            )
            generated.extend(
                GeneratedRequirement(
                    "immediate_terminal", link.terminal.ref, "R03", naming
                )
                for link in scan.binding.bindings
            )
        for column in body.columns:
            if type(column) is SQLLiteralColumn:
                generated.append(
                    GeneratedRequirement(
                        "value_projection", column.projection.ref, "R04", ()
                    )
                )
                if column.value is not None:
                    for node in parameters.value_nodes(column.value):
                        kind = (
                            "unary"
                            if type(node) is parameters.SQLUnary
                            else "type_anchor"
                            if type(node) is parameters.SQLAnchor
                            else "parameter"
                            if type(node) is parameters.SQLParameter
                            else "literal"
                        )
                        generated.append(
                            GeneratedRequirement(
                                kind,
                                node.original.ref,
                                "R04",
                                parameters.anchor_premises(
                                    request, kind, parameters.tag_of(node.original)
                                ),
                            )
                        )
                continue
            generated.append(
                GeneratedRequirement(
                    "field_projection",
                    column,
                    "R02",
                    applicable_premises(
                        request, column.origin.realization.owner, column.source_field
                    ),
                )
            )
        generated.append(
            GeneratedRequirement("read_only_select_bytes", body, "R23", ())
        )
    if ast.ctes:
        generated.append(
            GeneratedRequirement("nonrecursive_with_bytes", ast, "R23", ())
        )
    return original, tuple(generated)


ADMITTED_EXPRESSIONS = (
    row.ProjectSQLLiteral,
    row.ProjectSQLBoundLiteral,
    row.ProjectSQLReference,
    row.ProjectSQLUnary,
    row.ProjectSQLBinary,
    row.ProjectSQLComparison,
    row.ProjectSQLIsNull,
)
ADMITTED_STAGE_EXPRESSIONS = (
    *ADMITTED_EXPRESSIONS,
    grouping.ProjectSQLResultReference,
    plan_windows.ProjectSQLWindowReference,
)
STAGE_KINDS = grouping.STAGE_KINDS
RETENTION = (("true", True), ("false", False), ("unknown", False))


@dataclass(frozen=True, slots=True, eq=False)
class RowScan:
    source: Any
    realization: BoundSource
    use: Any
    symbol: SQLSymbol
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class RowNamedUse:
    body: Any
    use: Any
    symbol: SQLSymbol
    binding: ScopeUse


@dataclass(frozen=True, slots=True, eq=False)
class RowStageUse:
    body: Any
    block: Any
    symbol: SQLSymbol


@dataclass(frozen=True, slots=True, eq=False)
class RowCarryColumn:
    ordinal: int
    export: Any
    input_port: Any
    read: rows.StageColumn
    symbol: SQLSymbol
    label: str
    column: rows.StageColumn


@dataclass(frozen=True, slots=True, eq=False)
class RowValueColumn:
    ordinal: int
    export: Any
    projection: Any
    site: Any
    expression: Any
    value: Any
    symbol: SQLSymbol
    label: str
    column: rows.StageColumn
    link: TerminalBinding | None


@dataclass(frozen=True, slots=True, eq=False)
class RowPredicate:
    original: Any
    expression: Any
    value: Any


@dataclass(frozen=True, slots=True, eq=False)
class RowBody:
    """One generated SELECT bound to one actual original stage occurrence."""

    definition: ScopeDefinition
    block: Any
    index: int
    scan: Any
    columns: tuple[Any, ...]
    terminals: tuple[Any, ...]
    predicate: RowPredicate | None
    final: bool
    symbol: SQLSymbol | None
    cte_columns: tuple[SQLSymbol, ...]
    aggregation: Any = None
    """This body's own realized GROUPED/GLOBAL stage, when it has one."""
    window: Any = None
    """This body's own realized window stage, when it has one."""


@dataclass(frozen=True, slots=True, eq=False)
class RowJoinUse:
    """A joined definition's first stage body reading its published joined ports."""

    body: Any
    tail: Any
    symbol: SQLSymbol


@dataclass(frozen=True, slots=True, eq=False)
class SQLRowQuery:
    request: PreparedEmission
    bodies: tuple[RowBody, ...]
    nodes: int


@dataclass(frozen=True, slots=True, eq=False)
class SQLJoinQuery:
    """Ordered generated units: one per JOIN occurrence, then its row stages."""

    request: PreparedEmission
    units: tuple[Any, ...]
    nodes: int

    @property
    def bodies(self) -> tuple[Any, ...]:
        return tuple(item for item in self.units if type(item) is RowBody)


@dataclass(frozen=True, slots=True, eq=False)
class JoinRealization:
    problems: tuple[Blocker, ...]
    query: SQLJoinQuery | None


@dataclass(frozen=True, slots=True, eq=False)
class RowRealization:
    problems: tuple[Blocker, ...]
    query: SQLRowQuery | None


def definition_blocks(request):
    """Group actual blocks by definition in retained definition and stage order."""
    plan = request.plan
    sources = {source.ref for source in plan.sources}
    grouped: dict[Any, list[Any]] = {}
    for block in plan.blocks:
        grouped.setdefault(block.definition, []).append(block)
    return tuple(
        (
            definition,
            tuple(
                sorted(
                    grouped.get(definition.original.ref, ()),
                    key=lambda block: block.position,
                )
            ),
        )
        for definition in request.layout.definitions
        if definition.original.ref not in sources
    )


def admitted_row_shape(plan):
    """One input relation and ordered LET/WHERE/aggregate/satisfying/projection."""
    named = tuple(
        d
        for d in plan.bindings.definitions
        if type(d.entry.owner.definition) is not SourceDef
    )
    return bool(
        len(plan.sources) == 1
        and named
        and len(plan.input_uses) == len(named)
        and len(plan.projections)
        + len(plan.aggregate_projections)
        + len(plan.window_projections)
        == len(plan.all_exports)
        and not any(
            (
                plan.joins,
                plan.distincts,
                plan.orders,
                plan.result_limits,
                plan.set_bodies,
            )
        )
        and all(type(e) in ADMITTED_STAGE_EXPRESSIONS for e in plan.expressions)
        and grouping.blocks_admitted(plan, single_input_use=True)
        and windowing.blocks_admitted(plan)
    )


def _stage_read(request, scan, position, port):
    """The exact scan column one stage input port carries, with its origin."""
    if type(scan) is RowScan:
        link = scan.binding.bindings[position]
        matches = tuple(
            f for f in scan.realization.fields if f.field is link.canonical.field
        )
        if len(matches) != 1 or link.terminal is not link.canonical:
            return None
        field = matches[0]
        realization = rows.field_realization(field)
        if realization is None:
            return None
        return rows.StageColumn(
            position,
            field.column,
            link.canonical.ref,
            realization,
            field=field,
            source_port=link.canonical.ref,
        )
    if type(scan) is RowNamedUse:
        link = scan.binding.bindings[position]
        column = scan.body.columns[position].column
        if column.terminal is not link.terminal.ref:
            return None
        return replace(column, position=position, name=f"c{position}")
    if type(scan) is RowJoinUse:
        reference = scan.tail.ports[position]
        matches = tuple(
            item for item in scan.body.columns if item.port.ref is reference
        )
        if len(matches) != 1:
            return None
        return replace(matches[0].column, position=position, name=matches[0].label)
    assert type(scan) is RowStageUse
    column = scan.body.columns[position].column
    return replace(column, position=position, name=f"c{position}")


def _join_input(
    request,
    join,
    reference,
    uses_by_ref,
    source_refs,
    by_definition,
    by_join,
    join_inputs,
    join_ports,
):
    """One JOIN input relation and the exact pre-match column it publishes."""
    original = join_inputs[reference]
    alias = SQLSymbol(0, original.ref, f"m{original.ref.position}")
    use = None
    producer: Any = None
    source_ref: Any = None
    reads: list[rows.StageColumn] = []
    if original.binding_use is not None:
        use = uses_by_ref.get(original.binding_use)
        if use is None or use.original.consumer is not join.definition:
            return None, ("PIE-B1001", "join_input_use_not_bound", original.ref, None)
        if use.original.producer in source_refs:
            source = source_refs[use.original.producer]
            matches = tuple(
                item for item in request.sources if item.owner is source.source.owner
            )
            if len(matches) != 1:
                return None, ("PIE-B1001", "source_mapping_missing", source.ref, None)
            producer = matches[0]
            source_ref = source.ref
            for position, port_ref in enumerate(original.ports):
                link = use.bindings[position]
                fields = tuple(
                    item
                    for item in producer.fields
                    if item.field is link.canonical.field
                )
                if len(fields) != 1 or link.terminal is not link.canonical:
                    return None, (
                        "PIE-B1001",
                        "join_input_source_field_not_bound",
                        port_ref,
                        None,
                    )
                realization = rows.field_realization(fields[0])
                if realization is None:
                    return None, (
                        "PIE-B1004",
                        "join_input_field_representation_missing",
                        port_ref,
                        None,
                    )
                reads.append(
                    rows.StageColumn(
                        position,
                        fields[0].column,
                        link.canonical.ref,
                        realization,
                        field=fields[0],
                        source_port=link.canonical.ref,
                        scope=alias,
                    )
                )
        else:
            producer = by_definition.get(use.original.producer)
            if producer is None:
                return None, (
                    "PIE-B1001",
                    "named_producer_not_realized",
                    original.ref,
                    None,
                )
            for position, port_ref in enumerate(original.ports):
                column = producer.columns[position].column
                if column.terminal is not use.bindings[position].terminal.ref:
                    return None, (
                        "PIE-B1001",
                        "join_input_terminal_drift",
                        port_ref,
                        None,
                    )
                reads.append(
                    replace(column, position=position, name=f"c{position}", scope=alias)
                )
    else:
        producer = by_join.get(original.predecessor)
        if producer is None:
            return None, (
                "PIE-B1001",
                "join_predecessor_not_realized",
                original.ref,
                None,
            )
        for position, port_ref in enumerate(original.ports):
            column = producer.columns[position]
            if column.port.ref is not join_ports[port_ref].source:
                return None, (
                    "PIE-B1001",
                    "join_predecessor_port_drift",
                    port_ref,
                    None,
                )
            reads.append(
                replace(
                    column.column, position=position, name=column.label, scope=alias
                )
            )
    columns = []
    for position, port_ref in enumerate(original.ports):
        port = join_ports[port_ref]
        realization, problem = joining.port_realization(
            port, reads[position], outer=False
        )
        if realization is None:
            assert problem is not None
            return None, (*problem, port_ref, None)
        columns.append(replace(reads[position], realization=realization))
    return (
        joining.JoinInput(
            original,
            original.ordinal,
            use,
            producer,
            alias,
            tuple(columns),
            tuple(original.ports),
            source_ref,
        ),
        None,
    )


def _join_body(
    request,
    join,
    index,
    uses_by_ref,
    source_refs,
    by_definition,
    by_join,
    join_inputs,
    join_ports,
    equalities,
    uses,
):
    """Realize one JOIN occurrence as its own closed generated SELECT."""
    inputs = []
    for reference in join.inputs:
        value, problem = _join_input(
            request,
            join,
            reference,
            uses_by_ref,
            source_refs,
            by_definition,
            by_join,
            join_inputs,
            join_ports,
        )
        if value is None:
            return None, problem
        inputs.append(value)
    left, right = inputs
    available = {}
    for item in inputs:
        for port_ref, column in zip(item.ports, item.columns, strict=True):
            available[port_ref] = column
    matches = []
    for reference in join.equalities:
        original = equalities.get(reference)
        if original is None or original.join is not join.ref:
            return None, (
                "PIE-B1001",
                "relationship_equality_not_retained",
                join.ref,
                None,
            )
        pair = (available.get(original.left), available.get(original.right))
        if pair[0] is None or pair[1] is None:
            return None, (
                "PIE-B1001",
                "relationship_equality_outside_pre_match_scope",
                reference,
                None,
            )
        if pair[0].realization.tag != pair[1].realization.tag:
            return None, (
                "PIE-B1002",
                "relationship_equality_type_pair_drift",
                reference,
                None,
            )
        matches.append(
            joining.JoinEquality(
                original,
                pair[0],
                pair[1],
                original.left,
                original.right,
                pair[0].scope,
                pair[1].scope,
            )
        )
    predicate = None
    if join.on is not None:
        predicate, problem = rows.build_row_value(
            request,
            available,
            join.on,
            uses,
            reference_type=row.ProjectSQLMatchReference,
        )
        if predicate is None:
            assert problem is not None
            site = join.site
            return None, (
                *problem,
                join.on,
                None if site is None else site.occurrence.span,
            )
        realization = rows.realization_of(predicate, request.family)
        if realization.tag != "Bool" or realization.domain.get("kind") != "bool01":
            return None, (
                "PIE-B1002",
                "match_condition_root_not_bool",
                join.on,
                None,
            )
    if not matches and predicate is None and join.kind is not AuthoredJoinKind.CROSS:
        return None, ("PIE-B1004", "match_condition_evidence_missing", join.ref, None)
    if join.kind is AuthoredJoinKind.FULL:
        problem = joining.full_admissible(
            join, tuple(matches), predicate, request.family
        )
        if problem is not None:
            return None, (*problem, join.ref, None)
    membership = joining.MEMBERSHIP.get(join.kind)
    if membership is not None and predicate is None and not matches:
        return None, ("PIE-B1004", "membership_condition_missing", join.ref, None)
    columns = []
    ordered = (*left.columns, *right.columns)
    carriers = (*left.ports, *right.ports)
    rejected = joining.null_rejected_ports(join, tuple(matches), predicate)
    for position, reference in enumerate(join.outputs):
        port = join_ports[reference]
        read = ordered[position]
        realization, problem = joining.port_realization(
            port, read, outer=True, proved=carriers[position] in rejected
        )
        if realization is None:
            assert problem is not None
            return None, (*problem, reference, None)
        label = f"c{position}"
        columns.append(
            joining.JoinColumn(
                position,
                port,
                join_ports[carriers[position]],
                label,
                SQLSymbol(position + 1, port.ref, label),
                replace(
                    read,
                    position=position,
                    name=label,
                    terminal=port.ref,
                    realization=realization,
                    scope=None,
                ),
                read.scope,
                read,
            )
        )
    return (
        joining.JoinBody(
            join,
            index,
            (left, right),
            tuple(matches),
            predicate,
            tuple(columns),
            SQLSymbol(index, join.ref, f"p{index}"),
            tuple(
                SQLSymbol(i, item.port.ref, item.label)
                for i, item in enumerate(columns)
            ),
            membership,
            None if membership is None else join.ref,
        ),
        None,
    )


def _join_node_count(unit) -> int:
    total = 4 + 3 * len(unit.columns) + 2 * len(unit.equalities)
    if unit.membership is not None:
        total += 3
    if unit.predicate is not None:
        total += _value_node_count(unit.predicate)
    return total


def realize_rows(request):
    """Realize every stage body once; construction and checking share this walk."""
    plan = request.plan
    family = request.family
    problems: list[Blocker] = []

    def add(code, detail, subject=None, location=None):
        problems.append(Blocker(code, detail, subject, location))

    groups = definition_blocks(request)
    uses_by_consumer = {u.consumer.original.ref: u for u in request.layout.uses}
    uses_by_ref = {u.original.ref: u for u in request.layout.uses}
    source_refs = {source.ref: source for source in plan.sources}
    lets = {value.site.block: value for value in plan.let_values}
    filters = {item.site.block: item for item in plan.filters}
    join_groups = joining.joined_definitions(plan)
    tails = {tail.definition: tail for tail in plan.join_tails}
    join_inputs = {item.ref: item for item in plan.join_inputs}
    join_ports = {port.ref: port for port in plan.join_ports}
    equalities = {item.ref: item for item in plan.relationship_matches}
    projections: dict[Any, list[Any]] = {}
    for projection in plan.projections:
        projections.setdefault(projection.block, []).append(projection)
    stages = grouping.aggregated_definitions(plan)
    aggregate_keys: dict[Any, list[Any]] = {}
    for key in plan.group_keys:
        aggregate_keys.setdefault(key.aggregation, []).append(key)
    aggregate_values: dict[Any, list[Any]] = {}
    for value in plan.aggregates:
        aggregate_values.setdefault(value.aggregation, []).append(value)
    aggregate_projections: dict[Any, list[Any]] = {}
    for projection in plan.aggregate_projections:
        aggregate_projections.setdefault(projection.block, []).append(projection)
    window_blocks = windowing.windowed_blocks(plan)
    window_policy = windowing.window_policies(plan)
    window_argument = windowing.window_arguments(plan)
    window_use = windowing.window_uses(plan)
    window_projection: dict[Any, list[Any]] = {}
    for entry in plan.window_projections:
        window_projection.setdefault(entry.block, []).append(entry)
    ordered = []
    for definition, blocks in groups:
        stage = stages.get(definition.original.ref)
        for join in join_groups.get(definition.original.ref, ()):
            if join.on is not None:
                ordered.append(join.on)
        for block in blocks:
            kind = block.kind.value
            if kind == "let":
                ordered.append(lets[block.ref].expression)
            elif kind in {"where", "satisfying", "qualify"}:
                ordered.append(filters[block.ref].predicate)
            elif kind == "aggregate":
                assert stage is not None
                for value in aggregate_values.get(stage.ref, ()):
                    ordered.extend(value.arguments)

            else:
                ordered.extend(p.expression for p in projections.get(block.ref, ()))
    occurrences = []
    for reference in ordered:
        try:
            chains = rows.constant_chains(plan, reference)
        except ValueError:
            add("PIE-B1008", "expression_tree_structure", reference)
            continue
        for chain, leaf in chains:
            problem = parameters.chain_problem(plan, chain, family)
            if problem is not None:
                add(*problem, chain, leaf.site.occurrence.span)
            elif type(leaf) is row.ProjectSQLBoundLiteral:
                tag = parameters.tag_of(leaf)
                assert tag is not None
                occurrences.append((leaf, parameters.PHYSICAL[family][tag]))
    if problems:
        return RowRealization(tuple(problems), None)
    try:
        allocated = parameters.allocate_uses(
            family, tuple(occurrences), resource_limits(request)["parameters"]
        )
    except ValueError as error:
        return RowRealization(
            (Blocker("PIE-B1008", "native_occurrence_allocation", str(error)),), None
        )
    uses = {use.original.ref: use for use in allocated}
    stage_ports = {port.ref: port for port in plan.stage_ports}
    units: list[Any] = []
    bodies: list[RowBody] = []
    by_definition: dict[Any, RowBody] = {}
    by_join: dict[Any, joining.JoinBody] = {}
    nodes = 0
    for definition, blocks in groups:
        joined = join_groups.get(definition.original.ref, ())
        for join in joined:
            unit, problem = _join_body(
                request,
                join,
                len(units),
                uses_by_ref,
                source_refs,
                by_definition,
                by_join,
                join_inputs,
                join_ports,
                equalities,
                uses,
            )
            if unit is None:
                assert problem is not None
                add(*problem[:2], *problem[2:])
                return RowRealization(tuple(problems), None)
            units.append(unit)
            by_join[join.ref] = unit
            nodes += _join_node_count(unit)
        binding = uses_by_consumer.get(definition.original.ref)
        previous: RowBody | None = None
        for index, block in enumerate(blocks):
            if index == 0 and joined:
                tail = tails[definition.original.ref]
                scan: Any = RowJoinUse(
                    by_join[joined[-1].ref],
                    tail,
                    SQLSymbol(0, tail.ref, f"t{tail.ref.position}"),
                )
            elif index == 0:
                assert binding is not None
                use = binding.original
                alias = SQLSymbol(0, use.ref, f"s{use.ref.position}")
                if use.producer in source_refs:
                    source = source_refs[use.producer]
                    matches = tuple(
                        s for s in request.sources if s.owner is source.source.owner
                    )
                    if len(matches) != 1:
                        add("PIE-B1001", "source_mapping_missing", source.ref)
                        return RowRealization(tuple(problems), None)
                    scan = RowScan(source, matches[0], use, alias, binding)
                else:
                    producer = by_definition.get(use.producer)
                    if producer is None:
                        add("PIE-B1001", "named_producer_not_realized", use.ref)
                        return RowRealization(tuple(problems), None)
                    scan = RowNamedUse(producer, use, alias, binding)
            else:
                assert previous is not None
                scan = RowStageUse(
                    previous, block, SQLSymbol(0, block.ref, f"t{block.ref.position}")
                )
            reference_type = (
                row.ProjectSQLJoinedReference if joined else row.ProjectSQLReference
            )
            incoming = []
            for position, port in enumerate(block.inputs):
                read = _stage_read(request, scan, position, port)
                if read is None:
                    add("PIE-B1001", "stage_input_not_bound", port)
                    return RowRealization(tuple(problems), None)
                incoming.append(read)
            columns: list[Any] = []
            available = {
                port: read for port, read in zip(block.inputs, incoming, strict=True)
            }
            kind = block.kind.value
            final = kind == "projection" and (
                definition.original.entry.owner is plan.scope.selected_owner
            )
            stage = stages.get(definition.original.ref)
            aggregate_stage = None
            window_stage = None
            block_exports: tuple[Any, ...] = ()
            if kind != "projection":
                resolved = [stage_ports.get(ref) for ref in block.exports]
                if any(port is None for port in resolved):
                    add("PIE-B1001", "stage_export_not_bound", block.ref)
                    return RowRealization(tuple(problems), None)
                block_exports = tuple(resolved)
            if kind == "aggregate":
                assert stage is not None
                built, aggregate_stage, problem = grouping.build_stage(
                    request,
                    stage,
                    block_exports,
                    available,
                    tuple(aggregate_keys.get(stage.ref, ())),
                    tuple(aggregate_values.get(stage.ref, ())),
                    uses,
                    reference_type=reference_type,
                    symbol=SQLSymbol,
                )
                if built is None:
                    assert problem is not None
                    add(*problem)
                    return RowRealization(tuple(problems), None)
                assert aggregate_stage is not None
                columns.extend(built)
                nodes += grouping.node_count(aggregate_stage, _value_node_count)
                exports: tuple[Any, ...] = ()
                items: tuple[Any, ...] = ()
            elif (
                kind == "projection"
                and stage is not None
                and not window_projection.get(block.ref)
            ):
                built, problem = grouping.build_projections(
                    request,
                    stage,
                    block,
                    definition.original.exports,
                    definition.terminals,
                    available,
                    tuple(aggregate_projections.get(block.ref, ())),
                    final,
                    symbol=SQLSymbol,
                )
                if built is None:
                    assert problem is not None
                    add(*problem)
                    return RowRealization(tuple(problems), None)
                columns.extend(built)
                exports = ()
                items = ()
            else:
                if kind != "projection":
                    for position, read in enumerate(incoming):
                        label = f"c{position}"
                        export = block_exports[position]
                        if export.source is not block.inputs[position]:
                            add("PIE-B1001", "stage_carry_port_drift", export)
                            return RowRealization(tuple(problems), None)
                        columns.append(
                            RowCarryColumn(
                                position,
                                export,
                                block.inputs[position],
                                read,
                                SQLSymbol(position + 1, export.ref, label),
                                label,
                                replace(
                                    read,
                                    position=position,
                                    name=label,
                                    terminal=export.ref,
                                ),
                            )
                        )
                if kind == "window":
                    built, window_stage, problem = windowing.build_stage(
                        request,
                        block,
                        block_exports[len(incoming) :],
                        available,
                        tuple(window_blocks.get(block.ref, ())),
                        window_policy,
                        window_argument,
                        window_use,
                        position_base=len(columns),
                        symbol=SQLSymbol,
                    )
                    if built is None:
                        assert problem is not None
                        add(*problem)
                        return RowRealization(tuple(problems), None)
                    assert window_stage is not None
                    columns.extend(built)
                    nodes += windowing.node_count(window_stage, _value_node_count)
                exports = (
                    definition.original.exports
                    if kind == "projection"
                    else ()
                    if kind == "window"
                    else block_exports[len(incoming) :]
                )
                if kind == "projection":
                    # A visible projection may mix ordinary values with this
                    # body's own window results, so each export takes exactly
                    # the one item that claims it, in export order.
                    claims: dict[Any, Any] = {}
                    for entry in projections.get(block.ref, ()):
                        claims[entry.export] = entry
                    for entry in aggregate_projections.get(block.ref, ()):
                        if entry.export in claims:
                            add("PIE-B1001", "projection_export_conflict", entry.ref)
                            return RowRealization(tuple(problems), None)
                        claims[entry.export] = entry
                    for entry in window_projection.get(block.ref, ()):
                        if entry.export in claims:
                            add("PIE-B1001", "projection_export_conflict", entry.ref)
                            return RowRealization(tuple(problems), None)
                        claims[entry.export] = entry
                    items = tuple(claims.get(export.ref) for export in exports)
                    if any(item is None for item in items):
                        add("PIE-B1001", "stage_export_denominator", block.ref)
                        return RowRealization(tuple(problems), None)
                else:
                    items = (lets[block.ref],) if kind == "let" else ()
                    if len(items) != len(exports):
                        add("PIE-B1001", "stage_export_denominator", block.ref)
                        return RowRealization(tuple(problems), None)
            for offset, (item, export) in enumerate(zip(items, exports, strict=True)):
                position = len(columns)
                label = export.identity.name if final else f"c{position}"
                if type(item) is grouping.plan_projection_type():
                    read = available.get(item.input)
                    if (
                        read is None
                        or stage is None
                        or item.aggregation is not stage.ref
                    ):
                        add("PIE-B1001", "aggregate_projection_drift", item.ref)
                        return RowRealization(tuple(problems), None)
                    terminal = definition.terminals[position]
                    columns.append(
                        grouping.AggregateProjectionColumn(
                            position,
                            export,
                            item,
                            item.input,
                            read,
                            SQLSymbol(position + 1, export.ref, label),
                            label,
                            replace(
                                read,
                                position=position,
                                name=label,
                                terminal=terminal.ref,
                            ),
                        )
                    )
                    continue
                if type(item) is windowing.plan_projection_type():
                    # This visible output IS an established window result port.
                    built, problem = windowing.build_projection(
                        block,
                        item,
                        export,
                        definition.terminals[position],
                        available,
                        position,
                        label,
                        symbol=SQLSymbol,
                    )
                    if built is None:
                        assert problem is not None
                        add(*problem)
                        return RowRealization(tuple(problems), None)
                    columns.append(built)
                    continue
                value, problem = rows.build_row_value(
                    request,
                    available,
                    item.expression,
                    uses,
                    reference_type=reference_type,
                )
                if value is None:
                    # Every unsupported value in this body keeps its own cause.
                    assert problem is not None
                    add(*problem, item.ref, item.site.occurrence.span)
                    continue
                if kind == "let" and export.source is not item.expression:
                    add("PIE-B1001", "let_export_expression_drift", export)
                    return RowRealization(tuple(problems), None)
                terminal = (
                    definition.terminals[position] if kind == "projection" else export
                )
                column = _value_column_image(
                    request, value, position, label, export, terminal, family
                )
                link = None
                if (
                    index == 0
                    and not joined
                    and binding is not None
                    and type(value) is rows.SQLStageReference
                ):
                    slot = block.inputs.index(value.port)
                    link = binding.bindings[slot]
                columns.append(
                    RowValueColumn(
                        position,
                        export,
                        item if kind == "projection" else None,
                        item.site,
                        item.expression,
                        value,
                        SQLSymbol(position + 1, export.ref, label),
                        label,
                        column,
                        link,
                    )
                )
                nodes += 1 + _value_node_count(value)
            if problems:
                return RowRealization(tuple(problems), None)
            predicate = None
            if kind in {"where", "satisfying", "qualify"}:
                item = filters[block.ref]
                value, problem = rows.build_row_value(
                    request,
                    available,
                    item.predicate,
                    uses,
                    reference_type=grouping.ProjectSQLResultReference
                    if kind == "satisfying"
                    else reference_type,
                )
                if value is None:
                    assert problem is not None
                    add(*problem, item.ref, item.site.occurrence.span)
                    return RowRealization(tuple(problems), None)
                realization = rows.realization_of(value, family)
                if realization.tag != "Bool" or realization.domain.get("kind") != (
                    "bool01"
                ):
                    add("PIE-B1002", "predicate_root_not_bool", item.ref)
                    return RowRealization(tuple(problems), None)
                if (
                    tuple(
                        (effect.truth.value, effect.retain_row)
                        for effect in item.retention_effects
                    )
                    != RETENTION
                ):
                    add("PIE-B1005", "predicate_retention_effects_changed", item.ref)
                    return RowRealization(tuple(problems), None)
                predicate = RowPredicate(item, item.predicate, value)
                nodes += _value_node_count(value)
            terminals = definition.terminals if kind == "projection" else block_exports
            if len(terminals) != len(columns):
                add("PIE-B1001", "stage_terminal_denominator", block.ref)
                return RowRealization(tuple(problems), None)
            body = RowBody(
                definition,
                block,
                index,
                scan,
                tuple(columns),
                tuple(terminals),
                predicate,
                final,
                None if final else SQLSymbol(len(units), block.ref, f"p{len(units)}"),
                ()
                if final
                else tuple(
                    SQLSymbol(i, terminal.ref, f"c{i}")
                    for i, terminal in enumerate(terminals)
                ),
                aggregate_stage,
                window_stage,
            )
            bodies.append(body)
            units.append(body)
            previous = body
            if kind == "projection":
                by_definition[definition.original.ref] = body
    if not bodies or not bodies[-1].final or units[-1] is not bodies[-1]:
        add("PIE-B1001", "selected_body_not_last", plan.scope)
        return RowRealization(tuple(problems), None)
    nodes += 3 * len(bodies) + 2 * sum(len(b.columns) for b in bodies)
    nodes += sum(2 + len(b.columns) for b in bodies[:-1])
    if plan.joins:
        return JoinRealization((), SQLJoinQuery(request, tuple(units), nodes))
    return RowRealization((), SQLRowQuery(request, tuple(bodies), nodes))


def _value_node_count(value):
    total = 0
    for node in rows.value_nodes(value):
        total += (
            1
            if type(node) in {rows.SQLStageReference, rows.SQLOperation}
            else len(parameters.value_nodes(node))
        )
    return total


def _value_column_image(request, value, position, label, export, terminal, family):
    """One output column's retained facts: unmodified field, fixed value or computed."""
    realization = rows.realization_of(value, family)
    if type(value) is rows.SQLStageReference:
        return replace(
            value.column, position=position, name=label, terminal=terminal.ref
        )
    if type(value) is not rows.SQLOperation:
        return rows.StageColumn(
            position,
            label,
            terminal.ref,
            realization,
            literal=parameters.LiteralOrigin(value, export, terminal),
        )
    return rows.StageColumn(position, label, terminal.ref, realization)


def node_premises(request, realization, operands, kind):
    keys = {"operator_environment"}
    if realization.tag == "Text" or any(item.tag == "Text" for item in operands):
        keys.add("client_encoding")
    if kind == "parameter":
        keys.add("parameter_protocol")
    return tuple(
        p for p in request.premises if p.scope == "statement" and p.key in keys
    )


def value_requirements(request, value):
    """One requirement per actual node, in the exact order it is rendered."""
    family = request.family
    result = []
    for node in rows.value_nodes(value):
        if type(node) in {rows.SQLStageReference, rows.SQLOperation}:
            kind = rows.requirement_kind(node)
            operands = (
                ()
                if type(node) is rows.SQLStageReference
                else tuple(rows.realization_of(o, family) for o in node.operands)
            )
            result.append(
                GeneratedRequirement(
                    kind,
                    node.original.ref,
                    rows.REQUIREMENT_RULES[kind],
                    node_premises(request, node.realization, operands, kind),
                )
            )
            continue
        for leaf in parameters.value_nodes(node):
            kind = (
                "unary"
                if type(leaf) is parameters.SQLUnary
                else "type_anchor"
                if type(leaf) is parameters.SQLAnchor
                else "parameter"
                if type(leaf) is parameters.SQLParameter
                else "literal"
            )
            result.append(
                GeneratedRequirement(
                    kind,
                    leaf.original.ref,
                    "R04",
                    parameters.anchor_premises(
                        request, kind, parameters.tag_of(leaf.original)
                    ),
                )
            )
    return tuple(result)


def join_requirements(request, unit, naming):
    """Every requirement this JOIN occurrence's own structure introduces."""
    join = unit.join
    rule = joining.join_rule(join.kind)
    result = [GeneratedRequirement("join", join.ref, rule, naming)]
    for item in unit.inputs:
        result.append(
            GeneratedRequirement("join_input", item.original.ref, "R07", naming)
        )
        # A JOIN input that reaches a physical relation keeps the same source
        # realization and field representation obligations as any other scan.
        if type(item.producer) is BoundSource:
            result.append(
                GeneratedRequirement(
                    "qualified_scan",
                    item,
                    "R01",
                    applicable_premises(request, item.producer.owner),
                )
            )
            result.extend(
                GeneratedRequirement(
                    "source_representation",
                    field,
                    "R02",
                    applicable_premises(request, item.producer.owner, field),
                )
                for field in item.producer.fields
            )
    for item in unit.equalities:
        result.append(
            GeneratedRequirement(
                "relationship_equality", item.original.ref, "R07", naming
            )
        )
    if unit.predicate is not None:
        result.append(
            GeneratedRequirement(
                "match_condition",
                join.on,
                "R07",
                node_premises(
                    request,
                    rows.realization_of(unit.predicate, request.family),
                    (),
                    "match_condition",
                ),
            )
        )
        result.extend(value_requirements(request, unit.predicate))
    if join.kind is AuthoredJoinKind.FULL:
        result.append(GeneratedRequirement("full_condition", join.ref, "R09", naming))
    if unit.membership is not None:
        result.append(GeneratedRequirement("membership", join.ref, "R11", naming))
        result.append(GeneratedRequirement("correlation", join.ref, "R11", naming))
        result.append(GeneratedRequirement("sentinel", unit.sentinel, "R11", naming))
    for column in unit.columns:
        result.append(
            GeneratedRequirement("join_output", column.port.ref, "R07", naming)
        )
        if column.port.nulling:
            result.append(
                GeneratedRequirement("null_extension", column.port.ref, "R08", naming)
            )
    return tuple(result)


def build_row_requirements(request, query):
    units = getattr(query, "units", query.bodies)
    generated_scopes = len(units) > 1
    original = tuple(
        OriginalRequirement(
            entry,
            original_rule(request.plan, entry, generated_scopes=generated_scopes),
        )
        for entry in request.report.report.entries
    )
    naming = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "identifier_case"
    )
    generated: list[GeneratedRequirement] = []
    for unit in units[:-1]:
        reference = unit.join.ref if type(unit) is joining.JoinBody else unit.block.ref
        generated.append(
            GeneratedRequirement("cte_definition", reference, "R03", naming)
        )
        generated.extend(
            GeneratedRequirement("terminal_column", symbol.binding, "R03", naming)
            for symbol in unit.cte_columns
        )
    for unit in units:
        if type(unit) is joining.JoinBody:
            generated.extend(join_requirements(request, unit, naming))
            continue
        body = unit
        scan = body.scan
        if type(scan) is RowScan:
            generated.append(
                GeneratedRequirement(
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            generated.extend(
                GeneratedRequirement(
                    "source_representation",
                    field,
                    "R02",
                    applicable_premises(request, scan.realization.owner, field),
                )
                for field in scan.realization.fields
            )
        elif type(scan) is RowNamedUse:
            generated.append(
                GeneratedRequirement("named_use", scan.use.ref, "R03", naming)
            )
            generated.extend(
                GeneratedRequirement(
                    "immediate_terminal", link.terminal.ref, "R03", naming
                )
                for link in scan.binding.bindings
            )
        elif type(scan) is RowJoinUse:
            generated.append(
                GeneratedRequirement("join_use", scan.tail.ref, "R07", naming)
            )
            generated.extend(
                GeneratedRequirement("join_terminal", symbol.binding, "R07", naming)
                for symbol in scan.body.cte_columns
            )
        else:
            generated.append(
                GeneratedRequirement("stage_use", scan.block.ref, "R03", naming)
            )
            generated.extend(
                GeneratedRequirement("stage_terminal", symbol.binding, "R03", naming)
                for symbol in scan.body.cte_columns
            )
        operators = tuple(
            p
            for p in request.premises
            if p.scope == "statement" and p.key == "operator_environment"
        )
        if body.aggregation is not None:
            generated.append(
                GeneratedRequirement(
                    "aggregation", body.aggregation.aggregation.ref, "R12", operators
                )
            )
        for column in body.columns:
            if type(column) is RowCarryColumn:
                generated.append(
                    GeneratedRequirement(
                        "carry_projection", column.export.ref, "R05", ()
                    )
                )
                continue
            if type(column) is grouping.AggregateKeyColumn:
                generated.append(
                    GeneratedRequirement("group_key", column.key.ref, "R12", operators)
                )
                continue
            if type(column) is grouping.AggregateValueColumn:
                generated.append(
                    GeneratedRequirement(
                        "aggregate", column.aggregate.ref, "R13", operators
                    )
                )
                if column.argument is not None:
                    generated.extend(value_requirements(request, column.argument))
                continue
            if type(column) is grouping.AggregateProjectionColumn:
                generated.append(
                    GeneratedRequirement(
                        "result_projection", column.projection.ref, "R12", ()
                    )
                )
                continue
            if type(column) is windowing.WindowColumn:
                # R14 owns the computation, its input BAG and its result
                # representation; R15 owns the realized frame and named
                # components. Each generated structure keeps its own cause.
                generated.append(
                    GeneratedRequirement(
                        "window_computation", column.window.ref, "R14", operators
                    )
                )
                generated.append(
                    GeneratedRequirement(
                        "window_specification", column.window.policy, "R15", ()
                    )
                )
                for _binding, read in column.specification.partitions:
                    generated.append(
                        GeneratedRequirement(
                            "window_partition_comparison", read.terminal, "R14", ()
                        )
                    )
                for item in column.specification.orders:
                    generated.append(
                        GeneratedRequirement(
                            "window_order_comparison", item.read.terminal, "R14", ()
                        )
                    )
                continue
            if type(column) is windowing.WindowProjectionColumn:
                generated.append(
                    GeneratedRequirement(
                        "window_result_projection", column.projection.ref, "R17", ()
                    )
                )
                continue
            generated.append(
                GeneratedRequirement(
                    "computed_projection", column.export.ref, "R05", ()
                )
            )
            generated.extend(value_requirements(request, column.value))
        if body.predicate is not None:
            satisfying = body.block.kind.value == "satisfying"
            generated.append(
                GeneratedRequirement(
                    "satisfying_root" if satisfying else "predicate_root",
                    body.predicate.original.ref,
                    "R12" if satisfying else "R06",
                    operators,
                )
            )
            generated.extend(value_requirements(request, body.predicate.value))
        generated.append(
            GeneratedRequirement("read_only_select_bytes", body, "R23", ())
        )
    if generated_scopes:
        generated.append(
            GeneratedRequirement("nonrecursive_with_bytes", query, "R23", ())
        )
    return original, tuple(generated)


def row_parameter_leaves(query):
    """Native parameter leaves in exact rendering order across every unit."""
    result = []
    for body in getattr(query, "units", query.bodies):
        if type(body) is joining.JoinBody:
            values = [] if body.predicate is None else [body.predicate]
        else:
            values = []
            for column in body.columns:
                if type(column) is RowValueColumn:
                    values.append(column.value)
                elif (
                    type(column) is grouping.AggregateValueColumn
                    and column.argument is not None
                ):
                    values.append(column.argument)
            if body.predicate is not None:
                values.append(body.predicate.value)
        for value in values:
            for node in rows.value_nodes(value):
                if type(node) in {rows.SQLStageReference, rows.SQLOperation}:
                    continue
                result.extend(
                    leaf
                    for leaf in parameters.value_nodes(node)
                    if type(leaf) is parameters.SQLParameter
                )
    return tuple(result)
